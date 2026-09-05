"""IEC 61853-1 güç matrisi — modülün (G, T) ızgarasındaki gücü/verimi ve enerji derecelendirme.

IEC 61853-1 matrisi: G ∈ {100,200,400,600,800,1000,1100} W/m², T ∈ {15,25,50,75} °C (bazı hücreler tanımsız).
Fonksiyonlar:
  matris_uydur   : matristen ADR verim modeli (pvlib.pvarray.fit_pvefficiency_adr) — ölçüm noktaları dışına düzgün uzatma
  verim          : (G,T) → η/η_STC (ADR) ya da iki-doğrusal interpolasyon (yalnız ızgara içinde)
  matris_uret    : veri sayfası parametrelerinden (γ_P, düşük ışınım katsayısı) sentetik matris (matris yoksa)
  enerji_derecesi: saatlik (POA, T_cell) ile yıllık DC enerji (kWh/kWp) — IEC 61853-3 CSER'in sadeleşmiş hali
Modül davranışını fizik zincirine 'η(G,T) çarpanı' olarak vermek için tasarlanmıştır.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pvlib

G_IEC = np.array([100, 200, 400, 600, 800, 1000, 1100], float)
T_IEC = np.array([15, 25, 50, 75], float)


def matris_uydur(matris: pd.DataFrame, p_stc: float) -> dict:
    """matris: index=G (W/m²), columns=T (°C), değer=P_mpp (W); NaN hücreler atlanır. Döner ADR parametreleri."""
    G, T, P = [], [], []
    for g in matris.index:
        for t in matris.columns:
            v = matris.loc[g, t]
            if pd.notna(v):
                G.append(float(g)); T.append(float(t)); P.append(float(v))
    G, T, P = np.array(G), np.array(T), np.array(P)
    eta = P / (G * (p_stc / 1000.0))          # η/η_STC oranı: P/(G·A·η_stc) = P/(G·P_stc/1000)
    return pvlib.pvarray.fit_pvefficiency_adr(G, T, eta, dict_output=True)


def verim(poa: pd.Series | np.ndarray, t_cell: pd.Series | np.ndarray, adr: dict) -> np.ndarray:
    """η(G,T)/η_STC (ADR). Gece/0 için 0."""
    g = np.asarray(poa, float); t = np.asarray(t_cell, float)
    out = pvlib.pvarray.pvefficiency_adr(np.clip(g, 1e-3, None), t, **adr)
    return np.where(g <= 0, 0.0, np.nan_to_num(out, nan=0.0))


def interpolasyon(matris: pd.DataFrame, g: float, t: float) -> float:
    """İki-doğrusal interpolasyon (ızgara içinde); dışında en yakın kenar."""
    Gs = np.array(matris.index, float); Ts = np.array(matris.columns, float)
    M = matris.values.astype(float)
    # NaN hücreleri satır/kolon komşularıyla doldur (basit)
    M = pd.DataFrame(M).interpolate(axis=0, limit_direction="both").interpolate(axis=1, limit_direction="both").values
    g = float(np.clip(g, Gs.min(), Gs.max())); t = float(np.clip(t, Ts.min(), Ts.max()))
    i = np.searchsorted(Gs, g, side="right") - 1; i = int(np.clip(i, 0, len(Gs) - 2))
    j = np.searchsorted(Ts, t, side="right") - 1; j = int(np.clip(j, 0, len(Ts) - 2))
    fg = (g - Gs[i]) / (Gs[i + 1] - Gs[i]); ft = (t - Ts[j]) / (Ts[j + 1] - Ts[j])
    return float((1 - fg) * (1 - ft) * M[i, j] + fg * (1 - ft) * M[i + 1, j] + (1 - fg) * ft * M[i, j + 1] + fg * ft * M[i + 1, j + 1])


def matris_uret(p_stc: float, gamma_p: float = -0.0035, dusuk_isinim_k: float = 0.02) -> pd.DataFrame:
    """Veri sayfasından sentetik IEC 61853-1 matrisi: P = P_stc·(G/1000)·(1+k·ln(G/1000))·(1+γ(T−25)).
    IEC'nin tanımsız hücreleri (100 W/m² @ 75 °C, 1100 @ 15 °C) NaN bırakılır."""
    M = pd.DataFrame(index=G_IEC, columns=T_IEC, dtype=float)
    for g in G_IEC:
        for t in T_IEC:
            if (g == 100 and t == 75) or (g == 1100 and t == 15) or (g == 100 and t == 50) or (g == 200 and t == 75):
                M.loc[g, t] = np.nan; continue
            M.loc[g, t] = p_stc * (g / 1000) * (1 + dusuk_isinim_k * np.log(g / 1000)) * (1 + gamma_p * (t - 25))
    return M


def enerji_derecesi(poa: pd.Series, t_cell: pd.Series, adr: dict, p_stc_kwp: float = 1.0) -> dict:
    """Yıllık DC enerji (kWh/kWp) ve 'iklim-özgü verim oranı' (CSER benzeri): E / (H_POA · P_stc)."""
    eta = verim(poa.values, t_cell.values, adr)
    e_kwh = float((poa.values / 1000.0 * eta * p_stc_kwp).sum())
    h = float(poa.clip(lower=0).sum() / 1000.0)
    return {"E_dc_kwh_per_kwp": e_kwh / p_stc_kwp, "H_poa_kwh_m2": h, "CSER": e_kwh / (h * p_stc_kwp) if h > 0 else np.nan}
