"""v2.248 — worker olasiliksal_skorlar: P10-P90 bandinin gun sinavi (DB yok)."""
import numpy as np
import pandas as pd

from apps.worker.main import kova_skorlari, olasiliksal_skorlar

CAP = 1000.0


def _df(bant=True):
    ts = pd.date_range("2026-07-01", periods=24, freq="h", tz="UTC")
    g = np.clip(np.sin((ts.hour - 6) / 12 * np.pi), 0, None)
    gercek = 800 * g
    df = pd.DataFrame({"ts_utc": ts, "gun": ts.date, "kova": "0-24", "power_kw": gercek,
                       "p50_kw": gercek * 1.02, "naif": gercek * 1.1})
    if bant:
        df["p10_kw"] = gercek * 0.8; df["p90_kw"] = gercek * 1.2      # gercek hep bant icinde
    return df[gercek > 0.02 * CAP]


def test_bant_icinde_kalan_gun():
    o = olasiliksal_skorlar(_df(), CAP)
    assert o["pc"] == 1.0                                  # PICP80 = 1 → bant fazla genis (asiri temkinli)
    assert o["k10"] == 0.0 and o["k90"] == 1.0             # reliability uclari
    assert 0 < o["q10"] and 0 < o["q50"] and 0 < o["q90"] and o["cr"] > 0
    assert abs(o["bn"] - (0.4 * 800 * _df().power_kw.mean() / 800) / CAP) < 1e-9


def test_bant_yoksa_none_ve_kova_skorlari_tasir():
    assert olasiliksal_skorlar(_df(bant=False), CAP) == {k: None for k in ("q10", "q50", "q90", "cr", "pc", "k10", "k90", "bn")}
    r = kova_skorlari(_df(), CAP, "t", "p")[0]
    assert {"q10", "q50", "q90", "cr", "pc", "k10", "k90", "bn"} <= set(r) and r["pc"] == 1.0 and r["m"] > 0
