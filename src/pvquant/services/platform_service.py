"""24.10 Faz 1 — PLATFORM KİMLİĞİ ve MÜŞTERİ YÖNETİMİ (PVQuant personeli).

Kimlik modeli (docs/YONETICI-PANELI-YOL-HARITASI-2026-10-24.md §3): platform kullanıcıları AYRI tabloda
(platform_kullanicilar), kiracıya bağlı değil. Jeton iddiaları {sub, kapsam:"platform", rol, sv, exp ≤ 4 sa};
müşteri jetonundan kapsamla ayrılır ve iki yüz birbirinin ucunu açamaz (deps). İki adımlı doğrulama: açıksa zorunlu;
açık değilse giriş yine olur ama yanıt `iki_adim_kurulmali: true` taşır (ilk sahip kurulumu için; Faz 2 arayüzü
kurulumu dayatır). Parola bcrypt, TOTP pyotp (valid_window=1); kurtarma kodu bu fazda yok (telefon kaybı → başka sahip
`operator_guncelle` ile 2FA'yı sıfırlar; tek sahipse CLI).

Kiracı işleri RLS dışı çalışır (platform_baglami: aktörlü, izli). Kiracı oluşturma: tenants + ilk admin (rastgele
parola, KİMSEYE gösterilmez) + 72 saatlik davet bağlantısı (parola_sifirlama tablosu, mevcut /parola-yenile akışı).
Posta yapılandırılmamışsa bağlantı yanıtta döner ki operatör elden iletsin (bir kez görünür; denetim izine YAZILMAZ)."""
from __future__ import annotations

import datetime as dt
import os
import secrets
import time

import jwt
import pyotp
from passlib.hash import bcrypt
from sqlalchemy import text

from pvquant.db import sistem_baglami, platform_baglami
from pvquant.services import auth_service

ROLLER = ("operator", "sahip")
JWT_SAAT = 4
DAVET_SAAT = 72
ONBELLEK_SN = 60
_ISSUER = "PVQuant Platform"
_onbellek: dict[str, tuple[float, dict | None]] = {}


class PlatformHata(ValueError):
    """Kullanıcıya gösterilebilir, 422'ye çevrilen hata."""


# ---------------- kimlik ----------------
def _jeton(row, ilk: int | None = None) -> str:
    """ilk: oturumun İLK giriş anı (epoch sn) — yenilemelerde taşınır; deps.platform_yetkisi MUTLAK_SAAT sonra 401 (25.10 O8)."""
    return jwt.encode({"sub": str(row.id), "kapsam": "platform", "rol": row.rol, "sv": int(row.oturum_surumu),
                       "ilk": int(ilk or time.time()),
                       "exp": dt.datetime.utcnow() + dt.timedelta(hours=JWT_SAAT)}, auth_service._sir(), algorithm="HS256")


_KUKLA_HASH = bcrypt.hash("kukla-" + "x" * 16)   # yalnız zamanlama eşitlemek için; hiçbir parolayla eşleşmez


def giris(email: str, sifre: str, kod: str | None = None) -> dict | None:
    """None = hatalı (varlık sızdırılmaz); {"iki_adim_gerekli": True} = parola doğru, kod şart;
    {token, rol, email, iki_adim_kurulmali} = oturum açıldı."""
    with sistem_baglami() as s:
        row = s.execute(text(
            "SELECT id, email, pw_hash, rol, aktif, totp_secret, totp_aktif, oturum_surumu "
            "FROM platform_kullanicilar WHERE email=:e"), {"e": (email or "").strip().lower()}).first()
        if not row:
            bcrypt.verify(sifre or "", _KUKLA_HASH)   # 26.10 denetim-3: hesap yokken de bcrypt koşar — zamanlamayla varlık sızmasın
            return None
        dogru = bcrypt.verify(sifre or "", row.pw_hash)   # pasif hesapta da koşar (kısa devre 6 ms ↔ 280 ms varlığı ele veriyordu)
        if not row.aktif or not dogru:
            return None
    if row.totp_aktif:
        if not kod:
            return {"iki_adim_gerekli": True}
        if not pyotp.TOTP(row.totp_secret).verify((kod or "").replace(" ", ""), valid_window=1):
            return None
    with sistem_baglami() as s:
        s.execute(text("UPDATE platform_kullanicilar SET last_login=now() WHERE id=:i"), {"i": row.id})
    return {"token": _jeton(row), "rol": row.rol, "email": row.email, "iki_adim_kurulmali": not row.totp_aktif}


