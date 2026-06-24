"""
PVQuant - Veri Sözleşmeleri (Pydantic models)
==============================================

Modellerin girdi/çıktı yapısını tanımlar.
Tasarım: pvmodel_interface_draft_v1.2.py
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional, Any

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field


# ============================================================
# PLANT PROFILE — Santral profili (statik)
# ============================================================

class Location(BaseModel):
    """Santral coğrafi konumu. WGS84."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    elevation_m: float = Field(default=0)
    timezone: str  # IANA tz, örn: "Europe/Istanbul"


class PanelSpec(BaseModel):
    """Panel datasheet bilgileri."""
    technology: Literal["mono", "bifacial", "thin_film"]
    nominal_power_w: float
    temperature_coefficient_gamma: float  # %/°C, örn: -0.34
    noct_celsius: float = Field(default=45)
    bifaciality_factor: Optional[float] = None


class MountingSpec(BaseModel):
    """Montaj bilgileri."""
    mount_type: Literal["rooftop_fixed", "ground_fixed",
                        "single_axis_tracker", "dual_axis_tracker"]
    tilt_degrees: float = Field(..., ge=0, le=90)
    azimuth_degrees: float = Field(..., ge=0, lt=360)
    gcr: Optional[float] = None
    height_above_ground_m: Optional[float] = None


class InverterSpec(BaseModel):
    """İnverter bilgileri."""
    ac_capacity_kw: float
    count: int
    efficiency: float = Field(default=0.98)
    clipping_kw: Optional[float] = None


class PlantProfile(BaseModel):
    """Tam santral profili. Kayıtta bir kez oluşturulur, değişmez."""
    plant_id: str
    name: str
    location: Location
    dc_capacity_kwp: float
    panel_count: int
    panel: PanelSpec
    mounting: MountingSpec
    inverter: InverterSpec
    commissioning_date: Optional[datetime] = None
    notes: Optional[str] = None


# ============================================================
# INPUTS — Modele giren veriler
# ============================================================

class ForecastInput(BaseModel):
    """
    predict() için meteorolojik veri.
    
    Beklenen kolonlar (data DataFrame'inde):
      - timestamp (UTC)
      - ghi (W/m²)
      - t_air (°C)
      - wind_speed (m/s)
    
    Opsiyonel kolonlar:
      - poa_global (W/m²) — SCADA'dan geliyorsa
      - t_module (°C) — SCADA'dan geliyorsa
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    source: Literal["open_meteo", "scada", "solcast", "solargis", "ecmwf"]
    resolution_minutes: int = Field(..., ge=1, le=60)
    data: pd.DataFrame


class HistoricalData(BaseModel):
    """
    calibrate() için SCADA verisi.
    
    Beklenen kolonlar:
      - timestamp (UTC)
      - power_kw (gerçek üretim)
    
    Opsiyonel ama değerli:
      - poa_global, t_air, t_module
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    plant_id: str
    data: pd.DataFrame
    quality_score: float = Field(default=1.0, ge=0, le=1)


class OperationConfig(BaseModel):
    """predict() runtime config."""
    operation_mode: Literal["pure_forecast", "calibrated"]
    forecast_horizon_hours: int = Field(default=168, ge=1, le=336)
    include_debug_info: bool = Field(default=False)
    confidence_intervals: bool = Field(default=False)


# ============================================================
# OUTPUTS — Modelden çıkan veriler
# ============================================================

class CalibrationParams(BaseModel):
    """calibrate() çıktısı."""
    plant_id: str
    model_name: str
    fitted_at: datetime
    valid_hours_used: int
    parameters: dict[str, float]  # {"eta_bos": 0.917, "bg": 0.347, ...}
    quality_metrics: dict[str, float]  # {"yearly_deviation_pct": -0.77, ...}


class ForecastSummary(BaseModel):
    """Tahmin özeti."""
    total_energy_kwh: float
    peak_power_kw: float
    average_capacity_factor: float
    forecast_window_start: datetime  # UTC
    forecast_window_end: datetime  # UTC


class ConfidenceIntervals(BaseModel):
    """Faz 4+: tahmin belirsizliği."""
    p10_total_kwh: float
    p50_total_kwh: float
    p90_total_kwh: float
    method: Literal["quantile_regression", "ensemble", "ml_uncertainty"]


class ForecastResult(BaseModel):
    """
    predict() çıktısı — hibrit yapı.
    
    Metadata Pydantic'te (tip güvenli), timeseries DataFrame'de (verimli).
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    plant_id: str
    model_name: str
    model_version: str
    operation_mode: str
    weather_source: str
    
    # timeseries kolonları:
    # timestamp_utc, poa_global, t_cell, dc_power_kw, ac_power_kw
    timeseries: pd.DataFrame
    
    summary: ForecastSummary
    debug_info: Optional[dict[str, Any]] = None
    confidence: Optional[ConfidenceIntervals] = None


class ModelMetadata(BaseModel):
    """Model durum bilgisi (şeffaflık için)."""
    model_name: str
    model_version: str
    description: str
    suitable_for: list[str]  # ["mono", "bifacial", ...]
    calibrated: bool
    last_calibration_date: Optional[datetime] = None
    current_parameters: dict[str, float]