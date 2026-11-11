"""v2.589 (Faz 3 F3-B) — portföy belirsizliği (saf): naif kantil toplamının bandı şişirdiğinin kanıtı; ρ = 0,9 / 0,2 / −0,5 ile kapsama sınavı
(kalibre marjinaller → portföy PICP ≈ %80); 1 / 5 / 20 santral; farklı kapasiteler; eksik tahmin/saat; günlük ampirik bant ve dönem bootstrap;
kapsama sınavı durumları; bölge göstergesi; NREL 3 santral (gerçek veri, 30 gün) ile korelasyon."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pvquant.ext.tahmin import portfoy_belirsizlik as pb

TZ = "Europe/Istanbul"
Z = 1.2816


def _profil(kap: float, idx: pd.DatetimeIndex) -> np.ndarray:
    h = idx.tz_convert(TZ).hour.values
    return 0.85 * kap * np.clip(np.sin((h - 6) / 12 * np.pi), 0, None) * ((h >= 6) & (h <= 18))   # tepe %85: P90 kapasiteye kırpılmasın (kalibre marjinal)


def _sentetik(kaps: list[float], rho: float, gun: int = 60, seed: int = 1, sigma_oran: float = 0.12):
    """Kalibre marjinaller: σᵢ(h) = oran × p50ᵢ(h); P10/P90 = p50 ∓ Z·σ; gerçek y = p50 − e, e ~ N(0, Σ) (eşit korelasyon ρ)."""
    rng = np.random.default_rng(seed)
    n = len(kaps)
    idx = pd.date_range(pd.Timestamp("2026-06-01", tz=TZ), periods=gun * 24, freq="h").tz_convert("UTC")
    C = np.full((n, n), rho); np.fill_diagonal(C, 1.0)
    L = np.linalg.cholesky(C)
    z = rng.standard_normal((len(idx), n)) @ L.T
    tah, y, art = {}, {}, {}
    for i, kap in enumerate(kaps):
        p50 = _profil(kap, idx); sig = sigma_oran * p50
        e = z[:, i] * sig
        df = pd.DataFrame({"p50": p50, "p10": np.clip(p50 - Z * sig, 0, None), "p90": np.minimum(p50 + Z * sig, kap)}, index=idx)
        tah[f"S{i}"] = df; y[f"S{i}"] = pd.Series(p50 - e, index=idx)
        gunduz = p50 > 0.02 * kap
        art[f"S{i}"] = pd.Series(np.where(gunduz, e, np.nan), index=idx)
    return idx, tah, y, pd.DataFrame(art)


def _picp(saatlik: pd.DataFrame, y_top: pd.Series, lo: str, hi: str, kap: float) -> float:
    d = pd.DataFrame({"y": y_top, "p50": saatlik["p50"], "lo": saatlik[lo], "hi": saatlik[hi]}).dropna()
    d = d[(d["y"] > 0.02 * kap) | (d["p50"] > 0.02 * kap)]
    return float(((d["y"] >= d["lo"]) & (d["y"] <= d["hi"])).mean() * 100)


@pytest.mark.parametrize("rho, kaps", [(0.9, [1000, 800, 1200, 600, 900]), (0.2, [1000, 800, 1200, 600, 900]), (-0.5, [1000, 1000])])
def test_kapsama_kalibre_marjinallerle_rho_yontemi_hedefe_yakin_naif_sisirir(rho, kaps):
    idx, tah, y, art = _sentetik(kaps, rho, gun=60, seed=int(abs(rho) * 10) + 3)
    kap = float(sum(kaps))
    egitim = art[idx < idx[30 * 24]]; sinav = idx[idx >= idx[30 * 24]]
    ko = pb.korelasyon(egitim)
    assert ko["durum"] == "yeterli" and ko["n_gun"] == 30
    # ρ tahmini gerçek ρ'ya yakın (büzülme ile)
    off = ko["rho"].values[~np.eye(len(kaps), dtype=bool)]
    assert abs(off.mean() - rho) < 0.12
    h = pb.hizala({a: d.loc[sinav] for a, d in tah.items()})
    s = pb.saatlik_bant(h, ko["rho"], {a: k for a, k in zip(tah, kaps, strict=True)})
    y_top = sum(y[a].loc[sinav] for a in tah)
    picp_r = _picp(s, y_top, "p10", "p90", kap); picp_naif = _picp(s, y_top, "p10_naif", "p90_naif", kap); picp_bag = _picp(s, y_top, "p10_bagimsiz", "p90_bagimsiz", kap)
    assert 72 <= picp_r <= 88, (rho, picp_r)                      # ρ yöntemi hedefe (%80) yakın
    assert picp_naif >= picp_r - 0.5                                # naif asla daha dar değil
    if rho == 0.2:
        assert picp_naif > 90 and picp_bag < picp_r                 # naif şişirir, bağımsız daraltır
    if rho == -0.5:
        assert (s["sigma_alt"] < s["p50"] - s["p10_bagimsiz"] + 1e-9).loc[s["p50"] > 0].mean() > 0.95   # negatif korelasyon: bağımsızdan da dar
    if rho == 0.9:
        assert abs(picp_naif - picp_r) < 6                          # güçlü korelasyonda naif ≈ ρ yöntemi
    # bant sırası ve kapasite tavanı
    assert (s["p10"] <= s["p50"] + 1e-9).all() and (s["p50"] <= s["p90"] + 1e-9).all() and (s["p90"] <= kap + 1e-9).all() and (s["p10"] >= 0).all()
    assert (s["p10_bagimsiz"] >= s["p10_naif"] - 1e-9).all() and (s["p90_bagimsiz"] <= s["p90_naif"] + 1e-9).all()   # naif en geniş sınır


def test_tek_santral_bant_santralin_bandi_ve_katki_toplami_yirmi_santral():
    idx, tah, y, art = _sentetik([750.0], 0.0, gun=20)
    h = pb.hizala(tah); s = pb.saatlik_bant(h, None, {"S0": 750.0})
    assert np.allclose(s["p10"], tah["S0"]["p10"]) and np.allclose(s["p90"], tah["S0"]["p90"]) and np.allclose(s["p50"], tah["S0"]["p50"])
    ko = pb.korelasyon(art); assert ko["durum"] == "tek_santral"
    kaps = [float(100 + 97 * i) for i in range(20)]
    idx, tah, y, art = _sentetik(kaps, 0.4, gun=30, seed=7)
    ko = pb.korelasyon(art); h = pb.hizala(tah); s = pb.saatlik_bant(h, ko["rho"], dict(zip(tah, kaps, strict=True)))
    assert ko["rho"].shape == (20, 20) and np.allclose(np.diag(ko["rho"].values), 1.0)
    katki = s[[c for c in s.columns if c.endswith("__p50")]].sum(axis=1)
    assert np.allclose(katki, s["p50"]) and (s["p90"] <= sum(kaps) + 1e-9).all() and not s["eksik"].any()
    o = pb.portfoy_tahmini(tah, dict(zip(tah, kaps, strict=True)), art, TZ, koordinatlar={a: (37.0 + i * 0.01, 32.0) for i, a in enumerate(tah)})
    assert o["belirsizlik"]["durum"] == "dogrulanmadi" and o["bolge"]["bolge_sayisi"] == 1 and o["kapasite_kwp"] == sum(kaps) and o["gunluk_meta"]["durum"] == "ampirik"
    assert (o["gunluk"]["p10_mwh"] <= o["gunluk"]["p50_mwh"]).all() and (o["gunluk"]["p90_mwh"] >= o["gunluk"]["p50_mwh"]).all() and len(o["gunluk"]) == 30


def test_eksik_tahmin_ve_saat_sifir_sayilmaz_ve_yetersiz_veri():
    idx, tah, y, art = _sentetik([1000, 500, 800], 0.3, gun=10)
    tah["S1"] = tah["S1"].iloc[:-24]            # son gün eksik
    tah["S2"].loc[tah["S2"].index[30], "p10"] = np.nan   # bir saat bant yok
    tah["S3"] = None                               # tahmin yok
    h = pb.hizala(tah)
    assert h["tahmin_yok"] == ["S3"] and len(h["idx"]) == 9 * 24 and h["eksik_saat"] == {"S0": 24, "S1": 0, "S2": 24}
    ko = pb.korelasyon(art.iloc[: 5 * 24])      # 5 gün < 14 → yetersiz
    assert ko["durum"] == "yetersiz_veri" and (ko["rho"].values == 1.0).all()
    s = pb.saatlik_bant(h, ko["rho"], {"S0": 1000, "S1": 500, "S2": 800})
    assert bool(s["eksik"].iloc[30]) and np.isnan(s["p10"].iloc[30]) and not np.isnan(s["p50"].iloc[30]) and s["eksik"].sum() == 1
    assert np.allclose(s["p10"].dropna(), s["p10_naif"].dropna())   # ρ=1 → naif ile aynı
    o = pb.portfoy_tahmini(tah, {"S0": 1000, "S1": 500, "S2": 800}, art.iloc[: 5 * 24], TZ)
    assert o["belirsizlik"]["durum"] == "yetersiz_veri" and o["gunluk_meta"]["durum"] == "yetersiz_veri" and o["hizalama"]["tahmin_yok"] == ["S3"]
    assert pb.korelasyon(None)["durum"] == "yetersiz_veri" and pb.hizala({"a": None})["santral"] == []


def test_gunluk_ampirik_ve_donem_bootstrap_ve_kapsama_sinavi():
    idx, tah, y, art = _sentetik([1000, 800], 0.5, gun=45, seed=11)
    ga = pb.gunluk_artiklar(art, TZ)
    assert len(ga) == 45 and abs(ga.mean()) < ga.std()
    h = pb.hizala(tah); s = pb.saatlik_bant(h, pb.korelasyon(art)["rho"], {"S0": 1000, "S1": 800})
    g, meta = pb.gunluk(s, TZ, ga)
    assert meta["durum"] == "ampirik" and meta["n_gun"] == 45 and (g["p10_mwh"] < g["p50_mwh"]).all() and (g["p90_mwh"] > g["p50_mwh"]).all()
    assert (g["p10_mwh"] >= g["p10_naif_mwh"] - 1e-9).all() and (g["p90_mwh"] <= g["p90_naif_mwh"] + 1e-9).all()   # günlük naif toplam en geniş
    g2, meta2 = pb.gunluk(s, TZ, ga.iloc[:5])
    assert meta2["durum"] == "yetersiz_veri" and np.allclose(g2["p10_mwh"], g2["p10_naif_mwh"])
    b7 = pb.donem_bandi(ga, 7); b30 = pb.donem_bandi(ga, 30)
    assert b7 and b30 and b7["q10_kwh"] < 0 < b7["q90_kwh"] and (b30["q90_kwh"] - b30["q10_kwh"]) > (b7["q90_kwh"] - b7["q10_kwh"]) and pb.donem_bandi(ga.iloc[:3], 7) is None
    # kapsama sınavı: 45 gün ≥ 30 → doğrulandı (~%80); 10 gün → yetersiz; kaydırılmış bant → doğrulanmadı
    e = pd.DataFrame({"y": y["S0"] + y["S1"], "p50": s["p50"], "p10": s["p10"], "p90": s["p90"]})
    k = pb.kapsama_sinavi(e, 1800.0, tz=TZ)
    assert k["durum"] == "dogrulandi" and 72 <= k["picp80"] <= 88 and k["n_gun"] == 45 and k["winkler_kw"] > 0 and k["durum_ad"] == "Doğrulandı"
    assert pb.kapsama_sinavi(e.iloc[: 10 * 24], 1800.0, tz=TZ)["durum"] == "yetersiz_veri"
    e2 = e.assign(p10=e["p50"] * 0.999, p90=e["p50"] * 1.001)
    assert pb.kapsama_sinavi(e2, 1800.0, tz=TZ)["durum"] == "dogrulanmadi" and pb.kapsama_sinavi(pd.DataFrame(), 1.0)["durum"] == "yetersiz_veri"


def test_bolge_gostergesi():
    b = pb.bolge_gostergesi({"A": (37.0, 32.0), "B": (37.2, 32.1), "C": (39.9, 32.8)}, esik_km=50)
    assert b["bolge_sayisi"] == 2 and ["A", "B"] in b["bolgeler"] and [c for c in b["ciftler"] if c["a"] == "A" and c["b"] == "C"][0]["km"] > 300


KOK = Path(__file__).parent / "fixtures" / "nrel"
NREL = ("az_31.85_-110.85_UPV_100MW", "ca_32.65_-115.15_UPV_75MW", "ny_41.25_-73.55_UPV_38MW")


def _nrel(klasor: str, dosya: str) -> pd.Series:
    df = pd.read_csv(KOK / klasor / dosya)
    t = pd.DatetimeIndex(pd.to_datetime(df["LocalTime"], format="%m/%d/%y %H:%M")).tz_localize("UTC")   # yerel saat; korelasyon için ortak eksen yeterli
    return pd.Series(df["Power(MW)"].values, index=t).resample("h").mean()


def test_nrel_uc_santral_korelasyon_ve_bant():
    art, tah, kaps = {}, {}, {}
    for k in NREL:
        a = _nrel(k, "Actual_5_Min_2006-06.csv"); f = _nrel(k, "DA_60_Min_2006-06.csv")
        kap = float(k.split("_")[-1].rstrip("MW")); kaps[k] = kap
        idx = a.index.intersection(f.index)
        gunduz = (a.loc[idx] > 0.02 * kap) | (f.loc[idx] > 0.02 * kap)
        art[k] = (f.loc[idx] - a.loc[idx]).where(gunduz)
        sig = 0.2 * f.loc[idx]
        tah[k] = pd.DataFrame({"p50": f.loc[idx], "p10": (f.loc[idx] - Z * sig).clip(lower=0), "p90": np.minimum(f.loc[idx] + Z * sig, kap)})
    A = pd.DataFrame(art)
    ko = pb.korelasyon(A)
    assert ko["durum"] == "yeterli" and ko["n_gun"] >= 14 and (ko["rho"].abs().values <= 1.0).all()
    o = pb.portfoy_tahmini(tah, kaps, A, "UTC", koordinatlar={NREL[0]: (31.85, -110.85), NREL[1]: (32.65, -115.15), NREL[2]: (41.25, -73.55)})
    assert o["bolge"]["bolge_sayisi"] == 3 and o["kapasite_kwp"] == 213.0 and o["gunluk_meta"]["durum"] == "ampirik"
    s = o["saatlik"]
    assert (s["p90"] <= 213.0 + 1e-9).all() and (s["p10_naif"] <= s["p10"] + 1e-9).all() and (s["p90"] <= s["p90_naif"] + 1e-9).all()
