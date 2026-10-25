"""API bagimlilik enjeksiyonu: token dogrulama + rol kontrolu."""
import os
from fastapi import Header, HTTPException, Depends, Request
from pvquant.services import auth_service
from pvquant.services.auth_service import token_coz


def gecerli_kullanici(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Bearer token gerekli")
    c = token_coz(authorization.removeprefix("Bearer ").strip())
    if c is None:
        raise HTTPException(401, "Gecersiz/suresi dolmus token")
    # 24.10 Faz 1: platform (PVQuant personeli) jetonu müşteri uçlarını AÇAMAZ — iki yüz, iki kapsam.
    if c.get("kapsam") == "platform":
        raise HTTPException(403, "platform jetonu müşteri ucunda geçersiz")
    # 24.10 Faz 0: imza yetmez — oturum sürümü, aktiflik ve kiracı durumu DB'den (60 sn önbellek) doğrulanır.
    # `sv` iddiası olmayan eski jeton 0 sayılır: sürümü hiç artmamış kullanıcıda geçerli kalır (geriye uyumlu).
    d = auth_service.oturum_durumu(c["sub"])
    if d is None or not d["aktif"]:
        raise HTTPException(401, "hesap etkin değil")
    if d["kiraci_durum"] != "active":
        raise HTTPException(403, "hesap askıda")
    if int(c.get("sv", 0)) != d["sv"]:
        raise HTTPException(401, "oturum geçersiz; yeniden giriş yapın")
    return c  # {"sub","tenant_id","role","exp","sv"}


# 2FA kurulmadan açık kalan platform uçları: kim olduğunu görme, kurulum, parola, oturum tazeleme
PLATFORM_KURULUM_YOLLARI = frozenset({"/v1/yonetim/ben", "/v1/yonetim/iki-adim/baslat", "/v1/yonetim/iki-adim/dogrula",
                                      "/v1/yonetim/parola", "/v1/yonetim/oturum/yenile"})


def platform_yetkisi(rol: str | None = None):
    """24.10 Faz 1 — PLATFORM kapısı: yalnız `kapsam: platform` jetonu; platform_kullanicilar'dan aktiflik ve oturum
    sürümü (60 sn önbellek); `rol="sahip"` verilirse operatör 403. Müşteri jetonu burada 403: kapsamlar karışmaz."""
    def _ic(request: Request, authorization: str = Header(...)):
        from pvquant.services import platform_service
        if not authorization.startswith("Bearer "):
            raise HTTPException(401, "Bearer token gerekli")
        c = token_coz(authorization.removeprefix("Bearer ").strip())
        if c is None:
            raise HTTPException(401, "Gecersiz/suresi dolmus token")
        if c.get("kapsam") != "platform":
            raise HTTPException(403, "platform jetonu gerekli")
        d = platform_service.oturum_durumu(c["sub"])
        if d is None or not d["aktif"]:
            raise HTTPException(401, "hesap etkin değil")
        if int(c.get("sv", 0)) != d["sv"]:
            raise HTTPException(401, "oturum geçersiz; yeniden giriş yapın")
        # 25.10 denetim Y2: 2FA kurulu değilse jeton YALNIZ kurulum uçlarını açar (arayüz zaten dayatıyordu; artık API de).
        # Durum DB'den (60 sn önbellek; kurulum/sıfırlama önbelleği düşürür) — jeton değişmez, açık oturumlar bozulmaz.
        if not d.get("totp_aktif", False) and request.url.path not in PLATFORM_KURULUM_YOLLARI:
            raise HTTPException(403, "iki adımlı doğrulama kurulumu gerekli")
        if rol == "sahip" and d["rol"] != "sahip":
            raise HTTPException(403, "sahip yetkisi gerekli")
        return {**c, "rol": d["rol"], "email": d["email"]}
    return _ic


def yonetici_yetkisi():
    """v2.264: yalnız admin (API anahtarı ve webhook yönetimi)."""
    def _ic(claims=Depends(gecerli_kullanici)):
        if claims["role"] != "admin":
            raise HTTPException(403, "admin gerekli")
        return claims
    return _ic


def api_anahtari(kapsam: str):
    """v2.264: dış API kapısı — X-API-Key başlığı; kapsam zorunlu. 401 (geçersiz), 403 (kapsam), 429 (oran)."""
    def _ic(x_api_key: str = Header(..., alias="X-API-Key")):
        from pvquant.services import api_anahtar_service
        try:
            return api_anahtar_service.dogrula(x_api_key, kapsam)
        except PermissionError as e:
            raise HTTPException(403 if "kapsam" in str(e) else 401, str(e))
        except RuntimeError:
            raise HTTPException(429, "oran siniri: dakikalik istek hakki doldu")
    return _ic


def yazma_yetkisi():
    """editor/admin isteyen endpoint'ler icin Depends(yazma_yetkisi())."""
    def _ic(claims=Depends(gecerli_kullanici)):
        if claims["role"] not in ("editor", "admin"):
            raise HTTPException(403, "editor/admin gerekli")
        return claims
    return _ic
