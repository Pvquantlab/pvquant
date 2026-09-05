"""Solar Forecast Arbiter deterministik metrik sözlüğü (solarforecastarbiter-core.metrics.deterministic).

MAE, MBE, RMSE, MAPE, nMAE, nMBE, nRMSE (normalizasyon: kapasite ya da gözlem ortalaması),
CRMSE (merkezlenmiş RMSE), forecast skill s = 1 − RMSE_f/RMSE_ref, Pearson r, R²,
KSI (Kolmogorov–Smirnov integral, Espinar 2009), OVER (KSI'nin kritik değeri aşan kısmı),
CPI = (KSI + OVER + 2·RMSE)/4 (Gueymard 2014; normalize biçimleriyle).
Raporlama: `karne_satiri` — PVQuant karnesine eklenecek kolonlar (nMAE/nRMSE/nMBE/skill).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

_trapz = getattr(np, "trapezoid", None) or np.trapz


def _hizala(obs: pd.Series, fx: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    idx = obs.dropna().index.intersection(fx.dropna().index)
    return obs.loc[idx].values.astype(float), fx.loc[idx].values.astype(float)


def mae(o, f): o, f = _hizala(o, f); return float(np.mean(np.abs(f - o)))
def mbe(o, f): o, f = _hizala(o, f); return float(np.mean(f - o))
def rmse(o, f): o, f = _hizala(o, f); return float(np.sqrt(np.mean((f - o) ** 2)))
def mape(o, f):
    o, f = _hizala(o, f); m = o != 0
    return float(np.mean(np.abs((f[m] - o[m]) / o[m])) * 100) if m.any() else np.nan
def nmae(o, f, norm): return mae(o, f) / norm * 100
def nmbe(o, f, norm): return mbe(o, f) / norm * 100
def nrmse(o, f, norm): return rmse(o, f) / norm * 100
def crmse(o, f):
    o, f = _hizala(o, f); return float(np.sqrt(np.mean(((f - f.mean()) - (o - o.mean())) ** 2)))
def skill(o, f, ref): return float(1 - rmse(o, f) / rmse(o, ref)) if rmse(o, ref) > 0 else np.nan
def r(o, f): o, f = _hizala(o, f); return float(np.corrcoef(o, f)[0, 1]) if o.std() > 0 and f.std() > 0 else np.nan
def r2(o, f):
    o, f = _hizala(o, f); ss = np.sum((o - o.mean()) ** 2)
    return float(1 - np.sum((f - o) ** 2) / ss) if ss > 0 else np.nan


def ksi(o, f, kutu: int = 100) -> float:
    """KSI = ∫|CDF_f − CDF_o| dx (Espinar 2009); birim gözlemle aynı."""
    o, f = _hizala(o, f)
    lo, hi = min(o.min(), f.min()), max(o.max(), f.max())
    if hi <= lo:
        return 0.0
    x = np.linspace(lo, hi, kutu + 1)
    Fo = np.searchsorted(np.sort(o), x, side="right") / len(o)
    Ff = np.searchsorted(np.sort(f), x, side="right") / len(f)
    return float(_trapz(np.abs(Ff - Fo), x))


def over(o, f, kutu: int = 100) -> float:
    """OVER: |ΔCDF|'nin kritik değer V_c = 1,63/√N'yi aştığı kısmın integrali."""
    o, f = _hizala(o, f)
    lo, hi = min(o.min(), f.min()), max(o.max(), f.max())
    if hi <= lo:
        return 0.0
    x = np.linspace(lo, hi, kutu + 1)
    d = np.abs(np.searchsorted(np.sort(f), x, side="right") / len(f) - np.searchsorted(np.sort(o), x, side="right") / len(o))
    vc = 1.63 / np.sqrt(len(o))
    return float(_trapz(np.clip(d - vc, 0, None), x))


def cpi(o, f, norm: float | None = None) -> float:
    """CPI = (KSI + OVER + 2·RMSE)/4; norm verilirse hepsi normalize (%)."""
    k, ov, rm = ksi(o, f), over(o, f), rmse(o, f)
    if norm:
        k, ov, rm = k / norm * 100, ov / norm * 100, rm / norm * 100
    return float((k + ov + 2 * rm) / 4)


def hepsi(obs: pd.Series, fx: pd.Series, kapasite: float, ref: pd.Series | None = None, norm: str = "kapasite") -> pd.Series:
    """Tüm SFA metrikleri tek seride; norm: 'kapasite' (SFA varsayılanı) ya da 'ortalama'."""
    o, f = _hizala(obs, fx)
    n = kapasite if norm == "kapasite" else float(np.mean(o))
    out = {"n": len(o), "mae": mae(obs, fx), "mbe": mbe(obs, fx), "rmse": rmse(obs, fx), "mape": mape(obs, fx),
           "nmae": nmae(obs, fx, n), "nmbe": nmbe(obs, fx, n), "nrmse": nrmse(obs, fx, n), "crmse": crmse(obs, fx),
           "r": r(obs, fx), "r2": r2(obs, fx), "ksi": ksi(obs, fx), "over": over(obs, fx), "cpi": cpi(obs, fx, n)}
    if ref is not None:
        out["skill"] = skill(obs, fx, ref)
    return pd.Series(out)


def karne_satiri(obs: pd.Series, fx: pd.Series, kapasite: float, ref: pd.Series | None = None) -> dict:
    """PVQuant karnesine eklenecek kolonlar (mevcut WMAPE'nin yanına)."""
    h = hepsi(obs, fx, kapasite, ref)
    return {"nmae_pct": round(h["nmae"], 2), "nrmse_pct": round(h["nrmse"], 2), "nmbe_pct": round(h["nmbe"], 2),
            "skill": (round(h["skill"], 3) if "skill" in h else None), "cpi_pct": round(h["cpi"], 2)}
