"""G3 — Sapma katmanı deneyi, arşivden (Faz 1 F1-02; 25.11.2026). SALT OKUNUR: hiçbir tablo yazılmaz, ayar değişmez.

Yayımlandığı anda saklanmış koşuların servis P50'si (sapma katmanı dâhil) ile aynı koşuların saf fizik P50'si (`physics_kw`,
katman öncesi) ölçüme karşı gün-bloklu eşli bootstrap ile kıyaslanır (pvquant.ext.tahmin.sapma_deneyi). Seçim/eşleştirme/gündüz
maskesi bağımsız doğrulama motorunun kendisidir (bagimsiz_dogrulama_service: kosu_sec → eslestir → degerlendirilebilir).

Kullanım (DB bağlantısı ortamdan; üretimde yalnız okuma yetkili rol):
    PYTHONPATH=src python scripts/g3_sapma_deneyi.py [--gun 30] [--kural ufuk|program|gun_oncesi|gun_ici] [--plant <uuid>]
Çıktı: santral başına kova tablosu (markdown) + öneri. Öneri karar değildir; katmanı kapatma = Settings.sapma_katmani='kapali' (onayla).
"""
from __future__ import annotations

import argparse
import sys

from sqlalchemy import text

from pvquant.db import sistem_baglami
from pvquant.ext.tahmin import sapma_deneyi as sd
from pvquant.services import bagimsiz_dogrulama_service as bd
from pvquant.services import olcum_uygunluk_service as ou


def santraller(plant_id: str | None) -> list[dict]:
    with sistem_baglami() as s:
        q = ("SELECT p.*, p.tenant_id FROM plants p JOIN tenants t ON t.id = p.tenant_id "
             "WHERE t.status = 'active' AND NOT p.archived" + (" AND p.id = CAST(:p AS uuid)" if plant_id else "") + " ORDER BY p.name")
        return [dict(r._mapping) for r in s.execute(text(q), {"p": plant_id} if plant_id else {})]


def deney(plant: dict, gun: int, kural: str):
    tz = plant.get("tz") or bd.PIYASA_TZ
    bas, bit, bas_g, bit_g = bd.donem(plant, gun)
    tahmin, _kosular = bd.tahmin_oku(plant["tenant_id"], plant["id"], bas, bit)
    saatler, _dokum = ou.saat_durumlari(plant["tenant_id"], plant, bas, bit, "scada")
    secim = bd.kosu_sec(tahmin, kural, tz)
    e = bd.degerlendirilebilir(bd.eslestir(secim, saatler, tz), float(plant["capacity_kwp"]))
    e = e[e["physics_kw"].notna()]
    tablo = sd.deney_tablosu(e, grup="kova") if kural == "ufuk" else sd.deney_tablosu(e.assign(kova=kural), grup="kova")
    return bas_g, bit_g, tablo, sd.karar(tablo)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="G3 sapma katmanı deneyi (salt okunur)")
    ap.add_argument("--gun", type=int, default=30)
    ap.add_argument("--kural", default="ufuk", choices=bd.KURALLAR)
    ap.add_argument("--plant", default=None, help="tek santral (uuid); yoksa tüm etkin santraller")
    a = ap.parse_args(argv)
    ps = santraller(a.plant)
    if not ps:
        print("etkin santral yok")
        return 1
    print(f"# G3 sapma katmanı deneyi — son {a.gun} gün, kural {a.kural} (servis P50 vs physics_kw; yayımlanmış koşular; salt okunur)")
    for p in ps:
        bas_g, bit_g, tablo, k = deney(p, a.gun, a.kural)
        print(f"\n## {p.get('name')} ({bas_g} → {bit_g}, {float(p['capacity_kwp']):.0f} kWp)")
        if tablo.empty:
            print("değerlendirilebilir saat yok (ölçüm/tahmin eşleşmedi)")
            continue
        print(sd.markdown(tablo, "kova"))
        print(f"**Öneri:** {k['oneri']} — {k['gerekce']} (kötü {k['kotu']}, iyi {k['iyi']}, belirsiz {k['belirsiz']}, yetersiz {k['yetersiz']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
