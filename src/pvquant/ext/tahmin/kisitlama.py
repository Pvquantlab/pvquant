"""Curtailment / clipping tespiti ve kalibrasyon maskesi (pvanalytics kalıbı, bağımlılıksız).

- `clipping_maskesi`: AC gücün tavana (ya da eşik×tavan) yapıştığı plato saatleri — ardışık
  değerlerin türevi ~0 ve seviye üst yüzdeliğe yakın (pvanalytics.features.clipping.levels / geometric).
- `curtailment_maskesi`: beklenen (fizik/tahmin) gücün çok altında ve DÜZ giden segmentler —
  şebeke kısıntısı imzası (sabit MW tavanı); bulut kaynaklı düşüşlerden düzlükle ayrılır.
- `kalibrasyon_maskesi`: ikisinin birleşimi + veri kalitesi bayrakları → kalibrasyona ve
  metriklere giren saatler. Kısıtlı saatler ATILMAZ, bayraklanır (tire ilkesi).
- `kisitsiz_senaryo`: "kısıtlama olmasaydı" üretimi = beklenen ile gerçekleşenin kısıt saatlerinde
  beklenenle değiştirilmesi (kayıp muhasebesi için).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def clipping_maskesi(guc_ac: pd.Series, tavan_kw: float | None = None, oran: float = 0.985,
                     turev_esik: float = 0.005, min_ardisik: int = 2) -> pd.Series:
    """Plato + üst seviye. tavan_kw verilmezse gündüz gücünün %99,5 yüzdeliği alınır."""
    p = guc_ac.astype(float)
    tavan = tavan_kw if tavan_kw else float(np.nanpercentile(p[p > 0].values, 99.5))
    seviye = p >= oran * tavan
    d = (p.diff().abs() / tavan)
    duz = (d.fillna(1.0) <= turev_esik) | (d.shift(-1).fillna(1.0) <= turev_esik)
    aday = seviye & duz
    # en az min_ardisik ardışık saat
    grup = (aday != aday.shift()).cumsum()
    uzunluk = aday.groupby(grup).transform("size")
    return aday & (uzunluk >= min_ardisik)


def curtailment_maskesi(gercek: pd.Series, beklenen: pd.Series, oran_esik: float = 0.6, duzluk_esik: float = 0.03,
                        min_ardisik: int = 2, kapasite: float | None = None) -> pd.Series:
    """Gerçek < oran_esik·beklenen VE gerçek düz (|Δ|/kapasite ≤ duzluk_esik) VE beklenen yüksek."""
    idx = gercek.index.intersection(beklenen.index)
    g = gercek.loc[idx].astype(float); b = beklenen.loc[idx].astype(float)
    kap = kapasite or float(np.nanmax(b.values))
    dusuk = (g < oran_esik * b) & (b > 0.2 * kap)
    d = (g.diff().abs() / kap)
    duz = (d.fillna(1.0) <= duzluk_esik) | (d.shift(-1).fillna(1.0) <= duzluk_esik)
    aday = dusuk & duz & (g > 0.02 * kap)  # sıfır = kesinti, kısıt değil
    grup = (aday != aday.shift()).cumsum()
    uzunluk = aday.groupby(grup).transform("size")
    return (aday & (uzunluk >= min_ardisik)).reindex(gercek.index, fill_value=False)


def kalibrasyon_maskesi(gercek: pd.Series, beklenen: pd.Series | None = None, tavan_kw: float | None = None,
                        kalite_bayragi: pd.Series | None = None) -> pd.DataFrame:
    """Kolonlar: clipping, curtailment, kalite_kotu, kullan (kalibrasyon/metrik için True)."""
    df = pd.DataFrame(index=gercek.index)
    df["clipping"] = clipping_maskesi(gercek, tavan_kw)
    df["curtailment"] = curtailment_maskesi(gercek, beklenen, kapasite=tavan_kw) if beklenen is not None else False
    df["kalite_kotu"] = kalite_bayragi.reindex(gercek.index).fillna(False) if kalite_bayragi is not None else False
    df["kullan"] = ~(df["clipping"] | df["curtailment"] | df["kalite_kotu"]) & gercek.notna()
    return df


def kisitsiz_senaryo(gercek: pd.Series, beklenen: pd.Series, maske: pd.DataFrame) -> pd.DataFrame:
    """Kısıt saatlerinde beklenenle değiştirilmiş seri + kayıp (kWh) muhasebesi."""
    k = maske["clipping"] | maske["curtailment"]
    senaryo = gercek.where(~k, beklenen.reindex(gercek.index))
    kayip = (senaryo - gercek).clip(lower=0.0).where(k, 0.0)
    return pd.DataFrame({"gercek": gercek, "kisitsiz": senaryo, "kayip": kayip})
