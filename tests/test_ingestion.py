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
    MappingFailedError, RowFlag, TemplateStore, ingest_file, preview_file,
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
# Senaryo 1: Türkçe FusionSolar tarzı
# ---------------------------------------------------------------------------

@pytest.fixture
def turkish_csv(tmp_path):
    p = _hourly_power_profile(30, TZ)
    lines = [
        "Santral;REFPLANT GES;;",
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
    assert str(result.data.index.tz) == "UTC"
    first_local = original.index[0]
    assert result.data.index[0] == first_local.tz_convert("UTC")
    got = result.data["power_kw"].iloc[:100].values
    want = original.iloc[:100].round(1).values
    np.testing.assert_allclose(got, want, atol=0.06)
    assert result.report.valid_fraction > 0.98
    assert not any("saat dilimi" in w for w in result.report.warnings)


# ---------------------------------------------------------------------------
# Senaryo 2: MW birimli, UTC zamanlı
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
    np.testing.assert_allclose(
        result.data["power_kw"].iloc[:50].values,
        p.iloc[:50].values, rtol=0.01,
    )


# ---------------------------------------------------------------------------
# Senaryo 3: 15 dakikalık, yalnız enerji → saatlik güce
# ---------------------------------------------------------------------------

def test_energy_only_15min_to_hourly_power(tmp_path):
    times = pd.date_range("2025-05-01", periods=10 * 96, freq="15min", tz="UTC")
    hour = np.array(times.hour) + np.array(times.minute) / 60
    bell = np.clip(np.sin(np.pi * (hour - 3.3) / 13), 0, None) ** 1.6
    power_kw = CAP_KWP * 0.8 * bell
    energy_kwh_15 = power_kw * 0.25

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
    hourly_expected = pd.Series(energy_kwh_15, index=times).resample("1h").sum()
    np.testing.assert_allclose(
        result.data["power_kw"].values,
        hourly_expected.values, rtol=1e-3,
    )


# ---------------------------------------------------------------------------
# Senaryo 4: Saat dilimi hatası → gece üretimi uyarısı
# ---------------------------------------------------------------------------

def test_timezone_mistake_triggers_night_warning(tmp_path):
    p = _hourly_power_profile(20, TZ)
    df = pd.DataFrame({
        "Time": p.index.tz_localize(None).strftime("%Y-%m-%d %H:%M"),
        "Power(kW)": p.values.round(1),
    })
    path = tmp_path / "tz_mistake.csv"
    df.to_csv(path, index=False)

    result = ingest_file(path, capacity_kwp=CAP_KWP, latitude=LAT,
                         longitude=LON, source_timezone="UTC")
    n_night = result.report.flag_counts.get(RowFlag.NIGHT_PRODUCTION.value, 0)
    assert n_night > 0
    assert any("saat dilimi" in w for w in result.report.warnings)


# ---------------------------------------------------------------------------
# Senaryo 5: Kalite kuralları
# ---------------------------------------------------------------------------

def test_quality_flags(tmp_path):
    p = _hourly_power_profile(10, "UTC")
    vals = p.values.copy()
    vals[30] = -500.0
    vals[40] = CAP_KWP * 1.5
    vals[56:64] = 1234.5
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
    clean = result.to_clean_frame()
    assert len(clean) == result.report.n_rows_valid
    assert "flag" not in clean.columns
    assert "timestamp" in clean.columns


# ---------------------------------------------------------------------------
# Senaryo 6: Şablon döngüsü
# ---------------------------------------------------------------------------

def test_template_roundtrip(turkish_csv, tmp_path):
    path, _ = turkish_csv
    store = TemplateStore(tmp_path / "templates")

    pv1 = preview_file(path, template_store=store)
    assert pv1.matched_template is None

    result = ingest_file(
        path, capacity_kwp=CAP_KWP, latitude=LAT, longitude=LON,
        source_timezone=TZ, file_format=pv1.file_format, mapping=pv1.mapping,
    )
    store.save("fusionsolar_tr_v1", result.to_template())

    pv2 = preview_file(path, template_store=store)
    assert pv2.matched_template == "fusionsolar_tr_v1"
    assert pv2.mapping.power == "Aktif Güç(kW)"


# ---------------------------------------------------------------------------
# Senaryo 7: REFPLANT xlsx — başlık 5. satırda
# ---------------------------------------------------------------------------

def test_refplant_xlsx_header_row_detection(tmp_path):
    """REFPLANT xlsx dosyalarında başlık genellikle 5. satırda olur;
    üstünde 'Tesis Raporu_REFPLANT GES' ve boş satırlar bulunur."""
    p = _hourly_power_profile(10, TZ)

    meta_rows = [
        ["Tesis Raporu_REFPLANT GES"] + [None] * 3,
        ["Rapor Aralığı", "01.03.2025 - 10.03.2025", None, None],
        ["Kapasite", "4514 kWp", None, None],
        [None, None, None, None],
    ]
    header_row = ["Zaman", "Aktif Güç (kW)", "POA Işınım (W/m2)", "Ortam (°C)"]
    data_rows = []
    for t, v in p.items():
        local = t.tz_localize(None)
        data_rows.append([
            local.strftime("%Y-%m-%d %H:%M"),
            round(float(v), 1),
            round(max(0, float(v) / CAP_KWP * 1000), 0),
            round(15 + 10 * np.sin(local.hour / 24 * np.pi), 1),
        ])

    all_rows = meta_rows + [header_row] + data_rows
    df = pd.DataFrame(all_rows)
    path = tmp_path / "refplant.xlsx"
    df.to_excel(path, index=False, header=False)

    pv = preview_file(path)
    assert pv.file_format.header_row == 4
    assert pv.mapping.timestamp == "Zaman"
    assert pv.mapping.power == "Aktif Güç (kW)"

    result = ingest_file(
        path, capacity_kwp=CAP_KWP, latitude=LAT, longitude=LON,
        source_timezone=TZ, file_format=pv.file_format, mapping=pv.mapping,
    )
    assert result.report.valid_fraction > 0.95


# ---------------------------------------------------------------------------
# Senaryo 8: Kümülatif ömür sayacı → aralık enerjisi
# ---------------------------------------------------------------------------

def test_cumulative_energy_counter_diff(tmp_path):
    """SolarEdge Etotal, Enphase whLifetime: ömür sayacı (monoton artan).
    Aralık enerjisi olarak yorumlanırsa güç yüzlerce kat yanlış çıkar."""
    times = pd.date_range("2025-05-01", periods=200, freq="h", tz="UTC")
    hour = np.array(times.hour) + np.array(times.minute) / 60
    bell = np.clip(np.sin(np.pi * (hour - 3.3) / 13), 0, None) ** 1.6
    interval_energy = pd.Series(CAP_KWP * 0.8 * bell, index=times)
    cumulative = interval_energy.cumsum() + 12_345_000  # başlangıçta yüksek

    df = pd.DataFrame({
        "Time": times.tz_localize(None).strftime("%Y-%m-%d %H:%M"),
        "Etotal(kWh)": cumulative.round(3).values,
    })
    path = tmp_path / "solaredge_etotal.csv"
    df.to_csv(path, index=False)

    result = ingest_file(path, capacity_kwp=CAP_KWP, latitude=LAT,
                         longitude=LON, source_timezone="UTC")
    assert result.transform.energy_cumulative is True
    # İlk satır NaN olur (diff), sonraki değerler ~aralık enerjisi
    expected_power = interval_energy.values[1:]
    got_power = result.data["power_kw"].values[1:len(expected_power) + 1]
    np.testing.assert_allclose(got_power, expected_power, rtol=0.01)


# ---------------------------------------------------------------------------
# Senaryo 9: SMA Sunny Explorer — 7 satır metadata
# ---------------------------------------------------------------------------

def test_sma_sunny_explorer_pattern(tmp_path):
    """SMA export deseni: 7 satır metadata, sonra başlık."""
    p = _hourly_power_profile(15, "UTC")
    lines = [
        "sep=;",
        "Version;1.5.0;;",
        "Anlage;Test PV;;",
        "Zeitraum;01.05.2025 - 15.05.2025;;",
        "Zeitzone;UTC+0;;",
        "Aufloesung;60 Min;;",
        ";;;",
        "Zeit;Pac (kW);E-Total (kWh);T-Modul (°C)",
    ]
    cumulative = pd.Series(p.values, index=p.index).cumsum() + 1_000_000
    for t, v, e in zip(p.index, p.values, cumulative.values):
        local = t.tz_localize(None)
        val = f"{v:.2f}".replace(".", ",")
        etotal = f"{e:.2f}".replace(".", ",")
        temp = f"{25 + 15 * v / CAP_KWP:.1f}".replace(".", ",")
        lines.append(f"{local:%d.%m.%Y %H:%M};{val};{etotal};{temp}")

    path = tmp_path / "sma_sunny.csv"
    path.write_bytes("\r\n".join(lines).encode("cp1254"))

    pv = preview_file(path)
    assert pv.file_format.delimiter == ";"
    assert pv.file_format.decimal == ","
    assert pv.mapping.power == "Pac (kW)"
    assert pv.mapping.energy == "E-Total (kWh)"


# ---------------------------------------------------------------------------
# Senaryo 10: Kaggle Anikannal deseni — BÜYÜK_HARF alt çizgi
# ---------------------------------------------------------------------------

def test_kaggle_upper_underscore_pattern(tmp_path):
    """Kaggle Anikannal Hindistan santrali deseni: AC_POWER, AMBIENT_TEMPERATURE
    gibi büyük harf underscore. Fuzzy eşleşme bunları yakalamalı."""
    p = _hourly_power_profile(15, "UTC")
    df = pd.DataFrame({
        "DATE_TIME": p.index.tz_localize(None).strftime("%Y-%m-%d %H:%M"),
        "AC_POWER": p.values.round(1),
        "AMBIENT_TEMPERATURE": [20 + 5 * np.sin(h / 24 * np.pi) for h in p.index.hour],
        "IRRADIATION": [max(0, v / CAP_KWP * 1000) for v in p.values],
    })
    path = tmp_path / "kaggle_anikannal.csv"
    df.to_csv(path, index=False)

    pv = preview_file(path)
    assert pv.mapping.timestamp == "DATE_TIME"
    assert pv.mapping.power == "AC_POWER"
    assert pv.mapping.temp_ambient == "AMBIENT_TEMPERATURE"
    # IRRADIATION belirsiz — POA veya GHI olabilir; en az birine eşlenmeli
    assert pv.mapping.poa_irradiance == "IRRADIATION" or pv.mapping.ghi == "IRRADIATION"


# ---------------------------------------------------------------------------
# Senaryo 11: Alakasız dosya → MappingFailedError
# ---------------------------------------------------------------------------

def test_unrelated_file_raises_mapping_failed(tmp_path):
    """SCADA'yla alakasız bir dosya (mesela alışveriş listesi) yüklenirse
    otomatik eşleme pes etmeli, MappingFailedError fırlatmalı ki UI
    manuel eşleme ekranı kursun."""
    df = pd.DataFrame({
        "Ürün": ["Elma", "Armut", "Muz"],
        "Fiyat": [10.5, 8.0, 12.3],
        "Stok": [100, 50, 75],
    })
    path = tmp_path / "market.csv"
    df.to_csv(path, index=False)

    with pytest.raises(MappingFailedError) as exc_info:
        preview_file(path)

    err = exc_info.value
    # MappingFailedError fırlatıldı; kolon listesi ve sample_rows
    # CSV ayraç tespitine göre değişebilir (tek kolonda birleşik
    # gelebilir), önemli olan istisnanın yapılandırılmış bilgi
    # taşıması ve UI'ın manuel eşleme kurabilmesi.
    assert len(err.columns) > 0
    assert err.file_format is not None