"""Ensemble yayılımı → ufukla büyüyen belirsizlik.

1. `yayilim_beceri`: ufuk başına spread–skill ilişkisi (σ_ens vs |hata|): kalibrasyon
   katsayısı c(h) = RMSE(h)/ortalama σ_ens(h) (underdispersion düzeltmesi).
2. `emos_lite`: nonhomogeneous Gaussian regression'ın kırpılmış (≥0) hali: μ = a + b·ens_ort,
   σ² = c + d·ens_var; ufuk bazlı katsayılar; kantiller normalden.
3. `ufuk_sigma`: üyesiz durumda geçmiş hatadan ufuk-bazlı σ(h) eğrisi (monoton büyüyen).
Çıktı: P10/P50/P90 (ya da istenen τ) — model çekirdeğine değil, sonrası katmana aittir.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

Z = {0.1: -1.2816, 0.25: -0.6745, 0.5: 0.0, 0.75: 0.6745, 0.9: 1.2816}


def yayilim_beceri(gercek: pd.Series, uyeler: pd.DataFrame, ufuk: pd.Series) -> pd.DataFrame:
    """Ufuk (saat) başına: ort. üye std, RMSE(ort), c = RMSE/std (1 ≈ kalibre; >1 underdispersed)."""
    idx = gercek.dropna().index.intersection(uyeler.dropna().index).intersection(ufuk.index)
    ort = uyeler.loc[idx].mean(axis=1); sd = uyeler.loc[idx].std(axis=1)
    e2 = (ort - gercek.loc[idx]) ** 2
    df = pd.DataFrame({"ufuk": ufuk.loc[idx], "sd": sd, "e2": e2})
    g = df.groupby("ufuk").agg(sd=("sd", "mean"), rmse=("e2", lambda x: np.sqrt(x.mean())), n=("e2", "size"))
    g["c"] = g["rmse"] / g["sd"].replace(0, np.nan)
    return g


def emos_lite(gercek: pd.Series, uyeler: pd.DataFrame, ufuk: pd.Series, kova: int = 6) -> dict[int, tuple[float, float, float, float]]:
    """Ufuk kovaları (0–kova, kova–2·kova, ...) için (a,b,c,d): μ=a+b·m, σ²=c+d·v. En küçük kareler + varyans eşleme."""
    idx = gercek.dropna().index.intersection(uyeler.dropna().index).intersection(ufuk.index)
    m = uyeler.loc[idx].mean(axis=1); v = uyeler.loc[idx].var(axis=1); y = gercek.loc[idx]
    kv = (ufuk.loc[idx] // kova).astype(int)
    kat = {}
    for k, ii in kv.groupby(kv).groups.items():
        if len(ii) < 30:
            continue
        A = np.c_[np.ones(len(ii)), m.loc[ii].values]
        ab, *_ = np.linalg.lstsq(A, y.loc[ii].values, rcond=None)
        r2 = (y.loc[ii].values - A @ ab) ** 2
        B = np.c_[np.ones(len(ii)), v.loc[ii].values]
        cd, *_ = np.linalg.lstsq(B, r2, rcond=None)
        cd = np.maximum(cd, [1e-6, 0.0])
        kat[int(k)] = (float(ab[0]), float(ab[1]), float(cd[0]), float(cd[1]))
    if not kat:
        raise ValueError("EMOS için yeterli veri yok")
    return kat


def emos_uygula(uyeler: pd.DataFrame, ufuk: pd.Series, kat: dict, kova: int = 6, taular=(0.1, 0.5, 0.9),
                taban: float = 0.0, tavan: float | None = None) -> pd.DataFrame:
    m = uyeler.mean(axis=1); v = uyeler.var(axis=1)
    kv = (ufuk.reindex(uyeler.index) // kova).astype(int)
    en_yakin = lambda k: kat[k] if k in kat else kat[min(kat, key=lambda j: abs(j - k))]
    out = pd.DataFrame(index=uyeler.index)
    mu = np.empty(len(m)); sd = np.empty(len(m))
    for i, (k, mi, vi) in enumerate(zip(kv.values, m.values, v.values)):
        a, b, c, d = en_yakin(int(k)); mu[i] = a + b * mi; sd[i] = np.sqrt(max(c + d * vi, 1e-9))
    for t in taular:
        q = mu + Z.get(t, 0.0) * sd
        q = np.clip(q, taban, tavan) if tavan is not None else np.maximum(q, taban)
        out[f"p{int(t*100)}"] = q
    return out


def ufuk_sigma(hata: pd.Series, ufuk: pd.Series, monoton: bool = True) -> pd.Series:
    """Üyesiz: ufuk başına hata std'si; monoton=True ise kümülatif maksimumla düzgünleştirir."""
    idx = hata.dropna().index.intersection(ufuk.index)
    s = pd.DataFrame({"u": ufuk.loc[idx], "e": hata.loc[idx]}).groupby("u")["e"].std()
    return s.cummax() if monoton else s


def sigma_ile_kantil(p50: pd.Series, ufuk: pd.Series, sigma_h: pd.Series, taular=(0.1, 0.9), taban: float = 0.0,
                     tavan: float | None = None) -> pd.DataFrame:
    s = ufuk.reindex(p50.index).map(lambda u: sigma_h.get(u, sigma_h.iloc[-1]))
    out = pd.DataFrame({"p50": p50})
    for t in taular:
        q = p50 + Z[t] * s
        out[f"p{int(t*100)}"] = q.clip(lower=taban, upper=tavan) if tavan is not None else q.clip(lower=taban)
    return out
