"""v2.259 — Dalga 4.12: dengesizlik maliyeti simülatörü — karnenin TL dili.

Program (KGÜP) = D-1 günü 15:30 (İstanbul) öncesinde verilmiş SON koşunun D günü P50'si — yani gerçekten
teslim edilebilecek program (sonraki koşular sayılmaz). Naif program = dün-aynı-saat gerçekleşen (akılsız
referans). Gerçekleşen = SCADA (flag 'valid'). Fiyat = piyasa_service.fiyatlar (EPİAŞ ya da senaryo — kaynak
satır satır taşınır). Formül: pvquant.ext.turkiye.dengesizlik (DUY md. 110–111, k=l=0,03; KÜPST parametre,
varsayılan 0). Segment: plants.params_json.segment → dengesizliği santral mı taşıyor (ext.turkiye.segment).
Tire ilkesi: eşleşen gün yoksa boş; senaryo fiyatı kullanıldıysa yanıt bunu sayıyla söyler.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from pvquant.ext.turkiye import dengesizlik as d, segment as sg

IST = "Europe/Istanbul"


def _pj(v) -> dict:
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return {}
    return v or {}


def program_df(tenant_id, plant_id, gun: int = 90) -> pd.DataFrame:
    """DB: ts_utc, gercek_kw, kgup_kw (D-1 15:30 IST öncesi son koşu), naif_kw (dün-aynı-saat)."""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        df = pd.read_sql(text(
            "WITH g AS (SELECT ts_utc, power_kw FROM scada_hourly WHERE plant_id=:p AND flag='valid' "
            "  AND ts_utc >= (SELECT max(ts_utc) FROM scada_hourly WHERE plant_id=:p AND flag='valid') - (:g * INTERVAL '1 day')) "
            "SELECT g.ts_utc, g.power_kw AS gercek_kw, "
            " (SELECT f.p50_kw FROM forecast_values f JOIN forecast_runs r ON r.id=f.run_id "
            "   WHERE f.plant_id=:p AND f.ts_utc=g.ts_utc "
            "   AND r.run_at <= ((date_trunc('day', g.ts_utc AT TIME ZONE 'Europe/Istanbul') - INTERVAL '1 day' + INTERVAL '15 hours 30 minutes') AT TIME ZONE 'Europe/Istanbul') "
            "   ORDER BY r.run_at DESC LIMIT 1) AS kgup_kw, "
            " (SELECT s2.power_kw FROM scada_hourly s2 WHERE s2.plant_id=:p AND s2.flag='valid' AND s2.ts_utc = g.ts_utc - INTERVAL '24 hour') AS naif_kw "
            "FROM g ORDER BY g.ts_utc"),
            s.connection(), params={"p": plant_id, "g": gun}, parse_dates=["ts_utc"])
    if not df.empty:
        df["ts_utc"] = pd.to_datetime(df["ts_utc"], utc=True)
    return df


def hesapla_df(df: pd.DataFrame, fiyat: pd.DataFrame, kat: d.Katsayilar = d.Katsayilar()) -> dict:
    """SAF. df: ts_utc, gercek_kw, kgup_kw, naif_kw (kW ≈ kWh/saat → MWh = /1000). fiyat: aynı ts index'li ptf/smf/kaynak."""
    bos = {"gun_sayisi": 0, "aylar": [], "toplam": None, "fiyat": {"epias_saat": 0, "senaryo_saat": 0}}
    if df is None or df.empty:
        return bos
    x = df.dropna(subset=["gercek_kw", "kgup_kw"]).copy().set_index("ts_utc")
    if x.empty:
        return bos
    f = fiyat.reindex(x.index)
    ger = x["gercek_kw"].astype(float) / 1000.0; kg = x["kgup_kw"].astype(float) / 1000.0
    ptf = f["ptf"].astype(float); smf = f["smf"].astype(float)
    pv = d.saatlik(kg, ger, ptf, smf, kat)
    ay_pv = d.aylik_karne(pv)
    naif_var = x["naif_kw"].notna(); ay_naif = None
    if naif_var.sum() >= 24:
        xn = x[naif_var]
        nv = d.saatlik(xn["naif_kw"].astype(float) / 1000.0, ger.loc[xn.index], ptf.loc[xn.index], smf.loc[xn.index], kat)
        ay_naif = d.aylik_karne(nv)
    out_ay = []
    for ay, r in ay_pv.iterrows():
        kn = float(ay_naif.loc[ay, "toplam_maliyet"]) if ay_naif is not None and ay in ay_naif.index else None
        out_ay.append({"ay": ay.strftime("%Y-%m"), "uretim_mwh": round(float(r["gerceklesen"]), 1), "sapma_mwh": round(float(r["sapma"]), 1),
                       "referans_gelir_tl": round(float(r["referans_gelir"]), 0), "pvquant_tl": round(float(r["toplam_maliyet"]), 0),
                       "naif_tl": (round(kn, 0) if kn is not None else None), "kurtarilan_tl": (round(kn - float(r["toplam_maliyet"]), 0) if kn is not None else None),
                       "gelir_oran_pct": round(float(r["maliyet_gelir_orani"]) * 100, 2) if pd.notna(r["maliyet_gelir_orani"]) else None,
                       "tl_per_mwh": round(float(r["tl_per_mwh"]), 1) if pd.notna(r["tl_per_mwh"]) else None})
    top_pv = float(pv["toplam_maliyet"].sum()); top_ref = float(pv["referans_gelir"].sum())
    top_naif = float(ay_naif["toplam_maliyet"].sum()) if ay_naif is not None else None
    return {"gun_sayisi": int(pd.Series(x.index.tz_convert(IST).date).nunique()), "aylar": out_ay,
            "toplam": {"pvquant_tl": round(top_pv, 0), "naif_tl": (round(top_naif, 0) if top_naif is not None else None),
                       "kurtarilan_tl": (round(top_naif - top_pv, 0) if top_naif is not None else None),
                       "gelir_oran_pct": round(top_pv / top_ref * 100, 2) if top_ref else None, "referans_gelir_tl": round(top_ref, 0)},
            "fiyat": {"epias_saat": int((f["kaynak"] == "epias").sum()), "senaryo_saat": int((f["kaynak"] == "senaryo").sum())},
            "katsayilar": {"k": kat.k, "l": kat.l, "kupst_n": kat.kupst_n}}


