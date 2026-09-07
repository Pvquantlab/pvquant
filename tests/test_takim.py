"""v2.299 — ekip yönetimi: kapılar, son yönetici koruması, parola kuralları, geçici parola sözleşmesi."""
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.services import auth_service as au


def _rol(r):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u1", "tenant_id": "t1", "role": r, "exp": 0}


def test_kapilar_ve_akislar(monkeypatch):
    monkeypatch.setattr(au, "takim_listesi", lambda t: [{"id": "u1", "email": "a@b.c", "rol": "admin", "aktif": True, "son_giris": None, "olusturma": None}])
    monkeypatch.setattr(au, "kullanici_ekle", lambda t, e, r: {"id": "u2", "email": e, "rol": r, "gecici_parola": "Xy9-abc"})
    monkeypatch.setattr(au, "kullanici_guncelle", lambda t, u, rol=None, aktif=None: True)
    monkeypatch.setattr(au, "parola_degistir", lambda u, e, y: None)
    try:
        _rol("editor")
        c = TestClient(api_main.app)
        assert c.get("/v1/takim").status_code == 403                      # ekip yalnız yönetici
        assert c.post("/v1/parola", json={"eski": "a", "yeni": "b" * 12}).status_code == 200   # parola herkese
        _rol("admin")
        c = TestClient(api_main.app)
        assert c.get("/v1/takim").json()["roller"] == ["viewer", "editor", "admin"]
        j = c.post("/v1/takim", json={"email": "x@y.z", "rol": "editor"}).json()
        assert j["gecici_parola"] == "Xy9-abc"
        assert c.put("/v1/takim/u2", json={"aktif": False}).json() == {"tamam": True}
    finally:
        api_main.app.dependency_overrides.clear()


def test_dogrulamalar():
    with pytest.raises(ValueError, match="rol"):
        au.kullanici_ekle("t", "a@b.co", "patron")
    with pytest.raises(ValueError, match="e-posta"):
        au.kullanici_ekle("t", "bozuk", "viewer")
    with pytest.raises(ValueError, match="10 karakter"):
        au.parola_degistir("u", "eski", "kisa")


def test_son_yonetici_hatasi_422(monkeypatch):
    monkeypatch.setattr(au, "kullanici_guncelle",
                        lambda t, u, rol=None, aktif=None: (_ for _ in ()).throw(ValueError("son etkin yönetici düşürülemez — önce başka bir yönetici atayın")))
    _rol("admin")
    try:
        y = TestClient(api_main.app).put("/v1/takim/u1", json={"aktif": False})
        assert y.status_code == 422 and "son etkin yönetici" in y.json()["detail"]
    finally:
        api_main.app.dependency_overrides.clear()
