"""v2.599 (Faz 4 F4-E, Stage 6) — SANTRAL KİMLİĞİ: tarihli künye (santral_kunye) ve güç tanımları tek yer.

Okuma: `guncel(tenant, plant_id, gun)` o tarihte geçerli künye; `tarihce` bütün sürümler. Yazma: `yeni_surum` eski satırı
kapatır (gecerli_bit = yeni gecerli_bas), yeni satırı ekler, `plants` güncel görünümüne ve `params_json` kimlik anahtarlarına
ÇİFT yazar (geriye uyum), denetim izine düşer. Güç tanımları `guc_tanimlari(plant, gun, kunye)`: DC / AC / EAK / ihracat sınırı
ve her birinin kaynağı — `kgup_service.eak_etkin`, EPİAŞ anomali tavanı, yükleme kapasite kuralı ve karne gündüz maskesi buradan
okur. Beyan (`params_json.dsg_kodu` / `toplayici_portfoyu`) portföy üyeliğine devreder: `beyan_uyarilari`.
Belge: docs/SANTRAL-KIMLIGI.md.
"""
from __future__ import annotations

import json
from datetime import date

from sqlalchemy import text

from pvquant.db import tenant_baglami

ALANLAR = ("dc_kwp", "ac_kw", "eak_kw", "baglanti_turu", "gerilim_kv", "segment", "lisans_durumu", "uevcb_kod", "eic", "epias_santral_id",
           "sayac_kimligi", "olcum_siniri")
SAYISAL = ("dc_kwp", "ac_kw", "eak_kw", "gerilim_kv")
BAGLANTI_TURLERI = ("iletim", "dagitim")
LISANS_DURUMLARI = ("lisansli", "lisanssiz", "muaf")
OLCUM_SINIRLARI = ("inverter_ac", "plant_gross_ac", "pcc_net", "settlement")
KAYNAKLAR = ("kayit", "beyan", "belge", "goc", "epias")
DOGRULAMALAR = ("beyan", "belgeli", "dogrulandi")
#: params_json'a çift yazılan kimlik anahtarları (künye alanı → params anahtarı)
PARAMS_ANAHTARI = {"eak_kw": "eak_kw", "segment": "segment", "uevcb_kod": "uevcb", "epias_santral_id": "epias_santral_id"}
SURUM = "2026-11-12"
BASLANGIC = date(2000, 1, 1)   # ilk sürüm «başlangıçtan beri» — geçmişe dönük düzeltme (devreye alma tarihi vb.) bu tarihten sonra her güne eklenebilir


def _uuid_mi(v) -> bool:
    import uuid as _u
    try:
        _u.UUID(str(v)); return True
    except (ValueError, TypeError, AttributeError):
        return False


def _pj(plant) -> dict:
    pj = plant.get("params_json") if hasattr(plant, "get") else None
    if isinstance(pj, str):
        try:
            return json.loads(pj)
        except ValueError:
            return {}
    return pj or {}


def _f(v):
    return None if v is None else float(v)


def _satir(r) -> dict:
    d = dict(r)
    for k in SAYISAL:
        d[k] = _f(d.get(k))
    for k in ("gecerli_bas", "gecerli_bit"):
        d[k] = d[k].isoformat() if d.get(k) is not None and hasattr(d[k], "isoformat") else d.get(k)
    d["id"] = int(d["id"]); d["plant_id"] = str(d["plant_id"]); d["tenant_id"] = str(d["tenant_id"])
    d["olusturan"] = str(d["olusturan"]) if d.get("olusturan") else None
    d["olusturma"] = d["olusturma"].isoformat() if d.get("olusturma") is not None else None
    return d


