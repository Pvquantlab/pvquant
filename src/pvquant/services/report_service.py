"""Rapor baglami: forecast_values + calibrations -> ReportContext.
reporting paketi TEK SATIR degismez (Parca 3 §4).
Fable 5 v1.7 kurali: JSONB dict olarak geldigi icin isinstance kontrolu."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from sqlalchemy import text
from pvquant.db import tenant_baglami
from pvquant.reporting import ReportContext, build_pdf, build_excel, build_json
from pvquant.services.forecast_service import son_kosu


def rapor_baglami(tenant_id, plant: dict) -> ReportContext | None:
    h = son_kosu(tenant_id, plant["id"])
    if h is None:
        return None
    h = h.rename(columns={"physics_kw": "p_dc_kw"})  # gecici: dc yoksa fizik
    h["energy_kwh"] = h["p50_kw"]
    h["poa"] = 0.0
    h["temp_cell"] = 25.0
    yerel = h.tz_convert(plant["tz"])
    daily = h["energy_kwh"].groupby(h.index.tz_convert("UTC").date).sum()
    import pandas as pd
    daily.index = pd.to_datetime(daily.index)
    with tenant_baglami(tenant_id) as s:
        cal = s.execute(text(
            "SELECT mode,params_json,quality_json,gate_json,n_valid_hours,"
            " created_at FROM calibrations WHERE plant_id=:p AND active"),
            {"p": plant["id"]}).first()
    ctx = ReportContext(
        plant_name=plant["name"],
        capacity_kwp=plant["capacity_kwp"],
        latitude=plant["lat"],
        longitude=plant["lon"],
        tilt_deg=plant.get("tilt") or 20,
        azimuth_deg=plant.get("azimuth") or 180,
        plant_tz=plant["tz"],
        run_at_utc=datetime.now(timezone.utc),
        mode=(cal.mode if cal else "A"),
        model_name="barhdadi_bennis",
        meteo_source="open-meteo",
        hourly=h,
        daily_kwh=daily,
    )
    if cal:
        # Fable 5 v1.7: JSONB psycopg-den dict olarak gelir, str degil
        pa = cal.params_json if isinstance(cal.params_json, dict) else json.loads(cal.params_json)
        q_raw = cal.quality_json
        q = q_raw if isinstance(q_raw, dict) else (json.loads(q_raw) if q_raw else {})
        ctx.eta_bos = pa.get("eta_bos")
        ctx.bg = pa.get("bg")
        ctx.mape_pct = q.get("mape_pct")
        ctx.warnings = q.get("warnings", [])
        ctx.n_valid_hours = cal.n_valid_hours
        ctx.calibrated_at = cal.created_at
        g_raw = cal.gate_json
        g = g_raw if isinstance(g_raw, dict) else (json.loads(g_raw) if g_raw else {})
        if cal.mode == "C" and g.get("gecti"):
            ctx.holdout_mape_pct = g.get("holdout_mape")
            ctx.holdout_physics_mape_pct = g.get("fizik_mape")
            ctx.holdout_improvement_pct = g.get("iyilesme_pct")
    return ctx

# --------------------------------------------------------------- Adim 6
import datetime as _dt
from pvquant.reporting import build_pdf, build_excel, build_json


def uret(tenant_id, plant: dict, fmt: str):
    """Tek uretim kapisi (KURAL 2 — sayfada build_* cagrisi olmaz).
    Donus: (bytes, dosya_adi, uretim_ts). ctx None ise ValueError —
    sayfa bos-durum bekcileri bunu zaten engeller."""
    ctx = rapor_baglami(tenant_id, plant)
    if ctx is None:
        raise ValueError("rapor baglami kurulamadi — once tahmin uretin")
    ad_kok = plant["name"].replace(" ", "_")
    gun = _dt.date.today().strftime("%Y%m%d")
    if fmt == "pdf":
        veri, uzanti = build_pdf(ctx), "pdf"
    elif fmt == "xlsx":
        veri, uzanti = build_excel(ctx), "xlsx"
    elif fmt == "json":
        j = build_json(ctx)
        veri = j.encode("utf-8") if isinstance(j, str) else j
        uzanti = "json"
    else:
        raise ValueError(f"bilinmeyen format: {fmt}")
    return veri, f"PVQuant_{ad_kok}_{gun}.{uzanti}", _dt.datetime.now()
