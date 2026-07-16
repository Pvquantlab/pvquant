"""Referans santral (4514 kWp bifacial) ucu uca dogrulama."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import pandas as pd

from pvquant.models_v2.contracts import (
    PlantProfile, Location, PanelSpec, MountingSpec, InverterSpec,
    ForecastInput, HistoricalData, OperationConfig,
)
from pvquant.models_v2.barhdadi_bennis import BarhdadiBennisModel
from pvquant.io.meteo import OpenMeteoClient


print("=" * 60)
print("REFERANS SANTRAL UCU UCA DOGRULAMA")
print("=" * 60)

# --- 1. PlantProfile ---
print("\n[1/5] PlantProfile olusturuluyor...")
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
    inverter=InverterSpec(
        ac_capacity_kw=215, count=18, efficiency=0.98,
    ),
)
print(f"  OK: {plant.name} - {plant.dc_capacity_kwp} kWp")

# --- 2. SCADA verisi ---
print("\n[2/5] SCADA verisi yukleniyor...")
SCADA_CSV = ROOT / "data" / "REFPLANT_SCADA_FULL.csv"
scada_df = pd.read_csv(SCADA_CSV, parse_dates=["timestamp"])
print(f"  OK: {len(scada_df)} satir, {scada_df['timestamp'].min()} -> {scada_df['timestamp'].max()}")

# --- 3. Kalibrasyon ---
print("\n[3/5] Kalibrasyon calistiriliyor (birkac dakika)...")
model = BarhdadiBennisModel(plant)
historical = HistoricalData(plant_id="REFPLANT", data=scada_df)
cal = model.calibrate(historical)
print(f"  OK: Kalibrasyon tamamlandi.")
print(f"  BG          : {cal.parameters['bifacial_gain_geometric']:.4f}")
print(f"  eta_BoS     : {cal.parameters['eta_bos']:.4f}")
bb = plant.ghi_bias_bins or []
print(f"  Bias bins   : {len(bb)} adet (plant'a kaydedildi)")
print(f"  Gecerli saat: {cal.valid_hours_used}")
print(f"  MAPE oncesi : {cal.quality_metrics['mape_pct_before']:.2f}%")
print(f"  MAPE sonrasi: {cal.quality_metrics['mape_pct_after']:.2f}%")

# --- 4. Tahmin ---
print("\n[4/5] Ayni donem icin tahmin yapiliyor...")
start_date = scada_df["timestamp"].min().strftime("%Y-%m-%d")
end_date = scada_df["timestamp"].max().strftime("%Y-%m-%d")

client = OpenMeteoClient()
meteo = client.get_historical(
    latitude=plant.location.latitude,
    longitude=plant.location.longitude,
    start_date=start_date, end_date=end_date,
    timezone=plant.location.timezone,
)

forecast_df = pd.DataFrame({
    "timestamp": meteo.ghi.index,
    "ghi": meteo.ghi.values,
    "t_air": meteo.temp_air.values,
    "wind_speed": meteo.wind_speed_10m.values,
})
forecast_input = ForecastInput(
    source="open_meteo", resolution_minutes=60, data=forecast_df,
)
config = OperationConfig(operation_mode="calibrated")
result = model.predict(forecast_input, config)
print(f"  OK: {len(result.timeseries)} saatlik tahmin uretildi.")

# --- 5. Karsilastirma ---
print("\n[5/5] SCADA vs tahmin karsilastirma...")
ts = result.timeseries.set_index("timestamp_utc")
if ts.index.tz is None:
    ts.index = pd.to_datetime(ts.index).tz_localize("UTC")
scada_idx = scada_df.set_index("timestamp")
if scada_idx.index.tz is None:
    scada_idx.index = scada_idx.index.tz_localize(
        plant.location.timezone, ambiguous="infer", nonexistent="shift_forward"
    ).tz_convert("UTC")

comp = pd.DataFrame({
    "scada_kw": scada_idx["power_kw"],
    "pred_kw":  ts["ac_power_kw"],
}).dropna()

scada_total = comp["scada_kw"].sum()
pred_total  = comp["pred_kw"].sum()
dev_pct = 100 * (pred_total - scada_total) / scada_total

errors = comp["pred_kw"] - comp["scada_kw"]
rmse = float(np.sqrt((errors ** 2).mean()))
mae = float(errors.abs().mean())
mask = comp["scada_kw"] > 50
mape = float(100 * (errors[mask].abs() / comp.loc[mask, "scada_kw"]).mean())

print(f"\n--- SONUC ---")
print(f"  Karsilastirilan saat: {len(comp)}")
print(f"  SCADA toplam        : {scada_total/1000:.1f} MWh")
print(f"  Tahmin toplam       : {pred_total/1000:.1f} MWh")
print(f"  Yillik sapma        : {dev_pct:+.2f}%  <-- HEDEF: -1% ile +1%")
print(f"  RMSE                : {rmse:.1f} kW")
print(f"  MAE                 : {mae:.1f} kW")
print(f"  MAPE (gunduz)       : {mape:.1f}%")
print("=" * 60)
