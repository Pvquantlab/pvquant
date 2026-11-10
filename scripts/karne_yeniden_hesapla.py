"""v2.568 (10.11.2026, Faz 0 onay paketi 1) — karneyi yeni kuralla (karne_kurali.py) TÜM arşivden yeniden hesaplar.

Neden: gece_skill her gece yalnız son 10 günü yeniden yazar; kural değişince pencere içinde iki tanım karışırdı.
Ne yapar: (1) `skill_daily_eski_<tarih>` yedek tablosu (yoksa) — eski değerler kıyas için saklanır;
(2) her santral için gece_skill(plant, pencere_gun=<ilk tahminden bugüne gün>) → skill_daily UPSERT.
Çekirdek tahmin matematiğine dokunmaz; yalnız hangi koşuların karneye girdiği değişir.

Kullanım (DB SAHİBİ bağlantısıyla; sistem bağlamı tüm kiracıları dolaşır):
  PYTHONPATH=src PVQ_DB_URL=postgresql+psycopg://pvquant:***@db:5432/pvquant python scripts/karne_yeniden_hesapla.py [--yedek-yok] [--santral <plant_id>]
Çıktı: santral başına yazılan satır sayısı ve kova dağılımı. Gizli değer yazmaz.
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from pvquant.db import sistem_baglami  # noqa: E402


def yedekle() -> str:
    ad = "skill_daily_eski_" + dt.date.today().strftime("%Y%m%d")
    with sistem_baglami() as s:
        var = s.execute(text("SELECT to_regclass(:a)"), {"a": ad}).scalar()
        if var is None:
            s.execute(text(f"CREATE TABLE {ad} AS SELECT * FROM skill_daily"))
            n = s.execute(text(f"SELECT count(*) FROM {ad}")).scalar()
            print(f"yedek alındı: {ad} ({n} satır)")
        else:
            print(f"yedek zaten var: {ad}")
    return ad


def santrallar(plant_id: str | None):
    with sistem_baglami() as s:
        q = "SELECT p.id, p.tenant_id, p.name, p.capacity_kwp, p.lat, p.lon, p.tz FROM plants p"
        if plant_id:
            q += " WHERE p.id = CAST(:p AS uuid)"
        rows = s.execute(text(q), {"p": plant_id} if plant_id else {}).mappings().all()
        out = []
        for r in rows:
            ilk = s.execute(text("SELECT min(ts_utc) FROM forecast_values WHERE plant_id=:p"), {"p": r["id"]}).scalar()
            out.append((dict(r), ilk))
        return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--yedek-yok", action="store_true")
    ap.add_argument("--santral", default=None)
    a = ap.parse_args()
    if not a.yedek_yok:
        yedekle()
    from apps.worker.main import gece_skill
    for plant, ilk in santrallar(a.santral):
        if ilk is None:
            print(f"{plant['name']}: tahmin arşivi yok, atlandı"); continue
        gun = (dt.datetime.now(dt.timezone.utc) - ilk).days + 2
        gece_skill(plant, pencere_gun=gun)
        with sistem_baglami() as s:
            d = s.execute(text("SELECT horizon_bucket, count(*) FROM skill_daily WHERE plant_id=:p GROUP BY 1 ORDER BY 1"), {"p": plant["id"]}).all()
        print(f"{plant['name']}: pencere {gun} gün →", ", ".join(f"{k}:{n}" for k, n in d))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
