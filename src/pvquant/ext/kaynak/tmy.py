"""TMY üretimi (ISO 15927-4 / Sandia Finkelstein–Schafer) ve bankable P50/P90 yılı.

Girdi: çok yıllı saatlik çerçeve (PVGIS-SARAH3, CAMS ya da ERA5). Her takvim ayı için,
GHI (ağırlık 0,5), sıcaklık (0,25) ve rüzgar (0,25) günlük değerlerinin CDF'si uzun dönem
CDF'sine en yakın olan yıl seçilir (FS istatistiği); seçilen aylar birleştirilir, ay
sınırlarında 6 saatlik doğrusal yumuşatma yapılır. Ek olarak `pxx_yili()` yıllık toplamı
istenen yüzdeliğe en yakın gerçek yılı döndürür (P90 senaryo yılı — Solargis'in 'P90 TMY' muadili).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

AGIRLIK = {"ghi": 0.5, "temp_air": 0.25, "wind_speed_10m": 0.25}


def _fs(gunluk: pd.Series, yil: int, ay: int) -> float:
    uzun = gunluk[gunluk.index.month == ay].dropna()
    aday = uzun[uzun.index.year == yil]
    if len(aday) < 20 or len(uzun) < 100:
        return np.inf
    x = np.sort(uzun.values); F = np.arange(1, len(x) + 1) / len(x)
    Fa = np.searchsorted(np.sort(aday.values), x, side="right") / len(aday)
    return float(np.mean(np.abs(F - Fa)))


def tmy_uret(df: pd.DataFrame, min_yil: int = 8) -> tuple[pd.DataFrame, dict[int, int]]:
    """df: saatlik UTC, kolonlar ghi/temp_air/wind_speed_10m. Döner: (tmy saatlik, {ay: seçilen yıl})."""
    yillar = sorted(set(df.index.year))
    if len(yillar) < min_yil:
        raise ValueError(f"TMY için en az {min_yil} yıl gerekir, {len(yillar)} var")
    gunluk = {k: (df[k].resample("D").sum() if k == "ghi" else df[k].resample("D").mean()) for k in AGIRLIK}
    secim: dict[int, int] = {}
    for ay in range(1, 13):
        puan = {}
        for y in yillar:
            top = sum(AGIRLIK[k] * _fs(gunluk[k], y, ay) for k in AGIRLIK)
            if np.isfinite(top):
                puan[y] = top
        if not puan:
            raise ValueError(f"ay {ay} için aday yıl yok")
        secim[ay] = min(puan, key=puan.get)
    parcalar = []
    for ay, y in secim.items():
        p = df[(df.index.year == y) & (df.index.month == ay)].copy()
        p.index = p.index.map(lambda t: t.replace(year=2001) if not (t.month == 2 and t.day == 29) else pd.NaT)
        parcalar.append(p[p.index.notna()])
    tmy = pd.concat(parcalar).sort_index()
    tmy = tmy[~tmy.index.duplicated()]
    # ay sınırlarında yumuşatma (±3 saat doğrusal)
    for ay in range(2, 13):
        sinir = pd.Timestamp(2001, ay, 1, tz="UTC")
        pencere = tmy.loc[sinir - pd.Timedelta(hours=3): sinir + pd.Timedelta(hours=2)]
        if len(pencere) == 6:
            for k in ("temp_air", "wind_speed_10m"):
                tmy.loc[pencere.index, k] = np.linspace(pencere[k].iloc[0], pencere[k].iloc[-1], 6)
    return tmy, secim


def pxx_yili(df: pd.DataFrame, p: int = 90) -> tuple[int, float, pd.DataFrame]:
    """Yıllık GHI toplamı P-p yüzdeliğine (düşük taraf) en yakın gerçek yıl: (yıl, toplam kWh/m², o yılın saatlik verisi)."""
    yillik = df["ghi"].resample("YE").sum() / 1000.0
    say = df["ghi"].resample("YE").count()
    yillik = yillik[say >= 0.95 * 8760]
    hedef = float(np.percentile(yillik.values, 100 - p))
    yil = int(yillik.index[(yillik - hedef).abs().argmin()].year)
    return yil, float(yillik[yillik.index.year == yil].iloc[0]), df[df.index.year == yil]