def yeniden_dogrula(pid: str, sifre: str | None, kod: str | None) -> bool:
    """26.10 denetim-3 (bağımsız kontrol 1.1): hassas sahip işlemleri (sahip hesabı açma/yükseltme, başkasının 2FA'sını sıfırlama)
    çalınmış bir JETONLA yapılamasın — aktörün parolası + TOTP kodu yeniden istenir. 2FA kurulu değilse (platform kapısı zaten
    yalnız kurulum uçlarını açar) parola yetmez: False."""
    with sistem_baglami() as s:
        r = s.execute(text("SELECT pw_hash, totp_secret, totp_aktif, aktif FROM platform_kullanicilar WHERE id=:i"), {"i": str(pid)}).first()
    if r is None or not r.aktif or not r.totp_aktif:
        bcrypt.verify(sifre or "", _KUKLA_HASH)
        return False
    if not bcrypt.verify(sifre or "", r.pw_hash):
        return False
    return bool(kod) and pyotp.TOTP(r.totp_secret).verify((kod or "").replace(" ", ""), valid_window=1)


def oturum_durumu(pid: str) -> dict | None:
    simdi = time.monotonic()
    k = _onbellek.get(str(pid))
    if k is not None and simdi - k[0] < ONBELLEK_SN:
        return k[1]
    with sistem_baglami() as s:
        r = s.execute(text("SELECT oturum_surumu, aktif, rol, email, totp_aktif FROM platform_kullanicilar WHERE id=:i"),
                      {"i": str(pid)}).first()
    # 25.10 denetim Y2: totp_aktif kapıda okunur — 2FA kurulmadan jeton yalnız kurulum uçlarını açar (deps.platform_yetkisi)
    d = None if r is None else {"sv": int(r.oturum_surumu), "aktif": bool(r.aktif), "rol": r.rol, "email": r.email,
                                "totp_aktif": bool(r.totp_aktif)}
    _onbellek[str(pid)] = (simdi, d)
    return d


def oturum_onbellegi_dusur(pid: str | None = None) -> None:
    if pid is None:
        _onbellek.clear()
    else:
        _onbellek.pop(str(pid), None)


def _surum_artir(s, pid) -> None:
    s.execute(text("UPDATE platform_kullanicilar SET oturum_surumu = oturum_surumu + 1 WHERE id=:i"), {"i": str(pid)})
    oturum_onbellegi_dusur(pid)


def oturum_yenile(pid: str, ilk: int | None = None) -> dict | None:
    with sistem_baglami() as s:
        row = s.execute(text("SELECT id, email, rol, aktif, totp_aktif, oturum_surumu FROM platform_kullanicilar WHERE id=:i"),
                        {"i": str(pid)}).first()
    if row is None or not row.aktif:
        return None
    return {"token": _jeton(row, ilk), "rol": row.rol, "email": row.email, "iki_adim_kurulmali": not row.totp_aktif}


def ben(pid: str) -> dict | None:
    with sistem_baglami() as s:
        r = s.execute(text("SELECT id, email, rol, totp_aktif, last_login, created_at FROM platform_kullanicilar WHERE id=:i"),
                      {"i": str(pid)}).first()
    return None if r is None else {"id": str(r.id), "email": r.email, "rol": r.rol, "totp_aktif": bool(r.totp_aktif),
                                   "son_giris": r.last_login.isoformat() if r.last_login else None,
                                   "olusturma": r.created_at.isoformat()}


