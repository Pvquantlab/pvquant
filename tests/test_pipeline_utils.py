"""Pipeline yardımcı fonksiyonları için birim testler."""
from __future__ import annotations

import pandas as pd
import pytest

from pvquant.pipeline.utils import (
    _detect_timestep_hours,
    _detect_timestep_minutes,
)


class TestDetectTimestepHours:
    """_detect_timestep_hours() testleri."""

    def test_hourly(self):
        """1 saatlik veri -> 1.0."""
        idx = pd.date_range("2024-01-01", periods=24, freq="1h")
        assert _detect_timestep_hours(idx) == pytest.approx(1.0)

    def test_thirty_minutes(self):
        """30 dakikalık veri -> 0.5."""
        idx = pd.date_range("2024-01-01", periods=48, freq="30min")
        assert _detect_timestep_hours(idx) == pytest.approx(0.5)

    def test_fifteen_minutes(self):
        """15 dakikalık veri -> 0.25."""
        idx = pd.date_range("2024-01-01", periods=96, freq="15min")
        assert _detect_timestep_hours(idx) == pytest.approx(0.25)

    def test_five_minutes(self):
        """5 dakikalık veri -> 5/60 = 0.0833..."""
        idx = pd.date_range("2024-01-01", periods=288, freq="5min")
        assert _detect_timestep_hours(idx) == pytest.approx(5 / 60)

    def test_one_minute(self):
        """1 dakikalık veri -> 1/60 = 0.01667..."""
        idx = pd.date_range("2024-01-01", periods=1440, freq="1min")
        assert _detect_timestep_hours(idx) == pytest.approx(1 / 60)

    def test_too_few_records(self):
        """1 kayıt -> ValueError."""
        idx = pd.DatetimeIndex(["2024-01-01 00:00"])
        with pytest.raises(ValueError, match="En az 2 kayıt"):
            _detect_timestep_hours(idx)

    def test_inconsistent_gaps(self):
        """Tutarsız adımlar -> ValueError."""
        # 15 dk, 15 dk, sonra 2 saat boşluk, sonra 15 dk
        # %90 tutarlılık eşiğini geçemez
        idx = pd.DatetimeIndex([
            "2024-01-01 00:00",
            "2024-01-01 00:15",
            "2024-01-01 00:30",
            "2024-01-01 02:30",  # 2 saat boşluk
            "2024-01-01 02:45",
        ])
        with pytest.raises(ValueError, match="tutarsız"):
            _detect_timestep_hours(idx)


class TestDetectTimestepMinutes:
    """_detect_timestep_minutes() testleri (dakika versiyonu)."""

    def test_hourly(self):
        idx = pd.date_range("2024-01-01", periods=24, freq="1h")
        assert _detect_timestep_minutes(idx) == 60

    def test_thirty_minutes(self):
        idx = pd.date_range("2024-01-01", periods=48, freq="30min")
        assert _detect_timestep_minutes(idx) == 30

    def test_fifteen_minutes(self):
        idx = pd.date_range("2024-01-01", periods=96, freq="15min")
        assert _detect_timestep_minutes(idx) == 15

    def test_five_minutes(self):
        idx = pd.date_range("2024-01-01", periods=288, freq="5min")
        assert _detect_timestep_minutes(idx) == 5

    def test_one_minute(self):
        idx = pd.date_range("2024-01-01", periods=1440, freq="1min")
        assert _detect_timestep_minutes(idx) == 1


class TestRealWorldPatterns:
    """Gerçek dünya SCADA veri örnekleri."""

    def test_daylight_savings_hourly(self):
        """DST geçişli saatlik veri hala tespit edilir (medyan robust)."""
        # 25 saatlik gün (DST sonu) — 1 saatlik veri kalıbı korunmalı
        idx = pd.date_range("2024-11-03", periods=25, freq="1h")
        assert _detect_timestep_hours(idx) == pytest.approx(1.0)

    def test_partial_data_gap(self):
        """Küçük boşluk (%10'dan az) -> yine de tespit."""
        # 100 saatlik veri, 5 saat eksik = %95 tutarlılık, OK
        idx1 = pd.date_range("2024-01-01", periods=50, freq="1h")
        idx2 = pd.date_range("2024-01-03 06:00", periods=45, freq="1h")
        idx = idx1.append(idx2)
        assert _detect_timestep_hours(idx) == pytest.approx(1.0)
