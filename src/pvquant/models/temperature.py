"""Hücre sıcaklığı modelleri.

PV modülünün verimi sıcaklıkla doğrusal olarak düşer (her +1°C için yaklaşık
−%0.30 ila −%0.45 güç kaybı). Bu yüzden hücre sıcaklığını ne kadar doğru
tahmin edersek, güç tahmini de o kadar doğru olur.

Üç model sunulur:

1. **NOCT** (en basit): Datasheet'teki NOCT değeri kullanılır, rüzgar etkisi
   hesaba katılmaz. Mevcut Barhdadi & Bennis tezinde bu model kullanılmıştır.

2. **Faiman** (önerilen): Rüzgar hızını da hesaba katar, IEC 61853-2/-3
   standartlarında resmi olarak benimsenmiştir.

3. **SAPM thermal** (ileri): Sandia'nın iki-aşamalı ampirik modeli, montaj
   tipine göre kalibre edilmiş parametre setleri sunar.

Referanslar:
    Faiman, D. (2008). Assessing the outdoor operating temperature of photovoltaic
        modules. Progress in Photovoltaics 16(4), 307-315.

    King, D.L., Boyson, W.E., Kratochvil, J.A. (2004). Photovoltaic Array
        Performance Model. SAND2004-3535.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd
import pvlib


# -----------------------------------------------------------------------------
# Faiman parametre setleri (literatür ve IEC 61853 verisi)
# -----------------------------------------------------------------------------

FAIMAN_PARAMS: dict[str, dict[str, float]] = {
    # Faiman 2008 orijinal: Negev çölü, 7 silikon modül, açık rack, 30.9° eğim.
    # pvlib default değerleri.
    "open_rack_default": {"u0": 25.0, "u1": 6.84},
    # IEC 61853 testlerinde cam-cam modüller için
    "glass_glass_open_rack": {"u0": 30.02, "u1": 6.28},
    # Çatı, hava akışlı yarı entegre
    "roof_ventilated": {"u0": 20.0, "u1": 4.0},
    # Tam entegre BIPV (rüzgar etkisi yok)
    "bipv_integrated": {"u0": 15.0, "u1": 0.0},
}


# -----------------------------------------------------------------------------
# 1) NOCT — en basit
# -----------------------------------------------------------------------------

def cell_temperature_noct(
    poa_global: pd.Series,
    temp_ambient: pd.Series,
    noct: float = 45.0,
) -> pd.Series:
    """NOCT (Normal Operating Cell Temperature) modeliyle hücre sıcaklığı.

    .. code::

        T_cell = T_amb + ((NOCT - 20) / 800) * G

    NOCT, modül datasheet'inde verilen ve şu koşullardaki hücre sıcaklığıdır:
    G = 800 W/m², T_amb = 20°C, WS = 1 m/s, açık devre.
    Tipik c-Si modüller için NOCT = 44-48°C.

    Args:
        poa_global: Modül düzlemine gelen toplam ışınım, W/m².
        temp_ambient: Ortam sıcaklığı, °C.
        noct: Datasheet NOCT değeri, °C. Varsayılan 45°C.

    Returns:
        Hücre sıcaklığı zaman serisi, °C.

    Referans:
        IEC 61215 / Modül datasheet.

    Notlar:
        Bu model hızlı ve datasheet harici veri istemez ama:
        - Rüzgar etkisini hesaba katmaz (yaz öğleninde aşırı tahmin yapabilir).
        - Montaj tipini (zemin/çatı/BIPV) ayırt etmez.
        Rüzgar verisi varsa Faiman tercih edilmeli.
    """
    return temp_ambient + ((noct - 20.0) / 800.0) * poa_global


# -----------------------------------------------------------------------------
# 2) Faiman — rüzgar dahil (önerilen)
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class FaimanParams:
    """Faiman modeli ısı kaybı katsayıları.

    Attributes:
        u0: Rüzgardan bağımsız ısı kaybı katsayısı, W/(m²·K).
        u1: Rüzgara bağlı ısı kaybı katsayısı, W·s/(m³·K).
    """

    u0: float = 25.0
    u1: float = 6.84

    @classmethod
    def from_preset(cls, preset: str) -> FaimanParams:
        """Önceden tanımlı parametre setini yükler."""
        if preset not in FAIMAN_PARAMS:
            available = ", ".join(FAIMAN_PARAMS.keys())
            raise ValueError(f"Bilinmeyen preset '{preset}'. Mevcut: {available}")
        return cls(**FAIMAN_PARAMS[preset])


def cell_temperature_faiman(
    poa_global: pd.Series,
    temp_ambient: pd.Series,
    wind_speed: pd.Series | float = 1.0,
    params: FaimanParams | None = None,
) -> pd.Series:
    """Faiman (2008) modeli ile hücre/modül sıcaklığı.

    .. code::

        T_cell = T_amb + G / (U0 + U1 * WS)

    Faiman modeli IEC 61853-2 ve IEC 61853-3 standartlarında resmi olarak
    benimsenmiştir. Açık arazi GES'lerinde NOCT'a göre %3-8 daha düşük
    yıllık MAPE verir.

    Args:
        poa_global: Modül düzlemine gelen toplam ışınım, W/m².
        temp_ambient: Ortam sıcaklığı, °C.
        wind_speed: Modül yüksekliğindeki rüzgar hızı, m/s. Varsayılan 1.0
            (NOCT koşullarındaki rüzgar). Open-Meteo gibi servisler 10m
            yüksekliğinden rüzgar verir; modül yüksekliğine çevirmek için
            `adjust_wind_speed_log_profile()` kullanın.
        params: FaimanParams. Verilmezse açık rack default (U0=25, U1=6.84).

    Returns:
        Hücre sıcaklığı zaman serisi, °C.

    Referans:
        Faiman, D. (2008). Progress in Photovoltaics 16(4), 307-315.
        DOI: 10.1002/pip.813.

    Notlar:
        - IEC 61853 kullanımında modül ile hücre sıcaklığı ayırt edilmez.
        - Uzun dalga radyasyon dahil versiyon için faiman_rad (Driesse uzantısı).
    """
    p = params or FaimanParams()
    return pvlib.temperature.faiman(
        poa_global=poa_global,
        temp_air=temp_ambient,
        wind_speed=wind_speed,
        u0=p.u0,
        u1=p.u1,
    )


def adjust_wind_speed_log_profile(
    wind_speed_10m: pd.Series,
    target_height: float = 2.5,
    roughness_length: float = 0.03,
) -> pd.Series:
    """10m rüzgar hızını modül yüksekliğine logaritmik profil ile düzeltir.

    .. code::

        WS_modul = WS_10m * ln(z_modul / z0) / ln(10 / z0)

    Args:
        wind_speed_10m: 10 m yüksekliğindeki rüzgar hızı, m/s
            (Open-Meteo, NASA POWER gibi servislerin verdiği).
        target_height: Modül yüksekliği, m. Tipik 2-3 m.
        roughness_length: Yüzey pürüzlülük uzunluğu, m.
            - Kısa ot / toprak: 0.03
            - Uzun ot / tarla: 0.10
            - Köy / dağınık ağaç: 0.30
            - Şehir: 1.0+

    Returns:
        Modül yüksekliğindeki rüzgar hızı zaman serisi, m/s.
    """
    if target_height <= roughness_length:
        raise ValueError(
            f"target_height ({target_height}) > roughness_length ({roughness_length}) olmalı"
        )
    scaling = np.log(target_height / roughness_length) / np.log(10.0 / roughness_length)
    return (wind_speed_10m * scaling).clip(lower=0)


# -----------------------------------------------------------------------------
# 3) SAPM Thermal — Sandia ampirik
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class SAPMThermalParams:
    """Sandia thermal model parametreleri.

    Attributes:
        a: Üst sınır temp katsayısı (boyutsuz).
        b: Rüzgar etki katsayısı (s/m).
        delta_t: Hücre-modül sıcaklık farkı 1000 W/m² koşulunda, °C.
    """

    a: float
    b: float
    delta_t: float


# pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS["sapm"] içinden
SAPM_PRESETS: dict[str, SAPMThermalParams] = {
    "open_rack_glass_glass": SAPMThermalParams(a=-3.47, b=-0.0594, delta_t=3.0),
    "open_rack_glass_polymer": SAPMThermalParams(a=-3.56, b=-0.0750, delta_t=3.0),
    "close_mount_glass_glass": SAPMThermalParams(a=-2.98, b=-0.0471, delta_t=1.0),
    "insulated_back_glass_polymer": SAPMThermalParams(a=-2.81, b=-0.0455, delta_t=0.0),
}


def cell_temperature_sapm(
    poa_global: pd.Series,
    temp_ambient: pd.Series,
    wind_speed: pd.Series | float,
    params: SAPMThermalParams | str = "open_rack_glass_polymer",
) -> pd.Series:
    """Sandia (King 2004) thermal modeli ile hücre sıcaklığı.

    İki aşamalı:

    .. code::

        T_module = G * exp(a + b * WS) + T_amb
        T_cell   = T_module + (G / 1000) * delta_T

    Args:
        poa_global: Modül düzlemine gelen toplam ışınım, W/m².
        temp_ambient: Ortam sıcaklığı, °C.
        wind_speed: Rüzgar hızı, m/s.
        params: SAPMThermalParams veya preset adı (string).

    Returns:
        Hücre sıcaklığı zaman serisi, °C.

    Referans:
        King, D.L., Boyson, W.E., Kratochvil, J.A. (2004). SAND2004-3535.
    """
    if isinstance(params, str):
        if params not in SAPM_PRESETS:
            available = ", ".join(SAPM_PRESETS.keys())
            raise ValueError(f"Bilinmeyen SAPM preset '{params}'. Mevcut: {available}")
        params = SAPM_PRESETS[params]

    return pvlib.temperature.sapm_cell(
        poa_global=poa_global,
        temp_air=temp_ambient,
        wind_speed=wind_speed,
        a=params.a,
        b=params.b,
        deltaT=params.delta_t,
    )


# -----------------------------------------------------------------------------
# Genel dispatcher
# -----------------------------------------------------------------------------

ThermalModel = Literal["noct", "faiman", "sapm"]


def cell_temperature(
    model: ThermalModel,
    poa_global: pd.Series,
    temp_ambient: pd.Series,
    wind_speed: pd.Series | float | None = None,
    **kwargs,
) -> pd.Series:
    """Genel hücre sıcaklığı dispatcher'ı.

    Args:
        model: 'noct', 'faiman', veya 'sapm'.
        poa_global: POA ışınımı, W/m².
        temp_ambient: Ortam sıcaklığı, °C.
        wind_speed: Rüzgar hızı, m/s (NOCT için gereksiz).
        **kwargs: Modele özel parametreler (noct, params, vs).

    Returns:
        Hücre sıcaklığı zaman serisi, °C.
    """
    if model == "noct":
        noct = kwargs.get("noct", 45.0)
        return cell_temperature_noct(poa_global, temp_ambient, noct=noct)
    if model == "faiman":
        if wind_speed is None:
            wind_speed = 1.0
        params = kwargs.get("params")
        return cell_temperature_faiman(poa_global, temp_ambient, wind_speed, params=params)
    if model == "sapm":
        if wind_speed is None:
            raise ValueError("SAPM modeli rüzgar hızı gerektirir")
        params = kwargs.get("params", "open_rack_glass_polymer")
        return cell_temperature_sapm(poa_global, temp_ambient, wind_speed, params=params)
    raise ValueError(f"Bilinmeyen model: {model}")
