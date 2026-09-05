"""Degradasyon oranı (%/yıl) ve Performance Ratio trendi (IEC 61724-1).

- `pr`: PR = Y_f / Y_r = (E_AC / P_0) / (H_POA / G_STC); sıcaklık düzeltmeli PR′ (Y_r × [1 + γ(T_c − 25)]).
- `yoy_degradasyon`: RdTools YoY kalıbı — normalize edilmiş günlük verimin tam 365 gün arayla
  değişimlerinin medyanı; bootstrap ile güven aralığı.
- `pr_trendi`: aylık PR/PR′ serisi + doğrusal eğim (%/yıl) + son 3 ay vs önceki 12 ay kıyası.
Çıktılar 'sağlık' kartı içindir; tahmin çekirdeğine girmez.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

G_STC = 1000.0


def pr(e_ac_kwh: pd.Series, poa_wm2: pd.Series, p0_kw: float, t_cell: pd.Series | None = None, gamma: float = -0.0035,
       aralik: str = "ME") -> pd.DataFrame:
    """Saatlik girdi → aralık (ay) bazlı PR ve PR′. e_ac kWh/saat, POA W/m² (saatlik ort.), p0 kWp."""
    idx = e_ac_kwh.index.intersection(poa_wm2.index)
    e = e_ac_kwh.loc[idx]; h = poa_wm2.loc[idx] / 1000.0  # kWh/m² per saat
    yf = e / p0_kw
    yr = h
    out = pd.DataFrame({"Yf": yf.resample(aralik).sum(), "Yr": yr.resample(aralik).sum()})
    out["PR"] = out["Yf"] / out["Yr"].replace(0, np.nan)
    if t_cell is not None:
        yr_c = (h * (1 + gamma * (t_cell.loc[idx] - 25.0))).resample(aralik).sum()
        out["PR_sicaklik_duzeltmeli"] = out["Yf"] / yr_c.replace(0, np.nan)
    return out


def normalize_verim(e_ac_kwh: pd.Series, poa_wm2: pd.Series, t_cell: pd.Series | None = None, gamma: float = -0.0035,
                    min_poa_kwh: float = 2.0) -> pd.Series:
    """Günlük normalize verim (PR benzeri, sıcaklık düzeltmeli) — degradasyon girdisi."""
    idx = e_ac_kwh.index.intersection(poa_wm2.index)
    h = poa_wm2.loc[idx] / 1000.0
    if t_cell is not None:
        h = h * (1 + gamma * (t_cell.loc[idx] - 25.0))
    g = pd.DataFrame({"e": e_ac_kwh.loc[idx], "h": h}).resample("D").sum()
    g = g[g["h"] >= min_poa_kwh]
    return g["e"] / g["h"]


def yoy_degradasyon(verim_gunluk: pd.Series, bootstrap: int = 500, seed: int = 0) -> dict:
    """Year-on-year: her gün için 365 gün sonraki değerle oran − 1; medyan = yıllık oran (%/yıl)."""
    v = verim_gunluk.dropna()
    ileri = v.shift(freq=pd.Timedelta(days=-365)).reindex(v.index)  # t+365'in değeri t'ye gelir
    oran = (ileri / v - 1.0).dropna() * 100.0
    if len(oran) < 30:
        raise ValueError("YoY için en az ~13 ay veri gerekir")
    rng = np.random.default_rng(seed)
    orn = [np.median(rng.choice(oran.values, len(oran), replace=True)) for _ in range(bootstrap)]
    return {"rd_yuzde_yil": float(np.median(oran)), "ga_%68": (float(np.percentile(orn, 16)), float(np.percentile(orn, 84))),
            "n": int(len(oran))}


def pr_trendi(pr_aylik: pd.Series) -> dict:
    s = pr_aylik.dropna()
    if len(s) < 6:
        return {"egim_yuzde_yil": np.nan, "son3_vs_onceki12": np.nan}
    t = (s.index - s.index[0]).days / 365.25
    a, b = np.polyfit(t, s.values, 1)
    son3 = s.tail(3).mean(); onceki = s.iloc[-15:-3].mean() if len(s) >= 15 else s.iloc[:-3].mean()
    return {"egim_yuzde_yil": float(a / max(b, 1e-9) * 100), "son3_vs_onceki12": float((son3 / onceki - 1) * 100) if onceki else np.nan}
