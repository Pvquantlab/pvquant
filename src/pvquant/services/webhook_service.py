"""v2.264 — Dalga 5.16: webhook'lar — 'tahmin.yeni' olayı sabah koşusundan sonra HMAC imzalı POST.

İmza: pvquant.ext.platform.api_anahtar.webhook_imzala (X-PVQ-Timestamp + X-PVQ-Signature v1=hex, 5 dk tolerans).
Alıcı hatası sessizce sayılır (fail_count), koşuyu ASLA düşürmez. URL https zorunlu (localhost hariç, geliştirme).
"""
from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from urllib.parse import urlparse

import pandas as pd

from pvquant.ext.platform.api_anahtar import webhook_imzala

OLAYLAR = ("tahmin.yeni", "deneme")
ZAMAN_ASIMI_SN = 10.0


def url_gecerli(url: str) -> bool:
    u = urlparse((url or "").strip())
    if u.scheme == "https" and u.netloc:
        return True
    return u.scheme == "http" and u.hostname in ("localhost", "127.0.0.1", "host.docker.internal")   # yalnız geliştirme


def istek_hazirla(secret: str, olay: str, govde: dict, zaman: int | None = None) -> tuple[bytes, dict]:
    """(gövde bayt, başlıklar) — imza gövdenin tam baytı üzerinden; alıcı aynı baytı doğrular."""
    b = json.dumps(govde, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")
    h = webhook_imzala(secret, b, zaman)
    h.update({"Content-Type": "application/json; charset=utf-8", "X-PVQ-Event": olay, "User-Agent": "PVQuant-Webhook/1"})
    return b, h


def ekle(tenant_id, url: str, plant_id: str | None = None, olaylar: list[str] | None = None) -> dict:
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    if not url_gecerli(url):
        raise ValueError("url https:// ile başlamalı")
    ol = sorted(set(olaylar or ["tahmin.yeni"]))
    if not set(ol) <= set(OLAYLAR):
        raise ValueError(f"bilinmeyen olay: {sorted(set(ol) - set(OLAYLAR))}")
    secret = "whsec_" + secrets.token_urlsafe(24)
    with tenant_baglami(tenant_id) as s:
        wid = s.execute(text(
            "INSERT INTO webhooks(tenant_id, plant_id, url, secret, events) VALUES(:t, :p, :u, :s, CAST(:e AS jsonb)) RETURNING id"),
            {"t": tenant_id, "p": plant_id, "u": url.strip(), "s": secret, "e": json.dumps(ol)}).scalar()
    return {"id": str(wid), "url": url.strip(), "plant_id": plant_id, "olaylar": ol, "secret": secret}


def listele(tenant_id) -> list[dict]:
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        rows = s.execute(text(
            "SELECT w.id, w.plant_id, p.name AS santral, w.url, w.events, w.active, w.created_at, w.last_sent_at, w.last_status, w.fail_count "
            "FROM webhooks w LEFT JOIN plants p ON p.id = w.plant_id ORDER BY w.created_at DESC")).fetchall()
    return [{"id": str(r.id), "plant_id": str(r.plant_id) if r.plant_id else None, "santral": r.santral, "url": r.url,
             "olaylar": list(r.events or []), "aktif": bool(r.active),
             "son_gonderim": r.last_sent_at.isoformat() if r.last_sent_at else None, "son_durum": r.last_status,
             "hata_sayisi": int(r.fail_count or 0)} for r in rows]


def sil(tenant_id, webhook_id) -> bool:
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        return s.execute(text("DELETE FROM webhooks WHERE id=:i"), {"i": webhook_id}).rowcount > 0


def _post(url: str, b: bytes, h: dict) -> int:
    import httpx
    try:
        return int(httpx.post(url, content=b, headers=h, timeout=ZAMAN_ASIMI_SN).status_code)
    except Exception:
        return 0   # ağ hatası: durum 0 (alıcıya ulaşılamadı)


def gonder(tenant_id, olay: str, govde: dict, plant_id: str | None = None, webhook_id: str | None = None, post=_post) -> list[dict]:
    """Uygun alıcılara imzalı POST; sonuçları DB'ye işler; hiçbir zaman yükseltmez."""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    sonuc = []
    with tenant_baglami(tenant_id) as s:
        rows = s.execute(text(
            "SELECT id, url, secret, events FROM webhooks WHERE active "
            "AND (CAST(:w AS uuid) IS NULL OR id = CAST(:w AS uuid)) "
            "AND (plant_id IS NULL OR CAST(:p AS uuid) IS NULL OR plant_id = CAST(:p AS uuid))"),   # psycopg: parametre tipi belirsiz kalmasın
            {"w": webhook_id, "p": plant_id}).fetchall()
        for r in rows:
            if olay not in (r.events or []) and olay != "deneme":
                continue
            b, h = istek_hazirla(r.secret, olay, govde)
            durum = post(r.url, b, h)
            ok = 200 <= durum < 300
            s.execute(text("UPDATE webhooks SET last_sent_at=now(), last_status=:d, fail_count = CASE WHEN :ok THEN 0 ELSE fail_count + 1 END WHERE id=:i"),
                      {"d": durum, "ok": ok, "i": r.id})
            sonuc.append({"id": str(r.id), "durum": durum, "ok": ok})
    return sonuc


def tahmin_yeni_govdesi(tenant_id, plant: dict, kosu_id: str | None) -> dict | None:
    """Son koşunun yerel-gün P50/P10/P90 toplamları (≥20 saat kapsamalı günler) + saatlik ucun adresi."""
    from pvquant.services import forecast_service
    from pvquant.services.portfoy_service import gunluk_toplamlar
    df = forecast_service.son_kosu(tenant_id, plant["id"])
    if df is None or df.empty:
        return None
    tz = plant.get("tz") or "UTC"
    g = gunluk_toplamlar(df, tz)
    return {"olay": "tahmin.yeni", "santral_id": str(plant["id"]), "santral": plant.get("name"), "kosu_id": kosu_id,
            "zaman": datetime.now(timezone.utc).isoformat(), "birim": "kWh",
            "gunluk": [{"gun": k, **v} for k, v in g.items()],
            "saatlik_uc": f"/v1/dis/santral/{plant['id']}/tahmin"}


def sabah_sonrasi(plant: dict, kosu_id: str | None) -> None:
    """Worker kancası: sabah_tahmin bitince çağrılır; her hata yutulur (koşu düşmez)."""
    try:
        govde = tahmin_yeni_govdesi(plant["tenant_id"], plant, kosu_id)
        if govde:
            gonder(plant["tenant_id"], "tahmin.yeni", govde, plant_id=str(plant["id"]))
    except Exception as e:   # noqa: BLE001
        print(f"webhook tahmin.yeni atlandı ({plant.get('name')}): {type(e).__name__}: {e}")
