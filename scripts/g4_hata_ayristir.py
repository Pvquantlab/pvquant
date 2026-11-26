"""G4-P4 (26.11.2026) — retrospektif HATA AYRIŞTIRMA: yüksek WMAPE ışınım mı, santral mı, mevsim mi? (salt okunur; DB/ağ yok)
Kullanım: PYTHONPATH=src python scripts/g4_hata_ayristir.py --scada golden33_2022_saatlik_utc.csv --meteo golden33_2022_pvgis_era5_meteo_utc.csv --cikti tani.json
Ölçülmüş POA yalnız tanı referansıdır; meteo yolu metriklerine girmez. Eşikler değiştirilmez; hüküm metindir."""
from __future__ import annotations

import argparse
import json
import sys

import pandas as pd

from pvquant.ext.kaynak.pvdaq import GOLDEN33
from pvquant.services import retrospektif_kalibrasyon as rk


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="G4 hata ayrıştırma")
    ap.add_argument("--scada", required=True)
    ap.add_argument("--meteo", required=True)
    ap.add_argument("--cikti", required=True)
    ap.add_argument("--santral-json", default=None, help="{lat, lon, tilt, azimuth, capacity_kwp}; yoksa Golden 33")
    a = ap.parse_args(argv)
    if a.santral_json:
        with open(a.santral_json, encoding="utf-8") as f:
            plant = json.load(f)
    else:
        plant = {**GOLDEN33, "name": GOLDEN33["ad"]}
    m = pd.read_csv(a.scada, index_col="ts_utc", parse_dates=True)
    e = pd.read_csv(a.meteo, index_col="ts_utc", parse_dates=True)
    out = rk.hata_ayristir(m, e, plant)
    out["girdi"] = {"scada": a.scada.rsplit("/", 1)[-1], "meteo": a.meteo.rsplit("/", 1)[-1], "santral": plant.get("name") or plant.get("ad")}
    with open(a.cikti, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    i, s, mv = out["isinim"], out["santral"], out["mevsim"]
    print(f"ışınım: meteo→POA WMAPE %{i['wmape_pct']} sapma %{i['bias_pct']} | berrak %{i['berraklik_olculen']['berrak']['wmape_pct']} bulutlu sapma %{i['berraklik_olculen']['bulutlu']['bias_pct']}")
    print(f"zaman varyantları: {i['zaman_varyantlari']}")
    print(f"santral: PR medyan {s['pr_medyan']} (sıc. düz. {s['pr_sicaklik_duzeltmeli_medyan']}), PR çökme {s['pr_cokme_saat']} sa")
    print(f"holdout {mv['holdout']['bas'][:10]}→: meteo yolu %{mv['holdout']['meteo_yolu']} | ölçülmüş POA %{mv['holdout']['olculmus_poa']} | eğitim: %{mv['egitim']['meteo_yolu']} / %{mv['egitim']['olculmus_poa']}")
    print(f"hüküm: {out['hukum']['baskin_bilesen']} — {out['hukum']['aciklama']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
