"""Dogruluk/Kalibrasyon sunum hesaplari. saat_profili: saat basina ortalama isaretli hata (v2.532; eski hata_matrisi kaldirildi).
Kurallar gece_skill ile ozdes (tek kural kitabi): flag='valid' eslesme,
ufuk = ts_utc - run_at, gunduz = power > %2 kapasite. Hesap hafif tutulur;
agir skorlar worker'da (tek uretici o), burada ham eslesme + pivot var."""
from __future__ import annotations
import pandas as pd
from sqlalchemy import text
from pvquant.db import tenant_baglami

_KOVALAR = {"0-24": (0, 24), "24-72": (24, 72),
            "72-168": (72, 168), "168+": (168, 999)}
_SAAT_ILK, _SAAT_SON = 5, 20          # rapor s06 ile ayni iskelet (05-20 yerel)


def saat_profili_hesapla(df: pd.DataFrame, kapasite_kwp: float, tz: str, gun: int, bugun=None) -> dict:
    """SAF (v2.532): eşleşmiş saatlik çiftlerden (ts_utc, p50_kw, power_kw) saat başına ortalama İŞARETLİ hata (p50 − gerçek, kW)
    ve ortalama mutlak hata; dünle biten N tam yerel gün, gündüz (> %2 kapasite), 05–20 yerel. Aynı saate birden çok gözlem düşerse
    önce saatlik ortalama (çoklu-koşu savunması, hata_dagilimi ile özdeş). `sistematik`: |ortalama işaretli hata| ≥ %5 kapasite ve
    n ≥ 5 olan saatler (yön: fazla | eksik). Eski saat × gün matrisi (v2.111 hata_matrisi) 04.11.2026'da kaldırıldı: müşteri için
    karar üretmiyordu; kalibrasyonun teşhis bilgisi olan saat profili Kalibrasyon sayfasına taşındı."""
    saatler = ["%02d\u2013%02d" % (h, h + 1) for h in range(_SAAT_ILK, _SAAT_SON)]
    esik = 0.05 * float(kapasite_kwp)
    bos = {"saatler": saatler, "profil": [{"saat": a, "ort_hata_kw": None, "ort_mutlak_kw": None, "n": 0} for a in saatler],
           "gun_sayisi": 0, "ilk_gun": None, "son_gun": None, "sistematik": [], "esik_kw": round(esik, 1),
           "metrik": "isaretli_hata", "birim": "kW", "tz": tz}
    if df is None or df.empty:
        return bos
    if df.ts_utc.dt.tz is None:
        yerel = df.ts_utc.dt.tz_localize("UTC").dt.tz_convert(tz)
    else:
        yerel = df.ts_utc.dt.tz_convert(tz)
    df = df.assign(y_gun=yerel.dt.date, y_saat=yerel.dt.hour)
    dun = ((bugun if bugun is not None else pd.Timestamp.now(tz=tz)) - pd.Timedelta(days=1)).date()
    ilk = dun - pd.Timedelta(days=gun - 1)
    df = df[(df.y_gun >= ilk) & (df.y_gun <= dun)]
    df = df[(df.y_saat >= _SAAT_ILK) & (df.y_saat < _SAAT_SON)]
    df = df[df.power_kw > 0.02 * float(kapasite_kwp)]
    if df.empty:
        return bos
    df = (df.groupby(["y_gun", "y_saat"], as_index=False).agg(p50_kw=("p50_kw", "mean"), power_kw=("power_kw", "mean")))
    df = df.assign(hata=df.p50_kw - df.power_kw, mutlak=(df.p50_kw - df.power_kw).abs())
    g = df.groupby("y_saat").agg(ort=("hata", "mean"), mut=("mutlak", "mean"), n=("hata", "size"))
    profil = []; sistematik = []
    for h, ad in zip(range(_SAAT_ILK, _SAAT_SON), saatler):
        if h in g.index:
            ort, mut, n = float(g.loc[h, "ort"]), float(g.loc[h, "mut"]), int(g.loc[h, "n"])
            profil.append({"saat": ad, "ort_hata_kw": round(ort, 1), "ort_mutlak_kw": round(mut, 1), "n": n})
            if n >= 5 and abs(ort) >= esik:
                sistematik.append({"saat": ad, "yon": "fazla" if ort > 0 else "eksik", "ort_hata_kw": round(ort, 1), "n": n})
        else:
            profil.append({"saat": ad, "ort_hata_kw": None, "ort_mutlak_kw": None, "n": 0})
    gunler = sorted(df.y_gun.unique())
    return {"saatler": saatler, "profil": profil, "gun_sayisi": len(gunler), "ilk_gun": gunler[0].isoformat(), "son_gun": gunler[-1].isoformat(),
            "sistematik": sistematik, "esik_kw": round(esik, 1), "metrik": "isaretli_hata", "birim": "kW", "tz": tz}


