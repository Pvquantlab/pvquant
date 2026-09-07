"""v2.300 — kayan oturum: tazeleme taze rol/durumla; pasif hesap tazeleyemez."""
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.services import auth_service as au


def test_yenile_taze_rolle(monkeypatch):
    monkeypatch.setattr(au, "oturum_yenile", lambda u: {"token": "yeni.jeton.x", "role": "editor"})
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u1", "tenant_id": "t", "role": "admin", "exp": 0}
    try:
        j = TestClient(api_main.app).post("/v1/oturum/yenile").json()
        assert j["token"] == "yeni.jeton.x" and j["role"] == "editor"   # rol DB'den taze — eski jetondaki değil
    finally:
        api_main.app.dependency_overrides.clear()


def test_pasif_hesap_401(monkeypatch):
    monkeypatch.setattr(au, "oturum_yenile", lambda u: None)
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u1", "tenant_id": "t", "role": "admin", "exp": 0}
    try:
        assert TestClient(api_main.app).post("/v1/oturum/yenile").status_code == 401
    finally:
        api_main.app.dependency_overrides.clear()