def parola_degistir(pid: str, eski: str, yeni: str) -> None:
    if len(yeni or "") < 12:
        raise PlatformHata("yeni parola en az 12 karakter olmalı")
    with sistem_baglami() as s:
        r = s.execute(text("SELECT pw_hash FROM platform_kullanicilar WHERE id=:i AND aktif"), {"i": str(pid)}).first()
        if r is None or not bcrypt.verify(eski or "", r.pw_hash):
            raise PlatformHata("mevcut parola hatalı")
        s.execute(text("UPDATE platform_kullanicilar SET pw_hash=:h WHERE id=:i"), {"i": str(pid), "h": bcrypt.hash(yeni)})
        _surum_artir(s, pid)


def iki_adim_baslat(pid: str) -> dict:
    """Yeni sır üretir (etkinleştirme dogrula ile); açıksa önce kapatılmalı (bu fazda kapatma yalnız başka sahip eliyle)."""
    with sistem_baglami() as s:
        r = s.execute(text("SELECT email, totp_aktif FROM platform_kullanicilar WHERE id=:i"), {"i": str(pid)}).first()
        if r is None:
            raise PlatformHata("kullanıcı yok")
        if r.totp_aktif:
            raise PlatformHata("iki adımlı doğrulama zaten açık")
        sir = pyotp.random_base32()
        s.execute(text("UPDATE platform_kullanicilar SET totp_secret=:s WHERE id=:i"), {"s": sir, "i": str(pid)})
    uri = pyotp.totp.TOTP(sir).provisioning_uri(name=r.email, issuer_name=_ISSUER)
    return {"secret": sir, "otpauth_uri": uri}


def iki_adim_dogrula(pid: str, kod: str) -> None:
    with sistem_baglami() as s:
        r = s.execute(text("SELECT totp_secret, totp_aktif FROM platform_kullanicilar WHERE id=:i"), {"i": str(pid)}).first()
        if r is None or not r.totp_secret:
            raise PlatformHata("önce kurulumu başlatın")
        if not pyotp.TOTP(r.totp_secret).verify((kod or "").replace(" ", ""), valid_window=1):
            raise PlatformHata("kod doğrulanamadı")
        s.execute(text("UPDATE platform_kullanicilar SET totp_aktif=true WHERE id=:i"), {"i": str(pid)})
    oturum_onbellegi_dusur(pid)   # kapı 60 sn beklemeden tam kapsamı açsın


def parola_sifirla_cli(email: str, sifre: str) -> str:
    """26.10 denetim D4 — kilitlenme çıkışı (sunucuda, gizli girdiyle): parola yenilenir, açık oturumlar düşer, 2FA aynı kalır. Döner id."""
    if len(sifre or "") < 12:
        raise PlatformHata("parola en az 12 karakter olmalı")
    with sistem_baglami() as s:
        pid = s.execute(text("UPDATE platform_kullanicilar SET pw_hash=:h, oturum_surumu = oturum_surumu + 1 WHERE email=:e AND aktif RETURNING id"),
                        {"h": bcrypt.hash(sifre), "e": email.strip().lower()}).scalar()
    if pid is None:
        raise PlatformHata("etkin hesap bulunamadı")
    oturum_onbellegi_dusur(str(pid))
    return str(pid)


def _plan_dogrula(plan: str | None) -> None:
    """26.10 denetim-2: bilinmeyen plan FK hatasıyla 500 vermesin — 422 «plan yok»."""
    with sistem_baglami() as s:
        if s.execute(text("SELECT 1 FROM planlar WHERE ad = :a"), {"a": plan or ""}).first() is None:
            raise PlatformHata(f"plan yok: {plan}")


# ---------------- platform kullanıcıları (operatörler) ----------------
def ilk_sahip_olustur(email: str, sifre: str) -> str:
    """Kurulum/CLI: ilk 'sahip'. Zaten sahip varsa CLI yine açabilir (kilitlenme çıkışı) — denetim izine yazılır (çağıran)."""
    if len(sifre or "") < 12:
        raise PlatformHata("parola en az 12 karakter olmalı")
    with sistem_baglami() as s:
        return str(s.execute(text(
            "INSERT INTO platform_kullanicilar(email, pw_hash, rol) VALUES(:e, :h, 'sahip') RETURNING id"),
            {"e": email.strip().lower(), "h": bcrypt.hash(sifre)}).scalar())


