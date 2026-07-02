"""Pipeline yardımcı fonksiyonları için birim testler."""
from __future__ import annotations

import pandas as pd
import pytest

from pvquant.pipeline.utils import (
    _detect_timestep_hours,
    _detect_timestep_minutes,
)
from pvquant.io.meteo import MeteoData


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


# --- Faz 1.6 Adim 3.2: Meteo Alignment Tests [BEGIN] ---
def _make_meteo(index: pd.DatetimeIndex, with_optionals: bool = True) -> MeteoData:
    """Test helper: sentetik MeteoData olustur.

    GHI: 0-1000 W/m² arasi sinusoidal (gunduz-gece kalibi taklidi).
    temp_air: 20 + 10*sin (24h period), yaklasik 10-30 °C.
    wind_speed_10m: sabit 3.0 m/s.
    """
    import numpy as np
    n = len(index)
    hours_from_start = np.arange(n) * (
        (index[1] - index[0]).total_seconds() / 3600.0 if n > 1 else 1.0
    )
    # Basit sinusoidal GHI: gunduz pozitif, gece 0 civari
    ghi_raw = 500 * np.sin(np.pi * (hours_from_start % 24) / 12)
    ghi_values = np.clip(ghi_raw, 0, None)
    temp_values = 20 + 10 * np.sin(2 * np.pi * hours_from_start / 24)
    wind_values = np.full(n, 3.0)

    kwargs = dict(
        ghi=pd.Series(ghi_values, index=index),
        temp_air=pd.Series(temp_values, index=index),
        wind_speed_10m=pd.Series(wind_values, index=index),
        latitude=37.87,
        longitude=32.49,
        timezone="UTC",
    )
    if with_optionals:
        kwargs["relative_humidity"] = pd.Series(np.full(n, 50.0), index=index)
        kwargs["cloud_cover"] = pd.Series(np.full(n, 20.0), index=index)
    else:
        kwargs["relative_humidity"] = None
        kwargs["cloud_cover"] = None

    return MeteoData(**kwargs)


