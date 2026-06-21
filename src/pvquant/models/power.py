"""DC güç modelleri.

Üç yaklaşım sunulur, hepsi vektörize ve aynı arayüze sahip:

1. **PVWatts v5** (Dobos 2014): Tek doğrusal sıcaklık katsayısı, hızlı.
2. **Skoplaki-Palyvos** (2009): PVWatts ile matematiksel olarak eş, β/γ farklı.
3. **Barhdadi-Bennis** (2012): Logaritmik düşük-ışınım terimi + sıcaklık. Mevcut
   tezde kullanılan model.

Tüm modeller şu varsayım üzerine kuruludur: STC referansta (G₀=1000 W/m², T_ref=25°C)
sistem nominal güç (P_nom) üretir, başka koşullarda bağıl verim η_rel ile çarpılır.

.. code::

    P_DC = P_nom * (G / G_0) * η_rel(G, T_cell)

Referanslar:
    Skoplaki, E., Palyvos, J.A. (2009). Solar Energy 83(5), 614-624.
    Dobos, A.P. (2014). PVWatts Version 5 Manual. NREL/TP-6A20-62641.
    Barhdadi, A., Bennis, M. (2012). African Review of Physics 7, 337-344.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

# -----------------------------------------------------------------------------
# Sabitler
# -----------------------------------------------------------------------------

G_STC: float = 1000.0  # STC ışınım, W/m²
T_STC: float = 25.0    # STC sıcaklık, °C


# Skoplaki-Palyvos 2009 Tablo 1'den tipik sıcaklık katsayıları (γ, 1/°C)
TYPICAL_GAMMA: dict[str, float] = {
    "mono_si": -0.0040,
    "multi_si": -0.0040,
    "topcon": -0.0028,    # Modern yüksek verim
    "hjt": -0.0026,       # En düşük sıcaklık duyarlılığı
    "a_si": -0.0015,
    "cdte": -0.0022,
    "cigs": -0.0032,
}


# -----------------------------------------------------------------------------
# 1) PVWatts v5
# -----------------------------------------------------------------------------

def pdc_pvwatts(
    poa_effective: pd.Series,
    temp_cell: pd.Series,
    p_dc0: float,
    gamma_pdc: float = -0.0040,
    temp_ref: float = T_STC,
) -> pd.Series:
    """PVWatts v5 (Dobos 2014) DC güç modeli.

    .. code::

        P_dc = (G_poa,eff / 1000) * P_dc0 * [ 1 + γ_pdc * (T_cell - T_ref) ]

    Args:
        poa_effective: Modül düzlemine etkili olarak gelen ışınım, W/m²
            (AOI yansıma kayıpları uygulanmış, spektral/kirlilik uygulanmamış).
        temp_cell: Hücre sıcaklığı, °C.
        p_dc0: STC altında nominal DC güç, W (veya kW). Çıktı aynı birimde döner.
        gamma_pdc: Sıcaklık katsayısı, 1/°C. Tipik c-Si için -0.0040.
            Modül teknolojisine göre `TYPICAL_GAMMA` sözlüğünden seçilebilir.
        temp_ref: Referans sıcaklık, °C. Varsayılan 25.

    Returns:
        DC güç zaman serisi, p_dc0 ile aynı birimde.

    Referans:
        Dobos, A.P. (2014). PVWatts Version 5 Manual. NREL/TP-6A20-62641.
    """
    return (poa_effective / G_STC) * p_dc0 * (1.0 + gamma_pdc * (temp_cell - temp_ref))


# -----------------------------------------------------------------------------
# 2) Skoplaki-Palyvos verim formu
# -----------------------------------------------------------------------------

def eta_skoplaki_palyvos(
    temp_cell: pd.Series,
    eta_ref: float,
    beta: float = 0.0040,
    temp_ref: float = T_STC,
) -> pd.Series:
    """Skoplaki-Palyvos (2009) bağıl verim formu.

    .. code::

        η = η_ref * [ 1 - β * (T_cell - T_ref) ]

    PVWatts ile matematiksel olarak eşdeğerdir; sadece parametrelendirme farkı:
    γ = -β / 1 (yaklaşık), yani PVWatts'taki gamma negatif, buradaki beta pozitif.

    Args:
        temp_cell: Hücre sıcaklığı, °C.
        eta_ref: STC referans verimi (0-1 arası).
        beta: Sıcaklık katsayısı, 1/°C (pozitif). c-Si için 0.0040-0.0045.
        temp_ref: Referans sıcaklık, °C.

    Returns:
        Bağıl verim zaman serisi (0-1 arası, T_cell=25 iken eta_ref).

    Referans:
        Skoplaki, E., Palyvos, J.A. (2009). Solar Energy 83(5), 614-624.
    """
    return eta_ref * (1.0 - beta * (temp_cell - temp_ref))


# -----------------------------------------------------------------------------
# 3) Barhdadi-Bennis — 3 parametreli bağıl verim (mevcut tez modeli)
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class BarhdadiBennisParams:
    """Barhdadi-Bennis bağıl verim modeli parametreleri.

    Attributes:
        c1: Logaritmik ışınım katsayısı. c-Si için 0.033 (Barhdadi & Bennis 2012).
        c2: Kuadratik logaritmik ışınım katsayısı. c-Si için -0.0092.
        gamma: Maksimum güç sıcaklık katsayısı, 1/°C. Datasheet'ten (örn. -0.0034).
    """

    c1: float = 0.033
    c2: float = -0.0092
    gamma: float = -0.0034


def eta_rel_barhdadi_bennis(
    poa_effective: pd.Series,
    temp_cell: pd.Series,
    params: BarhdadiBennisParams | None = None,
    g_ref: float = G_STC,
    temp_ref: float = T_STC,
) -> pd.Series:
    """Barhdadi-Bennis (2012) üç parametreli bağıl verim.

    .. code::

        η_rel = [ 1 + c1 * ln(G/G0) + c2 * (ln(G/G0))^2 ] * [ 1 + γ * (T_cell - T_ref) ]

    İlk parantez düşük ışınım koşullarındaki verim düşüşünü, ikinci parantez
    sıcaklık etkisini temsil eder. G = G_ref ve T_cell = T_ref iken η_rel = 1.

    Args:
        poa_effective: POA ışınımı (etkili), W/m².
        temp_cell: Hücre sıcaklığı, °C.
        params: BarhdadiBennisParams. Verilmezse c-Si default değerleri.
        g_ref: Referans ışınım, W/m².
        temp_ref: Referans sıcaklık, °C.

    Returns:
        Bağıl verim zaman serisi (G=G_ref, T=T_ref iken 1.0).

    Referans:
        Barhdadi, A., Bennis, M. (2012). African Review of Physics 7, 337-344.
        arXiv:1208.4325.

    Notlar:
        - G < 1 W/m² için log(0) durumundan kaçınmak adına bu saatlerde η_rel = 0.
        - Mevcut tezde c1=0.033, c2=-0.0092 (c-Si literatür) kullanıldı.
    """
    p = params or BarhdadiBennisParams()
    ln_g = np.log(poa_effective.clip(lower=1) / g_ref)
    irradiance_term = 1.0 + p.c1 * ln_g + p.c2 * ln_g**2
    temp_term = 1.0 + p.gamma * (temp_cell - temp_ref)
    eta = irradiance_term * temp_term
    # Çok düşük ışınımda model fiziksel olarak güç üretmiyor demek
    return eta.where(poa_effective >= 1, 0.0).clip(lower=0)


def pdc_barhdadi_bennis(
    poa_effective: pd.Series,
    temp_cell: pd.Series,
    p_nom: float,
    params: BarhdadiBennisParams | None = None,
    bifacial_gain_fraction: float = 0.0,
) -> pd.Series:
    """Barhdadi-Bennis tabanlı DC güç (bifacial revize ile).

    .. code::

        P_DC = P_nom * (G/G_0) * η_rel * (1 + BG·BF·A)

    Args:
        poa_effective: POA ışınımı, W/m².
        temp_cell: Hücre sıcaklığı, °C.
        p_nom: Nominal DC güç, W (veya kW).
        params: BarhdadiBennisParams.
        bifacial_gain_fraction: Net bifacial katkı (BG·BF·A çarpımı, mevcut tez için
            MERKAS GES'te 0.0607). Bifacial olmayan sistemler için 0.

    Returns:
        DC güç zaman serisi, p_nom ile aynı birimde.

    Referans:
        Barhdadi-Bennis (2012) + tez bifacial revize (Bölüm 3.3.2).
    """
    eta_rel = eta_rel_barhdadi_bennis(poa_effective, temp_cell, params)
    bifacial_factor = 1.0 + bifacial_gain_fraction
    return p_nom * (poa_effective / G_STC) * eta_rel * bifacial_factor


# -----------------------------------------------------------------------------
# AC dönüşüm — basit verim modeli
# -----------------------------------------------------------------------------

def pac_simple(
    p_dc: pd.Series,
    eta_bos: float = 0.93,
    eta_inv: float = 0.97,
    p_ac_clip: float | None = None,
) -> pd.Series:
    """Basit BoS + inverter verim modeliyle AC güç.

    .. code::

        P_AC = min(P_AC_clip, P_DC * η_BoS * η_inv)

    Args:
        p_dc: DC güç zaman serisi.
        eta_bos: BoS toplam verimi (kirlilik, gölge, mismatch, DC kablo, vb.
            çarpımı). Saha doğrulamada 0.85-0.93 arası tipik.
        eta_inv: Inverter nominal verimi (tipik 0.95-0.98).
        p_ac_clip: AC tarafı clipping limiti (nominal inverter kapasitesi).
            None ise clip yok.

    Returns:
        AC güç zaman serisi.
    """
    p_ac = p_dc * eta_bos * eta_inv
    if p_ac_clip is not None:
        p_ac = p_ac.clip(upper=p_ac_clip)
    return p_ac.clip(lower=0)


# -----------------------------------------------------------------------------
# Dispatcher
# -----------------------------------------------------------------------------

PowerModel = Literal["pvwatts", "barhdadi_bennis", "skoplaki_palyvos"]


def calculate_dc_power(
    model: PowerModel,
    poa_effective: pd.Series,
    temp_cell: pd.Series,
    p_nom: float,
    **kwargs,
) -> pd.Series:
    """Genel DC güç dispatcher.

    Args:
        model: 'pvwatts', 'barhdadi_bennis', veya 'skoplaki_palyvos'.
        poa_effective: POA ışınımı, W/m².
        temp_cell: Hücre sıcaklığı, °C.
        p_nom: Nominal DC güç.
        **kwargs: Modele özel parametreler.

    Returns:
        DC güç zaman serisi.
    """
    if model == "pvwatts":
        gamma_pdc = kwargs.get("gamma_pdc", -0.0040)
        return pdc_pvwatts(poa_effective, temp_cell, p_nom, gamma_pdc=gamma_pdc)
    if model == "barhdadi_bennis":
        params = kwargs.get("params")
        bg = kwargs.get("bifacial_gain_fraction", 0.0)
        return pdc_barhdadi_bennis(
            poa_effective, temp_cell, p_nom, params=params, bifacial_gain_fraction=bg
        )
    if model == "skoplaki_palyvos":
        beta = kwargs.get("beta", 0.0040)
        eta_ref = kwargs.get("eta_ref", 0.20)
        # P = P_nom * (G/G0) * (η_rel / η_ref)
        eta_rel = eta_skoplaki_palyvos(temp_cell, eta_ref, beta=beta)
        return p_nom * (poa_effective / G_STC) * (eta_rel / eta_ref)
    raise ValueError(f"Bilinmeyen model: {model}")
