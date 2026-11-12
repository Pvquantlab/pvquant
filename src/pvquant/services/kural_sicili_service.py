"""v2.600 (Faz 4 F4-F) — kural sicili anlık görüntüsü: sicil (kod) → `kural_sicili_anlik` (yalnız ekleme, sha16 benzersiz)."""
from __future__ import annotations

import json
from datetime import date

from sqlalchemy import text

from pvquant.db import sistem_baglami
from pvquant.ext.turkiye import kural_sicili as ks


def anlik_kaydet() -> dict:
    """Sicilin sha16'sı tabloda yoksa satır ekler. Döner {sha16, yeni, id}. Gece işi ve API açılışında çağrılır; idempotent."""
    sha = ks.sicil_sha16()
    from pvquant.surum import yazilim_surumu
    with sistem_baglami() as s:
        var = s.execute(text("SELECT id FROM kural_sicili_anlik WHERE sha16 = :s"), {"s": sha}).scalar()
        if var:
            return {"sha16": sha, "yeni": False, "id": int(var)}
        kid = s.execute(text(
            "INSERT INTO kural_sicili_anlik(sha16, sicil_surumu, kayit_sayisi, sicil_json, yazilim_surumu) "
            "VALUES(:s, :sv, :n, CAST(:j AS jsonb), :ys) RETURNING id"),
            {"s": sha, "sv": ks.SURUM, "n": len(ks.SICIL), "j": json.dumps(ks.tablo(), ensure_ascii=False, default=str), "ys": yazilim_surumu()}).scalar()
    return {"sha16": sha, "yeni": True, "id": int(kid)}


def anlik_listesi(n: int = 20) -> list[dict]:
    with sistem_baglami() as s:
        rows = s.execute(text("SELECT id, sha16, sicil_surumu, kayit_sayisi, yazilim_surumu, olusturma FROM kural_sicili_anlik ORDER BY id DESC LIMIT :n"), {"n": n}).mappings().all()
    return [{**dict(r), "olusturma": r["olusturma"].isoformat() if r["olusturma"] else None} for r in rows]


def anlik_getir(sha16: str) -> dict | None:
    with sistem_baglami() as s:
        r = s.execute(text("SELECT sha16, sicil_surumu, kayit_sayisi, sicil_json, yazilim_surumu, olusturma FROM kural_sicili_anlik WHERE sha16 = :s"), {"s": sha16}).mappings().first()
    if r is None:
        return None
    return {**dict(r), "olusturma": r["olusturma"].isoformat() if r["olusturma"] else None}


def gece_kural_sicili(_plant=None) -> dict:
    """Gece işi (küresel): anlık görüntü; sonuç jobs_log.sonuc_json'a düşer."""
    r = anlik_kaydet()
    return {"durum": "ok", **r, "sicil_surumu": ks.SURUM, "kayit": len(ks.SICIL)}


def meta_damgasi(tarih: date | None = None) -> dict:
    """Sonuç meta'ları için: {kural_sicili_sha, kural_sicili_surumu}."""
    return {"kural_sicili_sha": ks.sicil_sha16(), "kural_sicili_surumu": ks.SURUM}
