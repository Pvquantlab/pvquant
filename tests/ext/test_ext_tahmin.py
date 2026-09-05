import numpy as np, pandas as pd, pytest
from pvquant.ext.tahmin import (alt_saatlik, backtest, degradasyon, dogrulama, ensemble_belirsizlik as eb, fizik_terimler,
                            kirlenme, kisitlama, konformal, portfoy, referans)

LAT, LON, KAP = 37.87, 32.49, 1000.0


def _gunes(idx):
    return pd.Series(np.clip(np.sin((idx.hour - 6) / 12 * np.pi), 0, None), index=idx)


def _veri(n_gun=40, seed=0, sigma=0.25):
    idx = pd.date_range("2026-05-01", periods=24 * n_gun, freq="h", tz="UTC")
    g = _gunes(idx); rng = np.random.default_rng(seed)
    p50 = KAP * 0.7 * g
    gercek = (p50 * (1 + rng.normal(0, sigma, len(idx)))).clip(lower=0) * (g > 0)
    return idx, p50, gercek


# --- dogrulama ---
def test_deterministik_ve_skill():
    idx, p50, gercek = _veri()
    ref = p50 * 1.3
    s = dogrulama.deterministik(gercek, p50, KAP, referans=ref)
    assert 0 < s.nrmse < 0.5 and s.skill > 0 and 0 < s.wmape < 1


def test_pinball_crps_picp():
    idx, p50, gercek = _veri()
    q = pd.DataFrame({"p10": p50 * 0.6, "p50": p50, "p90": p50 * 1.4})
    m = dogrulama.gunduz_maskesi(gercek, p50, KAP)
    assert dogrulama.pinball(gercek[m], q.p50[m], 0.5) > 0
    assert dogrulama.crps_kantillerden(gercek[m], q[m]) > 0
    assert 0.5 < dogrulama.picp(gercek[m], q.p10[m], q.p90[m]) <= 1.0
    r = dogrulama.reliability(gercek[m], q[m]); assert list(r.tau) == [0.1, 0.5, 0.9]
    pit = dogrulama.pit_histogram(gercek[m], q[m]); assert abs(pit.sum() - 1) < 1e-9
    uy = pd.DataFrame({i: p50 * (0.7 + 0.6 * i / 20) for i in range(21)})
    assert dogrulama.crps_ensemble(gercek[m], uy[m]) > 0


# --- konformal ---
def test_cqr_kapsamayi_duzeltir():
    idx, p50, gercek = _veri(n_gun=80)
    m = dogrulama.gunduz_maskesi(gercek, p50, KAP)
    alt, ust = p50 * 0.95, p50 * 1.05          # bilerek dar
    kal, test = idx[: 24 * 40], idx[24 * 40:]
    once = dogrulama.picp(gercek[test][m[test]], alt[test], ust[test])
    c = konformal.CQR(alpha=0.2).kalibre_et(gercek[kal][m[kal]], alt[kal], ust[kal])
    a, u = c.uygula(alt[test], ust[test], tavan=KAP)
    sonra = dogrulama.picp(gercek[test][m[test]], a, u)
    assert once < 0.5 and 0.7 <= sonra <= 0.92


def test_aci_yakinsar():
    rng = np.random.default_rng(3); a = konformal.ACI(alpha=0.2, gamma=0.02)
    kapsama = []
    for t in range(2000):
        y = rng.normal(0, 1); lo, hi = -0.3, 0.3
        q = a.q_hat(); kapsama.append(lo - q <= y <= hi + q)
        a.adim(y, lo, hi)
    assert 0.72 <= np.mean(kapsama[-1000:]) <= 0.88


def test_kantil_regresyon_tau():
    rng = np.random.default_rng(0); X = rng.uniform(0, 1, (2000, 1)); y = 2 * X[:, 0] + rng.normal(0, 0.3, 2000)
    q9 = konformal.KantilRegresyon(0.9).fit(X, y).predict(X)
    assert 0.85 <= np.mean(y <= q9) <= 0.95


