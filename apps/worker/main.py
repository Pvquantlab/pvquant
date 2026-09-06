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
    kosu_id = forecast_service.uret_ve_kaydet(plant["tenant_id"], plant)
    # v2.264: koşu kaydedildikten SONRA webhook (tahmin.yeni); alıcı hatası koşuyu düşürmez
    from pvquant.services import webhook_service
    webhook_service.sabah_sonrasi(plant, str(kosu_id) if kosu_id else None)


def kova_etiketle(ufuk_s: "pd.Series") -> "pd.Series":
    """v2.70: ufuk saatini kovaya esle — 16g ufkuyla dorduncu kova dogdu.
    Eski '72+' kovasi 168 saatlik ufukta fiilen 72-168 idi; 16g kosulari
    baslayinca 3-7g ile 7-15g ayni kovada bulaniklasirdi. Simdi:
    (0,24] / (24,72] / (72,168] / (168,999]. Kova-bazli konformal ayarin
    (defter madde b) hakem verisi 168+ kovasinda birikecek."""
    return pd.cut(ufuk_s, [0, 24, 72, 168, 999],
                  labels=["0-24", "24-72", "72-168", "168+"])


def kova_skorlari(df: "pd.DataFrame", capacity_kwp: float, tid, pid) -> list[dict]:
    """v2.247 — gun+kova skorlarinin SAF hesabi (DB'siz, birim-testli). df kolonlari:
    gun, kova, power_kw, p50_kw, naif (NaN olabilir). Mevcut tanimlar AYNEN korunur
    (mape = gunluk WMAPE %, rmse kW, naif WMAPE %, skill %); yanina Solar Forecast
    Arbiter sozlugu eklenir: nmae/nrmse/nmbe = kapasiteye normalize yuzde
    (pvquant.ext.standart.sfa_metrik — Yang 2020 konsensusu). Kapasite <= 0 ise
    normalize kolonlar None (tire ilkesi: uydurma payda yok)."""
    from pvquant.ext.standart import sfa_metrik as _sfa
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
        skill, nm = None, None
        if len(gn) >= 3 and float(gn.power_kw.sum()) > 0:
            nm = float(abs(gn.naif - gn.power_kw).sum()
                       / float(gn.power_kw.sum()) * 100)               # WMAPE
            if nm > 0:
                skill = float(100 * (1 - mape / nm))
        nmae = nrmse = nmbe = None
        if capacity_kwp and capacity_kwp > 0:
            obs, fx = g.power_kw, g.p50_kw
            nmae = _sfa.nmae(obs, fx, capacity_kwp)
            nrmse = _sfa.nrmse(obs, fx, capacity_kwp)
            nmbe = _sfa.nmbe(obs, fx, capacity_kwp)
        # v2.248 (Dalga 1.3): P10-P90 bandinin sinavi — yalniz bant dolu saatlerde
        # (p10/p90 NULL olan eski kosular atlanir; <3 saat ise None = '—').
        ol = olasiliksal_skorlar(g, capacity_kwp)
        # v2.95 (sartname S4): naif olcumdur, saklanir — turetme donemi bitti.
        satirlar.append({"t": tid, "p": pid, "g": gun, "k": str(kova),
                         "m": mape, "r": rmse, "s": skill, "n": nm,
                         "na": nmae, "nr": nrmse, "nb": nmbe, **ol})
    return satirlar


_OL_BOS = {"q10": None, "q50": None, "q90": None, "cr": None, "pc": None, "k10": None, "k90": None, "bn": None}


