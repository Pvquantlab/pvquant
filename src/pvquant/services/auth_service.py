"""Kimlik: kayit, giris, JWT. 3 rol: viewer|editor|admin."""
from __future__ import annotations
import os, datetime as dt
import jwt
from passlib.hash import bcrypt
from sqlalchemy import text
from pvquant.db import sistem_baglami

JWT_SAAT = 12


def _sir() -> str:
    """v2.79 — bos sir gurultuyle reddedilir (gece vakasi: compose'un
    ${PVQ_JWT_SECRET:-} kalibi degiskeni BOS DIZEyle set eder; get'in
    varsayilani devreye girmez, jwt 'HMAC key must not be empty' ile
    sessizce 500 verirdi). Bos != yok: bos -> aciklamali hata;
    hic yok -> yerel dev varsayilani (davranis genisletilmedi)."""
    s = os.environ.get("PVQ_JWT_SECRET")
    if s == "":
        raise RuntimeError(
            "PVQ_JWT_SECRET BOS dize — .env'e gercek sir yazin "
            "(openssl rand -hex 32). Bos sirla oturum imzalanmaz.")
    return s if s is not None else "dev-secret-DEGISTIR"


def tenant_ve_admin_olustur(firma_adi, email, sifre):
    with sistem_baglami() as s:
        tid = s.execute(text(
            "INSERT INTO tenants(name) VALUES(:n) RETURNING id"),
            {"n": firma_adi}).scalar()
        uid = s.execute(text(
            "INSERT INTO users(tenant_id,email,pw_hash,role) "
            "VALUES(:t,:e,:h,'admin') RETURNING id"),
            {"t": tid, "e": email.lower(), "h": bcrypt.hash(sifre)}).scalar()
    return str(tid), str(uid)


def kullanici_davet(tenant_id, email, sifre, role):
    assert role in ("viewer", "editor", "admin")
    with sistem_baglami() as s:
        return str(s.execute(text(
            "INSERT INTO users(tenant_id,email,pw_hash,role) "
            "VALUES(:t,:e,:h,:r) RETURNING id"),
            {"t": tenant_id, "e": email.lower(),
             "h": bcrypt.hash(sifre), "r": role}).scalar())


def giris(email, sifre) -> dict | None:
    with sistem_baglami() as s:
        row = s.execute(text(
            "SELECT id, tenant_id, pw_hash, role, aktif FROM users "
            "WHERE email=:e"), {"e": email.lower()}).first()
        if not row or not row.aktif or not bcrypt.verify(sifre, row.pw_hash):
            return None   # v2.299: pasif hesap da 'hatalı' der — hesap varlığı sızdırılmaz
        s.execute(text("UPDATE users SET last_login=now() WHERE id=:i"),
                  {"i": row.id})
    token = jwt.encode({
        "sub": str(row.id), "tenant_id": str(row.tenant_id),
        "role": row.role,
        "exp": dt.datetime.utcnow() + dt.timedelta(hours=JWT_SAAT)},
        _sir(), algorithm="HS256")
    return {"token": token, "user_id": str(row.id),
            "tenant_id": str(row.tenant_id), "role": row.role}


def token_coz(token) -> dict | None:
    try:
        return jwt.decode(token, _sir(), algorithms=["HS256"])
    except jwt.PyJWTError:
        return None


# ---------------- v2.299: ekip yönetimi ----------------
ROLLER = ("viewer", "editor", "admin")


def takim_listesi(tenant_id) -> list[dict]:
    with sistem_baglami() as s:
        rows = s.execute(text(
            "SELECT id, email, role, aktif, last_login, created_at FROM users "
            "WHERE tenant_id=:t ORDER BY created_at"), {"t": tenant_id}).mappings().all()
    return [{"id": str(r["id"]), "email": r["email"], "rol": r["role"], "aktif": bool(r["aktif"]),
             "son_giris": r["last_login"].isoformat() if r["last_login"] else None,
             "olusturma": r["created_at"].isoformat() if r["created_at"] else None} for r in rows]