# --- ensemble ---
def test_emos_ve_spread_skill():
    idx, p50, gercek = _veri(n_gun=60)
    rng = np.random.default_rng(1)
    uy = pd.DataFrame({i: p50 * (1 + rng.normal(0, 0.1, len(idx))) for i in range(20)})   # underdispersed (gerçek σ=0,25)
    ufuk = pd.Series(np.tile(np.arange(24), 60), index=idx)
    m = dogrulama.gunduz_maskesi(gercek, p50, KAP)
    ss = eb.yayilim_beceri(gercek[m], uy[m], ufuk[m]); assert (ss["c"].dropna() > 1.2).mean() > 0.7
    kat = eb.emos_lite(gercek[m], uy[m], ufuk[m]); q = eb.emos_uygula(uy[m], ufuk[m], kat, tavan=KAP)
    assert 0.7 <= dogrulama.picp(gercek[m], q.p10, q.p90) <= 0.92
    sig = eb.ufuk_sigma((p50 - gercek)[m], ufuk[m]); assert sig.is_monotonic_increasing


# --- kisitlama ---
def test_clipping_ve_curtailment():
    idx = pd.date_range("2026-06-01", periods=24 * 5, freq="h", tz="UTC"); g = _gunes(idx)
    beklenen = 1000 * g; gercek = beklenen.clip(upper=800)          # 800 kW inverter tavanı
    cl = kisitlama.clipping_maskesi(gercek, tavan_kw=800); assert cl.sum() >= 5 and cl[gercek < 700].sum() == 0
    g2 = beklenen.copy(); g2.iloc[10:15] = 300.0                      # şebeke kısıntı platosu
    cu = kisitlama.curtailment_maskesi(g2, beklenen, kapasite=1000); assert cu.iloc[10:15].all() and cu.sum() <= 7
    mk = kisitlama.kalibrasyon_maskesi(g2, beklenen, tavan_kw=1000)
    sen = kisitlama.kisitsiz_senaryo(g2, beklenen, mk); assert sen.kayip.sum() > 0 and (sen.kisitsiz >= g2 - 1e-9).all()


# --- backtest ---
def test_rolling_origin_ve_kayma():
    idx, p50, gercek = _veri(n_gun=120)
    X = pd.DataFrame({"p50": p50, "saat": idx.hour})
    def fp(Xtr, ytr, Xte): return Xte["p50"].values * (ytr.sum() / max(Xtr["p50"].sum(), 1e-9))
    katlar = backtest.rolling_origin(X, gercek, fp, ilk_egitim_gun=60, test_gun=7, adim_gun=14)
    assert len(katlar) >= 3 and all(k.test_baslangic > k.egitim_bitis for k in katlar)
    kd = backtest.kayma_denetimi(X.iloc[:1000], X.iloc[1000:] * 1.5); assert (kd.loc[kd.ozellik == "p50", "uyari"] == "KAYMA").all()
    assert backtest.kaynak_tutarlilik({"ghi": "olcum"}, {"ghi": "nwp"})


# --- referans ---
def test_referans_optimal_w():
    idx, p50, gercek = _veri(n_gun=60, sigma=0.1)
    cs = fizik_terimler.acik_gok(idx, LAT, LON)["ghi"]
    pers = referans.akilli_persistans(gercek, cs, cs); ik = referans.iklimsel(gercek, idx)
    w = referans.optimal_agirlik(gercek.iloc[48:], pers.iloc[48:], ik.iloc[48:]); assert 0 <= w <= 1
    ref, W = referans.optimal_birlesim(gercek.iloc[48:], pers.iloc[48:], ik.iloc[48:], pers, ik); assert (ref >= 0).all()


# --- fizik_terimler ---
def test_iam_spektral_etkin():
    idx = pd.date_range("2026-06-10", periods=24, freq="h", tz="UTC")
    aoi = pd.Series(np.linspace(0, 89, 24), index=idx)
    iam = fizik_terimler.iam_katsayilari(aoi, "physical"); assert iam.iloc[0] > 0.99 and iam.iloc[-1] < 0.5
    M = fizik_terimler.spektral_duzeltme(idx, LAT, LON, pd.Series(25.0, index=idx), pd.Series(50.0, index=idx))
    assert (M.between(0.8, 1.2)).all()
    ge = fizik_terimler.etkin_isinim(pd.Series(500.0, index=idx), pd.Series(100.0, index=idx), pd.Series(10.0, index=idx), aoi, 25, M)
    assert (ge > 0).all() and (ge <= 610 * 1.2).all()


