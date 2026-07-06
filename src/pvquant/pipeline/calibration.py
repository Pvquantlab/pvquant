"""SCADA verisinden model parametre kalibrasyonu.

Senin diyagramındaki sol kol — "santral verisi olursa" akışı:

.. code::

    SCADA tarihçesi (en az 6 ay)
        +
    Tarihsel meteoroloji (Open-Meteo arşivi)
        ↓
    Forecast pipeline çalıştır (default parametrelerle)
        ↓
    Model çıktısı vs gerçek SCADA üretimi karşılaştır
        ↓
    En küçük kareler ile parametreleri fit et:
        - BG (geometrik arka yüz oranı)
        - η_BoS (toplam BoS verimi)
        - opsiyonel: c1, c2, γ (Barhdadi-Bennis)
        ↓
    Kalibre edilmiş PlantSpec
        ↓
    Bu spec ile forecast_7day çağrısı yap → daha doğru tahmin

Bu, PVQuant'ın "saha-kalibre" özelliğinin teknik karşılığıdır.
"""
from __future__ import annotations

from typing import Optional, List

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar

from pvquant.io.meteo import MeteoData
from pvquant.io.scada import SCADAData
from pvquant.pipeline.forecast import PlantSpec, forecast_7day
from pvquant.pipeline.utils import _align_meteo_to_scada, _detect_timestep_hours
from pvquant.validation.metrics import ValidationReport, validate


@dataclass
class CalibrationResult:
    """Kalibrasyon sonucu.

    Attributes:
        plant: Kalibre edilmiş PlantSpec.
        original_plant: Kalibrasyon öncesi PlantSpec.
        validation_before: Kalibrasyon öncesi doğrulama raporu.
        validation_after: Kalibrasyon sonrası doğrulama raporu.
        bg: Geri hesaplanmış BG değeri (bifacial sistemler için).
        eta_bos: Fit edilmiş BoS verimi.
        n_valid_hours: Kalibrasyonda kullanılan geçerli saat sayısı.
        notes: Açıklayıcı notlar.
    """

    plant: PlantSpec
    original_plant: PlantSpec
    validation_before: ValidationReport
    validation_after: ValidationReport
    bg: float
    eta_bos: float
    n_valid_hours: int
    notes: list[str] = field(default_factory=list)
    # --- Faz 1.9.1: warnings alani ---
    warnings: list[str] = field(default_factory=list)

    @property
    def mape_improvement_pct(self) -> float:
        """Kalibrasyon sonrası MAPE iyileşmesi (mutlak puan)."""
        return self.validation_before.mape_pct - self.validation_after.mape_pct

    def __str__(self) -> str:
        base = (
            f"CalibrationResult(\n"
            f"  BG (geometrik)     = {self.bg:.4f}\n"
            f"  η_BoS              = {self.eta_bos:.4f}\n"
            f"  Geçerli saat       = {self.n_valid_hours}\n"
            f"  MAPE öncesi        = {self.validation_before.mape_pct:.2f} %\n"
            f"  MAPE sonrası       = {self.validation_after.mape_pct:.2f} %\n"
            f"  İyileşme           = {self.mape_improvement_pct:+.2f} puan\n"
            f"  Toplam sapma öncesi  = {self.validation_before.total_deviation_pct:+.2f} %\n"
            f"  Toplam sapma sonrası = {self.validation_after.total_deviation_pct:+.2f} %\n"
            f")"
        )
        # --- Faz 1.9.1: notes+warnings repr ---
        if self.warnings:
            warn_lines = ["", "  UYARILAR:"]
            for w in self.warnings:
                warn_lines.append(f"    * {w}")
            base += "\n" + "\n".join(warn_lines)
        return base


