"""
SCADA POA vs Open-Meteo POA bias analizi.

Amac: REFPLANT'in olculmus POA'sini, Open-Meteo GHI'den Erbs+Perez ile
hesaplanmis POA ile karsilastirmak.

Cikti:
  - data/bias_hourly.csv
  - data/bias_summary.csv
  - Terminal raporu
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from pvquant.io.meteo import OpenMeteoClient
from pvquant.models import irradiance


SCADA_CSV = ROOT / "data" / "REFPLANT_SCADA_FULL.csv"
OUT_HOURLY = ROOT / "data" / "bias_hourly.csv"
OUT_SUMMARY = ROOT / "data" / "bias_summary.csv"

LATITUDE = 37.87
LONGITUDE = 32.49
TIMEZONE = "Europe/Istanbul"
ALBEDO = 0.25
TILT = 25.0
AZIMUTH = 180.0

MIN_POA_THRESHOLD = 50.0


def force_utc(series, tz=TIMEZONE):
    """Bir Series'in index'ini UTC tz-aware'e cevirir."""
    idx = series.index
    if idx.tz is None:
        idx = idx.tz_localize(tz, ambiguous="infer", nonexistent="shift_forward")
    return series.set_axis(idx.tz_convert("UTC"))


def main():
    print("=" * 60)
    print("SCADA POA vs Open-Meteo POA BIAS ANALIZI")
    print("=" * 60)
    print()

    # 1. SCADA
    print("[1/5] SCADA yukleniyor...")
    scada = pd.read_csv(SCADA_CSV)
    scada["timestamp"] = pd.to_datetime(scada["timestamp"])
    scada = scada.set_index("timestamp").sort_index()
    if scada.index.tz is None:
        scada.index = scada.index.tz_localize(TIMEZONE, ambiguous="infer", nonexistent="shift_forward")
    scada.index = scada.index.tz_convert("UTC")
    print(f"      Satir: {len(scada)}, donem (UTC): {scada.index.min()} -> {scada.index.max()}")
    print(f"      Kolonlar: {list(scada.columns)}")
    print()

    # 2. Open-Meteo
    print("[2/5] Open-Meteo arsivi cekiliyor (1-2 dk)...")
    start_date = scada.index.min().strftime("%Y-%m-%d")
    end_date = scada.index.max().strftime("%Y-%m-%d")
    client = OpenMeteoClient()
    meteo = client.get_historical(
        latitude=LATITUDE,
        longitude=LONGITUDE,
        start_date=start_date,
        end_date=end_date,
        timezone=TIMEZONE,
    )
    print(f"      GHI satir: {len(meteo.ghi)}")
    print()

    # 3. Open-Meteo GHI -> POA
    print("[3/5] Open-Meteo POA hesaplaniyor (Erbs + Perez)...")
    ghi = meteo.ghi.copy()
    if ghi.index.tz is None:
        ghi.index = ghi.index.tz_localize(TIMEZONE, ambiguous="infer", nonexistent="shift_forward")
    ghi.index = ghi.index.tz_convert("UTC")
    times = ghi.index

    solpos = irradiance.solar_position(
        times=times,
        latitude=LATITUDE,
        longitude=LONGITUDE,
    )
    decomposed = irradiance.decompose_ghi_erbs(
        ghi=ghi,
        solar_zenith=solpos["zenith"],
        times=times,
    )
    dni_extra, airmass = irradiance.extra_radiation_and_airmass(times, solpos["zenith"])
    poa = irradiance.transpose_perez(
        surface_tilt=TILT,
        surface_azimuth=AZIMUTH,
        solar_zenith=solpos["zenith"],
        solar_azimuth=solpos["azimuth"],
        dni=decomposed["dni"],
        ghi=decomposed["ghi"],
        dhi=decomposed["dhi"],
        dni_extra=dni_extra,
        airmass=airmass,
        albedo=ALBEDO,
    )
    poa_openmeteo = poa.global_
    print(f"      POA hesaplandi, ortalama: {poa_openmeteo.mean():.1f} W/m^2")
    print()

    # 4. Karsilastirma
    print("[4/5] Karsilastirma yapiliyor...")
    df = pd.DataFrame({
        "scada_poa": scada["poa_global"],
        "openmeteo_poa": poa_openmeteo,
        "ghi_openmeteo": ghi,
        "solar_zenith": solpos["zenith"],
        "t_air_scada": scada["t_air"],
    })
    df = df.dropna()
    print(f"      Hizalanan saat: {len(df)}")

    df_day = df[
        (df["scada_poa"] >= MIN_POA_THRESHOLD)
        & (df["openmeteo_poa"] >= MIN_POA_THRESHOLD)
    ].copy()
    print(f"      Gunduz saat (POA>=50): {len(df_day)}")
    print()

    # 5. Istatistikler
    print("[5/5] Bias istatistikleri:")
    print()

    df_day["bias"] = df_day["openmeteo_poa"] - df_day["scada_poa"]
    df_day["bias_pct"] = (df_day["bias"] / df_day["scada_poa"]) * 100
    df_day["ratio"] = df_day["openmeteo_poa"] / df_day["scada_poa"]

    print("  --- GENEL ---")
    print(f"  Ortalama SCADA POA      : {df_day['scada_poa'].mean():.1f} W/m^2")
    print(f"  Ortalama Open-Meteo POA : {df_day['openmeteo_poa'].mean():.1f} W/m^2")
    print(f"  Ortalama bias (W/m^2)   : {df_day['bias'].mean():+.1f}")
    print(f"  Ortalama bias (%)       : {df_day['bias_pct'].mean():+.2f}")
    print(f"  RMSE (W/m^2)            : {np.sqrt((df_day['bias']**2).mean()):.1f}")
    print(f"  Ortalama oran (OM/SC)   : {df_day['ratio'].mean():.4f}")
    print(f"  Median oran (OM/SC)     : {df_day['ratio'].median():.4f}")
    print()

    total_om = df_day["openmeteo_poa"].sum()
    total_sc = df_day["scada_poa"].sum()
    print(f"  Toplam Open-Meteo (W*h) : {total_om:.0f}")
    print(f"  Toplam SCADA (W*h)      : {total_sc:.0f}")
    print(f"  Toplam oran (OM/SC)     : {total_om/total_sc:.4f}")
    print(f"  -> GHI carpani (SC/OM)  : {total_sc/total_om:.4f}")
    print()

    print("  --- AYLIK ---")
    monthly = df_day.groupby(df_day.index.to_period("M")).agg(
        scada_mean=("scada_poa", "mean"),
        om_mean=("openmeteo_poa", "mean"),
        bias_mean=("bias", "mean"),
        bias_pct=("bias_pct", "mean"),
        ratio=("ratio", "mean"),
        n=("scada_poa", "count"),
    )
    monthly.index = monthly.index.astype(str)
    print(monthly.to_string())
    print()

    print("  --- ISINIM SEVIYESI ---")
    bins = [50, 200, 400, 600, 800, 1000, 1500]
    df_day["poa_bin"] = pd.cut(df_day["scada_poa"], bins=bins)
    by_bin = df_day.groupby("poa_bin", observed=True).agg(
        scada_mean=("scada_poa", "mean"),
        om_mean=("openmeteo_poa", "mean"),
        bias_mean=("bias", "mean"),
        bias_pct=("bias_pct", "mean"),
        ratio=("ratio", "mean"),
        n=("scada_poa", "count"),
    )
    print(by_bin.to_string())
    print()

    df_day[["scada_poa", "openmeteo_poa", "ghi_openmeteo", "solar_zenith", "bias", "bias_pct", "ratio"]].to_csv(OUT_HOURLY)
    monthly.to_csv(OUT_SUMMARY)
    print(f"  Saatlik karsilastirma: {OUT_HOURLY}")
    print(f"  Aylik ozet           : {OUT_SUMMARY}")
    print()
    print("=" * 60)
    print("BIAS ANALIZI TAMAMLANDI")
    print("=" * 60)


if __name__ == "__main__":
    main()
    