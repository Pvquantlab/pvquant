"""PVQuant worker — dort is: sabah tahmini, gece skill, aylik kalibrasyon, alarm."""
from __future__ import annotations
import datetime as dt, traceback
import pandas as pd
from sqlalchemy import text
from apscheduler.schedulers.blocking import BlockingScheduler
from pvquant.db import sistem_baglami, tenant_baglami
from pvquant.services import forecast_service, calib_service, plant_service
from pvquant.services.alarm_service import tara as alarm_tara

import os as _os
try:
    import sentry_sdk
    if _os.environ.get("PVQ_SENTRY_DSN"):
        sentry_sdk.init(dsn=_os.environ["PVQ_SENTRY_DSN"],
                        traces_sample_rate=0)
except ImportError:
    pass  # sentry-sdk kurulu değilse sessiz geç (dev ortamı)


def _tum_santraller():
    with sistem_baglami() as s:
        return [dict(r._mapping) for r in s.execute(text(
            "SELECT p.*, p.tenant_id FROM plants p JOIN tenants t "
            "ON t.id=p.tenant_id WHERE t.status='active' AND NOT p.archived"))]


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


def kova_etiketle(ufuk_s: "pd.Series") -> "pd.Series":
    """v2.70: ufuk saatini kovaya esle — 16g ufkuyla dorduncu kova dogdu.
    Eski '72+' kovasi 168 saatlik ufukta fiilen 72-168 idi; 16g kosulari
    baslayinca 3-7g ile 7-16g ayni kovada bulaniklasirdi. Simdi:
    (0,24] / (24,72] / (72,168] / (168,999]. Kova-bazli konformal ayarin
    (defter madde b) hakem verisi 168+ kovasinda birikecek."""
    return pd.cut(ufuk_s, [0, 24, 72, 168, 999],
                  labels=["0-24", "24-72", "72-168", "168+"])


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
    df["kova"] = kova_etiketle(df.ufuk_s)  # v2.70: 4 kova
    df["gun"] = df.ts_utc.dt.date
    gunduz = df.power_kw > 0.02 * float(plant["capacity_kwp"])
    df = df[gunduz]
    if df.empty:
        return
    # v2.55: AKILLI persistans (Kutu 14) — iki duzeltme birden:
    # (1) zaman-bazli dun-ayni-saat: eski shift(24) POZISYONELdi ve gunduz
    #     filtresinden sonra ~2 gun kayiyordu (hizalama hatasi).
    # (2) berrak-gok orani: dun bulutlu / bugun acik farki citaya islenir;
    #     duz 'dun=bugun' citasi puani sisiriyordu (kitap Kutu 14 tuzagi).
    import pvlib as _pvlib
    from pvquant.config import get_settings as _gs
    _clip = _gs().skill_naive_ratio_clip
    _act = df.drop_duplicates("ts_utc").set_index("ts_utc").power_kw
    df["naif_ham"] = (df.ts_utc - pd.Timedelta(hours=24)).map(_act)
    _ts = pd.DatetimeIndex(sorted(set(df.ts_utc) | set(df.ts_utc - pd.Timedelta(hours=24))))
    _cs = _pvlib.location.Location(float(plant["lat"]), float(plant["lon"]),
                                   tz="UTC").get_clearsky(_ts, model="haurwitz").ghi
    df["_cs_t"] = df.ts_utc.map(_cs)
    df["_cs_d"] = (df.ts_utc - pd.Timedelta(hours=24)).map(_cs)
    df["naif"] = df.naif_ham * (df._cs_t / df._cs_d).clip(1.0 / _clip, _clip)
    df.loc[(df._cs_d <= 5.0) | df.naif_ham.isna(), "naif"] = float("nan")
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
    import sys
    from pvquant.config import get_settings
    cfg = get_settings()
    if "--once" in sys.argv:
        # v2.56: elle tam tur — scheduler'siz, sirayla. Aylik kalibrasyon
        # BILEREK haric (durum degistiren agir is; takvimin/kullanicinin isi).
        print("PVQuant worker --once: tam tur basliyor…")
        _logla("gece_skill", gece_skill)()
        _logla("sabah_tahmin", sabah_tahmin)()
        _logla("alarm", alarm_tara)()
        print("Tam tur bitti — kanit jobs_log'da.")
        raise SystemExit(0)
    sch = BlockingScheduler(timezone="UTC", job_defaults=dict(coalesce=True, misfire_grace_time=3600, max_instances=1))
    sch.add_job(_logla("sabah_tahmin", sabah_tahmin), "cron", hour=cfg.worker_hour_forecast, minute=0)
    sch.add_job(_logla("gece_skill", gece_skill), "cron", hour=cfg.worker_hour_skill, minute=30)
    sch.add_job(_logla("alarm", alarm_tara), "cron", hour=cfg.worker_hour_alarm, minute=0)
    sch.add_job(_logla("aylik_kalibrasyon", aylik_kalibrasyon),
                "cron", day=cfg.worker_day_calibration, hour=cfg.worker_hour_calibration, minute=0)
    print(f"PVQuant worker basladi (UTC cron: {cfg.worker_hour_skill:02d}:30 skill /"
          f" {cfg.worker_hour_forecast:02d}:00 tahmin / {cfg.worker_hour_alarm:02d}:00 alarm /"
          f" ay-{cfg.worker_day_calibration} {cfg.worker_hour_calibration:02d}:00 kal.)")
    sch.start()
