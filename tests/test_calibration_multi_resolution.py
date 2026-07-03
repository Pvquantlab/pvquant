"""tests/test_calibration_multi_resolution.py — Faz 1.6 Adim 3.3.

Kalibrasyonun frekans-agnostik davranisini dogrular.

Test stratejisi:
  - Sentetik deterministik veri (sabit seed, sabit koordinat, sabit plant).
  - Baseline degerleri scripts/adim3_3_baseline.py cikitisindan gelir.
  - Regresyon: kod degisikliginden sonra ayni degerler beklenir.

NOT: 15dk / 30dk destegi testleri Adim 3.3 kodu uygulandiktan SONRA eklenir.
Bu dosyada su an sadece 1h regresyon + yetersiz veri hatasi vardir.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pvquant.io.meteo import MeteoData
from pvquant.io.scada import SCADAData
from pvquant.pipeline.calibration import calibrate_from_scada
from pvquant.pipeline.forecast import PlantSpec, forecast_7day


# ---------------------------------------------------------------------------
# Deterministik test sabitleri
# adim3_3_baseline.py ile ayni degerler olmali - regresyon icin kritik
# ---------------------------------------------------------------------------
RANDOM_SEED = 42
LATITUDE = 37.87
LONGITUDE = 32.49
N_DAYS = 30
START_DATE = "2024-06-01"
SCADA_SCALE_FACTOR = 0.92
SCADA_NOISE_STD = 0.02


# ---------------------------------------------------------------------------
# Baseline degerleri (scripts/adim3_3_baseline.py cikitisi)
# Adim 3.3 kod degisikliginden SONRA ayni testin ayni sonuclari uretmesi lazim
# ---------------------------------------------------------------------------
BASELINE_BG_1H = 0.146871
BASELINE_ETA_BOS_1H = 0.808436
BASELINE_N_VALID_HOURS_1H = 330
BASELINE_TOTAL_DEV_AFTER_1H = -0.0459  # yuzde


# ---------------------------------------------------------------------------
# Test helper'lari
# ---------------------------------------------------------------------------
def _make_synthetic_meteo(freq: str = "1h") -> MeteoData:
    """Sentetik meteoroloji verisi olustur (baseline script ile ayni)."""
    n_hours = N_DAYS * 24
    if freq == "1h":
        n_periods = n_hours
    elif freq == "30min":
        n_periods = n_hours * 2
    elif freq == "15min":
        n_periods = n_hours * 4
    else:
        raise ValueError(f"Desteklenmeyen freq: {freq}")

    index = pd.date_range(START_DATE, periods=n_periods, freq=freq)
    hours = np.arange(n_periods) * pd.Timedelta(freq).total_seconds() / 3600.0

    ghi_raw = 850 * np.sin(np.pi * (hours % 24) / 12)
    ghi_values = np.clip(ghi_raw, 0, None)
    temp_values = 22.5 + 7.5 * np.sin(2 * np.pi * (hours - 3) / 24)
    wind_values = np.full(n_periods, 3.0)

    return MeteoData(
        ghi=pd.Series(ghi_values, index=index, name="ghi"),
        temp_air=pd.Series(temp_values, index=index, name="temp_air"),
        wind_speed_10m=pd.Series(wind_values, index=index, name="wind_speed_10m"),
        relative_humidity=None,
        cloud_cover=None,
        latitude=LATITUDE,
        longitude=LONGITUDE,
        timezone="UTC",
    )


def _make_synthetic_plant() -> PlantSpec:
    """Deterministik bifacial plant (baseline ile ayni)."""
    return PlantSpec(
        latitude=LATITUDE,
        longitude=LONGITUDE,
        p_nom_kwp=1000.0,
        tilt=30.0,
        azimuth=180.0,
        eta_bos=0.88,
        eta_inv=0.98,
        bifacial_gain_geometric=0.15,
        bifacial_factor=0.75,
        albedo=0.20,
    )


def _make_synthetic_scada(
    forecast_power: pd.Series,
    scale: float = SCADA_SCALE_FACTOR,
    noise_std: float = SCADA_NOISE_STD,
    seed: int = RANDOM_SEED,
) -> SCADAData:
    """Forecast'ten sentetik SCADA uret (baseline ile ayni)."""
    rng = np.random.default_rng(seed)
    scaled = forecast_power * scale
    noise = rng.normal(0, noise_std, size=len(scaled)) * np.abs(scaled)
    noisy = np.clip(scaled + noise, 0, None)
    dt_minutes = int(
        (forecast_power.index[1] - forecast_power.index[0]).total_seconds() / 60
    )
    return SCADAData(
        power_kw=pd.Series(noisy, index=forecast_power.index, name="power_kw"),
        energy_kwh=None,
        poa_irradiance=None,
        temp_ambient=None,
        temp_module=None,
        wind_speed=None,
        plant_name="synthetic_test",
        timestep_minutes=dt_minutes,
    )


