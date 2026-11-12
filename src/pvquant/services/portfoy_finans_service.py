"""v2.594 (Faz 3 F3-G) — PORTFÖY FİNANSAL ETKİ SERVİSİ: zamanlı üyelikle santral kümesi; santral başına Faz 2 FEM sonucu (gece kaydı ≤36 sa, yoksa anında
`ozet`, kaydedilmez); DSG portföyünde F3-D perspektifleri; saf `ext/platform/portfoy_finans.birlestir`. Uzlaştırma, tarife, FEM formülleri DOKUNULMAZ."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from pvquant.ext.platform import finans as fn
from pvquant.ext.platform import portfoy_finans as pf
from pvquant.services import finansal_etki_service as fe
from pvquant.services import kural_sicili_service as _kss  # v2.600 (F4-F): sonuç meta damgası
from pvquant.services import portfoy_dsg_service as sd
from pvquant.services import portfoy_tahmin_service as pt
from pvquant.services import portfoy_varlik_service as pv

SURUM = pf.SURUM


def donem(tenant_id, portfoy_id, kod: str | None = None, uretim: str | None = None, bugun: date | None = None, tarih: date | None = None, taze: bool = False,
          dsg_sonuc: dict | None = None) -> dict:
    """v2.601 (F4-G): `dsg_sonuc` verilirse DSG perspektifi yeniden hesaplanmaz (gece işi DSG dönemini bir kez hesaplar, iki kayda paylaştırır)."""
    bugun = bugun or pd.Timestamp.now(tz=fn.IST_AD).date()
    dn = fn.donem_cozumle(kod, bugun, tz=fn.IST_AD)
    uyelik_tarihi = tarih or min(dn["bit"] - timedelta(days=1), bugun)
    try:
        p_bilgi = pv.portfoy(tenant_id, portfoy_id, uyelik_tarihi)
    except pv.PortfoyHatasi:
        return {"durum": "portfoy_yok", "not": "Portföy bulunamadı."}
    plants = pt.santraller(tenant_id, portfoy_id, uyelik_tarihi)
    if not plants:
        return {"durum": "uye_yok", "portfoy_id": str(portfoy_id), "donem_kodu": dn["kod"], "not": "Bu tarihte portföyün geçerli üyesi yok."}
    ozetler, kaynak = {}, {}
    for p in plants:
        plant = {"id": p["id"], "name": p["name"], "capacity_kwp": p["capacity_kwp"], "tz": p["tz"], "lat": p.get("lat"), "lon": p.get("lon"), "params_json": p.get("params_json") or {}, "archived": False}
        try:
            o = None if taze else fe.son(tenant_id, p["id"], dn["kod"], uretim, donem_bit=dn["bit"], plant=plant)
            if o is None:
                o = fe.ozet(tenant_id, plant, dn["kod"], uretim, bugun); kaynak[p["name"]] = "anında"
            else:
                kaynak[p["name"]] = "kayıtlı"
            o["plant_id"] = p["id"]
            ozetler[p["name"]] = o
        except Exception as ex:   # noqa: BLE001 — bir santralın hatası portföyü düşürmez
            ozetler[p["name"]] = {"hata": f"{type(ex).__name__}: {ex}"}; kaynak[p["name"]] = "hata"
    dsg = None
    if p_bilgi["tur"] == "dsg":
        if dsg_sonuc is not None:
            dsg = dsg_sonuc
        else:
            try:
                dsg = sd.donem(tenant_id, portfoy_id, kod, uretim, bugun, tarih=uyelik_tarihi)
            except Exception as ex:   # noqa: BLE001
                dsg = {"durum": "hata", "not": f"{type(ex).__name__}: {ex}"}
    kaps = {p["name"]: p["capacity_kwp"] for p in plants}
    out = pf.birlestir(ozetler, dsg if dsg and dsg.get("durum") == "ok" else None, kaps, dn["kod"])
    out.update({"durum": "ok", "portfoy_id": str(portfoy_id), "portfoy": {"ad": p_bilgi["ad"], "tur": p_bilgi["tur"], "dsg_kodu": p_bilgi.get("dsg_kodu")},
                "donem": {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in dn.items()}, "uyelik_tarihi": uyelik_tarihi.isoformat(), "santral": len(plants),
                "kaynaklar": kaynak, "dsg_durum": (dsg or {}).get("durum") if p_bilgi["tur"] == "dsg" else "dsg_degil", "dsg_not": (dsg or {}).get("not") if dsg and dsg.get("durum") != "ok" else None,
                "meta": {"surum": SURUM, **_kss.meta_damgasi(), "uretim_girdisi": uretim or "santral ayarı", "uyelik_anlik": pv.uyelik_anlik(tenant_id, portfoy_id, uyelik_tarihi),
                         "sozlesme_anlik": pv.sozlesme_anlik(tenant_id, portfoy_id, uyelik_tarihi), "taze": bool(taze),
                         # v2.601 (F4-G): girdi referansları — santral başına kayıt/anında + girdi sha, DSG fiyat damgası; hesap durumu en zayıf üye
                         "cikti_surumu": fe.CIKTI_SURUMU, "girdi": _girdi_referanslari(ozetler, kaynak, dsg),
                         "hesap_durumu": _hesap_durumu(ozetler, dsg if dsg and dsg.get("durum") == "ok" else None)}})
    return out


_DURUM_SIRA = {"hesaplanamadi": 0, "senaryo": 1, "kismi": 2, "tam": 3}


def _hesap_durumu(ozetler: dict, dsg: dict | None) -> str:
    """En zayıf üye durumu (hata = hesaplanamadi); DSG senaryo fiyatı kullandıysa en iyi «kismi»."""
    durumlar = [("hesaplanamadi" if "hata" in o else ((o.get("meta") or {}).get("hesap_durumu") or "kismi")) for o in ozetler.values()]
    if dsg and ((dsg.get("meta") or {}).get("hesap_durumu") in ("senaryo", "kismi")):
        durumlar.append((dsg.get("meta") or {}).get("hesap_durumu"))
    return min(durumlar, key=lambda d: _DURUM_SIRA.get(d, 0)) if durumlar else "hesaplanamadi"


def _girdi_referanslari(ozetler: dict, kaynak: dict, dsg: dict | None) -> dict:
    """Santral başına {kaynak: kayıtlı|anında|hata, kayit_id, girdi_sha16, hesap_durumu}; DSG fiyat damgası; bileşik sha (üye sha'ları + DSG fiyat sha)."""
    import hashlib
    import json
    santraller = {}
    for ad, o in ozetler.items():
        m = o.get("meta") or {}
        santraller[ad] = {"kaynak": kaynak.get(ad), "kayit_id": o.get("id") if o.get("kayitli") else None, "girdi_sha16": (m.get("girdi") or {}).get("sha16"),
                          "hesap_durumu": m.get("hesap_durumu"), "hata": o.get("hata")}
    dsg_fiyat = ((dsg or {}).get("meta") or {}).get("fiyat") if dsg else None
    birlesik = hashlib.sha256(json.dumps({"santraller": {a: v["girdi_sha16"] for a, v in santraller.items()}, "dsg_fiyat": (dsg_fiyat or {}).get("sha16")},
                                         sort_keys=True).encode("utf-8")).hexdigest()[:16]
    return {"santraller": santraller, "dsg_fiyat": dsg_fiyat, "sha16": birlesik}
