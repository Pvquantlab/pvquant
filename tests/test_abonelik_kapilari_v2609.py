"""v2.609 (Faz 6 F6-E) — abonelik kapıları: `yetki_service.kapi_hukmu` (saf hüküm) + `deps.modul_gerekli` / `deps.kota_kontrol` / dış API kapısı.
Altı senaryo × iki kip (00 §5): Pilot → anahtar üretimi (dis_api yok) · Standart 2. portföy (portföy limiti, sözleşme ezmesi) · Kurumsal açık ·
süresi dolmuş Pilot (okuma serbest, yazma 403) · kiracı A kiracı B'yi okuyamaz · temsil jetonu yazamaz · dış API anahtarı (modül) · uyarı izi saatte bir.
Varsayılan kip uyarı: iş yapılır, yalnız başlık + denetim izi. Zorla kipi yalnız testte (monkeypatch)."""
from __future__ import annotations

import datetime as dt
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

import apps.api.main as api_main
from apps.api import deps
from apps.api.deps import gecerli_kullanici
from pvquant.db import bakim_baglami, sistem_baglami
from pvquant.services import abonelik_service as ab
from pvquant.services import api_anahtar_service as ak
from pvquant.services import denetim_service as dz
from pvquant.services import yetki_service as ys

BUGUN = dt.date.today()


@pytest.fixture()
def ortam(monkeypatch):
    """Dört kiracı: pilot, standart (portföy ezmesi 1), kurumsal, süresi dolmuş pilot; her birinde admin; pilot ve kurumsal için dış API anahtarı."""
    monkeypatch.setattr(ak, "_paylasimli_izin", lambda p, r, t: ak._kova_izin(p, r))
    kayit: list = []
    monkeypatch.setattr(dz, "kaydet", lambda *a, **k: kayit.append((a, k)) or True)
    deps._uyari_izi.clear()
    o = {"kayit": kayit}
    with sistem_baglami() as s:
        for ad, plan in (("pilot", "pilot"), ("standart", "standart"), ("kurumsal", "kurumsal"), ("eski", "pilot")):
            t, u = str(uuid.uuid4()), str(uuid.uuid4())
            s.execute(text("INSERT INTO tenants(id, name, status, plan) VALUES(:t, :n, 'active', :p)"), {"t": t, "n": f"KP {ad}", "p": plan})
            s.execute(text("INSERT INTO users(id, tenant_id, email, pw_hash, role, aktif, oturum_surumu) VALUES(:u, CAST(:t AS uuid), :e, 'x', 'admin', true, 0)"),
                      {"u": u, "t": t, "e": f"kp-{ad}-{t[:8]}@pvq.test"})
            ab.varsayilan_olustur(s, t, plan, aktor="test", bugun=BUGUN)
            o[ad] = (t, u)
        s.execute(text("UPDATE kiraci_abonelik SET kota_ezme = '{\"portfoy\": 1}'::jsonb WHERE tenant_id = CAST(:t AS uuid)"), {"t": o["standart"][0]})
        s.execute(text("UPDATE kiraci_abonelik SET pilot_bitis = CURRENT_DATE - 1 WHERE tenant_id = CAST(:t AS uuid)"), {"t": o["eski"][0]})
    o["k_pilot"] = ak.uret(o["pilot"][0], "kp", ["tahmin:oku"])["anahtar"]
    o["k_kurumsal"] = ak.uret(o["kurumsal"][0], "kk", ["tahmin:oku"])["anahtar"]
    ys.onbellek_dusur()
    yield o
    ys.onbellek_dusur()
    api_main.app.dependency_overrides.pop(gecerli_kullanici, None)
    with bakim_baglami() as s:
        for ad in ("pilot", "standart", "kurumsal", "eski"):
            t = o[ad][0]
            for tb in ("kullanim_sayac", "api_keys", "denetim_izi", "portfoy_uyelik", "portfoy", "users"):
                s.execute(text(f"DELETE FROM {tb} WHERE tenant_id = CAST(:t AS uuid)"), {"t": t})
            s.execute(text("DELETE FROM tenants WHERE id = CAST(:t AS uuid)"), {"t": t})


