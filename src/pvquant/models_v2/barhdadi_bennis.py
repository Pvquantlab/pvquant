"""
PVQuant - BarhdadiBennisModel
=============================

Bifacial PV santralleri için Barhdadi-Bennis tabanlı model.
PVModel Protocol implementasyonu.

İki yollu yaşam döngüsü:
  - Mod A (Pure Forecast): Defaults yüklenir, calibrate atlanır
  - Mod B (Calibrated): SCADA ile katsayılar öğrenilir

İkisinde de predict() pipeline.forecast.forecast_7day()'i çağırır,
sadece kullandığı katsayılar farklıdır.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import pandas as pd

from .contracts import (
    PlantProfile,
    ForecastInput,
    OperationConfig,
    HistoricalData,
    ForecastResult,
    ForecastSummary,
    CalibrationParams,
    ModelMetadata,
)
from .registry import ModelRegistry

from pvquant.pipeline.forecast import PlantSpec


class BarhdadiBennisModel:
    """Barhdadi-Bennis bifacial PV modeli (PVModel Protocol uyumlu)."""

    MODEL_NAME = "barhdadi_bennis"
    MODEL_VERSION = "1.0.0"

    def __init__(self, plant: PlantProfile) -> None:
        if plant.panel.technology not in ("bifacial", "mono"):
            raise ValueError(
                f"BarhdadiBennisModel '{plant.panel.technology}' tipini desteklemez. "
                f"Desteklenen: bifacial, mono"
            )
        self.plant_profile = plant
        self._plant_spec = self._to_plant_spec(plant)
        self._calibrated = False
        self._last_calibration_date: Optional[datetime] = None

    def _to_plant_spec(self, plant: PlantProfile) -> PlantSpec:
        gamma_per_c = plant.panel.temperature_coefficient_gamma / 100.0
        return PlantSpec(
            p_nom_kwp=plant.dc_capacity_kwp,
            latitude=plant.location.latitude,
            longitude=plant.location.longitude,
            tilt=plant.mounting.tilt_degrees,
            azimuth=plant.mounting.azimuth_degrees,
            module_tech="mono_si",
            gamma_pdc=gamma_per_c,
            noct=plant.panel.noct_celsius,
            bifacial_factor=plant.panel.bifaciality_factor or 0.0,
            bifacial_gain_geometric=plant.initial_bifacial_gain,
            albedo=plant.albedo,
            eta_bos=plant.initial_eta_bos,
            eta_inv=plant.inverter.efficiency,
            p_ac_clip_kw=(
                plant.inverter.clipping_kw
                if plant.inverter.clipping_kw is not None
                else plant.inverter.count * plant.inverter.ac_capacity_kw
            ),
            altitude_m=plant.location.elevation_m,
            module_height_m=plant.mounting.height_above_ground_m or 2.0,
            thermal_model="faiman",
            power_model="barhdadi_bennis",
        )

    def _fit_ghi_bias(
        self,
        scada_poa,
        meteo,
    ):
        """SCADA POA ile Open-Meteo POA arasindaki bias icin 11-bin lookup fit eder.

        Open-Meteo GHI'den Erbs+Perez ile POA hesaplar, SCADA POA ile
        karsilastirir, her quantile bin icin carpan ogrenir.

        Returns:
            (bin_centers, corrections) - her ikisi liste.
        """
        import numpy as np
        from pvquant.models import irradiance

        times = meteo.ghi.index
        if not isinstance(times, pd.DatetimeIndex):
            times = pd.to_datetime(times)

        solpos = irradiance.solar_position(
            times=times,
            latitude=meteo.latitude,
            longitude=meteo.longitude,
            altitude=self._plant_spec.altitude_m,
        )
        decomposed = irradiance.decompose_ghi_erbs(
            ghi=meteo.ghi,
            solar_zenith=solpos["zenith"],
            times=times,
        )
        dni_extra, airmass = irradiance.extra_radiation_and_airmass(
            times, solpos["zenith"]
        )
        poa_om = irradiance.transpose_perez(
            surface_tilt=self._plant_spec.tilt,
            surface_azimuth=self._plant_spec.azimuth,
            solar_zenith=solpos["zenith"],
            solar_azimuth=solpos["azimuth"],
            dni=decomposed["dni"],
            ghi=decomposed["ghi"],
            dhi=decomposed["dhi"],
            dni_extra=dni_extra,
            airmass=airmass,
            albedo=self._plant_spec.albedo,
        )

        df = pd.DataFrame({
            "scada_poa": scada_poa,
            "om_poa": poa_om.global_,
        }).dropna()
        df = df[(df["scada_poa"] > 50) & (df["om_poa"] > 50)]

        if len(df) < 100:
            raise ValueError(
                f"Bias fit icin yetersiz veri: {len(df)} saat (min 100)"
            )

        n_bins = 11
        quantiles = np.linspace(0, 1, n_bins + 1)
        bin_edges = df["om_poa"].quantile(quantiles).values
        bin_centers = []
        corrections = []
        for i in range(n_bins):
            lo, hi = bin_edges[i], bin_edges[i + 1]
            if i < n_bins - 1:
                mask = (df["om_poa"] >= lo) & (df["om_poa"] < hi)
            else:
                mask = (df["om_poa"] >= lo) & (df["om_poa"] <= hi)
            if mask.sum() == 0:
                continue
            center = float(df.loc[mask, "om_poa"].mean())
            ratio = float(
                df.loc[mask, "scada_poa"].sum() / df.loc[mask, "om_poa"].sum()
            )
            bin_centers.append(center)
            corrections.append(ratio)

        return bin_centers, corrections

    def predict(
        self,
        forecast_input: ForecastInput,
        config: OperationConfig,
    ) -> ForecastResult:
        from pvquant.io.meteo import MeteoData
        from pvquant.pipeline.forecast import forecast_7day

        if config.operation_mode == "calibrated" and not self._calibrated:
            raise RuntimeError(
                "operation_mode='calibrated' istendi ama model henüz "
                "calibrate() ile öğretilmedi."
            )

        df = forecast_input.data.copy()
        if "timestamp" in df.columns:
            df = df.set_index(pd.to_datetime(df["timestamp"]))

        required = {"ghi", "t_air", "wind_speed"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(
                f"ForecastInput.data'da eksik kolon: {missing}. "
                f"Gerekli: {required}"
            )

        meteo = MeteoData(
            ghi=df["ghi"].astype(float),
            temp_air=df["t_air"].astype(float),
            wind_speed_10m=df["wind_speed"].astype(float),
            relative_humidity=df.get("relative_humidity"),
            cloud_cover=df.get("cloud_cover"),
            latitude=self.plant_profile.location.latitude,
            longitude=self.plant_profile.location.longitude,
            timezone=self.plant_profile.location.timezone,
        )

        pipeline_result = forecast_7day(
            meteo,
            self._plant_spec,
            ghi_bias_bins=self.plant_profile.ghi_bias_bins,
            ghi_bias_corrections=self.plant_profile.ghi_bias_corrections,
        )

        timeseries = pd.DataFrame(
            {
                "timestamp_utc": pipeline_result.hourly.index,
                "poa_global": pipeline_result.hourly["poa_global"].values,
                "t_cell": pipeline_result.hourly["temp_cell"].values,
                "dc_power_kw": pipeline_result.hourly["p_dc_kw"].values,
                "ac_power_kw": pipeline_result.hourly["p_ac_kw"].values,
            }
        )

        summary = ForecastSummary(
            total_energy_kwh=float(pipeline_result.total_kwh),
            peak_power_kw=float(pipeline_result.peak_power_kw),
            average_capacity_factor=float(pipeline_result.capacity_factor),
            forecast_window_start=pipeline_result.hourly.index[0].to_pydatetime(),
            forecast_window_end=pipeline_result.hourly.index[-1].to_pydatetime(),
        )

        debug = pipeline_result.meta if config.include_debug_info else None

        return ForecastResult(
            plant_id=self.plant_profile.plant_id,
            model_name=self.MODEL_NAME,
            model_version=self.MODEL_VERSION,
            operation_mode=config.operation_mode,
            weather_source=forecast_input.source,
            timeseries=timeseries,
            summary=summary,
            debug_info=debug,
        )

    def calibrate(self, historical: HistoricalData) -> CalibrationParams:
        from pvquant.io.meteo import OpenMeteoClient
        from pvquant.io.scada import SCADAData
        from pvquant.pipeline.calibration import calibrate_from_scada

        df = historical.data.copy()
        if "timestamp" in df.columns:
            df = df.set_index(pd.to_datetime(df["timestamp"]))

        if "power_kw" not in df.columns:
            raise ValueError("HistoricalData.data 'power_kw' kolonu icermelidir")

        # --- Faz 1.6 Adim 4: auto-detect timestep ---
        from pvquant.pipeline.utils import _detect_timestep_minutes
        detected_timestep = _detect_timestep_minutes(df.index)

        scada = SCADAData(
            power_kw=df["power_kw"].astype(float),
            energy_kwh=None,
            poa_irradiance=df["poa_global"].astype(float) if "poa_global" in df.columns else None,
            temp_ambient=df["t_air"].astype(float) if "t_air" in df.columns else None,
            temp_module=df["t_module"].astype(float) if "t_module" in df.columns else None,
            wind_speed=df["wind_speed"].astype(float) if "wind_speed" in df.columns else None,
            plant_name=self.plant_profile.name,
            timestep_minutes=detected_timestep,
        )

        start_date = df.index.min().strftime("%Y-%m-%d")
        end_date = df.index.max().strftime("%Y-%m-%d")
        client = OpenMeteoClient()
        historical_meteo = client.get_historical(
            latitude=self.plant_profile.location.latitude,
            longitude=self.plant_profile.location.longitude,
            start_date=start_date,
            end_date=end_date,
            timezone=self.plant_profile.location.timezone,
        )

        # --- BIAS OGRENME (POA-bin lookup) ---
        bias_bins = None
        bias_corrections = None
        if scada.poa_irradiance is not None:
            bias_bins, bias_corrections = self._fit_ghi_bias(
                scada_poa=scada.poa_irradiance,
                meteo=historical_meteo,
            )
            # PlantProfile'a kaydet (mutable, dogrudan atama)
            self.plant_profile.ghi_bias_bins = bias_bins
            self.plant_profile.ghi_bias_corrections = bias_corrections

        cal_result = calibrate_from_scada(
            scada=scada,
            historical_meteo=historical_meteo,
            plant=self._plant_spec,
            fit_bg=True,
            fit_eta_bos=True,
        )

        self._plant_spec = cal_result.plant
        self._calibrated = True
        self._last_calibration_date = datetime.now(timezone.utc)

        return CalibrationParams(
            plant_id=self.plant_profile.plant_id,
            model_name=self.MODEL_NAME,
            fitted_at=self._last_calibration_date,
            valid_hours_used=int(cal_result.n_valid_hours),
            parameters={
                "bifacial_gain_geometric": float(cal_result.bg),
                "eta_bos": float(cal_result.eta_bos),
                "albedo": float(self._plant_spec.albedo),
                "gamma_pdc": float(self._plant_spec.effective_gamma),
            },
            quality_metrics={
                "mape_pct_before": float(cal_result.validation_before.mape_pct),
                "mape_pct_after": float(cal_result.validation_after.mape_pct),
                "total_deviation_pct_before": float(cal_result.validation_before.total_deviation_pct),
                "total_deviation_pct_after": float(cal_result.validation_after.total_deviation_pct),
                "mape_improvement_pct": float(cal_result.mape_improvement_pct),
            },
        )

    def get_metadata(self) -> ModelMetadata:
        return ModelMetadata(
            model_name=self.MODEL_NAME,
            model_version=self.MODEL_VERSION,
            description=(
                "Barhdadi-Bennis (2012) bagil verim modeli + bifacial revize. "
                "Pipeline: Erbs -> Perez -> Faiman -> Barhdadi-Bennis -> AC."
            ),
            suitable_for=["bifacial", "mono"],
            calibrated=self._calibrated,
            last_calibration_date=self._last_calibration_date,
            current_parameters={
                "bifacial_gain_geometric": self._plant_spec.bifacial_gain_geometric,
                "eta_bos": self._plant_spec.eta_bos,
                "albedo": self._plant_spec.albedo,
                "gamma_pdc": self._plant_spec.effective_gamma,
            },
        )


ModelRegistry.register(BarhdadiBennisModel.MODEL_NAME, BarhdadiBennisModel)
