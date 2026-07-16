"""Bifacial katkı modelleri.

İki yaklaşım sunulur:

1. **Basit çarpımsal model** (mevcut tez yaklaşımı): Saatlik üretim sabit bir
   çarpan (1 + BG·BF·A) ile artırılır. BG saha verisinden geri kalibre edilir.

2. **Infinite sheds** (Mikofski 2019 / Marion 2017): View-factor tabanlı,
   saatlik bazda arka yüz ışınımını ayrı hesaplar. Büyük arazi GES için.

Referanslar:
    Marion, B. et al. (2017). A Practical Irradiance Model for Bifacial PV
        Modules. 44th IEEE PVSC, 1537-1543.

    Mikofski, M. et al. (2019). Bifacial Performance Modeling in Large Arrays.
        46th IEEE PVSC, 1282-1287.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import pvlib


# -----------------------------------------------------------------------------
# 1) Basit çarpımsal model (tez yaklaşımı)
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class SimpleBifacialParams:
    """Basit çarpımsal bifacial model parametreleri.

    Net bifacial katkı: BG · BF · A

    Attributes:
        bg: Geometrik arka yüz / ön yüz ışınım oranı.
            Modülün eğimi, yüksekliği, sıra aralığı (GCR) ve view factor'in
            net sonucu. Tipik 0.10-0.40. Saha verisinden geri hesaplanabilir
            Bir bifacial referans santralda gözlenen BG = 0.347 (bkz. tez Bölüm 3.3.7).
        bf: Bifacial faktör (datasheet'ten). Arka yüz verimi / ön yüz verimi.
            Tipik 0.65-0.85. Elin ELNSM72M-HC-BF: BF = 0.70.
        albedo: Saha albedosu. Sabit veya saatlik/aylık seri olabilir.
            - Kuru toprak: 0.20-0.30
            - Nemli toprak: 0.10-0.15
            - Beton: 0.30-0.35
            - Çim: 0.20-0.25
            - Yeni kar: 0.75-0.90
    """

    bg: float = 0.347
    bf: float = 0.70
    albedo: float = 0.25

    @property
    def net_gain_fraction(self) -> float:
        """Net bifacial katkı oranı (BG · BF · A).

        Çarpan: (1 + net_gain_fraction).
        """
        return self.bg * self.bf * self.albedo

    @property
    def multiplier(self) -> float:
        """Çarpımsal bifacial katsayı: (1 + BG·BF·A)."""
        return 1.0 + self.net_gain_fraction


def simple_bifacial_multiplier(params: SimpleBifacialParams) -> float:
    """Basit bifacial çarpan, (1 + BG·BF·A).

    Sabit, saatlik üretime doğrudan uygulanır.

    Args:
        params: SimpleBifacialParams.

    Returns:
        Çarpan değeri (örn. 1.0607).
    """
    return params.multiplier


def back_solve_bg_from_scada(
    measured_eta_rel: pd.Series,
    eta_irradiance: pd.Series,
    eta_temperature: pd.Series,
    bf: float,
    albedo: float | pd.Series,
    irradiance_weights: pd.Series | None = None,
) -> float:
    """SCADA verisinden BG (geometrik arka yüz oranı) geri hesabı.

    Tezin Bölüm 3.3.7'sindeki yöntem. Denklem 3.8:

    .. code::

        (BG · BF · A)_saatlik = η_rel,gerçek / (η_ışınım · η_sıcaklık) - 1

    Sonra ışınım-ağırlıklı ortalama alınır ve BF, A bilinen değerlerle BG izole edilir.

    Args:
        measured_eta_rel: SCADA üretiminden geri hesaplanan gerçek bağıl verim.
            (E_gerçek / [P_nom · (G/G0) · η_BoS])
        eta_irradiance: Modelin ışınım terimi (1 + c1·lnG + c2·(lnG)²).
        eta_temperature: Modelin sıcaklık terimi (1 + γ·(T-T_ref)).
        bf: Bifacial faktör (datasheet).
        albedo: Saha albedosu.
        irradiance_weights: Ağırlık olarak kullanılacak ışınım serisi
            (varsayılan: tüm saatler eşit).

    Returns:
        Geri hesaplanmış BG değeri (0-0.5 arası tipik).

    Referans:
    Bahsedilen tezde referans santral için 2794 geçerli saat üzerinden
        BG = 0.347 olarak bulunmuştur.
    """
    net_gain_hourly = measured_eta_rel / (eta_irradiance * eta_temperature) - 1.0

    if irradiance_weights is None:
        net_gain_mean = net_gain_hourly.mean()
    else:
        # Işınım ağırlıklı ortalama
        net_gain_mean = (net_gain_hourly * irradiance_weights).sum() / irradiance_weights.sum()

    # Ortalama albedo (sabit ise zaten skaler)
    avg_albedo = float(albedo.mean()) if hasattr(albedo, "mean") else float(albedo)

    bg = net_gain_mean / (bf * avg_albedo)
    return float(bg)


# -----------------------------------------------------------------------------
# 2) Infinite sheds — view factor tabanlı (pvlib wrap)
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class InfiniteShedsGeometry:
    """Infinite sheds modeli için saha geometrisi.

    Attributes:
        gcr: Ground Coverage Ratio = modül genişliği / sıra arası. 0-1 arası.
            Tipik arazi GES: 0.30-0.50. Yüksek GCR daha az arka yüz katkısı.
        height: Modül alt kenarının yerden yüksekliği, metre. Tipik 1.0-2.5 m.
        pitch: Sıralar arası mesafe (metre), GCR'den hesaplanabilir.
    """

    gcr: float
    height: float = 1.5
    pitch: float | None = None


def back_irradiance_infinite_sheds(
    surface_tilt: float,
    surface_azimuth: float,
    solar_zenith: pd.Series,
    solar_azimuth: pd.Series,
    ghi: pd.Series,
    dhi: pd.Series,
    dni: pd.Series,
    albedo: float | pd.Series,
    geometry: InfiniteShedsGeometry,
    bifaciality: float = 0.70,
) -> pd.DataFrame:
    """Infinite sheds modeli ile ön + arka yüz POA ışınımı.

    Marion (2017) + Mikofski (2019). Sıralar paralel, eşit aralıklı ve sonsuz
    uzun varsayılır; satır sonu etkileri ihmal edilir.

    Args:
        surface_tilt: Modül eğim açısı, derece.
        surface_azimuth: Modül azimut açısı, derece.
        solar_zenith: Güneş zenit zaman serisi, derece.
        solar_azimuth: Güneş azimut zaman serisi, derece.
        ghi: Yatay küresel ışınım, W/m².
        dhi: Yatay difüz, W/m².
        dni: Doğrudan normal, W/m².
        albedo: Saha albedosu (skaler veya zaman serisi).
        geometry: InfiniteShedsGeometry (gcr, height).
        bifaciality: Modülün arka yüz / ön yüz verim oranı.

    Returns:
        DataFrame with columns:
            - poa_global_front
            - poa_global_back
            - poa_global_bifacial (= front + bifaciality * back)

    Referans:
        Mikofski, M. et al. (2019). 46th IEEE PVSC, 1282-1287.
        Marion, B. et al. (2017). 44th IEEE PVSC, 1537-1543.
    """
    # pvlib API'sinde pitch kullanır; GCR'den çıkar
    pitch = geometry.pitch or (1.0 / geometry.gcr)  # 1m genişlik varsayımı

    result = pvlib.bifacial.infinite_sheds.get_irradiance(
        surface_tilt=surface_tilt,
        surface_azimuth=surface_azimuth,
        solar_zenith=solar_zenith,
        solar_azimuth=solar_azimuth,
        gcr=geometry.gcr,
        height=geometry.height,
        pitch=pitch,
        ghi=ghi,
        dhi=dhi,
        dni=dni,
        albedo=albedo,
        bifaciality=bifaciality,
    )
    # pvlib zaten birleşik 'poa_global' verir
    return pd.DataFrame(
        {
            "poa_global_front": result["poa_front"],
            "poa_global_back": result["poa_back"],
            "poa_global_bifacial": result["poa_global"],
        },
        index=ghi.index,
    )
