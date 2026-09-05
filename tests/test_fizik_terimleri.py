"""v2.255 — IAM/spektral çarpanları (varsayılan kapalı → zincir birebir), kt referansı (toa/ineichen), spec eşlemesi."""
import numpy as np
import pandas as pd
import pytest

from pvquant.io.meteo import MeteoData
from pvquant.pipeline.forecast import PlantSpec, forecast_7day
from pvquant.services.calib_service import _plant_spec


def _meteo(n_gun=2, rh=True):
    idx = pd.date_range("2026-06-10", periods=24 * n_gun, freq="h", tz="UTC")
    g = np.clip(np.sin((np.asarray(idx.hour) - 4) / 14 * np.pi), 0, None)      # Konya UTC'de ~04–18 gündüz
    return MeteoData(ghi=pd.Series(900 * g, index=idx), temp_air=pd.Series(25.0 + 8 * g, index=idx),
                     wind_speed_10m=pd.Series(2.0, index=idx),
                     relative_humidity=pd.Series(45.0, index=idx) if rh else None, cloud_cover=None,
                     latitude=37.87, longitude=32.49, timezone="UTC")


def _spec(**k):
    return PlantSpec(p_nom_kwp=1000.0, latitude=37.87, longitude=32.49, tilt=25.0, azimuth=180.0, **k)


def test_varsayilan_kapali_zincir_birebir():
    m = _meteo(); a = forecast_7day(m, _spec()).hourly; b = forecast_7day(m, PlantSpec(p_nom_kwp=1000.0, latitude=37.87, longitude=32.49, tilt=25.0, azimuth=180.0, iam_model="none", spectral_model="none")).hourly
    assert np.allclose(a["p_ac_kw"].fillna(0), b["p_ac_kw"].fillna(0))


def test_iam_acik_ureti_dusurur_ve_sabah_aksam_daha_cok():
    m = _meteo(); kapali = forecast_7day(m, _spec()).hourly; acik = forecast_7day(m, _spec(iam_model="physical")).hourly
    oran = (acik["p_ac_kw"] / kapali["p_ac_kw"].replace(0, np.nan)).dropna()
    assert (oran <= 1.0 + 1e-9).all() and 0.90 < oran.mean() < 1.0
    # öğle (küçük AOI) kaybı, sabah/akşam (büyük AOI) kaybından küçük
    saat = oran.index.hour
    assert oran[(saat >= 10) & (saat <= 12)].mean() > oran[(saat <= 6) | (saat >= 16)].mean()


def test_spektral_nem_varsa_uygulanir_yoksa_atlanir():
    kapali = forecast_7day(_meteo(), _spec()).hourly["p_ac_kw"]
    acik = forecast_7day(_meteo(), _spec(spectral_model="first_solar")).hourly["p_ac_kw"]
    oran = (acik / kapali.replace(0, np.nan)).dropna()
    assert (oran.between(0.8, 1.2)).all() and not np.allclose(acik.fillna(0), kapali.fillna(0))
    nemsiz = forecast_7day(_meteo(rh=False), _spec(spectral_model="first_solar")).hourly["p_ac_kw"]
    assert np.allclose(nemsiz.fillna(0), kapali.fillna(0))                        # nem yok → spektral atlanır


def test_kt_referansi_ineichen(monkeypatch):
    from pvquant.models_v2 import hybrid_residual as hr
    from pvquant import config
    m = _meteo(); h = forecast_7day(m, _spec()).hourly
    f_toa = hr.build_features(h, 37.87, 32.49, 0.0, "Europe/Istanbul")
    monkeypatch.setattr(config, "get_settings", lambda: type("S", (), {"kt_referans": "ineichen"})())
    f_ine = hr.build_features(h, 37.87, 32.49, 0.0, "Europe/Istanbul")
    g = h["ghi"] > 50
    # açık gök paydası atmosfer üstünden küçük → kt hiçbir gündüz saatinde düşmez, çoğunda büyür (1,2 kelepçesinde eşit kalabilir)
    assert (f_ine.loc[g, "kt"] >= f_toa.loc[g, "kt"] - 1e-9).all() and (f_ine.loc[g, "kt"] > f_toa.loc[g, "kt"]).mean() > 0.7
    assert f_ine["kt"].between(0, 1.2).all()


def test_plant_spec_params_json_eslemesi():
    p = {"capacity_kwp": 1000.0, "lat": 37.9, "lon": 32.5, "params_json": {"iam_model": "ashrae", "spectral_model": "first_solar"}}
    s = _plant_spec(p); assert s.iam_model == "ashrae" and s.spectral_model == "first_solar"
    s2 = _plant_spec({"capacity_kwp": 1000.0, "lat": 37.9, "lon": 32.5, "params_json": '{"iam_model": "physical"}'})
    assert s2.iam_model == "physical" and s2.spectral_model == "none"
    assert _plant_spec({"capacity_kwp": 1000.0, "lat": 37.9, "lon": 32.5}).iam_model == "none"
