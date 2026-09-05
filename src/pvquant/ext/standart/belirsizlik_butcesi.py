"""Bankable belirsizlik bütçesi — P50/P75/P90/P95/P99 (Solargis / DNV / IEA PVPS Task 13 kalıbı).

Bileşenler (göreli σ, birbirinden bağımsız varsayılır; RSS ile birleşir):
  yillar_arasi   : yıllık GHI toplamının değişkenliği (N yıl ortalaması için σ/√N)
  kaynak         : uydu/reanaliz ışınım verisinin sistematik belirsizliği (uydu ~%3–5; ölçümle kalibre ~%2)
  transpozisyon  : GHI→POA modeli (~%1,5–2,5)
  model_zinciri  : PV dönüşüm/ısıl/inverter (~%2–3)
  olcum          : ölçümle kalibre edilmişse piranometre/sayaç (~%1–2)
  degradasyon    : yıllık bozunma oranı belirsizliği (%/yıl × yıl / 2, uzun dönem için)
  kullanilabilirlik : işletme kesintileri (~%0,5–1,5)
Çıktı: P-değerleri tablosu (1 yıl ve N yıl), bileşen katkı yüzdeleri, isteğe bağlı Monte Carlo (lognormal).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

Z = {50: 0.0, 75: 0.6745, 90: 1.2816, 95: 1.6449, 99: 2.3263}
VARSAYILAN = {"kaynak": 0.04, "transpozisyon": 0.02, "model_zinciri": 0.025, "olcum": 0.0, "degradasyon": 0.0, "kullanilabilirlik": 0.01}


@dataclass
class Butce:
    p50: float
    bilesenler: dict[str, float]           # göreli σ (1 yıl)
    N_yil: int = 1
    _s1: float = field(init=False); _sN: float = field(init=False)

    def __post_init__(self):
        b = self.bilesenler
        self._s1 = float(np.sqrt(sum(v ** 2 for v in b.values())))
        bN = dict(b); bN["yillar_arasi"] = b.get("yillar_arasi", 0.0) / np.sqrt(max(self.N_yil, 1))
        self._sN = float(np.sqrt(sum(v ** 2 for v in bN.values())))

    def p(self, yuzde: int, N: bool = False) -> float:
        return self.p50 * (1 - Z[yuzde] * (self._sN if N else self._s1))

    def tablo(self) -> pd.DataFrame:
        return pd.DataFrame({"1 yıl": {f"P{q}": self.p(q) for q in Z}, f"{self.N_yil} yıl": {f"P{q}": self.p(q, True) for q in Z}})

    def katki(self) -> pd.Series:
        top = sum(v ** 2 for v in self.bilesenler.values()) or 1.0
        return pd.Series({k: v ** 2 / top for k, v in self.bilesenler.items()}).sort_values(ascending=False)

    def ozet(self) -> pd.Series:
        return pd.Series({"P50": self.p50, "sigma_1yil": self._s1, f"sigma_{self.N_yil}yil": self._sN,
                          "P90_1yil": self.p(90), f"P90_{self.N_yil}yil": self.p(90, True), "P99_1yil": self.p(99)})


def yillik_toplam(saatlik: pd.Series, tam_yil_esik: float = 0.95) -> pd.Series:
    s = saatlik.dropna(); yil = s.resample("YE").sum(); say = s.resample("YE").count()
    out = yil[say >= tam_yil_esik * 8760]; out.index = out.index.year
    return out


def yillar_arasi_sigma(yillik: pd.Series) -> float:
    y = yillik.dropna()
    if len(y) < 5:
        raise ValueError("en az 5 tam yıl")
    return float(y.std(ddof=1) / y.mean())


def butce_kur(p50: float, yillik: pd.Series | None = None, N_yil: int = 10, olcumle_kalibre: bool = False,
              degradasyon_sigma_yil: float = 0.0, ozel: dict | None = None) -> Butce:
    b = dict(VARSAYILAN)
    if yillik is not None:
        b["yillar_arasi"] = yillar_arasi_sigma(yillik)
    if olcumle_kalibre:
        b["kaynak"] = 0.02; b["olcum"] = 0.015
    if degradasyon_sigma_yil > 0:
        b["degradasyon"] = degradasyon_sigma_yil * N_yil / 2.0
    if ozel:
        b.update(ozel)
    return Butce(p50, b, N_yil)


def monte_carlo(p50: float, bilesenler: dict[str, float], n: int = 20000, seed: int = 0, N_yil: int = 1) -> pd.Series:
    """Lognormal bileşenlerin çarpımıyla P-değerleri (asimetri korunur; normal yaklaşımla kıyas için)."""
    rng = np.random.default_rng(seed)
    x = np.ones(n)
    for k, s in bilesenler.items():
        sN = s / np.sqrt(N_yil) if k == "yillar_arasi" else s
        x *= np.exp(rng.normal(-0.5 * sN ** 2, sN, n))
    v = p50 * x
    return pd.Series({f"P{q}": float(np.percentile(v, 100 - q)) for q in Z})
