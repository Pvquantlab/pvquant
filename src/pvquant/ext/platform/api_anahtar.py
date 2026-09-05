"""API anahtarları — üretim/doğrulama (yalnız hash saklanır), kapsam, oran sınırı, döndürme, webhook imzası.

Anahtar biçimi: `pvq_<prefix8>_<secret32>`; veritabanında prefix + sha256(secret) + kapsamlar + tenant + son kullanım.
Doğrulama sabit-zamanlı karşılaştırma. Oran sınırı: token bucket (anahtar başına, dakikada N). Döndürme: eski anahtar
`grace` süresi boyunca geçerli kalır. Webhook: HMAC-SHA256 imza + zaman damgası (5 dk tolerans, tekrar saldırısına karşı).
Depolama arayüzü soyut (`Depo`): bellek içi örnek + SQL için şema önerisi (mevcut api_keys tablosuyla eşlenebilir).
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass, field

KAPSAMLAR = {"tahmin:oku", "gerceklesen:oku", "rapor:indir", "kgup:oku", "alarm:oku", "santral:yaz"}


@dataclass
class AnahtarKaydi:
    prefix: str; hash_: str; tenant_id: str; kapsamlar: set[str]; ad: str = ""
    olusturma: float = field(default_factory=time.time); son_kullanim: float | None = None
    iptal: bool = False; gecerlilik_sonu: float | None = None; dakika_limit: int = 120


class Depo:
    """Bellek içi depo; üretimde aynı arayüzle SQL (prefix PK, hash, tenant_id, scopes JSON, revoked, expires_at, rpm)."""
    def __init__(self): self.kayitlar: dict[str, AnahtarKaydi] = {}
    def kaydet(self, k: AnahtarKaydi): self.kayitlar[k.prefix] = k
    def bul(self, prefix: str) -> AnahtarKaydi | None: return self.kayitlar.get(prefix)


def _hash(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


def uret(depo: Depo, tenant_id: str, kapsamlar: set[str], ad: str = "", gecerlilik_gun: int | None = None, dakika_limit: int = 120) -> tuple[str, AnahtarKaydi]:
    """Döner (düz anahtar — YALNIZ BİR KEZ gösterilir, kayıt)."""
    if not kapsamlar <= KAPSAMLAR:
        raise ValueError(f"bilinmeyen kapsam: {kapsamlar - KAPSAMLAR}")
    prefix = secrets.token_hex(4); secret = secrets.token_urlsafe(24)
    kayit = AnahtarKaydi(prefix, _hash(secret), tenant_id, set(kapsamlar), ad, dakika_limit=dakika_limit,
                         gecerlilik_sonu=(time.time() + gecerlilik_gun * 86400) if gecerlilik_gun else None)
    depo.kaydet(kayit)
    return f"pvq_{prefix}_{secret}", kayit


def dogrula(depo: Depo, anahtar: str, gereken_kapsam: str | None = None, simdi: float | None = None) -> AnahtarKaydi:
    """Hatalı/iptal/süresi dolmuş/kapsam dışı → PermissionError (mesaj ayrıntısız: sızdırmaz)."""
    simdi = simdi or time.time()
    try:
        _, prefix, secret = anahtar.split("_", 2)
    except ValueError:
        raise PermissionError("gecersiz anahtar")
    k = depo.bul(prefix)
    if k is None or not hmac.compare_digest(k.hash_, _hash(secret)):
        raise PermissionError("gecersiz anahtar")
    if k.iptal or (k.gecerlilik_sonu and simdi > k.gecerlilik_sonu):
        raise PermissionError("gecersiz anahtar")
    if gereken_kapsam and gereken_kapsam not in k.kapsamlar:
        raise PermissionError("kapsam yetersiz")
    k.son_kullanim = simdi
    return k


def iptal_et(depo: Depo, prefix: str) -> None:
    k = depo.bul(prefix)
    if k: k.iptal = True


def dondur(depo: Depo, eski_prefix: str, grace_saat: float = 24.0) -> tuple[str, AnahtarKaydi]:
    """Yeni anahtar üretir; eskisi grace süresi sonunda geçersiz olur."""
    eski = depo.bul(eski_prefix)
    if eski is None:
        raise KeyError(eski_prefix)
    eski.gecerlilik_sonu = time.time() + grace_saat * 3600
    return uret(depo, eski.tenant_id, eski.kapsamlar, eski.ad + " (döndürülmüş)", dakika_limit=eski.dakika_limit)


@dataclass
class TokenBucket:
    kapasite: int; doldurma_per_sn: float
    _kova: dict[str, tuple[float, float]] = field(default_factory=dict)

    def izin(self, anahtar: str, simdi: float | None = None) -> bool:
        simdi = simdi or time.time(); jeton, t = self._kova.get(anahtar, (float(self.kapasite), simdi))
        jeton = min(self.kapasite, jeton + (simdi - t) * self.doldurma_per_sn)
        if jeton >= 1:
            self._kova[anahtar] = (jeton - 1, simdi); return True
        self._kova[anahtar] = (jeton, simdi); return False


def oran_siniri(kayit: AnahtarKaydi, kova: TokenBucket, simdi: float | None = None) -> None:
    if not kova.izin(kayit.prefix, simdi):
        raise RuntimeError("429: oran siniri")


# --- webhook imzası ---
def webhook_imzala(gizli: str, govde: bytes, zaman: int | None = None) -> dict[str, str]:
    t = str(zaman or int(time.time()))
    imza = hmac.new(gizli.encode(), f"{t}.".encode() + govde, hashlib.sha256).hexdigest()
    return {"X-PVQ-Timestamp": t, "X-PVQ-Signature": f"v1={imza}"}


def webhook_dogrula(gizli: str, govde: bytes, basliklar: dict[str, str], tolerans_sn: int = 300, simdi: int | None = None) -> bool:
    try:
        t = int(basliklar["X-PVQ-Timestamp"]); imza = basliklar["X-PVQ-Signature"].split("=", 1)[1]
    except (KeyError, ValueError, IndexError):
        return False
    if abs((simdi or int(time.time())) - t) > tolerans_sn:
        return False
    beklenen = hmac.new(gizli.encode(), f"{t}.".encode() + govde, hashlib.sha256).hexdigest()
    return hmac.compare_digest(beklenen, imza)
