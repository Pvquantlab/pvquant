"""Rolling-origin backtest ve eğitim/servis kayması denetimi.

`rolling_origin`: zaman-sıralı katlar — her katta [eğitim: başlangıç..t_k], [test: t_k..t_k+ufuk];
model bir fabrika fonksiyonuyla verilir: fit(X_tr, y_tr) → predict(X_te). Skorlar kat başına.
`kayma_denetimi`: eğitimde kullanılan özellik dağılımı vs serviste görülen dağılım —
PSI (population stability index) + KS istatistiği; eşik üstü → uyarı. Ayrıca "tahmin türevli mi,
ölçüm türevli mi" denetimi: eğitimde ölçümden gelen bir özellik serviste tahminden geliyorsa
(ör. gerçek GHI ile eğitilip NWP GHI ile servis) sapma burada görünür.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd


@dataclass
class Kat:
    egitim_bitis: pd.Timestamp
    test_baslangic: pd.Timestamp
    test_bitis: pd.Timestamp
    skor: dict


def rolling_origin(X: pd.DataFrame, y: pd.Series, fit_predict: Callable[[pd.DataFrame, pd.Series, pd.DataFrame], np.ndarray],
                   ilk_egitim_gun: int = 60, test_gun: int = 7, adim_gun: int = 7, skor_fn: Callable | None = None,
                   bosluk_saat: int = 0) -> list[Kat]:
    """fit_predict(X_tr, y_tr, X_te) → tahmin. skor_fn(y_te, tahmin) → dict; varsayılan MAE/RMSE/WMAPE."""
    idx = X.index.intersection(y.dropna().index)
    X, y = X.loc[idx], y.loc[idx]
    t0 = idx[0]; son = idx[-1]
    def _skor(g, t):
        e = t - g
        return {"mae": float(np.mean(np.abs(e))), "rmse": float(np.sqrt(np.mean(e ** 2))),
                "wmape": float(np.sum(np.abs(e)) / max(np.sum(np.abs(g)), 1e-9)), "n": int(len(g))}
    skor_fn = skor_fn or _skor
    katlar = []
    kes = t0 + pd.Timedelta(days=ilk_egitim_gun)
    while kes + pd.Timedelta(days=test_gun) <= son:
        tr = idx[idx < kes]; te = idx[(idx >= kes + pd.Timedelta(hours=bosluk_saat)) & (idx < kes + pd.Timedelta(days=test_gun))]
        if len(tr) > 24 and len(te) > 0:
            tah = np.asarray(fit_predict(X.loc[tr], y.loc[tr], X.loc[te]), float)
            katlar.append(Kat(tr[-1], te[0], te[-1], skor_fn(y.loc[te].values, tah)))
        kes += pd.Timedelta(days=adim_gun)
    return katlar


def kat_tablosu(katlar: list[Kat]) -> pd.DataFrame:
    return pd.DataFrame([{"egitim_bitis": k.egitim_bitis, "test_baslangic": k.test_baslangic, **k.skor} for k in katlar])


def psi(egitim: pd.Series, servis: pd.Series, kutu: int = 10) -> float:
    """Population Stability Index; <0,1 kararlı, 0,1–0,25 dikkat, >0,25 kayma."""
    e = egitim.dropna().values; s = servis.dropna().values
    kenar = np.unique(np.quantile(e, np.linspace(0, 1, kutu + 1)))
    if len(kenar) < 3:
        return 0.0
    pe, _ = np.histogram(e, kenar); ps, _ = np.histogram(s, kenar)
    pe = pe / max(pe.sum(), 1); ps = ps / max(ps.sum(), 1)
    pe = np.clip(pe, 1e-4, None); ps = np.clip(ps, 1e-4, None)
    return float(np.sum((ps - pe) * np.log(ps / pe)))


def ks(egitim: pd.Series, servis: pd.Series) -> float:
    e = np.sort(egitim.dropna().values); s = np.sort(servis.dropna().values)
    hepsi = np.concatenate([e, s])
    Fe = np.searchsorted(e, hepsi, side="right") / len(e); Fs = np.searchsorted(s, hepsi, side="right") / len(s)
    return float(np.max(np.abs(Fe - Fs)))


def kayma_denetimi(X_egitim: pd.DataFrame, X_servis: pd.DataFrame, psi_esik: float = 0.25) -> pd.DataFrame:
    satir = []
    for k in X_egitim.columns:
        if k not in X_servis:
            satir.append({"ozellik": k, "psi": np.nan, "ks": np.nan, "uyari": "serviste yok"}); continue
        p = psi(X_egitim[k], X_servis[k]); d = ks(X_egitim[k], X_servis[k])
        satir.append({"ozellik": k, "psi": p, "ks": d, "uyari": "KAYMA" if p > psi_esik else ("dikkat" if p > 0.1 else "")})
    return pd.DataFrame(satir)


def kaynak_tutarlilik(egitim_kaynak: dict[str, str], servis_kaynak: dict[str, str]) -> list[str]:
    """Özellik → kaynak ('olcum'|'nwp'|'uydu'). Eğitimde ölçüm, serviste NWP ise uyarı."""
    return [f"{k}: eğitim={egitim_kaynak[k]} servis={servis_kaynak.get(k, '?')}"
            for k in egitim_kaynak if servis_kaynak.get(k) != egitim_kaynak[k]]
