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

# v2.73-B: dev SPA (vite, :5173) tarayici kapisi. Prod'da SPA ayni alan
# adindan (Caddy /v1) sunulur — oraya CORS gerekmez; liste env ile dar tutulur.
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=_os.environ.get(
        "PVQ_CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["GET", "POST"], allow_headers=["Authorization",
                                                  "Content-Type"])

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


def _kw(x):
    """JSON NaN tasiyamaz — NaN/None -> null, sayi -> 3 hane (kW)."""
    import math
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    return round(float(x), 3)


@app.get("/v1/plants/{plant_id}/forecast")
def forecast(plant_id: str, hours: int = 168,
             claims=Depends(gecerli_kullanici)):
    """v2.72 — son kosunun saatlik P10/P50/P90 serisi (ilk `hours` saat).

    Ince sargi: veri yolu forecast_service.son_kosu (tenant_baglami/RLS
    orada) + kosu_gecmisi(n=1) meta. Baska tenant'in santrali RLS'te
    bos doner -> 404; veri sizintisi yok. hours varsayilani 168 (7 gun,
    sartname); tavan 384 (16 gun ufku, v2.69).
    """
    from pvquant.services import forecast_service
    if not (1 <= hours <= 384):
        raise HTTPException(422, "hours 1-384 araliginda olmali")
    df = forecast_service.son_kosu(claims["tenant_id"], plant_id)
    if df is None:
        raise HTTPException(404, "tahmin kosusu yok")
    kosu = forecast_service.kosu_gecmisi(claims["tenant_id"], plant_id, n=1)
    df = df.iloc[:hours]
    return {
        "plant_id": plant_id,
        "run_at": kosu[0].run_at.isoformat() if kosu else None,
        "mode": kosu[0].mode if kosu else None,
        "hours": int(len(df)),
        "series": [
            {"ts_utc": ts.isoformat(), "p10_kw": _kw(r.p10_kw),
             "p50_kw": _kw(r.p50_kw), "p90_kw": _kw(r.p90_kw)}
            for ts, r in df.iterrows()
        ],
    }


@app.get("/v1/healthz")
def healthz():
    return {"ok": True}