def operator_listesi() -> list[dict]:
    with sistem_baglami() as s:
        rows = s.execute(text("SELECT id, email, rol, aktif, totp_aktif, last_login, created_at FROM platform_kullanicilar "
                              "ORDER BY created_at")).mappings().all()
    return [{"id": str(r["id"]), "email": r["email"], "rol": r["rol"], "aktif": bool(r["aktif"]),
             "totp_aktif": bool(r["totp_aktif"]), "son_giris": r["last_login"].isoformat() if r["last_login"] else None,
             "olusturma": r["created_at"].isoformat()} for r in rows]


def operator_ekle(email: str, rol: str) -> dict:
    """Geçici parola YALNIZ yanıtta; yeni operatör ilk girişte parolasını değiştirir ve 2FA kurar."""
    if rol not in ROLLER:
        raise PlatformHata(f"rol: {ROLLER}")
    email = (email or "").strip().lower()
    if "@" not in email:
        raise PlatformHata("geçerli e-posta gerekli")
    gecici = secrets.token_urlsafe(12)
    with sistem_baglami() as s:
        if s.execute(text("SELECT 1 FROM platform_kullanicilar WHERE email=:e"), {"e": email}).first():
            raise PlatformHata("bu e-posta zaten kayıtlı")
        pid = s.execute(text("INSERT INTO platform_kullanicilar(email, pw_hash, rol) VALUES(:e, :h, :r) RETURNING id"),
                        {"e": email, "h": bcrypt.hash(gecici), "r": rol}).scalar()
    return {"id": str(pid), "email": email, "rol": rol, "gecici_parola": gecici}


def operator_guncelle(pid: str, *, rol: str | None = None, aktif: bool | None = None, iki_adim_sifirla: bool = False) -> bool:
    if rol is not None and rol not in ROLLER:
        raise PlatformHata(f"rol: {ROLLER}")
    with sistem_baglami() as s:
        r = s.execute(text("SELECT rol, aktif FROM platform_kullanicilar WHERE id=:i"), {"i": str(pid)}).first()
        if r is None:
            return False
        dusuruyor = r.rol == "sahip" and r.aktif and ((rol is not None and rol != "sahip") or (aktif is not None and not aktif))
        if dusuruyor and int(s.execute(text("SELECT count(*) FROM platform_kullanicilar WHERE rol='sahip' AND aktif")).scalar()) <= 1:
            raise PlatformHata("son etkin sahip düşürülemez")
        s.execute(text("UPDATE platform_kullanicilar SET rol=COALESCE(:r, rol), aktif=COALESCE(:a, aktif)"
                       + (", totp_secret=NULL, totp_aktif=false" if iki_adim_sifirla else "") + " WHERE id=:i"),
                  {"r": rol, "a": aktif, "i": str(pid)})
        _surum_artir(s, pid)
    return True


# ---------------- kiracılar ----------------
def kiraci_listesi(aktor_id: str) -> list[dict]:
    with platform_baglami(aktor_id) as s:
        rows = s.execute(text("""
            SELECT t.id, t.name, t.plan, t.status, t.created_at, t.updated_at, t.notlar,
                   (SELECT count(*) FROM plants p WHERE p.tenant_id=t.id AND NOT p.archived) AS santral,
                   (SELECT coalesce(sum(p.capacity_kwp),0) FROM plants p WHERE p.tenant_id=t.id AND NOT p.archived) AS kwp,
                   (SELECT count(*) FROM users u WHERE u.tenant_id=t.id AND u.aktif) AS kullanici,
                   (SELECT max(u.last_login) FROM users u WHERE u.tenant_id=t.id) AS son_giris
            FROM tenants t ORDER BY t.created_at""")).mappings().all()
    return [{"id": str(r["id"]), "ad": r["name"], "plan": r["plan"], "durum": r["status"],
             "olusturma": r["created_at"].isoformat(), "guncelleme": r["updated_at"].isoformat() if r["updated_at"] else None,
             "notlar": r["notlar"], "santral": int(r["santral"]), "kurulu_guc_kwp": float(r["kwp"]),
             "kullanici": int(r["kullanici"]), "son_giris": r["son_giris"].isoformat() if r["son_giris"] else None}
            for r in rows]


