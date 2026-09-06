"""v2.264 — dış API anahtarı: ayrıştırma/doğrulama (DB'siz `bul`), kapı kodları, ETag/304, yönetici kapısı, webhook imzası."""
import hashlib
import json
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.ext.platform.api_anahtar import webhook_dogrula
from pvquant.services import api_anahtar_service as ak
from pvquant.services import webhook_service as wh
from pvquant.services.portfoy_service import gunluk_toplamlar


def _kayit(secret, **k):
    r = {"id": "k1", "tenant_id": "t1", "key_hash": hashlib.sha256(secret.encode()).hexdigest(),
         "scopes": ["tahmin:oku"], "revoked": False, "expires_at": None, "rpm": 120}
    r.update(k); return r


def test_ayristir():
    assert ak.ayristir("pvq_abcd1234_s3cr_et") == ("abcd1234", "s3cr_et")
    assert ak.ayristir("Bearer x") is None and ak.ayristir("pvq__x") is None and ak.ayristir("") is None


def test_dogrula_yollari():
    ak._kovalar.clear()
    bul = lambda p: _kayit("gizli") if p == "abcd1234" else None
    r = ak.dogrula("pvq_abcd1234_gizli", "tahmin:oku", bul=bul)
    assert r["tenant_id"] == "t1" and r["kapsamlar"] == ["tahmin:oku"]
    with pytest.raises(PermissionError, match="gecersiz"):
        ak.dogrula("pvq_abcd1234_yanlis", "tahmin:oku", bul=bul)
    with pytest.raises(PermissionError, match="gecersiz"):
        ak.dogrula("pvq_zzzz_gizli", "tahmin:oku", bul=bul)
    with pytest.raises(PermissionError, match="kapsam"):
        ak.dogrula("pvq_abcd1234_gizli", "kgup:oku", bul=bul)
    with pytest.raises(PermissionError):
        ak.dogrula("pvq_abcd1234_gizli", "tahmin:oku", bul=lambda p: _kayit("gizli", revoked=True))
    with pytest.raises(PermissionError):
        ak.dogrula("pvq_abcd1234_gizli", "tahmin:oku",
                   bul=lambda p: _kayit("gizli", expires_at=datetime.now(timezone.utc) - timedelta(days=1)))


def test_oran_siniri():
    ak._kovalar.clear()
    bul = lambda p: _kayit("g", rpm=2)
    ak.dogrula("pvq_ab_g", "tahmin:oku", bul=bul); ak.dogrula("pvq_ab_g", "tahmin:oku", bul=bul)
    with pytest.raises(RuntimeError, match="oran"):
        ak.dogrula("pvq_ab_g", "tahmin:oku", bul=bul)


@pytest.fixture()
def istemci(monkeypatch):
    ak._kovalar.clear()
    monkeypatch.setattr(ak, "_kayit_bul", lambda p: _kayit("gizli", scopes=["tahmin:oku"]) if p == "abcd1234" else None)
    monkeypatch.setattr(ak, "_kullanim_isle", lambda i: None)
    from pvquant.services import plant_service, forecast_service
    monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": p, "name": "Konya GES", "capacity_kwp": 4514.0, "tz": "Europe/Istanbul"})
    monkeypatch.setattr(plant_service, "listele", lambda t: [{"id": "p1", "name": "Konya GES", "capacity_kwp": 4514.0, "tz": "Europe/Istanbul"}])

    class K:  # forecast_runs satırı
        id = "run-1"; run_at = datetime(2026, 9, 6, 1, 53, tzinfo=timezone.utc); mode = "C"
    monkeypatch.setattr(api_main, "_son_kosu_kimligi", lambda t, p: K())
    ix = pd.date_range("2026-09-06", periods=3, freq="h", tz="UTC")
    monkeypatch.setattr(forecast_service, "son_kosu", lambda t, p: pd.DataFrame({"p50_kw": [0.0, 100.5, 200.0], "p10_kw": [0.0, 80.0, float("nan")], "p90_kw": [0.0, 120.0, 250.0]}, index=ix))
    yield TestClient(api_main.app)
    api_main.app.dependency_overrides.clear()


