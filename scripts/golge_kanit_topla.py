"""Gölge kanıt toplayıcı (SALT OKUNUR; 28.11.2026). Kullanım:
    PVQ_DB_URL=... PYTHONPATH=src python scripts/golge_kanit_topla.py --santral "Karapınar RT-2579" --bas 2026-12-01 --bit 2027-01-01 [--cikti dosya.json]
Yayın (müşteri, Mod B) ve gölge (etiket='golge') koşularını aynı gerçekleşen ve aynı maskeyle kıyaslar (golge_service.golge_degerlendir:
24-48 / 00-24 kovaları; WMAPE, nMAE, RMSE, sapma, PICP80, bant) ve provenans denetimi yapar: her gölge koşusunun nwp_kosu_zamani'ı aynı
günün yayın koşusuyla eşit mi, run_at (yayın zamanı) yayın koşusundan sonra mı, gerçekleşen mod C ise artefakt_sha16 dolu mu, yazılım
sürümü hangisi. Eşikler GOLGE_ESIKLER (Aralık protokolüyle aynı) yalnız bilgi amaçlı; «kabul» bu betikte verilmez. DB'ye yazmaz.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pvquant.db import sistem_baglami  # noqa: E402
from pvquant.services import golge_service as gs  # noqa: E402
from pvquant.services.karne_kurali import ETIKET_GOLGE, yayin_kosu_sql  # noqa: E402


def santral_bul(ad: str) -> dict:
    with sistem_baglami() as s:
        r = s.execute(text("SELECT id, tenant_id, name, capacity_kwp, ac_limit_kw, lat, lon, tz FROM plants WHERE name = :a"), {"a": ad}).mappings().first()
    if r is None:
        raise SystemExit(f"santral yok: {ad}")
    return dict(r)


def provenans(plant: dict, bas, bit) -> dict:
    """Gün bazında: yayın koşusu (nwp_kosu_zamani, run_at) ↔ gölge koşuları (mode, nwp_kosu_zamani, run_at, artefakt_sha16, yazilim_surumu)."""
    with sistem_baglami() as s:
        df = pd.read_sql(text(
            "SELECT r.id, r.run_at, r.etiket, r.mode, r.model, r.nwp_kosu_zamani, r.artefakt_sha16, r.yazilim_surumu, r.satir_sayisi, "
            " (r.meteo_ozet_json->>'geri_dusus') AS geri_dusus "
            "FROM forecast_runs r WHERE r.plant_id = :p AND r.run_at >= :a AND r.run_at < :b "
            " AND (r.etiket = :g OR (" + yayin_kosu_sql("r", elle_dahil=False) + " AND COALESCE(r.etiket,'yayin') = 'yayin')) ORDER BY r.run_at"),
            s.connection(), params={"p": plant["id"], "a": pd.Timestamp(bas).to_pydatetime(), "b": pd.Timestamp(bit).to_pydatetime(), "g": ETIKET_GOLGE})
    if df.empty:
        return {"gun": 0, "not": "koşu yok"}
    df["gun"] = pd.to_datetime(df["run_at"], utc=True).dt.tz_convert("Europe/Istanbul").dt.date.astype(str)
    gunler = []
    for gun, g in df.groupby("gun"):
        yayin = g[g["etiket"] != ETIKET_GOLGE]
        golge = g[g["etiket"] == ETIKET_GOLGE]
        y_nwp = pd.Timestamp(yayin["nwp_kosu_zamani"].iloc[-1]) if not yayin.empty else None
        satir = {"gun": gun, "yayin_kosu": len(yayin), "yayin_mode": sorted(yayin["mode"].unique().tolist()), "yayin_nwp": str(y_nwp),
                 "golge_kosu": len(golge), "golge_modlar": sorted(golge["mode"].unique().tolist()),
                 "ayni_nwp": bool(not golge.empty and y_nwp is not None and all(pd.Timestamp(x) == y_nwp for x in golge["nwp_kosu_zamani"])),
                 "golge_yayindan_sonra": bool(not golge.empty and not yayin.empty and golge["run_at"].min() >= yayin["run_at"].max()),
                 "c_sha_dolu": bool(all(sha for sha in golge.loc[golge["mode"] == "C", "artefakt_sha16"])) if (golge["mode"] == "C").any() else None,
                 "yazilim": sorted(set(g["yazilim_surumu"].dropna().tolist())), "geri_dusus": sorted(set(g["geri_dusus"].dropna().tolist()))}
        gunler.append(satir)
    return {"gun": len(gunler), "ayni_nwp_gun": sum(1 for x in gunler if x["ayni_nwp"]), "golge_gun": sum(1 for x in gunler if x["golge_kosu"]), "gunler": gunler}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--santral", required=True)
    ap.add_argument("--bas", required=True)
    ap.add_argument("--bit", required=True)
    ap.add_argument("--cikti")
    a = ap.parse_args()
    plant = santral_bul(a.santral)
    bas, bit = pd.Timestamp(a.bas, tz="Europe/Istanbul"), pd.Timestamp(a.bit, tz="Europe/Istanbul")
    sonuc = {"uretildi": pd.Timestamp.now(tz="Europe/Istanbul").isoformat(), "santral": plant["name"], "plant_id": str(plant["id"]),
             "donem_tsi": [str(bas), str(bit)], "esikler": gs.GOLGE_ESIKLER, "kanit_turu": "golge (ileriye dönük: koşu gerçekleşmeden önce yazıldı)",
             "metrikler": gs.golge_degerlendir(plant["tenant_id"], plant, bas, bit), "provenans": provenans(plant, bas, bit),
             "not": "kabul kararı bu betikte verilmez; ≥30 gün ve donmuş eşiklerle ayrı hesap"}
    js = json.dumps(sonuc, ensure_ascii=False, indent=1, default=str)
    if a.cikti:
        Path(a.cikti).write_text(js)
    print(js)


if __name__ == "__main__":
    main()