def kiraci_detay(aktor_id: str, tid: str) -> dict | None:
    with platform_baglami(aktor_id) as s:
        t = s.execute(text("SELECT id, name, plan, status, created_at, updated_at, notlar, yonetici_2fa_zorunlu FROM tenants WHERE id=:t"),
                      {"t": str(tid)}).mappings().first()
        if t is None:
            return None
        kullanicilar = s.execute(text(
            "SELECT id, email, role, aktif, totp_aktif, last_login, created_at FROM users WHERE tenant_id=:t ORDER BY created_at"),
            {"t": str(tid)}).mappings().all()
        santraller = s.execute(text(
            "SELECT p.id, p.name, p.capacity_kwp, p.tz, p.archived, p.created_at, "
            "(SELECT max(ts_utc) FROM scada_hourly sh WHERE sh.plant_id=p.id AND sh.flag='valid') AS son_scada, "
            "(SELECT max(run_at) FROM forecast_runs r WHERE r.plant_id=p.id) AS son_kosu "
            "FROM plants p WHERE p.tenant_id=:t ORDER BY p.name"), {"t": str(tid)}).mappings().all()
    iso = lambda v: v.isoformat() if v else None  # noqa: E731
    return {"id": str(t["id"]), "ad": t["name"], "plan": t["plan"], "durum": t["status"], "notlar": t["notlar"],
            "olusturma": iso(t["created_at"]), "guncelleme": iso(t["updated_at"]), "yonetici_2fa_zorunlu": bool(t["yonetici_2fa_zorunlu"]),
            "kullanicilar": [{"id": str(u["id"]), "email": u["email"], "rol": u["role"], "aktif": bool(u["aktif"]),
                              "totp_aktif": bool(u["totp_aktif"]), "son_giris": iso(u["last_login"]), "olusturma": iso(u["created_at"])}
                             for u in kullanicilar],
            "santraller": [{"id": str(p["id"]), "ad": p["name"], "kapasite_kwp": float(p["capacity_kwp"]), "tz": p["tz"],
                            "arsivli": bool(p["archived"]), "olusturma": iso(p["created_at"]), "son_scada": iso(p["son_scada"]),
                            "son_kosu": iso(p["son_kosu"])} for p in santraller]}


def _davet_baglantisi(s, user_id, saat: int) -> str:
    jeton = secrets.token_urlsafe(32)
    s.execute(text("DELETE FROM parola_sifirlama WHERE user_id=:u AND used_at IS NULL"), {"u": str(user_id)})
    s.execute(text("INSERT INTO parola_sifirlama(user_id, token_hash, expires_at) "
                   "VALUES(:u, :h, now() + make_interval(hours => :sa))"),
              {"u": str(user_id), "h": auth_service._jeton_ozet(jeton), "sa": int(saat)})
    taban = os.environ.get("PVQ_TABAN_URL") or f"https://{os.environ.get('PVQ_DOMAIN') or 'localhost'}"
    return f"{taban}/parola-yenile?jeton={jeton}"


def _davet_postala(eposta: str, firma: str, baglanti: str, saat: int, ilk: bool) -> bool:
    from pvquant.services import posta_service
    govde = ("Merhaba,\n\n"
             + (f"{firma} için PVQuant hesabınız açıldı. " if ilk else f"PVQuant ({firma}) hesabınız için parola belirleme bağlantınız hazır. ")
             + f"Parolanızı belirlemek için aşağıdaki bağlantıyı kullanın; bağlantı {saat} saat geçerlidir ve tek kez kullanılabilir:\n\n"
             + f"{baglanti}\n\n"
             + "Girişten sonra Portföy → Hesap ve ekip bölümünden iki adımlı doğrulamayı açmanızı öneririz.\n\nPVQuant")
    return posta_service.gonder(eposta, "PVQuant — hesabınız hazır" if ilk else "PVQuant — parola belirleme", govde)


