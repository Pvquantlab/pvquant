"""Santral kutuphanesi: listele, olustur, getir, guncelle.
Tum sorgular tenant_baglami icinde (RLS)."""
from sqlalchemy import text
from pvquant.db import tenant_baglami


def listele(tenant_id):
    with tenant_baglami(tenant_id) as s:
        return [dict(r._mapping) for r in s.execute(text(
            "SELECT id,name,capacity_kwp,lat,lon,tz,tilt,azimuth,panel_tech"
            " FROM plants ORDER BY name"))]


def olustur(tenant_id, *, name, lat, lon, tz, capacity_kwp,
            tilt=None, azimuth=None, panel_tech="bifacial"):
    with tenant_baglami(tenant_id) as s:
        return str(s.execute(text(
            "INSERT INTO plants(tenant_id,name,lat,lon,tz,capacity_kwp,"
            " tilt,azimuth,panel_tech) VALUES(:t,:n,:la,:lo,:tz,:c,:ti,:az,:pt)"
            " RETURNING id"),
            {"t": tenant_id, "n": name, "la": lat, "lo": lon, "tz": tz,
             "c": capacity_kwp, "ti": tilt, "az": azimuth,
             "pt": panel_tech}).scalar())


def getir(tenant_id, plant_id):
    with tenant_baglami(tenant_id) as s:
        r = s.execute(text("SELECT * FROM plants WHERE id=:p"),
                      {"p": plant_id}).first()
    return dict(r._mapping) if r else None


def guncelle(tenant_id, plant_id, **alanlar):
    if not alanlar: return
    izinli = {"name","lat","lon","tz","capacity_kwp","tilt","azimuth","panel_tech"}
    kume = {k: v for k, v in alanlar.items() if k in izinli}
    sset = ", ".join(f"{k}=:{k}" for k in kume)
    with tenant_baglami(tenant_id) as s:
        s.execute(text(f"UPDATE plants SET {sset} WHERE id=:_p"),
                  {**kume, "_p": plant_id})
