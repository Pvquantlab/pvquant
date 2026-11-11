"""v2.594 (Faz 3 F3-G) — PORTFÖY FİNANSAL ETKİ SERVİSİ: zamanlı üyelikle santral kümesi; santral başına Faz 2 FEM sonucu (gece kaydı ≤36 sa, yoksa anında
`ozet`, kaydedilmez); DSG portföyünde F3-D perspektifleri; saf `ext/platform/portfoy_finans.birlestir`. Uzlaştırma, tarife, FEM formülleri DOKUNULMAZ."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from pvquant.ext.platform import finans as fn
from pvquant.ext.platform import portfoy_finans as pf
from pvquant.services import finansal_etki_service as fe
from pvquant.services import portfoy_dsg_service as sd
from pvquant.services import portfoy_tahmin_service as pt
from pvquant.services import portfoy_varlik_service as pv

SURUM = pf.SURUM


def donem(tenant_id, portfoy_id, kod: str | None = None, uretim: str | None = None, bugun: date | None = None, tarih: date | None = None, taze: bool = False) -> dict:
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
        try:
            dsg = sd.donem(tenant_id, portfoy_id, kod, uretim, bugun, tarih=uyelik_tarihi)
        except Exception as ex:   # noqa: BLE001
            dsg = {"durum": "hata", "not": f"{type(ex).__name__}: {ex}"}
    kaps = {p["name"]: p["capacity_kwp"] for p in plants}
    out = pf.birlestir(ozetler, dsg if dsg and dsg.get("durum") == "ok" else None, kaps, dn["kod"])
    out.update({"durum": "ok", "portfoy_id": str(portfoy_id), "portfoy": {"ad": p_bilgi["ad"], "tur": p_bilgi["tur"], "dsg_kodu": p_bilgi.get("dsg_kodu")},
                "donem": {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in dn.items()}, "uyelik_tarihi": uyelik_tarihi.isoformat(), "santral": len(plants),
                "kaynaklar": kaynak, "dsg_durum": (dsg or {}).get("durum") if p_bilgi["tur"] == "dsg" else "dsg_degil", "dsg_not": (dsg or {}).get("not") if dsg and dsg.get("durum") != "ok" else None,
                "meta": {"surum": SURUM, "uretim_girdisi": uretim or "santral ayarı", "uyelik_anlik": pv.uyelik_anlik(tenant_id, portfoy_id, uyelik_tarihi),
                         "sozlesme_anlik": pv.sozlesme_anlik(tenant_id, portfoy_id, uyelik_tarihi), "taze": bool(taze)}})
    return out
