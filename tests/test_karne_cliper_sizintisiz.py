"""G2-B1a (Faz 1 G2B-02) — karne CLIPER referansi bagimsiz motor tanimiyla ayni; kosu bazli cipa (donem_bas = run_at):
orneklem disi, yayin anindan sonra gelen hic bir gozlem kullanilmaz, yetersizse NaN, deterministik."""
import numpy as np
import pandas as pd
import pvlib

from apps.worker.main import CLIPER_GECMIS_GUN, karne_cliper, karne_cliper_kosu_bazli, kova_skorlari
from pvquant.services import bagimsiz_dogrulama_service as bd

LAT, LON = 37.7, 33.5


def _gecmis(bas="2025-06-01", gun=540, kwp=1000.0, seed=0):
    # 540 gun: onceki yilin ayni ayi da var -> ay x saat iklimsel (>= 20 gun) run_at oncesinden dolabilir
    ix = pd.date_range(bas, periods=24 * gun, freq="h", tz="UTC")
    cs = pvlib.location.Location(LAT, LON, tz="UTC").get_clearsky(ix, model="haurwitz").ghi
    rng = np.random.default_rng(seed)
    return pd.Series((cs / 1000.0 * kwp * rng.uniform(0.6, 0.95, len(ix))).values, index=ix)


def _hedef(bas, gun=10):
    # her gun 02:00 UTC yayin kosusu; hedefler ayni gun 06-15 UTC (k=1) + ertesi gun (k=2) + 3 gun sonrasi (k=4)
    rows = []
    for g in range(gun):
        run = bas + pd.Timedelta(days=g, hours=2)
        for d in (0, 1, 3):
            for h in range(6, 16):
                rows.append({"ts_utc": run.normalize() + pd.Timedelta(days=d, hours=h), "run_at": run})
    return pd.DataFrame(rows)


def test_kosu_bazli_motorla_birebir():
    gecmis = _gecmis()
    df = _hedef(pd.Timestamp("2026-11-08", tz="UTC"))
    k = karne_cliper_kosu_bazli(df, gecmis, LAT, LON)
    assert k.notna().sum() > 200
    for run_at, idx in df.groupby("run_at").groups.items():
        kesit = gecmis[(gecmis.index >= run_at - pd.Timedelta(days=CLIPER_GECMIS_GUN)) & (gecmis.index < run_at)]   # tanim: 400 gun, run_at oncesi
        m, bilgi = bd.cliper(df.loc[idx, ["ts_utc", "run_at"]], kesit, pd.Timestamp(run_at), LAT, LON)
        assert bilgi is not None
        np.testing.assert_allclose(k.loc[idx].values, m.values, rtol=1e-12, equal_nan=True)
        np.testing.assert_allclose(karne_cliper(df.loc[idx], gecmis, run_at, LAT, LON).values, m.values, rtol=1e-12, equal_nan=True)


def test_yayin_anindan_sonraki_hic_bir_gozlem_kullanilmaz():
    gecmis = _gecmis()
    df = _hedef(pd.Timestamp("2026-11-08", tz="UTC"))
    k0 = karne_cliper_kosu_bazli(df, gecmis, LAT, LON)
    for run_at in df.run_at.unique()[:4]:
        g = gecmis.copy()
        g.loc[g.index >= run_at] *= 10.0                               # kosudan sonraki TUM gozlemler bozuk (gunduz dahil)
        k = karne_cliper_kosu_bazli(df, g, LAT, LON)
        sat = (df.run_at == run_at).values
        assert k0[sat].notna().sum() > 20
        np.testing.assert_allclose(k[sat].values, k0[sat].values, rtol=1e-12, equal_nan=True)   # o kosu icin birebir ayni
    # kosu ONCESI gozlemler degisirse referans degisir (ogrenme gercekten oradan)
    g2 = gecmis.copy()
    g2.loc[g2.index < df.run_at.min()] *= 1.5
    k2 = karne_cliper_kosu_bazli(df, g2, LAT, LON)
    assert not np.allclose(np.nan_to_num(k2.values), np.nan_to_num(k0.values))


