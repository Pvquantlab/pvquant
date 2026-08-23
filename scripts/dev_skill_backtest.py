"""Geriye tarihli GERCEK kosu: skill karnesini beklemeden doldurur.
Kullanim: PYTHONPATH=src python scripts/dev_skill_backtest.py <plant_id> 2026-07-01
Sahte veri URETMEZ: gercek model + tarihsel meteo + mevcut SCADA."""
import sys, json, datetime as dt
from pathlib import Path as _P
sys.path.insert(0, str(_P(__file__).parent.parent))  # repo koku (apps/ icin)
from sqlalchemy import text
from pvquant.db import sistem_baglami, tenant_baglami
from pvquant.io.meteo import OpenMeteoClient
from pvquant.pipeline.forecast import forecast_7day
from pvquant.services.calib_service import _plant_spec, aktif_kalibrasyon
from pvquant.services.forecast_service import _f, kosu_cercevesi_denetle
from apps.worker.main import gece_skill

pid, gun = sys.argv[1], dt.date.fromisoformat(sys.argv[2])
with sistem_baglami() as s:
    plant = dict(s.execute(text("SELECT * FROM plants WHERE id=:p"),
                           {"p": pid}).first()._mapping)
tid = plant["tenant_id"]
cal = aktif_kalibrasyon(tid, pid)
spec = _plant_spec(plant)
pr = json.loads(cal.params_json) if isinstance(cal.params_json, str) else cal.params_json
# spec uzerine kalibre katsayilar (uret_ve_kaydet ile ayni yol)
if "eta_bos" in pr: spec.eta_bos = pr["eta_bos"]
if "bg" in pr or "bifacial_factor" in pr:
    spec.bifacial_factor = pr.get("bifacial_factor", pr.get("bg"))

meteo = OpenMeteoClient().get_historical(
    latitude=plant["lat"], longitude=plant["lon"],
    start_date=str(gun), end_date=str(gun + dt.timedelta(days=3)))
fr = forecast_7day(meteo, spec)
h = fr.hourly.rename(columns={"p_ac_kw": "p50_kw"})
# v2.19 S2: fizik p50 sakla (backtest teshis kanitina hazir)
h["physics_kw"] = h["p50_kw"].copy()
# v2.18: hibrit artefakt varsa uret_ve_kaydet ile AYNI yol uygulanir
kosu_mode = "B"
with tenant_baglami(tid) as s:
    ml = s.execute(text("SELECT artifact_path FROM ml_models "
        "WHERE plant_id=:p AND active LIMIT 1"), {"p": pid}).first()
if cal.mode == "C" and ml:
    import pickle
    from pvquant.pipeline.hybrid_ui import hybrid_forecast_hourly
    with open(ml.artifact_path, "rb") as f:
        model = pickle.load(f)
    hh = hybrid_forecast_hourly(model, meteo)
    if hh is not None:
        h["p50_kw"] = hh["p50_kw"].reindex(h.index)
        h["ml_kw"] = h["p50_kw"] - h["physics_kw"]
        kosu_mode = "C"

kosu_cercevesi_denetle(h)   # v2.176: 15 Nis kapanışı — başsız run bırakılmaz
with tenant_baglami(tid) as s:
    rid = s.execute(text(
        "INSERT INTO forecast_runs(tenant_id,plant_id,run_at,mode,model,"
        "meteo_source) VALUES(:t,:p,:r,:m,\'backtest\',\'open-meteo-arsiv\') "
        "RETURNING id"), {"t": tid, "p": pid,
        "r": dt.datetime.combine(gun, dt.time(5)), "m": kosu_mode}).scalar()
    s.execute(text(
        "INSERT INTO forecast_values(tenant_id,run_id,plant_id,ts_utc,p50_kw,physics_kw,ml_kw)"
        " VALUES(:t,:r,:p,:ts,:v,:px,:ml)"),
        [{"t": tid, "r": rid, "p": pid, "ts": ts, "v": _f(v["p50_kw"]),
           "px": _f(v.get("physics_kw")), "ml": _f(v.get("ml_kw"))}
         for ts, v in h.iterrows()])
    _n = s.execute(text("SELECT count(*) FROM forecast_values "
                        "WHERE run_id=:r"), {"r": rid}).scalar()
    if _n != len(h):   # v2.176 son-bekçi: eksik koşu commit edilmez
        raise RuntimeError(f"koşu geri alındı: values {_n}/{len(h)}")
print(f"[+] Backtest kosu yazildi: run_id={rid}, {len(h)} satir")

gece_skill(plant, pencere_gun=365)
print("[+] gece_skill(pencere_gun=30) kosuldu")

with tenant_baglami(tid) as s:
    r = s.execute(text(
        "SELECT count(*) AS n, min(date) AS ilk, max(date) AS son "
        "FROM skill_daily WHERE plant_id=:p"), {"p": pid}).mappings().first()
    print(f"skill_daily: {dict(r)}")
