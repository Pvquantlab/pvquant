"""v2.260 — /kgup (sahte servis) ve /segment (yetki + doğrulama)."""
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici, yazma_yetkisi

PLANT = "22222222-2222-2222-2222-222222222222"


@pytest.fixture()
def istemci(monkeypatch):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "editor", "exp": 0}
    from pvquant.services import plant_service, kgup_service
    monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": p, "capacity_kwp": 10000.0, "ac_limit_kw": 9000.0, "params_json": {"uevcb": "UEVCB-1"}})
    def _uret(t, pl, gun, kantil="p50", uevcb=None):
        if gun.isoformat() == "2030-01-01":
            return {"hata": "koşu yok"}
        return {"gun": gun.isoformat(), "kantil": kantil, "kosu": {"mode": "C"}, "uyarilar": [], "sicrama_saatleri": [], "toplam_mwh": 40.5,
                "satirlar": [{"saat": h, "kgup_mwh": 1.0, "eak_mwh": 9.0} for h in range(24)], "csv": "Tarih;Saat;UEVCB;KGUP_MWh;EAK_MWh\n01.07.2025;0;UEVCB-1;0,0;9,0\n",
                "dosya_adi": f"KGUP_UEVCB-1_{gun.isoformat()}_{kantil}.csv", "teslim": {"durum": "erken"}}
    monkeypatch.setattr(kgup_service, "uret", _uret)
    monkeypatch.setattr(plant_service, "params_birlestir", lambda t, p, **k: {"segment": k.get("segment"), "uevcb": k.get("uevcb"), "eski": 1})
    yield TestClient(api_main.app)
    api_main.app.dependency_overrides.clear()


def test_kgup_csv_ve_json(istemci):
    r = istemci.get(f"/v1/plants/{PLANT}/kgup?gun=2025-07-01&kantil=p50")
    assert r.status_code == 200 and r.headers["content-disposition"].endswith('KGUP_UEVCB-1_2025-07-01_p50.csv"') and r.text.startswith("\ufeffTarih;Saat")
    j = istemci.get(f"/v1/plants/{PLANT}/kgup?gun=2025-07-01&fmt=json").json()
    assert j["toplam_mwh"] == 40.5 and len(j["satirlar"]) == 24 and "csv" not in j
    assert istemci.get(f"/v1/plants/{PLANT}/kgup?gun=2030-01-01").status_code == 409
    assert istemci.get(f"/v1/plants/{PLANT}/kgup?kantil=p42").status_code == 422


def test_segment_ayarla(istemci):
    r = istemci.put(f"/v1/plants/{PLANT}/segment", json={"segment": "lisansli_yekdem", "uevcb": "UEVCB-9"})
    assert r.status_code == 200 and r.json()["params_json"] == {"segment": "lisansli_yekdem", "uevcb": "UEVCB-9"} and r.json()["kgup_yukumlu"] is True
    assert istemci.put(f"/v1/plants/{PLANT}/segment", json={"segment": "bilinmeyen"}).status_code == 422


def test_segment_viewer_yasak(monkeypatch):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "viewer", "exp": 0}
    try:
        c = TestClient(api_main.app)
        assert c.put(f"/v1/plants/{PLANT}/segment", json={"segment": "lisansli_serbest"}).status_code in (401, 403)
    finally:
        api_main.app.dependency_overrides.clear()
