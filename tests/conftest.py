"""Pytest yapılandırması ve ortak fixture'lar."""
from __future__ import annotations

import sys
from pathlib import Path

# v2.72: `apps` paketi (API/worker) kurulan pakete dahil degil (src layout
# yalniz pvquant'i kurar). API testleri `import apps.api.main` yapabilsin
# diye depo koku sys.path'e eklenir — pip kurulumundan bagimsiz, CI dahil.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def hourly_index() -> pd.DatetimeIndex:
    """Tek günlük saatlik UTC zaman indeksi (24 saat)."""
    return pd.date_range("2026-06-21", periods=24, freq="1h", tz="UTC")


@pytest.fixture
def sample_ghi(hourly_index: pd.DatetimeIndex) -> pd.Series:
    """Yaz günü için sentetik GHI eğrisi (W/m²)."""
    hours = np.arange(24)
    # Öğlen civarı pik, gece sıfır olan bir bell shape
    ghi = np.maximum(0, 1000 * np.sin(np.pi * (hours - 6) / 12))
    return pd.Series(ghi, index=hourly_index, name="ghi")


@pytest.fixture
def sample_temp(hourly_index: pd.DatetimeIndex) -> pd.Series:
    """Sentetik ortam sıcaklığı (°C)."""
    hours = np.arange(24)
    # 15°C gece - 35°C öğlen arası sinüsoidal
    temp = 25 + 10 * np.sin(np.pi * (hours - 8) / 12)
    return pd.Series(temp, index=hourly_index, name="temp_air")


@pytest.fixture
def sample_wind(hourly_index: pd.DatetimeIndex) -> pd.Series:
    """Sentetik rüzgar hızı (m/s)."""
    return pd.Series(np.full(24, 3.0), index=hourly_index, name="wind_speed")
