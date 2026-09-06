"""v2.274 — sapma katmanı: saf oranlar ve uygulama."""
import numpy as np
import pandas as pd

from pvquant.services import sapma_service as sp


def _df(gun=7, oran=0.9, seed=0):
    rng = np.random.default_rng(seed)
    ix = pd.date_range("2026-08-01", periods=24 * gun, freq="h", tz="UTC")
    p50 = np.clip(3000 * np.sin(np.pi * (ix.hour - 3) / 12), 0, None)
    return pd.DataFrame({"ts_utc": ix, "p50": p50, "power_kw": p50 * oran * rng.uniform(0.97, 1.03, len(ix))})


def test_aktif_ve_kelepce():
    a = sp.oranlar_hesapla(_df(oran=0.9), 4000.0, "Europe/Istanbul")
    assert a["aktif"] and abs(a["oran_genel"] - 0.9) < 0.02 and all(0.8 <= v <= 1.2 for v in a["oran_saat"].values())
    b = sp.oranlar_hesapla(_df(oran=0.5), 4000.0, "Europe/Istanbul")
    assert b["aktif"] and min(b["oran_saat"].values()) == 0.8                       # kelepçe


def test_uyumaz_ve_yetersiz():
    assert not sp.oranlar_hesapla(_df(oran=1.01), 4000.0, "Europe/Istanbul")["aktif"]   # sapma küçük → dokunma
    r = sp.oranlar_hesapla(_df(gun=3, oran=0.8), 4000.0, "Europe/Istanbul"); assert not r["aktif"] and "yetersiz" in r["neden"]
    assert sp.oranlar_hesapla(pd.DataFrame(), 4000.0, "UTC")["neden"] == "veri yok"


def test_uygula():
    ix = pd.date_range("2026-09-07", periods=24, freq="h", tz="UTC")
    h = pd.DataFrame({"p50_kw": 1000.0, "p10_kw": 800.0, "p90_kw": 1200.0, "physics_kw": 1000.0}, index=ix)
    ayar = {"aktif": True, "oran_saat": {i: 0.9 for i in range(24)}}
    u = sp.uygula_df(h, ayar, "Europe/Istanbul")
    assert (u["p50_kw"] == 900.0).all() and (u["p10_kw"] == 720.0).all() and (u["physics_kw"] == 1000.0).all()   # fizik dokunulmaz
    assert sp.uygula_df(h, {"aktif": False}, "UTC").equals(h)
