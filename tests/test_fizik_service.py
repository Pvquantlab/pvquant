"""v2.274 — fizik terimleri: doğrulama (SAF), önizleme (monkeypatch), kapılar, nem formülü."""
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.io import acik_nwp
from pvquant.services import fizik_service as fz


def test_dogrula():
    assert fz.dogrula({"iam_model": "physical", "soiling_gunluk_kayip": "0.002"}) == {"iam_model": "physical", "soiling_gunluk_kayip": 0.002}
    for kotu in ({"iam_model": "erbs"}, {"bilinmeyen": 1}, {"soiling_temizleme_mm": 99}, {"soiling_baslangic": "x"}):
        with pytest.raises(ValueError):
            fz.dogrula(kotu)
    d = fz.durum({"params_json": '{"iam_model": "ashrae"}'})
    assert d["iam_model"] == "ashrae" and d["kar_model"] == "none" and "physical" in d["secenekler"]["iam_model"]


def test_bagil_nem():
    assert abs(float(acik_nwp.bagil_nem(20.0, 20.0)) - 100.0) < 1e-6
    assert 25 < float(acik_nwp.bagil_nem(30.0, 10.0)) < 32 and float(acik_nwp.bagil_nem(-5.0, -20.0)) > 0


def test_onizle(monkeypatch):
    from pvquant.io import meteo as mio
    from pvquant.io.meteo import MeteoData
    ix = pd.date_range("2026-09-07", periods=7 * 24, freq="h", tz="UTC")
    ghi = pd.Series(np.clip(900 * np.sin(np.pi * (ix.hour - 3) / 12), 0, None), index=ix)
    md = MeteoData(ghi=ghi, temp_air=pd.Series(25.0, index=ix), wind_speed_10m=pd.Series(2.0, index=ix), relative_humidity=None,
                   cloud_cover=None, latitude=37.87, longitude=32.49, timezone="UTC", kaynak="acik-nwp")
    monkeypatch.setattr(mio.OpenMeteoClient, "get_forecast", lambda self, **k: md)
    class FR:
        def __init__(self, spec):
            kat = 0.97 if spec.iam_model != "none" else 1.0
            self.hourly = pd.DataFrame({"p_ac_kw": ghi.values * 4.0 * kat}, index=ix)
    import pvquant.pipeline.forecast as pf
    monkeypatch.setattr(pf, "forecast_7day", lambda meteo, spec: FR(spec))
    plant = {"id": "p", "name": "K", "lat": 37.87, "lon": 32.49, "tz": "Europe/Istanbul", "capacity_kwp": 4000.0, "tilt": 20, "azimuth": 180,
             "panel_tech": "mono", "params_json": {}}
    r = fz.onizle("t", plant, {"iam_model": "physical"})
    assert r["toplam_fark_pct"] is not None and abs(r["toplam_fark_pct"] + 3.0) < 0.2 and r["nem_var"] is False and len(r["gun"]) >= 7


@pytest.fixture()
def istemci(monkeypatch):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "editor", "exp": 0}
    from pvquant.services import plant_service
    monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": p, "params_json": {"iam_model": "physical"}})
    monkeypatch.setattr(plant_service, "params_birlestir", lambda t, p, **k: {"iam_model": "physical", **k})
    yield TestClient(api_main.app)
    api_main.app.dependency_overrides.clear()


def test_kapilar(istemci):
    assert istemci.get("/v1/plants/p1/fizik-terimleri").json()["iam_model"] == "physical"
    j = istemci.put("/v1/plants/p1/fizik-terimleri", json={"ayar": {"soiling_model": "kimber"}}).json()
    assert j["soiling_model"] == "kimber" and j["iam_model"] == "physical"
    assert istemci.put("/v1/plants/p1/fizik-terimleri", json={"ayar": {"iam_model": "yok"}}).status_code == 422
