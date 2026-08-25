"""v2.203 — dogus/batis saf hesabi (pvlib SPA, DB'siz).

Konya (37.87K, 32.49D, Europe/Istanbul) icin astronomik akil-sagligi:
- dogus < batis, ikisi de ayni yerel gunun icinde
- yaz gundonumu gun uzunlugu ~14-15 saat, kis ~9-10 saat (genis bantla)
- istenen her gun icin bir satir (orta enlemde kutup gecesi yok)
"""
import pandas as pd

from pvquant.services.gunes_service import _dogus_batis_hesapla

LAT, LON, TZ = 37.87, 32.49, "Europe/Istanbul"


def _saat_farki(satir) -> float:
    d = pd.Timestamp(satir["dogus_utc"])
    b = pd.Timestamp(satir["batis_utc"])
    return (b - d).total_seconds() / 3600.0


def test_yaz_gunu_uzun_kis_gunu_kisa():
    yaz = _dogus_batis_hesapla(LAT, LON, TZ, ["2026-06-21"])
    kis = _dogus_batis_hesapla(LAT, LON, TZ, ["2026-12-21"])
    assert len(yaz) == 1 and len(kis) == 1
    assert 13.5 < _saat_farki(yaz[0]) < 15.5
    assert 8.5 < _saat_farki(kis[0]) < 10.5
    assert _saat_farki(yaz[0]) > _saat_farki(kis[0])


def test_dogus_batistan_once_ve_yerel_gun_icinde():
    rows = _dogus_batis_hesapla(LAT, LON, TZ, ["2026-08-26", "2026-08-27"])
    assert [r["gun"] for r in rows] == ["2026-08-26", "2026-08-27"]
    for r in rows:
        d = pd.Timestamp(r["dogus_utc"]).tz_convert(TZ)
        b = pd.Timestamp(r["batis_utc"]).tz_convert(TZ)
        assert d < b
        assert str(d.date()) == r["gun"] == str(b.date())
