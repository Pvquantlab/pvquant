"""v2.294 — kamuya açık doğrulama: kimliksiz uç, kapalı yol, kimlik sızmazlığı."""
from fastapi.testclient import TestClient

import apps.api.main as api_main
from pvquant.services import dogrulama_service as ds

ACIK_ORNEK = {
    "durum": "acik", "santral_etiketi": "Referans santral · 1–10 MW · İç Anadolu",
    "pencere_gun": 60, "son_gun": "2026-09-06", "wmape_pct": 5.6, "naif_wmape_pct": 28.0,
    "siki_referans_wmape_pct": 20.1, "nmae_pct": 2.1, "beceri_naif_pct": 80.0,
    "beceri_siki_pct": 72.0, "bant_kapsama_pct": 90.7, "bant_hedef_pct": 80.0,
    "aylar": [{"ay": "2026-09", "gun": 6, "wmape_pct": 5.2, "naif_wmape_pct": 27.0, "bant_kapsama_pct": 91.0}],
    "not": "0–24 saat ufku.",
}


def test_uc_kimliksiz_ve_onbellekli(monkeypatch):
    monkeypatch.setattr(ds, "ozet", lambda: dict(ACIK_ORNEK))
    y = TestClient(api_main.app).get("/v1/dogrulama")          # Authorization YOK
    assert y.status_code == 200 and y.json()["durum"] == "acik"
    assert "max-age=60" in y.headers.get("Cache-Control", "")


def test_kapali_yol(monkeypatch):
    monkeypatch.setattr(ds, "ozet", lambda: {"durum": "kapali"})
    assert TestClient(api_main.app).get("/v1/dogrulama").json() == {"durum": "kapali"}


def test_kimlik_sizmaz(monkeypatch):
    """Yayında santral kimliği geçemez: ad/koordinat/uuid alanları sözleşmede yok."""
    monkeypatch.setattr(ds, "ozet", lambda: dict(ACIK_ORNEK))
    j = TestClient(api_main.app).get("/v1/dogrulama").json()
    yasak = {"id", "plant_id", "name", "ad", "lat", "lon", "tenant_id", "capacity_kwp"}
    assert not (set(j) & yasak)
    assert "Konya" not in str(j)


def test_cilz_orneklem_kapali():
    """EN_AZ_GUN altında örneklem yayınlanmaz (sözleşme sabiti — cılız karne güven satamaz)."""
    assert ds.EN_AZ_GUN >= 30
