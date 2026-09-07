"""v2.283 — güç matrisi (IEC 61853): sentetik matris/uydurma davranışı, tipik yıl hesabı, kapılar."""
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.ext.standart import iec61853 as gm
from pvquant.services import guc_matrisi_service as gs


class SahteSpec:
    effective_gamma = -0.004


def test_matris_ve_davranis(monkeypatch):
    from pvquant.services import calib_service
    monkeypatch.setattr(calib_service, "_plant_spec", lambda p: SahteSpec())
    M, adr, kaynak, gamma = gs.matris_getir({"params_json": {}})
    assert gamma == -0.004 and kaynak.startswith("sentetik")
    t = gs.davranis_tablosu(adr)
    assert len(t) == 6 and t[-1]["g_wm2"] == 1000
    v25 = {r["g_wm2"]: r["verim_25_pct"] for r in t}; v50 = {r["g_wm2"]: r["verim_50_pct"] for r in t}
    assert 97 <= v25[1000] <= 101 and v25[200] < v25[1000]                      # düşük ışınımda verim düşer
    assert v50[1000] < v25[1000] and abs((v25[1000] - v50[1000]) / v25[1000] - 0.004 * 25) < 0.03   # γ·ΔT ≈ %10
    # veri sayfası matrisi yolu: aynı sentetik matris dict olarak verilirse etiket değişir
    m = gm.matris_uret(1000.0, gamma_p=-0.004)
    pj = {"guc_matrisi": {"G": list(m.index), "T": list(m.columns), "P": m.values.tolist()}}
    _, _, kaynak2, _ = gs.matris_getir({"params_json": pj})
    assert kaynak2 == "veri sayfası matrisi"
    assert abs(gm.interpolasyon(m, 600, 25) - float(m.loc[600, 25])) < 1e-6


def test_hesapla(monkeypatch):
    from pvquant.services import calib_service, plant_service
    from pvquant.io import arsiv_isinim
    monkeypatch.setattr(calib_service, "_plant_spec", lambda p: SahteSpec())
    ix = pd.date_range("2023-06-01", periods=48, freq="h", tz="UTC")
    z = np.clip(np.sin(np.pi * (ix.hour - 3) / 12), 0, None)
    df = pd.DataFrame({"ghi": 900 * z, "dni": 700 * z, "dhi": 150 * z, "temp_air": 25.0, "wind_speed_10m": 2.0}, index=ix)
    monkeypatch.setattr(arsiv_isinim, "pvgis_df", lambda *a, **k: df)
    kayit = {}
    monkeypatch.setattr(plant_service, "params_birlestir", lambda t, p, **k: kayit.update(k) or k)
    r = gs.hesapla("t", {"id": "p", "lat": 37.87, "lon": 32.49, "tilt": 20, "azimuth": 180, "capacity_kwp": 4000.0, "params_json": {}})
    assert r["durum"] == "ok" and 0.8 < r["cser"] <= 1.0 and r["dusuk_isinim_kayip_pct"] > 0 and r["sicaklik_50_kayip_pct"] > 5
    assert r["e_dc_kwh_kwp"] < r["h_poa_kwh_m2"] and "guc_matrisi_sonuc" in kayit
    assert gs.getir({"params_json": kayit})["cser"] == r["cser"]


@pytest.fixture()
def istemci(monkeypatch):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "editor", "exp": 0}
    from pvquant.services import plant_service
    monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": p, "params_json": {}})
    monkeypatch.setattr(gs, "hesapla", lambda t, plant, kaydet=True: {"durum": "ok", "cser": 0.95})
    yield TestClient(api_main.app)
    api_main.app.dependency_overrides.clear()


def test_kapilar(istemci):
    assert istemci.get("/v1/plants/p1/guc-matrisi").status_code == 404
    assert istemci.post("/v1/plants/p1/guc-matrisi/hesapla").json()["cser"] == 0.95