def kiraci_olustur(aktor_id: str, firma: str, yonetici_eposta: str, plan: str = "pilot", rol: str | None = None) -> dict:
    firma = (firma or "").strip(); eposta = (yonetici_eposta or "").strip().lower()
    if len(firma) < 2:
        raise PlatformHata("firma adı gerekli")
    if "@" not in eposta:
        raise PlatformHata("geçerli yönetici e-postası gerekli")
    _plan_dogrula(plan)
    with platform_baglami(aktor_id) as s:
        if s.execute(text("SELECT 1 FROM users WHERE email=:e"), {"e": eposta}).first():
            raise PlatformHata("bu e-posta başka bir hesapta kayıtlı")
        if s.execute(text("SELECT 1 FROM tenants WHERE lower(name)=lower(:n)"), {"n": firma}).first():
            raise PlatformHata("bu adla bir kiracı zaten var")
        tid = s.execute(text("INSERT INTO tenants(name, plan) VALUES(:n, :p) RETURNING id"), {"n": firma, "p": plan}).scalar()
        # ilk yönetici: parola RASTGELE ve kimseye gösterilmez — davet bağlantısıyla kendisi belirler
        uid = s.execute(text("INSERT INTO users(tenant_id, email, pw_hash, role) VALUES(:t, :e, :h, 'admin') RETURNING id"),
                        {"t": tid, "e": eposta, "h": bcrypt.hash(secrets.token_urlsafe(24))}).scalar()
        baglanti = _davet_baglantisi(s, uid, DAVET_SAAT)
    gonderildi = _davet_postala(eposta, firma, baglanti, DAVET_SAAT, ilk=True)
    return {"tenant_id": str(tid), "user_id": str(uid), "davet_gonderildi": gonderildi, **_baglanti_yaniti(gonderildi, baglanti, rol, "davet_baglantisi")}


def _baglanti_yaniti(gonderildi: bool, baglanti: str, rol: str | None, anahtar: str) -> dict:
    """26.10 denetim-3: posta gitmezse parola belirleme bağlantısı YALNIZ sahibe yanıtta düşer. Operatöre düşerse 24–72 saatlik
    bağlantıyla tam yazma yetkili müşteri hesabına girebilirdi (Faz 5'in «yalnız sahip, salt okunur» modeli boşa çıkar)."""
    if gonderildi:
        return {}
    if rol == "sahip":
        return {anahtar: baglanti, "not": "posta yapılandırılmamış ya da gönderilemedi; bağlantıyı elden iletin"}
    return {"not": "posta gönderilemedi; bağlantıyı yalnız sahip görebilir, sahipten isteyin"}


def kiraci_guncelle(aktor_id: str, tid: str, *, status: str | None = None, plan: str | None = None,
                    ad: str | None = None, notlar: str | None = None) -> dict | None:
    if status is not None and status not in ("active", "suspended"):
        raise PlatformHata("durum: active | suspended")
    if plan is not None:
        _plan_dogrula(plan)
    if ad is not None:
        ad = ad.strip()                     # 26.10 denetim-3 (1.3): oluşturmadaki kırpma + uzunluk kuralı güncellemede de
        if len(ad) < 2:
            raise PlatformHata("firma adı gerekli")
    with platform_baglami(aktor_id) as s:
        eski = s.execute(text("SELECT name, plan, status FROM tenants WHERE id=:t"), {"t": str(tid)}).mappings().first()
        if eski is None:
            return None
        if ad is not None and s.execute(text("SELECT 1 FROM tenants WHERE lower(name)=lower(:n) AND id<>:t"),
                                        {"n": ad, "t": str(tid)}).first():
            raise PlatformHata("bu adla bir kiracı zaten var")   # 26.10 denetim-3: oluşturmadaki benzersizlik güncellemede de
        s.execute(text("UPDATE tenants SET name=COALESCE(:n, name), plan=COALESCE(:p, plan), status=COALESCE(:s, status), "
                       "notlar=COALESCE(:no, notlar), updated_at=now() WHERE id=:t"),
                  {"n": ad, "p": plan, "s": status, "no": notlar, "t": str(tid)})
        if status is not None and status != eski["status"]:
            # askıya alma/açma: kiracının TÜM açık jetonları düşer (Faz 0 modeli), ≤60 sn içinde her işçide
            s.execute(text("UPDATE users SET oturum_surumu = oturum_surumu + 1 WHERE tenant_id=:t"), {"t": str(tid)})
    if status is not None and status != eski["status"]:
        auth_service.oturum_onbellegi_dusur()
    return {"eski": dict(eski), "yeni": {"name": ad or eski["name"], "plan": plan or eski["plan"], "status": status or eski["status"]}}


