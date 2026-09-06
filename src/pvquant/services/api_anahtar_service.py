"""v2.264 — Dalga 5.16: dışa dönük API anahtarları (DB destekli).

Anahtar biçimi `pvq_<prefix8>_<secret>`; DB'de yalnız sha256(secret) (api_keys.key_hash) + prefix + kapsamlar.
Doğrulama sabit-zamanlı; hata mesajları ayrıntısız (hangi parça yanlış söylenmez). Oran sınırı süreç içi
token bucket (anahtar başına rpm). Anahtar arama kiracıyı ÖNCE bilemez → sistem_baglami: bu, db.py'deki
"yalnız auth_service" kuralının v2.264 istisnasıdır (API-anahtar kimlik doğrulaması da bir auth kapısıdır);
yalnız prefix ile tek satır okunur, başka hiçbir veri okunmaz.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone

from pvquant.ext.platform.api_anahtar import KAPSAMLAR, TokenBucket

# Bu sürümde canlı uçları olan kapsamlar (UI yalnız bunları sunar; diğerleri ext sözlüğünde rezerve).
CANLI_KAPSAMLAR = ("tahmin:oku", "kgup:oku")
_kovalar: dict[str, TokenBucket] = {}


def _hash(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


def ayristir(anahtar: str) -> tuple[str, str] | None:
    """`pvq_<prefix>_<secret>` → (prefix, secret); biçim bozuksa None."""
    p = (anahtar or "").strip().split("_", 2)
    if len(p) != 3 or p[0] != "pvq" or not p[1] or not p[2]:
        return None
    return p[1], p[2]


def uret(tenant_id, ad: str, kapsamlar: list[str], gecerlilik_gun: int | None = None, rpm: int = 120) -> dict:
    """Yeni anahtar; düz metin YALNIZ bu dönüşte görünür (bir daha üretilemez)."""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    k = sorted(set(kapsamlar))
    if not k or not set(k) <= KAPSAMLAR:
        raise ValueError(f"bilinmeyen kapsam: {sorted(set(k) - KAPSAMLAR) or 'boş'}")
    if not (1 <= int(rpm) <= 6000):
        raise ValueError("rpm 1–6000")
    prefix = secrets.token_hex(4); secret = secrets.token_urlsafe(24)
    son = (datetime.now(timezone.utc) + timedelta(days=int(gecerlilik_gun))) if gecerlilik_gun else None
    with tenant_baglami(tenant_id) as s:
        kid = s.execute(text(
            "INSERT INTO api_keys(tenant_id, key_hash, label, prefix, scopes, expires_at, rpm) "
            "VALUES(:t, :h, :l, :p, CAST(:s AS jsonb), :e, :r) RETURNING id"),
            {"t": tenant_id, "h": _hash(secret), "l": (ad or "").strip()[:80] or None, "p": prefix,
             "s": json.dumps(k), "e": son, "r": int(rpm)}).scalar()
    return {"id": str(kid), "prefix": prefix, "ad": ad, "kapsamlar": k, "rpm": int(rpm),
            "expires_at": son.isoformat() if son else None, "anahtar": f"pvq_{prefix}_{secret}"}


def listele(tenant_id) -> list[dict]:
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        rows = s.execute(text(
            "SELECT id, label, prefix, scopes, revoked, expires_at, rpm, last_used_at, created_at "
            "FROM api_keys WHERE prefix IS NOT NULL ORDER BY created_at DESC")).fetchall()
    return [{"id": str(r.id), "ad": r.label, "prefix": r.prefix, "kapsamlar": list(r.scopes or []), "iptal": bool(r.revoked),
             "expires_at": r.expires_at.isoformat() if r.expires_at else None, "rpm": r.rpm,
             "son_kullanim": r.last_used_at.isoformat() if r.last_used_at else None,
             "olusturma": r.created_at.isoformat() if r.created_at else None} for r in rows]


def iptal(tenant_id, anahtar_id) -> bool:
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        n = s.execute(text("UPDATE api_keys SET revoked=true WHERE id=:i AND NOT revoked"), {"i": anahtar_id}).rowcount
    return n > 0


def _kayit_bul(prefix: str) -> dict | None:
    from sqlalchemy import text
    from pvquant.db import sistem_baglami
    with sistem_baglami() as s:
        r = s.execute(text(
            "SELECT id, tenant_id, key_hash, scopes, revoked, expires_at, rpm FROM api_keys WHERE prefix=:p"),
            {"p": prefix}).first()
        return dict(r._mapping) if r else None


def _kullanim_isle(anahtar_id) -> None:
    from sqlalchemy import text
    from pvquant.db import sistem_baglami
    try:
        with sistem_baglami() as s:
            s.execute(text("UPDATE api_keys SET last_used_at=now() WHERE id=:i "
                           "AND (last_used_at IS NULL OR last_used_at < now() - interval '60 seconds')"), {"i": anahtar_id})
    except Exception:
        pass   # kullanım damgası kritik değil; kapı yanıtı gecikmesin


def dogrula(anahtar: str, kapsam: str, *, bul=None, simdi: datetime | None = None) -> dict:
    """PermissionError('gecersiz anahtar' | 'kapsam yetersiz') ya da RuntimeError('oran siniri').
    Döner {"tenant_id", "prefix", "kapsamlar", "id"}."""
    bul = bul or _kayit_bul
    simdi = simdi or datetime.now(timezone.utc)
    p = ayristir(anahtar)
    if p is None:
        raise PermissionError("gecersiz anahtar")
    prefix, secret = p
    k = bul(prefix)
    if k is None or not hmac.compare_digest(str(k["key_hash"]), _hash(secret)):
        raise PermissionError("gecersiz anahtar")
    if k.get("revoked") or (k.get("expires_at") and simdi > k["expires_at"]):
        raise PermissionError("gecersiz anahtar")
    kaps = set(k.get("scopes") or [])
    if kapsam not in kaps:
        raise PermissionError("kapsam yetersiz")
    rpm = int(k.get("rpm") or 120)
    kova = _kovalar.get(prefix)
    if kova is None or kova.kapasite != rpm:
        kova = _kovalar[prefix] = TokenBucket(kapasite=rpm, doldurma_per_sn=rpm / 60.0)
    if not kova.izin(prefix):
        raise RuntimeError("oran siniri")
    if bul is _kayit_bul:
        _kullanim_isle(k["id"])
    return {"tenant_id": str(k["tenant_id"]), "prefix": prefix, "kapsamlar": sorted(kaps), "id": str(k["id"])}
