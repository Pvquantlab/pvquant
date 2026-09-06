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


def gunluk_toplamlar(df: pd.DataFrame, tz: str, min_saat: int = 20) -> dict[str, dict]:
    """Saatlik koşu çerçevesi → yerel gün toplamları {gun: {p50_kwh, p10_kwh, p90_kwh, saat}}.
    <min_saat kapsamalı gün yazılmaz; P10/P90 ancak günün tüm saatleri doluysa (tire ilkesinin toplam hâli)."""
    if df is None or df.empty:
        return {}
    ix = pd.DatetimeIndex(df.index)
    if ix.tz is None:
        ix = ix.tz_localize("UTC")
    yerel = ix.tz_convert(tz)
    out: dict[str, dict] = {}
    for gun, g in df.groupby(yerel.date):
        if len(g) < min_saat:
            continue
        r = {"p50_kwh": round(float(g["p50_kw"].sum()), 1), "saat": int(len(g))}
        for k in ("p10", "p90"):
            col = g[f"{k}_kw"] if f"{k}_kw" in g else None
            r[f"{k}_kwh"] = round(float(col.sum()), 1) if col is not None and col.notna().all() else None
        out[gun.isoformat()] = r
    return out


def _son_kosu_gunleri(s, plant_id: str, tz: str) -> dict[str, dict]:
    from sqlalchemy import text
    run = s.execute(text(
        "SELECT id FROM forecast_runs WHERE plant_id=:p AND EXISTS (SELECT 1 FROM forecast_values v WHERE v.run_id=forecast_runs.id) "
        "ORDER BY run_at DESC LIMIT 1"), {"p": plant_id}).first()
    if not run:
        return {}
    df = pd.read_sql(text("SELECT ts_utc, p50_kw, p10_kw, p90_kw FROM forecast_values WHERE run_id=:r ORDER BY ts_utc"),
                     s.connection(), params={"r": run.id}, index_col="ts_utc", parse_dates=["ts_utc"])
    return gunluk_toplamlar(df, tz)


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
        # v2.264: bugün/yarın SON KOŞUDAN (forecast_daily yalnız kapanmış günlerin arşividir — canlı kontrolde tire kaldı);
        # 'bugün' santralin yerel günü (İstanbul), sunucunun UTC takvimi değil (v2.262 dersi).
        bugun = pd.Timestamp.now(tz=santraller[0].get("tz") or "Europe/Istanbul").date(); yarin = bugun + timedelta(days=1)
        bek = {str(p["id"]): _son_kosu_gunleri(s, str(p["id"]), p.get("tz") or "UTC") for p in santraller}
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
            "bugun_kwh": (bek.get(pid, {}).get(bugun.isoformat()) or {}).get("p50_kwh"),
            "yarin_kwh": (bek.get(pid, {}).get(yarin.isoformat()) or {}).get("p50_kwh"),
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
