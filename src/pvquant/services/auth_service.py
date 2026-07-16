"""Kimlik: kayit, giris, JWT. 3 rol: viewer|editor|admin."""
from __future__ import annotations
import os, datetime as dt
import jwt
from passlib.hash import bcrypt
from sqlalchemy import text
from pvquant.db import sistem_baglami

JWT_SECRET = os.environ.get("PVQ_JWT_SECRET", "dev-secret-DEGISTIR")
JWT_SAAT = 12


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
            "SELECT id, tenant_id, pw_hash, role FROM users "
            "WHERE email=:e"), {"e": email.lower()}).first()
        if not row or not bcrypt.verify(sifre, row.pw_hash):
            return None
        s.execute(text("UPDATE users SET last_login=now() WHERE id=:i"),
                  {"i": row.id})
    token = jwt.encode({
        "sub": str(row.id), "tenant_id": str(row.tenant_id),
        "role": row.role,
        "exp": dt.datetime.utcnow() + dt.timedelta(hours=JWT_SAAT)},
        JWT_SECRET, algorithm="HS256")
    return {"token": token, "user_id": str(row.id),
            "tenant_id": str(row.tenant_id), "role": row.role}


def token_coz(token) -> dict | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