def kullanici_ekle(tenant_id, email: str, role: str) -> dict:
    """Geçici parolayı SUNUCU üretir ve YALNIZ bu yanıtta gösterir (API anahtarı kalıbı);
    kullanıcı ilk girişten sonra kendi parolasını değiştirir."""
    import secrets
    email = (email or "").strip().lower()
    if role not in ROLLER:
        raise ValueError(f"rol: {ROLLER}")
    if "@" not in email or "." not in email.split("@")[-1]:
        raise ValueError("geçerli bir e-posta girin")
    with sistem_baglami() as s:
        if s.execute(text("SELECT 1 FROM users WHERE email=:e"), {"e": email}).first():
            raise ValueError("bu e-posta zaten kayıtlı")
        gecici = secrets.token_urlsafe(9)
        uid = s.execute(text(
            "INSERT INTO users(tenant_id,email,pw_hash,role) VALUES(:t,:e,:h,:r) RETURNING id"),
            {"t": tenant_id, "e": email, "h": bcrypt.hash(gecici), "r": role}).scalar()
    return {"id": str(uid), "email": email, "rol": role, "gecici_parola": gecici}


def _etkin_admin_sayisi(s, tenant_id) -> int:
    return int(s.execute(text(
        "SELECT count(*) FROM users WHERE tenant_id=:t AND role='admin' AND aktif"), {"t": tenant_id}).scalar())


def kullanici_guncelle(tenant_id, user_id, rol: str | None = None, aktif: bool | None = None) -> bool:
    """Rol/durum değişimi. Son etkin yönetici düşürülemez ve pasifleştirilemez — kiracı kilitlenmesin."""
    if rol is not None and rol not in ROLLER:
        raise ValueError(f"rol: {ROLLER}")
    with sistem_baglami() as s:
        r = s.execute(text("SELECT role, aktif FROM users WHERE id=:i AND tenant_id=:t"),
                      {"i": user_id, "t": tenant_id}).first()
        if r is None:
            return False
        dusuruyor = r.role == "admin" and r.aktif and (
            (rol is not None and rol != "admin") or (aktif is not None and not aktif))
        if dusuruyor and _etkin_admin_sayisi(s, tenant_id) <= 1:
            raise ValueError("son etkin yönetici düşürülemez — önce başka bir yönetici atayın")
        s.execute(text("UPDATE users SET role=COALESCE(:r, role), aktif=COALESCE(:a, aktif) "
                       "WHERE id=:i AND tenant_id=:t"),
                  {"r": rol, "a": aktif, "i": user_id, "t": tenant_id})
    return True


def parola_degistir(user_id, eski: str, yeni: str) -> None:
    """Kullanıcının KENDİ parolası: eskisi doğrulanır, yenisi ≥ 10 karakter."""
    if len(yeni or "") < 10:
        raise ValueError("yeni parola en az 10 karakter olmalı")
    with sistem_baglami() as s:
        r = s.execute(text("SELECT pw_hash FROM users WHERE id=:i AND aktif"), {"i": user_id}).first()
        if r is None or not bcrypt.verify(eski or "", r.pw_hash):
            raise ValueError("mevcut parola hatalı")
        s.execute(text("UPDATE users SET pw_hash=:h WHERE id=:i"), {"i": user_id, "h": bcrypt.hash(yeni)})


def oturum_yenile(user_id) -> dict | None:
    """v2.300 — geçerli oturumdan yeni jeton. Rol/durum DB'den TAZE okunur: pasifleştirilen kullanıcı
    tazeleyemez, rolü değişen yeni rolüyle devam eder. Panel açıkken oturum kayarak uzar;
    kapalı tarayıcıda 12 saatlik ömür aynen geçerlidir."""
    with sistem_baglami() as s:
        row = s.execute(text("SELECT id, tenant_id, role, aktif FROM users WHERE id=:i"), {"i": user_id}).first()
    if row is None or not row.aktif:
        return None
    token = jwt.encode({
        "sub": str(row.id), "tenant_id": str(row.tenant_id), "role": row.role,
        "exp": dt.datetime.utcnow() + dt.timedelta(hours=JWT_SAAT)}, _sir(), algorithm="HS256")
    return {"token": token, "role": row.role}
