"""v2.328 — vitrin başvuru hattı: "Karneni başlat" formu → tablo → panelde yönetici.

Kamuya açık uç olduğundan koruma katmanları: uçtaki hız sınırı (main.py'deki
limiter — giriş ucuyla aynı idiom), alan uzunluk tavanları ve bal küpü alanı
(dolduran bot sayılır, sessizce yutulur).

v2.334: e-posta katmanı bağlandı (posta_service) — başvurana teyit, sahibe
(PVQ_BILDIRIM_EPOSTA) bildirim gider. SMTP yapılandırılmamışsa ikisi de
sessizce atlanır ve başvuru ESKİSİ GİBİ yalnız panele düşer; teyit alanı
istemciye dürüstçe False döner (gönderilmemiş mektup "gönderildi" denmez).
"""
from __future__ import annotations

import os
import re

from sqlalchemy import text

from pvquant.db import sistem_baglami, tenant_baglami
from pvquant.services import posta_service, yetki_service

_EPOSTA = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[^@\s]{2,24}$")


def kaydet(eposta: str, santral_adi: str | None, kurulu_guc_kwp: float | None,
           balkupu: str | None = None) -> dict:
    """dönen: {"tamam": bool, "neden": str|None}. Bot reddi de 'tamam' görünür —
    saldırgana sinyal verilmez; yalnız gerçek doğrulama hatası kullanıcıya söylenir."""
    if balkupu:                        # bal küpü dolduysa bot: sessizce yut
        return {"tamam": True}
    eposta = (eposta or "").strip().lower()[:255]
    if not _EPOSTA.match(eposta):
        return {"tamam": False, "neden": "Geçerli bir e-posta girin."}
    ad = (santral_adi or "").strip()[:120] or None
    kwp = None
    if kurulu_guc_kwp is not None:
        try:
            kwp = float(kurulu_guc_kwp)
            if not (0 < kwp < 5_000_000):
                kwp = None
        except (TypeError, ValueError):
            kwp = None
    with sistem_baglami() as s:
        s.execute(text(
            "INSERT INTO vitrin_basvurulari (eposta, santral_adi, kurulu_guc_kwp) "
            "VALUES (:e, :a, :k)"), {"e": eposta, "a": ad, "k": kwp})
    teyit = posta_service.gonder(
        eposta, "PVQuant — başvurunuz alındı",
        "Merhaba,\n\n"
        "PVQuant başvurunuz bize ulaştı. Başvurunuz değerlendirilip teklifimiz "
        "bu e-posta adresinize iletilecektir.\n\n"
        + (f"Santral: {ad}\n" if ad else "")
        + (f"Kurulu güç: {kwp/1000:.1f} MW\n" if kwp else "")
        + "\nBu iletiye yanıt vermenize gerek yoktur.\n\nPVQuant")
    sahip = os.environ.get("PVQ_BILDIRIM_EPOSTA")
    if sahip:
        posta_service.gonder(
            sahip, "[PVQuant] Yeni vitrin başvurusu",
            f"E-posta: {eposta}\n"
            f"Santral: {ad or '—'}\n"
            f"Kurulu güç (kWp): {kwp if kwp is not None else '—'}\n\n"
            "Ayrıntı: pvquant.com/yonetim → Başvurular")
    return {"tamam": True, "teyit": teyit}


TALEP_TURLERI = ("plan", "modul", "sanayi_ges", "diger")   # v2.609 (Faz 6 F6-D): müşteri paneli teklif / yükseltme talebi
TALEP_KAYNAK = {"plan": "yukseltme", "modul": "yukseltme", "sanayi_ges": "sanayi_ges", "diger": "yukseltme"}
KAYNAK_ETIKET = {"vitrin": "vitrin", "yukseltme": "yükseltme talebi", "sanayi_ges": "Sanayi GES talebi"}


def talep_kaydet(tenant_id, user_id, tur: str, hedef: str | None = None, mesaj: str | None = None) -> dict:
    """v2.609 (F6-D): kiracı yöneticisinin teklif / yükseltme talebi — aynı `vitrin_basvurulari` tablosuna (platform Başvurular'da görünür);
    e-posta kullanıcının kendi kayıtlı adresi (formdan alınmaz), santral_adi alanı «kuruluş · tür: hedef», kurulu güç kiracının etkin toplamı,
    kaynak `yukseltme` ya da `sanayi_ges` (00 §13/8–9). Mesaj denetim izinde (çağıran), tabloda kolon yok."""
    if tur not in TALEP_TURLERI:
        raise ValueError("talep türü: plan | modul | sanayi_ges | diger")
    hedef = (hedef or "").strip()[:64] or None
    if hedef and tur == "modul" and hedef not in yetki_service.MODULLER:          # F6-D öz incelemesi: hedef sözlükten (uç doğrudan çağrılabilir)
        raise ValueError("istenen özellik tanımsız")
    if hedef and tur == "plan":
        with sistem_baglami() as s:
            planlar = {r[0] for r in s.execute(text("SELECT ad FROM planlar"))}
        if hedef not in planlar:
            raise ValueError("istenen plan tanımsız")
    with tenant_baglami(tenant_id) as s:
        r = s.execute(text("SELECT u.email, t.name, (SELECT coalesce(sum(p.capacity_kwp), 0) FROM plants p WHERE p.tenant_id = t.id AND NOT p.archived) AS kwp "
                           "FROM users u JOIN tenants t ON t.id = u.tenant_id WHERE u.id = CAST(:u AS uuid) AND u.tenant_id = CAST(:t AS uuid)"),
                      {"u": str(user_id), "t": str(tenant_id)}).first()
    if r is None:
        raise LookupError("kullanıcı yok")
    etiket = {"plan": "plan", "modul": "modül", "sanayi_ges": "Sanayi GES", "diger": "talep"}[tur]
    santral_adi = f"{r.name} · {etiket}" + (f": {hedef}" if hedef else "")
    with sistem_baglami() as s:
        bid = s.execute(text("INSERT INTO vitrin_basvurulari(eposta, santral_adi, kurulu_guc_kwp, kaynak) VALUES (:e, :a, :k, :s) RETURNING id"),
                        {"e": r.email, "a": santral_adi[:120], "k": float(r.kwp) if r.kwp else None, "s": TALEP_KAYNAK[tur]}).scalar()
    return {"tamam": True, "id": str(bid), "kaynak": TALEP_KAYNAK[tur], "eposta": r.email}


def listele(n: int = 100) -> list[dict]:
    with sistem_baglami() as s:
        return [{"id": str(r.id), "eposta": r.eposta, "santral_adi": r.santral_adi,
                 "kurulu_guc_kwp": r.kurulu_guc_kwp, "okundu": r.okundu, "kaynak": r.kaynak, "kaynak_etiketi": KAYNAK_ETIKET.get(r.kaynak, r.kaynak),
                 "created_at": r.created_at.isoformat()} for r in s.execute(text(
            "SELECT id, eposta, santral_adi, kurulu_guc_kwp, okundu, kaynak, created_at "
            "FROM vitrin_basvurulari ORDER BY created_at DESC LIMIT :n"), {"n": min(int(n), 500)})]


def okundu_isaretle(basvuru_id: str) -> bool:
    with sistem_baglami() as s:
        r = s.execute(text(
            "UPDATE vitrin_basvurulari SET okundu = true WHERE id = :i"), {"i": basvuru_id})
        return r.rowcount > 0
