"""v2.258 — piyasa_service: senaryo fiyatı, EPİAŞ çekimi (sahte taşıyıcı), kapılar."""
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.ext.turkiye.epias import Istemci, sahte_tasiyici
from pvquant.services import piyasa_service as ps


def test_senaryo_ve_cekim():
    idx = pd.date_range("2025-07-01", periods=48, freq="h", tz="UTC")
    s = ps.senaryo_fiyat(idx); assert (s.kaynak == "senaryo").all() and s.ptf.iloc[0] == ps.SENARYO_PTF
    items = [{"date": "2025-07-01T00:00:00+03:00", "price": 2600.0}, {"date": "2025-07-01T01:00:00+03:00", "price": 2700.0}]
    smf = [{"date": "2025-07-01T00:00:00+03:00", "systemMarginalPrice": 2500.0}]
    yon = [{"date": "2025-07-01T00:00:00+03:00", "systemDirection": "Enerji Açığı"}]
    c = Istemci("u", "p", transport=sahte_tasiyici({"/v1/markets/dam/data/mcp": items, "/v1/markets/bpm/data/system-marginal-price": smf, "/v1/markets/bpm/data/system-direction": yon}))
    f = ps.fiyat_cek("2025-07-01", "2025-07-01", istemci=c)
    assert len(f) == 2 and (f.kaynak == "epias").all() and str(f.index.tz) == "UTC" and f.ptf.iloc[1] == 2700.0


@pytest.fixture()
def istemci(monkeypatch):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "viewer", "exp": 0}
    monkeypatch.setattr(ps, "durum", lambda: {"kimlik": False, "son_fiyat": None, "saat": 0, "senaryo": {"ptf": ps.SENARYO_PTF, "smf": ps.SENARYO_SMF, "ad": ps.SENARYO_AD}})
    monkeypatch.setattr(ps, "fiyatlar", lambda idx: ps.senaryo_fiyat(idx))
    yield TestClient(api_main.app)
    api_main.app.dependency_overrides.clear()


def test_kapilar(istemci):
    d = istemci.get("/v1/piyasa/durum").json(); assert d["kimlik"] is False and d["senaryo"]["ptf"] == ps.SENARYO_PTF
    f = istemci.get("/v1/piyasa/fiyat?bas=2025-07-01&bitis=2025-07-02").json()
    assert f["senaryo_saat"] == 48 and f["epias_saat"] == 0 and f["satirlar"][0]["ts"].endswith("21:00:00+00:00")
    assert istemci.get("/v1/piyasa/fiyat?bas=2020-01-01&bitis=2025-07-02").status_code == 422
