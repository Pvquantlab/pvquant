"""Işınım modelleri: GHI/DHI/DNI ayrıştırma ve POA transposition.

Bu modül iki ana adımı yönetir:

1. **Ayrıştırma (Decomposition)**: Açık meteoroloji servisleri (Open-Meteo gibi)
   genellikle yalnızca yatay küresel ışınım (GHI) verir. Modül düzlemine
   ışınım hesaplayabilmek için bunu yatay difüz (DHI) ve normal doğrudan (DNI)
   bileşenlerine ayırmamız gerekir.

2. **Transposition**: DHI/DNI/GHI'den, eğimli modül düzlemine düşen toplam
   ışınımı (POA — Plane of Array) hesaplarız.

Referanslar:
    Erbs, D.G., Klein, S.A., Duffie, J.A. (1982). Estimation of the diffuse
        radiation fraction for hourly, daily and monthly-average global
        radiation. Solar Energy 28(4), 293-302.

    Perez, R., Ineichen, P., Seals, R., Michalsky, J., Stewart, R. (1990).
        Modeling daylight availability and irradiance components from direct
        and global irradiance. Solar Energy 44(5), 271-289.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import pvlib


@dataclass(frozen=True)
class POAComponents:
    """POA (Plane of Array) ışınım bileşenleri.

    Tüm değerler W/m² cinsindendir ve zaman serileridir (saatlik veya sub-saatlik).

    Attributes:
        global_: Toplam POA ışınımı (beam + sky_diffuse + ground_diffuse).
        beam: Doğrudan ışınım bileşeni (DNI · cos(AOI)).
        sky_diffuse: Gökyüzü difüz bileşeni (Perez modeli).
        ground_diffuse: Zemin yansıması bileşeni (izotropik, albedo'ya bağlı).
        aoi: Geliş açısı (Angle of Incidence), derece.
    """

    global_: pd.Series
    beam: pd.Series
    sky_diffuse: pd.Series
    ground_diffuse: pd.Series
    aoi: pd.Series


def decompose_ghi_erbs(
    ghi: pd.Series,
    solar_zenith: pd.Series,
    times: pd.DatetimeIndex,
) -> pd.DataFrame:
    """GHI'yi Erbs (1982) modeli ile DHI ve DNI bileşenlerine ayrıştırır.

    Erbs modeli, açıklık endeksine (k_t) dayalı parçalı bir polinom
    ilişki kullanarak difüz oranı (DF = DHI/GHI) hesaplar:

    .. code::

        DF = 1.0 - 0.09*k_t                                    , k_t <= 0.22
        DF = 0.9511 - 0.1604*k_t + 4.388*k_t^2
             - 16.638*k_t^3 + 12.336*k_t^4                     , 0.22 < k_t <= 0.80
        DF = 0.165                                             , k_t > 0.80

    Args:
        ghi: Yatay küresel ışınım, W/m².
        solar_zenith: Güneş zenit açısı, derece (0 = tepe noktası, 90 = ufuk).
        times: Tarih-saat indeksi (gün/yıl bilgisi için).

    Returns:
        DataFrame with columns ['ghi', 'dhi', 'dni', 'kt']:
            - ghi: input GHI (geçirgen)
            - dhi: difüz yatay ışınım, W/m²
            - dni: doğrudan normal ışınım, W/m²
            - kt: açıklık endeksi (dimensionless)

    Referans:
        Erbs, D.G., Klein, S.A., Duffie, J.A. (1982). Solar Energy 28(4), 293-302.

    Notlar:
        - pvlib.irradiance.erbs() doğrudan orijinal makaleyi uygular.
        - cos(zenith) sayısal stabilitesi için min_cos_zenith=0.065 varsayılır.
        - k_t > 0.80 bölgesinde sabit DF=0.165 kullanılır; çok güneşli iklimlerde
          (Konya, Şanlıurfa) en parlak saatlerde DNI biraz az tahmin edilebilir.
          Daha doğru sonuç için `decompose_ghi_disc()` kullanılabilir.
    """
    result = pvlib.irradiance.erbs(ghi=ghi, zenith=solar_zenith, datetime_or_doy=times)
    return pd.DataFrame(
        {
            "ghi": ghi,
            "dhi": result["dhi"],
            "dni": result["dni"],
            "kt": result["kt"],
        },
        index=times,
    )


def decompose_ghi_disc(
    ghi: pd.Series,
    solar_zenith: pd.Series,
    times: pd.DatetimeIndex,
    pressure: pd.Series | float = 101325.0,
) -> pd.DataFrame:
    """GHI'yi DISC (Maxwell 1987) modeli ile bileşenlerine ayrıştırır.

    DISC, hava kütlesini de hesaba kattığı için sub-saatlik (15dk, 10dk) veride
    Erbs'den daha doğru DNI üretir.

    Args:
        ghi: Yatay küresel ışınım, W/m².
        solar_zenith: Güneş zenit açısı, derece.
        times: Tarih-saat indeksi.
        pressure: Atmosfer basıncı, Pa (varsayılan deniz seviyesi).

    Returns:
        DataFrame with columns ['ghi', 'dhi', 'dni', 'kt'].

    Referans:
        Maxwell, E.L. (1987). A Quasi-Physical Model for Converting Hourly Global
            Horizontal to Direct Normal Insolation. SERI/TR-215-3087.
    """
    result = pvlib.irradiance.disc(
        ghi=ghi, solar_zenith=solar_zenith, datetime_or_doy=times, pressure=pressure
    )
    dni = result["dni"]
    # DHI'yi closure equation ile geri çıkar: GHI = DHI + DNI * cos(zenith)
    import numpy as np
    cos_z = np.cos(np.radians(solar_zenith))
    dhi = (ghi - dni * cos_z).clip(lower=0)
    return pd.DataFrame(
        {"ghi": ghi, "dhi": dhi, "dni": dni, "kt": result["kt"]}, index=times
    )


def transpose_perez(
    surface_tilt: float,
    surface_azimuth: float,
    solar_zenith: pd.Series,
    solar_azimuth: pd.Series,
    dni: pd.Series,
    ghi: pd.Series,
    dhi: pd.Series,
    dni_extra: pd.Series,
    airmass: pd.Series,
    albedo: float | pd.Series = 0.25,
) -> POAComponents:
    """Perez (1990) transposition modeli ile POA bileşenlerini hesaplar.

    Perez modeli gökyüzü difüz ışınımını üç parçaya ayırır:
    izotropik arka plan, güneş çevresi parlaması (F1) ve ufuk bandı (F2).
    Saatlik bazda izotropik modellere kıyasla %5-10 daha düşük hata verir.

    .. code::

        POA_sky_diffuse = DHI * [ (1 - F1) * (1 + cos(beta)) / 2
                                  + F1 * a / b
                                  + F2 * sin(beta) ]
        POA_beam        = DNI * cos(AOI)
        POA_ground      = GHI * albedo * (1 - cos(beta)) / 2

    Args:
        surface_tilt: Modül eğim açısı, derece (0 = yatay, 90 = dik).
        surface_azimuth: Modül azimut açısı, derece (180 = güney - kuzey yarımküre için).
        solar_zenith: Güneş zenit açısı zaman serisi, derece.
        solar_azimuth: Güneş azimut açısı zaman serisi, derece.
        dni: Doğrudan normal ışınım, W/m².
        ghi: Yatay küresel ışınım, W/m².
        dhi: Yatay difüz ışınım, W/m².
        dni_extra: Atmosfer-üstü ışınım (eccentricity için), W/m².
        airmass: Bağıl hava kütlesi.
        albedo: Saha albedosu (0.25 toprak için tipik).

    Returns:
        POAComponents dataclass with beam, sky_diffuse, ground_diffuse, global, aoi.

    Referans:
        Perez, R. et al. (1990). Solar Energy 44(5), 271-289.

    Notlar:
        - "allsitescomposite1990" katsayı seti kullanılır (en yaygın).
        - Sub-saatlik veride pvlib.irradiance.perez_driesse() tercih edilebilir
          (Driesse-Jensen-Perez 2024 sürekli versiyonu).
    """
    aoi = pvlib.irradiance.aoi(
        surface_tilt=surface_tilt,
        surface_azimuth=surface_azimuth,
        solar_zenith=solar_zenith,
        solar_azimuth=solar_azimuth,
    )

    poa = pvlib.irradiance.get_total_irradiance(
        surface_tilt=surface_tilt,
        surface_azimuth=surface_azimuth,
        solar_zenith=solar_zenith,
        solar_azimuth=solar_azimuth,
        dni=dni,
        ghi=ghi,
        dhi=dhi,
        dni_extra=dni_extra,
        airmass=airmass,
        albedo=albedo,
        model="perez",
        model_perez="allsitescomposite1990",
    )

    # v2.156 (uydurma-0 avı, 18 Ağu): fillna(0) iki FARKLI NaN'ı tek fırçayla
    # boyuyordu — Perez'in gece/geometri NaN'ı (0 doğru) ile GİRDİ-EKSİK NaN'ı
    # (open-meteo radyasyon ufku ötesi saatler). İkincisini 0'a çevirmek
    # şartnamenin "veri yoksa '—', asla uydurma 0" kuralının ihlaliydi:
    # canlıda son ufuk günü 'üretim 0' diye rapora aktı. Girdisi eksik saat
    # eksik KALIR (NaN); zincir onu None olarak taşır, kimse 0 uydurmaz.
    _girdili = ghi.notna()
    return POAComponents(
        global_=poa["poa_global"].fillna(0).clip(lower=0).where(_girdili),
        beam=poa["poa_direct"].fillna(0).clip(lower=0).where(_girdili),
        sky_diffuse=poa["poa_sky_diffuse"].fillna(0).clip(lower=0).where(_girdili),
        ground_diffuse=poa["poa_ground_diffuse"].fillna(0).clip(lower=0).where(_girdili),
        aoi=aoi.fillna(90),
    )


def solar_position(
    times: pd.DatetimeIndex, latitude: float, longitude: float, altitude: float = 0
) -> pd.DataFrame:
    """Güneş pozisyonunu hesaplar (NREL SPA algoritması).

    Args:
        times: UTC veya tz-aware zaman serisi.
        latitude: Enlem, derece (kuzey pozitif).
        longitude: Boylam, derece (doğu pozitif).
        altitude: Rakım, metre.

    Returns:
        DataFrame with columns ['apparent_zenith', 'zenith', 'apparent_elevation',
        'elevation', 'azimuth', 'equation_of_time'].

    Referans:
        Reda, I., Andreas, A. (2004). Solar Position Algorithm for Solar Radiation
            Applications. NREL/TP-560-34302.
    """
    return pvlib.solarposition.get_solarposition(
        time=times, latitude=latitude, longitude=longitude, altitude=altitude
    )


def extra_radiation_and_airmass(
    times: pd.DatetimeIndex, solar_zenith: pd.Series
) -> tuple[pd.Series, pd.Series]:
    """Perez modeli için gerekli yardımcı büyüklükleri hesaplar.

    Returns:
        (dni_extra, airmass): atmosfer-üstü ışınım (W/m²) ve bağıl hava kütlesi.
    """
    dni_extra = pvlib.irradiance.get_extra_radiation(times)
    airmass_rel = pvlib.atmosphere.get_relative_airmass(solar_zenith)
    return dni_extra, airmass_rel
