"""v2.264 — Dalga 5.16: dışa dönük API anahtarları (DB destekli).

Anahtar biçimi `pvq_<prefix8>_<secret>`; DB'de yalnız sha256(secret) (api_keys.key_hash) + prefix + kapsamlar.
Doğrulama sabit-zamanlı; hata mesajları ayrıntısız (hangi parça yanlış söylenmez). Oran sınırı 25.10 Faz 4'ten beri
PAYLAŞIMLI 60 sn penceresi (hiz_pencere; süreç içi kova yalnız yedek/test yolu) + günlük dis_api sayacı (kullanim_sayac). Anahtar arama kiracıyı ÖNCE bilemez → sistem_baglami: bu, db.py'deki
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

# Canlı uçları olan kapsamlar (UI bunları sunar). v2.528 (P10): rezerve dört kapsam da canlı — gerceklesen:oku, alarm:oku, rapor:indir, santral:yaz.
CANLI_KAPSAMLAR = ("tahmin:oku", "kgup:oku", "gerceklesen:oku", "alarm:oku", "rapor:indir", "santral:yaz", "gerceklesen:yaz",
                   "veri_kalitesi:oku", "portfoy:oku", "finans:oku")   # v2.603 (F4-I)
KAPSAM_ACIKLAMA = {"gerceklesen:yaz": "Üretim dosyası itme (CSV/XLSX): SCADA ya da kayıt cihazı dışa aktarımı PVQuant'a gönderilir, dosya alım hattından geçer",
                   "tahmin:oku": "Son tahmin koşusu (saatlik P10/P50/P90) ve santral listesi",
                   "kgup:oku": "KGÜP programı (TPYS CSV) ve sürüm geçmişi; toplayıcı özeti",
                   "gerceklesen:oku": "Gerçekleşen üretim: saatlik SCADA ölçümü ya da yüklü sayaç verisi (en çok 92 gün)",
                   "alarm:oku": "Alarm listesi (kural, şiddet, mesaj, okunma/atama)",
                   "rapor:indir": "Dönem raporu (ay / çeyrek / yıl) HTML ya da JSON",
                   "santral:yaz": "Santral ayarı yazma: sayaç türü, SCADA durumu, uzlaştırma girdisi, sistem kullanım bedeli (sayaç ayarı alanları)",
                   "veri_kalitesi:oku": "Veri kalitesi özeti: saat başına nitelik dağılımı, tazelik, ölçüm künyesi (kaynak, son geliş)",   # v2.603 (F4-I)
                   "portfoy:oku": "Portföy listesi (tarihli üyelik sayısı) ve portföy kimlikleri",
                   "finans:oku": "Portföy finansal etkisi (dönem): santral satırları, toplam, nitelik; meta damgaları (kural sicili, fiyat, hesap durumu)"}
_kovalar: dict[str, TokenBucket] = {}


def _hash(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


def ayristir(anahtar: str) -> tuple[str, str] | None:
    """`pvq_<prefix>_<secret>` → (prefix, secret); biçim bozuksa None."""
    p = (anahtar or "").strip().split("_", 2)
    if len(p) != 3 or p[0] != "pvq" or not p[1] or not p[2]:
        return None
    return p[1], p[2]


def uret(tenant_id, ad: str, kapsamlar: list[str], gecerlilik_gun: int | None = None, rpm: int = 120, plant_ids: list[str] | None = None) -> dict:
    """Yeni anahtar; düz metin YALNIZ bu dönüşte görünür (bir daha üretilemez).
    v2.603 (F4-I): `plant_ids` → santral kapsamı (None/boş = kiracının tüm santralleri); kiracıda olmayan santral kimliği ValueError."""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    k = sorted(set(kapsamlar))
    if not k or not set(k) <= KAPSAMLAR:
        raise ValueError(f"bilinmeyen kapsam: {sorted(set(k) - KAPSAMLAR) or 'boş'}")
    if not (1 <= int(rpm) <= 6000):
        raise ValueError("rpm 1–6000")
    pids = sorted({str(x) for x in (plant_ids or []) if x}) or None
    prefix = secrets.token_hex(4); secret = secrets.token_urlsafe(24)
    son = (datetime.now(timezone.utc) + timedelta(days=int(gecerlilik_gun))) if gecerlilik_gun else None
    with tenant_baglami(tenant_id) as s:
        if pids:
            try:
                var = {str(r[0]) for r in s.execute(text("SELECT id FROM plants WHERE id = ANY(CAST(:p AS uuid[]))"), {"p": pids})}
            except Exception as e:   # noqa: BLE001 — uuid olmayan kimlik
                raise ValueError("santral kimliği geçersiz") from e
            eksik = sorted(set(pids) - var)
            if eksik:
                raise ValueError(f"santral bu kiracıda yok: {eksik[0]}")
        kid = s.execute(text(
            "INSERT INTO api_keys(tenant_id, key_hash, label, prefix, scopes, expires_at, rpm, plant_ids) "
            "VALUES(:t, :h, :l, :p, CAST(:s AS jsonb), :e, :r, CAST(:pl AS uuid[])) RETURNING id"),
            {"t": tenant_id, "h": _hash(secret), "l": (ad or "").strip()[:80] or None, "p": prefix,
             "s": json.dumps(k), "e": son, "r": int(rpm), "pl": pids}).scalar()
    return {"id": str(kid), "prefix": prefix, "ad": ad, "kapsamlar": k, "rpm": int(rpm), "plant_ids": pids,
            "expires_at": son.isoformat() if son else None, "anahtar": f"pvq_{prefix}_{secret}"}


def listele(tenant_id) -> list[dict]:
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        rows = s.execute(text(
            "SELECT id, label, prefix, scopes, revoked, expires_at, rpm, last_used_at, created_at, plant_ids "
            "FROM api_keys WHERE prefix IS NOT NULL ORDER BY created_at DESC")).fetchall()
    return [{"id": str(r.id), "ad": r.label, "prefix": r.prefix, "kapsamlar": list(r.scopes or []), "iptal": bool(r.revoked),
             "plant_ids": ([str(x) for x in r.plant_ids] if r.plant_ids else None),   # v2.603: None = tüm santraller
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
            "SELECT id, tenant_id, key_hash, scopes, revoked, expires_at, rpm, plant_ids FROM api_keys WHERE prefix=:p"),
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


def _kova_izin(prefix: str, rpm: int) -> bool:
    """Süreç içi token bucket (v2.264 davranışı) — test yolu ve paylaşımlı pencerenin yedeği."""
    kova = _kovalar.get(prefix)
    if kova is None or kova.kapasite != rpm:
        kova = _kovalar[prefix] = TokenBucket(kapasite=rpm, doldurma_per_sn=rpm / 60.0)
    return kova.izin(prefix)


def _paylasimli_izin(prefix: str, rpm: int, tenant_id) -> bool:
    """25.10 Faz 4: 60 sn'lik paylaşımlı pencere (hiz_pencere) — anahtar başına rpm tüm işçilerde birlikte sayılır.
    İzin verilen istek günlük dis_api sayacına yazılır (reddedilen yazılmaz). Pencere sayılamazsa (DB) kovaya düşer."""
    from pvquant.services import kullanim_service
    n = kullanim_service.pencere_say(f"anahtar:{prefix}")
    if n == 0:
        return _kova_izin(prefix, rpm)
    if n > rpm:
        return False
    kullanim_service.say(tenant_id, "dis_api")
    return True


def dogrula(anahtar: str, kapsam: str, *, bul=None, simdi: datetime | None = None) -> dict:
    """PermissionError('gecersiz anahtar' | 'kapsam yetersiz') ya da RuntimeError('oran siniri').
    Döner {"tenant_id", "prefix", "kapsamlar", "id", "plant_ids"}."""
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
    # 25.10 Faz 4: üretimde PAYLAŞIMLI pencere (tüm uvicorn işçileri aynı satırı sayar) + günlük dis_api sayacı;
    # test/enjekte edilmiş aramada süreç içi kova (DB'siz). DB'ye ulaşılamazsa pencere 0 döner → kovaya düşülür.
    izin = _paylasimli_izin(prefix, rpm, k["tenant_id"]) if bul is _kayit_bul else _kova_izin(prefix, rpm)
    if not izin:
        raise RuntimeError("oran siniri")
    if bul is _kayit_bul:
        _kullanim_isle(k["id"])
    pl = k.get("plant_ids")
    return {"tenant_id": str(k["tenant_id"]), "prefix": prefix, "kapsamlar": sorted(kaps), "id": str(k["id"]),
            "plant_ids": (sorted(str(x) for x in pl) if pl else None)}   # v2.603 (F4-I): santral kapsamı (None = tümü)


def santral_izinli(anahtar: dict, plant_id) -> bool:
    """v2.603 (F4-I): anahtarın santral kapsamı (plant_ids) verilen santrali kapsıyor mu? None → tüm santraller."""
    pl = anahtar.get("plant_ids")
    return True if not pl else str(plant_id) in set(pl)
