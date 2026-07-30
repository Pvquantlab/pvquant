"""v2.73-B — CORS: dev SPA kokeni izinli, yabanci koken degil."""
from fastapi.testclient import TestClient
import apps.api.main as api_main


def test_dev_kokeni_izinli():
    c = TestClient(api_main.app)
    r = c.get("/v1/healthz", headers={"Origin": "http://localhost:5173"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_yabanci_koken_izinsiz():
    c = TestClient(api_main.app)
    r = c.get("/v1/healthz", headers={"Origin": "https://kotu.example"})
    assert "access-control-allow-origin" not in r.headers
