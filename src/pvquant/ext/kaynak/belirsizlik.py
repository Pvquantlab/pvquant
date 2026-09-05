"""Belirsizlik bütçesi — P50/P90/P99 için bileşenlerin kök-kare-toplamı.

Bankable pratik (Solargis/DNV raporlarının iskeleti):
  σ_toplam² = σ_yıllar_arası² + σ_kaynak² + σ_model² + σ_ölçüm²
  P90 = P50 · (1 − 1,282·σ_toplam), P99 = P50 · (1 − 2,326·σ_toplam)   (σ göreli, normal varsayımı)
  N yıllık ortalama için yıllar-arası bileşen σ/√N (10-yıl P90 vs 1-yıl P90 farkı).
Girdi: yıllık toplamlar (kWh/m² ya da kWh) — ERA5/PVGIS/CAMS'tan `yillik_toplam()`.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

Z = {50: 0.0, 75: 0.674, 90: 1.282, 95: 1.645, 99: 2.326}


@dataclass
class ButceSonucu:
    p50: float
    sigma_goreli: float
    bilesenler: dict[str, float]
    olasiliklar: dict[int, float]   # {50: .., 90: .., 99: ..} — 1 yıl
    olasiliklar_N_yil: dict[int, float]


def yillik_toplam(ghi_saatlik: pd.Series, tam_yil_esik: float = 0.95) -> pd.Series:
    """Saatlik W/m² → yıllık kWh/m²; eksik saati %5'i aşan yıllar atılır."""
    s = ghi_saatlik.dropna()
    yillik = s.resample("YE").sum() / 1000.0
    say = s.resample("YE").count()
    tam = say >= tam_yil_esik * 8760
    out = yillik[tam]
    out.index = out.index.year
    return out


def kaynak_sapmasi(a: pd.Series, b: pd.Series) -> float:
    """İki kaynağın (ör. ERA5 vs SARAH-3) ortak yıllarda göreli fark std'si → σ_kaynak tahmini."""
    ortak = a.index.intersection(b.index)
    if len(ortak) < 3:
        return float("nan")
    fark = (a.loc[ortak] - b.loc[ortak]) / b.loc[ortak]
    return float(np.sqrt(np.mean(fark ** 2)))


def butce(yillik: pd.Series, sigma_kaynak: float = 0.04, sigma_model: float = 0.03, sigma_olcum: float = 0.0,
          N_yil: int = 10) -> ButceSonucu:
    """yillik: yıl → toplam. σ'lar göreli (0,04 = %4). Varsayılanlar uydu-tabanlı GHI için tipik;
    ölçümle kalibre edilmiş sahada sigma_kaynak düşürülür, ölçüm belirsizliği eklenir."""
    y = yillik.dropna()
    if len(y) < 5:
        raise ValueError("en az 5 tam yıl gerekir")
    p50 = float(y.mean())
    s_yil = float(y.std(ddof=1) / p50)
    bil = {"yillar_arasi": s_yil, "kaynak": sigma_kaynak, "model": sigma_model, "olcum": sigma_olcum}
    s_top = float(np.sqrt(sum(v ** 2 for v in bil.values())))
    s_N = float(np.sqrt((s_yil ** 2) / N_yil + sigma_kaynak ** 2 + sigma_model ** 2 + sigma_olcum ** 2))
    return ButceSonucu(p50, s_top, bil, {p: p50 * (1 - z * s_top) for p, z in Z.items()},
                       {p: p50 * (1 - z * s_N) for p, z in Z.items()})


def aylik_p_degerleri(ghi_saatlik: pd.Series, p: tuple[int, ...] = (10, 50, 90)) -> pd.DataFrame:
    """Ay × yıl matrisinden ampirik aylık P-değerleri (kWh/m²) — panelin 'aylık beklenti' dili."""
    s = ghi_saatlik.dropna()
    aylik = s.resample("ME").sum() / 1000.0
    m = pd.DataFrame({"yil": aylik.index.year, "ay": aylik.index.month, "v": aylik.values}).pivot(index="yil", columns="ay", values="v")
    return pd.DataFrame({f"P{q}": m.quantile(q / 100.0) for q in p})
