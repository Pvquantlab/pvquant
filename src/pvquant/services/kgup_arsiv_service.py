"""v2.502 — KGÜP sürüm arşivi (F-06): indirilen her KGÜP/EAK dosyası değiştirilemez kayıt; aynı içerik (SHA-256) yeniden
indirilince yeni satır açılmaz (son sürüm döner), içerik değiştiyse sürüm numarası artar. Yaptırımdan koruma vaadi değil, kayıt tutma.

Kayıt: kgup_service.uret() çıktısından (csv metni BOM'suz; baytlar = utf-8-sig, API'nin gönderdiğiyle ve sha256 ile birebir).
Okuma: listele (gün/son N), getir (yeniden indirme — bayt bayt aynı dosya). Silme/güncelleme yok (DB yetkisi de yok).
"""
from __future__ import annotations

import hashlib
import json
from datetime import date

from sqlalchemy import text

from pvquant.db import tenant_baglami


def baytlar(r: dict) -> bytes:
    """uret() çıktısının dosya baytları (BOM dâhil) — sha256 alanıyla aynı kaynak."""
    return r["csv"].encode("utf-8-sig")


def kaydet(tenant_id, plant_id, r: dict, indiren=None) -> dict:
    """uret() çıktısını arşivler. Dönüş: {id, surum, sha256, yeni(bool)}. Aynı gün aynı sha → mevcut kayıt (yeni=False)."""
    b = baytlar(r); sha = hashlib.sha256(b).hexdigest()
    if r.get("sha256") and r["sha256"] != sha:
        raise ValueError("sha256 uyuşmuyor: yanıt ile dosya baytları farklı")
    gun = date.fromisoformat(r["gun"]); kosu = r.get("kosu") or {}
    with tenant_baglami(tenant_id) as s:
        var = s.execute(text("SELECT id, surum FROM kgup_surum WHERE plant_id=:p AND teslim_gunu=:g AND sha256=:h ORDER BY surum DESC LIMIT 1"),
                        {"p": plant_id, "g": gun, "h": sha}).first()
        if var:
            return {"id": str(var.id), "surum": int(var.surum), "sha256": sha, "yeni": False}
        son = s.execute(text("SELECT coalesce(max(surum), 0) FROM kgup_surum WHERE plant_id=:p AND teslim_gunu=:g"), {"p": plant_id, "g": gun}).scalar()
        surum = int(son or 0) + 1
        eak = r.get("eak") or {}
        sid = s.execute(text(
            "INSERT INTO kgup_surum(tenant_id, plant_id, teslim_gunu, surum, kantil, run_id, run_at, kesim, eak_mw, eak_kaynak, toplam_mwh, "
            " sha256, dosya, dosya_adi, sablon_json, indiren) "
            "VALUES(:t, :p, :g, :s, :k, :rid, :rat, :kes, :eak, :eakk, :top, :h, :d, :ad, CAST(:sab AS jsonb), :u) RETURNING id"),
            {"t": tenant_id, "p": plant_id, "g": gun, "s": surum, "k": r.get("kantil", "p50"),
             "rid": kosu.get("run_id"), "rat": kosu.get("run_at"), "kes": kosu.get("kesim"),
             "eak": eak.get("eak_mw"), "eakk": eak.get("kaynak"), "top": r.get("toplam_mwh"),
             "h": sha, "d": b, "ad": r.get("dosya_adi", "KGUP.csv"), "sab": json.dumps(r.get("sablon") or {}, ensure_ascii=False), "u": indiren}).scalar()
    return {"id": str(sid), "surum": surum, "sha256": sha, "yeni": True}


def listele(tenant_id, plant_id, gun: date | None = None, n: int = 30) -> list[dict]:
    """Sürüm geçmişi (yeni → eski). gun verilirse yalnız o teslim günü."""
    with tenant_baglami(tenant_id) as s:
        rows = s.execute(text(
            "SELECT k.id, k.teslim_gunu, k.surum, k.kantil, k.run_id, k.run_at, k.kesim, k.eak_mw, k.eak_kaynak, k.toplam_mwh, k.sha256, k.dosya_adi, "
            " k.olusturma, u.email AS indiren_eposta, octet_length(k.dosya) AS bayt "
            "FROM kgup_surum k LEFT JOIN users u ON u.id = k.indiren "
            "WHERE k.plant_id=:p AND (CAST(:g AS date) IS NULL OR k.teslim_gunu = CAST(:g AS date)) ORDER BY k.teslim_gunu DESC, k.surum DESC LIMIT :n"),
            {"p": plant_id, "g": gun, "n": n}).fetchall()
    return [{"id": str(r.id), "teslim_gunu": r.teslim_gunu.isoformat(), "surum": int(r.surum), "kantil": r.kantil,
             "run_id": str(r.run_id) if r.run_id else None, "run_at": r.run_at.isoformat() if r.run_at else None,
             "kesim": r.kesim.isoformat() if r.kesim else None, "eak_mw": r.eak_mw, "eak_kaynak": r.eak_kaynak, "toplam_mwh": r.toplam_mwh,
             "sha256": r.sha256, "dosya_adi": r.dosya_adi, "olusturma": r.olusturma.isoformat(), "indiren": r.indiren_eposta, "bayt": int(r.bayt)}
            for r in rows]


def getir(tenant_id, plant_id, surum_id) -> dict | None:
    """Arşivdeki dosya — bayt bayt aynı (sha256 doğrulanır)."""
    with tenant_baglami(tenant_id) as s:
        r = s.execute(text("SELECT dosya, dosya_adi, sha256, surum, teslim_gunu FROM kgup_surum WHERE id=:i AND plant_id=:p"),
                      {"i": surum_id, "p": plant_id}).first()
    if r is None:
        return None
    b = bytes(r.dosya)
    if hashlib.sha256(b).hexdigest() != r.sha256:
        raise RuntimeError("arşiv bütünlüğü bozuk: sha256 uyuşmuyor")
    return {"dosya": b, "dosya_adi": r.dosya_adi, "sha256": r.sha256, "surum": int(r.surum), "teslim_gunu": r.teslim_gunu.isoformat()}
