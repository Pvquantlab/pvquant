"""v2.592 (Faz 3 F3-E) — PORTFÖY REVİZYON KARAR DESTEĞİ SERVİSİ: hedef gün (yarın ya da bugünün kalan saatleri) için güncel tahmin ↔ program (F3-C `gelecek`),
santral başına değişim, KGÜP teslim penceresi (`ext/turkiye/kgup.teslim_durumu`) ve gün içi düzeltme penceresi (`gun_ici_revizyon_penceresi`), fiyat kaynağı,
tahmini maruziyet oranı (son 30 günün `saatlik_pv` çerçevesi), ölçüm/tahmin tazeliği → saf `ext/platform/portfoy_oneri.oneriler`. Otomatik bildirim/emir YOK."""
from __future__ import annotations

from datetime import timedelta

import pandas as pd

from pvquant.ext.platform import finans as fn
from pvquant.ext.platform import portfoy_oneri as po
from pvquant.ext.turkiye import kgup as kg
from pvquant.services import dengesizlik_service as ds
from pvquant.services import finansal_etki_service as fe
from pvquant.services import piyasa_service
from pvquant.services import portfoy_sapma_service as sp
from pvquant.services import portfoy_tahmin_service as pt
from pvquant.services import portfoy_varlik_service as pv

SURUM = po.SURUM
HEDEFLER = ("yarin", "bugun")
MARUZIYET_GUN = 30


def gun_ici_penceresi(simdi: pd.Timestamp, azami_saat: int = 24) -> dict:
    """Şu andan sonraki ilk teslimat saati için düzeltme penceresi açık mı; değilse bir sonraki saatin son düzeltme anı."""
    t = simdi.tz_convert(fn.IST_AD); ilk = t.floor("h") + pd.Timedelta(hours=1)
    sonuc = None
    for i in range(azami_saat):
        h = ilk + pd.Timedelta(hours=i)
        r = kg.gun_ici_revizyon_penceresi(h)
        if t <= r["kgup_revizyon_son"]:
            kalan = int((r["kgup_revizyon_son"] - t) / pd.Timedelta(minutes=1))
            if i == 0:
                return {"acik": True, "teslimat": h.isoformat(timespec="minutes"), "gip_kapi_kapanis": r["gip_kapi_kapanis"].isoformat(timespec="minutes"),
                        "kgup_revizyon_son": r["kgup_revizyon_son"].isoformat(timespec="minutes"), "dakika_kaldi": kalan}
            sonuc = {"acik": False, "teslimat": ilk.isoformat(timespec="minutes"), "sonraki_teslimat": h.isoformat(timespec="minutes"),
                     "sonraki_revizyon_son": r["kgup_revizyon_son"].isoformat(timespec="minutes"), "dakika_kaldi": kalan}
            break
    return sonuc or {"acik": False, "teslimat": ilk.isoformat(timespec="minutes"), "sonraki_revizyon_son": None, "dakika_kaldi": None}


def _an(simdi: pd.Timestamp | None) -> pd.Timestamp:
    t = pd.Timestamp(simdi) if simdi is not None else pd.Timestamp.now(tz="UTC")
    return t.tz_convert(fn.IST_AD) if t.tz is not None else t.tz_localize(fn.IST_AD)


