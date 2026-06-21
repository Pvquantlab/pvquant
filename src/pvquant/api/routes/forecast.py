"""POST /forecast — 7 günlük üretim tahmini endpoint'i.

Senin diyagramındaki "meteorolojik veri olursa" akışını çağırır.
Açıkça SCADA verisi göndermediğin sürece default parametrelerle hesap yapılır.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from pvquant.api.schemas.forecast import (
    DailyPoint,
    ForecastMeta,
    ForecastRequest,
    ForecastResponse,
    HourlyPoint,
)
from pvquant.io.meteo import OpenMeteoClient, OpenMeteoError
from pvquant.pipeline.forecast import forecast_7day

router = APIRouter(prefix="/forecast", tags=["forecast"])


@router.post("/", response_model=ForecastResponse)
def forecast(req: ForecastRequest) -> ForecastResponse:
    """7 günlük üretim tahmini.

    1. Open-Meteo'dan saatlik forecast verisi çekilir.
    2. Erbs → Perez → Faiman → Barhdadi-Bennis zinciri çalıştırılır.
    3. Saatlik AC güç ve günlük toplamlar döner.

    Args:
        req: ForecastRequest (santral spec'i ve opsiyonlar).

    Returns:
        ForecastResponse.
    """
    try:
        meteo = OpenMeteoClient().get_forecast(
            latitude=req.plant.latitude,
            longitude=req.plant.longitude,
            days=req.days,
        )
    except OpenMeteoError as e:
        raise HTTPException(status_code=502, detail=f"Meteo servisi hatası: {e}") from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    plant_spec = req.plant.to_dataclass()
    result = forecast_7day(meteo, plant_spec)

    daily = [
        DailyPoint(date=str(ts.date()), energy_kwh=float(val))
        for ts, val in result.daily_energy_kwh.items()
    ]

    hourly: list[HourlyPoint] | None = None
    if req.include_hourly:
        hourly = [
            HourlyPoint(
                timestamp=ts,
                ghi=float(row["ghi"]),
                poa_global=float(row["poa_global"]),
                temp_cell=float(row["temp_cell"]),
                p_ac_kw=float(row["p_ac_kw"]),
                energy_kwh=float(row["energy_kwh"]),
            )
            for ts, row in result.hourly.iterrows()
        ]

    return ForecastResponse(
        plant=req.plant,
        daily=daily,
        hourly=hourly,
        total_kwh=float(result.total_kwh),
        average_daily_kwh=float(result.average_daily_kwh),
        peak_power_kw=float(result.peak_power_kw),
        capacity_factor=float(result.capacity_factor),
        meta=ForecastMeta(**result.meta),
    )
