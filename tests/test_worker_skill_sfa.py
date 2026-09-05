"""v2.247 — worker kova_skorlari SAF fonksiyonu: eski tanimlar (WMAPE/rmse/naif/skill)
birebir korunur, SFA kolonlari (nmae/nrmse/nmbe) yanina gelir. DB yok."""
import numpy as np
import pandas as pd

from apps.worker.main import kova_skorlari

CAP = 1000.0


def _df():
    ts = pd.date_range("2026-07-01", periods=48, freq="h", tz="UTC")
    g = np.clip(np.sin((ts.hour - 6) / 12 * np.pi), 0, None)
    gercek = 800 * g
    p50 = gercek + 40 * (g > 0)                       # gunduz sabit +40 kW sapma
    naif = gercek * 1.1
    return pd.DataFrame({"ts_utc": ts, "gun": ts.date, "kova": "0-24",
                         "power_kw": gercek, "p50_kw": p50, "naif": naif})[gercek > 0.02 * CAP]


def test_eski_tanimlar_ve_sfa_kolonlari():
    df = _df()
    satirlar = kova_skorlari(df, CAP, "t", "p")
    assert len(satirlar) == 2 and set(satirlar[0]) == {"t", "p", "g", "k", "m", "r", "s", "n", "na", "nr", "nb"}
    r = satirlar[0]; g = df[df.gun == r["g"]]
    assert r["m"] == float(abs(g.p50_kw - g.power_kw).sum() / g.power_kw.sum() * 100)   # WMAPE aynen
    assert abs(r["r"] - 40.0) < 1e-9                                                       # sabit sapma → rmse 40 kW
    assert abs(r["na"] - 4.0) < 1e-9 and abs(r["nr"] - 4.0) < 1e-9 and abs(r["nb"] - 4.0) < 1e-9   # 40/1000*100
    assert r["n"] > 0 and r["s"] is not None


def test_kapasite_yoksa_normalize_yok():
    r = kova_skorlari(_df(), 0.0, "t", "p")[0]
    assert r["na"] is None and r["nr"] is None and r["nb"] is None and r["m"] > 0
