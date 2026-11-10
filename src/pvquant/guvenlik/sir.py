"""10.11.2026 v2.570 (Faz 0 onay paketi 2: GV-01/GV-02) — SIR SAKLAMA ve TOTP TEKRAR KORUMASI, tek yer.

Sır saklama: TOTP sırları (users, platform_kullanicilar) ve webhook imza sırları veritabanında düz metin duruyordu; kasa (guvenlik/kasa.py,
AES-256-GCM zarf, KEK ortamda) yalnız bulut kimliğinde kullanılıyordu. Bu modül aynı kasayı küçük metin sırları için sarar:
  • `sakla(duz, aad)` → KEK varsa (zarf, None): zarf JSON'a yazılır, düz sütun NULL olur. KEK yoksa (None, duz): bugünkü davranış sürer
    (kurulum uyarısı kasa.kek_durum ile görünür; değer hiçbir yere yazılmaz).
  • `oku(zarf, duz, aad)` → geçiş dönemi ÇİFT OKUMA: zarf varsa çözülür, yoksa düz metin. Böylece kod önce, dönüşüm sonra gider ve geri dönüş
    (`scripts/sirlari_kasaya_tasi.py --geri`) her an mümkündür.
AAD bağları: «users:<id>:totp», «platform:<id>:totp», «webhooks:<tenant_id>:<id>» — bir kaydın zarfı başka kayda taşınamaz.
Zarf JSON: {kek_id, dek_sarili(b64), sifreli(b64), surum}; kasa.sifrele/coz ile aynı bayt yapısı.

TOTP tekrar koruması: pyotp `verify(valid_window=1)` hangi zaman adımının eşleştiğini söylemez ve son kabul edilen adımı saklamaz; aynı kod
≈90 sn içinde ikinci kez geçerdi. `totp_dogrula` eşleşen adımı bulur ve son kabul edilen adımdan küçük ya da eşitse REDDEDER; kabulde yeni adım
döner, çağıran katman onu atomik yazar (UPDATE … WHERE totp_son_adim IS NULL OR totp_son_adim < :adim; 0 satır = eşzamanlı tekrar → red).
Hiçbir işlev sırrı ya da kodu günlüğe yazmaz.
"""
from __future__ import annotations

import base64
import time

import pyotp

from pvquant.guvenlik import kasa

ADIM_SN = 30
PENCERE = 1


def _b64(b: bytes) -> str:
    return base64.b64encode(bytes(b)).decode()


def _unb64(s: str) -> bytes:
    return base64.b64decode(s)


def kasa_acik() -> bool:
    return bool(kasa.kek_durum().get("var"))


def sakla(duz: str, aad: str) -> tuple[dict | None, str | None]:
    """KEK varsa (zarf, None); yoksa (None, duz). Boş sır (None, None)."""
    if not duz:
        return None, None
    if not kasa_acik():
        return None, duz
    z = kasa.sifrele(duz.encode("utf-8"), aad)
    return {"kek_id": z["kek_id"], "dek_sarili": _b64(z["dek_sarili"]), "sifreli": _b64(z["sifreli"]), "surum": int(z["surum"])}, None


def oku(zarf: dict | None, duz: str | None, aad: str) -> str | None:
    """Çift okuma: zarf varsa çöz (KasaHata çağırana çıkar), yoksa düz metin."""
    if zarf:
        kayit = {"kek_id": zarf["kek_id"], "dek_sarili": _unb64(zarf["dek_sarili"]), "sifreli": _unb64(zarf["sifreli"]), "surum": zarf.get("surum", 1)}
        return kasa.coz(kayit, aad).decode("utf-8")
    return duz or None


def totp_temizle(kod: str | None) -> str:
    return "".join(ch for ch in (kod or "") if ch.isdigit())


def totp_dogrula(sir: str | None, kod: str | None, son_adim: int | None, simdi: float | None = None) -> tuple[bool, int | None]:
    """±PENCERE adımda eşleşen adımı bulur. Eşleşme yoksa (False, None); eşleşen adım son kabul edilenden yeni değilse (False, None) — tekrar;
    kabulde (True, adim). `simdi` test için (epoch saniye)."""
    kod = totp_temizle(kod)
    if not sir or len(kod) != 6:
        return False, None
    t = int((time.time() if simdi is None else simdi) // ADIM_SN)
    totp = pyotp.TOTP(sir)
    for adim in range(t - PENCERE, t + PENCERE + 1):
        if totp.at(adim * ADIM_SN) == kod:
            if son_adim is not None and adim <= int(son_adim):
                return False, None
            return True, adim
    return False, None
