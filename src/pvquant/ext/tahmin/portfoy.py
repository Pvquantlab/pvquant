"""Portföy / hiyerarşik uzlaştırma — bottom-up, top-down, MinT (Wickramasuriya, Athanasopoulos & Hyndman 2019).

Hiyerarşi: toplam → (bölge) → santral. S matrisi (m × n): m = tüm düğümler, n = taban (santral).
MinT: ỹ = S (S' W⁻¹ S)⁻¹ S' W⁻¹ ŷ; W = taban tahmin hatalarının kovaryansı (ols: I; wls: diag; shrink:
Schäfer–Strimmer büzülmüş örneklem kovaryansı). Girdi: her düğüm için bağımsız tahmin (ŷ);
çıktı: tutarlı (toplamı tutan) tahminler. Kantiller için taban kantilleri ayrı ayrı uzlaştırılır
(yaklaşık; tam olasılıksal uzlaştırma için üye/örnek düzeyinde uygulanır).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def toplama_matrisi(hiyerarsi: dict[str, list[str]], taban: list[str]) -> tuple[np.ndarray, list[str]]:
    """hiyerarsi: {düğüm: [taban üyeleri]}; taban listesi sırayı belirler. Döner (S, düğüm sırası [üst düğümler + taban])."""
    ust = list(hiyerarsi)
    S = np.zeros((len(ust) + len(taban), len(taban)))
    for i, d in enumerate(ust):
        for u in hiyerarsi[d]:
            S[i, taban.index(u)] = 1.0
    S[len(ust):, :] = np.eye(len(taban))
    return S, ust + taban


def bottom_up(taban_tahmin: pd.DataFrame, S: np.ndarray, dugumler: list[str]) -> pd.DataFrame:
    return pd.DataFrame(taban_tahmin.values @ S.T, index=taban_tahmin.index, columns=dugumler)


def top_down_oran(toplam_tahmin: pd.Series, gecmis_taban: pd.DataFrame, S: np.ndarray, dugumler: list[str]) -> pd.DataFrame:
    p = gecmis_taban.sum() / gecmis_taban.sum().sum()
    taban = pd.DataFrame(np.outer(toplam_tahmin.values, p.values), index=toplam_tahmin.index, columns=gecmis_taban.columns)
    return bottom_up(taban, S, dugumler)


def _buzulmus_kov(E: np.ndarray) -> np.ndarray:
    """Schäfer–Strimmer: köşegene doğru büzülmüş örneklem kovaryansı."""
    n, p = E.shape
    W = np.cov(E, rowvar=False, ddof=1)
    if p == 1:
        return np.atleast_2d(W)
    Xs = (E - E.mean(0)) / (E.std(0, ddof=1) + 1e-12)
    r = np.corrcoef(Xs, rowvar=False)
    var_r = ((Xs[:, :, None] * Xs[:, None, :]) ** 2).sum(0) / (n * (n - 1)) - r ** 2 / n
    np.fill_diagonal(var_r, 0)
    lam = float(np.clip(var_r.sum() / ((r - np.eye(p)) ** 2).sum(), 0, 1)) if p > 1 else 0.0
    D = np.diag(np.diag(W))
    return lam * D + (1 - lam) * W


def mint(tahminler: pd.DataFrame, S: np.ndarray, dugumler: list[str], hatalar: pd.DataFrame | None = None,
         yontem: str = "shrink") -> pd.DataFrame:
    """tahminler: kolonlar = dugumler sırasıyla tüm düğümlerin bağımsız tahmini (m). hatalar: aynı düzende geçmiş
    artıklar (uzlaştırma için W). yontem: ols|wls|shrink."""
    Y = tahminler[dugumler].values
    m = S.shape[0]
    if yontem == "ols" or hatalar is None:
        W = np.eye(m)
    else:
        E = hatalar[dugumler].dropna().values
        W = np.diag(np.var(E, axis=0, ddof=1) + 1e-9) if yontem == "wls" else _buzulmus_kov(E) + 1e-9 * np.eye(m)
    Wi = np.linalg.pinv(W)
    G = np.linalg.pinv(S.T @ Wi @ S) @ S.T @ Wi
    P = S @ G
    return pd.DataFrame(Y @ P.T, index=tahminler.index, columns=dugumler)


def tutarlilik_kontrol(uzlasik: pd.DataFrame, S: np.ndarray, dugumler: list[str], tol: float = 1e-6) -> bool:
    taban = uzlasik[dugumler[-S.shape[1]:]].values
    return bool(np.allclose(uzlasik[dugumler].values, taban @ S.T, atol=tol))
