"""v2.263 — Dalga 5.15: portföy görünümü — kiracının tüm santralleri tek tabloda.

Satır başına: kurulu güç, son ölçüm, 30 günlük WMAPE (0–24 s), bugün/yarın beklenen (forecast_daily P50),
açık alarm (son 7 gün, okunmamış), son koşu. Toplamlar: kapasite, beklenen toplamı (bir santral eksikse
toplam da eksik — sessiz eksik toplam yok; pvquant.ext.platform.portfoy kuralı), kapasite-ağırlıklı WMAPE,
açık alarm toplamı. Hiyerarşik uzlaştırma (MinT) ileride; bu dalga yalnız toplama ve görüntüleme.
"""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from pvquant.ext.platform import portfoy as pf


def _toplam(v: list) -> float | None:
    """Bir santral bile None ise toplam None (eksik sessizce sıfır sayılmaz)."""
    if not v or any(x is None for x in v):
        return None
    return float(sum(v))


def ozet(tenant_id) -> dict:
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        santraller = [dict(r._mapping) for r in s.execute(text(
            "SELECT id, name, capacity_kwp, tz, lat, lon, params_json FROM plants WHERE NOT archived ORDER BY name"))]
        if not santraller:
            return {"santraller": [], "toplam": None, "gun": date.today().isoformat()}
        ids = [str(p["id"]) for p in santraller]
        son_scada = {str(r.plant_id): r.son for r in s.execute(text(
            "SELECT plant_id, max(ts_utc) AS son FROM scada_hourly WHERE flag='valid' GROUP BY plant_id"))}
        wmape = {str(r.plant_id): (float(r.w) if r.w is not None else None) for r in s.execute(text(
            "SELECT plant_id, avg(mape) AS w FROM skill_daily WHERE horizon_bucket='0-24' "
            "AND date >= current_date - 30 GROUP BY plant_id"))}
        bugun = date.today(); yarin = bugun + timedelta(days=1)
        bek = {}
        for r in s.execute(text("SELECT plant_id, gun, p50_kwh FROM forecast_daily WHERE gun IN (:a, :b)"), {"a": bugun, "b": yarin}):
            bek.setdefault(str(r.plant_id), {})[r.gun] = float(r.p50_kwh)
        alarm = {str(r.plant_id): int(r.n) for r in s.execute(text(
            "SELECT plant_id, count(*) AS n FROM alerts WHERE created_at >= now() - interval '7 days' AND acked_by IS NULL GROUP BY plant_id"))}
        kosu = {str(r.plant_id): r.son for r in s.execute(text(
            "SELECT plant_id, max(run_at) AS son FROM forecast_runs r WHERE EXISTS (SELECT 1 FROM forecast_values v WHERE v.run_id=r.id) GROUP BY plant_id"))}
    satirlar = []
    for p in santraller:
        pid = str(p["id"]); pj = p.get("params_json") or {}
        satirlar.append({
            "id": pid, "ad": p["name"], "kapasite_kwp": float(p["capacity_kwp"]), "tz": p["tz"],
            "segment": (pj.get("segment") if isinstance(pj, dict) else None),
            "son_olcum": son_scada.get(pid).isoformat() if son_scada.get(pid) else None,
            "kesinti_gun": (int((pd.Timestamp.now(tz="UTC") - pd.Timestamp(son_scada[pid])).days) if son_scada.get(pid) else None),
            "wmape_30g": (round(wmape[pid], 2) if wmape.get(pid) is not None else None),
            "bugun_kwh": bek.get(pid, {}).get(bugun), "yarin_kwh": bek.get(pid, {}).get(yarin),
            "acik_alarm": alarm.get(pid, 0),
            "son_kosu": kosu.get(pid).isoformat() if kosu.get(pid) else None,
        })
    P = pf.Portfoy({r["id"]: pf.SantralKaydi(r["id"], r["ad"], r["kapasite_kwp"] / 1000.0, "", r["segment"] or "") for r in satirlar})
    karneler = {r["id"]: {"wmape": r["wmape_30g"]} for r in satirlar if r["wmape_30g"] is not None}
    kpi = pf.agirlikli_kpi(karneler, P, alanlar=("wmape",)) if karneler else None
    toplam = {
        "santral": len(satirlar), "kapasite_kwp": float(sum(r["kapasite_kwp"] for r in satirlar)),
        "bugun_kwh": _toplam([r["bugun_kwh"] for r in satirlar]), "yarin_kwh": _toplam([r["yarin_kwh"] for r in satirlar]),
        "wmape_agirlikli": (round(float(kpi["wmape"]), 2) if kpi is not None and not np.isnan(kpi["wmape"]) else None),
        "wmape_kapsanan_kwp": (float(kpi["kapsanan_kapasite_mw"]) * 1000.0 if kpi is not None else 0.0),
        "acik_alarm": int(sum(r["acik_alarm"] for r in satirlar)),
        "veri_gecikmis": int(sum(1 for r in satirlar if r["kesinti_gun"] is None or r["kesinti_gun"] > 2)),
    }
    return {"santraller": satirlar, "toplam": toplam, "gun": bugun.isoformat()}
