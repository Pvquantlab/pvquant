"""v2.303 — santral arşivleme: kapılar, son-santral koruması, geri alma."""
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.services import plant_service


def _rol(r):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": r, "exp": 0}


def test_kapilar(monkeypatch):
    monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": p, "name": "X"})
    monkeypatch.setattr(plant_service, "arsivle", lambda t, p: {"arsivlendi": True})
    monkeypatch.setattr(plant_service, "geri_al", lambda t, p: {"geri_alindi": True})
    monkeypatch.setattr(plant_service, "arsivli_listele", lambda t: [{"id": "p9", "name": "Eski GES", "capacity_kwp": 900.0}])
    try:
        _rol("editor")
        c = TestClient(api_main.app)
        assert c.delete("/v1/plants/p1").status_code == 403          # arşivleme yalnız yönetici
        assert c.get("/v1/plants-arsiv").status_code == 403
        _rol("admin")
        c = TestClient(api_main.app)
        assert c.delete("/v1/plants/p1").json() == {"arsivlendi": True}
        assert c.get("/v1/plants-arsiv").json()["santraller"][0]["name"] == "Eski GES"
        assert c.post("/v1/plants/p9/geri-al").json() == {"geri_alindi": True}
    finally:
        api_main.app.dependency_overrides.clear()


def test_son_santral_korunur(monkeypatch):
    monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": p, "name": "X"})
    monkeypatch.setattr(plant_service, "arsivle",
                        lambda t, p: (_ for _ in ()).throw(ValueError("son etkin santral arşivlenemez — önce yeni bir santral bağlayın")))
    _rol("admin")
    try:
        y = TestClient(api_main.app).delete("/v1/plants/p1")
        assert y.status_code == 422 and "son etkin santral" in y.json()["detail"]
    finally:
        api_main.app.dependency_overrides.clear()