def _kip(monkeypatch, kip: str):
    monkeypatch.setattr(ys, "zorlama_kipi", lambda: kip)


def _giris(o, ad, **ek):
    t, u = o[ad]
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": u, "tenant_id": t, "role": "admin", "exp": 0, **ek}
    return TestClient(api_main.app)


def test_kapi_hukmu_saf(ortam):
    o = ortam
    assert ys.kapi_hukmu(o["kurumsal"][0], modul="dis_api", alan="portfoy", yazma=True) is None            # her şey açık
    h = ys.kapi_hukmu(o["pilot"][0], modul="dis_api", yazma=True)
    assert h and h["kod"] == "modul_kapali" and h["http"] == 403 and "Kurumsal API" in h["mesaj"] and "Ayarlar › Aboneliğiniz" in h["mesaj"]
    assert ys.kapi_hukmu(o["pilot"][0], modul="tahmin") is None
    h = ys.kapi_hukmu(o["pilot"][0], alan="portfoy")                                                        # pilot portföy limiti 0 → ilk portföy bile aşım
    assert h and h["kod"] == "kota_asildi" and h["http"] == 409 and h["ayrinti"]["limit"] == 0 and h["ayrinti"]["kullanim"] == 0
    h = ys.kapi_hukmu(o["eski"][0], modul="tahmin", yazma=True)                                             # süresi dolmuş: yazma 403, okuma serbest
    assert h and h["kod"] == "abonelik_sona_erdi" and "sona erdi" in h["mesaj"]
    assert ys.kapi_hukmu(o["eski"][0], modul="tahmin") is None
    assert ys.kota_durumu(3, 3)["durum"] == "dolu" and ys.kota_durumu(3, 4)["durum"] == "asildi"           # dolu + 1 = aşım → yer yok


def test_pilot_anahtar_uretimi_iki_kip(ortam, monkeypatch):
    o = ortam; c = _giris(o, "pilot")
    _kip(monkeypatch, "zorla")
    r = c.post("/v1/api-anahtarlari", json={"ad": "x", "kapsamlar": ["tahmin:oku"]})
    assert r.status_code == 403 and r.json()["detail"]["kod"] == "modul_kapali" and r.json()["detail"]["modul"] == "dis_api"
    _kip(monkeypatch, "uyari")
    r = c.post("/v1/api-anahtarlari", json={"ad": "x", "kapsamlar": ["tahmin:oku"]})
    assert r.status_code == 201 and r.headers["X-PVQuant-Abonelik"] == "uyari" and r.headers["X-PVQuant-Abonelik-Kod"] == "modul_kapali"
    izler = [k for a, k in o["kayit"] if a[1] == "abonelik_uyari"]
    assert len(izler) == 1 and izler[0]["ayrinti"]["kod"] == "modul_kapali" and izler[0]["ayrinti"]["yol"] == "/v1/api-anahtarlari" and izler[0]["ayrinti"]["kip"] == "uyari"
    r = c.post("/v1/api-anahtarlari", json={"ad": "y", "kapsamlar": ["tahmin:oku"]})                        # ikinci uyarı: iz saatte bir
    assert r.status_code == 201 and len([k for a, k in o["kayit"] if a[1] == "abonelik_uyari"]) == 1
    c2 = _giris(o, "kurumsal"); r = c2.post("/v1/api-anahtarlari", json={"ad": "z", "kapsamlar": ["tahmin:oku"]})
    assert r.status_code == 201 and "X-PVQuant-Abonelik" not in r.headers                                   # kurumsal: açık, başlık yok


