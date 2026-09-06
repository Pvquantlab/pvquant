"""API bagimlilik enjeksiyonu: token dogrulama + rol kontrolu."""
from fastapi import Header, HTTPException, Depends
from pvquant.services.auth_service import token_coz


def gecerli_kullanici(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Bearer token gerekli")
    c = token_coz(authorization.removeprefix("Bearer ").strip())
    if c is None:
        raise HTTPException(401, "Gecersiz/suresi dolmus token")
    return c  # {"sub","tenant_id","role","exp"}


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
