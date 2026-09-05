import numpy as np, pandas as pd, pytest
from pvquant.ext.kaynak import atif, belirsizlik, epias, harman, nowcast, tmy
from pvquant.ext.kaynak.atif import KAYNAKLAR
from pvquant.ext.kaynak.nwp_icon import ortalamadan_aralik
from pvquant.ext.kaynak.ortak import MeteoCerceve, acik_gok_ghi, biriktirilmisten_saatlik, kaba_adimi_saatlige_indir

LAT, LON = 37.87, 32.49


def _idx(n=48, bas="2026-06-10"):
    return pd.date_range(bas, periods=n, freq="h", tz="UTC")


def _cerceve(kt=0.8, n=48):
    idx = _idx(n); cs = acik_gok_ghi(idx, LAT, LON)
    return MeteoCerceve(pd.DataFrame({"ghi": cs * kt, "temp_air": 25.0, "wind_speed_10m": 2.0, "cloud_cover": 20.0}, index=idx), LAT, LON, KAYNAKLAR["ecmwf"])


def test_cerceve_ayristirir_ve_utc():
    c = _cerceve()
    assert {"dni", "dhi"} <= set(c.df.columns) and str(c.df.index.tz) == "UTC"
    gunduz = c.df[c.df.ghi > 50]
    assert (gunduz.dni >= 0).all() and (gunduz.dhi <= gunduz.ghi + 1e-6).all()


def test_biriktirilmis_ve_kaba_adim():
    idx = pd.date_range("2026-06-10", periods=5, freq="3h", tz="UTC")
    J = pd.Series(np.cumsum([0, 1.0e6, 3.0e6, 3.0e6, 1.0e6]), index=idx)
    W = biriktirilmisten_saatlik(J, 3)
    assert abs(W.iloc[2] - 3.0e6 / 10800) < 1e-6
    hedef = _idx(13)
    s = kaba_adimi_saatlige_indir(W, LAT, LON, hedef)
    assert (s >= 0).all() and s.notna().all()


def test_icon_ortalamadan_aralik():
    idx = pd.date_range("2026-06-10 06:00", periods=4, freq="h", tz="UTC")
    ort = pd.Series([0.0, 100.0, 150.0, 200.0], index=idx)   # koşu başından ortalama
    a = ortalamadan_aralik(ort)
    assert abs(a.iloc[2] - 200.0) < 1e-9 and abs(a.iloc[3] - 300.0) < 1e-9


def test_harman_esit_agirlik_ve_kantil():
    a, b, c = _cerceve(0.9), _cerceve(0.7), _cerceve(0.5)
    h = harman.harmanla({"e": a, "i": b, "g": c})
    assert abs(sum(h.agirliklar.values()) - 1) < 1e-9
    g = h.df[h.df.ghi > 50]
    assert ((g.ghi_p10 <= g.ghi + 1e-6) & (g.ghi <= g.ghi_p90 + 1e-6)).all()
    beklenen = (a.df.ghi + b.df.ghi + c.df.ghi) / 3
    assert np.allclose(g.ghi, beklenen.loc[g.index], rtol=0.02)


def test_harman_uyelerle_ampirik():
    a = _cerceve(0.8)
    rng = np.random.default_rng(0)
    a.uyeler = {n: pd.DataFrame({"ghi": a.df.ghi * rng.uniform(0.6, 1.0)}) for n in range(1, 21)}
    h = harman.harmanla({"e": a})
    assert h.uye_sayisi == 20 and (h.df.ghi_p10 <= h.df.ghi_p90 + 1e-9).all()


def test_agirlik_ters_mse():
    idx = _idx(72); ger = pd.Series(0.7, index=idx)
    w = harman.agirlik_hesapla({"iyi": pd.Series(0.71, index=idx), "kotu": pd.Series(0.4, index=idx)}, ger)
    assert w["iyi"] > 0.9 > w["kotu"]


def test_nowcast_rampa_yaklasir():
    nwp = _cerceve(0.8); idx = nwp.df.index
    olcum = (acik_gok_ghi(idx, LAT, LON) * 0.5).loc[: idx[9]]
    h = nowcast.rampali_harman(nwp, olcum, tau_saat=2.0)
    ilk = h.df.ghi.loc[idx[10]]; nwp_ilk = nwp.df.ghi.loc[idx[10]]
    assert ilk < nwp_ilk                                  # ilk saat ölçüme yakın
    assert abs(h.df.ghi.loc[idx[20]] - nwp.df.ghi.loc[idx[20]]) < 1e-6   # 6 s sonrası NWP
    assert h.df.temp_air.equals(nwp.df.temp_air)


def test_sapma_duzelt_yon():
    idx = pd.date_range("2026-06-01", periods=24 * 10, freq="h", tz="UTC"); cs = acik_gok_ghi(idx, LAT, LON)
    ger = cs * 0.8; nwp_gec = cs * 0.6
    duz = nowcast.sapma_duzelt(nwp_gec, nwp_gec, ger, LAT, LON, gun=7)
    g = cs > 100
    assert (duz[g] > nwp_gec[g]).all()


def test_belirsizlik_butce():
    y = pd.Series([1800, 1850, 1790, 1900, 1820, 1780, 1860, 1810], index=range(2015, 2023))
    b = belirsizlik.butce(y, sigma_kaynak=0.04, sigma_model=0.03, N_yil=10)
    assert b.olasiliklar[99] < b.olasiliklar[90] < b.p50
    assert b.olasiliklar_N_yil[90] > b.olasiliklar[90]


def test_tmy_secer():
    idx = pd.date_range("2010-01-01", "2019-12-31 23:00", freq="h", tz="UTC")
    rng = np.random.default_rng(2); cs = acik_gok_ghi(idx, LAT, LON)
    df = pd.DataFrame({"ghi": cs * rng.uniform(0.4, 0.95, len(idx)), "temp_air": 15 + 10 * np.sin((idx.dayofyear - 100) / 365 * 2 * np.pi) + rng.normal(0, 2, len(idx)),
                       "wind_speed_10m": rng.gamma(2, 1.5, len(idx))}, index=idx)
    t, secim = tmy.tmy_uret(df, min_yil=8)
    assert len(secim) == 12 and 8600 <= len(t) <= 8784
    yil, toplam, _ = tmy.pxx_yili(df, 90)
    assert 2010 <= yil <= 2019 and toplam > 0


def test_dengesizlik_maliyeti_isareti():
    idx = pd.date_range("2025-07-01", periods=24, freq="h", tz="Europe/Istanbul")
    kgup = pd.Series(5.0, index=idx); ger = kgup.copy(); ger.iloc[10] = 4.0; ger.iloc[12] = 6.0
    ptf = pd.Series(2600.0, index=idx); smf = pd.Series(2500.0, index=idx)
    m = epias.dengesizlik_maliyeti(kgup, ger, ptf, smf)
    assert m.maliyet_tl.iloc[10] == pytest.approx(2600 * 1.03 - 2600)   # negatif: max(PTF,SMF)=2600 ×1,03 − PTF
    assert m.maliyet_tl.iloc[12] == pytest.approx(2600 - 2500 * 0.97)   # pozitif: PTF − min ×0,97
    assert m.maliyet_tl.iloc[0] == 0


def test_atif_kunye_ve_uyumluluk():
    k = atif.kunye(["ecmwf", "icon", "gfs", "cams", "pvgis"])
    assert "CC BY 4.0" in k and "işlenmiştir" in k and "ECMWF" in k
    assert atif.uyumluluk_denetimi(["ecmwf", "icon"]) == []
    assert atif.uyumluluk_denetimi(["open_meteo"])
