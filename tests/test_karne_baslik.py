"""v2.71-E: karne basligi kac gun ortaladigini soyler; sayfa hangi
tarihleri kapsadigini yazar.
"""
import datetime as dt
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pvquant.reporting.styles import (karne_donem_metni,  # noqa: E402
                                      wmape_baslik)


def test_baslik_gercek_gun_sayisini_soyler():
    """Konya vakasi: 4 gun varken 30 yazamaz."""
    assert wmape_baslik(4) == "WMAPE (0-24s, 4 GÜN ORT.)"


def test_otuz_gun_yalnizca_gercekten_otuzken():
    assert "30 GÜN ORT." in wmape_baslik(30)
    for n in (1, 4, 29, 31, 120):
        assert "30 GÜN ORT." not in wmape_baslik(n)


def test_bos_kovada_gun_iddiasi_yok():
    """Veri yoksa hicbir sayi iddia edilmez (K1)."""
    m = wmape_baslik(0)
    assert m == "WMAPE (0-24s)"
    assert "ORT." not in m


def test_donem_araligi_yazilir():
    assert karne_donem_metni(dt.date(2026, 4, 15),
                             dt.date(2026, 4, 18)) == "15 – 18 Nisan 2026"


def test_tek_gun_tek_tarih_yazar():
    g = dt.date(2026, 4, 15)
    assert karne_donem_metni(g, g) == "15 Nisan 2026"


def test_ay_gecisi_bozulmaz():
    m = karne_donem_metni(dt.date(2026, 4, 28), dt.date(2026, 5, 3))
    assert "Nisan" in m and "Mayıs" in m


def test_pandas_timestamp_ile_calisir():
    """sk['date'] parse_dates ile Timestamp doner."""
    assert karne_donem_metni(pd.Timestamp("2026-04-15"),
                             pd.Timestamp("2026-04-18")) == "15 – 18 Nisan 2026"
