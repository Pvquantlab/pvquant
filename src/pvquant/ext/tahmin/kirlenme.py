"""Soiling (kirlenme) ve kar örtüsü kayıpları — saha profiline göre açılan çarpanlar.

Soiling: HSU (Coello & Boyle 2019; pvlib.soiling.hsu) PM2.5/PM10 + yağış temizlemesiyle;
Kimber (2006) sabit günlük birikim + yağış eşiği. Kar: NREL (Marion 2013; pvlib.snow)
örtü oranı ve kayıp; kar derinliği/kar yağışı ve sıcaklık/ışınım ile erime.
Çıktı: soiling_ratio (0–1) ve snow_loss (0–1) saatlik seriler; POA'ya çarpan olarak uygulanır.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pvlib


def soiling_hsu(yagis_mm: pd.Series, pm2_5: pd.Series, pm10: pd.Series, tilt: float, temizleme_esik_mm: float = 1.0,
                depo_hizi_pm2_5: float = 0.0009, depo_hizi_pm10: float = 0.004) -> pd.Series:
    """HSU modeli; girdiler saatlik (yağış mm/saat, PM µg/m³). Döner soiling_ratio (1 = temiz)."""
    return pvlib.soiling.hsu(yagis_mm, temizleme_esik_mm, tilt, pm2_5.astype(float), pm10.astype(float),
                             depo_velocity={"2_5": depo_hizi_pm2_5, "10": depo_hizi_pm10})


def soiling_kimber(yagis_mm: pd.Series, gunluk_kayip: float = 0.0015, tavan: float = 0.30, temizleme_esik_mm: float = 6.0,
                   yagis_gecikme_gun: int = 0, ilk_gunler_temiz: int = 0) -> pd.Series:
    """Kimber: her gün gunluk_kayip kadar kayıp birikir (tavana kadar), yağış ≥ eşik olunca sıfırlanır.
    pvlib KAYIP oranı döndürür; burada soiling_ratio = 1 − kayıp olarak çevrilir (HSU ile aynı sözleşme)."""
    return 1.0 - pvlib.soiling.kimber(yagis_mm, cleaning_threshold=temizleme_esik_mm, soiling_loss_rate=gunluk_kayip,
                                grace_period=yagis_gecikme_gun, max_soiling=tavan, initial_soiling=0.0,
                                rain_accum_period=24)


def kar_ortusu(kar_yagisi_cm_saat: pd.Series, poa: pd.Series, temp_air: pd.Series, tilt: float, hucre_sayisi_yukseklik: int = 12,
               esik_cm_saat: float = 1.0) -> pd.DataFrame:
    """NREL kar modeli: örtü oranı (0–1) ve DC kayıp oranı. Kar yağışı ≥ eşik → tam örtü; erime ışınım+sıcaklıkla."""
    tam = pvlib.snow.fully_covered_nrel(kar_yagisi_cm_saat, threshold_snowfall=esik_cm_saat)
    ortu = pvlib.snow.coverage_nrel(kar_yagisi_cm_saat, poa, temp_air, tilt, threshold_snowfall=esik_cm_saat)
    kayip = pvlib.snow.dc_loss_nrel(ortu, num_strings=1) if hasattr(pvlib.snow, "dc_loss_nrel") else ortu
    return pd.DataFrame({"tam_ortu": tam, "ortu_orani": ortu, "kayip_orani": kayip})


def kirlenme_carpani(soiling_ratio: pd.Series | None, kar_kayip: pd.Series | None, index: pd.DatetimeIndex) -> pd.Series:
    """Birleşik çarpan: (soiling_ratio) × (1 − kar_kayip); eksikler 1 kabul edilir."""
    c = pd.Series(1.0, index=index)
    if soiling_ratio is not None:
        c *= soiling_ratio.reindex(index).fillna(1.0).clip(0, 1)
    if kar_kayip is not None:
        c *= (1 - kar_kayip.reindex(index).fillna(0.0).clip(0, 1))
    return c


def soiling_tahmini_verilerden(gercek: pd.Series, beklenen_temiz: pd.Series, pencere_gun: int = 14, yagis_mm: pd.Series | None = None,
                               esik_mm: float = 5.0) -> pd.Series:
    """Ölçümden ampirik soiling: günlük (gerçek/beklenen) oranının kayan medyanı; yağış günlerinde sıfırlanan trend.
    Beklenen 'temiz' sistem çıktısı (kalibre fizik) olmalı."""
    oran = (gercek.resample("D").sum() / beklenen_temiz.resample("D").sum()).clip(0.5, 1.1)
    med = oran.rolling(pencere_gun, min_periods=5).median()
    if yagis_mm is not None:
        gunluk_yagis = yagis_mm.resample("D").sum().reindex(med.index).fillna(0)
        med = med.where(gunluk_yagis < esik_mm, 1.0)
    return med.clip(upper=1.0)
