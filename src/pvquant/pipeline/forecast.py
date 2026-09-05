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
from typing import Literal, Optional, List 
import numpy as np
import pandas as pd

from pvquant.io.meteo import MeteoData
from pvquant.models import bifacial, irradiance, power, temperature
from pvquant.pipeline.utils import _detect_timestep_hours


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
    # v2.255 (Dalga 3.10, ★): fizik terimleri — VARSAYILAN KAPALI ("none"): açılmadıkça zincir birebir eski.
    # iam_model: geliş açısı kaybı (beam × IAM(aoi), difüz Marion integrali); spectral_model: hava kütlesi +
    # yağışa su ile spektral uyumsuzluk çarpanı (First Solar; nem yoksa uygulanmaz). Santral params_json ile açılır.
    iam_model: Literal["none", "physical", "ashrae", "martin_ruiz"] = "none"
    spectral_model: Literal["none", "first_solar"] = "none"

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

        Not: 'hours' aslında len(hourly) değil, gerçek geçen saat sayısı.
        15 dk veride 96 kayıt 24 saati temsil eder.
        """
        n_records = len(self.hourly)
        if n_records < 2 or self.plant.p_nom_kwp == 0:
            return 0.0
        dt_hours = _detect_timestep_hours(self.hourly.index)
        total_hours = n_records * dt_hours
        return float(self.total_kwh / (self.plant.p_nom_kwp * total_hours))


def _apply_poa_correction(
    poa: "irradiance.POAComponents",
    bins: List[float],
    corrections: List[float],
) -> "irradiance.POAComponents":
    """POA global isinima POA-bin lookup duzeltmesi uygular.

    Her saat icin, o saatin POA degerinin hangi bin'e dustugune gore
    bir carpan uygular. Bin merkezleri arasinda lineer interpolasyon
    yapilir. Bin sinirlarinin disindaki degerler icin en yakin bin'in
    carpani kullanilir.

    Bu duzeltme, Open-Meteo GHI -> Erbs+Perez ile hesaplanan POA'nin
    saha SCADA POA olcumunden sapmasini telafi eder (kalibrasyondan
    ogrenilir).

    Args:
        poa: Erbs+Perez sonrasi POA bilesenleri (immutable).
        bins: POA bin merkezleri (W/m^2), artan sirali.
        corrections: Her bin icin carpan, bins ile ayni boyutta.

    Returns:
        Yeni POAComponents - global_ duzeltilmis, diger bilesenler ayni.
    """
    poa_global_values = poa.global_.values
    multipliers = np.interp(poa_global_values, bins, corrections)
    corrected_global = pd.Series(
        poa_global_values * multipliers,
        index=poa.global_.index,
        name=poa.global_.name,
    )
    return irradiance.POAComponents(
        global_=corrected_global,
        beam=poa.beam,
        sky_diffuse=poa.sky_diffuse,
        ground_diffuse=poa.ground_diffuse,
        aoi=poa.aoi,
    )



def _apply_fizik_terimleri(poa, plant, meteo, times):
    """v2.255 — POA bileşenlerine IAM ve spektral çarpanları (pvquant.ext.tahmin.fizik_terimler).
    beam × IAM_b(aoi); sky × IAM_sky(tilt); ground × IAM_gnd(tilt); global = toplam × M_spektral.
    Spektral için nem gerekir (Gueymard94 yağışa su); meteo.relative_humidity yoksa spektral ATLANIR (uydurma yok).
    Döner (POAComponents, meta sözlüğü)."""
    from pvquant.ext.tahmin import fizik_terimler as ft
    beam, sky, gnd = poa.beam, poa.sky_diffuse, poa.ground_diffuse
    meta = {"iam": plant.iam_model, "spektral": "none"}
    if plant.iam_model != "none":
        iam_b = ft.iam_katsayilari(poa.aoi.astype(float).fillna(90.0), plant.iam_model).fillna(0.0)
        iam_sky, iam_gnd = ft.iam_difuz(plant.tilt, plant.iam_model)
        beam = (beam * iam_b.reindex(beam.index)).clip(lower=0.0)
        sky = sky * iam_sky; gnd = gnd * iam_gnd
    M = 1.0
    if plant.spectral_model == "first_solar" and meteo.relative_humidity is not None:
        modul = {"mono_si": "monosi", "perc": "monosi", "topcon": "monosi", "hjt": "monosi", "multi_si": "multisi",
                 "poly_si": "multisi", "cdte": "cdte", "cigs": "cigs", "a_si": "asi"}.get(plant.module_tech, "monosi")
        M = ft.spektral_duzeltme(times, meteo.latitude, meteo.longitude, meteo.temp_air, meteo.relative_humidity, modul=modul)
        meta["spektral"] = "first_solar"
    yeni_global = ((beam + sky + gnd) * M).clip(lower=0.0)
    yeni_global.name = poa.global_.name
    return irradiance.POAComponents(global_=yeni_global, beam=beam, sky_diffuse=sky, ground_diffuse=gnd, aoi=poa.aoi), meta


# --- measured_poa akil kontrolu esikleri (config'e tasinabilir) ---
MEASURED_POA_SANITY_RATIO = 0.20      # olculen/Perez alt siniri
MEASURED_POA_SANITY_DAY_WM2 = 200.0   # 'gunduz' esigi (Perez POA)
MEASURED_POA_SANITY_MIN_HOURS = 24    # karar icin asgari kiyas saati


def forecast_7day(
    meteo: MeteoData,
    plant: PlantSpec,
    ghi_bias_bins: Optional[List[float]] = None,
    ghi_bias_corrections: Optional[List[float]] = None,
    measured_poa: Optional[pd.Series] = None,
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
        # v2.51 (R-3): apparent_zenith — atmosferik kirilma dahil
        solar_zenith=solpos["apparent_zenith"],
        times=times,
    )

    # --- 3. POA (Perez) ---
    dni_extra, airmass = irradiance.extra_radiation_and_airmass(times, solpos["apparent_zenith"])
    poa = irradiance.transpose_perez(
        surface_tilt=plant.tilt,
        surface_azimuth=plant.azimuth,
        solar_zenith=solpos["apparent_zenith"],
        solar_azimuth=solpos["azimuth"],
        dni=decomposed["dni"],
        ghi=decomposed["ghi"],
        dhi=decomposed["dhi"],
        dni_extra=dni_extra,
        airmass=airmass,
        albedo=plant.albedo,
    )
    # --- 3.25. Olculen POA override (varsa) ---
    _measured_poa_meta = None
    if measured_poa is not None:
        aligned = measured_poa.reindex(poa.global_.index)
        mask = aligned.notna()
        # --- 14 Tem 2026: olu-sensor akil kontrolu ---
        # Gunduz (Perez POA > MEASURED_POA_SANITY_DAY_WM2) saatlerinde olculen
        # POA ortalamasi Perez'in MEASURED_POA_SANITY_RATIO'sunun altindaysa
        # sensor olu ya da yanlis eslenmis demektir: override ATLANIR, fizik
        # Perez ile devam eder ve karar meta'ya yazilir. Sessiz sifir uretimi
        # bu blokla yapisal olarak engellenir.
        _gunduz = (poa.global_ > MEASURED_POA_SANITY_DAY_WM2) & mask
        if int(_gunduz.sum()) >= MEASURED_POA_SANITY_MIN_HOURS:
            _olc = float(aligned[_gunduz].mean())
            _perez = float(poa.global_[_gunduz].mean())
            if _olc < MEASURED_POA_SANITY_RATIO * _perez:
                _measured_poa_meta = (
                    f"measured_poa YOK SAYILDI (olu/yanlis sensor suphesi): "
                    f"gunduz olculen ort {_olc:.1f} W/m2, Perez {_perez:.1f} W/m2, "
                    f"esik oran {MEASURED_POA_SANITY_RATIO:.0%}. Perez POA kullanildi."
                )
                mask = pd.Series(False, index=mask.index)
        if mask.any() and _measured_poa_meta is None:
            _measured_poa_meta = (
                f"measured_poa uygulandi: {int(mask.sum())} saat SCADA POA "
                f"ile override edildi."
            )
        yeni_global = poa.global_.copy()
        yeni_global[mask] = aligned[mask]
        poa = irradiance.POAComponents(
            global_=yeni_global,
            beam=poa.beam,
            sky_diffuse=poa.sky_diffuse,
            ground_diffuse=poa.ground_diffuse,
            aoi=poa.aoi,
        )

    # --- 3.5. POA bias duzeltmesi (Mod B'de kalibrasyondan ogrenilir) ---
    if ghi_bias_bins is not None and ghi_bias_corrections is not None:
        poa = _apply_poa_correction(poa, ghi_bias_bins, ghi_bias_corrections)

    # --- 4. Bifacial katkı (basit çarpan, ön yüze uygulanır) ---
    # --- 3.5. Fizik terimleri (v2.255, ★): IAM ve spektral — varsayılan kapalı ---
    fizik_meta = None
    if plant.iam_model != "none" or plant.spectral_model != "none":
        poa, fizik_meta = _apply_fizik_terimleri(poa, plant, meteo, times)
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

    # --- 8. Enerji hesabı (kWh = kW × dt_saat) ---
    # Frekans agnostik: 1h -> ×1.0, 15dk -> ×0.25, 5dk -> ×0.0833...
    dt_hours = _detect_timestep_hours(p_ac.index)
    energy_kwh = p_ac * dt_hours

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

    # v2.51 (R-4): gunluk toplam indeks tz gunundedir (genelde UTC).
    # PV gece ~0 urettigi icin yerel-gun kaymasi enerji toplamini etkilemez
    # (denetim raporu, bilinçli kabul).
    daily_energy = energy_kwh.resample("1D").sum()
    total = float(energy_kwh.sum())

    return ForecastResult(
        hourly=hourly,
        daily_energy_kwh=daily_energy,
        total_kwh=total,
        plant=plant,
        meta={
            "measured_poa": _measured_poa_meta,
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
