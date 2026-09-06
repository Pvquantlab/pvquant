"""v2.268 — Dalga 0: açık NWP okuyucu/harman/arşiv satırları (ağsız, DB'siz) + fasad yönlendirmesi."""
import numpy as np
import pandas as pd
import pytest
import xarray as xr

from pvquant.io import acik_nwp
from pvquant.io.meteo import MeteoData, MeteoIstemcisi, OpenMeteoClient

LAT, LON = 37.87, 32.49


def _ecmwf_sentetik(monkeypatch):
    """cfgrib.open_datasets yerine: 0.25° küçük ızgara, 3 saatlik 9 adım (0–24 s), biriktirilmiş ssrd/tp."""
    kosu = np.datetime64("2026-09-06T00:00:00")
    adim = np.array([np.timedelta64(3 * i, "h") for i in range(9)])
    lat = np.array([38.0, 37.75, 37.5]); lon = np.array([32.25, 32.5, 32.75])
    gecerli = kosu + adim
    saat = (adim / np.timedelta64(1, "h")).astype(float)
    # ssrd: gündüz (06–18 UTC değil, 03–15) J/m² birikimi — her 3 s adımda 600 W/m² × 10800 s
    guc = np.where((saat > 3) & (saat <= 15), 600.0, 0.0)
    ssrd = np.cumsum(guc * 10800.0)
    def alan(v):
        return xr.DataArray(np.broadcast_to(v[:, None, None], (9, 3, 3)).copy(), dims=("step", "latitude", "longitude"),
                            coords={"step": adim, "latitude": lat, "longitude": lon, "valid_time": ("step", gecerli), "time": kosu})
    ds1 = xr.Dataset({"ssrd": alan(ssrd), "tp": alan(np.cumsum(np.full(9, 0.0009)))})           # 0,9 mm / 3 s
    ds2 = xr.Dataset({"t2m": alan(np.full(9, 300.15)), "u10": alan(np.full(9, 3.0)), "v10": alan(np.full(9, 4.0))})
    ds3 = xr.Dataset({"tcc": alan(np.full(9, 0.25))})
    import cfgrib
    monkeypatch.setattr(cfgrib, "open_datasets", lambda *a, **k: [ds1, ds2, ds3])


def test_ecmwf_noktalar(monkeypatch):
    _ecmwf_sentetik(monkeypatch)
    out = acik_nwp.ecmwf_noktalar("sahte.grib2", [(LAT, LON)])
    df = out[(LAT, LON)]
    assert len(df) == 25 and df.index.tz is not None and df.index[0] == pd.Timestamp("2026-09-06", tz="UTC")
    assert abs(df["temp_air"].iloc[0] - 27.0) < 1e-6 and abs(df["wind_speed_10m"].iloc[0] - 5.0) < 1e-6 and df["cloud_cover"].iloc[0] == 25.0
    assert df["ghi"].min() >= 0 and df["ghi"].loc["2026-09-06 00:00"] == 0.0 and df["ghi"].loc["2026-09-06 09:00"] > 100
    assert abs(df["precipitation"].iloc[3] - 0.3) < 1e-6          # 0,9 mm / 3 saat


def test_harmanla_ortusme_ve_kuyruk():
    ix = pd.date_range("2026-09-06", periods=48, freq="h", tz="UTC")
    cs = pd.Series(np.clip(800 * np.sin(np.pi * (ix.hour - 3) / 12), 0, None), index=ix)
    e = pd.DataFrame({"ghi": cs * 0.6, "temp_air": 25.0, "wind_speed_10m": 3.0, "cloud_cover": 40.0, "precipitation": 0.0})
    i = pd.DataFrame({"ghi": cs.iloc[6:24] * 0.8, "dni": 0.0, "dhi": cs.iloc[6:24] * 0.8, "temp_air": 27.0, "wind_speed_10m": 5.0, "cloud_cover": 20.0})
    h = acik_nwp.harmanla(e, i, LAT, LON)                    # ICON 06z: baştaki 6 saat yalnız ECMWF
    assert len(h) == 48 and "precipitation" in h and "dni" in h and "dhi" in h
    assert abs(h["temp_air"].iloc[2] - 25.0) < 1e-6           # ICON öncesi: yalnız ECMWF
    assert abs(h["temp_air"].iloc[12] - 26.0) < 1e-6          # örtüşen saat: eşit ağırlık
    i2 = i.copy(); i2.loc[i2.index[3:6], ["temp_air", "cloud_cover"]] = np.nan; i2.loc[i2.index[8], "ghi"] = np.nan
    h2 = acik_nwp.harmanla(e, i2, LAT, LON)
    assert not h2[["ghi", "temp_air", "wind_speed_10m", "cloud_cover"]].isna().any().any()   # ICON boşluğu ECMWF'den dolar
    assert abs(h["temp_air"].iloc[30] - 25.0) < 1e-6          # ICON sonrası: yalnız ECMWF
    tek = acik_nwp.harmanla(e, None, LAT, LON)
    assert len(tek) == 48 and "dni" in tek                    # tek kaynak: ayrıştırma ile dni/dhi tamamlanır
    with pytest.raises(ValueError):
        acik_nwp.harmanla(None, None, LAT, LON)


