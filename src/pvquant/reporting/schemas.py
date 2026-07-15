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


class HybridQuality(BaseModel):
    """Mod C holdout sınavı — kronolojik son %20 (yalnız hibrit aktifken)."""
    holdout_mape_pct: float
    holdout_rmse_kw: float | None = None
    physics_mape_pct: float | None = None
    improvement_pct: float | None = None
    holdout_hours: int | None = None
    note: str | None = None      # marjinal iyileşme uyarısı (< kapı eşiği %3)


class Quality(BaseModel):
    mape_pct: float | None = None
    deviation_pct: float | None = None
    eta_bos: float | None = None
    bg: float | None = None
    hybrid: HybridQuality | None = None
    warnings: list[str] = []


class ForecastReport(BaseModel):
    schema_version: str = "1.0.0"   # build_json ctx'ten geçirir (SCHEMA_VERSION)
    generated_at: datetime
    plant: PlantInfo
    run: RunInfo
    totals: Totals
    daily: list[DailyPoint]
    hourly: list[HourlyPoint]
    quality: Quality


def _hybrid_quality(ctx) -> "HybridQuality | None":
    """Sözleşme koruması: mode!='C' ya da holdout yoksa blok HİÇ üretilmez
    (null değil, YOK) — Mod B tüketicileri geriye dönük aynen çalışır."""
    if ctx.mode != "C" or ctx.holdout_mape_pct is None:
        return None
    imp = ctx.holdout_improvement_pct
    not_metni = None
    if imp is not None and imp < 3.0:   # terfi kapısıyla AYNI eşik (config)
        not_metni = ("marjinal iyileşme — kapı eşiği %3'ün altında; "
                     "fizikten istatistiksel ayrışma zayıf olabilir")
    return HybridQuality(
        holdout_mape_pct=round(ctx.holdout_mape_pct, 2),
        holdout_rmse_kw=round(ctx.holdout_rmse_kw, 1)
            if ctx.holdout_rmse_kw is not None else None,
        physics_mape_pct=round(ctx.holdout_physics_mape_pct, 2)
            if ctx.holdout_physics_mape_pct is not None else None,
        improvement_pct=round(imp, 1) if imp is not None else None,
        holdout_hours=ctx.holdout_hours,
        note=not_metni,
    )


def build_json(ctx) -> str:
    import json as _json
    h = ctx.hourly
    rapor = ForecastReport(
        schema_version=ctx.schema_version,
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
                        hybrid=_hybrid_quality(ctx),
                        warnings=ctx.warnings or []),
    )
    d = rapor.model_dump(mode="json")
    if d["quality"].get("hybrid") is None:      # yok = YOK (null değil)
        d["quality"].pop("hybrid", None)
    return _json.dumps(d, indent=2, ensure_ascii=False)
