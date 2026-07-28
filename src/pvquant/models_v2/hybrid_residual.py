"""
PVQuant - HybridResidualModel
=============================

Fizik + ML hibrit model: Barhdadi-Bennis fizik zincirinin üstüne
LightGBM rezidüel düzeltme katmanı.

Mantık:

.. code::

    P_final = P_physics + f_ML(features)

    where  f_ML  ≈  E[ P_actual - P_physics | saat, mevsim, POA, T_cell, kt, ... ]

Fizik modeli (BarhdadiBennisModel) üretimin ~%85-90'ını açıklar;
LightGBM yalnızca fizik modelinin *sistematik* hatalarını öğrenir:
saat-bağımlı bias, bulutlu/açık gün farkı, mevsimsel kirlenme,
Open-Meteo GHI sapmaları vb.

İki yollu yaşam döngüsü (PVModel Protocol):

  - Mod A (Pure Forecast): ML katmanı yok → saf fizik tahmini döner.
    (SCADA olmadan rezidüel öğrenilemez; model degrade olur, hata vermez.)
  - Mod B (Calibrated): calibrate() önce fizik parametrelerini fit eder
    (η_BoS, BG — mevcut calibrate_from_scada), sonra rezidüelleri
    zaman-bazlı split ile LightGBM'e öğretir.

Kritik tasarım kararları:

  1. **Zaman-bazlı split**: Eğitim/validasyon ayrımı kronolojiktir
     (ilk %80 train, son %20 validation). Rastgele split veri sızıntısı
     yaratır ve metrikleri yalancı iyileştirir.
  2. **Curtailment/arıza filtresi**: Yüksek ışınımda üretimin fizik
     tahmininin çok altında kaldığı saatler eğitimden çıkarılır; model
     "santral bazen sebepsiz düşer" örüntüsünü öğrenmemelidir.
  3. **Gece kilidi**: POA < eşik iken çıktı her zaman 0'dır; ML katmanı
     gece saatlerine hiç dokunmaz.
  4. **Fiziksel sınırlar**: Nihai tahmin [0, AC clip] aralığına kırpılır.
  5. **Olasılıksal çıktı**: confidence_intervals=True ise P10/P50/P90
     quantile regresyon modelleri de eğitilir/kullanılır.

Bağımlılık: lightgbm (opsiyonel — yüklü değilse import anında değil,
kalibrasyon anında açıklayıcı hata verilir).

Kullanım:

    >>> from pvquant.models_v2.hybrid_residual import HybridResidualModel
    >>> model = HybridResidualModel(plant)
    >>> params = model.calibrate(historical)      # fizik fit + LGBM eğitimi
    >>> result = model.predict(forecast_input, config)
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from .contracts import (
    PlantProfile,
    ForecastInput,
    OperationConfig,
    HistoricalData,
    ForecastResult,
    ForecastSummary,
    ConfidenceIntervals,
    CalibrationParams,
    ModelMetadata,
)
from .registry import ModelRegistry
from .barhdadi_bennis import BarhdadiBennisModel


# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------

#: Gece/alacakaranlık eşiği — bu POA'nın (W/m²) altında çıktı daima 0.
NIGHT_POA_THRESHOLD_W = 5.0

#: Curtailment filtresi: POA bu eşiğin üstündeyken...
CURTAILMENT_POA_MIN_W = 300.0
#: ...gerçek üretim fizik tahmininin bu oranının altındaysa saat elenir.
CURTAILMENT_RATIO = 0.15

#: Kronolojik train/validation oranı.
TRAIN_FRACTION = 0.80

#: LGBM eğitiminde kullanılan feature kolonları (sıra önemli).
FEATURE_COLUMNS = [
    "p_physics_kw",     # fizik modelinin tahmini — en güçlü feature
    "poa_global",       # W/m²
    "t_cell",           # °C
    "ghi",              # W/m²
    "kt",               # açıklık endeksi (0-1.2)
    "zenith",           # derece
    "azimuth_sin",      # güneş azimutu (döngüsel)
    "azimuth_cos",
    "hour_sin",         # yerel saat (döngüsel)
    "hour_cos",
    "doy_sin",          # yıl günü (döngüsel — mevsimsellik)
    "doy_cos",
    "wind_speed",       # m/s (10m)
]


class LightGBMNotInstalledError(RuntimeError):
    """lightgbm paketi eksikse kalibrasyonda fırlatılır."""


def _import_lgbm():
    try:
        import lightgbm as lgb
        return lgb
    except ImportError as exc:  # pragma: no cover
        raise LightGBMNotInstalledError(
            "HybridResidualModel kalibrasyonu için lightgbm gerekli. "
            "Kurulum: pip install lightgbm"
        ) from exc


# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------

def build_features(
    physics_hourly: pd.DataFrame,
    latitude: float,
    longitude: float,
    altitude_m: float,
    local_tz: str,
) -> pd.DataFrame:
    """Fizik pipeline'ının saatlik çıktısından ML feature matrisi üretir.

    Hem kalibrasyonda (geçmiş) hem tahminde (gelecek) aynı fonksiyon
    kullanılır — train/serve tutarlılığı böyle garanti edilir.

    Args:
        physics_hourly: forecast_7day() çıktısındaki `hourly` DataFrame.
            Gerekli kolonlar: ghi, poa_global, temp_cell, wind_speed_10m,
            p_ac_kw. Index: tz-aware DatetimeIndex (UTC veya yerel).
        latitude, longitude, altitude_m: Saha konumu (solar pozisyon için).
        local_tz: IANA saat dilimi — saat feature'ı yerel saatte anlamlıdır
            (öğle piki her mevsim ~12-13'te olmalı).

    Returns:
        FEATURE_COLUMNS kolonlarını içeren DataFrame, physics_hourly ile
        aynı index'te.
    """
    from pvquant.models import irradiance

    times = physics_hourly.index
    solpos = irradiance.solar_position(
        times=times, latitude=latitude, longitude=longitude, altitude=altitude_m
    )
    dni_extra = __import__("pvlib").irradiance.get_extra_radiation(times)

    # Açıklık endeksi kt = GHI / (I0 · cos(zenith)); gece → 0.
    cos_z = np.cos(np.radians(solpos["zenith"])).clip(lower=0.0)
    ghi_clear_top = (dni_extra * cos_z).clip(lower=1.0)  # bölme güvenliği
    kt = (physics_hourly["ghi"] / ghi_clear_top).clip(0.0, 1.2)
    kt = kt.where(cos_z > 0.01, 0.0)

    # Yerel saat (döngüsel kodlama — 23 ile 0 komşudur)
    local_times = times.tz_convert(local_tz) if times.tz is not None else times
    hour = local_times.hour + local_times.minute / 60.0
    doy = local_times.dayofyear

    az_rad = np.radians(solpos["azimuth"])

    features = pd.DataFrame(
        {
            "p_physics_kw": physics_hourly["p_ac_kw"].astype(float),
            "poa_global": physics_hourly["poa_global"].astype(float),
            "t_cell": physics_hourly["temp_cell"].astype(float),
            "ghi": physics_hourly["ghi"].astype(float),
            "kt": kt.astype(float),
            "zenith": solpos["zenith"].astype(float),
            "azimuth_sin": np.sin(az_rad),
            "azimuth_cos": np.cos(az_rad),
            "hour_sin": np.sin(2 * np.pi * hour / 24.0),
            "hour_cos": np.cos(2 * np.pi * hour / 24.0),
            "doy_sin": np.sin(2 * np.pi * doy / 365.25),
            "doy_cos": np.cos(2 * np.pi * doy / 365.25),
            "wind_speed": physics_hourly["wind_speed_10m"].astype(float),
        },
        index=times,
    )
    return features[FEATURE_COLUMNS]


def filter_training_hours(
    features: pd.DataFrame,
    actual_kw: pd.Series,
    p_physics_kw: pd.Series,
) -> pd.Index:
    """Eğitime girecek 'temiz' saatlerin index'ini döner.

    Elenenler:
      - NaN içeren satırlar,
      - gece saatleri (POA < NIGHT_POA_THRESHOLD_W),
      - muhtemel curtailment/arıza: POA yüksekken üretim fizik tahmininin
        CURTAILMENT_RATIO katından az.

    Not: Bu kaba bir sezgisel filtredir. Şebeke operatöründen gelen resmi
    kısıtlama kayıtları varsa onları kullanmak her zaman daha doğrudur.
    """
    df = features.copy()
    df["actual"] = actual_kw
    df["p_phys"] = p_physics_kw
    df = df.dropna()

    daylight = df["poa_global"] >= NIGHT_POA_THRESHOLD_W
    curtailed = (df["poa_global"] > CURTAILMENT_POA_MIN_W) & (
        df["actual"] < CURTAILMENT_RATIO * df["p_phys"].clip(lower=0.001)
    )
    keep = daylight & ~curtailed
    return df.index[keep]


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

class HybridResidualModel:
    """Fizik (Barhdadi-Bennis) + LightGBM rezidüel hibrit modeli.

    PVModel Protocol uyumlu. Fizik katmanı olarak içeride bir
    BarhdadiBennisModel sarmalar; ML katmanı yalnızca rezidüeli öğrenir.
    """

    MODEL_NAME = "hybrid_residual"
    MODEL_VERSION = "0.1.0"

    #: LightGBM hiperparametreleri — saatlik PV rezidüeli için makul,
    #: agresif olmayan varsayılanlar. Aşırı öğrenmeye karşı sığ ağaçlar.
    LGBM_PARAMS: dict = {
        "objective": "regression",
        "n_estimators": 600,
        "learning_rate": 0.03,
        "num_leaves": 31,
        "max_depth": 6,
        "min_child_samples": 30,
        "subsample": 0.9,
        "subsample_freq": 1,
        "colsample_bytree": 0.9,
        "reg_lambda": 1.0,
        "verbose": -1,
    }

    def __init__(self, plant: PlantProfile) -> None:
        # Uygunluk kontrolü ve fizik katmanı — BarhdadiBennisModel'e devredilir
        # (mono/bifacial dışını zaten reddeder).
        self.plant_profile = plant
        self._base = BarhdadiBennisModel(plant)
        self._booster = None          # nokta tahmin modeli (L2)
        self._quantile_boosters: dict[float, object] = {}  # {0.1: m, 0.5: m, 0.9: m}
        self._calibrated = False
        self._last_calibration_date: Optional[datetime] = None
        self._training_report: dict[str, float] = {}

    # ------------------------------------------------------------------
    # Protocol: predict
    # ------------------------------------------------------------------

    def predict(
        self,
        forecast_input: ForecastInput,
        config: OperationConfig,
    ) -> ForecastResult:
        """Üretim tahmini. Mod'a göre saf fizik veya fizik+ML döner.

        operation_mode="calibrated" istendiğinde hem fizik parametreleri
        hem ML katmanı hazır olmalıdır; aksi halde RuntimeError.
        operation_mode="pure_forecast" ise ML katmanı bilinçli olarak
        atlanır (fizik tahmini, literatür katsayılarıyla).
        """
        if config.operation_mode == "calibrated" and not self._calibrated:
            raise RuntimeError(
                "operation_mode='calibrated' istendi ama HybridResidualModel "
                "henüz calibrate() ile öğretilmedi."
            )

        # 1) Fizik tahmini (base modelin tüm doğrulama/bias mantığı dahil)
        base_result = self._base.predict(forecast_input, config)

        # Pure forecast modunda ML katmanı yok → base sonucu yeniden etiketle
        if config.operation_mode == "pure_forecast" or self._booster is None:
            base_result = base_result.model_copy(
                update={
                    "model_name": self.MODEL_NAME,
                    "model_version": self.MODEL_VERSION,
                }
            )
            return base_result

        # 2) Fizik pipeline'ının ham saatlik çıktısını feature'a çevirmek için
        #    base timeseries'i yeniden indexle. (base.predict timeseries'i
        #    timestamp_utc kolonu ile döner.)
        ts = base_result.timeseries.set_index(
            pd.to_datetime(base_result.timeseries["timestamp_utc"])
        )
        # build_features'ın beklediği kolon adlarına eşle. ghi/rüzgar
        # forecast_input'tan gelir (fizik timeseries'inde yoklar).
        meteo_df = forecast_input.data.copy()
        if "timestamp" in meteo_df.columns:
            meteo_df = meteo_df.set_index(pd.to_datetime(meteo_df["timestamp"]))
        meteo_df = meteo_df.reindex(ts.index)

        physics_hourly = pd.DataFrame(
            {
                "ghi": meteo_df["ghi"].astype(float),
                "poa_global": ts["poa_global"].astype(float),
                "temp_cell": ts["t_cell"].astype(float),
                "wind_speed_10m": meteo_df["wind_speed"].astype(float),
                "p_ac_kw": ts["ac_power_kw"].astype(float),
            },
            index=ts.index,
        )

        features = build_features(
            physics_hourly,
            latitude=self.plant_profile.location.latitude,
            longitude=self.plant_profile.location.longitude,
            altitude_m=self.plant_profile.location.elevation_m,
            local_tz=self.plant_profile.location.timezone,
        )

        # 3) Rezidüel tahmini + fiziksel sınırlar
        residual_pred = pd.Series(
            self._booster.predict(features[FEATURE_COLUMNS]),
            index=features.index,
        )
        p_final = self._apply_constraints(
            physics_hourly["p_ac_kw"] + residual_pred, physics_hourly["poa_global"]
        )

        # 4) Timeseries'i güncelle (fizik kolonları korunur, AC güncellenir)
        out_ts = base_result.timeseries.copy()
        out_ts["ac_power_physics_kw"] = out_ts["ac_power_kw"]
        out_ts["ac_power_kw"] = p_final.values
        out_ts["ml_residual_kw"] = residual_pred.values

        # 5) Özet ve (istenirse) güven aralıkları
        energy_total = float(p_final.sum())
        summary = ForecastSummary(
            total_energy_kwh=energy_total,
            peak_power_kw=float(p_final.max()),
            average_capacity_factor=(
                energy_total
                / (self.plant_profile.dc_capacity_kwp * max(len(p_final), 1))
            ),
            forecast_window_start=base_result.summary.forecast_window_start,
            forecast_window_end=base_result.summary.forecast_window_end,
        )

        confidence = None
        if config.confidence_intervals and self._quantile_boosters:
            totals = {}
            for q, booster in self._quantile_boosters.items():
                res_q = pd.Series(
                    booster.predict(features[FEATURE_COLUMNS]), index=features.index
                )
                p_q = self._apply_constraints(
                    physics_hourly["p_ac_kw"] + res_q, physics_hourly["poa_global"]
                )
                totals[q] = float(p_q.sum())
            confidence = ConfidenceIntervals(
                p10_total_kwh=totals.get(0.1, energy_total),
                p50_total_kwh=totals.get(0.5, energy_total),
                p90_total_kwh=totals.get(0.9, energy_total),
                method="quantile_regression",
            )

        debug = None
        if config.include_debug_info:
            debug = dict(base_result.debug_info or {})
            debug.update(
                {
                    "ml_layer": "lightgbm_residual",
                    "ml_features": FEATURE_COLUMNS,
                    "training_report": self._training_report,
                }
            )

        return ForecastResult(
            plant_id=self.plant_profile.plant_id,
            model_name=self.MODEL_NAME,
            model_version=self.MODEL_VERSION,
            operation_mode=config.operation_mode,
            weather_source=forecast_input.source,
            timeseries=out_ts,
            summary=summary,
            debug_info=debug,
            confidence=confidence,
        )

    # ------------------------------------------------------------------
    # Protocol: calibrate
    # ------------------------------------------------------------------

    def calibrate(self, historical: HistoricalData) -> CalibrationParams:
        """İki aşamalı kalibrasyon: (1) fizik fit, (2) rezidüel LGBM.

        Aşama 1 mevcut calibrate_from_scada akışını (η_BoS, BG, POA-bin
        bias) BarhdadiBennisModel üzerinden aynen çalıştırır — fizik
        modeli önce kendi elinden geleni yapmalı ki ML'e kalan rezidüel
        küçük ve öğrenilebilir olsun.

        Aşama 2, kalibre fizik tahmini ile gerçek üretim arasındaki farkı
        kronolojik split ile LightGBM'e öğretir ve holdout metriklerini
        (fizik-vs-hibrit) rapora yazar.

        HistoricalData.data beklenen kolonlar:
          - timestamp, power_kw (zorunlu)
          - ghi, t_air, wind_speed (varsa Open-Meteo çağrısı atlanır —
            saha meteo istasyonu verisi tercih sebebidir)
          - poa_global, t_module (opsiyonel; fizik bias fit'inde kullanılır)

        14 Temmuz 2026: poa_global kolonu meteo_df'e taşınır ki holdout
        fizik tahmini de olculen POA'yı kullansın (BarhdadiBennisModel.predict
        forecast_input.data içindeki poa_global'ı forecast_7day'e geçirir).
        """
        lgb = _import_lgbm()
        from pvquant.io.meteo import MeteoData
        from pvquant.io.scada import SCADAData
        from pvquant.pipeline.calibration import calibrate_from_scada

        df = historical.data.copy()
        if "timestamp" in df.columns:
            df = df.set_index(pd.to_datetime(df["timestamp"]))
        df = df.sort_index()
        if "power_kw" not in df.columns:
            raise ValueError("HistoricalData.data 'power_kw' kolonu içermelidir")

        # ---------- Meteo: sahadan mı, Open-Meteo'dan mı? ----------
        # SCADA'da ghi/t_air/wind_speed varsa saha ölçümü tercih edilir:
        # hem daha doğrudur hem dış API bağımlılığını kaldırır.
        meteo_cols = {"ghi", "t_air", "wind_speed"}
        loc = self.plant_profile.location
        if meteo_cols.issubset(df.columns):
            hist_meteo = MeteoData(
                ghi=df["ghi"].astype(float),
                temp_air=df["t_air"].astype(float),
                wind_speed_10m=df["wind_speed"].astype(float),
                relative_humidity=None,
                cloud_cover=None,
                latitude=loc.latitude,
                longitude=loc.longitude,
                timezone=loc.timezone,
            )
            # 14 Temmuz: poa_global SCADA'da varsa meteo_df'e taşı ki
            # fizik holdout tahmini de olculen POA'yı kullansın.
            _cols = list(meteo_cols)
            if "poa_global" in df.columns:
                _cols.append("poa_global")
            meteo_df = df[_cols].copy()
            meteo_source = "scada"
        else:
            from pvquant.io.meteo import OpenMeteoClient

            client = OpenMeteoClient()
            hist_meteo = client.get_historical(
                latitude=loc.latitude,
                longitude=loc.longitude,
                start_date=df.index.min().strftime("%Y-%m-%d"),
                end_date=df.index.max().strftime("%Y-%m-%d"),
                timezone=loc.timezone,
            )
            meteo_df = pd.DataFrame(
                {
                    "ghi": hist_meteo.ghi,
                    "t_air": hist_meteo.temp_air,
                    "wind_speed": hist_meteo.wind_speed_10m,
                }
            )
            # 14 Temmuz: Open-Meteo dalında da olculen POA varsa SCADA
            # CSV'sinden ekle (hist_meteo'da yok, orasi Open-Meteo).
            if "poa_global" in df.columns:
                meteo_df["poa_global"] = df["poa_global"].reindex(meteo_df.index)
            meteo_source = "open_meteo"

        # ---------- Aşama 1: fizik kalibrasyonu ----------
        # Base modelin calibrate()'i her zaman Open-Meteo'ya gider; burada
        # aynı akışı (POA bias fit + η_BoS/BG fit) elimizdeki meteo ile
        # doğrudan çalıştırıyoruz — tek veri kaynağı, tek fetch.
        if "poa_global" in df.columns:
            bias_bins, bias_corrections = self._base._fit_ghi_bias(
                scada_poa=df["poa_global"].astype(float),
                meteo=hist_meteo,
            )
            self.plant_profile.ghi_bias_bins = bias_bins
            self.plant_profile.ghi_bias_corrections = bias_corrections
            self._base.plant_profile.ghi_bias_bins = bias_bins
            self._base.plant_profile.ghi_bias_corrections = bias_corrections

        scada_obj = SCADAData(
            power_kw=df["power_kw"].astype(float),
            energy_kwh=None,
            poa_irradiance=(
                df["poa_global"].astype(float) if "poa_global" in df.columns else None
            ),
            temp_ambient=(
                df["t_air"].astype(float) if "t_air" in df.columns else None
            ),
            temp_module=(
                df["t_module"].astype(float) if "t_module" in df.columns else None
            ),
            wind_speed=(
                df["wind_speed"].astype(float) if "wind_speed" in df.columns else None
            ),
            plant_name=self.plant_profile.name,
            timestep_minutes=60,
        )
        cal_result = calibrate_from_scada(
            scada=scada_obj,
            historical_meteo=hist_meteo,
            plant=self._base._plant_spec,
            fit_bg=True,
            fit_eta_bos=True,
            ghi_bias_bins=self.plant_profile.ghi_bias_bins,
            ghi_bias_corrections=self.plant_profile.ghi_bias_corrections,
        )
        self._base._plant_spec = cal_result.plant
        self._base._calibrated = True
        base_params = CalibrationParams(
            plant_id=self.plant_profile.plant_id,
            model_name=self.MODEL_NAME,
            fitted_at=datetime.now(timezone.utc),
            valid_hours_used=int(cal_result.n_valid_hours),
            parameters={
                "bifacial_gain_geometric": float(cal_result.bg),
                "eta_bos": float(cal_result.eta_bos),
                "albedo": float(cal_result.plant.albedo),
                "gamma_pdc": float(cal_result.plant.effective_gamma),
            },
            quality_metrics={
                "mape_pct_physics_before": float(
                    cal_result.validation_before.mape_pct
                ),
                "mape_pct_physics_after": float(
                    cal_result.validation_after.mape_pct
                ),
                "total_deviation_pct_after": float(
                    cal_result.validation_after.total_deviation_pct
                ),
            },
        )

        # ---------- Kalibre fizik tahmini (geçmiş dönem) ----------
        forecast_input = ForecastInput(
            source="scada" if meteo_source == "scada" else "open_meteo",
            resolution_minutes=60,
            data=meteo_df.reset_index().rename(columns={"index": "timestamp"}),
        )
        physics_result = self._base.predict(
            forecast_input,
            OperationConfig(operation_mode="calibrated", include_debug_info=False),
        )
        p_ts = physics_result.timeseries.set_index(
            pd.to_datetime(physics_result.timeseries["timestamp_utc"])
        )

        physics_hourly = pd.DataFrame(
            {
                "ghi": meteo_df["ghi"].reindex(p_ts.index).astype(float),
                "poa_global": p_ts["poa_global"].astype(float),
                "temp_cell": p_ts["t_cell"].astype(float),
                "wind_speed_10m": meteo_df["wind_speed"].reindex(p_ts.index).astype(float),
                "p_ac_kw": p_ts["ac_power_kw"].astype(float),
            },
            index=p_ts.index,
        )

        # ---------- Feature + hedef ----------
        features = build_features(
            physics_hourly,
            latitude=self.plant_profile.location.latitude,
            longitude=self.plant_profile.location.longitude,
            altitude_m=self.plant_profile.location.elevation_m,
            local_tz=self.plant_profile.location.timezone,
        )
        actual = df["power_kw"].astype(float).reindex(features.index)
        residual = actual - physics_hourly["p_ac_kw"]

        clean_idx = filter_training_hours(
            features, actual, physics_hourly["p_ac_kw"]
        )
        X = features.loc[clean_idx, FEATURE_COLUMNS]
        y = residual.loc[clean_idx]

        min_hours = 500
        if len(X) < min_hours:
            raise ValueError(
                f"Rezidüel eğitimi için yetersiz temiz gündüz saati: "
                f"{len(X)} (minimum {min_hours}). Daha uzun SCADA dönemi gerekli."
            )

        # ---------- Kronolojik split ----------
        split = int(len(X) * TRAIN_FRACTION)
        X_tr, X_va = X.iloc[:split], X.iloc[split:]
        y_tr, y_va = y.iloc[:split], y.iloc[split:]

        # ---------- Nokta modeli (L2) ----------
        self._booster = lgb.LGBMRegressor(**self.LGBM_PARAMS)
        self._booster.fit(
            X_tr,
            y_tr,
            eval_set=[(X_va, y_va)],
            callbacks=[lgb.early_stopping(50, verbose=False)],
        )

        # ---------- Quantile modelleri (P10/P50/P90) ----------
        self._quantile_boosters = {}
        for q in (0.1, 0.5, 0.9):
            q_params = dict(self.LGBM_PARAMS)
            q_params.update({"objective": "quantile", "alpha": q})
            booster_q = lgb.LGBMRegressor(**q_params)
            booster_q.fit(
                X_tr,
                y_tr,
                eval_set=[(X_va, y_va)],
                callbacks=[lgb.early_stopping(50, verbose=False)],
            )
            self._quantile_boosters[q] = booster_q

        # ---------- Dürüst holdout raporu: fizik vs hibrit ----------
        p_phys_va = physics_hourly["p_ac_kw"].loc[X_va.index]
        actual_va = actual.loc[X_va.index]
        p_hyb_va = self._apply_constraints(
            p_phys_va + pd.Series(self._booster.predict(X_va), index=X_va.index),
            physics_hourly["poa_global"].loc[X_va.index],
        )

        def _mape(pred: pd.Series, act: pd.Series) -> float:
            mask = act > 1.0
            if mask.sum() == 0:
                return float("nan")
            return float(
                np.mean(np.abs(pred[mask] - act[mask]) / act[mask]) * 100
            )

        def _rmse(pred: pd.Series, act: pd.Series) -> float:
            return float(np.sqrt(np.mean((pred - act) ** 2)))

        def _wmape(pred: pd.Series, act: pd.Series) -> float:
            # v2.51-B: agirlikli MAPE = sum|hata|/sum(gercek); maskesiz —
            # tan saatleri dogal agirligiyla dahil, payda sismesi yok.
            s = float(act.sum())
            if s <= 0:
                return float("nan")
            return float(np.abs(pred - act).sum() / s * 100)

        report = {
            "holdout_hours": float(len(X_va)),
            "train_hours": float(len(X_tr)),
            "mape_pct_physics_holdout": _mape(p_phys_va, actual_va),
            "mape_pct_hybrid_holdout": _mape(p_hyb_va, actual_va),
            "wmape_pct_physics_holdout": _wmape(p_phys_va, actual_va),
            "wmape_pct_hybrid_holdout": _wmape(p_hyb_va, actual_va),
            "rmse_kw_physics_holdout": _rmse(p_phys_va, actual_va),
            "rmse_kw_hybrid_holdout": _rmse(p_hyb_va, actual_va),
            "best_iteration": float(self._booster.best_iteration_ or 0),
        }
        report["mape_improvement_pct"] = (
            report["mape_pct_physics_holdout"] - report["mape_pct_hybrid_holdout"]
        )
        self._training_report = report

        self._calibrated = True
        self._last_calibration_date = datetime.now(timezone.utc)

        # Fizik parametreleri + ML raporu tek CalibrationParams'ta
        quality = dict(base_params.quality_metrics)
        quality.update(report)

        return CalibrationParams(
            plant_id=self.plant_profile.plant_id,
            model_name=self.MODEL_NAME,
            fitted_at=self._last_calibration_date,
            valid_hours_used=int(len(X)),
            parameters=dict(base_params.parameters),
            quality_metrics=quality,
        )

    # ------------------------------------------------------------------
    # Protocol: get_metadata
    # ------------------------------------------------------------------

    def get_metadata(self) -> ModelMetadata:
        base_meta = self._base.get_metadata()
        return ModelMetadata(
            model_name=self.MODEL_NAME,
            model_version=self.MODEL_VERSION,
            description=(
                "Hibrit model: Barhdadi-Bennis fizik zinciri + LightGBM "
                "rezidüel düzeltme. Fizik parametreleri calibrate_from_scada "
                "ile, ML katmanı kronolojik split + curtailment filtresi ile "
                "eğitilir. P10/P50/P90 quantile çıktısı destekler."
            ),
            suitable_for=["bifacial", "mono"],
            calibrated=self._calibrated,
            last_calibration_date=self._last_calibration_date,
            current_parameters=base_meta.current_parameters,
        )

    # ------------------------------------------------------------------
    # Kalıcılık (Protocol dışı yardımcılar)
    # ------------------------------------------------------------------

    def save_ml_layer(self, directory: str | Path) -> None:
        """Eğitilmiş LGBM modellerini diske yazar (joblib)."""
        import joblib

        d = Path(directory)
        d.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "booster": self._booster,
                "quantile_boosters": self._quantile_boosters,
                "training_report": self._training_report,
                "feature_columns": FEATURE_COLUMNS,
                "model_version": self.MODEL_VERSION,
            },
            d / f"{self.plant_profile.plant_id}_{self.MODEL_NAME}.joblib",
        )

    def load_ml_layer(self, directory: str | Path) -> bool:
        """Diskten ML katmanını yükler. Bulunduysa True döner.

        Dikkat: Fizik parametreleri ayrı saklanır (JsonCalibrationStorage);
        bu yalnızca ML katmanını yükler. Fizik parametreleri de yüklenmeden
        'calibrated' modda tutarlı tahmin alınamaz.
        """
        import joblib

        path = (
            Path(directory)
            / f"{self.plant_profile.plant_id}_{self.MODEL_NAME}.joblib"
        )
        if not path.exists():
            return False
        payload = joblib.load(path)
        if payload.get("feature_columns") != FEATURE_COLUMNS:
            raise ValueError(
                "Kaydedilmiş model farklı bir feature setiyle eğitilmiş; "
                "yeniden kalibrasyon gerekli."
            )
        self._booster = payload["booster"]
        self._quantile_boosters = payload["quantile_boosters"]
        self._training_report = payload.get("training_report", {})
        return True

    # ------------------------------------------------------------------
    # İç yardımcılar
    # ------------------------------------------------------------------

    def _apply_constraints(
        self, p_kw: pd.Series, poa_global: pd.Series
    ) -> pd.Series:
        """Fiziksel sınırları uygular: gece=0, alt=0, üst=AC clip."""
        clip_kw = self._base._plant_spec.p_ac_clip_kw
        p = p_kw.clip(lower=0.0)
        if clip_kw is not None:
            p = p.clip(upper=float(clip_kw))
        return p.where(poa_global >= NIGHT_POA_THRESHOLD_W, 0.0)


ModelRegistry.register(HybridResidualModel.MODEL_NAME, HybridResidualModel)