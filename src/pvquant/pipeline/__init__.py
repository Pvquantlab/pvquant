"""İş akışı (pipeline) modülleri.

Modeller ve IO katmanını birleştiren iki ana akış:

- `forecast`: Meteoroloji verisinden 7 günlük üretim tahmini.
- `calibration`: SCADA verisinden model parametre kalibrasyonu.

Bu iki akış senin diyagramındaki iki kollu girişi karşılar:
- "Santral verisi var" → calibration → tahmin
- "Sadece meteo var" → forecast (default parametrelerle)
"""

from pvquant.pipeline.forecast import ForecastResult, PlantSpec, forecast_7day
from pvquant.pipeline.calibration import CalibrationResult, calibrate_from_scada

__all__ = [
    "ForecastResult",
    "PlantSpec",
    "forecast_7day",
    "CalibrationResult",
    "calibrate_from_scada",
]
