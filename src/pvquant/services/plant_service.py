"""Santral kutuphanesi: listele, olustur, getir, guncelle.
Tum sorgular tenant_baglami icinde (RLS)."""
from sqlalchemy import text
from pvquant.db import tenant_baglami


def listele(tenant_id):
    with tenant_baglami(tenant_id) as s:
        return [dict(r._mapping) for r in s.execute(text(
            "SELECT id,name,capacity_kwp,lat,lon,tz,tilt,azimuth,panel_tech"
            " FROM plants WHERE NOT archived ORDER BY name"))]  # v2.54


def olustur(tenant_id, *, name, lat, lon, tz, capacity_kwp,
            tilt=None, azimuth=None, panel_tech="monofacial",
            ac_limit_kw=None):
    # v2.49: ad, tenant kapsaminda benzersiz (DB kisiti plants_tenant_name_uq).
    # Kisita carpan kayit, kullaniciya insan diliyle doner — olu uc yok.
    from sqlalchemy.exc import IntegrityError
    try:
        return _olustur_ic(tenant_id, name=name, lat=lat, lon=lon, tz=tz,
                           capacity_kwp=capacity_kwp, tilt=tilt, azimuth=azimuth,
                           panel_tech=panel_tech, ac_limit_kw=ac_limit_kw)
    except IntegrityError as e:
        if ("plants_tenant_name_uq" in str(e.orig)
                or "plants_tenant_lower_name_uq" in str(e.orig)):  # v2.49-B
            raise ValueError(
                f"'{name}' adinda bir santral zaten var. "
                "Farkli bir ad secin veya mevcut santrali kullanin.") from e
        raise


def _olustur_ic(tenant_id, *, name, lat, lon, tz, capacity_kwp,
                tilt, azimuth, panel_tech, ac_limit_kw):
    with tenant_baglami(tenant_id) as s:
        return str(s.execute(text(
            "INSERT INTO plants(tenant_id,name,lat,lon,tz,capacity_kwp,"
            " tilt,azimuth,panel_tech,ac_limit_kw)"
            " VALUES(:t,:n,:la,:lo,:tz,:c,:ti,:az,:pt,:ac)"
            " RETURNING id"),
            {"t": tenant_id, "n": name, "la": lat, "lo": lon, "tz": tz,
             "c": capacity_kwp, "ti": tilt, "az": azimuth,
             "pt": panel_tech, "ac": ac_limit_kw}).scalar())


def getir(tenant_id, plant_id):
    with tenant_baglami(tenant_id) as s:
        r = s.execute(text("SELECT * FROM plants WHERE id=:p"),
                      {"p": plant_id}).first()
    return dict(r._mapping) if r else None


def guncelle(tenant_id, plant_id, **alanlar):
    if not alanlar: return
    izinli = {"name","lat","lon","tz","capacity_kwp","tilt","azimuth","panel_tech","ac_limit_kw"}
    kume = {k: v for k, v in alanlar.items() if k in izinli}
    sset = ", ".join(f"{k}=:{k}" for k in kume)
    with tenant_baglami(tenant_id) as s:
        s.execute(text(f"UPDATE plants SET {sset} WHERE id=:_p"),
                  {**kume, "_p": plant_id})
def params_birlestir(tenant_id, plant_id, **anahtarlar) -> dict:
    """v2.260 — params_json'a anahtar ekle/güncelle (jsonb ||); öteki anahtarlar korunur."""
    import json as _json
    with tenant_baglami(tenant_id) as s:
        s.execute(text("UPDATE plants SET params_json = COALESCE(params_json, '{}'::jsonb) || CAST(:j AS jsonb) WHERE id=:p"),
                  {"j": _json.dumps(anahtarlar), "p": plant_id})
        r = s.execute(text("SELECT params_json FROM plants WHERE id=:p"), {"p": plant_id}).scalar()
    return r if isinstance(r, dict) else (_json.loads(r) if r else {})


def sil(tenant_id, plant_id) -> dict:
    """v2.54 (Sozlesme 4): SILMEZ, ARSIVLER. Tarih yerinde kalir.
    Santral listelerden ve koşulardan cekilir; olcum/kalibrasyon/tahmin
    gecmisi denetim icin durur. Geri alma: archived=false."""
    with tenant_baglami(tenant_id) as s:
        r = s.execute(text(
            "UPDATE plants SET archived=true WHERE id=:p AND NOT archived"),
            {"p": plant_id})
    return {"archived": r.rowcount}