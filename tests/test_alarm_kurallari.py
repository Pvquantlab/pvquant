"""v2.265 — ek alarm kuralları (opt-in, SAF), okundu/atama kapıları, damga ETag/304."""
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.services import alarm_service as al
from pvquant.services import damga_service


def test_secili_ve_esik_varsayilan():
    assert al.secili_kurallar({"params_json": None}) == []
    assert al.secili_kurallar({"params_json": '{"alarm_kurallari": ["clipping_orani_yuksek", "yok", "pr_dustu"]}'}) == ["pr_dustu", "clipping_orani_yuksek"]
    e = al.esikler({"params_json": {"alarm_esik": {"pr_esik": 0.75, "bilinmeyen": 1}}})
    assert e["pr_esik"] == 0.75 and e["clipping_esik"] == 0.15 and "bilinmeyen" not in e


def test_ek_alarmlar_yalniz_secili_ve_esik():
    p = {"name": "K", "params_json": {"alarm_kurallari": ["pr_dustu", "clipping_orani_yuksek", "iletisim_kesintisi"], "alarm_esik": {"iletisim_esik_saat": 12}}}
    b = {"pr_30g": 0.72, "clipping_orani_7g": 0.30, "son_scada_saat_once": 10}
    r = al.ek_alarmlar(p, b)
    assert [x[0] for x in r] == ["clipping_orani_yuksek"] and r[0][1] == "bilgi" and "%30" in r[0][2]
    b["pr_30g"] = 0.60; b["son_scada_saat_once"] = 13
    assert [x[0] for x in al.ek_alarmlar(p, b)] == ["pr_dustu", "clipping_orani_yuksek", "iletisim_kesintisi"]
    assert al.ek_alarmlar({"name": "K", "params_json": {}}, b) == []          # seçilmemişse hiçbir ek kural
    assert al.ek_alarmlar({"name": "K", "params_json": {"alarm_kurallari": ["pr_dustu"]}}, {"pr_30g": None}) == []   # PR yoksa tire, alarm yok


def test_etag_kararli():
    d = {"son_scada": "2026-09-06T14:00:00+00:00", "acik_alarm": 0}
    assert damga_service.etag_uret(d) == damga_service.etag_uret(dict(d)) and damga_service.etag_uret(d) != damga_service.etag_uret({**d, "acik_alarm": 1})


@pytest.fixture()
def istemci(monkeypatch):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u1", "tenant_id": "t", "role": "editor", "exp": 0}
    monkeypatch.setattr(damga_service, "hesapla", lambda t, p: {"son_scada": "2026-09-06T14:00:00+00:00", "son_kosu": None, "acik_alarm": 2})
    kayit = {}
    monkeypatch.setattr(al, "okundu", lambda t, p, a, u: kayit.setdefault("okundu", (a, u)) or True)
    monkeypatch.setattr(al, "ata", lambda t, p, a, k: (_ for _ in ()).throw(ValueError("kullanıcı bu hesapta değil")) if k == "yabanci" else True)
    from pvquant.services import plant_service
    monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": p, "params_json": {"alarm_kurallari": ["pr_dustu"]}})
    monkeypatch.setattr(al, "kural_ayarla", lambda t, p, k, e: al.kural_durumu({"params_json": {"alarm_kurallari": k, "alarm_esik": e or {}}}))
    yield TestClient(api_main.app), kayit
    api_main.app.dependency_overrides.clear()


def test_damga_304(istemci):
    c, _ = istemci
    y = c.get("/v1/plants/p1/damga"); assert y.status_code == 200 and y.headers["ETag"].startswith('W/"') and y.json()["acik_alarm"] == 2
    assert c.get("/v1/plants/p1/damga", headers={"If-None-Match": y.headers["ETag"]}).status_code == 304
    assert c.get("/v1/plants/p1/damga", headers={"If-None-Match": 'W/"eski"'}).status_code == 200


def test_okundu_ata_kurallar(istemci):
    c, kayit = istemci
    assert c.post("/v1/plants/p1/alarmlar/a1/okundu").json() == {"okundu": True} and kayit["okundu"] == ("a1", "u1")
    assert c.post("/v1/plants/p1/alarmlar/a1/ata", json={"kime": "u2"}).json() == {"atandi": "u2"}
    assert c.post("/v1/plants/p1/alarmlar/a1/ata", json={"kime": "yabanci"}).status_code == 422
    j = c.get("/v1/plants/p1/alarm-kurallari").json()
    assert j["secili"] == ["pr_dustu"] and j["varsayilan"] == ["veri_gelmedi", "skill_dustu"] and j["esik"]["pr_esik"] == 0.70
    j2 = c.put("/v1/plants/p1/alarm-kurallari", json={"kurallar": ["clipping_orani_yuksek", "yok"], "esik": {"clipping_esik": 0.2}}).json()
    assert j2["secili"] == ["clipping_orani_yuksek"] and j2["esik"]["clipping_esik"] == 0.2
