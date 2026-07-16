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


def yazma_yetkisi():
    """editor/admin isteyen endpoint'ler icin Depends(yazma_yetkisi())."""
    def _ic(claims=Depends(gecerli_kullanici)):
        if claims["role"] not in ("editor", "admin"):
            raise HTTPException(403, "editor/admin gerekli")
        return claims
    return _ic
