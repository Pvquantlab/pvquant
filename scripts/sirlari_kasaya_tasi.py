"""v2.570 (10.11.2026, Faz 0 onay paketi 2) — düz metin TOTP ve webhook sırlarını kasaya (zarf) taşır; `--geri` ile düz metne döndürür.

Kullanım (DB SAHİBİ bağlantısıyla; PVQ_KEK ortamda tanımlı olmalı):
  PYTHONPATH=src PVQ_DB_URL=postgresql+psycopg://pvquant:***@db:5432/pvquant PVQ_KEK=... python scripts/sirlari_kasaya_tasi.py [--geri] [--kuru]
İleri: her tabloda düz sütunu dolu, zarfı boş satırlar zarflanır, düz sütun NULL yapılır; önce ilk kayıt çözülerek doğrulanır.
Geri: zarfı dolu satırlar çözülüp düz sütuna yazılır, zarf NULL. Yalnız satır sayıları yazdırılır; sır değeri hiçbir zaman yazılmaz.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import text  # noqa: E402

from pvquant.db import sistem_baglami  # noqa: E402
from pvquant.guvenlik import sir  # noqa: E402

HEDEFLER = [
    # (tablo, kimlik sütunu, düz sütun, zarf sütunu, aad üretici)
    ("users", "id", "totp_secret", "totp_zarf", lambda r: f"users:{r['id']}:totp"),
    ("platform_kullanicilar", "id", "totp_secret", "totp_zarf", lambda r: f"platform:{r['id']}:totp"),
    ("webhooks", "id", "secret", "secret_zarf", lambda r: f"webhooks:{r['tenant_id']}:{r['id']}"),
]


def ileri(kuru: bool) -> None:
    if not sir.kasa_acik():
        raise SystemExit("PVQ_KEK tanımlı değil: dönüşüm yapılmaz")
    with sistem_baglami() as s:
        for tablo, kid, duz, zarf, aad in HEDEFLER:
            ek = ", tenant_id" if tablo == "webhooks" else ""
            rows = s.execute(text(f"SELECT {kid} AS id{ek}, {duz} AS duz FROM {tablo} WHERE {duz} IS NOT NULL AND {zarf} IS NULL")).mappings().all()
            n = 0
            for r in rows:
                z, _ = sir.sakla(r["duz"], aad(r))
                assert z is not None
                assert sir.oku(z, None, aad(r)) == r["duz"], "zarf doğrulaması başarısız"   # yazmadan önce çöz
                if not kuru:
                    s.execute(text(f"UPDATE {tablo} SET {zarf}=CAST(:z AS jsonb), {duz}=NULL WHERE {kid}=:i"), {"z": json.dumps(z), "i": r["id"]})
                n += 1
            print(f"{tablo}: {n} satır {'zarflanırdı (kuru)' if kuru else 'zarflandı'}")


def geri(kuru: bool) -> None:
    with sistem_baglami() as s:
        for tablo, kid, duz, zarf, aad in HEDEFLER:
            ek = ", tenant_id" if tablo == "webhooks" else ""
            rows = s.execute(text(f"SELECT {kid} AS id{ek}, {zarf} AS zarf FROM {tablo} WHERE {zarf} IS NOT NULL")).mappings().all()
            n = 0
            for r in rows:
                d = sir.oku(r["zarf"], None, aad(r))
                if not kuru:
                    s.execute(text(f"UPDATE {tablo} SET {duz}=:d, {zarf}=NULL WHERE {kid}=:i"), {"d": d, "i": r["id"]})
                n += 1
            print(f"{tablo}: {n} satır {'çözülürdü (kuru)' if kuru else 'düz metne döndü'}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--geri", action="store_true")
    ap.add_argument("--kuru", action="store_true", help="yazmadan say")
    a = ap.parse_args()
    (geri if a.geri else ileri)(a.kuru)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
