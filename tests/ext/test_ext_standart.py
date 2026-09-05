import numpy as np, pandas as pd, pytest
from pvquant.ext.standart import belirsizlik_butcesi as bb, iec61724, iec61853, kayip_agaci, kullanilabilirlik as ku, sfa_metrik


def _yil(seed=0):
    idx = pd.date_range("2025-01-01", "2025-12-31 23:00", freq="h", tz="UTC"); rng = np.random.default_rng(seed)
    g = np.clip(np.sin((idx.hour - 6) / 12 * np.pi), 0, None)
    poa = pd.Series(900 * g * rng.uniform(0.6, 1.0, len(idx)), index=idx)
    ta = pd.Series(20.0 + 5 * g, index=idx); wind = pd.Series(2.0, index=idx)
    return idx, poa, ta, wind


def test_iec_kpi_pr_ve_duzeltme():
    idx, poa, ta, wind = _yil()
    tc = iec61724.hucre_sicakligi_faiman(poa, ta, wind)
    e = 1000 * poa / 1000 * 0.85 * (1 - 0.0035 * (tc - 25))    # kWh/saat, 1000 kWp, PR_stc = 0,85
    k = iec61724.kpi(e, poa, 1000.0, t_cell=tc)
    assert len(k) == 12 and k.PR.between(0.75, 0.86).all()
    assert np.allclose(k.PR_stc, 0.85, atol=0.005)              # sıcaklık düzeltmesi PR_stc'yi tam geri verir
    assert (k.bayrak == "").all() and 0 < k.CF.mean() < 0.4
    y = iec61724.yillik_ozet(k); assert abs(y.PR - k.Y_f.sum() / k.Y_r.sum()) < 1e-9
    e2 = e.copy(); e2.iloc[:24 * 3] = np.nan                       # Ocak'ta 3 gün eksik → %90 < %95
    k2 = iec61724.kpi(e2, poa, 1000.0); assert k2.bayrak.iloc[0] != "" and k2.bayrak.iloc[1] == ""


def test_sfa_metrikleri():
    idx, poa, _, _ = _yil(); rng = np.random.default_rng(1)
    o = poa; f = poa * (1 + rng.normal(0, 0.1, len(idx))) + 10; ref = poa.shift(24).fillna(0)
    h = sfa_metrik.hepsi(o, f, 1000.0, ref)
    assert h.mbe > 0 and 0 < h.nrmse < 20 and 0 < h.skill < 1 and 0.9 < h.r < 1 and h.ksi >= 0 and h.over >= 0 and h.cpi > 0
    assert h.crmse <= h.rmse + 1e-9
    k = sfa_metrik.karne_satiri(o, f, 1000.0, ref); assert set(k) == {"nmae_pct", "nrmse_pct", "nmbe_pct", "skill", "cpi_pct"}
    assert sfa_metrik.ksi(o, o) == 0.0


def test_belirsizlik_butcesi():
    yillik = pd.Series([1700, 1650, 1720, 1680, 1600, 1750, 1690, 1710], index=range(2017, 2025))
    b = bb.butce_kur(1700, yillik, N_yil=10)
    t = b.tablo(); assert t.loc["P99", "1 yıl"] < t.loc["P90", "1 yıl"] < t.loc["P50", "1 yıl"] == 1700
    assert t.loc["P90", "10 yıl"] > t.loc["P90", "1 yıl"]
    assert abs(b.katki().sum() - 1) < 1e-9
    mc = bb.monte_carlo(1700, b.bilesenler, n=20000); assert abs(mc.P90 - b.p(90)) / 1700 < 0.02
    b2 = bb.butce_kur(1700, yillik, olcumle_kalibre=True); assert b2._s1 < b._s1


