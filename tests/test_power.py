"""DC güç modeli testleri."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pvquant.models.power import (
    BarhdadiBennisParams,
    G_STC,
    T_STC,
    TYPICAL_GAMMA,
    calculate_dc_power,
    eta_rel_barhdadi_bennis,
    eta_skoplaki_palyvos,
    pac_simple,
    pdc_barhdadi_bennis,
    pdc_pvwatts,
)


class TestPVWatts:
    def test_stc_returns_nominal_power(self):
        """STC koşullarında (G=1000, T=25) P_DC = P_nom."""
        ghi = pd.Series([G_STC])
        t_cell = pd.Series([T_STC])
        result = pdc_pvwatts(ghi, t_cell, p_dc0=5000)
        assert result.iloc[0] == pytest.approx(5000.0)

    def test_zero_irradiance_zero_power(self):
        ghi = pd.Series([0.0])
        t_cell = pd.Series([25.0])
        result = pdc_pvwatts(ghi, t_cell, p_dc0=5000)
        assert result.iloc[0] == 0.0

    def test_higher_temp_reduces_power(self):
        """T>25°C → güç düşmeli."""
        ghi = pd.Series([1000.0, 1000.0])
        t_cell = pd.Series([25.0, 50.0])
        result = pdc_pvwatts(ghi, t_cell, p_dc0=5000, gamma_pdc=-0.0040)
        assert result.iloc[1] < result.iloc[0]
        # 25°C fark × -0.004 = -0.10 (yani %10 düşüş)
        assert result.iloc[1] == pytest.approx(5000 * 0.90, rel=0.01)


class TestSkoplakiPalyvos:
    def test_stc_returns_eta_ref(self):
        t = pd.Series([T_STC])
        eta = eta_skoplaki_palyvos(t, eta_ref=0.20, beta=0.004)
        assert eta.iloc[0] == pytest.approx(0.20)

    def test_higher_temp_lower_efficiency(self):
        t = pd.Series([25.0, 60.0])
        eta = eta_skoplaki_palyvos(t, eta_ref=0.20, beta=0.004)
        assert eta.iloc[1] < eta.iloc[0]


class TestBarhdadiBennis:
    def test_stc_eta_rel_is_unity(self):
        """STC koşullarında η_rel = 1."""
        ghi = pd.Series([G_STC])
        t_cell = pd.Series([T_STC])
        eta = eta_rel_barhdadi_bennis(ghi, t_cell)
        assert eta.iloc[0] == pytest.approx(1.0, abs=1e-6)

    def test_default_params_match_paper(self):
        """c1=0.033, c2=-0.0092, γ=-0.0034 (Barhdadi-Bennis 2012 c-Si)."""
        p = BarhdadiBennisParams()
        assert p.c1 == 0.033
        assert p.c2 == -0.0092
        assert p.gamma == -0.0034

    def test_low_irradiance_efficiency_drops(self):
        """Düşük ışınımda η_rel<1 olmalı (logaritmik düşüş)."""
        ghi = pd.Series([100.0])  # 100 W/m²
        t_cell = pd.Series([T_STC])
        eta = eta_rel_barhdadi_bennis(ghi, t_cell)
        assert eta.iloc[0] < 1.0

    def test_zero_irradiance_zero_eta(self):
        """G=0 iken η_rel = 0 (log(0) önleme)."""
        ghi = pd.Series([0.0])
        t_cell = pd.Series([T_STC])
        eta = eta_rel_barhdadi_bennis(ghi, t_cell)
        assert eta.iloc[0] == 0.0

    def test_bifacial_gain_increases_power(self):
        """Bifacial katkı varsa P_DC artmalı."""
        ghi = pd.Series([G_STC])
        t_cell = pd.Series([T_STC])
        p_mono = pdc_barhdadi_bennis(ghi, t_cell, p_nom=5000, bifacial_gain_fraction=0.0)
        p_bifa = pdc_barhdadi_bennis(ghi, t_cell, p_nom=5000, bifacial_gain_fraction=0.0607)
        assert p_bifa.iloc[0] == pytest.approx(p_mono.iloc[0] * 1.0607, rel=1e-6)


class TestPacSimple:
    def test_apply_bos_and_inverter(self):
        p_dc = pd.Series([1000.0])
        p_ac = pac_simple(p_dc, eta_bos=0.93, eta_inv=0.97)
        assert p_ac.iloc[0] == pytest.approx(1000.0 * 0.93 * 0.97)

    def test_clip_limit(self):
        p_dc = pd.Series([1000.0, 5000.0])
        p_ac = pac_simple(p_dc, eta_bos=1.0, eta_inv=1.0, p_ac_clip=2000)
        assert p_ac.iloc[0] == 1000.0
        assert p_ac.iloc[1] == 2000.0


class TestTypicalGamma:
    def test_topcon_lower_than_mono_si(self):
        """Modern TOPCon mono c-Si'den daha düşük sıc. duyarlılığına sahip."""
        assert abs(TYPICAL_GAMMA["topcon"]) < abs(TYPICAL_GAMMA["mono_si"])

    def test_hjt_has_lowest_sensitivity(self):
        """HJT en düşük |γ| değerlerinden birine sahip."""
        assert abs(TYPICAL_GAMMA["hjt"]) <= abs(TYPICAL_GAMMA["mono_si"])


class TestDispatcher:
    def test_dispatcher_pvwatts(self):
        ghi = pd.Series([G_STC])
        t = pd.Series([T_STC])
        result = calculate_dc_power("pvwatts", ghi, t, p_nom=1000)
        assert result.iloc[0] == pytest.approx(1000)

    def test_dispatcher_barhdadi(self):
        ghi = pd.Series([G_STC])
        t = pd.Series([T_STC])
        result = calculate_dc_power("barhdadi_bennis", ghi, t, p_nom=1000)
        assert result.iloc[0] == pytest.approx(1000)

    def test_dispatcher_unknown_model(self):
        ghi = pd.Series([G_STC])
        t = pd.Series([T_STC])
        with pytest.raises(ValueError):
            calculate_dc_power("ghost", ghi, t, p_nom=1000)
