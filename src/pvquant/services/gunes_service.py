"""Gunes geometrisi — sunpath (Solargis Fig 2.3 gelenegi, v2.116).
pvlib solarposition ile santralin enlem/boylaminda uc karakteristik gunun
(yaz gundonumu, ekinoks, kis gundonumu) azimut x yukseklik egrileri +
saat basi isaretler. Salt hesap; DB'den yalniz plants okunur."""
from __future__ import annotations
import pandas as pd
from sqlalchemy import text
from pvquant.db import tenant_baglami

_GUNLER = [("yaz", "-06-21"), ("ekinoks", "-03-21"), ("kis", "-12-21")]


def gunes_yolu(tenant_id, plant_id, yil: int = 2026):
    import pvlib
    with tenant_baglami(tenant_id) as s:
        p = s.execute(text(
            "SELECT lat, lon, tz FROM plants WHERE id=:p"),
            {"p": plant_id}).mappings().first()
        if p is None:
            raise LookupError("santral yok: %s" % plant_id)
    tz = p["tz"] or "UTC"
    loc = pvlib.location.Location(float(p["lat"]), float(p["lon"]), tz=tz)
    egriler = []
    for ad, gun in _GUNLER:
        ts = pd.date_range(f"{yil}{gun} 00:00", f"{yil}{gun} 23:59",
                           freq="5min", tz=tz)
        sp = loc.get_solarposition(ts)
        gunduz = sp[sp.apparent_elevation > 0]
        saatler = gunduz[gunduz.index.minute == 0]
        egriler.append({
            "ad": ad,
            "nokta": [[round(float(a), 1), round(float(e), 1)]
                      for a, e in zip(gunduz.azimuth, gunduz.apparent_elevation)],
            "saat": [[round(float(a), 1), round(float(e), 1), int(h)]
                     for a, e, h in zip(saatler.azimuth,
                                        saatler.apparent_elevation,
                                        saatler.index.hour)]})
    return {"lat": float(p["lat"]), "lon": float(p["lon"]), "tz": tz,
            "yil": yil, "egriler": egriler}
