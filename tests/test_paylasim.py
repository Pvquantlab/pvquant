"""v2.289 — kuruluşlar arası veri paylaşımı: doğrulama kapıları, süre/izin denetimi, uç kapıları."""
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.services import paylasim_service as ps


def test_paylas_dogrulama(monkeypatch):
    with pytest.raises(ValueError, match="izinler"):
        ps.paylas("t1", "u1", {"id": "p"}, "a@b.c", ["scada:yaz"], None, None)   # kapsam dışı izin
    with pytest.raises(ValueError, match="izinler"):
        ps.paylas("t1", "u1", {"id": "p"}, "a@b.c", [], None, None)              # boş izin
    monkeypatch.setattr(ps, "hedef_bul", lambda e: None)
    with pytest.raises(ValueError, match="bulunamadı"):
        ps.paylas("t1", "u1", {"id": "p"}, "yok@b.c", ["tahmin:oku"], None, None)
    monkeypatch.setattr(ps, "hedef_bul", lambda e: {"tenant_id": "t1", "kurulus": "Kendi"})
    with pytest.raises(ValueError, match="kendi"):
        ps.paylas("t1", "u1", {"id": "p"}, "ben@b.c", ["tahmin:oku"], None, None)


def test_gecersiz_paylasim_403(monkeypatch):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t2", "role": "viewer", "exp": 0}
    try:
        monkeypatch.setattr(ps, "_gecerli_paylasim", lambda h, i, izin: (_ for _ in ()).throw(PermissionError("paylaşım geçersiz, süresi dolmuş ya da izin kapsam dışı")))
        c = TestClient(api_main.app)
        assert c.get("/v1/paylasimlar/x/veri", params={"tur": "saçma"}).status_code == 422      # tur kapısı
        assert c.get("/v1/paylasimlar/x/veri", params={"tur": "karne"}).status_code == 403      # izin kapısı
    finally:
        api_main.app.dependency_overrides.clear()


def test_paylasilan_tahmin_takma_ad(monkeypatch):
    """Takma ad varsa gerçek ad ve kapasite sızmaz; günlük toplamlar döner."""
    r = {"kaynak_tenant": "t1", "plant_id": "p", "takma_ad": "GES-A", "santral": "Konya GES",
         "tz": "Europe/Istanbul", "capacity_kwp": 4514.0}
    monkeypatch.setattr(ps, "_gecerli_paylasim", lambda h, i, izin: r)
    ix = pd.date_range("2026-09-05 21:00", periods=48, freq="h", tz="UTC")
    from pvquant.services import forecast_service
    monkeypatch.setattr(forecast_service, "son_kosu",
                        lambda t, p: pd.DataFrame({"p50_kw": 100.0, "p10_kw": 80.0, "p90_kw": 120.0}, index=ix))
    j = ps.paylasilan_tahmin("t2", "x")
    assert j["santral"] == "GES-A" and j["kapasite_kwp"] is None and "Konya" not in str(j)
    assert j["gunler"] and j["gunler"][0]["p50_kwh"] == pytest.approx(2400.0)
    monkeypatch.setattr(forecast_service, "son_kosu", lambda t, p: None)
    assert ps.paylasilan_tahmin("t2", "x")["gunler"] == [] and "koşu yok" in ps.paylasilan_tahmin("t2", "x")["not"]


def test_yonetici_kapisi():
    """Paylaşım kurmak/iptal etmek yalnız admin; listeleme her doğrulanmış kullanıcıya açık."""
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "editor", "exp": 0}
    try:
        c = TestClient(api_main.app)
        assert c.post("/v1/paylasimlar", json={"plant_id": "p", "hedef_eposta": "a@b.c", "izinler": ["tahmin:oku"]}).status_code == 403
        assert c.delete("/v1/paylasimlar/x").status_code == 403
    finally:
        api_main.app.dependency_overrides.clear()
