"""Dogruluk sunum hesaplari. hata_matrisi: saat x gun isaretli hata matrisi.
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


def hata_matrisi(tenant_id, plant_id, gun: int = 30, kova: str = "0-24"):
    """Dunle biten N tam YEREL gunun saat x gun isaretli hatasi (p50 - gercek, kW).
    Gece / verisiz / bayrakli hucreler None. Ayni hucreye birden cok gozlem
    duserse ortalama (kural belirsizligi olmasin)."""
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
    saatler = ["%02d\u2013%02d" % (h, h + 1) for h in range(_SAAT_ILK, _SAAT_SON)]
    bos = {"gunler": [], "saatler": saatler, "hucreler": [],
           "metrik": "isaretli_hata", "birim": "kW", "kova": kova, "tz": tz}
    if df.empty:
        return bos
    ufuk = (df.ts_utc - df.run_at).dt.total_seconds() / 3600
    df = df[(ufuk > lo) & (ufuk <= hi)]
    if df.empty:
        return bos
    if df.ts_utc.dt.tz is None:                       # surucu naive verdiyse
        yerel = df.ts_utc.dt.tz_localize("UTC").dt.tz_convert(tz)
    else:                                             # psycopg3: zaten aware
        yerel = df.ts_utc.dt.tz_convert(tz)
    df = df.assign(y_gun=yerel.dt.date, y_saat=yerel.dt.hour)
    # dunle biten N tam yerel gun
    dun = (pd.Timestamp.now(tz=tz) - pd.Timedelta(days=1)).date()
    ilk = dun - pd.Timedelta(days=gun - 1)
    df = df[(df.y_gun >= ilk) & (df.y_gun <= dun)]
    df = df[(df.y_saat >= _SAAT_ILK) & (df.y_saat < _SAAT_SON)]
    df = df[df.power_kw > 0.02 * float(p["capacity_kwp"])]      # gunduz
    if df.empty:
        return bos
    df = df.assign(hata=df.p50_kw - df.power_kw)
    piv = df.pivot_table(index="y_saat", columns="y_gun",
                         values="hata", aggfunc="mean")
    gunler = sorted(df.y_gun.unique())
    piv = piv.reindex(index=range(_SAAT_ILK, _SAAT_SON), columns=gunler)
    hucreler = [[None if pd.isna(v) else round(float(v), 1) for v in satir]
                for satir in piv.values]
    return {"gunler": [g.isoformat() for g in gunler], "saatler": saatler,
            "hucreler": hucreler, "metrik": "isaretli_hata", "birim": "kW",
            "kova": kova, "tz": tz}


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
    # (heatmap'in mean'iyle ozdes — iki panel ayni sayiyi soyler)
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