def segment_bilgisi(params_json) -> dict:
    pj = _pj(params_json); ad = pj.get("segment")
    try:
        seg = sg.Segment(ad) if ad else None
    except ValueError:
        seg = None
    if seg is None:
        return {"segment": None, "kgup_yukumlu": None, "dengesizlik_sahibi": None, "santral_tasir": None}
    k = sg.KURALLAR.loc[seg]
    st = sg.Santral("x", seg, 1.0)
    return {"segment": seg.value, "kgup_yukumlu": bool(k["kgup_yukumlu"]), "dengesizlik_sahibi": str(k["dengesizlik_sahibi"]), "santral_tasir": st.dengesizlik_tasir_mi()}


def simulasyon(tenant_id, plant: dict, gun: int = 90) -> dict:
    from pvquant.services import piyasa_service
    df = program_df(tenant_id, plant["id"], gun)
    idx = pd.DatetimeIndex(df["ts_utc"]) if not df.empty else pd.DatetimeIndex([], tz="UTC")
    fiyat = piyasa_service.fiyatlar(idx)
    out = hesapla_df(df, fiyat)
    out["pencere_gun"] = gun
    out["segment"] = segment_bilgisi(plant.get("params_json"))
    out["not"] = ("KGÜP = D-1 15:30 öncesi son koşunun P50'si; naif = dün-aynı-saat; DUY md. 110–111, k=l=0,03; "
                  + ("fiyat: EPİAŞ" if out["fiyat"]["senaryo_saat"] == 0 and out["fiyat"]["epias_saat"] > 0 else f"fiyat: {piyasa_service.SENARYO_AD} (EPİAŞ kimliği yok)"))
    return out
