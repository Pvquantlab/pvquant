"""Referans santral üzerinde HybridResidualModel demo.

refplant_validation.py ile aynı kurulum; tek fark model sınıfı.
Fizik-vs-hibrit holdout karşılaştırmasını yazdırır.

Gereksinim: pip install lightgbm joblib
Veri: data/REFPLANT_SCADA_FULL.csv (timestamp, power_kw [, poa_global, t_air, ...])
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd

from pvquant.models_v2.contracts import (
    PlantProfile, Location, PanelSpec, MountingSpec, InverterSpec,
    ForecastInput, HistoricalData, OperationConfig,
)
from pvquant.models_v2.hybrid_residual import HybridResidualModel
from pvquant.io.meteo import OpenMeteoClient

print("=" * 60)
print("REFERANS SANTRAL — HYBRID RESIDUAL MODEL DEMO")
print("=" * 60)

# --- 1. PlantProfile (refplant_validation.py ile aynı) ---
plant = PlantProfile(
    plant_id="REFPLANT",
  name="Referans Santral",
    location=Location(
        latitude=37.87, longitude=32.49,
        timezone="Europe/Istanbul", elevation_m=1000,
    ),
    dc_capacity_kwp=4514, panel_count=8280,
    panel=PanelSpec(
        technology="bifacial",
        nominal_power_w=545,
        temperature_coefficient_gamma=-0.34,
        noct_celsius=45,
        bifaciality_factor=0.7,
    ),
    mounting=MountingSpec(
        mount_type="ground_fixed",
        tilt_degrees=20, azimuth_degrees=180,
        height_above_ground_m=2.0,
    ),
    inverter=InverterSpec(ac_capacity_kw=215, count=18, efficiency=0.98),
)

# --- 2. SCADA ---
print("\n[1/4] SCADA yükleniyor...")
scada_df = pd.read_csv(ROOT / "data" / "REFPLANT_SCADA_FULL.csv", parse_dates=["timestamp"])
# TZ fix: SCADA timestamps yerel saatte (Europe/Istanbul), models_v2 tz-aware bekliyor
scada_df["timestamp"] = scada_df["timestamp"].dt.tz_localize(
    "Europe/Istanbul", ambiguous="infer", nonexistent="shift_forward"
)
print(f"  OK: {len(scada_df)} satır (tz: Europe/Istanbul)")

# --- 3. Kalibrasyon: fizik fit + LGBM rezidüel ---
# Not: SCADA CSV'de ghi/t_air/wind_speed kolonları varsa saha meteo verisi
# kullanılır ve Open-Meteo çağrısı atlanır; yoksa arşivden çekilir.
print("\n[2/4] Hibrit kalibrasyon (fizik + LightGBM)...")
model = HybridResidualModel(plant)
params = model.calibrate(HistoricalData(plant_id="REFPLANT", data=scada_df))

q = params.quality_metrics
print("\n  --- Holdout raporu (kronolojik son %20) ---")
print(f"  Fizik  MAPE : {q['mape_pct_physics_holdout']:.2f} %")
print(f"  Hibrit MAPE : {q['mape_pct_hybrid_holdout']:.2f} %")
print(f"  Fizik  RMSE : {q['rmse_kw_physics_holdout']:.1f} kW")
print(f"  Hibrit RMSE : {q['rmse_kw_hybrid_holdout']:.1f} kW")
print(f"  İyileşme    : {q['mape_improvement_pct']:+.2f} puan")

# --- 4. ML katmanını kaydet ---
print("\n[3/4] ML katmanı kaydediliyor...")
model.save_ml_layer(ROOT / "calibration_cache")
print("  OK: calibration_cache/REFPLANT_hybrid_residual.joblib")

# --- 5. 7 günlük canlı tahmin (P10/P50/P90 ile) ---
print("\n[4/4] 7 günlük tahmin...")
meteo = OpenMeteoClient().get_forecast(
    latitude=plant.location.latitude, longitude=plant.location.longitude
)
fi = ForecastInput(
    source="open_meteo",
    resolution_minutes=60,
    data=pd.DataFrame({
        "timestamp": meteo.ghi.index,
        "ghi": meteo.ghi.values,
        "t_air": meteo.temp_air.values,
        "wind_speed": meteo.wind_speed_10m.values,
    }),
)
result = model.predict(fi, OperationConfig(
    operation_mode="calibrated", confidence_intervals=True,
))
print(f"  7 gün toplam (P50 nokta): {result.summary.total_energy_kwh:,.0f} kWh")
if result.confidence:
    c = result.confidence
    print(f"  P10 / P50 / P90: {c.p10_total_kwh:,.0f} / "
          f"{c.p50_total_kwh:,.0f} / {c.p90_total_kwh:,.0f} kWh")
print("\nBitti.")
