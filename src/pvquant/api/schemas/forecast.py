"""Forecast endpoint için Pydantic şemaları."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from pvquant.api.schemas.plant import PlantSpecSchema


class ForecastRequest(BaseModel):
    """7 günlük tahmin isteği."""

    plant: PlantSpecSchema
    days: int = Field(7, ge=1, le=16, description="Tahmin gün sayısı")
    include_hourly: bool = Field(
        True, description="Saatlik detay yanıta dahil edilsin mi?"
    )


class HourlyPoint(BaseModel):
    """Saatlik tahmin tek bir nokta."""

    timestamp: datetime
    ghi: float = Field(..., description="Yatay küresel ışınım, W/m²")
    poa_global: float = Field(..., description="POA toplam ışınım, W/m²")
    temp_cell: float = Field(..., description="Hücre sıcaklığı, °C")
    p_ac_kw: float = Field(..., description="AC güç, kW")
    energy_kwh: float = Field(..., description="Saatlik enerji, kWh")


class DailyPoint(BaseModel):
    """Günlük toplam üretim."""

    date: str = Field(..., description="YYYY-MM-DD")
    energy_kwh: float


class ForecastMeta(BaseModel):
    """Hesaplama metadata."""

    thermal_model: str
    power_model: str
    is_bifacial: bool
    bifacial_gain_pct: float
    gamma_used: float
    meteo_source: str
    decomposition_model: str
    transposition_model: str


class ForecastResponse(BaseModel):
    """7 günlük tahmin yanıtı."""

    plant: PlantSpecSchema
    daily: list[DailyPoint]
    hourly: list[HourlyPoint] | None = None
    total_kwh: float
    average_daily_kwh: float
    peak_power_kw: float
    capacity_factor: float
    meta: ForecastMeta