def saat_profili(tenant_id, plant_id, gun: int = 30, kova: str = "0-24"):
    """Saat başına ortalama işaretli hata (Kalibrasyon sayfası). Kurallar hata_dagilimi ile özdeş: flag='valid' eşleşme, ufuk kovası,
    gündüz > %2 kapasite, dünle biten N tam yerel gün."""
    if kova not in _KOVALAR:
        raise ValueError("bilinmeyen kova: %s" % kova)
    lo, hi = _KOVALAR[kova]
    with tenant_baglami(tenant_id) as s:
        p = s.execute(text(
            "SELECT tz, capacity_kwp FROM plants WHERE id=:p"),
            {"p": plant_id}).mappings().first()
        if p is None:
            raise LookupError("santral yok: %s" % plant_id)
        df = pd.read_sql(text(
            "SELECT f.ts_utc, f.p50_kw, r.run_at, s.power_kw "
            "FROM forecast_values f "
            "JOIN forecast_runs r ON r.id=f.run_id "
            "JOIN scada_hourly s ON s.plant_id=f.plant_id AND s.ts_utc=f.ts_utc"
            " AND s.flag='valid' "
            "WHERE f.plant_id=:p "
            "AND f.ts_utc >= now() - ((:g + 2) * INTERVAL '1 day')"),
            s.connection(), params={"p": plant_id, "g": gun},
            parse_dates=["ts_utc", "run_at"])
    tz = p["tz"] or "UTC"
    if not df.empty:
        ufuk = (df.ts_utc - df.run_at).dt.total_seconds() / 3600
        df = df[(ufuk > lo) & (ufuk <= hi)]
    return saat_profili_hesapla(df, float(p["capacity_kwp"]), tz, gun)


def hata_dagilimi(tenant_id, plant_id, gun: int = 120, kova: str = "0-24",
                  kutu_mwh: float = 0.5):
    """Gunluk sapma dagilimi (F - A, MWh/gun) — rapor s08 tanimiyla ozdes.
    Saatlik ciftler (gece_skill kurallari) yerel gune toplanir; gunde >= 3
    eslesmis gunduz saati yoksa gun dagilima girmez. Kutu genisligi 1 MWh,
    sinirlar veriden. Yuzdelikler ham gunluk sapmalardan (interpolasyonsuz
    numpy percentile, linear)."""
    if kova not in _KOVALAR:
        raise ValueError("bilinmeyen kova: %s" % kova)
    lo, hi = _KOVALAR[kova]
    with tenant_baglami(tenant_id) as s:
        p = s.execute(text(
            "SELECT tz, capacity_kwp FROM plants WHERE id=:p"),
            {"p": plant_id}).mappings().first()
        if p is None:
            raise LookupError("santral yok: %s" % plant_id)
        df = pd.read_sql(text(
            "SELECT f.ts_utc, f.p50_kw, r.run_at, s.power_kw "
            "FROM forecast_values f "
            "JOIN forecast_runs r ON r.id=f.run_id "
            "JOIN scada_hourly s ON s.plant_id=f.plant_id AND s.ts_utc=f.ts_utc"
            " AND s.flag='valid' "
            "WHERE f.plant_id=:p "
            "AND f.ts_utc >= now() - ((:g + 2) * INTERVAL '1 day')"),
            s.connection(), params={"p": plant_id, "g": gun},
            parse_dates=["ts_utc", "run_at"])
    tz = p["tz"] or "UTC"
    bos = {"kutular": [], "mu": None, "sd": None, "ndays": 0,
           "p10": None, "p50": None, "p90": None,
           "birim": "MWh/gun", "kova": kova, "tz": tz}
    if df.empty:
        return bos
    ufuk = (df.ts_utc - df.run_at).dt.total_seconds() / 3600
    df = df[(ufuk > lo) & (ufuk <= hi)]
    if df.empty:
        return bos
    if df.ts_utc.dt.tz is None:
        yerel = df.ts_utc.dt.tz_localize("UTC").dt.tz_convert(tz)
    else:
        yerel = df.ts_utc.dt.tz_convert(tz)
    df = df.assign(y_gun=yerel.dt.date)
    dun = (pd.Timestamp.now(tz=tz) - pd.Timedelta(days=1)).date()
    ilk = dun - pd.Timedelta(days=gun - 1)
    df = df[(df.y_gun >= ilk) & (df.y_gun <= dun)]
    df = df[df.power_kw > 0.02 * float(p["capacity_kwp"])]      # gunduz
    if df.empty:
        return bos
    # coklu-kosu savunmasi: ayni saate birden cok gozlem duserse ortala
    # (saat profilinin mean'iyle ozdes — iki panel ayni sayiyi soyler)
    df = (df.groupby(["y_gun", "ts_utc"], as_index=False)
            .agg(p50_kw=("p50_kw", "mean"), power_kw=("power_kw", "mean")))
    g = df.groupby("y_gun").agg(n=("power_kw", "size"),
                                f=("p50_kw", "sum"), a=("power_kw", "sum"))
    g = g[g.n >= 3]                                              # gecerli gun
    if g.empty:
        return bos
    sapma = ((g.f - g.a) / 1000.0).astype(float)                 # kWh -> MWh
    import numpy as np
    mu, sd = float(sapma.mean()), float(sapma.std(ddof=1)) if len(sapma) > 1 else 0.0
    p10, p50, p90 = (float(np.percentile(sapma, q)) for q in (10, 50, 90))
    import math
    alt = math.floor(float(sapma.min()) / kutu_mwh) * kutu_mwh
    ust = math.ceil(float(sapma.max()) / kutu_mwh) * kutu_mwh
    if ust <= alt:
        ust = alt + kutu_mwh
    kutular = []
    k_lo = alt
    while k_lo < ust - 1e-9:
        k_hi = k_lo + kutu_mwh
        adet = int(((sapma >= k_lo) & (sapma < k_hi)).sum())
        kutular.append({"lo": round(k_lo, 2), "hi": round(k_hi, 2), "adet": adet})
        k_lo = k_hi
    return {"kutular": kutular, "mu": round(mu, 2), "sd": round(sd, 2),
            "ndays": int(len(sapma)), "p10": round(p10, 2),
            "p50": round(p50, 2), "p90": round(p90, 2),
            "birim": "MWh/gun", "kova": kova, "tz": tz}
