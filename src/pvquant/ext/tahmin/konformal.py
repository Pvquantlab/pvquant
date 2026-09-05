"""Konformal kalibrasyon — CQR (Romano, Patterson & Candès 2019) ve ACI (Gibbs & Candès 2021).

CQR: kalibrasyon kümesinde uyumsuzluk skoru s = max(q_lo − y, y − q_hi); (1−α)(1+1/n)
yüzdeliği Q̂ → bant [q_lo − Q̂, q_hi + Q̂]. Ufuk ve/veya saat dilimine göre ayrı Q̂ tutulabilir.
ACI: çevrimiçi α_t güncelleme: α_{t+1} = α_t + γ(α − err_t); kapsama uzun dönemde 1−α'ya yakınsar.
Model çekirdeğine dokunmaz: girdi mevcut P10/P90 çıktısı, çıktı düzeltilmiş P10/P90.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


def uyumsuzluk(y: pd.Series, alt: pd.Series, ust: pd.Series) -> pd.Series:
    idx = y.dropna().index.intersection(alt.index).intersection(ust.index)
    return pd.concat([alt.loc[idx] - y.loc[idx], y.loc[idx] - ust.loc[idx]], axis=1).max(axis=1)


@dataclass
class CQR:
    alpha: float = 0.2                    # hedef: %80 bant (P10–P90)
    grup: str | None = None               # None | "ufuk" | "saat"
    q_hat: dict = field(default_factory=dict)

    def _anahtar(self, idx: pd.DatetimeIndex, ufuk: pd.Series | None):
        if self.grup == "saat":
            return pd.Series(idx.hour, index=idx)
        if self.grup == "ufuk" and ufuk is not None:
            return ufuk.reindex(idx)
        return pd.Series(0, index=idx)

    def kalibre_et(self, y: pd.Series, alt: pd.Series, ust: pd.Series, ufuk: pd.Series | None = None) -> "CQR":
        s = uyumsuzluk(y, alt, ust)
        k = self._anahtar(s.index, ufuk)
        for g, sg in s.groupby(k):
            n = len(sg)
            if n < 20:
                continue
            q = min(1.0, np.ceil((n + 1) * (1 - self.alpha)) / n)
            self.q_hat[g] = float(np.quantile(sg.values, q))
        if not self.q_hat:
            raise ValueError("kalibrasyon için ≥20 örnek gerekir")
        self.q_hat.setdefault("_genel", float(np.quantile(s.values, min(1.0, np.ceil((len(s) + 1) * (1 - self.alpha)) / len(s)))))
        return self

    def uygula(self, alt: pd.Series, ust: pd.Series, ufuk: pd.Series | None = None, taban: float = 0.0,
               tavan: float | None = None) -> tuple[pd.Series, pd.Series]:
        k = self._anahtar(alt.index, ufuk)
        q = k.map(lambda g: self.q_hat.get(g, self.q_hat["_genel"]))
        a = (alt - q).clip(lower=taban); u = ust + q
        if tavan is not None:
            u = u.clip(upper=tavan)
        return a, u


@dataclass
class ACI:
    """Adaptive Conformal Inference: her adımda kapsama hatasına göre α_t'yi günceller."""
    alpha: float = 0.2
    gamma: float = 0.01
    alpha_t: float | None = None
    skorlar: list = field(default_factory=list)
    pencere: int = 500

    def adim(self, y: float, alt: float, ust: float) -> float:
        """Yeni gözlemle güncelle; döner: bir sonraki adımda kullanılacak Q̂ (uyumsuzluk yüzdeliği)."""
        if self.alpha_t is None:
            self.alpha_t = self.alpha
        s = max(alt - y, y - ust)
        self.skorlar.append(s); self.skorlar = self.skorlar[-self.pencere:]
        q_onceki = self.q_hat()
        hata = 1.0 if s > q_onceki else 0.0
        self.alpha_t = float(np.clip(self.alpha_t + self.gamma * (self.alpha - hata), 0.001, 0.999))
        return self.q_hat()

    def q_hat(self) -> float:
        if len(self.skorlar) < 10:
            return 0.0
        return float(np.quantile(self.skorlar, min(1.0, 1 - (self.alpha_t or self.alpha))))

    def uygula(self, alt: float, ust: float, taban: float = 0.0) -> tuple[float, float]:
        q = self.q_hat()
        return max(taban, alt - q), ust + q


class KantilRegresyon:
    """Küçük doğrusal kantil regresyonu (pinball kaybı, alt-gradyan iniş) — bağımlılıksız.
    Kullanım: kt tahmininden kantil düzeltme öğrenmek (ör. x = [1, p50, ufuk, saat_sin, saat_cos])."""

    def __init__(self, tau: float, adim: float = 0.01, iter: int = 3000):
        self.tau, self.adim, self.iter, self.w = tau, adim, iter, None

    def fit(self, X: np.ndarray, y: np.ndarray) -> "KantilRegresyon":
        X = np.asarray(X, float); y = np.asarray(y, float)
        mu, sd = X.mean(0), X.std(0) + 1e-9; self.mu, self.sd = mu, sd
        Z = (X - mu) / sd; Z = np.c_[np.ones(len(Z)), Z]
        w = np.zeros(Z.shape[1]); w[0] = np.quantile(y, self.tau)
        for i in range(self.iter):
            r = y - Z @ w
            g = -(Z.T @ np.where(r >= 0, self.tau, self.tau - 1)) / len(y)
            w -= self.adim * g * (1.0 / np.sqrt(1 + i / 200))
        self.w = w
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        Z = (np.asarray(X, float) - self.mu) / self.sd
        return np.c_[np.ones(len(Z)), Z] @ self.w
