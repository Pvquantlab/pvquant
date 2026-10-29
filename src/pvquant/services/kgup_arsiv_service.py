"""v2.502 — KGÜP sürüm arşivi (F-06): indirilen her KGÜP/EAK dosyası değiştirilemez kayıt; aynı içerik (SHA-256) yeniden
indirilince yeni satır açılmaz (son sürüm döner), içerik değiştiyse sürüm numarası artar. Yaptırımdan koruma vaadi değil, kayıt tutma.

Kayıt: kgup_service.uret() çıktısından (csv metni BOM'suz; baytlar = utf-8-sig, API'nin gönderdiğiyle ve sha256 ile birebir).
Okuma: listele (gün/son N), getir (yeniden indirme — bayt bayt aynı dosya). Silme/güncelleme yok (DB yetkisi de yok).
v2.503: kaynak = 'pvquant' | 'musteri' — müşterinin TPYS'ye bildirdiğini beyan ettiği dosya panelden yüklenir (csv_oku ile ayrıştırılır,
aynı tabloda değiştirilemez kayıt), kiyas() öneriyle (son pvquant sürümü) saat saat farkı verir. Dosya içeriği doğrulanır (24 saat, sayısal);
TPYS'nin kabul ettiği doğrulanamaz — beyan kaydıdır.
"""
from __future__ import annotations

import hashlib
import io
import json
from datetime import date

import pandas as pd

from sqlalchemy import text

from pvquant.db import tenant_baglami


def baytlar(r: dict) -> bytes:
    """uret() çıktısının dosya baytları (BOM dâhil) — sha256 alanıyla aynı kaynak."""
    return r["csv"].encode("utf-8-sig")


def kaydet(tenant_id, plant_id, r: dict, indiren=None, kaynak: str = "pvquant", dosya: bytes | None = None) -> dict:
    """uret() çıktısını (ya da kaynak='musteri' için okunmuş dosyayı) arşivler. Dönüş: {id, surum, sha256, yeni(bool)}.
    Aynı gün + kaynak + sha → mevcut kayıt (yeni=False). Sürüm sayacı (gün, kaynak) bazında."""
    if kaynak not in ("pvquant", "musteri"):
        raise ValueError("kaynak pvquant|musteri")
    b = dosya if dosya is not None else baytlar(r); sha = hashlib.sha256(b).hexdigest()
    if r.get("sha256") and r["sha256"] != sha:
        raise ValueError("sha256 uyuşmuyor: yanıt ile dosya baytları farklı")
    gun = date.fromisoformat(r["gun"]); kosu = r.get("kosu") or {}
    with tenant_baglami(tenant_id) as s:
        var = s.execute(text("SELECT id, surum FROM kgup_surum WHERE plant_id=:p AND teslim_gunu=:g AND kaynak=:ka AND sha256=:h ORDER BY surum DESC LIMIT 1"),
                        {"p": plant_id, "g": gun, "ka": kaynak, "h": sha}).first()
        if var:
            return {"id": str(var.id), "surum": int(var.surum), "sha256": sha, "yeni": False, "kaynak": kaynak}
        son = s.execute(text("SELECT coalesce(max(surum), 0) FROM kgup_surum WHERE plant_id=:p AND teslim_gunu=:g AND kaynak=:ka"), {"p": plant_id, "g": gun, "ka": kaynak}).scalar()
        surum = int(son or 0) + 1
        eak = r.get("eak") or {}
        sid = s.execute(text(
            "INSERT INTO kgup_surum(tenant_id, plant_id, teslim_gunu, surum, kantil, run_id, run_at, kesim, eak_mw, eak_kaynak, toplam_mwh, "
            " sha256, dosya, dosya_adi, sablon_json, indiren, kaynak) "
            "VALUES(:t, :p, :g, :s, :k, :rid, :rat, :kes, :eak, :eakk, :top, :h, :d, :ad, CAST(:sab AS jsonb), :u, :ka) RETURNING id"),
            {"t": tenant_id, "p": plant_id, "g": gun, "s": surum, "k": r.get("kantil", "p50"),
             "rid": kosu.get("run_id"), "rat": kosu.get("run_at"), "kes": kosu.get("kesim"),
             "eak": eak.get("eak_mw"), "eakk": eak.get("kaynak"), "top": r.get("toplam_mwh"),
             "h": sha, "d": b, "ad": r.get("dosya_adi", "KGUP.csv"), "sab": json.dumps(r.get("sablon") or {}, ensure_ascii=False), "u": indiren, "ka": kaynak}).scalar()
    return {"id": str(sid), "surum": surum, "sha256": sha, "yeni": True, "kaynak": kaynak}


