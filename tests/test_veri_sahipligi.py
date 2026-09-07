"""v2.298 — "veriniz sizindir": dışa aktarma her role, silme yalnız yönetici; kapılar ve biçim."""
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.services import ingest_service as ing


def _rol(r):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": r, "exp": 0}


def test_disa_aktarma_ve_silme_kapilari(monkeypatch):
    from pvquant.services import plant_service
    monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": p, "name": "Konya GES"})
    monkeypatch.setattr(ing, "scada_disa_csv", lambda t, p, b=None, e=None: "ts_utc,power_kw\n2026-08-01T05:00:00Z,120.0\n")
    monkeypatch.setattr(ing, "scada_sil", lambda t, p, b, e: 48)
    try:
        _rol("viewer")
        c = TestClient(api_main.app)
        y = c.get("/v1/plants/p1/scada/disa")
        assert y.status_code == 200 and y.text.startswith("ts_utc,power_kw")
        assert 'filename="pvquant_scada_Konya_GES.csv"' in y.headers["Content-Disposition"]
        assert c.delete("/v1/plants/p1/scada?baslangic=2026-08-01&bitis=2026-08-02").status_code == 403  # viewer silemez
        _rol("editor")
        assert TestClient(api_main.app).delete("/v1/plants/p1/scada?baslangic=2026-08-01&bitis=2026-08-02").status_code == 403
        _rol("admin")
        j = TestClient(api_main.app).delete("/v1/plants/p1/scada?baslangic=2026-08-01&bitis=2026-08-02")
        assert j.status_code == 200 and j.json() == {"silinen_satir": 48}
    finally:
        api_main.app.dependency_overrides.clear()


def test_silme_tarihsiz_reddedilir():
    with pytest.raises(ValueError, match="zorunlu"):
        ing.scada_sil("t", "p", "", "2026-08-02")
