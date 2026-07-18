"""ui_kit grafik dumanı — Zeyilname v2.21 eki (P4-B ile öne alındı).
Bu gecenin regresyon sınıfını kilitler: üç grafik fonksiyonu sentetik
veriyle headless fig üretir; exception = fail. Streamlit'e gerek yok —
fonksiyonlar saf plotly döndürür.
KONUM: tests/test_ui_grafik_dumani.py
NOT: frontend/ import yolu repo düzenine göre (D-doğrulama): ya
sys.path'e frontend eklenir ya da paket importu kullanılır.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "frontend"))

import ui_kit  # noqa: E402


def test_gun_isigi_egrisi_string_saat_ve_none_gercek():
    """v2.21 regresyonunun birebir senaryosu: string saat + None gerçek."""
    saat = [f"{h:02d}:00" for h in range(24)]
    tahmin = [max(0, 2000 - abs(12 - h) * 260) for h in range(24)]
    gercek = [None] * 24                       # SCADA bayat günü
    fig = ui_kit.gun_isigi_egrisi(saat, gercek, tahmin, simdi_idx=6)
    assert fig is not None and len(fig.data) >= 1


def test_tahmin_grafigi_mod_c_bantli():
    idx = pd.date_range("2026-07-18", periods=48, freq="h",
                        tz="Europe/Istanbul")
    df = pd.DataFrame({"p50_kw": 1000.0, "p10_kw": 900.0,
                       "p90_kw": 1100.0}, index=idx)
    fig = ui_kit.tahmin_grafigi(df, "C")
    assert fig is not None and len(fig.data) >= 2   # bant + p50


def test_skill_grafigi_tek_nokta():
    """1-2 noktalı karne (erken günler) çizilebilmeli — çökmemeli."""
    piv = pd.DataFrame({"0-24": [45.1]},
                       index=[pd.Timestamp("2026-04-16").date()])
    fig = ui_kit.skill_grafigi(piv)
    assert fig is not None
