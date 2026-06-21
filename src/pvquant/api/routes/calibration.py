"""POST /calibration — SCADA CSV upload ile kalibrasyon endpoint'i.

Senin diyagramındaki "santral verisi olursa" akışını çağırır.
Kullanıcı CSV yükler + santral koordinatlarını verir → kalibre PlantSpec döner.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from pvquant.api.schemas.plant import PlantSpecSchema
from pvquant.io.meteo import OpenMeteoClient, OpenMeteoError
from pvquant.io.scada import load_csv
from pvquant.pipeline.calibration import calibrate_from_scada

router = APIRouter(prefix="/calibration", tags=["calibration"])


class CalibrationResponse(BaseModel):
    """Kalibrasyon yanıtı."""

    original_plant: PlantSpecSchema
    calibrated_plant: PlantSpecSchema
    bg: float
    eta_bos: float
    n_valid_hours: int
    mape_before_pct: float
    mape_after_pct: float
    mape_improvement_pct: float
    total_deviation_before_pct: float
    total_deviation_after_pct: float
    notes: list[str]


@router.post("/", response_model=CalibrationResponse)
async def calibrate(
    plant_json: str = Form(..., description="PlantSpecSchema JSON string"),
    scada_csv: UploadFile = File(..., description="SCADA üretim CSV dosyası"),
) -> CalibrationResponse:
    """SCADA CSV ile model kalibrasyonu.

    Adımlar:
    1. SCADA CSV parse edilir (Türkçe/İngilizce kolon isimleri otomatik).
    2. Aynı tarih aralığı için Open-Meteo arşiv verisi çekilir.
    3. calibrate_from_scada pipeline'ı koşturulur.
    4. Kalibre PlantSpec + iyileşme metrikleri döner.

    Args:
        plant_json: PlantSpecSchema JSON formatında (multipart form alanı).
        scada_csv: SCADA üretim CSV dosyası.

    Returns:
        CalibrationResponse.
    """
    import json as _json

    try:
        plant_dict = _json.loads(plant_json)
        plant_schema = PlantSpecSchema(**plant_dict)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"plant_json parse hatası: {e}") from e

    # Geçici dosyaya kaydet
    suffix = Path(scada_csv.filename or "scada.csv").suffix or ".csv"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await scada_csv.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        scada = load_csv(tmp_path)
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=f"CSV parse hatası: {e}") from e
    finally:
        tmp_path.unlink(missing_ok=True)

    if scada.hours_count < 100:
        raise HTTPException(
            status_code=400,
            detail=f"Yetersiz veri: {scada.hours_count} saat, minimum 100 gerekli",
        )

    # SCADA tarihinin başlangıç/bitiş aralığı
    scada_hourly = scada.to_hourly()
    start = scada_hourly.power_kw.index.min().date().isoformat()
    end = scada_hourly.power_kw.index.max().date().isoformat()

    try:
        meteo = OpenMeteoClient().get_historical(
            latitude=plant_schema.latitude,
            longitude=plant_schema.longitude,
            start_date=start,
            end_date=end,
        )
    except OpenMeteoError as e:
        raise HTTPException(status_code=502, detail=f"Meteo arşiv hatası: {e}") from e

    plant_dc = plant_schema.to_dataclass()
    try:
        result = calibrate_from_scada(scada=scada, historical_meteo=meteo, plant=plant_dc)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return CalibrationResponse(
        original_plant=PlantSpecSchema.from_dataclass(result.original_plant),
        calibrated_plant=PlantSpecSchema.from_dataclass(result.plant),
        bg=result.bg,
        eta_bos=result.eta_bos,
        n_valid_hours=result.n_valid_hours,
        mape_before_pct=result.validation_before.mape_pct,
        mape_after_pct=result.validation_after.mape_pct,
        mape_improvement_pct=result.mape_improvement_pct,
        total_deviation_before_pct=result.validation_before.total_deviation_pct,
        total_deviation_after_pct=result.validation_after.total_deviation_pct,
        notes=result.notes,
    )
