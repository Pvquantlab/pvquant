"""G4-P1 — retrospektif kalibrasyon deneyi (DB yok, yazma yok). Golden 33 2018 için:
  PYTHONPATH=src python scripts/g4_retrospektif_kalibrasyon.py --scada g4/golden33_2018_saatlik_utc.csv --meteo <meteo.csv> [--cikti sonuc.json]
meteo.csv: ts_utc,ghi,temp_air[,wind_speed_10m] (UTC). --pvgis-era5 YIL verilirse meteo PVGIS 5.3 ERA5'ten çekilir (AĞ; kayıtsız, açık) ve
--meteo yoluna CSV olarak yazılır. Santral: --plant golden33 (ext/kaynak/pvdaq.GOLDEN33)."""
from __future__ import annotations

import argparse
import json
import sys

import pandas as pd

from pvquant.ext.kaynak import pvdaq
from pvquant.services import retrospektif_kalibrasyon as rk


def _pvgis_era5(lat: float, lon: float, yil: int) -> pd.DataFrame:
    from pvquant.ext.kaynak.uydu_isinim import pvgis_saatlik
    c = pvgis_saatlik(lat, lon, yil, yil, veri_tabani="PVGIS-ERA5")
    df = c.df.copy()
    kol = {k: v for k, v in (("ghi", "ghi"), ("temp_air", "temp_air"), ("wind_speed_10m", "wind_speed_10m")) if k in df.columns}
    return df[list(kol)].rename(columns=kol)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="G4 retrospektif kalibrasyon (yazma yok)")
    ap.add_argument("--scada", required=True)
    ap.add_argument("--meteo", required=True)
    ap.add_argument("--plant", default="golden33")
    ap.add_argument("--pvgis-era5", type=int, default=None)
    ap.add_argument("--cikti", default=None)
    ap.add_argument("--hibrit", action="store_true", help="Mod C (hibrit) retrospektif kapısı da denensin")
    a = ap.parse_args(argv)
    plant = {"id": None, "name": pvdaq.GOLDEN33["ad"], "capacity_kwp": pvdaq.GOLDEN33["capacity_kwp"], "lat": pvdaq.GOLDEN33["lat"],
             "lon": pvdaq.GOLDEN33["lon"], "tz": pvdaq.GOLDEN33["tz"], "tilt": pvdaq.GOLDEN33["tilt"], "azimuth": pvdaq.GOLDEN33["azimuth"],
             "panel_tech": pvdaq.GOLDEN33["panel_tech"], "ac_limit_kw": None, "params_json": {}}
    if a.plant != "golden33":
        print("yalnız golden33 tanımlı")
        return 2
    if a.pvgis_era5:
        m = _pvgis_era5(plant["lat"], plant["lon"], a.pvgis_era5)
        m.to_csv(a.meteo, index_label="ts_utc")
        print(f"PVGIS ERA5 {a.pvgis_era5}: {len(m)} saat → {a.meteo}")
    scada = pd.read_csv(a.scada, index_col="ts_utc", parse_dates=["ts_utc"])
    meteo_df = pd.read_csv(a.meteo, index_col="ts_utc", parse_dates=["ts_utc"])
    meteo = rk.meteo_cercevesi(meteo_df, plant["lat"], plant["lon"], kaynak=f"pvgis-era5-{a.pvgis_era5}" if a.pvgis_era5 else "csv")
    sonuc = rk.kalibre_et_retrospektif(scada, meteo, plant, meteo_kaynak=meteo.kaynak, hibrit=a.hibrit)
    metin = json.dumps(sonuc, ensure_ascii=False, indent=1, default=str)
    if a.cikti:
        with open(a.cikti, "w", encoding="utf-8") as f:
            f.write(metin)
    print(metin[:1500])
    return 0


if __name__ == "__main__":
    sys.exit(main())
