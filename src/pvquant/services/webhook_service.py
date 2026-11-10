"""v2.264 — Dalga 5.16: webhook'lar — 'tahmin.yeni' olayı sabah koşusundan sonra HMAC imzalı POST.

İmza: pvquant.ext.platform.api_anahtar.webhook_imzala (X-PVQ-Timestamp + X-PVQ-Signature v1=hex, 5 dk tolerans).
Alıcı hatası sessizce sayılır (fail_count), koşuyu ASLA düşürmez. URL https zorunlu (localhost hariç, geliştirme).
"""
from __future__ import annotations

import json
import secrets
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

import pandas as pd

from pvquant.ext.platform.api_anahtar import webhook_imzala
from pvquant.guvenlik import sir as _sir   # v2.570: imza sırrı kasada

OLAYLAR = ("tahmin.yeni", "alarm.yeni", "deneme")   # v2.519 (P7a): alarm.yeni — alerts satırı yazıldığında (alarm_service._bildir)
ZAMAN_ASIMI_SN = 10.0


GELISTIRME_HOSTLAR = ("localhost", "127.0.0.1", "host.docker.internal")
_IC_SONEKLER = (".localhost", ".internal", ".local", ".lan", ".home", ".corp")   # 03.11: genel ağ dışı ad alanları


def _ic_adres(host: str) -> bool:
    """03.11 (v2.528 inceleme, SSRF): hedef sunucunun kendi ağı — döngü, özel (RFC 1918), bağlantı-yerel / bulut meta veri
    (169.254.x), paylaşımlı (100.64/10), 0.0.0.0, IPv6 eşdeğerleri ve iç ad alanları. Ad çözümü YAPILMAZ (dış ağa
    çıkılmaz); adı özel IP'ye çözülen hedef bu süzgeçten geçer — bilinen sınır, gönderimde ağ katmanı sorumludur."""
    import ipaddress
    h = (host or "").strip().lower().rstrip(".")
    if not h or h in GELISTIRME_HOSTLAR or h.endswith(_IC_SONEKLER) or h == "metadata.google.internal":
        return True
    try:
        ip = ipaddress.ip_address(h.strip("[]"))
    except ValueError:
        return False
    return (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified
            or ip in ipaddress.ip_network("100.64.0.0/10"))


def url_gecerli(url: str) -> bool:
    """https ve genel ağda bir adres; http yalnız geliştirme ana makineleri (localhost/127.0.0.1/host.docker.internal)."""
    u = urlparse((url or "").strip())
    if u.scheme == "https" and u.netloc:
        return not _ic_adres(u.hostname or "")
    return u.scheme == "http" and u.hostname in GELISTIRME_HOSTLAR   # yalnız geliştirme


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
        raise ValueError("url https:// ile başlamalı ve genel ağda bir adres olmalı (iç ağ / özel IP kabul edilmez)")
    ol = sorted(set(olaylar or ["tahmin.yeni"]))
    if not set(ol) <= set(OLAYLAR):
        raise ValueError(f"bilinmeyen olay: {sorted(set(ol) - set(OLAYLAR))}")
    secret = "whsec_" + secrets.token_urlsafe(24)
    wid = uuid.uuid4()
    zarf, duz = _sir.sakla(secret, f"webhooks:{tenant_id}:{wid}")   # v2.570: KEK varsa zarf, düz sütun NULL
    with tenant_baglami(tenant_id) as s:
        s.execute(text(
            "INSERT INTO webhooks(id, tenant_id, plant_id, url, secret, secret_zarf, events) VALUES(CAST(:i AS uuid), :t, :p, :u, :s, CAST(:z AS jsonb), CAST(:e AS jsonb))"),
            {"i": str(wid), "t": tenant_id, "p": plant_id, "u": url.strip(), "s": duz, "z": json.dumps(zarf) if zarf else None, "e": json.dumps(ol)})
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
            "SELECT id, url, secret, secret_zarf, events FROM webhooks WHERE active "
            "AND (CAST(:w AS uuid) IS NULL OR id = CAST(:w AS uuid)) "
            "AND (plant_id IS NULL OR CAST(:p AS uuid) IS NULL OR plant_id = CAST(:p AS uuid))"),   # psycopg: parametre tipi belirsiz kalmasın
            {"w": webhook_id, "p": plant_id}).fetchall()
        for r in rows:
            if olay not in (r.events or []) and olay != "deneme":
                continue
            gizli = _sir.oku(getattr(r, "secret_zarf", None), r.secret, f"webhooks:{tenant_id}:{r.id}")   # v2.570 çift okuma
            b, h = istek_hazirla(gizli, olay, govde)
            durum = post(r.url, b, h)
            ok = 200 <= durum < 300
            s.execute(text("UPDATE webhooks SET last_sent_at=now(), last_status=:d, fail_count = CASE WHEN :ok THEN 0 ELSE fail_count + 1 END WHERE id=:i"),
                      {"d": durum, "ok": ok, "i": r.id})
            sonuc.append({"id": str(r.id), "durum": durum, "ok": ok})
    # 25.10 Faz 4: kullanım sayacı (teslim denemesi; hatalı olanlar ayrıca) — asla yükseltmez
    if sonuc:
        from pvquant.services import kullanim_service
        kullanim_service.say(tenant_id, "webhook", len(sonuc))
        if any(not x["ok"] for x in sonuc):
            kullanim_service.say(tenant_id, "webhook_hata", sum(1 for x in sonuc if not x["ok"]))
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
