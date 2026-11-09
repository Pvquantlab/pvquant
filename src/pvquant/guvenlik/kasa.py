"""09.11.2026 v2.556 (Aşama 3, K1) — ZARF ŞİFRELEME KASASI (uygulama içi KEK).

Karar (entegre değerlendirme 04 K1; Opus 05 §«Kimlik bilgisi saklama», T2): bulut hesaplarının kimlik bilgisi (FusionSolar userName/systemCode …)
veritabanında yalnız ŞİFRELİ durur. Zarf deseni:
  • Her kayıt için rastgele 256 bit DEK → gövde AES-256-GCM ile şifrelenir (nonce 12 bayt + şifreli metin + etiket).
  • DEK, ortamdaki KEK ile AES-256-GCM ile SARILIR (PVQ_KEK: base64 32 bayt; kimliği PVQ_KEK_ID, varsayılan «k1»). KEK veritabanında yoktur:
    DB yedeği tek başına çözülemez; KEK (.env) ve DB ayrı kanallardır.
  • AAD (ek doğrulanmış veri) = «tenant:plant:saglayici»: bir kaydın şifreli gövdesi başka kayda/kiracıya taşınamaz.
  • Dönüş: yeni KEK PVQ_KEK/PVQ_KEK_ID olur; eski KEK'ler PVQ_KEK_ESKI="k0=base64,k-1=base64" ile yalnız ÇÖZME için kalır; `yeniden_sar`
    DEK'i yeni KEK ile sarar (gövde yeniden şifrelenmez).
Neden uygulama içi: incelenen bulut KMS bölge listelerinde Türkiye yok; Vault Transit işletim yükü ve fiyatı doğrulanmadı. KVKK md. 9 görüşü ayrı
alınır (veri yurt dışına çıkmıyor). Çözülmüş değer hiçbir günlüğe/denetim izine yazılmaz; hata metinleri anahtar içermez.
Anahtar üretimi (işletim): `python -m pvquant.guvenlik.kasa` → base64 32 bayt; .env'e PVQ_KEK=… (yalnız sunucuda; depoya girmez).
"""
from __future__ import annotations

import base64
import json
import os
import secrets

KEK_ENV = "PVQ_KEK"
KEK_ID_ENV = "PVQ_KEK_ID"
ESKI_ENV = "PVQ_KEK_ESKI"
SURUM = 1
NONCE = 12


class KasaHata(RuntimeError):
    """Kasa kullanılamıyor ya da çözme başarısız; mesajlar anahtar içermez."""


def _b64_anahtar(s: str, ad: str) -> bytes:
    try:
        k = base64.b64decode(s.strip(), validate=True)
    except Exception as e:   # noqa: BLE001
        raise KasaHata(f"{ad} base64 olarak çözülemedi") from e
    if len(k) != 32:
        raise KasaHata(f"{ad} 32 bayt (256 bit) olmalı")
    return k


def aktif_kek_id() -> str:
    return (os.environ.get(KEK_ID_ENV) or "k1").strip() or "k1"


def _kekler() -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    k = os.environ.get(KEK_ENV)
    if k:
        out[aktif_kek_id()] = _b64_anahtar(k, "PVQ_KEK")
    for parca in (os.environ.get(ESKI_ENV) or "").split(","):
        if "=" in parca:
            i, v = parca.split("=", 1)
            out.setdefault(i.strip(), _b64_anahtar(v, f"PVQ_KEK_ESKI[{i.strip()}]"))
    return out


def kek_durum() -> dict:
    """UI/işletim için: KEK tanımlı mı, kimliği, eski anahtar kimlikleri. Anahtarın kendisi dönmez."""
    try:
        kk = _kekler()
    except KasaHata as e:
        return {"var": False, "id": None, "eski": [], "hata": str(e)}
    kid = aktif_kek_id()
    return {"var": kid in kk, "id": kid if kid in kk else None, "eski": [k for k in kk if k != kid]}


def anahtar_uret() -> str:
    return base64.b64encode(secrets.token_bytes(32)).decode()


def _aesgcm():
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    return AESGCM


def sifrele(duz: bytes, aad: str) -> dict:
    """Zarf: {kek_id, dek_sarili, sifreli, surum}. KEK yoksa KasaHata (kimlik saklama kapalı)."""
    kk = _kekler(); kid = aktif_kek_id()
    if kid not in kk:
        raise KasaHata("PVQ_KEK tanımlı değil: kimlik bilgisi saklama bu kurulumda kapalı")
    AESGCM = _aesgcm()
    dek = AESGCM.generate_key(bit_length=256)
    n1 = os.urandom(NONCE); govde = n1 + AESGCM(dek).encrypt(n1, duz, aad.encode())
    n2 = os.urandom(NONCE); sarili = n2 + AESGCM(kk[kid]).encrypt(n2, dek, kid.encode())
    return {"kek_id": kid, "dek_sarili": sarili, "sifreli": govde, "surum": SURUM}


def _dek_coz(kayit: dict, kk: dict[str, bytes]) -> bytes:
    from cryptography.exceptions import InvalidTag
    kid = kayit["kek_id"]
    if kid not in kk:
        raise KasaHata(f"KEK «{kid}» ortamda yok (PVQ_KEK ya da PVQ_KEK_ESKI)")
    s = bytes(kayit["dek_sarili"])
    try:
        return _aesgcm()(kk[kid]).decrypt(s[:NONCE], s[NONCE:], kid.encode())
    except InvalidTag as e:
        raise KasaHata("veri anahtarı çözülemedi: KEK uyuşmuyor ya da kayıt bozuk") from e


def coz(kayit: dict, aad: str) -> bytes:
    from cryptography.exceptions import InvalidTag
    dek = _dek_coz(kayit, _kekler())
    g = bytes(kayit["sifreli"])
    try:
        return _aesgcm()(dek).decrypt(g[:NONCE], g[NONCE:], aad.encode())
    except InvalidTag as e:
        raise KasaHata("şifreli gövde çözülemedi: bütünlük ya da bağlam (kiracı/santral/sağlayıcı) uyuşmazlığı") from e


def sifrele_json(veri: dict, aad: str) -> dict:
    return sifrele(json.dumps(veri, ensure_ascii=False, separators=(",", ":")).encode(), aad)


def coz_json(kayit: dict, aad: str) -> dict:
    return json.loads(coz(kayit, aad).decode())


def yeniden_sar(kayit: dict) -> dict | None:
    """Dönüş: eski KEK ile sarılı DEK'i aktif KEK ile yeniden sarar; gövdeye dokunmaz. Zaten aktifse None."""
    kk = _kekler(); kid = aktif_kek_id()
    if kayit["kek_id"] == kid:
        return None
    if kid not in kk:
        raise KasaHata("PVQ_KEK tanımlı değil")
    dek = _dek_coz(kayit, kk)
    n2 = os.urandom(NONCE)
    return {"kek_id": kid, "dek_sarili": n2 + _aesgcm()(kk[kid]).encrypt(n2, dek, kid.encode())}


if __name__ == "__main__":   # işletim: yeni KEK üret
    print(anahtar_uret())
