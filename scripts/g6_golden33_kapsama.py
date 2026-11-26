"""G6-P1 (26.11.2026) — Golden 33 saatlik ölçüm CSV'leri (g4_golden33_donustur çıktısı) → yıl × mevsim kapsama tablosu (JSON + tablo).
Kullanım: PYTHONPATH=src python scripts/g6_golden33_kapsama.py --cikti kapsama.json golden33_2014_saatlik_utc.csv golden33_2015_saatlik_utc.csv …
Yıl dosya adındaki 4 haneli sayıdan okunur (--yil ile tek dosya için zorlanabilir). Salt okunur; DB/ağ yok. Eşik yalnız raporlanır (G4 kapısı DJF ≥ %95)."""
from __future__ import annotations

import argparse
import json
import re
import sys

import pandas as pd

from pvquant.ext.kaynak import pvdaq


def yil_bul(yol: str) -> int | None:
    m = re.search(r"(19|20)\d{2}", yol.rsplit("/", 1)[-1])
    return int(m.group(0)) if m else None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Golden 33 mevsim kapsaması")
    ap.add_argument("dosyalar", nargs="+")
    ap.add_argument("--cikti", required=True)
    ap.add_argument("--yil", type=int, default=None, help="tek dosya için yılı zorla")
    ap.add_argument("--tz", default=pvdaq.GOLDEN33["tz"])
    a = ap.parse_args(argv)
    satirlar = []
    for yol in a.dosyalar:
        yil = a.yil or yil_bul(yol)
        if yil is None:
            print(f"yıl bulunamadı: {yol}", file=sys.stderr)
            return 2
        df = pd.read_csv(yol, index_col="ts_utc", parse_dates=True)
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        k = pvdaq.mevsim_kapsama(df, yil, tz=a.tz)
        k["dosya"] = yol.rsplit("/", 1)[-1]
        satirlar.append(k)
    satirlar.sort(key=lambda r: r["yil"])
    with open(a.cikti, "w", encoding="utf-8") as f:
        json.dump(satirlar, f, ensure_ascii=False, indent=1)
    print("yıl   saat  geçerli  gen%   DJF%   MAM%   JJA%   SON%  DJF≥95  maks_kW   kWh")
    for r in satirlar:
        print(f"{r['yil']}  {r['saat']:5d}  {r['gecerli']:7d}  {r['gecerli_pct']:5.1f}  {r['djf_pct']:5.1f}  {r['mam_pct']:5.1f}  {r['jja_pct']:5.1f}  "
              f"{r['son_pct']:5.1f}  {'evet' if r['djf_uygun'] else 'HAYIR':>6}  {r['maks_kw'] if r['maks_kw'] is not None else '-':>7}  {r['kwh'] if r['kwh'] is not None else '-':>5}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