def guncel(tenant_id, plant_id, gun: date | None = None) -> dict | None:
    """`gun` tarihinde (varsayılan bugün) geçerli künye; yoksa None (göç öncesi/plant_service dışı eklenen santral)."""
    g = gun or date.today()
    if not _uuid_mi(plant_id):
        return None
    with tenant_baglami(tenant_id) as s:
        r = s.execute(text(
            "SELECT * FROM santral_kunye WHERE plant_id = CAST(:p AS uuid) AND gecerli_bas <= :g AND (gecerli_bit IS NULL OR gecerli_bit > :g) "
            "ORDER BY gecerli_bas DESC LIMIT 1"), {"p": str(plant_id), "g": g}).mappings().first()
    return _satir(r) if r else None


def tarihce(tenant_id, plant_id) -> list[dict]:
    if not _uuid_mi(plant_id):
        return []
    with tenant_baglami(tenant_id) as s:
        rows = s.execute(text("SELECT * FROM santral_kunye WHERE plant_id = CAST(:p AS uuid) ORDER BY gecerli_bas DESC, id DESC"),
                         {"p": str(plant_id)}).mappings().all()
    return [_satir(r) for r in rows]


def _dogrula(alanlar: dict) -> dict:
    out = {}
    for k, v in alanlar.items():
        if k not in ALANLAR:
            raise ValueError(f"bilinmeyen künye alanı: {k}")
        if v is None or v == "":
            out[k] = None; continue
        if k in SAYISAL:
            v = float(v)
            if v < 0:
                raise ValueError(f"{k} negatif olamaz")
            out[k] = v
        elif k == "baglanti_turu" and v not in BAGLANTI_TURLERI:
            raise ValueError(f"baglanti_turu {', '.join(BAGLANTI_TURLERI)} olmalı")
        elif k == "lisans_durumu" and v not in LISANS_DURUMLARI:
            raise ValueError(f"lisans_durumu {', '.join(LISANS_DURUMLARI)} olmalı")
        elif k == "olcum_siniri" and v not in OLCUM_SINIRLARI:
            raise ValueError(f"olcum_siniri {', '.join(OLCUM_SINIRLARI)} olmalı")
        else:
            out[k] = str(v).strip()[:64] if isinstance(v, str) else v
    if out.get("ac_kw") and out.get("dc_kwp") and out["ac_kw"] > 1.5 * out["dc_kwp"]:
        raise ValueError("ac_kw kurulu DC gücün 1,5 katını aşamaz (birim hatası olabilir)")
    return out


