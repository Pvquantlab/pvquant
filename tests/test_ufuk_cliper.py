"""v2.279 — ufuk σ katmanı (SAF) + CLIPER referansı kova skorunda."""
import numpy as np
import pandas as pd

from pvquant.services import ufuk_service as uf


def test_sigma_hesapla_ve_uygula():
    rng = np.random.default_rng(0)
    run_at = pd.Timestamp("2026-08-01", tz="UTC")
    rows = []
    for d in range(60):
        ra = run_at + pd.Timedelta(days=d)
        for h in range(0, 240, 3):
            ts = ra + pd.Timedelta(hours=h)
            if 6 <= ts.hour <= 16:
                sig = 50 + 0.8 * h                                   # hata ufukla büyür
                rows.append({"ts_utc": ts, "run_at": ra, "p50_kw": 2000.0, "power_kw": 2000.0 + rng.normal(0, sig)})
    df = pd.DataFrame(rows)
    a = uf.sigma_hesapla_df(df, 4000.0)
    assert a is not None and a["kova_saat"] == 24 and len(a["sigma_kw"]) >= 8
    s = [a["sigma_kw"][k] for k in sorted(a["sigma_kw"], key=int)]
    assert all(s[i] <= s[i + 1] + 1e-9 for i in range(len(s) - 1)) and s[-1] > s[0] * 2     # monoton, büyüyen
    assert uf.sigma_hesapla_df(df.iloc[:20], 4000.0) is None
    # uygulama: dar bant genişler, geniş bant dokunulmaz, gece dokunulmaz
    ix = pd.date_range("2026-10-01", periods=72, freq="h", tz="UTC")
    p50 = pd.Series(np.where((ix.hour >= 6) & (ix.hour <= 16), 2000.0, 0.0), index=ix)
    h = pd.DataFrame({"p50_kw": p50, "p10_kw": p50 - 20, "p90_kw": p50 + 20, "physics_kw": p50}).clip(lower=0)
    h.loc[ix[30], ["p10_kw", "p90_kw"]] = [500.0, 3500.0]               # zaten geniş saat
    u = uf.uygula_df(h, a, ix[0], 3600.0)
    g = ix[10]; assert u.loc[g, "p90_kw"] - u.loc[g, "p10_kw"] > 2 * 1.2816 * 50 * 0.9
    assert u.loc[ix[30], "p10_kw"] == 500.0 and u.loc[ix[30], "p90_kw"] == 3500.0
    assert u.loc[ix[0], "p10_kw"] == 0.0 and u.loc[ix[0], "p90_kw"] == 20.0     # gece: dokunulmaz (ham 20 kalır)
    assert u["p90_kw"].max() <= 3600.0 and (u["p10_kw"] >= 0).all()
    assert uf.uygula_df(h, None, ix[0], 3600.0).equals(h)


def test_kova_skorlari_cliper():
    from apps.worker.main import kova_skorlari
    ix = pd.date_range("2026-08-01 06:00", periods=10, freq="h", tz="UTC")
    df = pd.DataFrame({"gun": [ix[0].date()] * 10, "kova": ["0-24"] * 10, "power_kw": 1000.0, "p50_kw": 950.0, "naif": 800.0, "cliper": 900.0}, index=ix)
    r = kova_skorlari(df, 4000.0, "t", "p")[0]
    assert abs(r["cw"] - 10.0) < 1e-9 and abs(r["sc"] - 50.0) < 1e-9 and r["n"] == 20.0     # CLIPER naiften sıkı: beceri %50 < %75
    df2 = df.drop(columns=["cliper"])
    assert kova_skorlari(df2, 4000.0, "t", "p")[0]["sc"] is None
