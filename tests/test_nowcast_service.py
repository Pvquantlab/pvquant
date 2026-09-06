"""v2.266 — kısa ufuk persistansı (SAF) + /nowcast kapısı."""
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.services import nowcast_service as ns


def _seri():
    ix = pd.date_range("2026-09-06 06:00", periods=12, freq="h", tz="UTC")
    p50 = pd.Series([0, 300, 900, 1500, 2000, 2300, 2400, 2300, 2000, 1500, 900, 300], index=ix, dtype=float)
    return ix, p50


def test_oran_ve_rampa():
    ix, p50 = _seri()
    gercek = (p50 * 0.8).iloc[:5]                     # 06–10 arası ölçüm, tahminin %80'i
    r = ns.rampali_persistans_guc(gercek, p50, simdi=ix[4])
    assert r["durum"] == "ok" and abs(r["oran"] - 0.8) < 1e-9 and r["n_saat"] == 3   # pencere 3 s, p50>0 olanlar
    u = r["ufuk"]; assert len(u) == 6 and u[0]["ts"] == ix[5].isoformat()
    w1 = np.exp(-1 / 2.0)
    assert abs(u[0]["nowcast_kw"] - (w1 * 0.8 * 2300 + (1 - w1) * 2300)) < 0.2 and u[0]["agirlik"] > u[5]["agirlik"]
    assert u[5]["nowcast_kw"] > 0.8 * u[5]["p50_kw"]  # ufuk sonunda P50'ye yaklaşır


def test_gece_ve_bos():
    ix, p50 = _seri()
    gece = pd.Series([0.0, 0.0, 0.0], index=ix[:3] - pd.Timedelta(hours=6))
    p = p50.copy(); p.iloc[:] = 0.0
    r = ns.rampali_persistans_guc(gece, pd.concat([pd.Series([0.0] * 3, index=gece.index), p]), simdi=gece.index[-1])
    assert r["durum"] == "gece" and all(x["agirlik"] == 0.0 for x in r["ufuk"])
    assert ns.rampali_persistans_guc(pd.Series(dtype=float), p50)["durum"] == "olcum_yok"
    assert ns.rampali_persistans_guc(p50.iloc[-2:], p50, simdi=ix[-1])["durum"] == "tahmin_yok"


def test_oran_siniri():
    ix, p50 = _seri()
    gercek = (p50 * 5.0).iloc[:5]                     # sensör hatası gibi aşırı oran
    assert ns.rampali_persistans_guc(gercek, p50, simdi=ix[4])["oran"] == 1.8


@pytest.fixture()
def istemci(monkeypatch):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "viewer", "exp": 0}
    from pvquant.services import plant_service
    monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": p, "name": "K"})
    monkeypatch.setattr(ns, "hesapla", lambda t, p: {"durum": "scada_bayat", "uydu": False, "tazelik_saat": 649.0, "ufuk": [], "not": "canlı SCADA gerektirir"})
    yield TestClient(api_main.app)
    api_main.app.dependency_overrides.clear()


def test_nowcast_kapisi(istemci):
    j = istemci.get("/v1/plants/p1/nowcast").json()
    assert j["durum"] == "scada_bayat" and j["uydu"] is False and j["ufuk"] == []