def test_satirlar_ve_meteodata():
    ix = pd.date_range("2026-09-06", periods=3, freq="h", tz="UTC")
    df = pd.DataFrame({"ghi": [0.0, np.nan, 50.0], "dni": 0.0, "dhi": 0.0, "temp_air": 20.0, "wind_speed_10m": 1.0, "cloud_cover": 0.0, "precipitation": 0.0}, index=ix)
    s = acik_nwp.satirlar_uret(df, "acik-nwp", pd.Timestamp("2026-09-06", tz="UTC"), 37.8712, 32.4891)
    assert len(s) == 2 and s[0]["la"] == 37.871 and s[0]["lo"] == 32.489 and s[1]["ghi"] == 50.0   # NaN saat yazılmaz
    md = acik_nwp._cerceve_to_meteodata(df.dropna(), LAT, LON)
    assert isinstance(md, MeteoData) and md.kaynak == "acik-nwp" and md.nwp_model == "ECMWF IFS + ICON-EU" and md.snowfall is None


def test_eski_temizle(tmp_path):
    for k in ("2026090100", "2026090112", "2026090200"):
        (tmp_path / f"ecmwf_ifs_{k}.grib2").write_bytes(b"x"); (tmp_path / f"icon_eu_{k}").mkdir()
    (tmp_path / "a.part").write_bytes(b"x")
    sil = acik_nwp.eski_temizle(tmp_path, tut=2)
    assert set(sil) == {"ecmwf_ifs_2026090100.grib2", "icon_eu_2026090100"} and not (tmp_path / "a.part").exists()
    assert (tmp_path / "ecmwf_ifs_2026090200.grib2").exists() and (tmp_path / "icon_eu_2026090112").is_dir()


def test_fasad_acik_yolu(monkeypatch):
    from pvquant import config
    config.get_settings.cache_clear()
    monkeypatch.setenv("PVQUANT_METEO_KAYNAK", "acik")
    ix = pd.date_range("2026-09-06", periods=24, freq="h", tz="UTC")
    md = acik_nwp._cerceve_to_meteodata(pd.DataFrame({"ghi": 100.0, "temp_air": 20.0, "wind_speed_10m": 1.0, "cloud_cover": 0.0}, index=ix), LAT, LON)
    cagri = {"indir": 0}
    durum = {"var": False}
    monkeypatch.setattr(acik_nwp, "arsivden_tahmin", lambda la, lo, d, p=0, **k: md if durum["var"] else None)
    monkeypatch.setattr(acik_nwp, "kosu_cek_ve_arsivle", lambda n, **k: (cagri.__setitem__("indir", cagri["indir"] + 1), durum.__setitem__("var", True)))
    r = MeteoIstemcisi().get_forecast(LAT, LON, days=7)
    assert r.kaynak == "acik-nwp" and cagri["indir"] == 1                      # arşiv boş → bir kez indirdi
    assert OpenMeteoClient().get_forecast(LAT, LON, days=7).kaynak == "acik-nwp" and cagri["indir"] == 1   # taze → indirmedi
    monkeypatch.setattr(acik_nwp, "arsivden_gecmis", lambda *a, **k: md)
    assert OpenMeteoClient().get_historical(LAT, LON, "2026-09-06", "2026-09-06").kaynak == "acik-nwp"
    config.get_settings.cache_clear()