def test_standart_portfoy_limiti_iki_kip(ortam, monkeypatch):
    o = ortam; c = _giris(o, "standart")
    g = {"ad": "P1", "tur": "isletme", "gecerli_bas": "2026-01-01"}
    _kip(monkeypatch, "uyari")
    r = c.post("/v1/portfoyler", json=g); assert r.status_code == 200 and "X-PVQuant-Abonelik" not in r.headers        # 0/1 → yer var
    ys.onbellek_dusur(o["standart"][0])
    r = c.post("/v1/portfoyler", json={**g, "ad": "P2"}); assert r.status_code == 200 and r.headers["X-PVQuant-Abonelik-Kod"] == "kota_asildi"   # 1/1 dolu → yer yok, uyarı kipinde yapılır
    ys.onbellek_dusur(o["standart"][0])
    _kip(monkeypatch, "zorla")
    r = c.post("/v1/portfoyler", json={**g, "ad": "P3"})
    assert r.status_code == 409 and r.json()["detail"]["kod"] == "kota_asildi" and r.json()["detail"]["limit"] == 1 and r.json()["detail"]["kullanim"] == 2 and r.json()["detail"]["kaynak"] == "ezme"
    with sistem_baglami() as s:
        assert s.execute(text("SELECT count(*) FROM portfoy WHERE tenant_id = CAST(:t AS uuid)"), {"t": o["standart"][0]}).scalar() == 2
    r = c.get("/v1/portfoy/finansal-etki"); assert r.status_code != 403                                                  # standart FEM açık (zorla kipinde bile)


def test_suresi_dolmus_pilot_okur_yazamaz(ortam, monkeypatch):
    o = ortam; c = _giris(o, "eski")
    _kip(monkeypatch, "zorla")
    r = c.get("/v1/abonelik"); assert r.status_code == 200 and r.json()["durum"] == "sona_erdi" and r.json()["tenant_id"] == o["eski"][0]   # giriş var, okuma serbest
    r = c.post("/v1/portfoyler", json={"ad": "P", "tur": "isletme", "gecerli_bas": "2026-01-01"})
    assert r.status_code == 403 and r.json()["detail"]["kod"] == "abonelik_sona_erdi"
    r = c.post("/v1/api-anahtarlari", json={"ad": "x", "kapsamlar": ["tahmin:oku"]}); assert r.status_code == 403 and r.json()["detail"]["kod"] == "abonelik_sona_erdi"
    r = c.get("/v1/portfoy/finansal-etki"); assert r.status_code == 403 and r.json()["detail"]["kod"] == "modul_kapali"   # pilot: FEM modülü yok (okuma kapısı modül)
    _kip(monkeypatch, "uyari")
    r = c.post("/v1/api-anahtarlari", json={"ad": "x", "kapsamlar": ["tahmin:oku"]}); assert r.status_code == 201 and r.headers["X-PVQuant-Abonelik-Kod"] == "abonelik_sona_erdi"


def test_kiraci_ayrimi_ve_temsil(ortam, monkeypatch):
    o = ortam
    _kip(monkeypatch, "zorla")
    c = _giris(o, "pilot"); a = c.get("/v1/abonelik").json()
    c = _giris(o, "kurumsal"); b = c.get("/v1/abonelik").json()
    assert a["tenant_id"] == o["pilot"][0] and b["tenant_id"] == o["kurumsal"][0] and a["plan"]["ad"] == "pilot" and b["plan"]["ad"] == "kurumsal"
    assert not a["moduller"]["dis_api"]["dahil"] and b["moduller"]["dis_api"]["dahil"]
    c = _giris(o, "kurumsal", temsil=True)                                                                  # görüntüleme oturumu: okur, yazamaz
    assert c.get("/v1/abonelik").status_code == 200
    assert c.post("/v1/abonelik/talep", json={"tur": "plan", "hedef": "standart"}).status_code == 403
    assert c.post("/v1/api-anahtarlari", json={"ad": "x", "kapsamlar": ["tahmin:oku"]}).status_code == 403


def test_dis_api_anahtari_iki_kip(ortam, monkeypatch):
    o = ortam; c = TestClient(api_main.app)
    _kip(monkeypatch, "zorla")
    r = c.get("/v1/dis/santraller", headers={"X-API-Key": o["k_pilot"]})
    assert r.status_code == 403 and r.json()["kod"] == "modul_kapali" and "schema_version" in r.json()      # dış API gövdesi {detail, kod}
    r = c.get("/v1/dis/santraller", headers={"X-API-Key": o["k_kurumsal"]}); assert r.status_code == 200 and "X-PVQuant-Abonelik" not in r.headers
    _kip(monkeypatch, "uyari")
    r = c.get("/v1/dis/santraller", headers={"X-API-Key": o["k_pilot"]})
    assert r.status_code == 200 and r.headers["X-PVQuant-Abonelik"] == "uyari" and r.headers["X-PVQuant-Abonelik-Kod"] == "modul_kapali"
    iz = [k for a, k in o["kayit"] if a[1] == "abonelik_uyari" and a[0] == "dis_api"]
    assert len(iz) == 1 and iz[0]["tenant_id"] == o["pilot"][0] and iz[0]["aktor_id"] is None


