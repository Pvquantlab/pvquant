"""Kısa ufuk (0–6 saat) katmanı — uydu/ölçüm nowcast'ı ile NWP'nin rampalı harmanı.

Gerçek uydu bulut-hareket-vektörü (CMV) nowcast'ı EUMETSAT gerçek zamanlı
görüntü lisansı ve işlem altyapısı ister; bu modül onun YERİNE üç şeyi yapar:
  1. Akıllı persistans: son ölçülen (SCADA/piranometre ya da CAMS) gök açıklığı
     endeksini ileri taşır (Yang 2019 referans tahmini).
  2. Rampalı harman: ufuk h saat için w(h) = exp(-h/τ) ile persistans, 1-w ile
     NWP (τ varsayılan 2 s; NREL setinde HA4'ün DA'ya üstünlüğünün mühendislik karşılığı).
  3. Uydu GHI kancası: `uydu_ghi_son` verilirse persistans ölçüm yerine uydudan başlar.
Çıktı yine MeteoCerceve; yalnız GHI (ve türetilen DNI/DHI) değişir, öteki
kolonlar NWP'den gelir. Türkiye'de gün içi KGÜP güncellemesi (GİP kapı +30 dk)
için tasarlanmıştır.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .ortak import MeteoCerceve, acik_gok_ghi, gok_acikligi


def akilli_persistans(son_ghi: pd.Series, lat: float, lon: float, hedef_index: pd.DatetimeIndex,
                      pencere_saat: int = 3) -> pd.Series:
    """Son `pencere_saat` saatin ortalama gök açıklığı endeksini hedef saatlere taşır."""
    kt = gok_acikligi(son_ghi, lat, lon).dropna()
    if kt.empty:
        return pd.Series(np.nan, index=hedef_index)
    kt0 = float(kt.tail(pencere_saat).mean())
    cs = acik_gok_ghi(hedef_index, lat, lon)
    return (kt0 * cs).clip(lower=0.0)


def rampali_harman(nwp: MeteoCerceve, son_ghi: pd.Series, simdi: pd.Timestamp | None = None,
                   tau_saat: float = 2.0, ufuk_saat: int = 6) -> MeteoCerceve:
    """0–ufuk saat aralığında persistans ↔ NWP harmanı; ötesi NWP.

    son_ghi: ölçülen ya da uydu GHI (saatlik, UTC), son değeri 'şimdi'ye en yakın.
    """
    simdi = pd.Timestamp(simdi or son_ghi.dropna().index[-1])
    simdi = simdi.tz_localize("UTC") if simdi.tz is None else simdi.tz_convert("UTC")
    df = nwp.df.copy()
    hedef = df.index[(df.index > simdi) & (df.index <= simdi + pd.Timedelta(hours=ufuk_saat))]
    if len(hedef) == 0:
        return nwp
    pers = akilli_persistans(son_ghi, nwp.latitude, nwp.longitude, hedef)
    h = ((hedef - simdi) / pd.Timedelta(hours=1)).astype(float)
    w = np.exp(-h / tau_saat)
    harman = w * pers.values + (1.0 - w) * df.loc[hedef, "ghi"].values
    df.loc[hedef, "ghi"] = np.where(np.isnan(pers.values), df.loc[hedef, "ghi"].values, harman)
    df = df.drop(columns=[c for c in ("dni", "dhi") if c in df.columns])
    return MeteoCerceve(df, nwp.latitude, nwp.longitude, nwp.kaynak, nwp.kosu_zamani, nwp.uyeler)


def sapma_duzelt(nwp_ghi: pd.Series, gecmis_nwp: pd.Series, gecmis_gerceklesen: pd.Series,
                 lat: float, lon: float, gun: int = 7) -> pd.Series:
    """Son `gun` günün saat-bazlı kt sapmasını (OCF trend_adjuster kalıbı) tahmine uygular.

    Model çekirdeğine değil, meteoroloji girdisine uygulanır: NWP GHI'nın sistematik
    sabah/akşam sapması düzeltilir. Kalibre santralde rezidüel model zaten bunu
    öğreniyorsa çift sayım olmasın diye kapalı tutulmalıdır.
    """
    kt_n = gok_acikligi(gecmis_nwp, lat, lon)
    kt_g = gok_acikligi(gecmis_gerceklesen, lat, lon)
    ortak = kt_n.dropna().index.intersection(kt_g.dropna().index)
    son = ortak[ortak >= ortak.max() - pd.Timedelta(days=gun)] if len(ortak) else ortak
    if len(son) < 24:
        return nwp_ghi
    fark = (kt_g.loc[son] - kt_n.loc[son])
    saat_sapma = fark.groupby(fark.index.hour).mean()
    kt_t = gok_acikligi(nwp_ghi, lat, lon)
    duzeltme = pd.Series(nwp_ghi.index.hour, index=nwp_ghi.index).map(saat_sapma).fillna(0.0)
    cs = acik_gok_ghi(nwp_ghi.index, lat, lon)
    return ((kt_t.fillna(0.0) + duzeltme).clip(lower=0.0, upper=1.3) * cs)
