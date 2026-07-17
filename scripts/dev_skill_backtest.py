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
from pvquant.services.forecast_service import _f
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

with tenant_baglami(tid) as s:
    rid = s.execute(text(
        "INSERT INTO forecast_runs(tenant_id,plant_id,run_at,mode,model,"
        "meteo_source) VALUES(:t,:p,:r,:m,\'backtest\',\'open-meteo-arsiv\') "
        "RETURNING id"), {"t": tid, "p": pid,
        "r": dt.datetime.combine(gun, dt.time(5)), "m": cal.mode}).scalar()
    s.execute(text(
        "INSERT INTO forecast_values(tenant_id,run_id,plant_id,ts_utc,p50_kw)"
        " VALUES(:t,:r,:p,:ts,:v)"),
        [{"t": tid, "r": rid, "p": pid, "ts": ts, "v": _f(v["p50_kw"])}
         for ts, v in h.iterrows()])
print(f"[+] Backtest kosu yazildi: run_id={rid}, {len(h)} satir")

gece_skill(plant, pencere_gun=365)
print("[+] gece_skill(pencere_gun=30) kosuldu")

with tenant_baglami(tid) as s:
    r = s.execute(text(
        "SELECT count(*) AS n, min(date) AS ilk, max(date) AS son "
        "FROM skill_daily WHERE plant_id=:p"), {"p": pid}).mappings().first()
    print(f"skill_daily: {dict(r)}")