# ---------------------------------------------------------------------------
# Test 1: 1h regresyon
# ---------------------------------------------------------------------------
class TestCalibrationRegression1h:
    """1h SCADA + 1h meteo ile regresyon: baseline degerleri korunmali."""

    @pytest.fixture(scope="class")
    def calibration_result(self):
        """Bir kez hesapla, class icinde paylas (calibration pahali)."""
        meteo = _make_synthetic_meteo(freq="1h")
        plant = _make_synthetic_plant()
        forecast = forecast_7day(meteo, plant)
        scada = _make_synthetic_scada(forecast.hourly["p_ac_kw"])
        return calibrate_from_scada(
            scada=scada,
            historical_meteo=meteo,
            plant=plant,
            fit_bg=True,
            fit_eta_bos=True,
        )

    def test_bg_matches_baseline(self, calibration_result):
        """Kalibre BG degeri baseline ile birebir eslesmeli."""
        assert calibration_result.bg == pytest.approx(
            BASELINE_BG_1H, rel=1e-4
        ), (
            f"BG baseline ile eslesmiyor: "
            f"beklenen {BASELINE_BG_1H:.6f}, gelen {calibration_result.bg:.6f}"
        )

    def test_eta_bos_matches_baseline(self, calibration_result):
        """Kalibre eta_bos degeri baseline ile birebir eslesmeli."""
        assert calibration_result.eta_bos == pytest.approx(
            BASELINE_ETA_BOS_1H, rel=1e-4
        ), (
            f"eta_bos baseline ile eslesmiyor: "
            f"beklenen {BASELINE_ETA_BOS_1H:.6f}, gelen {calibration_result.eta_bos:.6f}"
        )

    def test_n_valid_hours_matches_baseline(self, calibration_result):
        """Gecerli saat sayisi baseline ile eslesmeli."""
        assert calibration_result.n_valid_hours == BASELINE_N_VALID_HOURS_1H

    def test_total_deviation_near_zero_after(self, calibration_result):
        """Kalibrasyon sonrasi toplam sapma sifira yakin olmali (< %1)."""
        assert abs(calibration_result.validation_after.total_deviation_pct) < 1.0

    def test_mape_improved(self, calibration_result):
        """Kalibrasyon MAPE'yi iyilestirmeli."""
        assert (
            calibration_result.validation_after.mape_pct
            < calibration_result.validation_before.mape_pct
        )


# ---------------------------------------------------------------------------
# Test 3: 1h veride yetersiz veri hatasi
# ---------------------------------------------------------------------------
class TestCalibrationInsufficientData1h:
    """1h verile yetersiz SCADA (< 100 saat) hata vermeli."""

    def test_insufficient_1h_raises(self):
        """50 saatlik 1h SCADA -> ValueError."""
        plant = _make_synthetic_plant()

        # 50 saatlik meteo (yeterli boyutta olustur ama SCADA az)
        meteo = _make_synthetic_meteo(freq="1h")

        # 50 nokta 1h SCADA
        short_index = pd.date_range(START_DATE, periods=50, freq="1h")
        short_power = pd.Series(
            np.full(50, 100.0), index=short_index, name="power_kw"
        )
        scada = SCADAData(
            power_kw=short_power,
            energy_kwh=None,
            poa_irradiance=None,
            temp_ambient=None,
            temp_module=None,
            wind_speed=None,
            plant_name="short_test",
            timestep_minutes=60,
        )

        with pytest.raises(ValueError, match="Yetersiz"):
            calibrate_from_scada(
                scada=scada,
                historical_meteo=meteo,
                plant=plant,
            )



