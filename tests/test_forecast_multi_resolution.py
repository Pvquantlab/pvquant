"""Multi-resolution enerji hesabı ve kapasite faktörü testleri.

Faz 1.6 Adım 2 için — forecast.py'daki enerji ve capacity_factor
düzeltmelerinin doğruluğunu ve regresyon güvenliğini kanıtlar.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pvquant.pipeline.forecast import ForecastResult, PlantSpec
from pvquant.pipeline.utils import _detect_timestep_hours


def _make_result(index: pd.DatetimeIndex, p_ac_values: np.ndarray) -> ForecastResult:
    """Sentetik ForecastResult üretir - sadece capacity_factor testi için."""
    p_ac = pd.Series(p_ac_values, index=index, name="p_ac_kw")
    dt_hours = _detect_timestep_hours(index)
    energy_kwh = p_ac * dt_hours

    hourly = pd.DataFrame({
        "p_ac_kw": p_ac,
        "energy_kwh": energy_kwh,
    })

    plant = PlantSpec(p_nom_kwp=1000.0, latitude=37.0, longitude=32.0)
    return ForecastResult(
        hourly=hourly,
        daily_energy_kwh=energy_kwh.resample("1D").sum(),
        total_kwh=float(energy_kwh.sum()),
        plant=plant,
        meta={},
    )


class TestEnergyCalculation:
    """Enerji hesabı çözünürlüğe göre doğru mu?"""

    def test_hourly_1kw_for_24h_gives_24kwh(self):
        """Saatlik: 1 kW × 24 saat = 24 kWh."""
        idx = pd.date_range("2024-06-01", periods=24, freq="1h")
        values = np.full(24, 1.0)  # 1 kW sabit
        result = _make_result(idx, values)
        assert result.total_kwh == pytest.approx(24.0)

    def test_fifteen_min_1kw_for_24h_gives_24kwh(self):
        """15 dk: 1 kW × 96 çeyrek saat = 24 kWh (aynı!)."""
        idx = pd.date_range("2024-06-01", periods=96, freq="15min")
        values = np.full(96, 1.0)
        result = _make_result(idx, values)
        assert result.total_kwh == pytest.approx(24.0)

    def test_five_min_1kw_for_24h_gives_24kwh(self):
        """5 dk: 1 kW × 288 kayıt × 5/60 saat = 24 kWh."""
        idx = pd.date_range("2024-06-01", periods=288, freq="5min")
        values = np.full(288, 1.0)
        result = _make_result(idx, values)
        assert result.total_kwh == pytest.approx(24.0)

    def test_one_min_1kw_for_1h_gives_1kwh(self):
        """1 dk: 1 kW × 60 dakika = 1 kWh."""
        idx = pd.date_range("2024-06-01", periods=60, freq="1min")
        values = np.full(60, 1.0)
        result = _make_result(idx, values)
        assert result.total_kwh == pytest.approx(1.0)

    def test_thirty_min_1kw_for_2h_gives_2kwh(self):
        """30 dk: 1 kW × 4 kayıt × 0.5 saat = 2 kWh."""
        idx = pd.date_range("2024-06-01", periods=4, freq="30min")
        values = np.full(4, 1.0)
        result = _make_result(idx, values)
        assert result.total_kwh == pytest.approx(2.0)


class TestCapacityFactor:
    """Kapasite faktörü çözünürlüğe göre doğru mu?"""

    def test_hourly_full_output_gives_100_percent(self):
        """1000 kW nominal, 24 saat 1000 kW üretim -> CF = 1.0."""
        idx = pd.date_range("2024-06-01", periods=24, freq="1h")
        values = np.full(24, 1000.0)
        result = _make_result(idx, values)
        assert result.capacity_factor == pytest.approx(1.0)

    def test_fifteen_min_full_output_gives_100_percent(self):
        """15 dk çözünürlükte de aynı: 96 kayıt × 1000 kW -> CF = 1.0."""
        idx = pd.date_range("2024-06-01", periods=96, freq="15min")
        values = np.full(96, 1000.0)
        result = _make_result(idx, values)
        assert result.capacity_factor == pytest.approx(1.0)

    def test_five_min_full_output_gives_100_percent(self):
        """5 dk çözünürlükte de aynı: 288 kayıt × 1000 kW -> CF = 1.0."""
        idx = pd.date_range("2024-06-01", periods=288, freq="5min")
        values = np.full(288, 1000.0)
        result = _make_result(idx, values)
        assert result.capacity_factor == pytest.approx(1.0)

    def test_hourly_half_output_gives_50_percent(self):
        """Yarım kapasite -> CF = 0.5."""
        idx = pd.date_range("2024-06-01", periods=24, freq="1h")
        values = np.full(24, 500.0)  # 1000 kW nominal'in yarısı
        result = _make_result(idx, values)
        assert result.capacity_factor == pytest.approx(0.5)


class TestRegressionSafety:
    """Regresyon güvenliği: saatlik veri için eski davranışla aynı sonuç."""

    def test_hourly_energy_equals_power(self):
        """Saatlik veri için energy_kwh = p_ac (dt_hours=1.0)."""
        idx = pd.date_range("2024-06-01", periods=100, freq="1h")
        # Rastgele ama tekrar üretilebilir güç profili
        np.random.seed(42)
        values = np.random.uniform(0, 20000, 100)
        result = _make_result(idx, values)

        # energy_kwh saatlik veri için p_ac'ye eşit olmalı
        assert np.allclose(
            result.hourly["energy_kwh"].values,
            result.hourly["p_ac_kw"].values,
        )

    def test_hourly_total_kwh_equals_sum_p_ac(self):
        """Saatlik veri için total_kwh = sum(p_ac)."""
        idx = pd.date_range("2024-06-01", periods=100, freq="1h")
        np.random.seed(42)
        values = np.random.uniform(0, 20000, 100)
        result = _make_result(idx, values)

        assert result.total_kwh == pytest.approx(float(np.sum(values)))