# --- kirlenme ---
def test_kimber_ve_carpan():
    idx = pd.date_range("2026-07-01", periods=24 * 30, freq="h", tz="UTC")
    yagis = pd.Series(0.0, index=idx); yagis.iloc[24 * 20] = 10.0
    sr = kirlenme.soiling_kimber(yagis, gunluk_kayip=0.002)
    assert sr.iloc[24 * 19] < 0.98 and sr.iloc[24 * 21] > sr.iloc[24 * 19]
    c = kirlenme.kirlenme_carpani(sr, None, idx); assert (c <= 1).all() and (c > 0.9).all()


# --- degradasyon ---
def test_pr_ve_yoy():
    idx = pd.date_range("2024-01-01", periods=24 * 800, freq="h", tz="UTC"); g = _gunes(idx)
    poa = 900 * g; gun = np.arange(len(idx)) / 24 / 365.25
    e = pd.Series(0.8 * 1000.0 * (poa / 1000.0) * (1 - 0.01 * gun), index=idx)   # kWh/saat: PR 0,8, p0=1000 kWp, −1 %/yıl
    p = degradasyon.pr(e, poa, 1000.0); assert p.PR.dropna().between(0.75, 0.85).all()
    v = degradasyon.normalize_verim(e, poa); r = degradasyon.yoy_degradasyon(v, bootstrap=50)
    assert -1.5 < r["rd_yuzde_yil"] < -0.5


# --- alt_saatlik ---
def test_15dk_enerji_korur():
    idx = pd.date_range("2026-06-10", periods=48, freq="h", tz="UTC")
    cs = fizik_terimler.acik_gok(idx, LAT, LON)["ghi"]; saatlik = cs * 0.7
    s15 = alt_saatlik.saatlikten_15dk(saatlik, LAT, LON, degiskenlik=0.2)
    geri = alt_saatlik.saatlige_topla(s15).reindex(idx)
    g = saatlik > 50
    assert np.allclose(geri[g], saatlik[g], rtol=0.02) and (s15 >= 0).all()
    uz = alt_saatlik.uzlastirma_15dk(s15 / 100, (s15 / 100) * 0.9, pd.Series(2600.0, index=idx), pd.Series(2500.0, index=idx))
    assert uz.pozitif_gelir.sum() > 0


# --- portfoy ---
def test_mint_tutarli_ve_iyilestirir():
    taban = ["S1", "S2", "S3"]; S, dug = portfoy.toplama_matrisi({"Toplam": taban, "A": ["S1", "S2"], "B": ["S3"]}, taban)
    rng = np.random.default_rng(0); idx = pd.date_range("2026-06-01", periods=24 * 10, freq="h", tz="UTC")
    gt = pd.DataFrame({s: 10 * (i + 1) * _gunes(idx).values for i, s in enumerate(taban)}, index=idx)
    gercek = pd.DataFrame(gt.values @ S.T, index=idx, columns=dug)
    tahmin = gercek * (1 + rng.normal(0, 0.1, gercek.shape))
    hat = pd.DataFrame(rng.normal(0, 1, (300, len(dug))) * gercek.max().values * 0.1, columns=dug)
    for y in ("ols", "wls", "shrink"):
        uz = portfoy.mint(tahmin, S, dug, hat, y); assert portfoy.tutarlilik_kontrol(uz, S, dug)
    bu = portfoy.bottom_up(tahmin[taban], S, dug); assert portfoy.tutarlilik_kontrol(bu, S, dug)
    td = portfoy.top_down_oran(tahmin["Toplam"], gt, S, dug); assert portfoy.tutarlilik_kontrol(td, S, dug)
    assert np.sqrt(((uz - gercek) ** 2).mean().mean()) <= np.sqrt(((tahmin - gercek) ** 2).mean().mean()) * 1.05
