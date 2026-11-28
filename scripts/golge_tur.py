"""Faz 1 G2-1 (26.11.2026): ELLE gölge turu — tek santral, A/B/C paralel koşu, 'golge' etiketiyle arşiv. Zamanlayıcı YOK.

Kullanım (sunucuda api konteyneri ya da PVQ_DB_URL tanımlı ortam; yalnız açık onayla):
    python scripts/golge_tur.py --tenant <uuid> --plant <uuid> [--modlar A,B,C] [--kuru]
--kuru: meteo çekilir, koşular hesaplanır, arşive YAZILMAZ (run_id yok). Çıktı: tek satır JSON (yayın anı, NWP koşu zamanı, mod →
run_id/ufuk/gerçekleşen mod/geri düşüş, hatalar). Çıkış kodu: 0 tam tur, 2 kısmi/boş tur. Müşteri yüzeyleri bu koşuları görmez (G3).
"""
from __future__ import annotations

import argparse
import json
import sys


def argumanlar(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="PVQuant elle gölge turu (G2-1)")
    p.add_argument("--tenant", required=True, help="kiracı uuid")
    p.add_argument("--plant", required=True, help="santral uuid")
    p.add_argument("--modlar", default="A,B,C", help="virgülle: A,B,C")
    p.add_argument("--kuru", action="store_true", help="arşive yazma (kuru koşu)")
    a = p.parse_args(argv)
    a.modlar = tuple(m.strip().upper() for m in a.modlar.split(",") if m.strip())
    return a


def santral_getir(tenant_id: str, plant_id: str) -> dict:
    from sqlalchemy import text

    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        r = s.execute(text("SELECT id, tenant_id, name, capacity_kwp, ac_limit_kw, lat, lon, tz, params_json, archived "
                           "FROM plants WHERE id = CAST(:p AS uuid)"), {"p": plant_id}).mappings().first()
    if r is None or r["archived"]:
        raise SystemExit(f"santral yok ya da arşivli: {plant_id}")
    d = dict(r)
    d["id"], d["tenant_id"] = str(d["id"]), str(d["tenant_id"])
    return d


def main(argv=None) -> int:
    from pvquant.services.golge_service import golge_turu
    a = argumanlar(argv)
    plant = santral_getir(a.tenant, a.plant)
    t = golge_turu(a.tenant, plant, modlar=a.modlar, kaydet=not a.kuru)
    ozet = {"etiket": t.etiket, "kaydedildi": t.kaydedildi, "yayin_zamani": t.yayin_zamani.isoformat(), "meteo_kaynak": t.meteo_kaynak,
            "nwp_kosu_zamani": (str(t.nwp_kosu_zamani) if t.nwp_kosu_zamani is not None else None),
            "modlar": {m: {"run_id": s.run_id, "mode_gerceklesen": s.mode_gerceklesen, "model": s.model_adi, "ufuk_saat": s.ufuk_saat,
                           "geri_dusus": s.geri_dusus, "saat": len(s.h)} for m, s in t.sonuclar.items()},
            "hatalar": t.hatalar}
    print(json.dumps(ozet, ensure_ascii=False, default=str))
    return 0 if t.tam else 2


if __name__ == "__main__":
    sys.exit(main())
