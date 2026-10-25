"""24.10 Faz 1 — /v1/yonetim kapıları (DB'siz: servis monkeypatch, GERÇEK jeton akışı).
Kapsam ayrımı: platform jetonu müşteri ucunu açamaz, müşteri jetonu yönetim ucunu açamaz; sahip-only uçlar; denetim izi
çağrıları; kiracı oluşturma/askıya alma uçları servis sözleşmesiyle."""
import datetime as dt
import jwt as _jwt
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from pvquant.services import auth_service as au, platform_service as ps, denetim_service as dz, basvuru_service


@pytest.fixture(autouse=True)
def _ortam(monkeypatch):
    monkeypatch.setenv("PVQ_JWT_SECRET", "test-sirri-0123456789abcdef-uzun")
    kayitlar = []
    monkeypatch.setattr(dz, "kaydet", lambda *a, **k: kayitlar.append((a, k)) or True)
    yield kayitlar
    ps.oturum_onbellegi_dusur(); au.oturum_onbellegi_dusur()
    api_main.app.dependency_overrides.clear()


def _jeton(**ek):
    g = {"sub": "p1", "kapsam": "platform", "rol": "sahip", "sv": 0, "exp": dt.datetime.utcnow() + dt.timedelta(hours=1)}
    g.update(ek)
    return {"Authorization": "Bearer " + _jwt.encode(g, au._sir(), algorithm="HS256")}


def _musteri_jeton():
    return {"Authorization": "Bearer " + _jwt.encode({"sub": "u1", "tenant_id": "t1", "role": "admin", "sv": 0,
                                                       "exp": dt.datetime.utcnow() + dt.timedelta(hours=1)}, au._sir(), algorithm="HS256")}


def test_kapsamlar_karismaz(monkeypatch):
    monkeypatch.setattr(ps, "oturum_durumu", lambda p: {"sv": 0, "aktif": True, "rol": "sahip", "email": "s@pvq"})
    monkeypatch.setattr(au, "oturum_durumu", lambda u: {"sv": 0, "aktif": True, "kiraci_durum": "active"})
    monkeypatch.setattr(ps, "ben", lambda p: {"id": "p1", "email": "s@pvq", "rol": "sahip", "totp_aktif": True})
    c = TestClient(api_main.app)
    assert c.get("/v1/yonetim/ben", headers=_jeton()).status_code == 200            # platform → yönetim ucu
    assert c.get("/v1/plants", headers=_jeton()).status_code == 403                 # platform jetonu müşteri ucunda 403
    assert c.get("/v1/yonetim/ben", headers=_musteri_jeton()).status_code == 403    # müşteri jetonu yönetim ucunda 403
    assert c.get("/v1/yonetim/ben").status_code == 422                              # başlık yok


def test_platform_surum_ve_pasif(monkeypatch):
    durum = {"sv": 2, "aktif": True, "rol": "operator", "email": "o@pvq"}
    monkeypatch.setattr(ps, "oturum_durumu", lambda p: dict(durum))
    monkeypatch.setattr(ps, "ben", lambda p: {"id": "p1"})
    c = TestClient(api_main.app)
    assert c.get("/v1/yonetim/ben", headers=_jeton(sv=2)).status_code == 200
    assert c.get("/v1/yonetim/ben", headers=_jeton(sv=1)).status_code == 401       # sürüm artmış
    durum["aktif"] = False
    assert c.get("/v1/yonetim/ben", headers=_jeton(sv=2)).status_code == 401       # pasif


def test_sahip_only_ve_operator(monkeypatch):
    monkeypatch.setattr(ps, "oturum_durumu", lambda p: {"sv": 0, "aktif": True, "rol": "operator", "email": "o@pvq"})
    monkeypatch.setattr(ps, "operator_listesi", lambda: [])
    monkeypatch.setattr(ps, "kiraci_listesi", lambda a: [{"id": "t1", "ad": "A"}])
    c = TestClient(api_main.app)
    assert c.get("/v1/yonetim/operatorler", headers=_jeton(rol="operator")).status_code == 403   # operatör sahip ucunu açamaz
    assert c.get("/v1/yonetim/kiracilar", headers=_jeton(rol="operator")).json() == {"kiracilar": [{"id": "t1", "ad": "A"}]}


def test_kiraci_olustur_ve_askiya_al(monkeypatch, _ortam):
    monkeypatch.setattr(ps, "oturum_durumu", lambda p: {"sv": 0, "aktif": True, "rol": "sahip", "email": "s@pvq"})
    monkeypatch.setattr(ps, "kiraci_olustur", lambda a, f, e, plan="pilot": {"tenant_id": "t9", "user_id": "u9", "davet_gonderildi": False, "davet_baglantisi": "https://x/parola-yenile?jeton=GIZLI"})
    monkeypatch.setattr(ps, "kiraci_guncelle", lambda a, t, **k: {"eski": {"name": "F", "plan": "pilot", "status": "active"}, "yeni": {"name": "F", "plan": "pilot", "status": k.get("status")}})
    c = TestClient(api_main.app)
    y = c.post("/v1/yonetim/kiracilar", json={"firma": "Firma", "yonetici_eposta": "A@B.C"}, headers=_jeton())
    assert y.status_code == 201 and y.json()["tenant_id"] == "t9" and "davet_baglantisi" in y.json()
    # denetim izine davet bağlantısı (jeton) YAZILMAZ
    kayit = [k for a, k in _ortam if a[1] == "kiraci_olustur"][0]
    assert "GIZLI" not in str(kayit) and kayit["ayrinti"]["yonetici_eposta"] == "a@b.c"
    y = c.put("/v1/yonetim/kiracilar/t9", json={"durum": "suspended"}, headers=_jeton())
    assert y.status_code == 200 and y.json()["yeni"]["status"] == "suspended"
    assert c.put("/v1/yonetim/kiracilar/t9", json={"durum": "bozuk"}, headers=_jeton()).status_code in (200, 422)


