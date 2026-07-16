"""Isinim birim normalizasyonu testleri (B1) — 14 Tem 2026.

Yasanan vaka: 'Toplam Isima (kWh/m2)' kolonu ham gecti, fizik 0.5 W/m2
sanip sifir uretti. Bu testler o hata sinifini kalici kilitler.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import pytest

from pvquant.io.ingestion.pipeline import ingest_file
from pvquant.io.ingestion.transform import normalize_irradiance_wm2


def _saat_index(n=72):
    return pd.date_range("2025-06-01 00:00", periods=n, freq="1h")


def _gunes_profili(n=72, tepe=1.0):
    """Basit gunduz cani: gece 0, ogle tepe."""
    idx = _saat_index(n)
    saat = idx.hour.values
    profil = np.clip(np.sin((saat - 5) / 14 * np.pi), 0, None) * tepe
    return idx, profil


def test_kwh_m2_adiyla_donusur():
    idx, p = _gunes_profili(tepe=1.05)  # kWh/m2 olceginde
    s = pd.Series(p, index=idx)
    out, unit, src = normalize_irradiance_wm2(s, "Toplam Işıma (kWh/m²)", 60)
    assert unit == "kWh/m2" and src == "ad"
    assert out.max() == pytest.approx(1050.0, rel=0.01)


def test_wh_m2_adiyla_donusur():
    idx, p = _gunes_profili(tepe=1050.0)  # Wh/m2 (saatlikte W/m2 ile ayni)
    out, unit, src = normalize_irradiance_wm2(
        pd.Series(p, index=idx), "POA (Wh/m2)", 60
    )
    assert unit == "Wh/m2" and src == "ad"
    assert out.max() == pytest.approx(1050.0, rel=0.01)


def test_w_m2_dokunulmaz():
    idx, p = _gunes_profili(tepe=980.0)
    out, unit, src = normalize_irradiance_wm2(
        pd.Series(p, index=idx), "POA Irradiance(W/m2)", 60
    )
    assert unit == "W/m2" and src == "ad"
    assert out.max() == pytest.approx(980.0, rel=0.01)


def test_birimsiz_ad_icerikten_yakalanir():
    idx, p = _gunes_profili(tepe=0.95)  # ad birimsiz, degerler kWh olceginde
    out, unit, src = normalize_irradiance_wm2(
        pd.Series(p, index=idx), "Isinim", 60
    )
    assert unit == "kWh/m2" and src == "icerik"
    assert out.max() == pytest.approx(950.0, rel=0.01)


def test_15dk_kwh_m2_carpani():
    idx = pd.date_range("2025-06-01", periods=96, freq="15min")
    s = pd.Series(0.25, index=idx)  # 15 dk'da 0.25 kWh/m2 = 1000 W/m2 ort
    out, unit, _ = normalize_irradiance_wm2(s, "Işıma (kWh/m²)", 15)
    assert unit == "kWh/m2"
    assert out.iloc[50] == pytest.approx(1000.0, rel=0.001)


def test_refplant_istatistik_exportu_uctan_uca(tmp_path):
    """REFPLANT vakasinin birebir taklidi: enerji-tek + kWh/m2 isinim.

    Dogrulanan iki sey:
      B1 — poa_global W/m2 olceginde cikar (gunduz yuzler),
      C  — power kolonu yokken 'Inverter Kazanci (kWh)' gucten turer.
    """
    idx, gunes = _gunes_profili(n=72, tepe=1.0)
    df = pd.DataFrame({
        "İstatistiksel dönem": idx.strftime("%Y-%m-%d %H:%M:%S"),
        "Toplam Işıma (kWh/m²)": np.round(gunes * 1.05, 3),
        "Ortalama Sıcaklık (°C)": 22 + 8 * gunes,
        "İnverter Kazancı (kWh)": np.round(gunes * 3800, 1),
    })
    yol = tmp_path / "stats_export.csv"
    df.to_csv(yol, index=False)

    res = ingest_file(
        str(yol), capacity_kwp=4514.0,
        latitude=37.87, longitude=32.49,
        source_timezone="Europe/Istanbul",
    )
    clean = res.data if hasattr(res, "data") else res[0]
    spec = getattr(res, "transform", None) or getattr(res, "spec", None)

    assert "poa_global" in clean.columns
    gunduz = clean["poa_global"].dropna()
    gunduz = gunduz[gunduz > 0]
    assert gunduz.max() > 300, "kWh/m2 -> W/m2 donusumu uygulanmamis!"

    assert "power_kw" in clean.columns
    assert clean["power_kw"].max() == pytest.approx(3800.0, rel=0.05)

    if spec is not None:
        assert getattr(spec, "irradiance_unit", None) == "kWh/m2"
        assert getattr(spec, "irradiance_unit_source", None) == "ad"
