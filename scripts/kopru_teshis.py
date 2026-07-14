"""KOPRU TESHISI — UI'nin kalibrasyona gonderdigi SCADAData'yi birebir yeniden uretir.

Kullanim (repo kokunden):
    python scripts/kopru_teshis.py data/MERKAS.xlsx --tz Europe/Istanbul --kwp 4514

Ne yapar:
  1. Ayni ingestion cagrisini yapar (UI ile ayni parametrelerle)
  2. frontend/veri_yukleme.py:_kopru_scadadata_ve_gec mantigini BIREBIR uygular
  3. SCADAData'nin roentgenini basar: tz, aralik, kolon kolon gunduz ortalamalari
  4. --meteo verilirse calibrate_from_scada'yi kosturur (ag gerekir)

Boylece 'UI yolu' terminalde kosulabilir hale gelir ve teshis betiginin
(%23 veren) SCADAData'siyla alan alan kiyaslanabilir.
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
sys.path.insert(0, "src")
import pandas as pd


def kopru_ile_scadadata(dosya: str, tz: str, kwp: float, lat: float, lon: float):
    """UI koprusunun birebir kopyasi (st.* cagrilari haric)."""
    from pvquant.io.ingestion.pipeline import ingest_file
    from pvquant.io.scada import SCADAData

    res = ingest_file(dosya, capacity_kwp=kwp, latitude=lat, longitude=lon,
                      source_timezone=tz)
    clean = res.data if hasattr(res, "data") else res[0]
    print(f"[ingestion] kolonlar          : {list(clean.columns)}")
    rep = getattr(res, "report", None)
    if rep is not None:
        for attr in ("n_total", "n_valid"):
            v = getattr(rep, attr, None)
            if v is not None:
                print(f"[ingestion] {attr:<18}: {v}")

    df = clean.set_index("timestamp") if "timestamp" in clean.columns else clean
    if "flag" in df.columns:
        n0 = len(df)
        df = df[df["flag"] == "valid"]
        print(f"[kopru] valid filtresi        : {n0} -> {len(df)} satir")

    if isinstance(df.index, pd.DatetimeIndex) and len(df) > 1:
        full = pd.date_range(df.index.min(), df.index.max(), freq="1h", tz=df.index.tz)
        df = df.reindex(full)
        df.index.name = "timestamp"
        import pvlib
        sol = pvlib.solarposition.get_solarposition(df.index, lat, lon)
        night = (sol["apparent_elevation"] < -3.0).values
        df.loc[night & df["power_kw"].isna().values, "power_kw"] = 0.0

    def _opt(c):
        return df[c] if c in df.columns else None

    scada = SCADAData(
        power_kw=df["power_kw"],
        energy_kwh=_opt("energy_kwh"),
        poa_irradiance=_opt("poa_global"),
        temp_ambient=_opt("t_air"),
        temp_module=_opt("t_module"),
        wind_speed=_opt("wind_speed"),
        plant_name=Path(dosya).stem,
        timestep_minutes=60,
    )
    return scada, df


def rontgen(scada, lat: float, kwp: float):
    """SCADAData'nin kalibrasyonu ilgilendiren her alanini basar."""
    import pvlib
    p = scada.power_kw
    idx = p.index
    print("\n================ SCADAData RONTGENI ================")
    print(f"index tz        : {idx.tz}")
    print(f"aralik          : {idx.min()}  ->  {idx.max()}   ({len(idx)} satir)")
    # gunduz maskesi (guneş yuksekligi > 10) — 'olu sensor' testinin kalbi
    sol = pvlib.solarposition.get_solarposition(idx, lat, scada_lon_tahmini(idx))
    gunduz = sol["apparent_elevation"].values > 10.0
    print(f"gunduz saati    : {int(gunduz.sum())}")
    print(f"\n{'seri':<14}{'var?':<6}{'notna':<8}{'GUNDUZ ort':<12}{'max':<10}")
    for ad in ("power_kw", "poa_irradiance", "temp_ambient", "temp_module", "wind_speed", "energy_kwh"):
        s = getattr(scada, ad)
        if s is None:
            print(f"{ad:<14}{'YOK':<6}")
            continue
        g = s[gunduz]
        print(f"{ad:<14}{'VAR':<6}{int(s.notna().sum()):<8}"
              f"{g.mean():<12.1f}{s.max():<10.1f}")
    # KIRMIZI BAYRAK KONTROLLERI
    print("\n---- kirmizi bayrak kontrolleri ----")
    poa = scada.poa_irradiance
    if poa is not None:
        poa_gunduz = poa[gunduz].mean()
        if pd.notna(poa_gunduz) and poa_gunduz < 100:
            print(f"!! POA gunduz ortalamasi {poa_gunduz:.1f} W/m2 — OLU/YANLIS SENSOR."
                  f" measured_poa fizigi sifira cekiyor olabilir. Kolon eslemesini kontrol et.")
        else:
            print(f"POA gunduz ortalamasi {poa_gunduz:.1f} W/m2 — makul.")
    else:
        print("POA yok — fizik Perez'e duser (sifir uretmez).")
    pmax = p.max()
    oran = pmax / kwp
    if oran < 0.05:
        print(f"!! power max {pmax:.2f} kW = kapasitenin %{oran*100:.1f}'i — BIRIM 1000x kucuk olabilir (MW->kW hatasi).")
    elif oran > 5:
        print(f"!! power max {pmax:.0f} kW = kapasitenin {oran:.0f} kati — BIRIM 1000x buyuk olabilir (W->kW hatasi).")
    else:
        print(f"power max {pmax:.0f} kW — kapasiteyle tutarli.")
    # ogle ornekleri (yerel algi icin ilk 3 gunun UTC 09-10'u ~ TR ogle)
    print("\nornek satirlar (ilk 3 gun, gunduz):")
    day_idx = idx[gunduz][:72:24] if gunduz.any() else []
    for i in day_idx:
        pv = poa.loc[i] if poa is not None else float("nan")
        print(f"  {i}   power={p.loc[i]:.1f}   poa={pv}")
    print("====================================================\n")


