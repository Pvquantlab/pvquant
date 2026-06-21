"""7 günlük üretim tahmini pipeline.

Tam fizik zinciri:

.. code::

    Open-Meteo (GHI, T, WS, lat, lon)
        ↓
    Solar position (zenith, azimuth)
        ↓
    Erbs decomposition (GHI → DHI + DNI)
        ↓
    Perez transposition (→ POA front)
        ↓
    Simple bifacial multiplier (× (1 + BG·BF·A))
        ↓
    Faiman cell temperature (rüzgar dahil)
        ↓
    Barhdadi-Bennis η_rel
        ↓
    P_DC × η_BoS × η_inv → P_AC
        ↓
    7 günlük günlük toplamlar
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import pandas as pd

from pvquant.io.meteo import MeteoData
from pvquant.models import bifacial, irradiance, power, temperature


@dataclass
class PlantSpec:
    """Santral teknik özellikleri.

    Forecast pipeline'ı için gerekli minimum bilgi seti.

    Attributes:
        p_nom_kwp: DC nominal güç, kWp.
        latitude: Enlem, derece.
        longitude: Boylam, derece.
        tilt: Modül eğim açısı, derece (0 = yatay).
        azimuth: Modül azimut açısı, derece (180 = güney).
        module_tech: 'mono_si', 'topcon', 'hjt', vb. (γ otomatik seçimi için).
        gamma_pdc: Sıcaklık katsayısı override (None ise teknolojiden seçilir).
        noct: NOCT değeri, °C (Faiman kullanılınca gereksiz).
        bifacial_factor: BF, bifacial modül için datasheet'ten. 0 = monofacial.
        bifacial_gain_geometric: BG, geometrik arka yüz oranı.
        albedo: Saha albedosu.
        eta_bos: BoS verimi (kirlilik, mismatch, kablo, vb. toplam).
        eta_inv: Inverter nominal verimi.
        p_ac_clip_kw: AC clip limiti (None ise yok).
        altitude_m: Rakım, metre.
        module_height_m: Modül alt kenar yüksekliği, metre (rüzgar düzeltmesi için).
        thermal_model: 'noct' veya 'faiman'.
        power_model: 'barhdadi_bennis', 'pvwatts', veya 'skoplaki_palyvos'.
    """

    p_nom_kwp: float
    latitude: float
    longitude: float
    tilt: float = 30.0
    azimuth: float = 180.0
    module_tech: str = "mono_si"
    gamma_pdc: float | None = None
    noct: float = 45.0
    bifacial_factor: float = 0.0  # 0 = monofacial
    bifacial_gain_geometric: float = 0.347
    albedo: float = 0.25
    eta_bos: float = 0.93
    eta_inv: float = 0.97
    p_ac_clip_kw: float | None = None
    altitude_m: float = 0.0
    module_height_m: float = 2.0
    thermal_model: Literal["noct", "faiman"] = "faiman"
    power_model: Literal["barhdadi_bennis", "pvwatts", "skoplaki_palyvos"] = "barhdadi_bennis"

    @property
    def effective_gamma(self) -> float:
        """γ değerini döner: override varsa onu, yoksa teknolojiden varsayılan."""
        if self.gamma_pdc is not None:
            return self.gamma_pdc
        return power.TYPICAL_GAMMA.get(self.module_tech, -0.0040)

    @property
    def is_bifacial(self) -> bool:
        return self.bifacial_factor > 0


@dataclass
class ForecastResult:
    """7 günlük tahmin sonucu.

    Attributes:
        hourly: Saatlik DataFrame. Kolonlar: ghi, dhi, dni, poa, temp_cell,
            p_dc_kw, p_ac_kw, energy_kwh.
        daily_energy_kwh: Her gün için toplam enerji üretimi, kWh.
        total_kwh: 7 günlük toplam, kWh.
        plant: Kullanılan PlantSpec.
        meta: Hesaplama metadata (model, kaynak, vb).
    """

    hourly: pd.DataFrame
    daily_energy_kwh: pd.Series
    total_kwh: float
    plant: PlantSpec
    meta: dict = field(default_factory=dict)

    @property
    def peak_power_kw(self) -> float:
        """En yüksek anlık AC güç, kW."""
        return float(self.hourly["p_ac_kw"].max())

    @property
    def average_daily_kwh(self) -> float:
        """Günlük ortalama üretim, kWh/gün."""
        return float(self.daily_energy_kwh.mean())

    @property
    def capacity_factor(self) -> float:
        """Kapasite faktörü (0-1 arası).

        CF = toplam üretim / (P_nom * süre)
        """
        hours = len(self.hourly)
        if hours == 0 or self.plant.p_nom_kwp == 0:
            return 0.0
        return float(self.total_kwh / (self.plant.p_nom_kwp * hours))


def forecast_7day(
    meteo: MeteoData,
    plant: PlantSpec,
) -> ForecastResult:
    """7 günlük üretim tahmini ana pipeline'ı.

    Pipeline tüm fiziksel adımları geçer ve hem saatlik hem günlük sonuç döner.
    Senin diyagramındaki sağ koldaki "meteo verisi olursa" akışıdır.

    Args:
        meteo: Open-Meteo'dan alınmış meteoroloji verisi.
        plant: Santral özellikleri.

    Returns:
        ForecastResult.

    Example:
        >>> from pvquant.io.meteo import OpenMeteoClient
        >>> from pvquant.pipeline.forecast import forecast_7day, PlantSpec
        >>> meteo = OpenMeteoClient().get_forecast(37.87, 32.49)
        >>> plant = PlantSpec(p_nom_kwp=5000, latitude=37.87, longitude=32.49)
        >>> result = forecast_7day(meteo, plant)
        >>> print(result.total_kwh)
    """
    times = meteo.ghi.index
    if not isinstance(times, pd.DatetimeIndex):
        times = pd.to_datetime(times)
        meteo.ghi.index = times

    # --- 1. Güneş pozisyonu ---
    solpos = irradiance.solar_position(
        times=times,
        latitude=meteo.latitude,
        longitude=meteo.longitude,
        altitude=plant.altitude_m,
    )

    # --- 2. GHI → DHI/DNI (Erbs) ---
    decomposed = irradiance.decompose_ghi_erbs(
        ghi=meteo.ghi,
        solar_zenith=solpos["zenith"],
        times=times,
    )

    # --- 3. POA (Perez) ---
    dni_extra, airmass = irradiance.extra_radiation_and_airmass(times, solpos["zenith"])
    poa = irradiance.transpose_perez(
        surface_tilt=plant.tilt,
        surface_azimuth=plant.azimuth,
        solar_zenith=solpos["zenith"],
        solar_azimuth=solpos["azimuth"],
        dni=decomposed["dni"],
        ghi=decomposed["ghi"],
        dhi=decomposed["dhi"],
        dni_extra=dni_extra,
        airmass=airmass,
        albedo=plant.albedo,
    )

    # --- 4. Bifacial katkı (basit çarpan, ön yüze uygulanır) ---
    if plant.is_bifacial:
        bf_params = bifacial.SimpleBifacialParams(
            bg=plant.bifacial_gain_geometric,
            bf=plant.bifacial_factor,
            albedo=plant.albedo,
        )
        bifacial_gain_fraction = bf_params.net_gain_fraction
    else:
        bifacial_gain_fraction = 0.0

    # --- 5. Hücre sıcaklığı ---
    if plant.thermal_model == "faiman":
        ws_at_module = temperature.adjust_wind_speed_log_profile(
            meteo.wind_speed_10m,
            target_height=plant.module_height_m,
        )
        temp_cell = temperature.cell_temperature_faiman(
            poa_global=poa.global_,
            temp_ambient=meteo.temp_air,
            wind_speed=ws_at_module,
        )
    else:  # noct
        temp_cell = temperature.cell_temperature_noct(
            poa_global=poa.global_,
            temp_ambient=meteo.temp_air,
            noct=plant.noct,
        )

    # --- 6. DC güç ---
    if plant.power_model == "barhdadi_bennis":
        bb_params = power.BarhdadiBennisParams(gamma=plant.effective_gamma)
        p_dc = power.pdc_barhdadi_bennis(
            poa_effective=poa.global_,
            temp_cell=temp_cell,
            p_nom=plant.p_nom_kwp,
            params=bb_params,
            bifacial_gain_fraction=bifacial_gain_fraction,
        )
    elif plant.power_model == "pvwatts":
        p_dc = power.pdc_pvwatts(
            poa_effective=poa.global_,
            temp_cell=temp_cell,
            p_dc0=plant.p_nom_kwp,
            gamma_pdc=plant.effective_gamma,
        )
        if plant.is_bifacial:
            p_dc = p_dc * (1.0 + bifacial_gain_fraction)
    else:  # skoplaki_palyvos
        p_dc = power.calculate_dc_power(
            "skoplaki_palyvos",
            poa_effective=poa.global_,
            temp_cell=temp_cell,
            p_nom=plant.p_nom_kwp,
            beta=-plant.effective_gamma,
        )
        if plant.is_bifacial:
            p_dc = p_dc * (1.0 + bifacial_gain_fraction)

    # --- 7. AC güç ---
    p_ac = power.pac_simple(
        p_dc=p_dc,
        eta_bos=plant.eta_bos,
        eta_inv=plant.eta_inv,
        p_ac_clip=plant.p_ac_clip_kw,
    )

    # --- 8. Saatlik enerji (kWh = kW × 1h) ---
    energy_kwh = p_ac  # saatlik adımda kW = kWh

    # --- Sonuçları topla ---
    hourly = pd.DataFrame(
        {
            "ghi": meteo.ghi,
            "dhi": decomposed["dhi"],
            "dni": decomposed["dni"],
            "poa_global": poa.global_,
            "temp_ambient": meteo.temp_air,
            "wind_speed_10m": meteo.wind_speed_10m,
            "temp_cell": temp_cell,
            "p_dc_kw": p_dc,
            "p_ac_kw": p_ac,
            "energy_kwh": energy_kwh,
        }
    )

    daily_energy = energy_kwh.resample("1D").sum()
    total = float(energy_kwh.sum())

    return ForecastResult(
        hourly=hourly,
        daily_energy_kwh=daily_energy,
        total_kwh=total,
        plant=plant,
        meta={
            "thermal_model": plant.thermal_model,
            "power_model": plant.power_model,
            "is_bifacial": plant.is_bifacial,
            "bifacial_gain_pct": bifacial_gain_fraction * 100,
            "gamma_used": plant.effective_gamma,
            "meteo_source": "open-meteo",
            "decomposition_model": "erbs",
            "transposition_model": "perez_1990",
        },
    )
