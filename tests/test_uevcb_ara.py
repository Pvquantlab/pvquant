"""v2.513 (04 #14 kalan) — UEVÇB adayları: kuruluş adı araması (organization-list önbellekli) + uevcb-list; API kapıları (422/503/200)."""
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.services import piyasa_service as ps


class _Istemci:
    def __init__(self):
        self.org_cagri = 0
    def organizasyon_listesi(self, b, e):
        self.org_cagri += 1
        return [{"organizationId": 1, "organizationName": "Format Lab Enerji Üretim A.Ş."}, {"organizationId": 2, "organizationName": "Başka Enerji"},
                {"organizationId": 3, "organizationName": "FORMAT GÜNEŞ"}]
    def uevcb_listesi(self, oid, b):
        if oid == 3:
            raise RuntimeError("400 SEF1181")
        return [{"id": 10 * oid, "eic": f"40X{oid:013d}A", "name": f"UEVÇB {oid}"}]


@pytest.fixture()
def istemci(monkeypatch):
    ist = _Istemci()
    monkeypatch.setattr(ps, "_istemci", lambda: ist)
    monkeypatch.setattr(ps, "kimlik_var", lambda: True)
    ps._ORG_ONBELLEK.update({"zaman": None, "liste": []})
    return ist


def test_uevcb_ara_ad_eslesmesi_ve_onbellek(istemci):
    r = ps.uevcb_ara("format")
    assert r["durum"] == "ok" and r["toplam_kurulus"] == 3 and [k["kurulus_id"] for k in r["kuruluslar"]] == [1, 3]
    assert r["kuruluslar"][0]["uevcbler"] == [{"id": 10, "eic": "40X0000000000001A", "name": "UEVÇB 1"}]
    assert r["kuruluslar"][1]["uevcbler"] == [] and "SEF1181" in r["kuruluslar"][1]["hata"]   # bir kuruluş düşerse ötekiler gelir
    ps.uevcb_ara("BAŞKA"); assert istemci.org_cagri == 1                                     # kuruluş listesi önbellekten
    assert ps.uevcb_ara("yok böyle")["kuruluslar"] == []
    ps._ORG_ONBELLEK["zaman"] = pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=7)
    ps.uevcb_ara("format"); assert istemci.org_cagri == 2                                    # 6 saat sonra yenilenir


def test_uevcb_ara_kimlik_yok(monkeypatch):
    monkeypatch.setattr(ps, "kimlik_var", lambda: False)
    assert ps.uevcb_ara("format")["durum"] == "kimlik_yok"


def test_uevcb_ara_ucu(istemci):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "viewer", "exp": 0}
    try:
        c = TestClient(api_main.app)
        assert c.get("/v1/epias/uevcb-ara?kurulus=fo").status_code == 422
        j = c.get("/v1/epias/uevcb-ara?kurulus=format").json(); assert j["durum"] == "ok" and len(j["kuruluslar"]) == 2
        from pvquant.services import piyasa_service
        piyasa_service.kimlik_var = lambda: False
        assert c.get("/v1/epias/uevcb-ara?kurulus=format").status_code == 503
    finally:
        api_main.app.dependency_overrides.clear()
