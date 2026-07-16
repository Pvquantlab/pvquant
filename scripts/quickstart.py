"""PVQuant hızlı başlangıç örneği.

Bu script iki ana kullanım senaryosunu gösterir:

1. Sadece koordinat ile 7 günlük tahmin (yeni proje / ön fizibilite).
2. SCADA CSV ile model kalibrasyonu (operasyonel saha).

Çalıştırmak için:

.. code:: bash

    python scripts/quickstart.py

Önce paket kurulu olmalı:

.. code:: bash

    pip install -e ".[dev]"
"""
from __future__ import annotations

import sys
from pathlib import Path

# Eğer paket henüz kurulmadıysa src/ dizinini path'e ekle
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from pvquant.io.meteo import OpenMeteoClient
from pvquant.io.scada import load_csv
from pvquant.pipeline.calibration import calibrate_from_scada
from pvquant.pipeline.forecast import PlantSpec, forecast_7day


def demo_forecast_only() -> None:
    """Senaryo 1: Sadece meteo verisi ile 7 günlük tahmin."""
    print("=" * 60)
    print("SENARYO 1: Meteo-only forecast (Konya, 5 MWp)")
    print("=" * 60)

    # Konya merkez koordinatları
    meteo = OpenMeteoClient().get_forecast(latitude=37.87, longitude=32.49, days=7)
    print(f"Open-Meteo'dan {len(meteo.ghi)} saatlik veri alındı")
    print(f"GHI ortalama: {meteo.ghi.mean():.1f} W/m²")
    print(f"Sıcaklık ortalama: {meteo.temp_air.mean():.1f} °C")

    plant = PlantSpec(
        p_nom_kwp=5000,
        latitude=37.87,
        longitude=32.49,
        tilt=30,
        azimuth=180,
        module_tech="topcon",
        bifacial_factor=0.70,  # Bifacial modül
        bifacial_gain_geometric=0.347,
        albedo=0.25,
        eta_bos=0.93,
        thermal_model="faiman",
        power_model="barhdadi_bennis",
    )

    result = forecast_7day(meteo, plant)

    print("\n--- 7 Günlük Tahmin ---")
    for date, kwh in result.daily_energy_kwh.items():
        print(f"  {date.date()}  →  {kwh:>10,.0f} kWh")
    print(f"\nToplam       : {result.total_kwh:>10,.0f} kWh")
    print(f"Günlük ort.  : {result.average_daily_kwh:>10,.0f} kWh")
    print(f"Pik güç      : {result.peak_power_kw:>10,.1f} kW")
    print(f"Kapasite fak.: {result.capacity_factor:>10.2%}")


def demo_calibration() -> None:
    """Senaryo 2: SCADA CSV ile kalibrasyon (yerel örnek veri)."""
    print("\n" + "=" * 60)
    print("SENARYO 2: SCADA tabanlı kalibrasyon (REFPLANT örnek)")
    print("=" * 60)

    sample_csv = REPO_ROOT / "tests" / "data" / "refplant_sample.csv"
    if not sample_csv.exists():
        print(f"Örnek CSV bulunamadı: {sample_csv}")
        return

    scada = load_csv(sample_csv, plant_name="REFPLANT Sample")
    print(f"SCADA yüklendi: {scada.hours_count} geçerli saat, {scada.timestep_minutes} dk adım")

    scada_hourly = scada.to_hourly()
    start = scada_hourly.power_kw.index.min().date()
    end = scada_hourly.power_kw.index.max().date()
    print(f"Tarih aralığı: {start} → {end}")

    print("\nOpen-Meteo arşivinden meteo çekiliyor...")
    meteo = OpenMeteoClient().get_historical(
        latitude=38.76,
        longitude=30.54,
        start_date=str(start),
        end_date=str(end),
    )

    plant_initial = PlantSpec(
        p_nom_kwp=4514,
        latitude=38.76,
        longitude=30.54,
        tilt=25,
        azimuth=180,
        module_tech="mono_si",
        bifacial_factor=0.70,
        bifacial_gain_geometric=0.30,  # Başlangıç tahmini
        albedo=0.25,
        eta_bos=0.90,
        thermal_model="faiman",
        power_model="barhdadi_bennis",
    )

    calibration = calibrate_from_scada(
        scada=scada,
        historical_meteo=meteo,
        plant=plant_initial,
    )

    print("\n--- Kalibrasyon Sonucu ---")
    print(calibration)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="PVQuant hızlı başlangıç")
    parser.add_argument(
        "scenario",
        choices=["forecast", "calibrate", "both"],
        default="forecast",
        nargs="?",
        help="Çalıştırılacak senaryo",
    )
    args = parser.parse_args()

    try:
        if args.scenario in ("forecast", "both"):
            demo_forecast_only()
        if args.scenario in ("calibrate", "both"):
            demo_calibration()
    except Exception as e:
        print(f"\nHATA: {type(e).__name__}: {e}")
        print("İnternet bağlantısı veya Open-Meteo erişimi sorunlu olabilir.")
        sys.exit(1)
