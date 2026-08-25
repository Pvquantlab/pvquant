"""v2.205 — gunluk_toplam saf fonksiyonu (DB'siz).

Kurallar sinanir:
- tam yerel gun: p50 toplami dogru, saat_sayisi 24
- <20 saatlik kismi gun: None (beklenti YAZILMAZ)
- p10 kolonunda tek NaN bile varsa p10_kwh None, p50 yine dolu
- yerel gun siniri: Istanbul gunu UTC 21:00'de baslar — pencere dogru kayar
"""
import numpy as np
import pandas as pd

from apps.worker.main import gunluk_toplam

TZ = "Europe/Istanbul"


def _cerceve(bas_utc: str, saat: int, p50=100.0, p10=80.0, p90=120.0):
    ix = pd.date_range(bas_utc, periods=saat, freq="h", tz="UTC")
    return pd.DataFrame({"p50_kw": [p50] * saat,
                         "p10_kw": [p10] * saat,
                         "p90_kw": [p90] * saat}, index=ix)


def test_tam_gun_toplamlari():
    # 25 Agu Istanbul gunu = 24 Agu 21:00 UTC .. 25 Agu 21:00 UTC
    df = _cerceve("2026-08-24 21:00", 24)
    t = gunluk_toplam(df, TZ, "2026-08-25")
    assert t is not None
    assert t["saat_sayisi"] == 24
    assert t["p50_kwh"] == 2400.0
    assert t["p10_kwh"] == 1920.0 and t["p90_kwh"] == 2880.0


def test_kismi_gun_yazilmaz():
    df = _cerceve("2026-08-24 21:00", 12)     # gunun yarisi
    assert gunluk_toplam(df, TZ, "2026-08-25") is None


def test_bant_nan_ise_bant_toplami_null_p50_dolu():
    df = _cerceve("2026-08-24 21:00", 24)
    df.iloc[5, df.columns.get_loc("p10_kw")] = np.nan
    t = gunluk_toplam(df, TZ, "2026-08-25")
    assert t is not None
    assert t["p50_kwh"] == 2400.0
    assert t["p10_kwh"] is None               # kismi bant toplami yaniltir
    assert t["p90_kwh"] == 2880.0


def test_yerel_gun_siniri_komsu_gunu_almaz():
    # 48 saatlik cerceve; yalniz 25 Agu yerel gununun 24 saati sayilmali
    df = _cerceve("2026-08-23 21:00", 48)
    t = gunluk_toplam(df, TZ, "2026-08-24")
    assert t is not None and t["saat_sayisi"] == 24