def hazirla(tenant_id, portfoy_id, hedef: str = "yarin", simdi: pd.Timestamp | None = None, kural: str = "son") -> dict:
    """18.11 DSG/portfoy hiz turu — onerinin PAHALI, zamana en az bagli girdileri (DB: santraller, ileri program/risk, fiyat kaynagi, maruziyet,
    son olcum zamani, uyelik anlik gorunumu; test DB olcumu 1,0–1,4 s). JSON'a yazilabilir; `oneriler_hazirdan(h, simdi)` bundan teslim
    penceresini, gun ici pencereyi ve olcum yasini SU ANA gore hesaplayip oneri metinlerini uretir (saf, ms). Yanit onbellegi bunu portfoy
    damgasiyla saklar. «bugun» hedefinde ileri program gecmis saatleri `simdi`ye gore dusurur: onbellek TTL'si (5 dk) kadar gecikebilir."""
    if hedef not in HEDEFLER:
        raise ValueError("hedef " + "|".join(HEDEFLER))
    t = _an(simdi)
    bugun = t.date(); gun = bugun + timedelta(days=1) if hedef == "yarin" else bugun
    plants = pt.santraller(tenant_id, portfoy_id, gun)
    if not plants:
        return {"durum": "uye_yok", "santral": 0, "hedef": hedef, "gun": gun.isoformat()}
    g = sp.gelecek(tenant_id, portfoy_id, gun=1, kural=kural, bugun=bugun, bas_gun=gun, simdi=t)   # «bugün» için geçmiş saatler düşer; «yarın» pencerenin önünde kalır
    if g.get("durum") != "ok":
        return {**g, "hedef": hedef, "gun": gun.isoformat()}
    santraller = []
    for ad, pr in g["santral_program"].items():
        prog = pr.get("mwh"); tah = (g.get("santral_tahmin") or {}).get(ad)
        fark = None if prog is None or tah is None else round(tah - prog, 3)
        santraller.append({"santral": ad, "program_mwh": prog, "tahmin_mwh": tah, "fark_mwh": fark,
                           "degisim_pct": None if fark is None or not prog or prog <= 1e-9 else round(100.0 * fark / prog, 1),
                           "bildirilen": bool(pr.get("bildirilen_saat")) and not pr.get("oneri_saat"), "tahmin_var": tah is not None})
    santraller.sort(key=lambda s: -abs(s["degisim_pct"] or 0.0))
    tz = g["tz"]
    izgara = pd.date_range(pt._utc(gun, tz), pt._utc(gun + timedelta(days=1), tz), freq="h", inclusive="left", tz="UTC")
    try:
        f = piyasa_service.fiyatlar(izgara)
        fiyat = {"epias_saat": int((f["kaynak"] == "epias").sum()), "senaryo_saat": int((f["kaynak"] != "epias").sum())}
    except Exception:   # noqa: BLE001 — fiyat tablosu okunamazsa «fiyat yok»
        fiyat = {"epias_saat": 0, "senaryo_saat": int(len(izgara))}
    pvs = []
    for p in plants:
        try:
            x = ds.saatlik_pv(tenant_id, p, gun=MARUZIYET_GUN)
            if x is not None and not x.empty:
                pvs.append(x)
        except Exception:   # noqa: BLE001 — bir santralin geçmişi okunamazsa maruziyet onsuz
            continue
    mar = po.maruziyet_orani(pd.concat(pvs), tz) if pvs else None
    olcumler = []   # 18.11: ham zamanlar saklanir, yas (saat) istek aninda hesaplanir
    for p in plants:
        try:
            z = fe.son_olcum_zamani(tenant_id, p["id"])
        except Exception:   # noqa: BLE001
            z = None
        if z is not None:
            olcumler.append(z)
    en_eski_olcum = min(zlar).isoformat() if (zlar := [pd.Timestamp(z).tz_convert("UTC") if pd.Timestamp(z).tz is not None else pd.Timestamp(z).tz_localize("UTC")
                                                      for z in olcumler]) else None
    return {"durum": "ok", "hazir": True, "portfoy_id": str(portfoy_id), "hedef": hedef, "gun": gun.isoformat(), "tz": tz, "kural": kural, "kural_ad": g["kural_ad"],
            "santral": len(plants), "risk": g["risk"], "santraller": santraller, "program_kaynak": g["program_kaynak"], "tahmin_yok": g["tahmin_yok"],
            "tazelik": g["tazelik"], "belirsizlik": g["belirsizlik"], "fiyat": fiyat, "maruziyet": mar, "gunluk": g.get("gunluk"), "kapasite_kwp": g.get("kapasite_kwp"),
            "en_eski_olcum_utc": en_eski_olcum, "uyelik_anlik": pv.uyelik_anlik(tenant_id, portfoy_id, gun), "program_meta": g["meta"]["program"]}


def oneriler_hazirdan(h: dict, simdi: pd.Timestamp | None = None) -> dict:
    """SAF: `hazirla` ciktisindan (onbellekten de gelebilir, JSON) su ana gore teslim penceresi, gun ici pencere, olcum yasi ve oneri metinleri.
    Hazir degilse (uye yok / ileri program yok) girdi oldugu gibi doner."""
    if not h.get("hazir"):
        return h
    t = _an(simdi); hedef = h["hedef"]
    pencere = kg.teslim_durumu(t); gi = gun_ici_penceresi(t) if hedef == "bugun" else {}
    olcum_yas = round((t.tz_convert("UTC") - pd.Timestamp(h["en_eski_olcum_utc"])).total_seconds() / 3600, 1) if h.get("en_eski_olcum_utc") else None
    girdi = {"hedef": hedef, "gun": h["gun"], "risk": h["risk"], "program_kaynak": h["program_kaynak"], "santraller": h["santraller"], "tahmin_yok": h["tahmin_yok"],
             "belirsizlik": h["belirsizlik"], "tazelik": h["tazelik"] or {}, "olcum_yas_saat": olcum_yas, "pencere": pencere, "gun_ici": gi, "fiyat": h["fiyat"], "maruziyet": h["maruziyet"],
             "kapasite_kwp": h.get("kapasite_kwp")}
    on = po.oneriler(girdi)
    return {"durum": "ok", "portfoy_id": h["portfoy_id"], "hedef": hedef, "hedef_ad": "Yarın" if hedef == "yarin" else "Bugün (kalan saatler)", "gun": h["gun"],
            "simdi": t.isoformat(timespec="minutes"), "tz": h["tz"], "kural": h["kural"], "kural_ad": h["kural_ad"], "santral": h["santral"], "ozet": po.ozet_cumlesi(girdi, on),
            "oneriler": on, "risk": h["risk"], "santraller": h["santraller"], "program_kaynak": h["program_kaynak"], "tahmin_yok": h["tahmin_yok"], "tazelik": h["tazelik"],
            "olcum_yas_saat": olcum_yas, "belirsizlik": h["belirsizlik"], "pencere": pencere, "gun_ici": gi, "fiyat": h["fiyat"], "maruziyet": h["maruziyet"], "gunluk": h.get("gunluk"),
            "etiketler": po.ETIKET_AD, "meta": {"surum": SURUM, "uyelik_anlik": h["uyelik_anlik"], "program": h["program_meta"],
                                                 "karar": "Karar desteğidir; otomatik KGÜP bildirimi ya da piyasa emri yapılmaz."}}


def oneriler(tenant_id, portfoy_id, hedef: str = "yarin", simdi: pd.Timestamp | None = None, kural: str = "son") -> dict:
    """DB: hazirla + oneriler_hazirdan (ayni an). Cikti 18.11 oncesiyle birebir (test_portfoy_revizyon_db)."""
    return oneriler_hazirdan(hazirla(tenant_id, portfoy_id, hedef, simdi, kural), simdi)
