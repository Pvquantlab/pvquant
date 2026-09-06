"""v2.269 — açık arşiv ışınım yolu (ağsız: pvlib/arşiv monkeypatch)."""
import numpy as np
import pandas as pd
import pvlib

from pvquant import config
from pvquant.io import acik_nwp, arsiv_isinim

LAT, LON = 37.87, 32.49


def _pvgis_sahte(*a, **k):
    ix = pd.date_range("2023-06-01 00:09", periods=48, freq="h", tz="UTC")
    yuk = np.clip(60 * np.sin(np.pi * (ix.hour - 3) / 12), 0, None)           # güneş yüksekliği (°)
    return pd.DataFrame({"poa_direct": np.where(yuk > 0, 500.0, 0.0), "poa_sky_diffuse": np.where(yuk > 0, 100.0, 0.0),
                         "poa_ground_diffuse": 0.0, "solar_elevation": yuk, "temp_air": 25.0, "wind_speed": 2.0, "Int": 0}, index=ix), {}


def test_pvgis_df_kolonlar(monkeypatch):
    monkeypatch.setattr(pvlib.iotools, "get_pvgis_hourly", _pvgis_sahte)
    df = arsiv_isinim.pvgis_df(LAT, LON, 2023, 2023)
    assert df.index[0] == pd.Timestamp("2023-06-01 00:00", tz="UTC") and set(df.columns) >= {"ghi", "dni", "dhi", "temp_air", "wind_speed_10m"}
    ogle = df.loc["2023-06-01 09:00"]
    assert ogle["ghi"] == 600.0 and ogle["dhi"] == 100.0 and ogle["dni"] > 500.0 and df["ghi"].min() == 0.0
    assert arsiv_isinim.pvgis_df(LAT, LON, 2024, 2026).empty                  # SARAH-3 kapsamı 2005–2023


def test_gecmis_sirasi(monkeypatch):
    config.get_settings.cache_clear(); monkeypatch.delenv("PVQUANT_CAMS_EMAIL", raising=False)
    monkeypatch.setattr(acik_nwp, "arsivden_gecmis", lambda *a, **k: None)
    monkeypatch.setattr(pvlib.iotools, "get_pvgis_hourly", _pvgis_sahte)
    md = arsiv_isinim.gecmis(LAT, LON, "2023-06-01", "2023-06-02")
    assert md is not None and md.kaynak == "pvgis-sarah3"
    assert arsiv_isinim.gecmis(LAT, LON, "2026-08-01", "2026-08-05") is None  # 2023 sonrası, CAMS yok, NASA gecikmesi → dürüst None
    ix = pd.date_range("2026-08-01", periods=120, freq="h", tz="UTC")
    ars = acik_nwp._cerceve_to_meteodata(pd.DataFrame({"ghi": 100.0, "temp_air": 20.0, "wind_speed_10m": 1.0, "cloud_cover": 0.0}, index=ix), LAT, LON)
    monkeypatch.setattr(acik_nwp, "arsivden_gecmis", lambda *a, **k: ars)
    assert arsiv_isinim.gecmis(LAT, LON, "2026-08-01", "2026-08-05").kaynak == "acik-nwp"   # arşiv öncelikli


def test_cams_yolu(monkeypatch):
    config.get_settings.cache_clear(); monkeypatch.setenv("PVQUANT_CAMS_EMAIL", "ornek@ornek.com")
    monkeypatch.setattr(acik_nwp, "arsivden_gecmis", lambda *a, **k: None)
    ix = pd.date_range("2026-08-01 00:00", periods=5 * 24, freq="h", tz="UTC")
    monkeypatch.setattr(pvlib.iotools, "get_cams", lambda *a, **k: (pd.DataFrame({"ghi": 200.0, "dni": 300.0, "dhi": 80.0}, index=ix), {}))
    md = arsiv_isinim.gecmis(LAT, LON, "2026-08-01", "2026-08-05")
    assert md.kaynak == "cams" and md.temp_air.isna().all()                  # sıcaklık uydurulmaz: arşiv yoksa NaN
    config.get_settings.cache_clear()


def test_iklim_serisi(monkeypatch):
    monkeypatch.setattr(pvlib.iotools, "get_pvgis_hourly", _pvgis_sahte)
    df, ilk, son = arsiv_isinim.iklim_serisi(LAT, LON, 20)
    assert (ilk, son) == (2005, 2023) and "ghi" in df