def test_deterministik_gece_sayisindan_bagimsiz():
    # Ayni satir kumesi 10 ayri "gece" (farkli simdi) hesaplansa da deger ayni: cipa run_at, gecmis kesiti run_at sonrasini icerse de icermese de
    gecmis = _gecmis()
    df = _hedef(pd.Timestamp("2026-11-08", tz="UTC"), gun=3)
    k_tam = karne_cliper_kosu_bazli(df, gecmis, LAT, LON)
    son_hedef = df.ts_utc.max()
    k_kesik = karne_cliper_kosu_bazli(df, gecmis[gecmis.index <= son_hedef], LAT, LON)        # gece D+1 kesiti
    k_uzun = karne_cliper_kosu_bazli(df, gecmis[gecmis.index <= son_hedef + pd.Timedelta(days=9)], LAT, LON)   # gece D+10 kesiti
    np.testing.assert_allclose(k_kesik.values, k_tam.values, rtol=1e-12, equal_nan=True)
    np.testing.assert_allclose(k_uzun.values, k_tam.values, rtol=1e-12, equal_nan=True)
    # kesitin BASI da sonucu degistirmez: 400 gunden eski gozlemler bozulsa ayni (QA I-8)
    g_eski = gecmis.copy()
    g_eski.loc[g_eski.index < df.run_at.min() - pd.Timedelta(days=CLIPER_GECMIS_GUN)] *= 7.0
    k_eski = karne_cliper_kosu_bazli(df, g_eski, LAT, LON)
    np.testing.assert_allclose(k_eski.values, k_tam.values, rtol=1e-12, equal_nan=True)
    # 400 gun icindeki eski gozlemler bozulsa degisir (pencere gercekten 400 gun)
    g_ic = gecmis.copy()
    g_ic.loc[(g_ic.index < df.run_at.min() - pd.Timedelta(days=300)) & (g_ic.index >= df.run_at.min() - pd.Timedelta(days=CLIPER_GECMIS_GUN))] *= 7.0
    k_ic = karne_cliper_kosu_bazli(df, g_ic, LAT, LON)
    assert not np.allclose(np.nan_to_num(k_ic.values), np.nan_to_num(k_tam.values))


def test_eski_sizintili_kuraldan_farkli():
    # Eski blok iklimseli skorlanan pencereden aliyordu: hedef gunlerini 10x yapmak eski ciktiyi degistirirdi
    from pvquant.ext.tahmin import referans as ref
    gecmis = _gecmis()
    donem_bas = pd.Timestamp("2026-10-01", tz="UTC")
    df = _hedef(donem_bas, gun=25)
    pencere = gecmis[gecmis.index >= donem_bas]
    ikl_a = ref.iklimsel(pencere, pd.DatetimeIndex(df.ts_utc), min_gun=20)
    g1 = gecmis.copy()
    g1.loc[g1.index.isin(df.ts_utc)] *= 10.0
    ikl_b = ref.iklimsel(g1[g1.index >= donem_bas], pd.DatetimeIndex(df.ts_utc), min_gun=20)
    assert ikl_a.notna().any() and not np.allclose(ikl_a.dropna().values, ikl_b.dropna().values)   # eski kural sizdiriyordu
    # yeni kuralda ilk kosunun referansi bu bozmadan etkilenmez (hedefler kosudan sonra)
    ilk = (df.run_at == df.run_at.min()).values
    k0 = karne_cliper_kosu_bazli(df, gecmis, LAT, LON)
    k1 = karne_cliper_kosu_bazli(df, g1, LAT, LON)
    assert k0[ilk].notna().sum() > 20
    np.testing.assert_allclose(k1[ilk].values, k0[ilk].values, rtol=1e-12, equal_nan=True)


def test_yetersiz_gecmis_nan_ve_skor_none():
    kisa = _gecmis(bas="2026-10-25", gun=24)                       # tek yil, Kasim < 20 gun: ay x saat dolmaz (genc santral)
    df = _hedef(pd.Timestamp("2026-11-08", tz="UTC"))
    k = karne_cliper_kosu_bazli(df, kisa, LAT, LON)
    assert k.isna().all()
    df2 = df.assign(gun=df.ts_utc.dt.date, kova="0-24", power_kw=500.0, p50_kw=480.0, naif=400.0, cliper=k.values)
    r = kova_skorlari(df2, 1000.0, "t", "p")
    assert r and all(x["sc"] is None and x["cw"] is None for x in r)   # tire, uydurma yok


def test_bos_df_ve_sabit():
    bos = pd.DataFrame(columns=["ts_utc", "run_at"])
    assert karne_cliper_kosu_bazli(bos, _gecmis(gun=30), LAT, LON).empty
    assert karne_cliper(bos, _gecmis(gun=30), pd.Timestamp("2026-11-08", tz="UTC"), LAT, LON).empty
    assert CLIPER_GECMIS_GUN == 400   # bagimsiz motor gecmis_olcum_oku varsayilani ile ayni
