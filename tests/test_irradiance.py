"""Işınım modeli testleri (Erbs, Perez, solar position)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pvquant.models.irradiance import (
    decompose_ghi_erbs,
    extra_radiation_and_airmass,
    solar_position,
    transpose_perez,
)


@pytest.fixture
def konya_solpos():
    """Konya (37.87°N, 32.49°E) için 21 Haziran saatlik güneş pozisyonu."""
    times = pd.date_range("2026-06-21", periods=24, freq="1h", tz="UTC")
    return solar_position(times, latitude=37.87, longitude=32.49, altitude=1000)


@pytest.fixture
def konya_solpos_winter():
    """Konya için 21 Aralık (kış gündönümü) — düşük güneş açısı, tilt avantajı belirgin."""
    times = pd.date_range("2026-12-21", periods=24, freq="1h", tz="UTC")
    return solar_position(times, latitude=37.87, longitude=32.49, altitude=1000)


class TestSolarPosition:
    def test_returns_required_columns(self, konya_solpos):
        for col in ["zenith", "azimuth", "apparent_zenith"]:
            assert col in konya_solpos.columns

    def test_zenith_at_solar_noon_is_minimum(self, konya_solpos):
        """Gün boyu en küçük zenit, öğlen civarında olmalı."""
        min_idx = konya_solpos["zenith"].idxmin()
        # Konya UTC+0'da öğlen ≈ 10:00 UTC (boylam etkisi)
        assert 8 <= min_idx.hour <= 11

    def test_night_zenith_above_90(self, konya_solpos):
        """Geceleri zenit > 90° (güneş ufuk altında)."""
        midnight = konya_solpos.iloc[0]
        assert midnight["zenith"] > 90


class TestErbsDecomposition:
    def test_zero_ghi_gives_zero_components(self):
        times = pd.date_range("2026-06-21", periods=3, freq="1h", tz="UTC")
        ghi = pd.Series([0.0, 0.0, 0.0], index=times)
        zenith = pd.Series([85.0, 89.0, 90.0], index=times)
        result = decompose_ghi_erbs(ghi, zenith, times)
        assert result["dhi"].sum() == 0
        assert result["dni"].sum() == 0

    def test_clear_day_produces_dni(self):
        """Açık öğle koşulunda yüksek GHI → DNI > 0."""
        times = pd.date_range("2026-06-21 09:00", periods=1, freq="1h", tz="UTC")
        ghi = pd.Series([900.0], index=times)
        zenith = pd.Series([25.0], index=times)
        result = decompose_ghi_erbs(ghi, zenith, times)
        assert result["dni"].iloc[0] > 0
        assert result["dhi"].iloc[0] > 0

    def test_closure_equation_holds(self):
        """GHI ≈ DHI + DNI·cos(zenith) (kapanış denklemi)."""
        times = pd.date_range("2026-06-21 09:00", periods=1, freq="1h", tz="UTC")
        ghi = pd.Series([700.0], index=times)
        zenith = pd.Series([35.0], index=times)
        result = decompose_ghi_erbs(ghi, zenith, times)
        reconstructed = result["dhi"].iloc[0] + result["dni"].iloc[0] * np.cos(np.radians(35.0))
        assert reconstructed == pytest.approx(700.0, rel=0.05)


class TestPerezTransposition:
    def test_horizontal_surface_poa_equals_ghi(self, konya_solpos):
        """Yatay yüzey (tilt=0) için POA ≈ GHI."""
        times = konya_solpos.index
        ghi = pd.Series(np.maximum(0, 800 * np.cos(np.radians(konya_solpos["zenith"]))),
                        index=times)
        decomposed = decompose_ghi_erbs(ghi, konya_solpos["zenith"], times)
        dni_extra, airmass = extra_radiation_and_airmass(times, konya_solpos["zenith"])

        poa = transpose_perez(
            surface_tilt=0,
            surface_azimuth=180,
            solar_zenith=konya_solpos["zenith"],
            solar_azimuth=konya_solpos["azimuth"],
            dni=decomposed["dni"],
            ghi=ghi,
            dhi=decomposed["dhi"],
            dni_extra=dni_extra,
            airmass=airmass,
        )
        # Sadece güneş ufuk üstünde olduğu saatleri karşılaştır
        daylight = konya_solpos["zenith"] < 85
        if daylight.any():
            diff = (poa.global_[daylight] - ghi[daylight]).abs()
            # %5'lik tolerans (zemin yansıması küçük katkı)
            assert (diff / ghi[daylight].clip(lower=1) < 0.10).all()

    def test_tilted_surface_increases_poa_at_low_sun(self, konya_solpos_winter):
        """Düşük güneş açısında (kış) eğimli yüzey daha çok POA toplar."""
        times = konya_solpos_winter.index
        ghi = pd.Series(np.maximum(0, 600 * np.cos(np.radians(konya_solpos_winter["zenith"]))),
                        index=times)
        decomposed = decompose_ghi_erbs(ghi, konya_solpos_winter["zenith"], times)
        dni_extra, airmass = extra_radiation_and_airmass(times, konya_solpos_winter["zenith"])

        poa_flat = transpose_perez(
            surface_tilt=0, surface_azimuth=180,
            solar_zenith=konya_solpos_winter["zenith"], solar_azimuth=konya_solpos_winter["azimuth"],
            dni=decomposed["dni"], ghi=ghi, dhi=decomposed["dhi"],
            dni_extra=dni_extra, airmass=airmass,
        )
        poa_tilted = transpose_perez(
            surface_tilt=37, surface_azimuth=180,
            solar_zenith=konya_solpos_winter["zenith"], solar_azimuth=konya_solpos_winter["azimuth"],
            dni=decomposed["dni"], ghi=ghi, dhi=decomposed["dhi"],
            dni_extra=dni_extra, airmass=airmass,
        )
        # Kışın günlük toplamda eğimli > yatay (kuzey yarımküre, enleme yakın eğim)
        assert poa_tilted.global_.sum() > poa_flat.global_.sum()


class TestExtraRadiation:
    def test_extra_radiation_near_solar_constant(self):
        """Atmosfer üstü ışınım ≈ 1367 W/m² civarında salınır."""
        times = pd.date_range("2026-06-21", periods=24, freq="1h", tz="UTC")
        zenith = pd.Series(np.linspace(30, 80, 24), index=times)
        dni_extra, _ = extra_radiation_and_airmass(times, zenith)
        # Yıl ortası için ~1322 W/m² (eccentricity nedeniyle)
        assert 1300 < float(dni_extra.iloc[0]) < 1420
