"""MERKAS fizik kalibrasyonu teshis betigi."""
from __future__ import annotations
import time
from pathlib import Path
import pandas as pd

MERKAS_CAPACITY_KWP = 4514.0
MERKAS_LAT = 37.87
MERKAS_LON = 32.49
CSV_PATH = Path("data/MERKAS_SCADA_FULL.csv")


def build_scada_data():
    from pvquant.io.scada import SCADAData
    print(f"[1/4] CSV yukleniyor: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.set_index("timestamp")
    full_range = pd.date_range(start=df.index.min(), end=df.index.max(), freq="1h")
    df = df.reindex(full_range)
    df.index.name = "timestamp"
    import pvlib
    solpos = pvlib.solarposition.get_solarposition(df.index, MERKAS_LAT, MERKAS_LON)
    is_night = solpos["apparent_elevation"].values < -3.0
    night_nan_mask = is_night & df["power_kw"].isna().values
    df.loc[night_nan_mask, "power_kw"] = 0.0
    def _opt(col):
        return df[col] if col in df.columns else None
    scada = SCADAData(
        power_kw=df["power_kw"],
        energy_kwh=_opt("energy_kwh"),
        poa_irradiance=_opt("poa_global"),
        temp_ambient=_opt("t_air"),
        temp_module=_opt("t_module"),
        wind_speed=_opt("wind_speed"),
        plant_name="MERKAS_teshis",
        timestep_minutes=60,
    )
    n_valid = int(df["power_kw"].notna().sum())
    poa_txt = "var" if scada.has_irradiance else "yok"
    print(f"      -> SCADAData: {n_valid:,} saat, POA={poa_txt}")
    print(f"      -> Aralik: {df.index.min()} -> {df.index.max()}")
    return scada


def fetch_meteo(start_date, end_date):
    from pvquant.io.meteo import OpenMeteoClient
    print(f"[2/4] Open-Meteo cekiliyor: {start_date} -> {end_date}")
    t0 = time.time()
    client = OpenMeteoClient()
    meteo = client.get_historical(
        latitude=MERKAS_LAT, longitude=MERKAS_LON,
        start_date=start_date, end_date=end_date,
    )
    print(f"      -> tamam ({time.time() - t0:.1f}s), {len(meteo.ghi):,} saat")
    return meteo


def build_plant_spec():
    from pvquant.pipeline.forecast import PlantSpec
    plant = PlantSpec(
        p_nom_kwp=MERKAS_CAPACITY_KWP,
        latitude=MERKAS_LAT,
        longitude=MERKAS_LON,
    )
    print(f"[3/4] PlantSpec: p_nom={plant.p_nom_kwp:.0f} kWp, "
          f"tilt={plant.tilt}, azimuth={plant.azimuth}, tech={plant.module_tech}")
    return plant


def run_calibration(scada, meteo, plant, *, fit_tilt, fit_azimuth):
    from pvquant.pipeline.calibration import calibrate_from_scada
    t0 = time.time()
    result = calibrate_from_scada(
        scada=scada, historical_meteo=meteo, plant=plant,
        fit_bg=(plant.bifacial_factor > 0),
        fit_eta_bos=True,
        fit_tilt=fit_tilt, fit_azimuth=fit_azimuth,
        clean_outliers=True,
    )
    return result, time.time() - t0


def format_row(name, result, duration):
    p = result.plant
    vb = result.validation_before
    va = result.validation_after
    return (
        f"  {name}\n"
        f"    MAPE oncesi        : {vb.mape_pct:>7.2f} %\n"
        f"    MAPE sonrasi       : {va.mape_pct:>7.2f} %\n"
        f"    Iyilesme           : {result.mape_improvement_pct:>+7.2f} puan\n"
        f"    Toplam sapma sonra : {va.total_deviation_pct:>+7.2f} %\n"
        f"    eta_BoS            : {result.eta_bos:.4f}\n"
        f"    BG                 : {result.bg:.4f}\n"
        f"    tilt   30 ->       : {p.tilt:.2f}\n"
        f"    azimuth 180 ->     : {p.azimuth:.2f}\n"
        f"    Gecerli saat       : {result.n_valid_hours:,}\n"
        f"    Sure               : {duration:.1f}s"
    )


def main():
    print("=" * 68)
    print("MERKAS FIZIK KALIBRASYONU -- TESHIS")
    print("=" * 68)
    scada = build_scada_data()
    start_date = scada.power_kw.index.min().strftime("%Y-%m-%d")
    end_date = scada.power_kw.index.max().strftime("%Y-%m-%d")
    meteo = fetch_meteo(start_date, end_date)
    plant = build_plant_spec()
    print()
    print("[4/4] Uc senaryo kosturuluyor...")
    print()
    senaryolar = [
        ("A -- Baseline (fit_tilt=F, fit_azimuth=F)",
         dict(fit_tilt=False, fit_azimuth=False)),
        ("B -- Tilt ogren",
         dict(fit_tilt=True, fit_azimuth=False)),
        ("C -- Tilt+Azimuth ogren",
         dict(fit_tilt=True, fit_azimuth=True)),
    ]
    sonuclar = []
    for i, (etiket, kwargs) in enumerate(senaryolar, 1):
        print(f"  Senaryo {i}/3: {etiket}")
        try:
            result, dur = run_calibration(scada, meteo, plant, **kwargs)
            sonuclar.append((etiket, result, dur, None))
            print(f"    -> tamam, MAPE={result.validation_after.mape_pct:.2f}% ({dur:.1f}s)")
        except Exception as e:
            sonuclar.append((etiket, None, 0.0, str(e)))
            print(f"    -> HATA: {e}")
        print()
    print("=" * 68)
    print("SONUCLAR")
    print("=" * 68)
    for etiket, result, dur, err in sonuclar:
        if err is not None:
            print(f"\n  {etiket}\n    HATA: {err}")
        else:
            print()
            print(format_row(etiket, result, dur))
    print()
    print("=" * 68)
    print("YORUM")
    print("=" * 68)
    if all(s[1] is not None for s in sonuclar):
        m_a = sonuclar[0][1].validation_after.mape_pct
        m_b = sonuclar[1][1].validation_after.mape_pct
        m_c = sonuclar[2][1].validation_after.mape_pct
        print(f"  A->B: {m_a:.1f}% -> {m_b:.1f}%  (tilt etkisi: {m_a - m_b:+.1f} puan)")
        print(f"  A->C: {m_a:.1f}% -> {m_c:.1f}%  (tilt+azimuth: {m_a - m_c:+.1f} puan)")
        if m_c < 20:
            print("  OK. Fizik zemin toparlandi. Hibrit modele gecilebilir.")
        elif m_c < 60:
            print("  ~ Kismen toparlandi. Hibrit ustune binmesi anlamli.")
        else:
            print("  UYARI: Hala yuksek. Veri ya da fizik parametresi sorunu.")


if __name__ == "__main__":
    main()
