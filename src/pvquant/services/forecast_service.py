"""Tahmin uret ve ARSIVLE. Ekranlar yalniz bu tablolardan okur."""
from __future__ import annotations
import json, pickle
import pandas as pd
from sqlalchemy import text
from pvquant.db import tenant_baglami
from pvquant.io.meteo import OpenMeteoClient
from pvquant.pipeline.forecast import forecast_7day
from pvquant.pipeline.hybrid_ui import hybrid_forecast_hourly
from pvquant.services.calib_service import _plant_spec


def uret_ve_kaydet(tenant_id, plant: dict) -> str:
    meteo = OpenMeteoClient().get_forecast(latitude=plant["lat"],
                                           longitude=plant["lon"])
    with tenant_baglami(tenant_id) as s:
        cal = s.execute(text(
            "SELECT mode, params_json FROM calibrations "
            "WHERE plant_id=:p AND active LIMIT 1"), {"p": plant["id"]}).first()
        ml = s.execute(text(
            "SELECT artifact_path FROM ml_models "
            "WHERE plant_id=:p AND active LIMIT 1"), {"p": plant["id"]}).first()
    mode = cal.mode if cal else "A"
    spec = _plant_spec(plant)
    if cal:
        pr = json.loads(cal.params_json) if isinstance(cal.params_json, str) else cal.params_json
        # kalibre katsayilar spec'e islenir — PlantSpec alan adlarini dogrula
        if pr.get("eta_bos"): spec.eta_bos = pr["eta_bos"]
        if pr.get("bg") is not None: spec.bifacial_factor = pr["bg"]
    fr = forecast_7day(meteo, spec)
    h = fr.hourly.rename(columns={"p_ac_kw": "p50_kw"})
    h["physics_kw"] = h["p50_kw"]; h["ml_kw"] = None
    h["p10_kw"] = None; h["p90_kw"] = None
    if mode == "C" and ml:
        with open(ml.artifact_path, "rb") as f: model = pickle.load(f)
        hh = hybrid_forecast_hourly(model, meteo)
        if hh is not None:
            h["p50_kw"] = hh["p50_kw"].reindex(h.index)
            h["ml_kw"] = h["p50_kw"] - h["physics_kw"]
            for k in ("p10_kw", "p90_kw"):
                if k in hh.columns: h[k] = hh[k].reindex(h.index)
    with tenant_baglami(tenant_id) as s:
        run_id = s.execute(text(
            "INSERT INTO forecast_runs(tenant_id,plant_id,mode,model,meteo_source)"
            " VALUES(:t,:p,:m,:mo,'open-meteo') RETURNING id"),
            {"t": tenant_id, "p": plant["id"], "m": mode,
             "mo": "hybrid_residual" if mode == "C" else "barhdadi_bennis"}).scalar()
        satirlar = [{"t": tenant_id, "r": run_id, "p": plant["id"], "ts": ts,
                     "p50": _f(v["p50_kw"]), "p10": _f(v["p10_kw"]),
                     "p90": _f(v["p90_kw"]), "ph": _f(v["physics_kw"]),
                     "ml": _f(v["ml_kw"])} for ts, v in h.iterrows()]
        s.execute(text(
            "INSERT INTO forecast_values(tenant_id,run_id,plant_id,ts_utc,"
            " p50_kw,p10_kw,p90_kw,physics_kw,ml_kw) "
            "VALUES(:t,:r,:p,:ts,:p50,:p10,:p90,:ph,:ml)"), satirlar)
    return str(run_id)


def _f(v):
    return None if v is None or pd.isna(v) else float(v)


def son_kosu(tenant_id, plant_id) -> pd.DataFrame | None:
    with tenant_baglami(tenant_id) as s:
        run = s.execute(text(
            "SELECT id FROM forecast_runs WHERE plant_id=:p "
            "ORDER BY run_at DESC LIMIT 1"), {"p": plant_id}).first()
        if not run: return None
        return pd.read_sql(text(
            "SELECT ts_utc,p50_kw,p10_kw,p90_kw,physics_kw,ml_kw "
            "FROM forecast_values WHERE run_id=:r ORDER BY ts_utc"),
            s.connection(), params={"r": run.id},
            index_col="ts_utc", parse_dates=["ts_utc"])