def test_kayip_agaci():
    idx, poa, ta, wind = _yil()
    import pvlib
    cs = pvlib.location.Location(37.87, 32.49, tz="UTC").get_clearsky(idx + pd.Timedelta(minutes=30)); cs.index = idx
    o, ghi, poa2 = kayip_agaci.oranlari_saatlikten(cs.ghi, cs.dni, cs.dhi, ta, wind, 37.87, 32.49, 25, 180)
    assert 0 <= o["iam"] < 0.08 and 0 < o["sicaklik"] < 0.15 and 0 <= o["isinim_seviyesi"] < 0.05 and poa2 > ghi * 0.9
    a = kayip_agaci.agac(ghi, poa2, 5000, 0.2, o, sebeke_kwh=None)
    assert a.sebeke_kwh < a.nominal_dc_kwh and len(a.selale) == len(kayip_agaci.SIRA) + 2
    zincir = a.tablo.iloc[1:]; assert np.allclose(zincir.giren.values[1:], zincir.cikan.values[:-1])
    a2 = kayip_agaci.agac(ghi, poa2, 5000, 0.2, o, sebeke_kwh=a.sebeke_kwh * 0.97)
    assert a2.tablo.iloc[-1].adim == "aciklanamayan" and abs(a2.tablo.iloc[-1].kayip_pct - 3) < 1e-6


def test_iec61853_matris_adr():
    M = iec61853.matris_uret(400.0, gamma_p=-0.0035, dusuk_isinim_k=0.02)
    assert np.isnan(M.loc[100.0, 75.0]) and abs(M.loc[1000.0, 25.0] - 400) < 1e-9
    adr = iec61853.matris_uydur(M, 400.0)
    eta = iec61853.verim(np.array([1000.0, 200.0, 0.0]), np.array([25.0, 25.0, 25.0]), adr)
    assert abs(eta[0] - 1) < 0.02 and 0.9 < eta[1] < 1.0 and eta[2] == 0
    assert abs(iec61853.interpolasyon(M, 1000, 25) - 400) < 1e-9 and iec61853.interpolasyon(M, 700, 40) < 280
    idx = pd.date_range("2025-06-01", periods=24 * 10, freq="h", tz="UTC")
    poa = pd.Series(900 * np.clip(np.sin((idx.hour - 6) / 12 * np.pi), 0, None), index=idx)
    d = iec61853.enerji_derecesi(poa, pd.Series(35.0, index=idx), adr); assert 0.85 < d["CSER"] < 1.0


def test_kullanilabilirlik():
    idx, poa, _, _ = _yil()
    b = pd.Timestamp("2025-06-10 06:00", tz="UTC")
    olaylar = [ku.Olay(b, b + pd.Timedelta(hours=12), "ariza", "INV1"), ku.Olay(b + pd.Timedelta(days=1), b + pd.Timedelta(days=1, hours=6), "sebeke"),
               ku.Olay(b + pd.Timedelta(days=5), b + pd.Timedelta(days=5, hours=3), "ariza", "INV2")]
    z = ku.zaman_tabanli(idx, poa, olaylar); assert 0.99 < z["A_t"] < 1.0 and z["saat_haric"] > 0
    bek = poa / 1000 * 1000; ger = bek.copy(); ger[(idx >= b) & (idx < b + pd.Timedelta(hours=12))] = 0
    e = ku.enerji_tabanli(ger, bek, olaylar); assert 0.99 < e["A_e"] < 1.0 and e["E_kayip_ariza_kwh"] > 0
    m = ku.mtbf_mttr(olaylar, idx[0], idx[-1]); assert m["ariza_sayisi"] == 2 and m["MTTR_saat"] == 7.5
    bb_ = ku.birim_bazli(idx, poa, olaylar, {"INV1": 500, "INV2": 500}); assert 0.99 < bb_.attrs["tesis_A_t"] < 1.0
    s = ku.sozlesme(0.975, 0.98, 1_500_000, 2.65); assert abs(s["acik_puan"] - 0.005) < 1e-12 and s["acik_tl"] > 0