def yeni_surum(tenant_id, plant_id, *, gecerli_bas: date | str, aktor_id=None, kaynak: str = "beyan", dogrulama: str = "beyan",
               belge_adi: str | None = None, notlar: str | None = None, **alanlar) -> dict:
    """Yeni künye sürümü: önceki satır `gecerli_bas` ile kapanır; verilmeyen alanlar önceki sürümden taşınır; plants + params_json çift
    yazılır; denetim izi düşer. gecerli_bas geçmişte olabilir (geçmiş dönem yeniden hesabı için) ama var olan bir sürümün başlangıcından
    önce olamaz."""
    if kaynak not in KAYNAKLAR:
        raise ValueError(f"kaynak {', '.join(KAYNAKLAR)} olmalı")
    if dogrulama not in DOGRULAMALAR:
        raise ValueError(f"dogrulama {', '.join(DOGRULAMALAR)} olmalı")
    if dogrulama != "beyan" and not belge_adi:
        raise ValueError("belgeli/doğrulanmış künye için belge adı gerekir")
    g = date.fromisoformat(str(gecerli_bas)[:10]) if not isinstance(gecerli_bas, date) else gecerli_bas
    yeni = _dogrula(alanlar)
    with tenant_baglami(tenant_id) as s:
        onceki = s.execute(text("SELECT * FROM santral_kunye WHERE plant_id = CAST(:p AS uuid) AND gecerli_bit IS NULL ORDER BY gecerli_bas DESC LIMIT 1"),
                           {"p": str(plant_id)}).mappings().first()
        if onceki is not None and onceki["gecerli_bas"] > g:
            raise ValueError(f"gecerli_bas ({g.isoformat()}) mevcut sürümün başlangıcından ({onceki['gecerli_bas'].isoformat()}) sonra olmalı")
        tasinan = {k: onceki[k] for k in ALANLAR} if onceki is not None else {k: None for k in ALANLAR}
        for k in SAYISAL:
            tasinan[k] = _f(tasinan[k])
        satir = {**tasinan, **yeni}
        ayni_gun = onceki is not None and onceki["gecerli_bas"] == g
        if ayni_gun:
            # aynı gün ikinci düzeltme: sürüm satırı yerinde güncellenir (tarihçede tek satır/gün), iz denetim kaydında kalır
            s.execute(text(
                "UPDATE santral_kunye SET dc_kwp=:dc, ac_kw=:ac, eak_kw=:eak, baglanti_turu=:bt, gerilim_kv=:gk, segment=:seg, lisans_durumu=:ld, uevcb_kod=:uev, "
                " eic=:eic, epias_santral_id=:eps, sayac_kimligi=:say, olcum_siniri=:os, kaynak=:kay, dogrulama=:dog, belge_adi=:bel, notlar=:not, olusturan=:olu, olusturma=now() "
                "WHERE id = :i"),
                {"dc": satir["dc_kwp"], "ac": satir["ac_kw"], "eak": satir["eak_kw"], "bt": satir["baglanti_turu"], "gk": satir["gerilim_kv"], "seg": satir["segment"],
                 "ld": satir["lisans_durumu"], "uev": satir["uevcb_kod"], "eic": satir["eic"], "eps": satir["epias_santral_id"], "say": satir["sayac_kimligi"],
                 "os": satir["olcum_siniri"], "kay": kaynak, "dog": dogrulama, "bel": belge_adi, "not": notlar, "olu": str(aktor_id) if aktor_id else None, "i": onceki["id"]})
            kid = onceki["id"]
        elif onceki is not None:
            s.execute(text("UPDATE santral_kunye SET gecerli_bit = :g WHERE id = :i"), {"g": g, "i": onceki["id"]})
        if not ayni_gun:
            kid = s.execute(text(
            "INSERT INTO santral_kunye(tenant_id, plant_id, gecerli_bas, dc_kwp, ac_kw, eak_kw, baglanti_turu, gerilim_kv, segment, lisans_durumu, uevcb_kod, "
            " eic, epias_santral_id, sayac_kimligi, olcum_siniri, kaynak, dogrulama, belge_adi, notlar, olusturan) "
            "VALUES(CAST(:t AS uuid), CAST(:p AS uuid), :g, :dc, :ac, :eak, :bt, :gk, :seg, :ld, :uev, :eic, :eps, :say, :os, :kay, :dog, :bel, :not, :olu) RETURNING id"),
            {"t": str(tenant_id), "p": str(plant_id), "g": g, "dc": satir["dc_kwp"], "ac": satir["ac_kw"], "eak": satir["eak_kw"], "bt": satir["baglanti_turu"],
             "gk": satir["gerilim_kv"], "seg": satir["segment"], "ld": satir["lisans_durumu"], "uev": satir["uevcb_kod"], "eic": satir["eic"],
             "eps": satir["epias_santral_id"], "say": satir["sayac_kimligi"], "os": satir["olcum_siniri"], "kay": kaynak, "dog": dogrulama,
             "bel": belge_adi, "not": notlar, "olu": str(aktor_id) if aktor_id else None}).scalar()
        # çift yazım — güncel görünüm (yalnız yeni sürüm bugünü kapsıyorsa; geçmişe sürüm eklemek güncel görünümü değiştirmez)
        bugun = date.today()
        if g <= bugun:
            if "dc_kwp" in yeni or "ac_kw" in yeni:
                s.execute(text("UPDATE plants SET capacity_kwp = COALESCE(:dc, capacity_kwp), ac_limit_kw = :ac WHERE id = CAST(:p AS uuid)"),
                          {"dc": satir["dc_kwp"], "ac": satir["ac_kw"], "p": str(plant_id)})
            pj_ek = {PARAMS_ANAHTARI[k]: satir[k] for k in PARAMS_ANAHTARI if k in yeni}
            if pj_ek:
                s.execute(text("UPDATE plants SET params_json = COALESCE(params_json, '{}'::jsonb) || CAST(:j AS jsonb) WHERE id = CAST(:p AS uuid)"),
                          {"j": json.dumps(pj_ek), "p": str(plant_id)})
    from pvquant.services import denetim_service
    denetim_service.kaydet("musteri", "santral_kunye", aktor_id=aktor_id, tenant_id=tenant_id, nesne_tur="plant", nesne_id=plant_id,
                           ayrinti={"kunye_id": int(kid), "gecerli_bas": g.isoformat(), "degisen": {k: yeni[k] for k in yeni},
                                    "onceki": ({k: tasinan[k] for k in yeni} if onceki is not None else None), "kaynak": kaynak, "dogrulama": dogrulama})
    return guncel(tenant_id, plant_id, g) or {"id": int(kid)}


