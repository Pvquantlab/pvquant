"""
PVQuant - PVModel Protocol
==========================

Tüm modellerin uyması gereken sözleşme.
Implementations: BarhdadiBennisModel, SAPMModel, PVWattsModel, vb.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .contracts import (
    PlantProfile,
    ForecastInput,
    OperationConfig,
    HistoricalData,
    ForecastResult,
    CalibrationParams,
    ModelMetadata,
)


@runtime_checkable
class PVModel(Protocol):
    """
    Her PV modelinin uyması gereken sözleşme.

    İki yollu yaşam döngüsü (müşterinin veri durumuna göre):

      YOL A — Pure Forecast (SCADA yok):
        1. plant profile ile constructor    (__init__)
        2. (kalibrasyon atlanır)
        3. predict() literatür katsayılarıyla
        4. metadata sorgulanabilir

      YOL B — Calibrated (SCADA var, 3+ ay):
        1. plant profile ile constructor    (__init__)
        2. SCADA verisiyle calibrate
        3. predict() fit edilmiş katsayılarla
        4. metadata sorgulanabilir

    İki yol da aynı predict()'i kullanır — fark sadece katsayılarda.
    """

    def __init__(self, plant: PlantProfile) -> None:
        """
        Santral profili ile modeli başlat.

        Davranış:
          - Modelin santral için uygun olduğunu doğrular
            (örn: PVWatts bifacial paneli reddeder)
          - Datasheet katsayılarını çıkarır ve saklar
          - Varsayılan katsayıları yükler (Pure Forecast modu için)
          - Hiçbir hava verisi yüklemez, tahmin yapmaz

        Raises:
          PlantNotSuitableError: Model bu santral tipini desteklemiyorsa
        """
        ...

    def predict(
        self,
        forecast_input: ForecastInput,
        config: OperationConfig,
    ) -> ForecastResult:
        """
        Üretim tahmini yap.

        Input: ForecastInput — atmosferik koşullar (Open-Meteo veya başka
               meteo kaynağından). ASLA gerçek üretim verisi almaz.

        Davranış:
          - Girdi verisini doğrular (yeterli saat, NaN kümeleri yok)
          - config.operation_mode'a göre dallanır:
              "pure_forecast": literatür/datasheet katsayıları
              "calibrated": prior calibrate()'den gelen fit katsayıları
          - Fiziksel modeli uygular: ışınım → sıcaklık → güç
          - ForecastResult olarak paketler

        Raises:
          InsufficientDataError: Girdi 6+ saat boşluk içeriyorsa
          ModeError: "calibrated" istenmiş ama kalibrasyon yapılmamışsa
        """
        ...

    def calibrate(self, historical: HistoricalData) -> CalibrationParams:
        """
        Geçmiş SCADA üretim verisinden katsayıları öğren.

        Input: HistoricalData — santralın gerçek üretim ölçümleri,
               opsiyonel olarak ölçülmüş meteo (POA, T_air).
               Modelin fit edeceği "ground truth".

        Davranış:
          - Veri yeterliliğini doğrular (>= 3 ay, >= 1500 valid saat)
          - Modele özel katsayıları scipy.optimize ile fit eder
          - YAN ETKİ: fit edilen katsayıları self içinde saklar
            (model artık calibrated)
          - Audit/logging için params nesnesini döner

        Raises:
          InsufficientDataError: Veri eşikleri karşılamıyorsa
        """
        ...

    def get_metadata(self) -> ModelMetadata:
        """
        Bu model örneğinin mevcut durumunu döndür.
        Saf okuma; yan etki yok.
        """
        ...