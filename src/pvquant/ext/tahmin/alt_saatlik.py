"""Alt-saatlik (15 dk) tahmin — saatlikten indirgeme ve uzlaştırma yardımcıları.

Saatlik P50'yi 15 dakikaya indirirken gök açıklığı endeksi saat içinde sabit tutulur ve
açık gök 15 dk profiliyle çarpılır (enerji korunur, doğuş/batış eğriliği doğru). İsteğe bağlı
kt değişkenliği (bulutlu saatlerde) log-normal gürültüyle eklenir; kantiller aynı yolla indirilir.
Ters yönde `saatlige_topla` ve 15 dk uzlaştırma için `uzlastirma_15dk` (DUY 2027 hazırlığı).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pvlib


def acik_gok_15dk(index_15: pd.DatetimeIndex, lat: float, lon: float, yukseklik: float = 0.0) -> pd.Series:
    konum = pvlib.location.Location(lat, lon, altitude=yukseklik, tz="UTC")
    orta = index_15 + pd.Timedelta(minutes=7, seconds=30)
    cs = konum.get_clearsky(orta, model="ineichen")
    cs.index = index_15
    return cs["ghi"].clip(lower=0.0)


def saatlikten_15dk(saatlik: pd.Series, lat: float, lon: float, degiskenlik: float = 0.0, seed: int = 0) -> pd.Series:
    """saatlik: GHI ya da güç (kt oranıyla ölçeklenir). degiskenlik: kt'ye eklenen log-normal σ (0 = düz)."""
    s = saatlik.dropna()
    idx15 = pd.date_range(s.index[0], s.index[-1] + pd.Timedelta(minutes=45), freq="15min", tz="UTC")
    cs15 = acik_gok_15dk(idx15, lat, lon)
    cs_saat = cs15.resample("h").mean()
    kt = (s / cs_saat.reindex(s.index).where(lambda x: x > 20)).clip(0, 1.3)
    kt15 = kt.reindex(idx15, method="ffill")
    if degiskenlik > 0:
        rng = np.random.default_rng(seed)
        g = np.exp(rng.normal(0, degiskenlik, len(idx15)))
        # bulutlu saatlerde (kt<0,8) uygula, enerji koruyacak şekilde saat içinde normalize
        g = pd.Series(g, index=idx15).where(kt15 < 0.8, 1.0)
        g = g / g.groupby(g.index.floor("h")).transform("mean")
        kt15 = (kt15 * g).clip(0, 1.3)
    out = (kt15 * cs15).clip(lower=0.0)
    # enerji koruma: saat toplamı saatlik değere eşitlensin (cs eğriliği sonrası küçük sapma)
    olcek = s / out.resample("h").mean().reindex(s.index).replace(0, np.nan)
    return (out * olcek.reindex(idx15, method="ffill").fillna(1.0)).fillna(0.0)


def saatlige_topla(seri_15: pd.Series, enerji: bool = False) -> pd.Series:
    r = seri_15.resample("h")
    return r.sum() if enerji else r.mean()


def uzlastirma_15dk(uretim_mw_15: pd.Series, program_mw_15: pd.Series, ptf: pd.Series, smf: pd.Series, k: float = 0.03, l: float = 0.03) -> pd.DataFrame:
    """15 dk uzlaştırma dönemi: MWh = MW/4; dengesizlik tutarı DUY formülüyle (15 dk SMF varsa o kullanılır)."""
    idx = uretim_mw_15.index.intersection(program_mw_15.index)
    sap = (uretim_mw_15.loc[idx] - program_mw_15.loc[idx]) / 4.0
    p = ptf.reindex(idx, method="ffill"); s = smf.reindex(idx, method="ffill")
    poz = sap.clip(lower=0) * pd.concat([p, s], axis=1).min(axis=1) * (1 - l)
    neg = (-sap).clip(lower=0) * pd.concat([p, s], axis=1).max(axis=1) * (1 + k)
    return pd.DataFrame({"sapma_mwh": sap, "pozitif_gelir": poz, "negatif_gider": neg})
