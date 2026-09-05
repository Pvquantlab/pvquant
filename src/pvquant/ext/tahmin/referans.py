"""Referans tahminler ve optimal konveks birleşim (Yang 2019, Solar Energy).

- `iklimsel`: saat × ay iklimsel ortalama (gündüz profili) — 'climatology'.
- `akilli_persistans`: dünün aynı saatinin gök açıklığı endeksi × bugünün açık gök GHI'sı.
- `optimal_birlesim`: CLIPER benzeri — iklimsel ile persistansın konveks birleşimi
  ŷ = w·pers + (1−w)·iklim; w, geçmiş üzerinde RMSE'yi en aza indirecek şekilde (kapalı form,
  [0,1]'e kırpılmış) ufuk başına öğrenilir. Skill hesaplarında referans olarak kullanılır:
  bu referansı geçemeyen model 'beceri' iddia edemez.
Gerçek gerçekleşen üretim ya da GHI için aynı şekilde çalışır.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def iklimsel(gecmis: pd.Series, hedef_index: pd.DatetimeIndex, min_gun: int = 20) -> pd.Series:
    g = gecmis.dropna()
    tablo = g.groupby([g.index.month, g.index.hour]).agg(["mean", "size"])
    tablo.loc[tablo["size"] < min_gun, "mean"] = np.nan
    anahtar = list(zip(hedef_index.month, hedef_index.hour))
    return pd.Series([tablo["mean"].get(a, np.nan) for a in anahtar], index=hedef_index)


def akilli_persistans(gecmis: pd.Series, acik_gok_gecmis: pd.Series, acik_gok_hedef: pd.Series, gecikme_gun: int = 1) -> pd.Series:
    """kt(t − gecikme) × cs(t). acik_gok serileri aynı sözleşmeyle (saatlik, aynı büyüklük) verilmeli."""
    kt = (gecmis / acik_gok_gecmis.where(acik_gok_gecmis > 20)).clip(0, 1.3)
    kaynak = kt.shift(freq=pd.Timedelta(days=gecikme_gun)).reindex(acik_gok_hedef.index).fillna(0.0)
    return (kaynak * acik_gok_hedef).clip(lower=0.0)


def optimal_agirlik(gercek: pd.Series, pers: pd.Series, iklim: pd.Series) -> float:
    """w* = argmin ||y − (w·p + (1−w)·c)||² = <y−c, p−c>/||p−c||², [0,1]'e kırpılır."""
    idx = gercek.dropna().index.intersection(pers.dropna().index).intersection(iklim.dropna().index)
    y, p, c = gercek.loc[idx].values, pers.loc[idx].values, iklim.loc[idx].values
    d = p - c
    pay = float(np.dot(y - c, d)); payda = float(np.dot(d, d))
    if payda <= 0:
        return 0.5
    return float(np.clip(pay / payda, 0.0, 1.0))


def optimal_birlesim(gercek_gecmis: pd.Series, pers_gecmis: pd.Series, iklim_gecmis: pd.Series,
                     pers_hedef: pd.Series, iklim_hedef: pd.Series, ufuk_gecmis: pd.Series | None = None,
                     ufuk_hedef: pd.Series | None = None) -> tuple[pd.Series, dict]:
    """Ufuk verilirse w(h) ayrı; yoksa tek w. Döner: (referans tahmin, ağırlıklar)."""
    if ufuk_gecmis is None:
        w = optimal_agirlik(gercek_gecmis, pers_gecmis, iklim_gecmis)
        return (w * pers_hedef + (1 - w) * iklim_hedef.reindex(pers_hedef.index)).clip(lower=0), {"tum": w}
    W = {}
    for h, ii in ufuk_gecmis.groupby(ufuk_gecmis).groups.items():
        W[int(h)] = optimal_agirlik(gercek_gecmis.loc[ii], pers_gecmis.loc[ii], iklim_gecmis.loc[ii])
    wh = ufuk_hedef.reindex(pers_hedef.index).map(lambda h: W.get(int(h), np.mean(list(W.values()))))
    return (wh * pers_hedef + (1 - wh) * iklim_hedef.reindex(pers_hedef.index)).clip(lower=0), W