def ilk_surum(tenant_id, plant_id, *, dc_kwp, ac_kw=None, gecerli_bas: date | None = None, aktor_id=None) -> int | None:
    """Santral kaydında ilk künye (kaynak 'kayit', «başlangıçtan beri» = BASLANGIC); varsa dokunmaz."""
    with tenant_baglami(tenant_id) as s:
        var = s.execute(text("SELECT 1 FROM santral_kunye WHERE plant_id = CAST(:p AS uuid) LIMIT 1"), {"p": str(plant_id)}).scalar()
        if var:
            return None
        return s.execute(text(
            "INSERT INTO santral_kunye(tenant_id, plant_id, gecerli_bas, dc_kwp, ac_kw, kaynak, dogrulama, olusturan) "
            "VALUES(CAST(:t AS uuid), CAST(:p AS uuid), :g, :dc, :ac, 'kayit', 'beyan', :o) RETURNING id"),
            {"t": str(tenant_id), "p": str(plant_id), "g": gecerli_bas or BASLANGIC, "dc": _f(dc_kwp), "ac": _f(ac_kw), "o": str(aktor_id) if aktor_id else None}).scalar()


# ---- güç tanımları (saf) -----------------------------------------------------------------------------------------------
def guc_tanimlari(plant: dict, gun: date | None = None, kunye: dict | None = None) -> dict:
    """SAF. DC kurulu güç, AC tavanı, EAK (emre amade kapasite) ve ihracat sınırı — her biri kaynağıyla.
    Öncelik: künye (verilmişse) > plants sütunu > params_json. EAK kuralı (v2.275 ile aynı): geçici kısıt (bitişe kadar) > EAK alanı >
    AC tavanı > kurulu güç; EAK AC/DC'yi aşamaz. İhracat sınırı = EAK'nin kW hâli (program/anomali tavanı)."""
    gun = gun or date.today()
    pj = _pj(plant)
    k = kunye or {}
    dc = _f(k.get("dc_kwp")) or _f(plant.get("capacity_kwp"))
    dc_kaynak = "kunye" if k.get("dc_kwp") else "plants"
    ac = _f(k.get("ac_kw")) if k.get("ac_kw") is not None else _f(plant.get("ac_limit_kw"))
    ac_kaynak = ("kunye" if k.get("ac_kw") is not None else ("plants" if plant.get("ac_limit_kw") else None))
    eak_alani = _f(k.get("eak_kw")) if k.get("eak_kw") is not None else (_f(pj.get("eak_kw")) if pj.get("eak_kw") else None)
    kap_mw = (dc or 0.0) / 1000.0
    ac_mw = (ac / 1000.0) if ac else None
    eak: dict
    g = pj.get("eak_gecici") or {}
    try:
        if g.get("kw") and g.get("bitis") and date.fromisoformat(str(g["bitis"])) >= gun and float(g["kw"]) > 0:
            eak = {"eak_mw": round(min(float(g["kw"]) / 1000.0, ac_mw or kap_mw), 3), "kaynak": "gecici", "bitis": str(g["bitis"])}
        else:
            raise KeyError
    except (TypeError, ValueError, KeyError):
        if eak_alani:
            eak = {"eak_mw": round(min(eak_alani / 1000.0, kap_mw), 3), "kaynak": "eak_alani"}
        elif ac_mw:
            eak = {"eak_mw": round(ac_mw, 3), "kaynak": "ac_tavani"}
        else:
            eak = {"eak_mw": round(kap_mw, 3), "kaynak": "kurulu_guc"}
    return {"dc_kwp": dc, "ac_kw": ac, "eak_kw": round(eak["eak_mw"] * 1000.0, 3), "eak": eak,
            "ihracat_siniri_kw": round(eak["eak_mw"] * 1000.0, 3),
            "kaynaklar": {"dc": dc_kaynak, "ac": ac_kaynak, "eak": eak["kaynak"], "kunye": bool(kunye)}, "gun": gun.isoformat()}


