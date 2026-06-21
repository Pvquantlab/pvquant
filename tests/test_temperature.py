"""Sıcaklık modeli testleri."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pvquant.models.temperature import (
    FaimanParams,
    SAPM_PRESETS,
    adjust_wind_speed_log_profile,
    cell_temperature,
    cell_temperature_faiman,
    cell_temperature_noct,
    cell_temperature_sapm,
)


class TestNOCT:
    def test_stc_returns_ambient_at_zero_irradiance(self, sample_temp):
        """G=0 iken T_cell = T_amb."""
        zero_ghi = pd.Series(np.zeros(len(sample_temp)), index=sample_temp.index)
        result = cell_temperature_noct(zero_ghi, sample_temp, noct=45)
        pd.testing.assert_series_equal(result, sample_temp, check_names=False)

    def test_noct_at_800_wm2_matches_definition(self):
        """G=800 W/m² ve T_amb=20°C iken T_cell = NOCT (datasheet tanımı)."""
        ghi = pd.Series([800.0])
        t_amb = pd.Series([20.0])
        result = cell_temperature_noct(ghi, t_amb, noct=45)
        assert result.iloc[0] == pytest.approx(45.0, abs=0.01)


class TestFaiman:
    def test_zero_irradiance(self, sample_temp, sample_wind):
        """G=0 iken T_cell = T_amb."""
        zero_ghi = pd.Series(np.zeros(len(sample_temp)), index=sample_temp.index)
        result = cell_temperature_faiman(zero_ghi, sample_temp, sample_wind)
        np.testing.assert_allclose(result.values, sample_temp.values)

    def test_higher_wind_lower_temp(self, sample_ghi, sample_temp):
        """Yüksek rüzgar → daha düşük hücre sıcaklığı."""
        ws_low = pd.Series(np.full(24, 1.0), index=sample_ghi.index)
        ws_high = pd.Series(np.full(24, 10.0), index=sample_ghi.index)
        t_low_wind = cell_temperature_faiman(sample_ghi, sample_temp, ws_low)
        t_high_wind = cell_temperature_faiman(sample_ghi, sample_temp, ws_high)
        # Pik saatte yüksek rüzgar daha düşük sıcaklık vermeli
        assert t_high_wind.max() < t_low_wind.max()

    def test_default_params_match_pvlib_faiman_2008(self, sample_ghi, sample_temp, sample_wind):
        """Default U0=25, U1=6.84 (Faiman 2008 Negev)."""
        params = FaimanParams()
        assert params.u0 == 25.0
        assert params.u1 == 6.84

    def test_from_preset(self):
        """Preset yükleme çalışıyor."""
        params = FaimanParams.from_preset("bipv_integrated")
        assert params.u0 == 15.0
        assert params.u1 == 0.0

    def test_unknown_preset_raises(self):
        with pytest.raises(ValueError, match="Bilinmeyen preset"):
            FaimanParams.from_preset("madeup_preset")


class TestWindAdjustment:
    def test_logarithmic_profile_decreases_speed(self):
        """Modül seviyesinde rüzgar 10m'dekinden düşük olmalı."""
        ws_10m = pd.Series([5.0, 8.0, 12.0])
        ws_module = adjust_wind_speed_log_profile(ws_10m, target_height=2.0)
        assert (ws_module < ws_10m).all()

    def test_returns_input_at_10m(self):
        """target_height=10m → scaling=1.0."""
        ws_10m = pd.Series([5.0, 8.0, 12.0])
        ws_out = adjust_wind_speed_log_profile(ws_10m, target_height=10.0)
        np.testing.assert_allclose(ws_out.values, ws_10m.values)

    def test_raises_when_target_below_roughness(self):
        ws = pd.Series([5.0])
        with pytest.raises(ValueError):
            adjust_wind_speed_log_profile(ws, target_height=0.01, roughness_length=0.03)


class TestSAPM:
    def test_open_rack_polymer_preset_exists(self):
        """SAPM önceden tanımlı setler dokümandaki değerlerle eşleşmeli."""
        p = SAPM_PRESETS["open_rack_glass_polymer"]
        assert p.a == pytest.approx(-3.56)
        assert p.b == pytest.approx(-0.0750)
        assert p.delta_t == 3.0

    def test_sapm_calculation_runs(self, sample_ghi, sample_temp, sample_wind):
        result = cell_temperature_sapm(sample_ghi, sample_temp, sample_wind)
        assert len(result) == len(sample_ghi)
        # Pik saatte SAPM hücre sıcaklığı ortam sıcaklığından yüksek olmalı
        assert result.max() > sample_temp.max()


class TestDispatcher:
    def test_dispatcher_noct(self, sample_ghi, sample_temp):
        result = cell_temperature("noct", sample_ghi, sample_temp, noct=45)
        assert len(result) == 24

    def test_dispatcher_faiman_no_wind_uses_default(self, sample_ghi, sample_temp):
        # wind_speed=None → 1.0 default
        result = cell_temperature("faiman", sample_ghi, sample_temp)
        assert len(result) == 24

    def test_dispatcher_sapm_requires_wind(self, sample_ghi, sample_temp):
        with pytest.raises(ValueError, match="rüzgar"):
            cell_temperature("sapm", sample_ghi, sample_temp)

    def test_unknown_model_raises(self, sample_ghi, sample_temp):
        with pytest.raises(ValueError, match="Bilinmeyen model"):
            cell_temperature("not_a_model", sample_ghi, sample_temp)