def test_kip_varsayilani_uyari():
    assert ys.zorlama_kipi() == "uyari"


def test_uyari_izi_gercek_yazilir(monkeypatch):
    """Öz inceleme: dış API kapsamında aktörsüz `abonelik_uyari` satırı denetim_izi kısıtlarından gerçekten geçer (fixture'ın monkeypatch'i yok)."""
    from starlette.requests import Request as _R
    from starlette.responses import Response as _Y
    t = str(uuid.uuid4())
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO tenants(id, name, status, plan) VALUES(:t, 'KP iz', 'active', 'pilot')"), {"t": t})
    try:
        deps._uyari_izi.clear()
        istek = _R({"type": "http", "method": "GET", "path": "/v1/dis/santraller", "headers": [], "query_string": b"", "client": ("127.0.0.1", 1), "server": ("t", 80), "scheme": "http"})
        yanit = _Y()
        hukum = {"kod": "modul_kapali", "http": 403, "mesaj": "m", "ayrinti": {"modul": "dis_api", "plan": "pilot"}}
        deps.abonelik_kapisi_uygula(istek, yanit, t, hukum, kapsam="dis_api", nesne="dis_api", aktor_id=None)
        assert yanit.headers["X-PVQuant-Abonelik"] == "uyari" and istek.state.abonelik_uyari == "modul_kapali"
        with sistem_baglami() as s:
            r = s.execute(text("SELECT kapsam, aktor_id, eylem, ayrinti->>'kod' AS kod, ayrinti->>'yol' AS yol FROM denetim_izi WHERE tenant_id = CAST(:t AS uuid)"), {"t": t}).mappings().all()
        assert len(r) == 1 and r[0]["kapsam"] == "dis_api" and r[0]["aktor_id"] is None and r[0]["eylem"] == "abonelik_uyari" and r[0]["kod"] == "modul_kapali" and r[0]["yol"] == "/v1/dis/santraller"
    finally:
        with bakim_baglami() as s:
            s.execute(text("DELETE FROM denetim_izi WHERE tenant_id = CAST(:t AS uuid)"), {"t": t})
            s.execute(text("DELETE FROM tenants WHERE id = CAST(:t AS uuid)"), {"t": t})


def test_response_donen_ucta_baslik(ortam, monkeypatch):
    """Öz inceleme: uç `Response(...)` döndürünce (dış API 304) başlık middleware'den gelir."""
    from fastapi import Depends as _D
    from starlette.responses import Response as _Y
    o = ortam
    if not any(getattr(r, "path", "") == "/v1/_test/abonelik-response" for r in api_main.app.router.routes):   # dış API 304/HTML uçları santral + koşu ister; aynı dönüş kalıbı küçük uçla
        api_main.app.add_api_route("/v1/_test/abonelik-response", lambda _k=_D(deps.modul_gerekli("dis_api")): _Y(status_code=204), methods=["GET"])   # noqa: B008 (Depends kalıbı)
    c = _giris(o, "pilot")
    _kip(monkeypatch, "uyari")
    r = c.get("/v1/_test/abonelik-response")
    assert r.status_code == 204 and r.headers["X-PVQuant-Abonelik"] == "uyari" and r.headers["X-PVQuant-Abonelik-Kod"] == "modul_kapali"
    c = _giris(o, "kurumsal"); r = c.get("/v1/_test/abonelik-response"); assert r.status_code == 204 and "X-PVQuant-Abonelik" not in r.headers
    c2 = _giris(o, "pilot")
    _kip(monkeypatch, "zorla")
    r = c2.post(f"/v1/portfoyler/{uuid.uuid4()}/uyeler", json={"plant_id": str(uuid.uuid4()), "gecerli_bas": "2026-01-01"})
    assert r.status_code == 403 and r.json()["detail"]["kod"] == "modul_kapali"                           # üyelik ekleme de portföy modülü ister
