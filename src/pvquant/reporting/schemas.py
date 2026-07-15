"""JSON çıktı — Pydantic v2 şeması (Tur 3'te derinleşecek çekirdek)."""
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class PlantInfo(BaseModel):
    name: str
    capacity_kwp: float
    latitude: float
    longitude: float
    timezone: str


class RunInfo(BaseModel):
    model: str
    model_version: str
    mode: str
    meteo_source: str
    run_at: datetime


class HourlyPoint(BaseModel):
    ts: datetime
    p50_kw: float
    energy_kwh: float


class DailyPoint(BaseModel):
    date: str
    p50_kwh: float


class Totals(BaseModel):
    p50_mwh: float
    capacity_factor_pct: float
    specific_yield_kwh_kwp: float = Field(
        description="IEC 61724-1 dönem özgül verimi")


class Quality(BaseModel):
    mape_pct: float | None = None
    deviation_pct: float | None = None
    eta_bos: float | None = None
    bg: float | None = None
    warnings: list[str] = []


class ForecastReport(BaseModel):
    schema_version: str = "1.0.0"
    generated_at: datetime
    plant: PlantInfo
    run: RunInfo
    totals: Totals
    daily: list[DailyPoint]
    hourly: list[HourlyPoint]
    quality: Quality


def build_json(ctx) -> str:
    h = ctx.hourly
    rapor = ForecastReport(
        generated_at=ctx.run_at_utc,
        plant=PlantInfo(name=ctx.plant_name, capacity_kwp=ctx.capacity_kwp,
                        latitude=ctx.latitude, longitude=ctx.longitude,
                        timezone=ctx.plant_tz),
        run=RunInfo(model=ctx.model_name, model_version=ctx.model_version,
                    mode=ctx.mode, meteo_source=ctx.meteo_source,
                    run_at=ctx.run_at_utc),
        totals=Totals(p50_mwh=round(ctx.total_mwh, 2),
                      capacity_factor_pct=round(ctx.capacity_factor_pct, 2),
                      specific_yield_kwh_kwp=round(ctx.specific_yield, 2)),
        daily=[DailyPoint(date=f"{g:%Y-%m-%d}", p50_kwh=round(float(v), 1))
               for g, v in ctx.daily_kwh.items()],
        hourly=[HourlyPoint(ts=ts.to_pydatetime(),
                            p50_kw=round(float(r["p50_kw"]), 2),
                            energy_kwh=round(float(r["energy_kwh"]), 2))
                for ts, r in h.iterrows()],
        quality=Quality(mape_pct=ctx.mape_pct, deviation_pct=ctx.deviation_pct,
                        eta_bos=ctx.eta_bos, bg=ctx.bg,
                        warnings=ctx.warnings or []),
    )
    return rapor.model_dump_json(indent=2)
