"""v2.263 — portfoy_service toplam kuralları (SAF parçalar) + /portfoy kapısı."""
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.services.portfoy_service import _toplam


def test_toplam_eksikte_none():
    assert _toplam([1.0, 2.5]) == 3.5 and _toplam([1.0, None]) is None and _toplam([]) is None


@pytest.fixture()
def istemci(monkeypatch):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "viewer", "exp": 0}
    from pvquant.services import portfoy_service
    monkeypatch.setattr(portfoy_service, "ozet", lambda t: {"santraller": [{"id": "a", "ad": "A", "kapasite_kwp": 1000.0}], "toplam": {"santral": 1, "kapasite_kwp": 1000.0}, "gun": "2026-09-06"})
    yield TestClient(api_main.app)
    api_main.app.dependency_overrides.clear()


def test_portfoy_kapisi(istemci):
    j = istemci.get("/v1/portfoy").json(); assert j["toplam"]["santral"] == 1 and j["santraller"][0]["ad"] == "A"


def test_program_durumu_bildirildi(monkeypatch):
    """29.10 — müşterinin yarın için yüklediği KGÜP dosyası «bildirildi» rozeti olarak döner; yoksa False; TPYS kabulü doğrulanmaz."""
    from datetime import date, datetime, timezone
    from pvquant.services import kgup_service, portfoy_service
    monkeypatch.setattr(kgup_service, "kaynak_kosu_df", lambda t, p, g: (None, {"run_at": "2026-10-24T09:30:00+00:00"}))
    p = {"id": "a", "params_json": {"segment": "lisansli_serbest"}}
    z = datetime(2026, 10, 24, 13, 2, tzinfo=timezone.utc)
    r = portfoy_service._program_durumu("t", p, date(2026, 10, 25), z)
    assert r["yukumlu"] is True and r["hazir"] is True and r["bildirilen"] is True and r["bildirim_zamani"] == z.isoformat()
    r0 = portfoy_service._program_durumu("t", p, date(2026, 10, 25))
    assert r0["bildirilen"] is False and r0["bildirim_zamani"] is None
    s = portfoy_service._program_durumu("t", {"id": "a", "params_json": {}}, date(2026, 10, 25), z)
    assert s["yukumlu"] is None and s["bildirilen"] is True                            # segment seçilmemiş olsa da beyan görünür
