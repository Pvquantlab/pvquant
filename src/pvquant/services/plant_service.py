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
        pid = str(s.execute(text(
            "INSERT INTO plants(tenant_id,name,lat,lon,tz,capacity_kwp,"
            " tilt,azimuth,panel_tech,ac_limit_kw)"
            " VALUES(:t,:n,:la,:lo,:tz,:c,:ti,:az,:pt,:ac)"
            " RETURNING id"),
            {"t": tenant_id, "n": name, "la": lat, "lo": lon, "tz": tz,
             "c": capacity_kwp, "ti": tilt, "az": azimuth,
             "pt": panel_tech, "ac": ac_limit_kw}).scalar())
    # v2.599 (F4-E): ilk künye sürümü (kaynak 'kayit') — tarihli kimlik kayıtla başlar
    from pvquant.services import santral_kunye_service
    santral_kunye_service.ilk_surum(tenant_id, pid, dc_kwp=capacity_kwp, ac_kw=ac_limit_kw)
    return pid


def getir(tenant_id, plant_id):
    with tenant_baglami(tenant_id) as s:
        r = s.execute(text("SELECT * FROM plants WHERE id=:p"),
                      {"p": plant_id}).first()
    return dict(r._mapping) if r else None


def guncelle(tenant_id, plant_id, aktor_id=None, **alanlar):
    """Güncel görünümü günceller. v2.599 (F4-E): kapasite/AC değişirse tarihli künyeye yeni sürüm açılır (plants çift yazılır) ve
    her güncelleme denetim izine düşer (önceki/yeni değerle)."""
    if not alanlar: return
    izinli = {"name","lat","lon","tz","capacity_kwp","tilt","azimuth","panel_tech","ac_limit_kw"}
    kume = {k: v for k, v in alanlar.items() if k in izinli}
    if not kume: return
    onceki = getir(tenant_id, plant_id) or {}
    guc = {k: kume[k] for k in ("capacity_kwp", "ac_limit_kw") if k in kume and _degisti(onceki.get(k), kume[k])}
    diger = {k: v for k, v in kume.items() if k not in guc}
    if diger:
        sset = ", ".join(f"{k}=:{k}" for k in diger)
        with tenant_baglami(tenant_id) as s:
            s.execute(text(f"UPDATE plants SET {sset} WHERE id=:_p"), {**diger, "_p": plant_id})
    if guc:
        from datetime import date as _date

        from pvquant.services import santral_kunye_service as _sk
        alan = {}
        if "capacity_kwp" in guc: alan["dc_kwp"] = guc["capacity_kwp"]
        if "ac_limit_kw" in guc: alan["ac_kw"] = guc["ac_limit_kw"]
        if _sk.guncel(tenant_id, plant_id) is None:   # künyesiz eski santral: önce mevcut değerlerle ilk sürüm
            _sk.ilk_surum(tenant_id, plant_id, dc_kwp=onceki.get("capacity_kwp"), ac_kw=onceki.get("ac_limit_kw"))
        _sk.yeni_surum(tenant_id, plant_id, gecerli_bas=_date.today(), aktor_id=aktor_id, kaynak="beyan", **alan)   # plants çift yazılır
    from pvquant.services import denetim_service
    denetim_service.kaydet("musteri", "santral_guncelle", aktor_id=aktor_id, tenant_id=tenant_id, nesne_tur="plant", nesne_id=plant_id,
                           ayrinti={"yeni": kume, "onceki": {k: onceki.get(k) for k in kume}})


def _degisti(a, b) -> bool:
    try:
        return (a is None) != (b is None) or (a is not None and abs(float(a) - float(b)) > 1e-9)
    except (TypeError, ValueError):
        return a != b
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

# ---------------- v2.303: yaşam döngüsünün öbür ucu ----------------
def arsivli_listele(tenant_id):
    from sqlalchemy import text

    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        return [dict(r._mapping) for r in s.execute(text(
            "SELECT id, name, capacity_kwp FROM plants WHERE archived ORDER BY name"))]


def arsivle(tenant_id, plant_id) -> dict:
    """v2.54 sözleşmesi uçtan erişilir oldu: SİLMEZ, arşivler — veri denetim için yerinde kalır,
    santral listelerden ve gece koşularından çekilir. Koruma: son etkin santral arşivlenemez
    (panel santralsız kalmasın; önce yenisini bağlayın)."""
    from sqlalchemy import text

    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        etkin = s.execute(text("SELECT count(*) FROM plants WHERE NOT archived")).scalar()
        if int(etkin) <= 1:
            raise ValueError("son etkin santral arşivlenemez — önce yeni bir santral bağlayın")
        n = s.execute(text("UPDATE plants SET archived=true WHERE id=:p AND NOT archived"), {"p": plant_id}).rowcount
    return {"arsivlendi": n > 0}


def geri_al(tenant_id, plant_id) -> dict:
    from sqlalchemy import text

    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        n = s.execute(text("UPDATE plants SET archived=false WHERE id=:p AND archived"), {"p": plant_id}).rowcount
    return {"geri_alindi": n > 0}