# ---------------- kiracı kullanıcıları ----------------
def kullanici_ara(aktor_id: str, q: str = "", limit: int = 100) -> list[dict]:
    with platform_baglami(aktor_id) as s:
        rows = s.execute(text(
            "SELECT u.id, u.email, u.role, u.aktif, u.totp_aktif, u.last_login, u.created_at, t.id AS tid, t.name AS firma "
            "FROM users u JOIN tenants t ON t.id=u.tenant_id "
            "WHERE (:q = '' OR u.email ILIKE :qq OR t.name ILIKE :qq) ORDER BY t.name, u.email LIMIT :n"),
            {"q": q or "", "qq": f"%{q}%", "n": max(1, min(int(limit), 500))}).mappings().all()
    return [{"id": str(r["id"]), "email": r["email"], "rol": r["role"], "aktif": bool(r["aktif"]), "totp_aktif": bool(r["totp_aktif"]),
             "son_giris": r["last_login"].isoformat() if r["last_login"] else None, "olusturma": r["created_at"].isoformat(),
             "tenant_id": str(r["tid"]), "firma": r["firma"]} for r in rows]


def kullanici_getir(aktor_id: str, uid: str) -> dict | None:
    with platform_baglami(aktor_id) as s:
        r = s.execute(text("SELECT u.id, u.email, u.tenant_id, u.role, u.aktif, t.name AS firma FROM users u JOIN tenants t ON t.id=u.tenant_id WHERE u.id=:i"),
                      {"i": str(uid)}).mappings().first()
    return None if r is None else {"id": str(r["id"]), "email": r["email"], "tenant_id": str(r["tenant_id"]), "rol": r["role"],
                                   "aktif": bool(r["aktif"]), "firma": r["firma"]}


def davet_gonder(aktor_id: str, uid: str, saat: int = 24, rol: str | None = None) -> dict | None:
    """Operatör eliyle parola belirleme bağlantısı (destek: 'parolamı unuttum' çalışmayanlar). Kullanıcı etkin olmalı.
    Posta gitmezse bağlantı yalnız sahibe döner (_baglanti_yaniti)."""
    from pvquant.services import posta_service
    k = kullanici_getir(aktor_id, uid)
    if k is None or not k["aktif"]:
        return None
    if rol != "sahip" and not posta_service.yapilandirildi():
        # 26.10 denetim-3 (bağımsız kontrol 3): operatör göremeyeceği jetonu üretmesin — müşterinin bekleyen bağlantısı da bozulmasın
        return {"gonderildi": False, **_baglanti_yaniti(False, "", rol, "baglanti")}
    with platform_baglami(aktor_id) as s:
        baglanti = _davet_baglantisi(s, uid, saat)
    gonderildi = _davet_postala(k["email"], k["firma"], baglanti, saat, ilk=False)
    if not gonderildi and rol != "sahip":
        with platform_baglami(aktor_id) as s:   # posta arızası: kimsenin görmeyeceği canlı jeton DB'de kalmasın
            s.execute(text("DELETE FROM parola_sifirlama WHERE user_id=:u AND used_at IS NULL"), {"u": str(uid)})
    return {"gonderildi": gonderildi, **_baglanti_yaniti(gonderildi, baglanti, rol, "baglanti")}


# ---------------- 26.10 Faz 5: planlar (uyarı kipi) ----------------
PLAN_LIMITLER = ("santral_limit", "kullanici_limit", "api_rpm_limit", "aylik_rapor_limit", "aylik_dis_api_limit")
LIMIT_UST = 1_000_000_000   # planlar sütunları INTEGER; «sınırsız» için None kullanılır


