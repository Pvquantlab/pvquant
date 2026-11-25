"""G4 hazırlık — Golden 33 PVDAQ dakikalık CSV dizinini saatlik ölçüm CSV'sine çevirir (salt okunur kaynak; DB yazmaz, ağ yok).
Kullanım: PYTHONPATH=src python scripts/g4_golden33_donustur.py <giris_dizini> <cikti.csv> [--tz Etc/GMT+7]
Çıktı: ts_utc,power_kw,energy_kwh,poa_wm2,t_air,t_module,dc_power_kw,kapsama_dk + yanında <cikti>.ozet.json."""
from __future__ import annotations

import argparse
import json
import sys

from pvquant.ext.kaynak import pvdaq


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="PVDAQ dakikalık → saatlik")
    ap.add_argument("giris")
    ap.add_argument("cikti")
    ap.add_argument("--tz", default=pvdaq.GOLDEN33["tz"])
    a = ap.parse_args(argv)
    saat, ozet = pvdaq.dizin_donustur(a.giris, tz=a.tz)
    if saat.empty:
        print("girdi yok")
        return 1
    saat.to_csv(a.cikti, float_format="%.4f")
    with open(a.cikti + ".ozet.json", "w", encoding="utf-8") as f:
        json.dump(ozet, f, ensure_ascii=False, indent=1)
    print(json.dumps(ozet, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
