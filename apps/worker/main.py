"""PVQuant worker — dort is: sabah tahmini, gece skill, aylik kalibrasyon, alarm."""
from __future__ import annotations
import datetime as dt, traceback
import pandas as pd
from sqlalchemy import text
from apscheduler.schedulers.blocking import BlockingScheduler
from pvquant.db import sistem_baglami, tenant_baglami
from pvquant.services import forecast_service, calib_service, plant_service
from pvquant.services.alarm_service import tara as alarm_tara


def _tum_santraller():
    with sistem_baglami() as s:
        return [dict(r._mapping) for r in s.execute(text(
            "SELECT p.*, p.tenant_id FROM plants p JOIN tenants t "
            "ON t.id=p.tenant_id WHERE t.status='active'"))]


def _logla(job, fn):
    """Her isi jobs_log'a yazan sarmal — 'dun gece ne oldu' cevabi."""
    def ic():
        for plant in _tum_santraller():
            bas = dt.datetime.now(dt.timezone.utc)
            durum, det = "ok", ""
            try:
                fn(plant)
            except Exception as e:
                durum, det = "error", f"{type(e).__name__}: {e}"
                traceback.print_exc()
            with sistem_baglami() as s:
                s.execute(text(
                    "INSERT INTO jobs_log(job,tenant_id,plant_id,started,"
                    " finished,status,detail) VALUES(:j,:t,:p,:b,now(),:s,:d)"),
                    {"j": job, "t": plant["tenant_id"], "p": plant["id"],
                     "b": bas, "s": durum, "d": det[:500]})
    return ic


def sabah_tahmin(plant):
    forecast_service.uret_ve_kaydet(plant["tenant_id"], plant)


def gece_skill(plant, pencere_gun: int = 10):
    """Yeni gerceklesmeleri gecmis kosularla esle, gun+kova skoru yaz.
    v2.16 P1: mape = gunluk WMAPE = sum(|p50-gercek|)/sum(gercek)*100
    (saat-basi MAPE omuz saatlerinde sisiyordu; WMAPE dengesizlik
    maliyetiyle orantili dogru tanim). Naif referans da ayni tanimla."""
    tid, pid = plant["tenant_id"], plant["id"]
    with tenant_baglami(tid) as s:
        df = pd.read_sql(text(
            "SELECT f.ts_utc, f.p50_kw, r.run_at, s.power_kw "
            "FROM forecast_values f "
            "JOIN forecast_runs r ON r.id=f.run_id "
            "JOIN scada_hourly s ON s.plant_id=f.plant_id AND s.ts_utc=f.ts_utc"
            " AND s.flag='valid' "
            "WHERE f.plant_id=:p AND f.ts_utc >= now()-(:g * INTERVAL '1 day')"),
            s.connection(), params={"p": pid, "g": pencere_gun},
            parse_dates=["ts_utc", "run_at"])
    if df.empty:
        return
    df["ufuk_s"] = (df.ts_utc - df.run_at).dt.total_seconds() / 3600
    df = df[df.ufuk_s >= 0]
    df["kova"] = pd.cut(df.ufuk_s, [0, 24, 72, 999],
                        labels=["0-24", "24-72", "72+"])
    df["gun"] = df.ts_utc.dt.date
    gunduz = df.power_kw > 0.02 * float(plant["capacity_kwp"])
    df = df[gunduz]
    if df.empty:
        return
    ap = df.pivot_table(index="ts_utc", values="power_kw", aggfunc="first")
    naif = ap.power_kw.shift(24)
    df = df.merge(naif.rename("naif"), left_on="ts_utc", right_index=True)
    satirlar = []
    for (gun, kova), g in df.groupby(["gun", "kova"], observed=True):
        if len(g) < 3:
            continue
        toplam = float(g.power_kw.sum())
        if toplam <= 0:
            continue
        mape = float(abs(g.p50_kw - g.power_kw).sum() / toplam * 100)  # WMAPE
        rmse = float(((g.p50_kw - g.power_kw) ** 2).mean() ** 0.5)
        gn = g.dropna(subset=["naif"])
        skill = None
        if len(gn) >= 3 and float(gn.power_kw.sum()) > 0:
            nm = float(abs(gn.naif - gn.power_kw).sum()
                       / float(gn.power_kw.sum()) * 100)               # WMAPE
            if nm > 0:
                skill = float(100 * (1 - mape / nm))
        satirlar.append({"t": tid, "p": pid, "g": gun, "k": str(kova),
                         "m": mape, "r": rmse, "s": skill})
    if not satirlar:
        return
    with tenant_baglami(tid) as s:
        s.execute(text(
            "INSERT INTO skill_daily(tenant_id,plant_id,date,horizon_bucket,"
            " mape,rmse,skill_vs_naive) VALUES(:t,:p,:g,:k,:m,:r,:s) "
            "ON CONFLICT (plant_id,date,horizon_bucket) DO UPDATE SET "
            " mape=EXCLUDED.mape, rmse=EXCLUDED.rmse,"
            " skill_vs_naive=EXCLUDED.skill_vs_naive"), satirlar)
def aylik_kalibrasyon(plant):
    calib_service.kalibre_et(plant["tenant_id"], plant, hibrit=True)


if __name__ == "__main__":
    sch = BlockingScheduler(timezone="UTC")
    sch.add_job(_logla("sabah_tahmin", sabah_tahmin), "cron", hour=2, minute=0)
    sch.add_job(_logla("gece_skill", gece_skill), "cron", hour=0, minute=30)
    sch.add_job(_logla("alarm", alarm_tara), "cron", hour=4, minute=0)
    sch.add_job(_logla("aylik_kalibrasyon", aylik_kalibrasyon),
                "cron", day=1, hour=3, minute=0)
    print("PVQuant worker basladi (UTC cron: 00:30 skill / 02:00 tahmin / 04:00 alarm / ay-1 03:00 kal.)")
    sch.start()