def test_dis_tahmin_kapisi(istemci):
    assert istemci.get("/v1/dis/santral/p1/tahmin").status_code == 422           # başlık yok
    assert istemci.get("/v1/dis/santral/p1/tahmin", headers={"X-API-Key": "pvq_abcd1234_yanlis"}).status_code == 401
    assert istemci.get("/v1/dis/santral/p1/kgup", headers={"X-API-Key": "pvq_abcd1234_gizli"}).status_code == 403   # kapsam yok
    y = istemci.get("/v1/dis/santral/p1/tahmin", headers={"X-API-Key": "pvq_abcd1234_gizli"})
    assert y.status_code == 200 and y.headers["ETag"] == 'W/"run-1"'
    j = y.json(); assert j["kosu"]["id"] == "run-1" and j["saatlik"][1]["p50_kw"] == 100.5 and j["saatlik"][2]["p10_kw"] is None
    y2 = istemci.get("/v1/dis/santral/p1/tahmin", headers={"X-API-Key": "pvq_abcd1234_gizli", "If-None-Match": 'W/"run-1"'})
    assert y2.status_code == 304 and y2.content == b""
    assert istemci.get("/v1/dis/santraller", headers={"X-API-Key": "pvq_abcd1234_gizli"}).json()[0]["ad"] == "Konya GES"


def test_yonetici_kapisi(monkeypatch):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "editor", "exp": 0}
    try:
        assert TestClient(api_main.app).get("/v1/api-anahtarlari").status_code == 403
        api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "admin", "exp": 0}
        monkeypatch.setattr(ak, "listele", lambda t: [])
        j = TestClient(api_main.app).get("/v1/api-anahtarlari").json()
        assert j["anahtarlar"] == [] and "tahmin:oku" in j["kapsamlar"]
        monkeypatch.setattr(ak, "uret", lambda t, ad, k, g, r: (_ for _ in ()).throw(ValueError("bilinmeyen kapsam")))
        assert TestClient(api_main.app).post("/v1/api-anahtarlari", json={"ad": "x", "kapsamlar": ["yok:oku"]}).status_code == 422
    finally:
        api_main.app.dependency_overrides.clear()


def test_webhook_imza_ve_url():
    b, h = wh.istek_hazirla("whsec_abc", "tahmin.yeni", {"a": 1, "b": "ç"})
    assert json.loads(b) == {"a": 1, "b": "ç"} and h["X-PVQ-Event"] == "tahmin.yeni"
    assert webhook_dogrula("whsec_abc", b, h) and not webhook_dogrula("whsec_baska", b, h)
    assert wh.url_gecerli("https://ornek.com/hook") and wh.url_gecerli("http://localhost:9000/x") and not wh.url_gecerli("http://ornek.com/x")


def test_gunluk_toplamlar_kurallari():
    ix = pd.date_range("2026-09-05 21:00", periods=48, freq="h", tz="UTC")   # İstanbul 06 Eyl 00:00'dan 2 tam gün
    df = pd.DataFrame({"p50_kw": 100.0, "p10_kw": 80.0, "p90_kw": 120.0}, index=ix)
    df.loc[df.index[30], "p10_kw"] = float("nan")
    g = gunluk_toplamlar(df, "Europe/Istanbul")
    assert set(g) == {"2026-09-06", "2026-09-07"} and g["2026-09-06"]["p50_kwh"] == 2400.0 and g["2026-09-06"]["p10_kwh"] == 1920.0
    assert g["2026-09-07"]["p10_kwh"] is None and g["2026-09-07"]["p90_kwh"] == 2880.0      # eksik saat → bant toplamı yok
    assert gunluk_toplamlar(df.iloc[:10], "Europe/Istanbul") == {}                            # <20 saat → gün yazılmaz
    assert gunluk_toplamlar(df.tz_localize(None), "Europe/Istanbul") == g                      # naive → UTC varsayımı