def scada_lon_tahmini(idx):
    # rontgen fonksiyonu lon'a yalniz gunduz maskesi icin ihtiyac duyar;
    # cagiran zaten dogru lon'u main'den geciriyor (asagida monkeypatch).
    return scada_lon_tahmini.lon


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dosya")
    ap.add_argument("--tz", default="Europe/Istanbul")
    ap.add_argument("--kwp", type=float, default=4514.0)
    ap.add_argument("--lat", type=float, default=37.87)
    ap.add_argument("--lon", type=float, default=32.49)
    ap.add_argument("--kalibre", action="store_true",
                    help="Open-Meteo cekip calibrate_from_scada da kostur (ag gerekir)")
    a = ap.parse_args()
    scada_lon_tahmini.lon = a.lon

    scada, _df = kopru_ile_scadadata(a.dosya, a.tz, a.kwp, a.lat, a.lon)
    rontgen(scada, a.lat, a.kwp)

    if a.kalibre:
        from pvquant.io.meteo import OpenMeteoClient
        from pvquant.pipeline.calibration import calibrate_from_scada
        from pvquant.pipeline.forecast import PlantSpec
        start = scada.power_kw.index.min().strftime("%Y-%m-%d")
        end = scada.power_kw.index.max().strftime("%Y-%m-%d")
        meteo = OpenMeteoClient().get_historical(
            latitude=a.lat, longitude=a.lon, start_date=start, end_date=end)
        plant = PlantSpec(p_nom_kwp=a.kwp, latitude=a.lat, longitude=a.lon,
                          tilt=20.0, azimuth=180.0, bifacial_factor=0.7)
        r = calibrate_from_scada(scada=scada, historical_meteo=meteo, plant=plant,
                                 fit_bg=True, fit_eta_bos=True, clean_outliers=True)
        print(f"\nKALIBRASYON: eta_bos={r.eta_bos:.3f}")
        for n in r.notes:
            print("  -", n)


if __name__ == "__main__":
    main()