def test_basvurular_platforma_tasindi(monkeypatch, _ortam):
    monkeypatch.setattr(ps, "oturum_durumu", lambda p: {"sv": 0, "aktif": True, "rol": "operator", "email": "o@pvq"})
    monkeypatch.setattr(basvuru_service, "listele", lambda n=100: [{"id": "b1"}])
    monkeypatch.setattr(basvuru_service, "okundu_isaretle", lambda i: True)
    c = TestClient(api_main.app)
    assert c.get("/v1/yonetim/basvurular", headers=_jeton(rol="operator")).json() == {"basvurular": [{"id": "b1"}]}
    assert c.post("/v1/yonetim/basvurular/b1/okundu", headers=_jeton(rol="operator")).json() == {"tamam": True}
    assert any(a[1] == "basvuru_okundu" for a, k in _ortam)


def test_giris_ucu_ve_denetim(monkeypatch, _ortam):
    monkeypatch.setattr(ps, "giris", lambda e, s, k=None: None if s != "dogru" else {"token": "x", "rol": "sahip", "email": e, "iki_adim_kurulmali": True})
    c = TestClient(api_main.app)
    assert c.post("/v1/yonetim/giris", json={"email": "s@pvq", "sifre": "yanlis"}).status_code == 401
    assert c.post("/v1/yonetim/giris", json={"email": "s@pvq", "sifre": "dogru"}).json()["iki_adim_kurulmali"] is True
    eylemler = [a[1] for a, k in _ortam]
    assert "giris_basarisiz" in eylemler and "giris" in eylemler


def test_musteri_girisi_denetim_izine(monkeypatch, _ortam):
    monkeypatch.setattr(au, "giris", lambda e, s, k=None: {"token": "t", "user_id": "u1", "tenant_id": "t1", "role": "admin"})
    c = TestClient(api_main.app)
    assert c.post("/v1/auth/login", json={"email": "a@b.c", "sifre": "x" * 10}).status_code == 200
    assert any(a[0] == "musteri" and a[1] == "giris" and k.get("tenant_id") == "t1" for a, k in _ortam)


# ---------------- 25.10 Faz 3: sistem izleme uçları ----------------
def test_sistem_uclari_kapsam_ve_suzgec(monkeypatch):
    from pvquant.services import sistem_service as ss
    monkeypatch.setattr(ps, "oturum_durumu", lambda p: {"sv": 0, "aktif": True, "rol": "operator", "email": "o@pvq"})
    monkeypatch.setattr(au, "oturum_durumu", lambda u: {"sv": 0, "aktif": True, "kiraci_durum": "active"})
    monkeypatch.setattr(ss, "ozet", lambda a: {"nabiz": {"durum": "calisiyor"}, "aktor": a})
    gorulen = {}
    monkeypatch.setattr(ss, "isler", lambda a, **k: gorulen.update(k) or {"isler": [{"kod": "sabah_tahmin", "ayrinti": "KeyError: x"}], "pencere_saat": k["saat"], "is_turleri": []})
    monkeypatch.setattr(ss, "santraller", lambda a, **k: {"santraller": [], "esik": {"scada_saat": 48, "kosu_saat": 30}, "toplam": 0, "sorunlu": k["sorunlu"]})
    c = TestClient(api_main.app)
    y = c.get("/v1/yonetim/sistem", headers=_jeton(rol="operator"))                 # operatör de okur (salt okunur)
    assert y.status_code == 200 and y.json()["aktor"] == "p1"
    y = c.get("/v1/yonetim/isler?saat=72&yalniz_hata=true&job=sabah_tahmin&tenant_id=t1&limit=50", headers=_jeton(rol="operator"))
    assert y.status_code == 200 and y.json()["isler"][0]["ayrinti"] == "KeyError: x"   # hata ayrıntısı platformda GÖRÜNÜR
    assert gorulen == {"saat": 72, "yalniz_hata": True, "job": "sabah_tahmin", "tenant_id": "t1", "limit": 50}
    assert c.get("/v1/yonetim/santraller?sorunlu=true", headers=_jeton()).json()["sorunlu"] is True
    for yol in ("/v1/yonetim/sistem", "/v1/yonetim/isler", "/v1/yonetim/santraller"):
        assert c.get(yol, headers=_musteri_jeton()).status_code == 403            # müşteri jetonu platform ucunu açamaz
        assert c.get(yol).status_code == 422                                      # başlık yok
