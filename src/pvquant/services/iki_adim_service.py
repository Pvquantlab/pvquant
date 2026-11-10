"""v2.338 — TOTP iki adımlı doğrulama (authenticator uygulaması) + kurtarma kodları.

Akış:
- baslat(): sır üretilir (henüz AKTİF DEĞİL), otpauth URI + QR (SVG) döner.
- dogrula_ve_ac(): ilk kod doğrulanır → aktif olur, 10 kurtarma kodu üretilir
  (düz metin YALNIZ burada döner; sonra yalnız özetleri saklanır).
- giris_dogrula(): girişte TOTP kodu YA DA bir kurtarma kodu (tek kullanımlık).
- kapat(): kodla doğrulayıp sırrı ve kurtarma kodlarını siler.

Sözleşme: TOTP sırrı doğrulama için geri okunur, bu yüzden özetlenemez —
kısıtlı sütunda tutulur ve hiçbir uçtan geri verilmez (yalnız kayıt anında).
Kurtarma kodları parola gibi bcrypt ile özetlenir.
"""
from __future__ import annotations

import io
import secrets

import json as _json
import pyotp

from pvquant.guvenlik import sir as _sir   # v2.570: sır kasası + TOTP tekrar koruması (tek yer)
import qrcode
from qrcode.image.svg import SvgPathImage
from passlib.hash import bcrypt
from sqlalchemy import text

from pvquant.db import sistem_baglami

_KURTARMA_ADET = 10
_ISSUER = "PVQuant"


def durum(user_id) -> dict:
    """{aktif: bool, kalan_kurtarma: int}. Sır ASLA dönmez."""
    with sistem_baglami() as s:
        row = s.execute(text("SELECT totp_aktif FROM users WHERE id=:i"),
                        {"i": user_id}).first()
        kalan = s.execute(text(
            "SELECT count(*) FROM kurtarma_kodlari "
            "WHERE user_id=:i AND kullanildi_at IS NULL"), {"i": user_id}).scalar()
    return {"aktif": bool(row and row.totp_aktif), "kalan_kurtarma": int(kalan or 0)}


def baslat(user_id, email: str) -> dict:
    """Yeni sır üretir (aktif etmez — dogrula_ve_ac gerekir). Zaten aktifse
    ValueError. Dönüş: {secret, otpauth_uri, qr_svg}."""
    with sistem_baglami() as s:
        row = s.execute(text("SELECT totp_aktif FROM users WHERE id=:i"),
                        {"i": user_id}).first()
        if row is None:
            raise ValueError("kullanıcı yok")
        if row.totp_aktif:
            raise ValueError("iki adımlı doğrulama zaten açık")
        sir = pyotp.random_base32()
        zarf, duz = _sir.sakla(sir, f"users:{user_id}:totp")   # v2.570: KEK varsa zarf, düz sütun NULL
        s.execute(text("UPDATE users SET totp_secret=:x, totp_zarf=CAST(:z AS jsonb), totp_aktif=false, totp_son_adim=NULL WHERE id=:i"),
                  {"x": duz, "z": _json.dumps(zarf) if zarf else None, "i": user_id})
    uri = pyotp.totp.TOTP(sir).provisioning_uri(name=email, issuer_name=_ISSUER)
    return {"secret": sir, "otpauth_uri": uri, "qr_svg": _qr_svg(uri)}


def dogrula_ve_ac(user_id, kod: str) -> dict:
    """İlk TOTP kodunu doğrular, 2FA'yı açar ve kurtarma kodları üretir.
    Dönüş: {kurtarma_kodlari: [...]} (düz metin — bir daha gösterilmez)."""
    with sistem_baglami() as s:
        row = s.execute(text("SELECT totp_secret, totp_zarf, totp_aktif, totp_son_adim FROM users WHERE id=:i"),
                        {"i": user_id}).first()
        sirr = _sir.oku(getattr(row, "totp_zarf", None), getattr(row, "totp_secret", None), f"users:{user_id}:totp") if row is not None else None
        if not sirr:
            raise ValueError("önce kurulumu başlatın")
        ok, adim = _sir.totp_dogrula(sirr, kod, getattr(row, "totp_son_adim", None))
        if not ok or not _adim_yaz(s, "users", user_id, adim):
            raise ValueError("kod doğrulanamadı — uygulamadaki 6 haneyi girin (aynı kod ikinci kez kullanılamaz)")
        s.execute(text("UPDATE users SET totp_aktif=true WHERE id=:i"), {"i": user_id})
        kodlar = _kurtarma_uret(s, user_id)
    return {"kurtarma_kodlari": kodlar}


def kapat(user_id, kod: str) -> None:
    """Geçerli TOTP ya da kurtarma koduyla 2FA'yı kapatır; sır ve kurtarma
    kodları silinir."""
    if not giris_dogrula(user_id, kod):
        raise ValueError("kod doğrulanamadı")
    with sistem_baglami() as s:
        s.execute(text("UPDATE users SET totp_secret=NULL, totp_zarf=NULL, totp_son_adim=NULL, totp_aktif=false WHERE id=:i"),
                  {"i": user_id})
        s.execute(text("DELETE FROM kurtarma_kodlari WHERE user_id=:i"), {"i": user_id})


