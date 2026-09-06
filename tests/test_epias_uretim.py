"""v2.278 — EPİAŞ gerçekleşen üretim: satır dönüşümü (SAF), sahte taşıyıcıyla çekim, uygunluk, kapı."""
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant import config
from pvquant.ext.turkiye.epias import Istemci, sahte_tasiyici
from pvquant.services import epias_uretim_service as eu


def test_satirlar_uret():
    ix = pd.date_range("2026-09-01", periods=4, freq="h", tz="UTC")
    s = pd.Series([0.0, 1.2, 5.0, -0.1], index=ix)                       # 5 MWh > 4,514 MW×1,05 → tavan aşımı; negatif
    r = eu.satirlar_uret(s, 4514.0)
    assert len(r) == 4 and r[1]["power_kw"] == 1200.0 and r[1]["flag"] == "valid" and r[2]["flag"] == "anomali" and r[3]["flag"] == "anomali"


def test_uygunluk(monkeypatch):
    config.get_settings.cache_clear(); monkeypatch.delenv("PVQUANT_EPIAS_KULLANICI", raising=False)
    ok, neden = eu.uygun_mu({"params_json": {"epias_santral_id": 123}})
    assert not ok and "kimliği yok" in neden
    monkeypatch.setenv("PVQUANT_EPIAS_KULLANICI", "u"); monkeypatch.setenv("PVQUANT_EPIAS_SIFRE", "p"); config.get_settings.cache_clear()
    assert eu.uygun_mu({"params_json": {}})[0] is False and eu.uygun_mu({"params_json": {"epias_santral_id": 123}})[0] is True
    config.get_settings.cache_clear()


def test_cek_sahte():
    items = [{"date": "2026-09-01T10:00:00+03:00", "total": 2.5}, {"date": "2026-09-01T11:00:00+03:00", "total": 3.0}]
    c = Istemci("u", "p", transport=sahte_tasiyici({"/realtime-generation": items}))
    from datetime import date
    s = eu.cek({"params_json": {"epias_santral_id": 42}}, date(2026, 9, 1), date(2026, 9, 1), istemci=c)
    assert len(s) == 2 and s.index[0] == pd.Timestamp("2026-09-01 07:00", tz="UTC") and float(s.iloc[1]) == 3.0


@pytest.fixture()
def istemci(monkeypatch):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "editor", "exp": 0}
    from pvquant.services import plant_service
    depo = {"params_json": {}}
    monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": p, "capacity_kwp": 4514.0, **depo})
    def birlestir(t, p, **k):
        depo["params_json"] = {**depo["params_json"], **k}; return depo["params_json"]
    monkeypatch.setattr(plant_service, "params_birlestir", birlestir)
    monkeypatch.setattr(eu, "durum", lambda t, plant: {"uygun": bool(eu._pj(plant).get("epias_santral_id")), "epias_santral_id": eu._pj(plant).get("epias_santral_id"), "n_saat": 0, "son": None, "neden": "test"})
    yield TestClient(api_main.app)
    api_main.app.dependency_overrides.clear()


def test_kapilar(istemci):
    assert istemci.get("/v1/plants/p1/epias-uretim").json()["epias_santral_id"] is None
    assert istemci.put("/v1/plants/p1/epias-uretim", json={"epias_santral_id": 777}).json()["epias_santral_id"] == 777
    assert istemci.put("/v1/plants/p1/epias-uretim", json={"epias_santral_id": None}).json()["epias_santral_id"] is None