def csv_oku(b: bytes, sablon=None) -> pd.DataFrame:
    """KGÜP CSV baytları → DataFrame(saat 0–23, kgup_mwh, eak_mw|None). Ayraç/ondalık şablondan (yoksa ; ve ,; sezgisel yedek),
    kolonlar ada göre (büyük/küçük harf duyarsız; KGUP/EAK içeren başlıklar). 24 saat zorunlu; 96 çeyrek satırı saatlik toplama çevrilir."""
    from pvquant.ext.turkiye.kgup import Sablon
    sab = sablon or Sablon()
    metin = b.decode("utf-8-sig", errors="replace")
    ilk = metin.splitlines()[0] if metin.strip() else ""
    ayrac = sab.ayrac if sab.ayrac in ilk else ("," if ilk.count(",") > ilk.count(";") else ";")
    ondalik = sab.ondalik if ayrac != sab.ondalik else ("." if ayrac == "," else ",")
    df = pd.read_csv(io.StringIO(metin), sep=ayrac, decimal=ondalik, dtype=str)
    df.columns = [str(c).strip() for c in df.columns]
    alt = {c.lower(): c for c in df.columns}
    def bul(ad, *ipucu):
        if ad.lower() in alt:
            return alt[ad.lower()]
        for c in df.columns:
            if any(i in c.lower() for i in ipucu):
                return c
        return None
    k_saat = bul(sab.saat, "saat", "hour"); k_kgup = bul(sab.kgup, "kgup", "kgüp", "program"); k_eak = bul(sab.eak, "eak", "emre")
    k_ceyrek = bul(sab.ceyrek, "ceyrek", "çeyrek", "dakika")
    if k_saat is None or k_kgup is None:
        raise ValueError(f"saat/KGÜP kolonu bulunamadı: {list(df.columns)[:6]}")
    def sayi(ser):
        return pd.to_numeric(ser.astype(str).str.replace(" ", "").str.replace(".", "", regex=False).str.replace(",", ".", regex=False) if ondalik == "," else ser, errors="coerce")
    out = pd.DataFrame({"saat": pd.to_numeric(df[k_saat], errors="coerce"), "kgup_mwh": sayi(df[k_kgup]),
                        "eak_mw": sayi(df[k_eak]) if k_eak else None})
    if k_ceyrek and df[k_ceyrek].notna().any() and len(out) > 24:
        out = out.groupby("saat", as_index=False).agg({"kgup_mwh": "sum", "eak_mw": "max"})
    out = out.dropna(subset=["saat"]).sort_values("saat").reset_index(drop=True)
    out["saat"] = out["saat"].astype(int)
    if out["saat"].tolist() != list(range(24)):
        raise ValueError(f"24 saat bekleniyor; bulunan saatler: {out['saat'].tolist()[:30]}")
    if out["kgup_mwh"].isna().any() or (out["kgup_mwh"] < 0).any():
        raise ValueError("KGÜP değerleri eksik ya da negatif")
    return out


def musteri_kaydet(tenant_id, plant_id, gun: date, b: bytes, dosya_adi: str, indiren=None, sablon=None) -> dict:
    """Müşterinin TPYS'ye bildirdiğini beyan ettiği dosya: doğrula, 'musteri' kaynağıyla arşivle. Dönüş kayıt + özet."""
    t = csv_oku(b, sablon)
    r = {"gun": gun.isoformat(), "kantil": "bildirilen", "toplam_mwh": round(float(t["kgup_mwh"].sum()), 3), "dosya_adi": dosya_adi,
         "eak": {"eak_mw": (float(t["eak_mw"].max()) if t["eak_mw"] is not None and t["eak_mw"].notna().any() else None), "kaynak": "musteri_dosyasi"},
         "sablon": {"durum": "müşteri beyanı; TPYS kabulü doğrulanmadı"}}
    k = kaydet(tenant_id, plant_id, r, indiren=indiren, kaynak="musteri", dosya=b)
    return {**k, "toplam_mwh": r["toplam_mwh"], "satir": int(len(t))}


