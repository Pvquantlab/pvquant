"""v2.263 — portfoy_service toplam kuralları (SAF parçalar) + /portfoy kapısı."""
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.services.portfoy_service import _toplam


def test_toplam_eksikte_none():
    assert _toplam([1.0, 2.5]) == 3.5 and _toplam([1.0, None]) is None and _toplam([]) is None


@pytest.fixture()
def istemci(monkeypatch):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "viewer", "exp": 0}
    from pvquant.services import portfoy_service
    monkeypatch.setattr(portfoy_service, "ozet", lambda t: {"santraller": [{"id": "a", "ad": "A", "kapasite_kwp": 1000.0}], "toplam": {"santral": 1, "kapasite_kwp": 1000.0}, "gun": "2026-09-06"})
    yield TestClient(api_main.app)
    api_main.app.dependency_overrides.clear()


def test_portfoy_kapisi(istemci):
    j = istemci.get("/v1/portfoy").json(); assert j["toplam"]["santral"] == 1 and j["santraller"][0]["ad"] == "A"