# --- Faz 1.6 Adim 3.3: 15min capability tests [BEGIN] ---
# ---------------------------------------------------------------------------
# Test 2: 15dk SCADA + 1h meteo -> kalibrasyon calisiyor
# ---------------------------------------------------------------------------
class TestCalibration15minSCADA:
    """15dk SCADA + 1h meteo ile kalibrasyon calisiyor ve makul sonuc uretiyor.

    Adim 3.3'un yeni kabiliyetinin ana testi. Meteo 1h, SCADA 15dk.
    Kalibrasyon icinde _align_meteo_to_scada meteo'yu 15dk'ya interpolate eder.

    Beklenti: BG ve eta_bos, 1h baseline degerine yakin (%5 tolerans).
    Ayni fiziksel senaryo -> ayni fiziksel sonuc olmali. Kucuk sapma
    interpolasyon ve fit convergence'inden kaynaklanabilir.
    """

    @pytest.fixture(scope="class")
    def calibration_result(self):
        # 15dk meteo -> 15dk forecast -> 15dk SCADA
        meteo_15min = _make_synthetic_meteo(freq="15min")
        plant = _make_synthetic_plant()
        forecast_15min = forecast_7day(meteo_15min, plant)
        scada_15min = _make_synthetic_scada(forecast_15min.hourly["p_ac_kw"])

        # Ama kalibrasyona 1h meteo veriyoruz - gercek dunya senaryo
        # (Open-Meteo 1h veri veriyor, kullanicinin SCADA'si 15dk)
        meteo_1h = _make_synthetic_meteo(freq="1h")

        return calibrate_from_scada(
            scada=scada_15min,
            historical_meteo=meteo_1h,
            plant=plant,
            fit_bg=True,
            fit_eta_bos=True,
        )

    def test_bg_close_to_1h_baseline(self, calibration_result):
        """15dk kalibrasyonun BG'si 1h baseline'a %5 icinde olmali."""
        assert calibration_result.bg == pytest.approx(BASELINE_BG_1H, rel=0.05), (
            f"BG 1h baseline'dan uzak: beklenen ~{BASELINE_BG_1H:.6f}, "
            f"gelen {calibration_result.bg:.6f}"
        )

    def test_eta_bos_close_to_1h_baseline(self, calibration_result):
        """15dk kalibrasyonun eta_bos'u 1h baseline'a %5 icinde olmali."""
        assert calibration_result.eta_bos == pytest.approx(
            BASELINE_ETA_BOS_1H, rel=0.05
        ), (
            f"eta_bos 1h baseline'dan uzak: beklenen ~{BASELINE_ETA_BOS_1H:.6f}, "
            f"gelen {calibration_result.eta_bos:.6f}"
        )

    def test_more_valid_samples_than_1h(self, calibration_result):
        """15dk veride daha fazla gecerli nokta olmali (yaklasik 4x)."""
        # 1h baseline: 330 saat. 15dk: yaklasik 4x = 1320 civari (esitlik degil)
        assert calibration_result.n_valid_hours > BASELINE_N_VALID_HOURS_1H * 3

    def test_total_deviation_near_zero_after(self, calibration_result):
        """Kalibrasyon sonrasi toplam sapma sifira yakin olmali."""
        assert abs(calibration_result.validation_after.total_deviation_pct) < 1.0

    def test_mape_improved(self, calibration_result):
        """MAPE kalibrasyondan sonra iyilesmeli."""
        assert (
            calibration_result.validation_after.mape_pct
            < calibration_result.validation_before.mape_pct
        )