def olasiliksal_skorlar(g: "pd.DataFrame", capacity_kwp: float) -> dict:
    """v2.248 — gun+kova icin kantil sinavi (pvquant.ext.tahmin.dogrulama):
    pinball P10/P50/P90 (kW), CRPS (kW, kantillerden), PICP80 (P10<=y<=P90 orani),
    kapsama_p10/p90 (P(y<=q) — reliability uclari), bant_n (ort. genislik/kapasite).
    p10/p90 kolonu yok ya da <3 dolu saat ise hepsi None."""
    if "p10_kw" not in g or "p90_kw" not in g:
        return dict(_OL_BOS)
    d = g.dropna(subset=["p10_kw", "p90_kw"])
    if len(d) < 3:
        return dict(_OL_BOS)
    from pvquant.ext.tahmin import dogrulama as _dg
    y = d.power_kw.astype(float); q = pd.DataFrame({"p10": d.p10_kw, "p50": d.p50_kw, "p90": d.p90_kw}, index=d.index).astype(float)
    kaps = _dg.reliability(y, q).set_index("tau")["gozlenen"]
    return {"q10": _dg.pinball(y, q.p10, 0.1), "q50": _dg.pinball(y, q.p50, 0.5), "q90": _dg.pinball(y, q.p90, 0.9),
            "cr": _dg.crps_kantillerden(y, q), "pc": _dg.picp(y, q.p10, q.p90),
            "k10": float(kaps.loc[0.1]), "k90": float(kaps.loc[0.9]),
            "bn": (_dg.bant_genisligi(q.p10, q.p90, capacity_kwp) if capacity_kwp and capacity_kwp > 0 else None)}