def guc_tanimlari_db(tenant_id, plant: dict, gun: date | None = None) -> dict:
    """DB: o günkü künyeyle güç tanımları."""
    return guc_tanimlari(plant, gun, guncel(tenant_id, plant["id"], gun))


# ---- beyan → üyelik geçişi --------------------------------------------------------------------------------------------
def beyan_uyarilari(tenant_id, plant: dict) -> list[dict]:
    """params_json.dsg_kodu / toplayici_portfoyu beyanı varken tarihli portföy üyeliği yoksa uyarı + geçiş önerisi (otomatik üyelik açılmaz)."""
    pj = _pj(plant)
    uyarilar = []
    dsg = str(pj.get("dsg_kodu") or "").strip(); top = str(pj.get("toplayici_portfoyu") or "").strip()
    if not dsg and not top:
        return uyarilar
    with tenant_baglami(tenant_id) as s:
        uyelik = s.execute(text("SELECT count(*) FROM portfoy_uyelik WHERE plant_id = CAST(:p AS uuid) AND gecerli_bit IS NULL"), {"p": str(plant["id"])}).scalar()
        aday = None
        if dsg:
            aday = s.execute(text("SELECT g.portfoy_id FROM dsg_grubu g WHERE g.dsg_kodu = :k LIMIT 1"), {"k": dsg}).scalar()
    if int(uyelik or 0) > 0:
        return uyarilar
    if dsg:
        uyarilar.append({"kod": "dsg_beyani", "alan": "dsg_kodu", "deger": dsg,
                         "metin": "Santral ayarlarında DSG kodu beyan edilmiş ama tarihli portföy üyeliği yok; dengesizlik hesabı beyana dayanıyor.",
                         "oneri": ("Bu DSG koduyla tanımlı portföye üyelik ekleyin." if aday else "Önce Portföy yönetimi'nde DSG portföyü tanımlayın, sonra üyelik ekleyin."),
                         "portfoy_id": str(aday) if aday else None, "sayfa": "portfoyler"})
    if top:
        uyarilar.append({"kod": "toplayici_beyani", "alan": "toplayici_portfoyu", "deger": top,
                         "metin": "Toplayıcı portföyü beyan edilmiş ama tarihli portföy üyeliği yok.",
                         "oneri": "Portföy yönetimi'nde toplayıcı portföyü tanımlayıp üyelik ekleyin.", "portfoy_id": None, "sayfa": "portfoyler"})
    return uyarilar


def sozluk() -> dict:
    return {"surum": SURUM, "alanlar": list(ALANLAR), "baglanti_turleri": list(BAGLANTI_TURLERI), "lisans_durumlari": list(LISANS_DURUMLARI),
            "olcum_sinirlari": list(OLCUM_SINIRLARI), "kaynaklar": list(KAYNAKLAR), "dogrulamalar": list(DOGRULAMALAR)}