def plan_listesi() -> list[dict]:
    with sistem_baglami() as s:
        rows = s.execute(text("SELECT ad, baslik, santral_limit, kullanici_limit, api_rpm_limit, aylik_rapor_limit, aylik_dis_api_limit, notlar, sira, "
                              "guncelleme, (SELECT count(*) FROM tenants t WHERE t.plan = p.ad) AS kiraci FROM planlar p ORDER BY sira, ad")).mappings().all()
    return [{"ad": r["ad"], "baslik": r["baslik"], **{k: r[k] for k in PLAN_LIMITLER}, "notlar": r["notlar"], "sira": int(r["sira"]),
             "guncelleme": r["guncelleme"].isoformat(), "kiraci": int(r["kiraci"])} for r in rows]


def plan_guncelle(ad: str, *, baslik: str | None = None, notlar: str | None = None, **limitler) -> dict | None:
    """Sahip: limitleri değiştirir (None = sınırsız; negatif reddedilir). Zorlama yok — rozetler yeni eşikle çizilir."""
    alanlar = {k: v for k, v in limitler.items() if k in PLAN_LIMITLER}
    for k, v in alanlar.items():
        if v is not None and int(v) < 0:
            raise PlatformHata(f"{k} negatif olamaz")
        if v is not None and int(v) > LIMIT_UST:
            raise PlatformHata(f"{k} en çok {LIMIT_UST}")   # 26.10 denetim-3: INTEGER taşması 500 veriyordu
    if baslik is not None and not baslik.strip():
        raise PlatformHata("başlık boş olamaz")
    with sistem_baglami() as s:
        eski = s.execute(text("SELECT ad FROM planlar WHERE ad = :a"), {"a": ad}).first()
        if eski is None:
            return None
        setler = [f"{k} = :{k}" for k in alanlar] + (["baslik = :baslik"] if baslik is not None else []) + (["notlar = :notlar"] if notlar is not None else [])
        if setler:
            s.execute(text(f"UPDATE planlar SET {', '.join(setler)}, guncelleme = now() WHERE ad = :a"),
                      {"a": ad, **{k: (None if v is None else int(v)) for k, v in alanlar.items()}, "baslik": baslik, "notlar": notlar})
    return next((x for x in plan_listesi() if x["ad"] == ad), None)


# ---------------- 26.10 Faz 5: kimliğe bürünme (salt okunur, 15 dk) ----------------
TEMSIL_DK = 15


def temsil_jetonu(aktor_id: str, tid: str) -> dict | None:
    """Sahip → kiracıyı MÜŞTERİ GÖZÜYLE, salt okunur: kapsam müşteri, rol viewer, `temsil` = platform aktörü, 15 dk.
    deps.gecerli_kullanici temsil jetonunu yalnız GET'te kabul eder; yazma kapıları ayrıca reddeder. Denetim izi çağıranda."""
    with sistem_baglami() as s:
        t = s.execute(text("SELECT id, name, status FROM tenants WHERE id = CAST(:t AS uuid)"), {"t": str(tid)}).first()
        d = oturum_durumu(aktor_id)
    if t is None:
        return None
    if t.status != "active":
        raise PlatformHata("kiracı askıda; görüntüleme açılmaz")
    if d is None or not d["aktif"]:
        raise PlatformHata("aktör etkin değil")
    bitis = dt.datetime.utcnow() + dt.timedelta(minutes=TEMSIL_DK)
    token = jwt.encode({"sub": str(aktor_id), "tenant_id": str(t.id), "role": "viewer", "sv": int(d["sv"]),
                        "temsil": str(aktor_id), "exp": bitis}, auth_service._sir(), algorithm="HS256")
    return {"token": token, "tenant_id": str(t.id), "kiraci": t.name, "sure_dk": TEMSIL_DK,
            "bitis": bitis.replace(tzinfo=dt.timezone.utc).isoformat()}


def kiraci_durumu(tid: str) -> str | None:
    with sistem_baglami() as s:
        return s.execute(text("SELECT status FROM tenants WHERE id = CAST(:t AS uuid)"), {"t": str(tid)}).scalar()
