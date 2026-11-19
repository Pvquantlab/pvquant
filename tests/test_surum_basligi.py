"""19.11 canli ozellik testi (Bulgu 7, surum kaymasi): her yanitta X-PVQ-Yazilim (PVQ_SURUM tanimliysa; X-PVQ-Surum KGUP arsiv surumudur, ezilmez); CORS expose."""
import inspect
import re

from fastapi.testclient import TestClient

import apps.api.main as api_main


def test_her_yanitta_surum_basligi(monkeypatch):
    monkeypatch.setenv("PVQ_SURUM", "v2.638-test-abc123")
    c = TestClient(api_main.app)
    r = c.get("/v1/healthz")
    assert r.status_code == 200 and r.headers["x-pvq-yazilim"] == "v2.638-test-abc123"
    assert re.fullmatch(r"\d+", r.headers["x-sure-ms"])   # mevcut baslik korunur
    r2 = c.get("/v1/plants/00000000-0000-0000-0000-000000000000/summary")   # yetkisiz de olsa baslik tasir (middleware her yanitta)
    assert "x-pvq-yazilim" in r2.headers


def test_surum_tanimsizsa_baslik_yok(monkeypatch):
    monkeypatch.delenv("PVQ_SURUM", raising=False)
    r = TestClient(api_main.app).get("/v1/healthz")
    assert r.status_code == 200 and "x-pvq-yazilim" not in r.headers   # sayi/surum uydurulmaz (surum.py ilkesi)


def test_cors_expose_ve_kaynak_pini():
    k = inspect.getsource(api_main)
    assert '"X-PVQ-Yazilim"])' in k.split("expose_headers=")[1][:160]
    assert 'yanit.headers["X-PVQ-Yazilim"] = surum' in inspect.getsource(api_main._sure_basligi)
    assert 'yanit.headers["X-PVQ-Surum"]' not in inspect.getsource(api_main._sure_basligi)   # KGUP arsiv surumu basligi middleware'de ezilmez