# ---------------------------------------------------------------------------
# Test 4: 15dk veride yetersiz veri hatasi
# ---------------------------------------------------------------------------
class TestCalibrationInsufficientData15min:
    """15dk veride yetersiz SCADA (< 400 nokta = < 100 saat) hata vermeli."""

    def test_insufficient_15min_raises(self):
        """200 nokta 15dk SCADA (=50 saat) -> ValueError.

        1h veride 100 nokta yeterlidir ama 15dk'da 400 nokta (=100 saat) lazim.
        200 nokta 15dk = 50 saat -> yetersiz.
        """
        plant = _make_synthetic_plant()
        meteo = _make_synthetic_meteo(freq="1h")

        # 200 nokta 15dk SCADA
        short_index = pd.date_range(START_DATE, periods=200, freq="15min")
        short_power = pd.Series(
            np.full(200, 100.0), index=short_index, name="power_kw"
        )
        scada = SCADAData(
            power_kw=short_power,
            energy_kwh=None,
            poa_irradiance=None,
            temp_ambient=None,
            temp_module=None,
            wind_speed=None,
            plant_name="short_15min_test",
            timestep_minutes=15,
        )

        with pytest.raises(ValueError, match="Yetersiz"):
            calibrate_from_scada(
                scada=scada,
                historical_meteo=meteo,
                plant=plant,
            )

    def test_15min_400_samples_passes_check(self):
        """400 nokta 15dk (=100 saat) minimum'u karsilar, ilerlemeli.

        Bu test yetersiz veri hatasi vermemeli. Kalibrasyon ilerledigini
        ama sonucta anlamsiz olabilir (100 saatlik yaz gunesli veri).
        Onemli olan Yetersiz hatasi almamaktir.
        """
        plant = _make_synthetic_plant()
        # 400 nokta 15dk = 100 saat
        # Meteo da 100 saati kapsamali
        meteo_idx = pd.date_range(START_DATE, periods=100, freq="1h")
        import numpy as np
        n = len(meteo_idx)
        ghi_raw = 850 * np.sin(np.pi * (np.arange(n) % 24) / 12)
        ghi = pd.Series(np.clip(ghi_raw, 0, None), index=meteo_idx)
        temp = pd.Series(np.full(n, 20.0), index=meteo_idx)
        wind = pd.Series(np.full(n, 3.0), index=meteo_idx)
        short_meteo = MeteoData(
            ghi=ghi, temp_air=temp, wind_speed_10m=wind,
            relative_humidity=None, cloud_cover=None,
            latitude=LATITUDE, longitude=LONGITUDE, timezone="UTC",
        )

        scada_idx = pd.date_range(START_DATE, periods=400, freq="15min")
        # Fiziksel olarak makul degerler - fit basarisiz olsa da hata vermesin
        power_values = np.full(400, 100.0)
        scada = SCADAData(
            power_kw=pd.Series(power_values, index=scada_idx),
            energy_kwh=None,
            poa_irradiance=None,
            temp_ambient=None,
            temp_module=None,
            wind_speed=None,
            plant_name="minimum_15min_test",
            timestep_minutes=15,
        )

        # Yetersiz hatasi verilmemeli
        # Diger hatalar (fit convergence vs) olabilir, onlari yakalayip
        # sadece "Yetersiz" hatasinin cikmadigini dogrulariz
        try:
            result = calibrate_from_scada(
                scada=scada,
                historical_meteo=short_meteo,
                plant=plant,
                fit_bg=False,  # Fit karisikliginden kacinmak icin kapali
                fit_eta_bos=True,
            )
            # Basarili ise kalibrasyon ilerledi demektir
            assert result is not None
        except ValueError as e:
            # Sadece "Yetersiz" hatasi degilse OK
            assert "Yetersiz" not in str(e), (
                f"Beklenmedik Yetersiz hatasi: {e}"
            )
# --- Faz 1.6 Adim 3.3: 15min capability tests [END] ---
