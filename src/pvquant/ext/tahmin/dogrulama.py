"""Doğrulama — deterministik (SFA / Yang 2020 sözlüğü) ve olasılıksal (Lauret 2019, Gneiting 2007).

Deterministik: MAE, MBE, RMSE, nMAE/nRMSE/nMBE (kapasiteye normalize), WMAPE, R²,
skill = 1 − RMSE_model/RMSE_referans (referans: akıllı persistans ya da iklimsel).
Olasılıksal: pinball (kantil kaybı), CRPS (kantillerden ya da ensemble üyelerinden),
PICP (bant kapsaması), ortalama bant genişliği, Winkler/aralık skoru, reliability
diyagramı (kantil bazlı), PIT histogramı.
Yalnız gündüz saatleri değerlendirilir: `gunduz_maskesi` (gerçekleşen ya da tahmin > eşik).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


def gunduz_maskesi(gercek: pd.Series, tahmin: pd.Series, kapasite: float, esik_oran: float = 0.01) -> pd.Series:
    return (gercek > esik_oran * kapasite) | (tahmin > esik_oran * kapasite)


@dataclass
class DeterministikSkor:
    n: int; mae: float; mbe: float; rmse: float; nmae: float; nmbe: float; nrmse: float; wmape: float; r2: float
    skill: float | None = None

    def tablo(self) -> pd.Series:
        return pd.Series(self.__dict__)


def deterministik(gercek: pd.Series, tahmin: pd.Series, kapasite: float, referans: pd.Series | None = None,
                  maske: pd.Series | None = None) -> DeterministikSkor:
    idx = gercek.dropna().index.intersection(tahmin.dropna().index)
    g, t = gercek.loc[idx].astype(float), tahmin.loc[idx].astype(float)
    m = maske.reindex(idx).fillna(False) if maske is not None else gunduz_maskesi(g, t, kapasite)
    g, t = g[m], t[m]
    if len(g) == 0:
        raise ValueError("değerlendirilecek gündüz saati yok")
    e = t - g
    mae = float(e.abs().mean()); mbe = float(e.mean()); rmse = float(np.sqrt((e ** 2).mean()))
    wmape = float(e.abs().sum() / g.abs().sum()) if g.abs().sum() > 0 else np.nan
    ss = float(((g - g.mean()) ** 2).sum()); r2 = float(1 - (e ** 2).sum() / ss) if ss > 0 else np.nan
    skill = None
    if referans is not None:
        r = referans.reindex(g.index).astype(float)
        ok = r.notna()
        rmse_r = float(np.sqrt(((r[ok] - g[ok]) ** 2).mean()))
        skill = float(1 - rmse / rmse_r) if rmse_r > 0 else np.nan
    return DeterministikSkor(int(len(g)), mae, mbe, rmse, mae / kapasite, mbe / kapasite, rmse / kapasite, wmape, r2, skill)


# ---------- olasılıksal ----------
def pinball(gercek: pd.Series, kantil_tahmin: pd.Series, tau: float) -> float:
    """Kantil kaybı: τ·(y−q)⁺ + (1−τ)·(q−y)⁺, ortalama."""
    idx = gercek.dropna().index.intersection(kantil_tahmin.dropna().index)
    d = gercek.loc[idx].values - kantil_tahmin.loc[idx].values
    return float(np.mean(np.where(d >= 0, tau * d, (tau - 1) * d)))


def crps_kantillerden(gercek: pd.Series, kantiller: pd.DataFrame) -> float:
    """CRPS ≈ 2·ortalama(pinball(τ_k)) kantil ızgarası üzerinde (kantil-ortalamalı yaklaşım).
    kantiller: kolonlar τ (0–1 float ya da 'p10' gibi), satırlar zaman."""
    taular = []
    for c in kantiller.columns:
        taular.append(float(c) if not isinstance(c, str) else float(str(c).lower().lstrip("p")) / 100.0)
    kayip = [pinball(gercek, kantiller[c], t) for c, t in zip(kantiller.columns, taular)]
    return float(2.0 * np.mean(kayip))


def crps_ensemble(gercek: pd.Series, uyeler: pd.DataFrame) -> float:
    """CRPS (Gneiting & Raftery 2007, enerji formu): E|X−y| − ½E|X−X'|; uyeler kolon=üye."""
    idx = gercek.dropna().index.intersection(uyeler.dropna().index)
    y = gercek.loc[idx].values[:, None]; X = uyeler.loc[idx].values
    t1 = np.mean(np.abs(X - y), axis=1)
    t2 = np.mean(np.abs(X[:, :, None] - X[:, None, :]), axis=(1, 2))
    return float(np.mean(t1 - 0.5 * t2))


