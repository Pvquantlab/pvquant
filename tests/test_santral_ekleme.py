"""v2.302 — yeni santral bağlama: kapılar, doğrulama, yinelenen ad insan dilinde 422."""
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.services import plant_service


def _rol(r):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": r, "exp": 0}


GOVDE = {"name": "Karapınar GES", "lat": 37.7, "lon": 33.5, "capacity_kwp": 2500.0,
         "tilt": 25.0, "ac_limit_kw": 2200.0, "panel_tech": "bifacial"}


def test_kapilar_ve_dogrulama(monkeypatch):
    monkeypatch.setattr(plant_service, "olustur", lambda t, **k: "yeni-uuid")
    try:
        _rol("viewer")
        assert TestClient(api_main.app).post("/v1/plants", json=GOVDE).status_code == 403
        _rol("editor")
        c = TestClient(api_main.app)
        assert c.post("/v1/plants", json=GOVDE).json() == {"id": "yeni-uuid"}
        assert c.post("/v1/plants", json={**GOVDE, "lat": 123.0}).status_code == 422       # konum
        assert c.post("/v1/plants", json={**GOVDE, "capacity_kwp": 0}).status_code == 422  # güç
    finally:
        api_main.app.dependency_overrides.clear()


def test_yinelenen_ad_422(monkeypatch):
    monkeypatch.setattr(plant_service, "olustur",
                        lambda t, **k: (_ for _ in ()).throw(ValueError("'Karapınar GES' adinda bir santral zaten var. Farkli bir ad secin veya mevcut santrali kullanin.")))
    _rol("admin")
    try:
        y = TestClient(api_main.app).post("/v1/plants", json=GOVDE)
        assert y.status_code == 422 and "zaten var" in y.json()["detail"]
    finally:
        api_main.app.dependency_overrides.clear()