def kurtarma_yenile(user_id, kod: str) -> dict:
    """Kodla doğrulayıp kurtarma kodlarını yeniden üretir (eskiler geçersiz)."""
    if not giris_dogrula(user_id, kod):
        raise ValueError("kod doğrulanamadı")
    with sistem_baglami() as s:
        s.execute(text("DELETE FROM kurtarma_kodlari WHERE user_id=:i"), {"i": user_id})
        kodlar = _kurtarma_uret(s, user_id)
    return {"kurtarma_kodlari": kodlar}


def giris_dogrula(user_id, kod: str) -> bool:
    """Girişte çağrılır: TOTP kodu doğruysa True; değilse kurtarma kodlarını
    dener ve eşleşeni TÜKETİR. 2FA kapalıysa True (kapı yok)."""
    kod = _temiz(kod)
    with sistem_baglami() as s:
        row = s.execute(text("SELECT totp_secret, totp_zarf, totp_aktif, totp_son_adim FROM users WHERE id=:i"),
                        {"i": user_id}).first()
        sirr = _sir.oku(getattr(row, "totp_zarf", None), getattr(row, "totp_secret", None), f"users:{user_id}:totp") if row is not None else None
        if row is None or not row.totp_aktif or not sirr:
            return True
        ok, adim = _sir.totp_dogrula(sirr, kod, getattr(row, "totp_son_adim", None))   # v2.570: aynı kod ikinci kez geçmez
        if ok and _adim_yaz(s, "users", user_id, adim):
            return True
        # kurtarma kodu mu? (kısa devre yok — kullanılmamış her kodu dener)
        adaylar = s.execute(text(
            "SELECT id, kod_hash FROM kurtarma_kodlari "
            "WHERE user_id=:i AND kullanildi_at IS NULL"), {"i": user_id}).all()
        ham = (kod or "").replace("-", "").lower()
        for aday in adaylar:
            if ham and bcrypt.verify(ham, aday.kod_hash):
                s.execute(text("UPDATE kurtarma_kodlari SET kullanildi_at=now() WHERE id=:k"),
                          {"k": aday.id})
                return True
    return False


def yonetici_sifirla(tenant_id, user_id) -> bool:
    """v2.339 — KİLİTLENME ÇIKIŞI: telefonunu ve kurtarma kodlarını birlikte
    kaybeden üyenin 2FA'sını yöneticisi kapatır (kullanıcı sonra yeniden kurar).
    Bu olmadan tek çare hesabı pasifleştirip sıfırdan açmaktı — geçmiş kopardı.
    Kapsam AYNI KİRACI ile sınırlıdır: yönetici başka kurumun üyesine dokunamaz.
    Dönüş False = o kiracıda böyle bir üye yok."""
    with sistem_baglami() as s:
        r = s.execute(text(
            "UPDATE users SET totp_secret=NULL, totp_zarf=NULL, totp_son_adim=NULL, totp_aktif=false, oturum_surumu = oturum_surumu + 1 "
            "WHERE id=:u AND tenant_id=:t"), {"u": user_id, "t": tenant_id})   # 24.10 Faz 0: açık jetonlar düşer
        if r.rowcount == 0:
            return False
        s.execute(text("DELETE FROM kurtarma_kodlari WHERE user_id=:u"), {"u": user_id})
        from pvquant.services.auth_service import oturum_onbellegi_dusur
        oturum_onbellegi_dusur(user_id)
    return True


# ---- yardımcılar --------------------------------------------------------
def _adim_yaz(s, tablo: str, kimlik, adim: int | None) -> bool:
    """v2.570: kabul edilen zaman adımını ATOMİK yazar; başka bir istek aynı/yeni adımı önce yazdıysa 0 satır → red (eşzamanlı tekrar)."""
    if adim is None:
        return False
    r = s.execute(text(f"UPDATE {tablo} SET totp_son_adim=:a WHERE id=:i AND (totp_son_adim IS NULL OR totp_son_adim < :a)"), {"a": int(adim), "i": kimlik})
    return getattr(r, "rowcount", 1) != 0


def _temiz(kod: str) -> str:
    return (kod or "").strip().replace(" ", "")


def _kurtarma_uret(s, user_id) -> list[str]:
    kodlar = []
    for _ in range(_KURTARMA_ADET):
        ham = secrets.token_hex(4)              # 8 hex
        kodlar.append(f"{ham[:4]}-{ham[4:]}")   # xxxx-xxxx (gösterim)
        s.execute(text(
            "INSERT INTO kurtarma_kodlari(user_id, kod_hash) VALUES(:u, :h)"),
            {"u": user_id, "h": bcrypt.hash(ham)})   # tireli değil, ham hex saklanır
    return kodlar


def _qr_svg(uri: str) -> str:
    img = qrcode.make(uri, image_factory=SvgPathImage, box_size=9, border=2)
    buf = io.BytesIO()
    img.save(buf)
    return buf.getvalue().decode()
