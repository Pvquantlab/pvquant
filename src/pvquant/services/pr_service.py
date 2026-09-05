"""v2.249 — Dalga 1.4: IEC 61724-1 performans oranı kartı (Santralım künyesi).

Kaynak: scada_hourly (power_kw, poa_wm2, t_module, flag='valid') + plants.capacity_kwp.
Hesap: pvquant.ext.standart.iec61724 (Y_r/Y_f/PR/PR′). Tire ilkesi: POA ölçümü gündüz
saatlerinin %95'inden azında varsa PR YAZILMAZ — 'poa_yok' döner (GHI ile uydurulmaz;
IEC düzlem-içi ışınım ister). t_module yoksa PR′ None, PR yine verilir.
Model çekirdeğine dokunmaz; yalnız ölçümden hesap.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from pvquant.ext.standart import iec61724


def pr_hesapla(df: pd.DataFrame, capacity_kwp: float, min_poa_orani: float = 0.95, gamma: float = -0.0035) -> dict:
    """SAF: df kolonları ts_utc, power_kw, poa_wm2, t_module (NaN olabilir). Döner sözlük JSON-güvenli."""
    bos = {"durum": "veri_yok", "gun": 0, "saat": 0, "poa_orani": None, "Y_r": None, "Y_f": None,
           "PR": None, "PR_sicaklik": None, "CF": None, "t_ref": None}
    if df is None or df.empty or not capacity_kwp or capacity_kwp <= 0:
        return bos
    d = df.dropna(subset=["power_kw"]).copy()
    d["ts_utc"] = pd.to_datetime(d["ts_utc"], utc=True)
    d = d.set_index("ts_utc").sort_index()
    gunduz = d[d.power_kw > 0.02 * capacity_kwp]
    if gunduz.empty:
        return bos
    poa_var = gunduz["poa_wm2"].notna() & (gunduz["poa_wm2"] > 0)
    oran = float(poa_var.mean())
    gun = int(pd.Series(gunduz.index.date).nunique())
    if oran < min_poa_orani:
        return {**bos, "durum": "poa_yok", "gun": gun, "saat": int(len(gunduz)), "poa_orani": round(oran, 3)}
    kesit = d[d["poa_wm2"].notna()]
    e = kesit["power_kw"].astype(float)          # saatlik kW ≈ kWh
    poa = kesit["poa_wm2"].astype(float).clip(lower=0)
    t_cell = kesit["t_module"] if "t_module" in kesit and kesit["t_module"].notna().mean() >= 0.9 else None
    k = iec61724.kpi(e, poa, capacity_kwp, t_cell=t_cell, gamma=gamma, donem="YE", min_veri_orani=0.0)
    y = iec61724.yillik_ozet(k)
    def _f(v):
        return None if v is None or (isinstance(v, float) and np.isnan(v)) else round(float(v), 3)
    pr_w = k["PR_yillik_agirlikli"].iloc[-1] if t_cell is not None and "PR_yillik_agirlikli" in k else None
    return {"durum": "ok", "gun": gun, "saat": int(len(kesit)), "poa_orani": round(oran, 3),
            "Y_r": _f(y["Y_r"]), "Y_f": _f(y["Y_f"]), "PR": _f(y["PR"]),
            "PR_sicaklik": _f(pr_w), "CF": _f(y["CF"]), "t_ref": _f(k.attrs.get("t_ref"))}


def pr_karti(tenant_id, plant_id, gun: int = 30) -> dict:
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    # v2.251: pencere takvime degil SON OLCUME baglanir — SCADA yuklemesi gecikmis santralde
    # "son 30 gun" bos kalip PR'i sessizce tireye dusuruyordu; simdi son olcum gununden geriye
    # N gun okunur ve bitis tarihi (son_olcum) yanitta soylenir.
    with tenant_baglami(tenant_id) as s:
        cap = s.execute(text("SELECT capacity_kwp FROM plants WHERE id=:p"), {"p": plant_id}).scalar()
        son = s.execute(text("SELECT max(ts_utc) FROM scada_hourly WHERE plant_id=:p AND flag='valid'"), {"p": plant_id}).scalar()
        df = pd.read_sql(text(
            "SELECT ts_utc, power_kw, poa_wm2, t_module FROM scada_hourly "
            "WHERE plant_id=:p AND flag='valid' AND ts_utc >= :son - (:g * INTERVAL '1 day') AND ts_utc <= :son ORDER BY ts_utc"),
            s.connection(), params={"p": plant_id, "g": gun, "son": son}, parse_dates=["ts_utc"]) if son is not None else pd.DataFrame()
    out = pr_hesapla(df, float(cap) if cap is not None else 0.0)
    out["pencere_gun"] = gun
    out["son_olcum"] = son.date().isoformat() if son is not None else None
    return out
