"""PVQuant API — ince katman: HTTP -> services -> HTTP."""
from fastapi import FastAPI, Depends, HTTPException, Request
from pydantic import BaseModel
from apps.api.deps import gecerli_kullanici, yazma_yetkisi
from pvquant.services import auth_service, plant_service

import os as _os
try:
    import sentry_sdk
    if _os.environ.get("PVQ_SENTRY_DSN"):
        sentry_sdk.init(dsn=_os.environ["PVQ_SENTRY_DSN"],
                        traces_sample_rate=0)
except ImportError:
    pass  # sentry-sdk kurulu değilse sessiz geç (dev ortamı)

app = FastAPI(title="PVQuant API", version="0.1")

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


class GirisIstek(BaseModel):
    email: str
    sifre: str


@app.post("/v1/auth/login")
@limiter.limit("5/minute")
def login(request: Request, g: GirisIstek):
    r = auth_service.giris(g.email, g.sifre)
    if r is None:
        raise HTTPException(401, "hatali")
    return r


@app.get("/v1/plants")
def plants(claims=Depends(gecerli_kullanici)):
    return plant_service.listele(claims["tenant_id"])


class PlantIstek(BaseModel):
    name: str
    lat: float
    lon: float
    tz: str = "Europe/Istanbul"
    capacity_kwp: float
    tilt: float | None = None
    azimuth: float | None = None
    panel_tech: str = "bifacial"


@app.post("/v1/plants")
def plant_ekle(p: PlantIstek, claims=Depends(yazma_yetkisi())):
    return {"id": plant_service.olustur(claims["tenant_id"], **p.model_dump())}


@app.get("/v1/healthz")
def healthz():
    return {"ok": True}