class TestAlignMeteoToScada:
    """_align_meteo_to_scada() testleri."""

    def test_identity_same_index(self):
        """Ayni index -> ayni degerler (identity)."""
        from pvquant.pipeline.utils import _align_meteo_to_scada
        idx = pd.date_range("2024-06-01", periods=24, freq="1h")
        meteo = _make_meteo(idx)
        aligned = _align_meteo_to_scada(meteo, idx)

        assert len(aligned.ghi) == 24
        pd.testing.assert_series_equal(
            aligned.ghi, meteo.ghi, check_names=False
        )
        pd.testing.assert_series_equal(
            aligned.temp_air, meteo.temp_air, check_names=False
        )

    def test_upsample_1h_to_15min(self):
        """1h meteo -> 15dk SCADA index: 24 nokta -> 96 nokta."""
        from pvquant.pipeline.utils import _align_meteo_to_scada
        meteo_idx = pd.date_range("2024-06-01", periods=24, freq="1h")
        scada_idx = pd.date_range("2024-06-01", periods=96, freq="15min")
        meteo = _make_meteo(meteo_idx)
        aligned = _align_meteo_to_scada(meteo, scada_idx)

        assert len(aligned.ghi) == 96
        # Tam saat basi noktalar orijinal deger ile ayni olmali
        assert aligned.ghi.loc["2024-06-01 12:00"] == pytest.approx(
            meteo.ghi.loc["2024-06-01 12:00"]
        )
        # 12:15 icin 12:00 ve 13:00 arasinda olmali
        v_12_00 = meteo.ghi.loc["2024-06-01 12:00"]
        v_13_00 = meteo.ghi.loc["2024-06-01 13:00"]
        v_12_15 = aligned.ghi.loc["2024-06-01 12:15"]
        assert min(v_12_00, v_13_00) <= v_12_15 <= max(v_12_00, v_13_00)

    def test_upsample_1h_to_5min(self):
        """1h meteo -> 5dk SCADA index: 24 nokta -> 288 nokta."""
        from pvquant.pipeline.utils import _align_meteo_to_scada
        meteo_idx = pd.date_range("2024-06-01", periods=24, freq="1h")
        scada_idx = pd.date_range("2024-06-01", periods=288, freq="5min")
        meteo = _make_meteo(meteo_idx)
        aligned = _align_meteo_to_scada(meteo, scada_idx)

        assert len(aligned.ghi) == 288
        assert len(aligned.temp_air) == 288
        assert len(aligned.wind_speed_10m) == 288

    def test_preserves_none_optionals(self):
        """humidity ve cloud_cover None ise None kalmali."""
        from pvquant.pipeline.utils import _align_meteo_to_scada
        meteo_idx = pd.date_range("2024-06-01", periods=24, freq="1h")
        scada_idx = pd.date_range("2024-06-01", periods=96, freq="15min")
        meteo = _make_meteo(meteo_idx, with_optionals=False)
        aligned = _align_meteo_to_scada(meteo, scada_idx)

        assert aligned.relative_humidity is None
        assert aligned.cloud_cover is None

    def test_preserves_optionals_when_present(self):
        """humidity ve cloud_cover varsa hizalanmali."""
        from pvquant.pipeline.utils import _align_meteo_to_scada
        meteo_idx = pd.date_range("2024-06-01", periods=24, freq="1h")
        scada_idx = pd.date_range("2024-06-01", periods=96, freq="15min")
        meteo = _make_meteo(meteo_idx, with_optionals=True)
        aligned = _align_meteo_to_scada(meteo, scada_idx)

        assert aligned.relative_humidity is not None
        assert aligned.cloud_cover is not None
        assert len(aligned.relative_humidity) == 96
        assert len(aligned.cloud_cover) == 96

    def test_preserves_metadata(self):
        """lat/lon/timezone alanlari kopyalanmali."""
        from pvquant.pipeline.utils import _align_meteo_to_scada
        meteo_idx = pd.date_range("2024-06-01", periods=24, freq="1h")
        scada_idx = pd.date_range("2024-06-01", periods=96, freq="15min")
        meteo = _make_meteo(meteo_idx)
        aligned = _align_meteo_to_scada(meteo, scada_idx)

        assert aligned.latitude == meteo.latitude
        assert aligned.longitude == meteo.longitude
        assert aligned.timezone == meteo.timezone

    def test_out_of_range_bounds(self):
        """Hedef index meteo araligi disina tasarsa uc degerler tekrar edilir."""
        from pvquant.pipeline.utils import _align_meteo_to_scada
        meteo_idx = pd.date_range("2024-06-01 06:00", periods=12, freq="1h")
        # SCADA meteo baslamadan once basliyor
        scada_idx = pd.date_range("2024-06-01 04:00", periods=64, freq="15min")
        meteo = _make_meteo(meteo_idx)
        aligned = _align_meteo_to_scada(meteo, scada_idx)

        # Uc noktalarda NaN olmamali (backward fill sayesinde)
        assert not aligned.ghi.isna().any()
        assert not aligned.temp_air.isna().any()

    def test_downsample_15min_to_1h(self):
        """15dk meteo -> 1h SCADA index (nadir ama olabilir)."""
        from pvquant.pipeline.utils import _align_meteo_to_scada
        meteo_idx = pd.date_range("2024-06-01", periods=96, freq="15min")
        scada_idx = pd.date_range("2024-06-01", periods=24, freq="1h")
        meteo = _make_meteo(meteo_idx)
        aligned = _align_meteo_to_scada(meteo, scada_idx)

        assert len(aligned.ghi) == 24
        # Tam saat basi noktalarda orijinal degerlerle uyusmali
        pd.testing.assert_series_equal(
            aligned.ghi,
            meteo.ghi.loc[scada_idx],
            check_names=False,
        )
# --- Faz 1.6 Adim 3.2: Meteo Alignment Tests [END] ---
