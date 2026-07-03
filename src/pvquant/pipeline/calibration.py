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

    @property
    def mape_improvement_pct(self) -> float:
        """Kalibrasyon sonrası MAPE iyileşmesi (mutlak puan)."""
        return self.validation_before.mape_pct - self.validation_after.mape_pct

    def __str__(self) -> str:
        return (
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


def calibrate_from_scada(
    scada: SCADAData,
    historical_meteo: MeteoData,
    plant: PlantSpec,
    fit_bg: bool = True,
    fit_eta_bos: bool = True,
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

    # 2. Meteo'yu SCADA index'ine hizala (1h meteo + 15dk SCADA gibi durumlar icin)
    historical_meteo = _align_meteo_to_scada(historical_meteo, actual_power.index)

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

    return CalibrationResult(
        plant=calibrated_plant,
        original_plant=plant,
        validation_before=validation_before,
        validation_after=validation_after,
        bg=fitted_bg,
        eta_bos=fitted_eta_bos,
        n_valid_hours=validation_after.n_samples,
        notes=notes,
    )


def _clone_plant(plant: PlantSpec, **overrides) -> PlantSpec:
    """PlantSpec'in immutable benzeri kopyasını döner (dataclass replace mantığı)."""
    from dataclasses import replace
    return replace(plant, **overrides)
