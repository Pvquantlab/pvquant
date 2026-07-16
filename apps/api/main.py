"""PVQuant API — ince katman: HTTP -> services -> HTTP."""
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from apps.api.deps import gecerli_kullanici, yazma_yetkisi
from pvquant.services import auth_service, plant_service

app = FastAPI(title="PVQuant API", version="0.1")


class GirisIstek(BaseModel):
    email: str
    sifre: str


@app.post("/v1/auth/login")
def login(g: GirisIstek):
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
