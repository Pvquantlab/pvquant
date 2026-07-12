"""Ingestion katmanı uçtan uca testleri.

Her test, sahada gerçekten karşılaşılan bir 'kirli dosya' senaryosunu
sentetik olarak üretir ve pipeline'ın onu doğru normalize ettiğini
doğrular.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pvquant.io.ingestion import (
    RowFlag, TemplateStore, ingest_file, preview_file,
)

LAT, LON, CAP_KWP = 37.87, 32.49, 4514.0
TZ = "Europe/Istanbul"
RNG = np.random.default_rng(7)


def _hourly_power_profile(n_days: int, tz: str) -> pd.Series:
    """Gerçekçi saatlik üretim: GÜNEŞ öğlesinde pik yapan çan eğrisi.

    Boylam 32.5°E'de güneş öğlesi ~09:50 UTC'dir; UTC profillerde bell
    buna hizalanmazsa doğrulamanın gece kuralı haklı olarak alarm verir.
    """
    times = pd.date_range("2025-03-01", periods=n_days * 24, freq="h", tz=tz)
    hour = times.hour + times.minute / 60
    center = 12.7 if tz != "UTC" else 9.8
    width = 13 if tz != "UTC" else 12
    bell = np.clip(np.sin(np.pi * (hour - (center - width / 2)) / width), 0, None) ** 1.6
    power = CAP_KWP * 0.82 * bell * (0.7 + 0.3 * RNG.uniform(size=len(times)))
    return pd.Series(power.round(1), index=times)


# ---------------------------------------------------------------------------
# Senaryo 1: Türkçe FusionSolar tarzı — cp1254, ';', ondalık virgül,
# 4 satır meta, yerel saat, Türkçe kolon adları
# ---------------------------------------------------------------------------

@pytest.fixture
def turkish_csv(tmp_path):
    p = _hourly_power_profile(30, TZ)
    lines = [
        "Santral;MERKAS GES;;",
        "Rapor Aralığı;01.03.2025 - 30.03.2025;;",
        "Oluşturma;31.03.2025 09:15;;",
        ";;;",
        "Tarih Saat;Aktif Güç(kW);Ortam Sıcaklığı(°C);Işınım(W/m2)",
    ]
    for t, v in p.items():
        local = t.tz_localize(None)
        val = f"{v:.1f}".replace(".", ",")
        temp = f"{15 + 10 * np.sin(local.hour / 24 * np.pi):.1f}".replace(".", ",")
        poa = f"{max(0, v / CAP_KWP * 1000):.0f}"
        lines.append(f"{local:%d.%m.%Y %H:%M};{val};{temp};{poa}")
    path = tmp_path / "fusionsolar_tr.csv"
    path.write_bytes("\r\n".join(lines).encode("cp1254"))
    return path, p


def test_turkish_fusionsolar_end_to_end(turkish_csv):
    path, original = turkish_csv
    pv = preview_file(path)

    assert pv.file_format.encoding == "cp1254"
    assert pv.file_format.delimiter == ";"
    assert pv.file_format.decimal == ","
    assert pv.file_format.header_row == 4
    assert pv.mapping.timestamp == "Tarih Saat"
    assert pv.mapping.power == "Aktif Güç(kW)"
    assert pv.mapping.temp_ambient == "Ortam Sıcaklığı(°C)"
    assert pv.mapping.poa_irradiance == "Işınım(W/m2)"

    result = ingest_file(
        path, capacity_kwp=CAP_KWP, latitude=LAT, longitude=LON,
        source_timezone=TZ, file_format=pv.file_format, mapping=pv.mapping,
    )
    # UTC'ye çevrildi mi? (Istanbul = UTC+3)
    assert str(result.data.index.tz) == "UTC"
    first_local = original.index[0]
    assert result.data.index[0] == first_local.tz_convert("UTC")
    # Değerler ondalık virgüle rağmen doğru okundu mu?
    got = result.data["power_kw"].iloc[:100].values
    want = original.iloc[:100].round(1).values
    np.testing.assert_allclose(got, want, atol=0.06)
    # Kalite: her satır geçerli, gece üretimi uyarısı YOK
    assert result.report.valid_fraction > 0.98
    assert not any("saat dilimi" in w for w in result.report.warnings)


# ---------------------------------------------------------------------------
# Senaryo 2: MW birimli, virgül ayraçlı, UTC zamanlı dosya
# ---------------------------------------------------------------------------

def test_mw_unit_detection(tmp_path):
    p = _hourly_power_profile(15, "UTC")
    df = pd.DataFrame({
        "Datetime": p.index.tz_localize(None).strftime("%Y-%m-%d %H:%M"),
        "Active Power (MW)": (p.values / 1000).round(4),
    })
    path = tmp_path / "mw_file.csv"
    df.to_csv(path, index=False)

    result = ingest_file(path, capacity_kwp=CAP_KWP, latitude=LAT,
                         longitude=LON, source_timezone="UTC")
    assert result.transform.power_unit == "MW"
    # kW'a çevrilmiş olmalı
    np.testing.assert_allclose(
        result.data["power_kw"].iloc[:50].values,
        p.iloc[:50].values, rtol=0.01,
    )


# ---------------------------------------------------------------------------
# Senaryo 3: 15 dakikalık, yalnız enerji (kWh) kolonu → saatlik güce
# ---------------------------------------------------------------------------

def test_energy_only_15min_to_hourly_power(tmp_path):
    times = pd.date_range("2025-05-01", periods=10 * 96, freq="15min", tz="UTC")
    hour = times.hour + times.minute / 60
    bell = np.clip(np.sin(np.pi * (hour - 3.3) / 13), 0, None) ** 1.6
    power_kw = CAP_KWP * 0.8 * bell
    energy_kwh_15 = power_kw * 0.25          # 15 dk enerji = P × 0.25h

    df = pd.DataFrame({
        "Time": times.tz_localize(None).strftime("%Y-%m-%d %H:%M"),
        "Yield(kWh)": energy_kwh_15.round(3),
    })
    path = tmp_path / "energy15.csv"
    df.to_csv(path, index=False)

    result = ingest_file(path, capacity_kwp=CAP_KWP, latitude=LAT,
                         longitude=LON, source_timezone="UTC")
    assert result.transform.energy_to_power is True
    assert result.transform.timestep_minutes == 60
    # Saatlik enerji toplamı = 4 × 15dk; güç = o toplam / 1h
    hourly_expected = pd.Series(energy_kwh_15, index=times).resample("1h").sum()
    np.testing.assert_allclose(
        result.data["power_kw"].values,
        hourly_expected.values, rtol=1e-3,   # CSV 3 ondalıkla yazıldı
    )


# ---------------------------------------------------------------------------
# Senaryo 4: Saat dilimi HATASI — UTC veri "yerel" diye yüklenirse
# gece üretimi bayrağı ve uyarı üretilmeli
# ---------------------------------------------------------------------------

def test_timezone_mistake_triggers_night_warning(tmp_path):
    p = _hourly_power_profile(20, TZ)          # gerçek: Istanbul yereli
    df = pd.DataFrame({
        "Time": p.index.tz_localize(None).strftime("%Y-%m-%d %H:%M"),
        "Power(kW)": p.values.round(1),
    })
    path = tmp_path / "tz_mistake.csv"
    df.to_csv(path, index=False)

    # Kullanıcı yanlışlıkla "UTC" seçti → üretim 3 saat kayar
    result = ingest_file(path, capacity_kwp=CAP_KWP, latitude=LAT,
                         longitude=LON, source_timezone="UTC")
    n_night = result.report.flag_counts.get(RowFlag.NIGHT_PRODUCTION.value, 0)
    assert n_night > 0
    assert any("saat dilimi" in w for w in result.report.warnings)


# ---------------------------------------------------------------------------
# Senaryo 5: Kalite kuralları — negatif, kapasite üstü, donmuş değer
# ---------------------------------------------------------------------------

def test_quality_flags(tmp_path):
    p = _hourly_power_profile(10, "UTC")
    vals = p.values.copy()
    vals[30] = -500.0                    # büyük negatif
    vals[40] = CAP_KWP * 1.5             # kapasite üstü
    vals[56:64] = 1234.5                 # 8 saat donmuş (08-15 UTC, gün ortası)
    df = pd.DataFrame({
        "Time": p.index.tz_localize(None).strftime("%Y-%m-%d %H:%M"),
        "Power(kW)": vals.round(1),
    })
    path = tmp_path / "quality.csv"
    df.to_csv(path, index=False)

    result = ingest_file(path, capacity_kwp=CAP_KWP, latitude=LAT,
                         longitude=LON, source_timezone="UTC")
    fc = result.report.flag_counts
    assert fc.get(RowFlag.NEGATIVE_POWER.value, 0) >= 1
    assert fc.get(RowFlag.OVER_CAPACITY.value, 0) >= 1
    assert fc.get(RowFlag.FROZEN_VALUE.value, 0) >= 4
    # to_clean_frame bayraklıları dışlar
    clean = result.to_clean_frame()
    assert len(clean) == result.report.n_rows_valid
    assert "flag" not in clean.columns
    assert "timestamp" in clean.columns


# ---------------------------------------------------------------------------
# Senaryo 6: Şablon döngüsü — kaydet, eşleştir, yeniden kullan
# ---------------------------------------------------------------------------

def test_template_roundtrip(turkish_csv, tmp_path):
    path, _ = turkish_csv
    store = TemplateStore(tmp_path / "templates")

    pv1 = preview_file(path, template_store=store)
    assert pv1.matched_template is None          # ilk sefer: şablon yok

    result = ingest_file(
        path, capacity_kwp=CAP_KWP, latitude=LAT, longitude=LON,
        source_timezone=TZ, file_format=pv1.file_format, mapping=pv1.mapping,
    )
    store.save("fusionsolar_tr_v1", result.to_template())

    pv2 = preview_file(path, template_store=store)  # ikinci sefer
    assert pv2.matched_template == "fusionsolar_tr_v1"
    assert pv2.mapping.power == "Aktif Güç(kW)"