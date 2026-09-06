"""v2.278 — bankable bütçe (SAF), hesapla (monkeypatch), kapılar."""
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.services import bankable_service as bs


def test_butce_uygula():
    y = pd.Series([7000, 7200, 6800, 7100, 6900, 7300, 7000], index=range(2017, 2024), dtype=float)
    r = bs.butce_uygula(y, 4.0)
    assert r["p50_kwh"] == 7043 and r["ozgul_verim_kwh_kwp"] == 1760.7 and r["bir_yil"]["p90"] < r["p50_kwh"] < r["bir_yil"]["p50"] + 1
    assert r["n_yil"]["p90"] > r["bir_yil"]["p90"]                      # 10 yıl ortalamasında yıllar arası bileşen küçülür
    assert set(r["bilesenler"]) == {"yillar_arasi", "kaynak", "model", "olcum"}
    with pytest.raises(ValueError):
        bs.butce_uygula(y.iloc[:3], 4.0)


def test_hesapla(monkeypatch):
    ix = pd.date_range("2010-01-01", "2019-12-31 23:00", freq="h", tz="UTC")
    rng = np.random.default_rng(0)
    ghi = np.clip(700 * np.sin(np.pi * (ix.hour - 4) / 14), 0, None) * (1 + 0.05 * np.sin(2 * np.pi * (ix.dayofyear / 365)))
    df = pd.DataFrame({"ghi": ghi, "temp_air": 20.0, "wind_speed_10m": 2.0}, index=ix)
    from pvquant.io import arsiv_isinim
    monkeypatch.setattr(arsiv_isinim, "iklim_serisi", lambda lat, lon, n: (df, 2010, 2019))
    import pvquant.pipeline.forecast as pf
    class FR:
        def __init__(self, md): self.hourly = pd.DataFrame({"p_ac_kw": md.ghi.values * 3.0 * (1 + rng.normal(0, 0.02))}, index=md.ghi.index)
    monkeypatch.setattr(pf, "forecast_7day", lambda md, spec: FR(md))
    from pvquant.services import calib_service, plant_service
    monkeypatch.setattr(calib_service, "_plant_spec", lambda p: object())
    kayit = {}
    monkeypatch.setattr(plant_service, "params_birlestir", lambda t, p, **k: kayit.update(k) or k)
    plant = {"id": "p", "lat": 37.87, "lon": 32.49, "capacity_kwp": 4000.0, "params_json": {}}
    r = bs.hesapla("t", plant)
    assert r["durum"] == "ok" and r["yil_sayisi"] == 10 and r["donem"] == "2010–2019" and r["bir_yil"]["p90"] < r["p50_kwh"]
    assert "secilen_yillar" in r["tmy"] and len(r["tmy"]["secilen_yillar"]) == 12 and 2010 <= r["tmy"]["p90_yili"] <= 2019
    assert "bankable" in kayit and bs.getir({"params_json": kayit})["p50_kwh"] == r["p50_kwh"]


@pytest.fixture()
def istemci(monkeypatch):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "editor", "exp": 0}
    from pvquant.services import plant_service
    monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": p, "params_json": {}})
    monkeypatch.setattr(bs, "hesapla", lambda t, plant, kaydet=True: {"durum": "ok", "p50_kwh": 1.0})
    yield TestClient(api_main.app)
    api_main.app.dependency_overrides.clear()


def test_kapilar(istemci):
    assert istemci.get("/v1/plants/p1/bankable").status_code == 404
    assert istemci.post("/v1/plants/p1/bankable/hesapla").json()["p50_kwh"] == 1.0