def kiyas(tenant_id, plant_id, gun: date) -> dict:
    """Son PVQuant önerisi (kaynak pvquant, en yüksek sürüm) ↔ son müşteri bildirimi: saat saat fark (MWh), toplam, en büyük fark."""
    with tenant_baglami(tenant_id) as s:
        rows = s.execute(text("SELECT DISTINCT ON (kaynak) kaynak, id, surum, sha256, dosya, olusturma, toplam_mwh, kantil FROM kgup_surum "
                              "WHERE plant_id=:p AND teslim_gunu=:g ORDER BY kaynak, surum DESC"), {"p": plant_id, "g": gun}).fetchall()
    kay = {r.kaynak: r for r in rows}
    out = {"gun": gun.isoformat(), "oneri": None, "bildirilen": None, "saatler": [], "ozet": None}
    for ad in ("pvquant", "musteri"):
        if ad in kay:
            r = kay[ad]
            out["oneri" if ad == "pvquant" else "bildirilen"] = {"id": str(r.id), "surum": int(r.surum), "sha256": r.sha256, "zaman": r.olusturma.isoformat(),
                                                                "toplam_mwh": r.toplam_mwh, "kantil": r.kantil}
    if "pvquant" in kay and "musteri" in kay:
        a = csv_oku(bytes(kay["pvquant"].dosya)); b = csv_oku(bytes(kay["musteri"].dosya))
        fark = b["kgup_mwh"].values - a["kgup_mwh"].values
        out["saatler"] = [{"saat": int(h), "oneri_mwh": float(a.kgup_mwh[h]), "bildirilen_mwh": float(b.kgup_mwh[h]), "fark_mwh": round(float(fark[h]), 3)} for h in range(24)]
        out["ozet"] = {"fark_toplam_mwh": round(float(fark.sum()), 3), "fark_mutlak_mwh": round(float(abs(fark).sum()), 3),
                       "en_buyuk_fark_saat": int(abs(fark).argmax()), "en_buyuk_fark_mwh": round(float(fark[abs(fark).argmax()]), 3),
                       "farkli_saat": int((abs(fark) > 0.0005).sum()), "ayni": bool((abs(fark) <= 0.0005).all())}
    return out


def listele(tenant_id, plant_id, gun: date | None = None, n: int = 30) -> list[dict]:
    """Sürüm geçmişi (yeni → eski). gun verilirse yalnız o teslim günü."""
    with tenant_baglami(tenant_id) as s:
        rows = s.execute(text(
            "SELECT k.id, k.teslim_gunu, k.surum, k.kantil, k.run_id, k.run_at, k.kesim, k.eak_mw, k.eak_kaynak, k.toplam_mwh, k.sha256, k.dosya_adi, "
            " k.olusturma, u.email AS indiren_eposta, octet_length(k.dosya) AS bayt, k.kaynak "
            "FROM kgup_surum k LEFT JOIN users u ON u.id = k.indiren "
            "WHERE k.plant_id=:p AND (CAST(:g AS date) IS NULL OR k.teslim_gunu = CAST(:g AS date)) ORDER BY k.teslim_gunu DESC, k.kaynak, k.surum DESC LIMIT :n"),
            {"p": plant_id, "g": gun, "n": n}).fetchall()
    return [{"id": str(r.id), "teslim_gunu": r.teslim_gunu.isoformat(), "surum": int(r.surum), "kantil": r.kantil,
             "run_id": str(r.run_id) if r.run_id else None, "run_at": r.run_at.isoformat() if r.run_at else None,
             "kesim": r.kesim.isoformat() if r.kesim else None, "eak_mw": r.eak_mw, "eak_kaynak": r.eak_kaynak, "toplam_mwh": r.toplam_mwh,
             "sha256": r.sha256, "dosya_adi": r.dosya_adi, "olusturma": r.olusturma.isoformat(), "indiren": r.indiren_eposta, "bayt": int(r.bayt), "kaynak": r.kaynak}
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


SAKLAMA_TABAN_AY = 15   # itiraz 12 ay (m.133(5)) + fatura itirazı + pay; v2502 göç notu


def temizle(ay: int | None = None) -> int:
    """29.10 (F-06 saklama) — teslim günü `ay` aydan eski kgup_surum satırlarını siler; silinen sayısını döner.
    ay None → ayar (kgup_saklama_ay, varsayılan 24); 0 → dokunmaz; 1–14 → SAKLAMA_TABAN_AY'a çekilir (itiraz penceresi
    kapanmadan kayıt silinmez). Uygulama rolü (pvq_app) DELETE yetkisiz olduğundan iş bağlantı rolüyle (sistem_baglami) koşar;
    yalnız worker'ın aylık işi çağırır."""
    if ay is None:
        from pvquant.config import get_settings
        ay = int(get_settings().kgup_saklama_ay or 0)
    if ay <= 0:
        return 0
    ay = max(int(ay), SAKLAMA_TABAN_AY)
    from pvquant.db import sistem_baglami
    with sistem_baglami() as s:
        return int(s.execute(text("DELETE FROM kgup_surum WHERE teslim_gunu < current_date - (:ay * interval '1 month')"), {"ay": ay}).rowcount)