def calibrate_from_scada(
    scada: SCADAData,
    historical_meteo: MeteoData,
    plant: PlantSpec,
    fit_bg: bool = True,
    fit_eta_bos: bool = True,
    # --- Faz 1.8.1: fit_azimuth parametresi ---
    fit_azimuth: bool = False,
    azimuth_bounds: tuple[float, float] = (90.0, 270.0),
    # --- Faz 1.9.0: fit_tilt parametresi ---
    fit_tilt: bool = False,
    tilt_bounds: tuple[float, float] = (5.0, 60.0),
    threshold_kw: float = 1.0,
    ghi_bias_bins: Optional[List[float]] = None,
    ghi_bias_corrections: Optional[List[float]] = None,
) -> CalibrationResult:
    """SCADA + tarihsel meteoroloji verisinden parametre kalibrasyonu.

    İki aşamalı yaklaşım:

    1. **η_BoS fit**: Toplam üretim sapmasını sıfıra çekecek tek skaler katsayı.
    2. **BG fit** (bifacial ise): Mevsimsel bifacial katkı için BG değerini
       en küçük kareler ile ayarla.

    Args:
        scada: Tarihsel SCADA verisi (en az 6 ay önerilir).
        historical_meteo: Aynı dönemin Open-Meteo arşiv verisi.
        plant: Başlangıç (kalibrasyon öncesi) PlantSpec.
        fit_bg: BG parametresini fit et.
        fit_eta_bos: η_BoS parametresini fit et.
        threshold_kw: Gece saatlerini elemek için eşik (kW).

    Returns:
        CalibrationResult.

    Raises:
        ValueError: Yetersiz veri (< 100 saat) veya hizalama problemi.

    Notlar:
        - Kalibrasyon SCADA'nın AC üretim verisi üzerinden yapılır.
        - BG fit'i bifacial sistemler için anlamlıdır (BF > 0).
        - Daha gelişmiş kalibrasyon (c1, c2, γ aynı anda) için
          gelecek versiyonda scipy.optimize.differential_evolution eklenecek.
    """
    notes: list[str] = []

    # --- Faz 1.8: SCADA tz-aware localize ---
    # SCADA tz-naive, meteo tz-aware oldugunda pvlib solar position hesabi
    # bozulur (Faz 1.7'de tespit edilen bug). SCADA'yi meteo'nun timezone'una
    # localize ederek buna cozum getir.
    from dataclasses import replace as _dc_replace
    _meteo_tz = getattr(historical_meteo.ghi.index, 'tz', None)
    _scada_tz = getattr(scada.power_kw.index, 'tz', None)
    if _meteo_tz is not None and _scada_tz is None:
        def _tz_localize(s):
            if s is None:
                return None
            _result = s.tz_localize(
                _meteo_tz, ambiguous='infer', nonexistent='shift_forward'
            )
            # --- Faz 1.8.0.1: DST duplicate temizligi ---
            # DST 'shift_forward' 02:00 kaydini 03:00'a tasidiginda SCADA'da
            # zaten 03:00 varsa duplicate olusur. Ilkini tut.
            if _result.index.duplicated().any():
                _result = _result[~_result.index.duplicated(keep='first')]
            return _result
        scada = _dc_replace(
            scada,
            power_kw=_tz_localize(scada.power_kw),
            poa_irradiance=_tz_localize(scada.poa_irradiance),
            temp_ambient=_tz_localize(scada.temp_ambient),
            temp_module=_tz_localize(scada.temp_module),
            wind_speed=_tz_localize(scada.wind_speed),
            energy_kwh=_tz_localize(scada.energy_kwh),
        )
        notes.append(f"SCADA meteo timezone'una localize edildi: {_meteo_tz}")

    # 1. SCADA'yı ham çözünürlükte kullan (frekans-agnostik)
    # --- Faz 1.6 Adim 3.3: frequency-agnostic calibration ---
    actual_power = scada.power_kw
    scada_dt_hours = _detect_timestep_hours(actual_power.index)
    min_samples = int(100 / scada_dt_hours)  # 1h->100, 15dk->400, 5dk->1200

    n_valid = int(actual_power.notna().sum())
    if n_valid < min_samples:
        n_hours = n_valid * scada_dt_hours
        raise ValueError(
            f"Yetersiz SCADA verisi: {n_valid} örnek "
            f"({n_hours:.1f} saat, minimum 100 saat gerekli)"
        )

    # --- Faz 1.9.0: fit_azimuth vs fit_tilt XOR ---
    # Azimuth ve tilt ayni anda fit edilemez - iki degiskenli optimizasyon
    # local minimum'a takilabilir. Kullanici birini bilmeli, digerini fit et.
    if fit_azimuth and fit_tilt:
        raise ValueError(
            "fit_azimuth ve fit_tilt ayni anda kullanilamaz. "
            "Ikisinden birini secin - digerini plant spec'te dogru verin."
        )

    # 2. Meteo'yu SCADA index'ine hizala (1h meteo + 15dk SCADA gibi durumlar icin)
    historical_meteo = _align_meteo_to_scada(historical_meteo, actual_power.index)

    # --- Faz 1.8.1: azimuth fit blogu ---
    # Azimuth fit: panel yonelim varsayimini SCADA verisinden ogret.
    # OZELLIKLE eta_bos/BG fit'ten ONCE yapilir - geometri hatasi olursa
    # performans fit'i onu telafi etmeye calisir ve yanlis ogrenir.
    # Loss: sadece abs(NMBE). Sapmayi sifira cek, MAPE fit sonrasi kalabilir
    # (o profil hatasi, azimuth ile tam cozulmez).
    if fit_azimuth:
        # Kendi dataclass replace import'umuz - Faz 1.8.0 blogundaki _dc_replace
        # kosullu bir blokta tanimliydi, guvenli olmayabilir. Bagimsiz alalim.
        from dataclasses import replace as _az_replace

        _valid_mask = (actual_power.notna()) & (actual_power > threshold_kw)
        _valid_actual = actual_power[_valid_mask]

        if len(_valid_actual) < 100:
            notes.append(
                f"Azimuth fit atlandi: yetersiz gunduz verisi "
                f"({len(_valid_actual)} nokta, min 100)"
            )
        else:
            def _azimuth_loss(az: float) -> float:
                _cand_plant = _az_replace(plant, azimuth=float(az))
                _f = forecast_7day(
                    historical_meteo, _cand_plant,
                    ghi_bias_bins=ghi_bias_bins,
                    ghi_bias_corrections=ghi_bias_corrections,
                )
                _pred = _f.hourly["p_ac_kw"]
                _common = _pred.index.intersection(_valid_actual.index)
                if len(_common) == 0:
                    return 1e18
                _p = _pred.loc[_common]
                _a = _valid_actual.loc[_common]
                # --- Faz 1.8.1: loss=MAPE ---
                # MAPE - profil sekli hatasini minimize et.
                # NMBE (sapma) sonraki eta_bos fit ile zaten sifirlanir.
                # NMBE=0 olan bir egri var (birden fazla azimuth); MAPE ise
                # tek minimuma sahip - daha guvenilir hedef.
                _mape = (abs(_p - _a) / _a).mean()
                return _mape

            _az_result = minimize_scalar(
                _azimuth_loss,
                bounds=azimuth_bounds,
                method="bounded",
                options={"xatol": 1.0},  # 1° hassasiyet yeterli
            )
            if _az_result.success:
                _new_azimuth = float(_az_result.x)
                _old_azimuth = plant.azimuth
                plant = _az_replace(plant, azimuth=_new_azimuth)
                notes.append(
                    f"Azimuth fit: {_old_azimuth:.1f}° -> {_new_azimuth:.1f}° "
                    f"(MAPE={_az_result.fun*100:.2f}%, {_az_result.nfev} iterasyon)"
                )
            else:
                notes.append("Azimuth fit basarisiz: minimize_scalar convergence yok")

    # --- Faz 1.9.0: tilt fit blogu ---
    # Tilt fit: panel egim varsayimini SCADA verisinden ogret.
    # Ayni yaklasim: MAPE minimize, eta_bos'tan ONCE.
    if fit_tilt:
        from dataclasses import replace as _tilt_replace

        _valid_mask = (actual_power.notna()) & (actual_power > threshold_kw)
        _valid_actual = actual_power[_valid_mask]

        if len(_valid_actual) < 100:
            notes.append(
                f"Tilt fit atlandi: yetersiz gunduz verisi "
                f"({len(_valid_actual)} nokta, min 100)"
            )
        else:
            def _tilt_loss(tilt: float) -> float:
                _cand_plant = _tilt_replace(plant, tilt=float(tilt))
                _f = forecast_7day(
                    historical_meteo, _cand_plant,
                    ghi_bias_bins=ghi_bias_bins,
                    ghi_bias_corrections=ghi_bias_corrections,
                )
                _pred = _f.hourly["p_ac_kw"]
                _common = _pred.index.intersection(_valid_actual.index)
                if len(_common) == 0:
                    return 1e18
                _p = _pred.loc[_common]
                _a = _valid_actual.loc[_common]
                _mape = (abs(_p - _a) / _a).mean()
                return _mape

            _tilt_result = minimize_scalar(
                _tilt_loss,
                bounds=tilt_bounds,
                method="bounded",
                options={"xatol": 0.5},  # 0.5° hassasiyet
            )
            if _tilt_result.success:
                _new_tilt = float(_tilt_result.x)
                _old_tilt = plant.tilt
                plant = _tilt_replace(plant, tilt=_new_tilt)
                notes.append(
                    f"Tilt fit: {_old_tilt:.1f}° -> {_new_tilt:.1f}° "
                    f"(MAPE={_tilt_result.fun*100:.2f}%, {_tilt_result.nfev} iterasyon)"
                )
            else:
                notes.append("Tilt fit basarisiz: minimize_scalar convergence yok")

    # 2. Başlangıç tahminini hesapla (kalibrasyon öncesi)
    initial_forecast = forecast_7day(
        historical_meteo, plant,
        ghi_bias_bins=ghi_bias_bins,
        ghi_bias_corrections=ghi_bias_corrections,
    )
    predicted_power_initial = initial_forecast.hourly["p_ac_kw"]

    # 3. Doğrulama (öncesi)
    validation_before = validate(predicted_power_initial, actual_power, threshold=threshold_kw)

    # 4. η_BoS fit — sadece toplam sapmayı sıfıra çek
    fitted_eta_bos = plant.eta_bos
    if fit_eta_bos:
        # P_AC = P_DC * eta_BoS * eta_inv → toplam sapma oranı kadar düzelt
        if validation_before.total_actual > 0:
            ratio = validation_before.total_actual / validation_before.total_predicted
            fitted_eta_bos = float(np.clip(plant.eta_bos * ratio, 0.70, 0.99))
            notes.append(
                f"η_BoS düzeltmesi: {plant.eta_bos:.4f} → {fitted_eta_bos:.4f} "
                f"(oran={ratio:.4f})"
            )
        else:
            notes.append("Gerçek üretim toplamı 0, η_BoS fit atlandı")

    # 5. BG fit (bifacial)
    fitted_bg = plant.bifacial_gain_geometric
    if fit_bg and plant.is_bifacial:
        # η_BoS düzeltildi, şimdi BG için ince ayar.
        # Saatlik bazda model tahmini ile gerçek arasındaki RMSE'yi minimize et.
        def loss(bg_candidate: float) -> float:
            candidate_plant = _clone_plant(
                plant, eta_bos=fitted_eta_bos, bifacial_gain_geometric=bg_candidate
            )
            forecast = forecast_7day(
                historical_meteo, candidate_plant,
                ghi_bias_bins=ghi_bias_bins,
                ghi_bias_corrections=ghi_bias_corrections,
            )
            pred = forecast.hourly["p_ac_kw"]
            common_idx = pred.index.intersection(actual_power.index)
            if len(common_idx) == 0:
                return 1e18
            diff = pred.loc[common_idx] - actual_power.loc[common_idx]
            return float(np.mean(diff**2))

        result = minimize_scalar(
            loss, bounds=(0.05, 0.60), method="bounded", options={"xatol": 1e-4}
        )
        if result.success:
            fitted_bg = float(result.x)
            notes.append(
                f"BG fit: {plant.bifacial_gain_geometric:.4f} → {fitted_bg:.4f}"
            )
        else:
            notes.append("BG fit başarısız, başlangıç değeri korundu")

    # 6. Kalibre edilmiş plant ile yeni tahmin
    calibrated_plant = _clone_plant(
        plant, eta_bos=fitted_eta_bos, bifacial_gain_geometric=fitted_bg
    )
    final_forecast = forecast_7day(
        historical_meteo, calibrated_plant,
        ghi_bias_bins=ghi_bias_bins,
        ghi_bias_corrections=ghi_bias_corrections,
    )
    predicted_power_final = final_forecast.hourly["p_ac_kw"]
    validation_after = validate(predicted_power_final, actual_power, threshold=threshold_kw)

    # --- Faz 1.9.1: sanity checks ---
    _warnings: list[str] = []

    _mape_after = validation_after.mape_pct
    if _mape_after > 40.0:
        _warnings.append(
            f"MAPE %{_mape_after:.1f} - kalibrasyon zayif. "
            f"Muhtemelen meteo verinizde bias var (bulutlu donem?). "
            f"Farkli bir donem deneyebilirsiniz."
        )

    _eta_bos_final = calibrated_plant.eta_bos
    if _eta_bos_final > 0.98:
        _warnings.append(
            f"eta_bos={_eta_bos_final:.3f} ust sinira dayandi. Model "
            f"verinizi yakalamaya calisiyor ama fiziksel limit asildi. "
            f"Azimuth/tilt yanlis olabilir veya veri kalitesi dusuk."
        )
    elif _eta_bos_final < 0.70:
        _warnings.append(
            f"eta_bos={_eta_bos_final:.3f} alt sinira dayandi. Panelinizde "
            f"olagandisi kayip var (kirlilik, ariza, dc/ac orani?)."
        )

    _dev_after = validation_after.total_deviation_pct
    if abs(_dev_after) > 5.0:
        _warnings.append(
            f"Toplam sapma %{_dev_after:+.2f} - sifirlanamadi. "
            f"Kalibrasyon parametreleri yetersiz kaldi."
        )

    _n_samples = validation_after.n_samples
    if _n_samples < 100:
        _warnings.append(
            f"Sadece {_n_samples} gecerli saat kullanildi (min 100 onerilir). "
            f"Daha uzun bir donem verin."
        )

    # --- Faz 1.9.1: warnings return ---
    return CalibrationResult(
        plant=calibrated_plant,
        original_plant=plant,
        validation_before=validation_before,
        validation_after=validation_after,
        bg=fitted_bg,
        eta_bos=fitted_eta_bos,
        n_valid_hours=validation_after.n_samples,
        notes=notes,
        warnings=_warnings,
    )


def _clone_plant(plant: PlantSpec, **overrides) -> PlantSpec:
    """PlantSpec'in immutable benzeri kopyasını döner (dataclass replace mantığı)."""
    from dataclasses import replace
    return replace(plant, **overrides)
