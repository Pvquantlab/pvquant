"""G4-P1 (26.11.2026) — retrospektif kalibrasyon: DB yok; sentetik 30 gün; kapı mantığı ve etiket."""
import numpy as np
import pandas as pd

from pvquant.services import retrospektif_kalibrasyon as rk

PLANT = {"id": None, "name": "Golden sentetik", "capacity_kwp": 2.4, "lat": 39.7404, "lon": -105.1772, "tz": "Etc/GMT+7", "tilt": 40.0,
         "azimuth": 180.0, "panel_tech": None, "ac_limit_kw": None, "params_json": {}}


def _veri(gun=30, eta=0.80, tohum=3):
    rng = np.random.default_rng(tohum)
    idx = pd.date_range("2018-06-01", periods=gun * 24, freq="h", tz="UTC")
    saat_yerel = (idx.hour - 7) % 24                                            # Etc/GMT+7
    ghi = np.clip(950 * np.sin(np.pi * (saat_yerel - 5.5) / 13), 0, None)
    ghi = ghi * rng.uniform(0.7, 1.0, len(idx))                                # bulut
    meteo = pd.DataFrame({"ghi": ghi, "temp_air": 18 + 8 * np.sin(np.pi * (saat_yerel - 8) / 12), "wind_speed_10m": 2.0}, index=idx)
    # basit PV: POA ≈ 1,15×GHI (40° eğim yaz), P = kWp × POA/1000 × eta × (1 − 0,004·(Tm−25))
    poa = 1.15 * ghi
    tm = meteo["temp_air"].to_numpy() + 0.03 * poa
    p = 2.4 * poa / 1000.0 * eta * (1 - 0.004 * (tm - 25)) + rng.normal(0, 0.02, len(idx))
    scada = pd.DataFrame({"power_kw": np.clip(p, 0, None), "poa_wm2": poa, "t_air": meteo["temp_air"].to_numpy(), "t_module": tm,
                          "kapsama_dk": 60}, index=idx)
    scada.index.name = "ts_utc"
    return scada, meteo


def test_cerceveler():
    scada, meteo = _veri(gun=3)
    s = rk.scada_cercevesi(scada, PLANT)
    assert len(s.power_kw) == 72 and s.poa_irradiance is not None and s.temp_module is not None and s.timestep_minutes == 60
    m = rk.meteo_cercevesi(meteo.drop(columns="wind_speed_10m"), PLANT["lat"], PLANT["lon"], kaynak="sentetik")
    assert (m.wind_speed_10m == 1.0).all() and m.kaynak == "sentetik" and str(m.ghi.index.tz) == "UTC"
    try:
        rk.scada_cercevesi(scada.drop(columns="power_kw"), PLANT)
        raise AssertionError("power_kw yokken hata bekleniyordu")
    except ValueError:
        pass


def test_retrospektif_kalibrasyon_kapisi_ve_etiket():
    scada, meteo = _veri(gun=30)
    r = rk.kalibre_et_retrospektif(scada, rk.meteo_cercevesi(meteo, PLANT["lat"], PLANT["lon"], "sentetik"), PLANT, meteo_kaynak="sentetik")
    assert r["etiket"] == "retrospektif_model_deneyi" and r["mode"] in ("B", "atlandi") and isinstance(r["kapi"], str)
    assert 0.3 < r["eta_bos"] < 1.2 and r["n_valid_hours"] >= 100 and r["pencere"]["saat"] == 720 and r["meteo_kaynak"] == "sentetik"
    assert r["santral"]["bifacial_factor"] == 0.0                                 # beyansız panel → bifacial kazancı yok (G4-P0)
    assert set(r["holdout"]) >= {"wmape_holdout_pct", "holdout_not"} or "wmape_holdout_pct" in r["holdout"]
    assert "YAZILMAZ" in r["not"] and "kalibrasyon_penceresi uygulanmadı" in r["not"]


def test_kapi_yetersiz_saat_atlanir():
    scada, meteo = _veri(gun=4)                                                  # ~50 gündüz saati < 100
    r = rk.kalibre_et_retrospektif(scada, rk.meteo_cercevesi(meteo, PLANT["lat"], PLANT["lon"], "sentetik"), PLANT)
    assert r["mode"] == "atlandi" and "100" in r["kapi"] and r["n_valid_hours"] == 0 and r["pencere"]["saat"] == 96


def test_hibrit_kapisi_retrospektif():
    scada, meteo = _veri(gun=30)
    m = rk.meteo_cercevesi(meteo, PLANT["lat"], PLANT["lon"], "sentetik")
    r = rk.kalibre_et_retrospektif(scada, m, PLANT, meteo_kaynak="sentetik", hibrit=True)
    h = r["hibrit"]
    assert h is not None and h["denendi"] is True and isinstance(h["gecti"], bool) and "kronolojik" in h["not"]
    assert r["mode"] in ("B", "C") and (r["mode"] == "C") == h["gecti"]
    assert set(h) >= {"holdout_wmape", "fizik_wmape", "wmape_iyilesme_pct", "esik"}
    assert rk.kalibre_et_retrospektif(scada, m, PLANT, hibrit=False)["hibrit"] is None


def test_sensorsuz_meteo_yolu():
    scada, meteo = _veri(gun=30)
    m = rk.meteo_cercevesi(meteo, PLANT["lat"], PLANT["lon"], "sentetik")
    s2 = rk.sensorsuz(scada)
    assert "poa_wm2" not in s2.columns and "t_module" not in s2.columns and "power_kw" in s2.columns and len(s2) == len(scada)
    r = rk.kalibre_et_retrospektif(s2, m, PLANT, meteo_kaynak="sentetik")
    assert r["poa_olcumu_kullanildi"] is False and r["sensorler"] == [] and r["mode"] in ("B", "atlandi")
    r2 = rk.kalibre_et_retrospektif(scada, m, PLANT, meteo_kaynak="sentetik")
    assert r2["poa_olcumu_kullanildi"] is True and "poa" in r2["sensorler"]
