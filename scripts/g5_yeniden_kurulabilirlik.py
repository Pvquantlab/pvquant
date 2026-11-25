"""G5-P3 — son N günün yayın koşuları için yeniden kurulabilirlik denetimi (SALT OKUNUR; yazma yok, ayar değişmez).
Kullanım: PYTHONPATH=src python scripts/g5_yeniden_kurulabilirlik.py [--gun 7]
Çıktı: santral × durum sayımı + eksik/kısmi nedenlerinin dağılımı. Öneri değil, envanter."""
from __future__ import annotations

import argparse
import collections
import sys

from sqlalchemy import text

from pvquant.db import sistem_baglami
from pvquant.services import yeniden_kurma_service as yk


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="G5 yeniden kurulabilirlik (salt okunur)")
    ap.add_argument("--gun", type=int, default=7)
    a = ap.parse_args(argv)
    with sistem_baglami() as s:
        rows = [dict(r._mapping) for r in s.execute(text(
            "SELECT r.id, r.tenant_id, p.name FROM forecast_runs r JOIN plants p ON p.id = r.plant_id "
            "WHERE r.run_at >= now() - make_interval(days => :g) AND COALESCE(r.etiket, 'yayin') IN ('yayin', 'gun_ici') ORDER BY r.run_at"), {"g": a.gun})]
    if not rows:
        print("koşu yok")
        return 1
    sayim, nedenler = collections.Counter(), collections.Counter()
    for r in rows:
        k = yk.kurulabilirlik(r["tenant_id"], r["id"])
        if k is None:
            continue
        sayim[(r["name"], k["durum"])] += 1
        for n in k["eksik"] + k["kismi"]:
            nedenler[n.split(" (")[0]] += 1
    print(f"# G5 yeniden kurulabilirlik — son {a.gun} gün, {len(rows)} yayın koşusu")
    for (ad, durum), n in sorted(sayim.items()):
        print(f"- {ad}: {durum} {n}")
    print("\n## Eksik / kısmi nedenleri")
    for n, c in nedenler.most_common():
        print(f"- {c}× {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
