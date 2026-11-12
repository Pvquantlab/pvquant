"""v2.608 (Faz 5 F5-F Tur 3) — yetki ve izolasyon: kiracı A'nın santrali kiracı B jetonuyla 404; viewer okur; platform uçları müşteri jetonuyla
kapalı; boş santralda (veri yok) Genel bakış ve hizmet sağlığı sıfır uydurmadan «kritik/veri bekleniyor» der (test DB)."""
from __future__ import annotations

import datetime as dt
import uuid

import pytest
from sqlalchemy import text

from pvquant.db import bakim_baglami, sistem_baglami
from pvquant.services import genel_bakis_service as gb
from pvquant.services import hizmet_sagligi_service as hs

SIMDI = dt.datetime(2026, 11, 20, 8, 0, tzinfo=dt.timezone.utc)


@pytest.fixture()
def bos_santral():
    """Kiracı A: hiç verisi olmayan tek santral (segment seçilmemiş); kiracı B: santralsız."""
    ta, tb, pid = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    with sistem_baglami() as s:
        for t, ad in ((ta, "T3 Kiracı A"), (tb, "T3 Kiracı B")):
            s.execute(text("INSERT INTO tenants(id, name, status) VALUES(:t, :a, 'active')"), {"t": t, "a": ad})
        s.execute(text("INSERT INTO plants(id, tenant_id, name, capacity_kwp, lat, lon, tz, params_json) VALUES(:p, :t, 'T3 Boş GES', 500, 37.0, 32.0, 'Europe/Istanbul', '{}')"),
                  {"p": pid, "t": ta})
    yield ta, tb, pid
    with bakim_baglami() as s:
        s.execute(text("DELETE FROM plants WHERE id = :p"), {"p": pid})
        s.execute(text("DELETE FROM tenants WHERE id IN (CAST(:a AS uuid), CAST(:b AS uuid))"), {"a": ta, "b": tb})


def test_bos_santral_sifir_uydurmaz(bos_santral):
    from pvquant.services import plant_service
    ta, _, pid = bos_santral
    o = gb.ozet(ta, {**plant_service.getir(ta, pid), "id": pid}, simdi=SIMDI)
    assert o["bugun"]["durum"] == "kritik" and o["bugun"]["beklenen_kwh"] is None and o["bugun"]["gerceklesen_kwh"] is None
    assert o["yarin"]["beklenen_kwh"] is None and o["yarin"]["durum"] == "dikkat" and "segment" in o["yarin"]["eylem"]     # yükümlülük bilinmiyor
    assert o["finans"]["hesaplanamiyor"] and o["finans"]["son_sonuc"] is None
    assert o["genel"]["durum"] == "kritik" and "bugun" in o["genel"]["eylem_gereken"]
    h = hs.ozet(ta, simdi=SIMDI)
    assert len(h["santraller"]) == 1 and h["santraller"][0]["durum"] == "kritik" and {"veri", "tahmin"} <= set(h["santraller"][0]["eylem_gereken"])
    assert h["santraller"][0]["boyutlar"]["kgup"]["eksik"][0] == "segment" and h["ozet"]["durum"] == "kritik"
    assert hs.ozet(bos_santral[1], simdi=SIMDI)["santraller"] == []                                                       # kiracı B boş


def test_uclar_kiraci_izolasyonu_ve_viewer(bos_santral, monkeypatch):
    from fastapi.testclient import TestClient

    import apps.api.main as api_main
    from apps.api.deps import gecerli_kullanici
    ta, tb, pid = bos_santral
    c = TestClient(api_main.app)
    try:
        api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": tb, "role": "admin", "exp": 0}
        assert c.get(f"/v1/plants/{pid}/genel-bakis").status_code == 404                  # başka kiracının santrali yok sayılır (sızdırmaz)
        assert c.get("/v1/hizmet-sagligi").json()["santraller"] == []
        api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": ta, "role": "viewer", "exp": 0}
        y = c.get(f"/v1/plants/{pid}/genel-bakis")
        assert y.status_code == 200 and y.json()["santral"]["id"] == pid and y.json()["genel"]["durum"] == "kritik"       # viewer okur
        hz = c.get("/v1/hizmet-sagligi").json()
        assert [p["id"] for p in hz["santraller"]] == [pid]
        assert c.get("/v1/sozluk/durum").status_code == 200
    finally:
        api_main.app.dependency_overrides.clear()


def test_platform_uclari_musteri_jetonuyla_kapali(monkeypatch):
    import jwt as _jwt
    from fastapi.testclient import TestClient

    import apps.api.main as api_main
    from pvquant.services import auth_service as au
    monkeypatch.setenv("PVQ_JWT_SECRET", "test-sirri-0123456789abcdef-uzun")
    musteri = {"Authorization": "Bearer " + _jwt.encode({"sub": "u", "tenant_id": str(uuid.uuid4()), "role": "admin",
                                                          "exp": dt.datetime.now(dt.UTC) + dt.timedelta(hours=1)}, au._sir(), algorithm="HS256")}
    c = TestClient(api_main.app)
    for yol in ("/v1/yonetim/hizmet-sagligi", "/v1/yonetim/sistem-sagligi"):
        assert c.get(yol, headers=musteri).status_code in (401, 403), yol                   # müşteri jetonu platform kapsamı değil
        assert c.get(yol).status_code in (401, 422), yol                                     # jetonsuz
    for yol in ("/v1/hizmet-sagligi", "/v1/sozluk/durum"):
        assert c.get(yol).status_code in (401, 422), yol