def picp(gercek: pd.Series, alt: pd.Series, ust: pd.Series) -> float:
    idx = gercek.dropna().index.intersection(alt.dropna().index).intersection(ust.dropna().index)
    g = gercek.loc[idx]
    return float(((g >= alt.loc[idx]) & (g <= ust.loc[idx])).mean())


def bant_genisligi(alt: pd.Series, ust: pd.Series, kapasite: float | None = None) -> float:
    w = float((ust - alt).mean())
    return w / kapasite if kapasite else w


def aralik_skoru(gercek: pd.Series, alt: pd.Series, ust: pd.Series, alpha: float = 0.2) -> float:
    """Winkler/aralık skoru (küçük iyi): genişlik + (2/α)·kapsam dışı ceza."""
    idx = gercek.dropna().index.intersection(alt.index).intersection(ust.index)
    g, a, u = gercek.loc[idx].values, alt.loc[idx].values, ust.loc[idx].values
    s = (u - a) + (2 / alpha) * (a - g) * (g < a) + (2 / alpha) * (g - u) * (g > u)
    return float(np.mean(s))


def reliability(gercek: pd.Series, kantiller: pd.DataFrame) -> pd.DataFrame:
    """Kantil güvenilirliği: her τ için gözlenen kapsama oranı P(y ≤ q_τ). İdeal: köşegen."""
    satir = []
    for c in kantiller.columns:
        tau = float(c) if not isinstance(c, str) else float(str(c).lower().lstrip("p")) / 100.0
        idx = gercek.dropna().index.intersection(kantiller[c].dropna().index)
        satir.append({"tau": tau, "gozlenen": float((gercek.loc[idx] <= kantiller.loc[idx, c]).mean()), "n": len(idx)})
    df = pd.DataFrame(satir).sort_values("tau").reset_index(drop=True)
    df["sapma"] = df["gozlenen"] - df["tau"]
    return df


def pit_histogram(gercek: pd.Series, kantiller: pd.DataFrame, kutu: int = 10) -> pd.Series:
    """PIT: y'nin tahmin dağılımındaki yüzdeliği (kantiller arasında doğrusal); düz histogram = kalibre."""
    taular = np.array([float(c) if not isinstance(c, str) else float(str(c).lower().lstrip("p")) / 100.0 for c in kantiller.columns])
    sira = np.argsort(taular); taular = taular[sira]; Q = kantiller.values[:, sira]
    idx = gercek.dropna().index.intersection(kantiller.dropna().index)
    y = gercek.loc[idx].values; Q = kantiller.loc[idx].values[:, sira]
    pit = np.empty(len(y))
    for i in range(len(y)):
        q = Q[i]
        if y[i] <= q[0]:
            pit[i] = taular[0] * (y[i] / q[0] if q[0] > 0 else 1.0)
        elif y[i] >= q[-1]:
            pit[i] = taular[-1] + (1 - taular[-1]) * 0.5
        else:
            pit[i] = np.interp(y[i], q, taular)
    h, _ = np.histogram(pit, bins=kutu, range=(0, 1))
    return pd.Series(h / h.sum(), index=[f"{i/kutu:.1f}-{(i+1)/kutu:.1f}" for i in range(kutu)])


def olasiliksal_ozet(gercek: pd.Series, kantiller: pd.DataFrame, kapasite: float, alt: str = "p10", ust: str = "p90") -> pd.Series:
    """Karneye eklenecek tek satır: CRPS (kapasiteye normalize), pinball P10/P50/P90, PICP, bant, aralık skoru."""
    kolon = {str(c).lower(): c for c in kantiller.columns}
    out = {"crps_n": crps_kantillerden(gercek, kantiller) / kapasite}
    for ad, tau in (("p10", 0.1), ("p50", 0.5), ("p90", 0.9)):
        if ad in kolon:
            out[f"pinball_{ad}_n"] = pinball(gercek, kantiller[kolon[ad]], tau) / kapasite
    if alt in kolon and ust in kolon:
        out["picp_80"] = picp(gercek, kantiller[kolon[alt]], kantiller[kolon[ust]])
        out["bant_n"] = bant_genisligi(kantiller[kolon[alt]], kantiller[kolon[ust]], kapasite)
        out["aralik_skoru_n"] = aralik_skoru(gercek, kantiller[kolon[alt]], kantiller[kolon[ust]], 0.2) / kapasite
    return pd.Series(out)