def gece_skill(plant, pencere_gun: int = 10):
    """Yeni gerceklesmeleri gecmis kosularla esle, gun+kova skoru yaz.
    v2.16 P1: mape = gunluk WMAPE = sum(|p50-gercek|)/sum(gercek)*100
    (saat-basi MAPE omuz saatlerinde sisiyordu; WMAPE dengesizlik
    maliyetiyle orantili dogru tanim). Naif referans da ayni tanimla."""
    tid, pid = plant["tenant_id"], plant["id"]
    with tenant_baglami(tid) as s:
        df = pd.read_sql(text(
            "SELECT f.ts_utc, f.p50_kw, f.p10_kw, f.p90_kw, r.run_at, s.power_kw "
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
    # v2.130: naif kaynagi pencere+1 gun — kayan pencerenin ilk tam gununun
    # D-1'i cerceve disinda kaliyor, naif NaN'laniyor ve upsert onceki iyi
    # skoru NULL'la eziyordu (skill_daily'de 2-4 Agu yaralari; her kosu
    # sinir gununu yaralar, pencere kayinca yara kalici olur). Gerceklesme
    # artik scada_hourly'den BIR GUN geriden okunur; skor penceresi (df)
    # DEGISMEZ, yalniz naifin referans verisi tamamlanir. Yan kazanc: naif,
    # 'o saatte tahmin satiri da var' ortuk sartindan kurtulur.
    with tenant_baglami(tid) as s:
        _act = pd.read_sql(text(
            "SELECT ts_utc, power_kw FROM scada_hourly "
            "WHERE plant_id=:p AND flag='valid' "
            "AND ts_utc >= now()-((:g + 1) * INTERVAL '1 day')"),
            s.connection(), params={"p": pid, "g": pencere_gun},
            parse_dates=["ts_utc"]).drop_duplicates("ts_utc") \
            .set_index("ts_utc").power_kw
    df["naif_ham"] = (df.ts_utc - pd.Timedelta(hours=24)).map(_act)
    _ts = pd.DatetimeIndex(sorted(set(df.ts_utc) | set(df.ts_utc - pd.Timedelta(hours=24))))
    _cs = _pvlib.location.Location(float(plant["lat"]), float(plant["lon"]),
                                   tz="UTC").get_clearsky(_ts, model="haurwitz").ghi
    df["_cs_t"] = df.ts_utc.map(_cs)
    df["_cs_d"] = (df.ts_utc - pd.Timedelta(hours=24)).map(_cs)
    df["naif"] = df.naif_ham * (df._cs_t / df._cs_d).clip(1.0 / _clip, _clip)
    df.loc[(df._cs_d <= 5.0) | df.naif_ham.isna(), "naif"] = float("nan")
    satirlar = kova_skorlari(df, float(plant["capacity_kwp"]), tid, pid)  # v2.247
    if not satirlar:
        return
    with tenant_baglami(tid) as s:
        s.execute(text(
            "INSERT INTO skill_daily(tenant_id,plant_id,date,horizon_bucket,"
            " mape,rmse,skill_vs_naive,naive_wmape,nmae,nrmse,nmbe,"
            " pinball_p10,pinball_p50,pinball_p90,crps,picp80,kapsama_p10,kapsama_p90,bant_n)"
            " VALUES(:t,:p,:g,:k,:m,:r,:s,:n,:na,:nr,:nb,:q10,:q50,:q90,:cr,:pc,:k10,:k90,:bn) "
            "ON CONFLICT (plant_id,date,horizon_bucket) DO UPDATE SET "
            " mape=EXCLUDED.mape, rmse=EXCLUDED.rmse,"
            " skill_vs_naive=EXCLUDED.skill_vs_naive,"
            " naive_wmape=EXCLUDED.naive_wmape,"
            " nmae=EXCLUDED.nmae, nrmse=EXCLUDED.nrmse, nmbe=EXCLUDED.nmbe,"
            " pinball_p10=EXCLUDED.pinball_p10, pinball_p50=EXCLUDED.pinball_p50,"
            " pinball_p90=EXCLUDED.pinball_p90, crps=EXCLUDED.crps, picp80=EXCLUDED.picp80,"
            " kapsama_p10=EXCLUDED.kapsama_p10, kapsama_p90=EXCLUDED.kapsama_p90,"
            " bant_n=EXCLUDED.bant_n"), satirlar)
def gece_meteo(_plant=None):
    """v2.268 (Dalga 0) — açık NWP koşularını (ECMWF IFS + ICON-EU) indirip TÜM santrallerin noktalarını
    meteo_arsiv'e yazar; günde bir kez (gece_piyasa kalıbı). sabah_tahmin arşivden okur — API'ye çıkmaz."""
    from pvquant.config import get_settings as _gs
    if _gs().meteo_kaynak != "acik":
        return
    import datetime as _dt
    bugun = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d")
    if getattr(gece_meteo, "_son", None) == bugun:
        return
    from pvquant.io import acik_nwp
    noktalar = [(float(p["lat"]), float(p["lon"])) for p in _tum_santraller()]
    if not noktalar:
        return
    rapor = acik_nwp.kosu_cek_ve_arsivle(noktalar, gefs=True)   # v2.273: üyeler de
    print("gece_meteo:", rapor)
    gece_meteo._son = bugun


def gece_piyasa(_plant=None):
    """v2.258 — EPİAŞ fiyatları (tenant'sız, günde bir kez yeter; _logla santral döngüsünden çağırır,
    ikinci santralde tekrar çekmemek için 'bugün çekildi' bayrağı)."""
    from pvquant.services import piyasa_service
    import datetime as _dt
    bugun = _dt.date.today().isoformat()
    if getattr(gece_piyasa, "_son", None) == bugun:
        return
    piyasa_service.gece_piyasa(gun=3)
    gece_piyasa._son = bugun


def gece_hijyen(plant, pencere_gun: int = 10):
    """v2.254 — gece skill'den ÖNCE: son 10 günün kırpma/kısıntı bayrakları yeniden değerlendirilir
    (kısıntı flag='kisinti' → karne ve kalibrasyon dışı; kırpma yalnız kalibrasyon dışı)."""
    from pvquant.services import hijyen_service
    hijyen_service.gece_hijyen(plant["tenant_id"], plant, gun=pencere_gun)


def gece_konformal(plant, pencere_gun: int = 60):
    """v2.252 — gece skill'den sonra: son 60 günün HAM bandı + gerçekleşenden q̂ (CQR) öğren,
    konformal_ayar'a yaz; sabah tahmini bu ayarla servis bandını düzeltir. Yalnız Mod C
    (kantil üreten) santraller; yetersiz veri → eski ayar kalır, log 'yetersiz'."""
    from pvquant.services import konformal_service
    ayar = konformal_service.q_hat_hesapla(plant["tenant_id"], plant, gun=pencere_gun)
    if ayar is None:
        raise RuntimeError("konformal: yetersiz gündüz/bant verisi (ayar değişmedi)")


def gunluk_toplam(df, tz, gun):
    """v2.205 — saatlik kosu cercevesinden TEK yerel gunun kWh toplamlari.
    Saf fonksiyon (DB'siz, birim-testli). Kurallar:
    - <20 saat kapsama -> None (kismi gunle beklenti YAZILMAZ, uydurma yok)
    - p50_kwh her zaman; p10/p90_kwh ANCAK gunun tum saatlerinde doluysa
      (kismi bant toplami yaniltir — tire ilkesinin toplam hali)
    df: ts_utc indexli p50_kw/p10_kw/p90_kw cercevesi (saatlik kW ~ kWh)."""
    d0 = pd.Timestamp(gun).tz_localize(tz)
    d1 = d0 + pd.Timedelta(days=1)
    ix = pd.DatetimeIndex(df.index)
    if ix.tz is None:          # v2.264: boş/naive okuma (parse_dates boş sonuçta naive döner) → UTC varsay, patlama
        ix = ix.tz_localize("UTC")
    ix = ix.tz_convert(tz)
    win = df[(ix >= d0) & (ix < d1)]
    if len(win) < 20:
        return None
    out = {"p50_kwh": float(win["p50_kw"].sum()), "saat_sayisi": int(len(win))}
    for k in ("p10", "p90"):
        col = win[f"{k}_kw"]
        out[f"{k}_kwh"] = float(col.sum()) if col.notna().all() else None
    return out


def gunluk_beklenti(plant, geriye_gun: int = 120):
    """v2.205 — GUNLUK BEKLENTI ARSIVI: her kapanmis yerel gun icin, GUN
    BASLAMADAN verilmis en taze kosunun toplamlari forecast_daily'ye yazilir.
    ON CONFLICT DO NOTHING: 'gecmis sonuc degistirilmez; yenisi eklenir' —
    bir kez yazilan beklenti sabittir (kiyasin hakemi oynak olamaz)."""
    tid, pid = plant["tenant_id"], plant["id"]
    tz = plant.get("tz") or "UTC"
    bugun = pd.Timestamp.now(tz).date()   # santral yerel bugunu
    with tenant_baglami(tid) as s:
        var = {r.gun for r in s.execute(text(
            "SELECT gun FROM forecast_daily WHERE plant_id=:p "
            "AND gun >= :g0"), {"p": pid,
            "g0": bugun - dt.timedelta(days=geriye_gun)})}
        for i in range(1, geriye_gun + 1):
            gun = bugun - dt.timedelta(days=i)
            if gun in var:
                continue
            d0_utc = pd.Timestamp(gun).tz_localize(tz).tz_convert("UTC")
            run = s.execute(text(
                "SELECT id FROM forecast_runs WHERE plant_id=:p "
                "AND run_at < :d0 "
                "AND EXISTS (SELECT 1 FROM forecast_values v"
                "  WHERE v.run_id = forecast_runs.id) "
                "ORDER BY run_at DESC LIMIT 1"),
                {"p": pid, "d0": d0_utc}).first()
            if not run:
                continue
            df = pd.read_sql(text(
                "SELECT ts_utc,p50_kw,p10_kw,p90_kw FROM forecast_values "
                "WHERE run_id=:r AND ts_utc >= :a AND ts_utc < :b "
                "ORDER BY ts_utc"), s.connection(),
                params={"r": run.id, "a": d0_utc,
                        "b": d0_utc + pd.Timedelta(days=1)},
                index_col="ts_utc", parse_dates=["ts_utc"])
            t = gunluk_toplam(df, tz, gun)
            if t is None:
                continue
            s.execute(text(
                "INSERT INTO forecast_daily(tenant_id,plant_id,gun,"
                " p50_kwh,p10_kwh,p90_kwh,run_id,saat_sayisi)"
                " VALUES(:t,:p,:g,:p50,:p10,:p90,:r,:n)"
                " ON CONFLICT (plant_id,gun) DO NOTHING"),
                {"t": tid, "p": pid, "g": gun, "p50": t["p50_kwh"],
                 "p10": t["p10_kwh"], "p90": t["p90_kwh"],
                 "r": run.id, "n": t["saat_sayisi"]})


def error_matrix_hesapla(d24, gun_sayisi=30, saatler=range(6, 20)):
    """v2.185 (K-F): saat×gün gün-öncesi |hata| matrisi [MW] — B5 fotoğrafının
    kardeş alanı. d24: dedup'lu 0-24 eşleşmeleri (kolonlar: gun, saat, p50_kw,
    power_kw). Son gun_sayisi takvim günü × saatler; eşleşmesiz hücre None
    (uydurma 0 yok). Saf fonksiyon — DB'siz birim-testli."""
    if d24 is None or len(d24) == 0:
        return None
    gunler = sorted(pd.unique(d24["gun"]))[-gun_sayisi:]
    h = d24[d24["gun"].isin(gunler)].copy()
    h["mae"] = (h["p50_kw"] - h["power_kw"]).abs() / 1000.0
    piv = h.pivot_table(index="saat", columns="gun", values="mae", aggfunc="mean")
    mtx = [[(round(float(piv.loc[s, g]), 2)
             if s in piv.index and g in piv.columns and pd.notna(piv.loc[s, g])
             else None) for g in gunler] for s in saatler]
    if not any(v is not None for r in mtx for v in r):
        return None
    return {"days": [str(g) for g in gunler],
            "hours": list(saatler), "mae_mw": mtx}


def karne_kapsama_hesapla(gecerli_ts, tz, bugun=None, gun=30,
                          bas=None, son=None):
    """C-3b (v2.152, s08 kuralı 2): son `gun` takvim günü (dünle biter,
    v2.140 çapa kuralı) için gün içi kapsama yüzdesi. Gün içi = yerel
    [bas, son] saat aralığı (varsayılan config: 06–19, B5 mae penceresiyle
    aynı 14 saat — mevsimsel gündoğumu oynaklığı yerine sabit, belirlenimci
    payda). Saf fonksiyon: DB'siz test edilir (üreticiden beslenen fikstür).
    → {'YYYY-AA-GG': yüzde_int}; verisiz gün 0 (yokluk gizlenmez)."""
    from pvquant.config import get_settings
    ayar = get_settings()
    bas = ayar.karne_gunduz_bas if bas is None else bas
    son = ayar.karne_gunduz_son if son is None else son
    payda = son - bas + 1
    bugun = bugun or dt.datetime.now(dt.timezone.utc).date()
    ts = pd.DatetimeIndex(gecerli_ts)
    if ts.tz is None:
        ts = ts.tz_localize("UTC")
    yerel = ts.tz_convert(tz)
    yerel = yerel[(yerel.hour >= bas) & (yerel.hour <= son)]
    sayim = pd.Series(1, index=yerel).groupby(
        [yerel.date, yerel.hour]).first().groupby(level=0).sum()
    out = {}
    for g in range(gun, 0, -1):
        t = bugun - dt.timedelta(days=g)
        n = int(sayim.get(t, 0))
        out[str(t)] = int(round(min(n, payda) / payda * 100))
    return out


def rapor_alanlari(plant, pencere_gun: int = 120):
    """v2.103 (E.3-a, B1+B5 — karar 9 Agu): rapor fotograflari report_stats'a.
    Tek uretici worker; servis yalniz OKUR (v2.96 ilkesi). Pencere 120 gun =
    skill_gecmisi(gun=120) ile AYNI (uc yuzey ayni sayiyi soyler).
    B1 uninterrupted_days: DUNDEN geriye ilk olculmemis gune kadar (v2.142)
    kesintisiz gun sayisi (servis karneden TURETMEZ — B1 karari, 8 Agu).
    B5 error_dist: s08 sozlugu — prof_mw[15] (yerel 05-19 medyan gercek MW),
    mae24/mae72[14] (yerel 06-19 saatlik MAE MW), mu/sd/ndays (F-A MWh/gun,
    >=8 gunduz saati eslesen gunler; %60 kapsama esiginin vekili)."""
    import json as _json
    tid, pid = plant["tenant_id"], plant["id"]
    # --- B1 ---
    with tenant_baglami(tid) as s:
        gunler = [r.date for r in s.execute(text(
            "SELECT DISTINCT date FROM skill_daily WHERE plant_id=:p "
            "AND horizon_bucket='0-24' ORDER BY date DESC LIMIT 400"),
            {"p": pid})]
    # v2.142: capa DUN'dur, son-veri-gunu degil. Eski hali gunler[0]'a
    # (skill_daily'deki son gune) capa atiyordu; SCADA kesilince sayac orada
    # DONUYORDU (canli D18 avi: kuyruk t=0 iken kart 46 diyordu). Sartname:
    # "bugunden geriye ilk olculmemis gune kadar" — dun olculmemisse 0.
    kesintisiz = 0
    beklenen = dt.datetime.now(dt.timezone.utc).date() - dt.timedelta(days=1)
    for g in gunler:
        if g != beklenen:
            break
        kesintisiz += 1
        beklenen = beklenen - dt.timedelta(days=1)
    # --- C-3b (v2.152): karne_kapsama — gün içi geçerli saat oranı, son 30
    # takvim günü. Kaynak scada_hourly flag='valid' TEK BAŞINA (tahmin
    # eşleşmesinden bağımsız: kapsama SCADA'nın malı, forecast'ın değil).
    with tenant_baglami(tid) as s:
        _kts = pd.read_sql(text(
            "SELECT ts_utc FROM scada_hourly WHERE plant_id=:p "
            "AND flag='valid' AND ts_utc >= now()-INTERVAL '31 days'"),
            s.connection(), params={"p": pid}, parse_dates=["ts_utc"]).ts_utc
    kapsama = karne_kapsama_hesapla(_kts, plant["tz"])
    # --- B5 ---
    with tenant_baglami(tid) as s:
        df = pd.read_sql(text(
            "SELECT f.ts_utc, f.p50_kw, r.run_at, sc.power_kw "
            "FROM forecast_values f "
            "JOIN forecast_runs r ON r.id=f.run_id "
            "JOIN scada_hourly sc ON sc.plant_id=f.plant_id "
            " AND sc.ts_utc=f.ts_utc AND sc.flag='valid' "
            "WHERE f.plant_id=:p AND f.ts_utc >= now()-(:g * INTERVAL '1 day')"),
            s.connection(), params={"p": pid, "g": pencere_gun},
            parse_dates=["ts_utc", "run_at"])
    foto = None
    if not df.empty:
        df["ts_utc"] = pd.to_datetime(df.ts_utc, utc=True)
        df["run_at"] = pd.to_datetime(df.run_at, utc=True)
        df["ufuk_s"] = (df.ts_utc - df.run_at).dt.total_seconds() / 3600
        df = df[df.ufuk_s >= 0]
        df["kova"] = kova_etiketle(df.ufuk_s)
        yerel = df.ts_utc.dt.tz_convert(plant["tz"])
        df["saat"], df["gun"] = yerel.dt.hour, yerel.dt.date
        gunduz = df.power_kw > 0.02 * float(plant["capacity_kwp"])
        d24 = df[(df.kova == "0-24")].sort_values("ufuk_s").drop_duplicates("ts_utc")
        d24g = d24[d24.power_kw > 0.02 * float(plant["capacity_kwp"])]
        if len(d24g) > 0:
            med = d24g.groupby("saat").power_kw.median()
            prof = [round(float(med.get(h, 0.0)) / 1000, 1) for h in range(5, 20)]
            m24 = df[df.kova == "0-24"].groupby("saat").apply(
                lambda g: float(abs(g.p50_kw - g.power_kw).mean()), include_groups=False)
            m72 = df[df.kova == "24-72"].groupby("saat").apply(
                lambda g: float(abs(g.p50_kw - g.power_kw).mean()), include_groups=False)
            mae24 = [round(float(m24.get(h, 0.0)) / 1000, 2) for h in range(6, 20)]
            mae72 = [round(float(m72.get(h, 0.0)) / 1000, 2) for h in range(6, 20)]
            sapma = d24g.groupby("gun").filter(lambda g: len(g) >= 8)
            gs = sapma.groupby("gun").apply(
                lambda g: float((g.p50_kw - g.power_kw).sum()) / 1000,
                include_groups=False)
            if len(gs) >= 2:
                foto = {"prof_mw": prof, "mae24": mae24, "mae72": mae72,
                        "mu": round(float(gs.mean()), 1),
                        "sd": round(float(gs.std(ddof=1)), 1),
                        "ndays": int(len(gs))}
                # v2.185 (K-F): matris fotoğrafın kardeş alanı — d24'ün
                # kendisinden (aynı dedup, aynı valid-join); yoksa alan yok,
                # rapor koşullu davranır (Şekil 8.3 basılmaz).
                _mtx = error_matrix_hesapla(d24)
                if _mtx:
                    foto["error_matrix"] = _mtx
    with tenant_baglami(tid) as s:
        for k, v in [("uninterrupted_days", {"value": int(kesintisiz)}),
                     ("error_dist", foto),
                     ("karne_kapsama", {"days": kapsama})]:
            if v is None:
                continue
            s.execute(text(
                "INSERT INTO report_stats(tenant_id,plant_id,key,value_json,"
                " updated_at) VALUES(:t,:p,:k,CAST(:v AS jsonb),now()) "
                "ON CONFLICT (plant_id,key) DO UPDATE SET "
                " value_json=EXCLUDED.value_json, updated_at=now()"),
                {"t": tid, "p": pid, "k": k, "v": _json.dumps(v)})


def aylik_kalibrasyon(plant):
    calib_service.kalibre_et(plant["tenant_id"], plant, hibrit=True)


def aylik_iklim(plant):
    """v2.77-C: iklim beklentisi ayda bir tazelenir (KUTU-2 hesaplayan yol).
    Arsiv probu olcumu: 20 yil tek cagri ~3 sn — santral basina ucuz."""
    from pvquant.services import iklim_service
    t, b = iklim_service.iklim_hesapla(plant["lat"], plant["lon"],
                                       tz=plant.get("tz"))
    iklim_service.iklim_kaydet(plant["tenant_id"], plant["id"], b)
    iklim_service.iklim_yil_kaydet(plant["tenant_id"], plant["id"], t)  # v2.78-A


if __name__ == "__main__":
    import sys
    from pvquant.config import get_settings
    cfg = get_settings()
    if "--once" in sys.argv:
        # v2.56: elle tam tur — scheduler'siz, sirayla. Aylik kalibrasyon
        # BILEREK haric (durum degistiren agir is; takvimin/kullanicinin isi).
        print("PVQuant worker --once: tam tur basliyor…")
        _logla("gece_meteo", gece_meteo)()                  # v2.268 (Dalga 0): NWP arşivi önce
        _logla("gece_piyasa", gece_piyasa)()                # v2.258 (kimlik yoksa atlar)
        _logla("gece_hijyen", gece_hijyen)()                # v2.254 (skill'den once)
        _logla("gece_skill", gece_skill)()
        _logla("gece_konformal", gece_konformal)()          # v2.252
        _logla("gunluk_beklenti", gunluk_beklenti)()        # v2.205
        _logla("rapor_alanlari", rapor_alanlari)()          # v2.103 (B1+B5)
        _logla("sabah_tahmin", sabah_tahmin)()
        _logla("alarm", alarm_tara)()
        print("Tam tur bitti — kanit jobs_log'da.")
        raise SystemExit(0)
    sch = BlockingScheduler(timezone="UTC", job_defaults=dict(coalesce=True, misfire_grace_time=3600, max_instances=1))
    sch.add_job(_logla("gece_meteo", gece_meteo), "cron",                # v2.268: tahminden 1 saat önce
                hour=(cfg.worker_hour_forecast - 1) % 24, minute=0)
    sch.add_job(_logla("sabah_tahmin", sabah_tahmin), "cron", hour=cfg.worker_hour_forecast, minute=0)
    sch.add_job(_logla("gece_piyasa", gece_piyasa), "cron", hour=cfg.worker_hour_skill, minute=15)   # v2.258
    sch.add_job(_logla("gece_hijyen", gece_hijyen), "cron", hour=cfg.worker_hour_skill, minute=20)   # v2.254
    sch.add_job(_logla("gece_skill", gece_skill), "cron", hour=cfg.worker_hour_skill, minute=30)
    sch.add_job(_logla("gece_konformal", gece_konformal),                # v2.252
                "cron", hour=cfg.worker_hour_skill, minute=35)
    sch.add_job(_logla("gunluk_beklenti", gunluk_beklenti),              # v2.205
                "cron", hour=cfg.worker_hour_skill, minute=40)
    sch.add_job(_logla("rapor_alanlari", rapor_alanlari),                # v2.103 (B1+B5)
                "cron", hour=cfg.worker_hour_skill, minute=45)
    sch.add_job(_logla("alarm", alarm_tara), "cron", hour=cfg.worker_hour_alarm, minute=0)
    sch.add_job(_logla("aylik_kalibrasyon", aylik_kalibrasyon),
                "cron", day=cfg.worker_day_calibration, hour=cfg.worker_hour_calibration, minute=0)
    sch.add_job(_logla("aylik_iklim", aylik_iklim),                      # v2.77-C
                "cron", day=cfg.worker_day_calibration, hour=cfg.worker_hour_calibration, minute=30)
    print(f"PVQuant worker basladi (UTC cron: {cfg.worker_hour_skill:02d}:30 skill /"
          f" {cfg.worker_hour_forecast:02d}:00 tahmin / {cfg.worker_hour_alarm:02d}:00 alarm /"
          f" ay-{cfg.worker_day_calibration} {cfg.worker_hour_calibration:02d}:00 kal.)")
    sch.start()
