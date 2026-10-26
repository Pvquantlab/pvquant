"""24.10 Faz 1 — /v1/yonetim kapıları (DB'siz: servis monkeypatch, GERÇEK jeton akışı).
Kapsam ayrımı: platform jetonu müşteri ucunu açamaz, müşteri jetonu yönetim ucunu açamaz; sahip-only uçlar; denetim izi
çağrıları; kiracı oluşturma/askıya alma uçları servis sözleşmesiyle."""
import datetime as dt
import jwt as _jwt
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main

# 26.10 denetim-3: yonetim._uuid biçimsiz kimliği 422 ile keser — fikstürler gerçek UUID
T1 = "11111111-1111-4111-8111-111111111111"
T9 = "99999999-9999-4999-8999-999999999999"
PL1 = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
B1 = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
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
    return {"Authorization": "Bearer " + _jwt.encode({"sub": "u1", "tenant_id": T1, "role": "admin", "sv": 0,
                                                       "exp": dt.datetime.utcnow() + dt.timedelta(hours=1)}, au._sir(), algorithm="HS256")}


def test_kapsamlar_karismaz(monkeypatch):
    monkeypatch.setattr(ps, "oturum_durumu", lambda p: {"sv": 0, "aktif": True, "rol": "sahip", "email": "s@pvq", "totp_aktif": True})
    monkeypatch.setattr(au, "oturum_durumu", lambda u: {"sv": 0, "aktif": True, "kiraci_durum": "active"})
    monkeypatch.setattr(ps, "ben", lambda p: {"id": "p1", "email": "s@pvq", "rol": "sahip", "totp_aktif": True})
    c = TestClient(api_main.app)
    assert c.get("/v1/yonetim/ben", headers=_jeton()).status_code == 200            # platform → yönetim ucu
    assert c.get("/v1/plants", headers=_jeton()).status_code == 403                 # platform jetonu müşteri ucunda 403
    assert c.get("/v1/yonetim/ben", headers=_musteri_jeton()).status_code == 403    # müşteri jetonu yönetim ucunda 403
    assert c.get("/v1/yonetim/ben").status_code == 422                              # başlık yok


def test_platform_surum_ve_pasif(monkeypatch):
    durum = {"sv": 2, "aktif": True, "rol": "operator", "email": "o@pvq", "totp_aktif": True}
    monkeypatch.setattr(ps, "oturum_durumu", lambda p: dict(durum))
    monkeypatch.setattr(ps, "ben", lambda p: {"id": "p1"})
    c = TestClient(api_main.app)
    assert c.get("/v1/yonetim/ben", headers=_jeton(sv=2)).status_code == 200
    assert c.get("/v1/yonetim/ben", headers=_jeton(sv=1)).status_code == 401       # sürüm artmış
    durum["aktif"] = False
    assert c.get("/v1/yonetim/ben", headers=_jeton(sv=2)).status_code == 401       # pasif


def test_sahip_only_ve_operator(monkeypatch):
    monkeypatch.setattr(ps, "oturum_durumu", lambda p: {"sv": 0, "aktif": True, "rol": "operator", "email": "o@pvq", "totp_aktif": True})
    monkeypatch.setattr(ps, "operator_listesi", lambda: [])
    monkeypatch.setattr(ps, "kiraci_listesi", lambda a: [{"id": T1, "ad": "A"}])
    c = TestClient(api_main.app)
    assert c.get("/v1/yonetim/operatorler", headers=_jeton(rol="operator")).status_code == 403   # operatör sahip ucunu açamaz
    assert c.get("/v1/yonetim/kiracilar", headers=_jeton(rol="operator")).json() == {"kiracilar": [{"id": T1, "ad": "A"}]}


def test_kiraci_olustur_ve_askiya_al(monkeypatch, _ortam):
    monkeypatch.setattr(ps, "oturum_durumu", lambda p: {"sv": 0, "aktif": True, "rol": "sahip", "email": "s@pvq", "totp_aktif": True})
    monkeypatch.setattr(ps, "kiraci_olustur", lambda a, f, e, plan="pilot", rol=None: {"tenant_id": T9, "user_id": "u9", "davet_gonderildi": False, "davet_baglantisi": "https://x/parola-yenile?jeton=GIZLI"})
    monkeypatch.setattr(ps, "kiraci_guncelle", lambda a, t, **k: {"eski": {"name": "F", "plan": "pilot", "status": "active"}, "yeni": {"name": "F", "plan": "pilot", "status": k.get("status")}})
    c = TestClient(api_main.app)
    y = c.post("/v1/yonetim/kiracilar", json={"firma": "Firma", "yonetici_eposta": "A@B.C"}, headers=_jeton())
    assert y.status_code == 201 and y.json()["tenant_id"] == T9 and "davet_baglantisi" in y.json()
    # denetim izine davet bağlantısı (jeton) YAZILMAZ
    kayit = [k for a, k in _ortam if a[1] == "kiraci_olustur"][0]
    assert "GIZLI" not in str(kayit) and kayit["ayrinti"]["yonetici_eposta"] == "a@b.c"
    y = c.put(f"/v1/yonetim/kiracilar/{T9}", json={"durum": "suspended"}, headers=_jeton())
    assert y.status_code == 200 and y.json()["yeni"]["status"] == "suspended"
    assert c.put(f"/v1/yonetim/kiracilar/{T9}", json={"durum": "bozuk"}, headers=_jeton()).status_code in (200, 422)


def test_basvurular_platforma_tasindi(monkeypatch, _ortam):
    monkeypatch.setattr(ps, "oturum_durumu", lambda p: {"sv": 0, "aktif": True, "rol": "operator", "email": "o@pvq", "totp_aktif": True})
    monkeypatch.setattr(basvuru_service, "listele", lambda n=100: [{"id": B1}])
    monkeypatch.setattr(basvuru_service, "okundu_isaretle", lambda i: True)
    c = TestClient(api_main.app)
    assert c.get("/v1/yonetim/basvurular", headers=_jeton(rol="operator")).json() == {"basvurular": [{"id": B1}]}
    assert c.post(f"/v1/yonetim/basvurular/{B1}/okundu", headers=_jeton(rol="operator")).json() == {"tamam": True}
    assert any(a[1] == "basvuru_okundu" for a, k in _ortam)


def test_giris_ucu_ve_denetim(monkeypatch, _ortam):
    monkeypatch.setattr(ps, "giris", lambda e, s, k=None: None if s != "dogru" else {"token": "x", "rol": "sahip", "email": e, "iki_adim_kurulmali": True})
    c = TestClient(api_main.app)
    assert c.post("/v1/yonetim/giris", json={"email": "s@pvq", "sifre": "yanlis"}).status_code == 401
    assert c.post("/v1/yonetim/giris", json={"email": "s@pvq", "sifre": "dogru"}).json()["iki_adim_kurulmali"] is True
    eylemler = [a[1] for a, k in _ortam]
    assert "giris_basarisiz" in eylemler and "giris" in eylemler


def test_musteri_girisi_denetim_izine(monkeypatch, _ortam):
    monkeypatch.setattr(au, "giris", lambda e, s, k=None: {"token": "t", "user_id": "u1", "tenant_id": T1, "role": "admin"})
    c = TestClient(api_main.app)
    assert c.post("/v1/auth/login", json={"email": "a@b.c", "sifre": "x" * 10}).status_code == 200
    assert any(a[0] == "musteri" and a[1] == "giris" and k.get("tenant_id") == T1 for a, k in _ortam)


# ---------------- 25.10 Faz 3: sistem izleme uçları ----------------
def test_sistem_uclari_kapsam_ve_suzgec(monkeypatch):
    from pvquant.services import sistem_service as ss
    monkeypatch.setattr(ps, "oturum_durumu", lambda p: {"sv": 0, "aktif": True, "rol": "operator", "email": "o@pvq", "totp_aktif": True})
    monkeypatch.setattr(au, "oturum_durumu", lambda u: {"sv": 0, "aktif": True, "kiraci_durum": "active"})
    monkeypatch.setattr(ss, "ozet", lambda a: {"nabiz": {"durum": "calisiyor"}, "aktor": a})
    gorulen = {}
    monkeypatch.setattr(ss, "isler", lambda a, **k: gorulen.update(k) or {"isler": [{"kod": "sabah_tahmin", "ayrinti": "KeyError: x"}], "pencere_saat": k["saat"], "is_turleri": []})
    monkeypatch.setattr(ss, "santraller", lambda a, **k: {"santraller": [], "esik": {"scada_saat": 48, "kosu_saat": 30}, "toplam": 0, "sorunlu": k["sorunlu"]})
    c = TestClient(api_main.app)
    y = c.get("/v1/yonetim/sistem", headers=_jeton(rol="operator"))                 # operatör de okur (salt okunur)
    assert y.status_code == 200 and y.json()["aktor"] == "p1"
    y = c.get(f"/v1/yonetim/isler?saat=72&yalniz_hata=true&job=sabah_tahmin&tenant_id={T1}&limit=50", headers=_jeton(rol="operator"))
    assert y.status_code == 200 and y.json()["isler"][0]["ayrinti"] == "KeyError: x"   # hata ayrıntısı platformda GÖRÜNÜR
    assert gorulen == {"saat": 72, "yalniz_hata": True, "job": "sabah_tahmin", "tenant_id": T1, "limit": 50, "plant_id": None}
    assert c.get("/v1/yonetim/santraller?sorunlu=true", headers=_jeton()).json()["sorunlu"] is True
    for yol in ("/v1/yonetim/sistem", "/v1/yonetim/isler", "/v1/yonetim/santraller"):
        assert c.get(yol, headers=_musteri_jeton()).status_code == 403            # müşteri jetonu platform ucunu açamaz
        assert c.get(yol).status_code == 422                                      # başlık yok


# ---------------- 25.10 Faz 4: kullanım ucu ----------------
def test_kullanim_ucu(monkeypatch):
    from pvquant.services import kullanim_service as ks
    monkeypatch.setattr(ps, "oturum_durumu", lambda p: {"sv": 0, "aktif": True, "rol": "operator", "email": "o@pvq", "totp_aktif": True})
    monkeypatch.setattr(au, "oturum_durumu", lambda u: {"sv": 0, "aktif": True, "kiraci_durum": "active"})
    monkeypatch.setattr(ks, "ozet", lambda a, ay=None: {"ay": ay or "bu", "kiracilar": [], "aktor": a})
    monkeypatch.setattr(ks, "gunler", lambda a, t, ay=None: {"ay": ay or "bu", "tenant_id": t, "gunler": [{"gun": "2026-10-25", "dis_api": 3}]})
    c = TestClient(api_main.app)
    y = c.get("/v1/yonetim/kullanim?ay=2026-09", headers=_jeton(rol="operator"))
    assert y.status_code == 200 and y.json() == {"ay": "2026-09", "kiracilar": [], "aktor": "p1"}
    y = c.get(f"/v1/yonetim/kullanim?tenant_id={T1}", headers=_jeton())
    assert y.status_code == 200 and y.json()["gunler"][0]["dis_api"] == 3
    assert c.get("/v1/yonetim/kullanim", headers=_musteri_jeton()).status_code == 403
    assert c.get("/v1/yonetim/kullanim").status_code == 422


# ---------------- 25.10 denetim Y2: 2FA kurulmadan jeton yalnız kurulum uçlarını açar ----------------
def test_iki_adim_kurulmadan_kapsam_dar(monkeypatch):
    durum = {"sv": 0, "aktif": True, "rol": "sahip", "email": "s@pvq", "totp_aktif": False}
    monkeypatch.setattr(ps, "oturum_durumu", lambda p: dict(durum))
    monkeypatch.setattr(ps, "ben", lambda p: {"id": "p1", "email": "s@pvq", "rol": "sahip", "totp_aktif": False})
    monkeypatch.setattr(ps, "iki_adim_baslat", lambda p: {"secret": "S", "otpauth_uri": "otpauth://x"})
    monkeypatch.setattr(ps, "kiraci_listesi", lambda a: [])
    monkeypatch.setattr(ps, "operator_listesi", lambda: [])
    monkeypatch.setattr(ps, "oturum_yenile", lambda p, ilk=None: {"token": "t2", "rol": "sahip", "email": "s@pvq", "iki_adim_kurulmali": True})
    c = TestClient(api_main.app)
    assert c.get("/v1/yonetim/ben", headers=_jeton()).status_code == 200                       # kurulum yolları açık
    assert c.post("/v1/yonetim/iki-adim/baslat", headers=_jeton()).status_code == 200
    assert c.post("/v1/yonetim/oturum/yenile", headers=_jeton()).status_code == 200
    for yol in ("/v1/yonetim/kiracilar", "/v1/yonetim/sistem", "/v1/yonetim/kullanim", "/v1/yonetim/denetim", "/v1/yonetim/operatorler"):
        y = c.get(yol, headers=_jeton())
        assert y.status_code == 403 and "iki adımlı" in y.json()["detail"], yol                 # veri uçları kapalı
    durum["totp_aktif"] = True                                                                 # kurulum bitti → tam kapsam
    assert c.get("/v1/yonetim/kiracilar", headers=_jeton()).status_code == 200


# ---------------- 25.10 denetim O6 + O8 ----------------
def test_goruntule_izi_gunde_tek(monkeypatch, _ortam):
    monkeypatch.setattr(ps, "oturum_durumu", lambda p: {"sv": 0, "aktif": True, "rol": "operator", "email": "o@pvq", "totp_aktif": True})
    monkeypatch.setattr(ps, "kiraci_detay", lambda a, t: {"id": t, "ad": "F"})
    from pvquant.services import kullanim_service as ks
    monkeypatch.setattr(ks, "gunler", lambda a, t, ay=None: {"gunler": []})
    var = {"v": False}
    monkeypatch.setattr(dz, "_goruntule_bugun_var", lambda a, t: var["v"])
    c = TestClient(api_main.app)
    assert c.get(f"/v1/yonetim/kiracilar/{T1}", headers=_jeton(rol="operator")).status_code == 200
    assert c.get(f"/v1/yonetim/kullanim?tenant_id={T1}", headers=_jeton(rol="operator")).status_code == 200
    goruntule = [k for a, k in _ortam if a[1] == "kiraci_goruntule"]
    assert len(goruntule) == 2 and goruntule[0]["tenant_id"] == T1 and goruntule[0]["aktor_eposta"] == "o@pvq"
    var["v"] = True                                                                     # bugün zaten var → yazılmaz
    assert c.get(f"/v1/yonetim/kiracilar/{T1}", headers=_jeton(rol="operator")).status_code == 200
    assert len([k for a, k in _ortam if a[1] == "kiraci_goruntule"]) == 2
    # genel bakış süzgeci: eylem_haric servise iletilir
    gorulen = {}
    monkeypatch.setattr(dz, "listele", lambda **k: gorulen.update(k) or [])
    assert c.get("/v1/yonetim/denetim?eylem_haric=kiraci_goruntule", headers=_jeton()).status_code == 200
    assert gorulen["eylem_haric"] == "kiraci_goruntule"


def test_mutlak_oturum_siniri(monkeypatch):
    import time as _t
    monkeypatch.setattr(ps, "oturum_durumu", lambda p: {"sv": 0, "aktif": True, "rol": "sahip", "email": "s@pvq", "totp_aktif": True})
    monkeypatch.setattr(ps, "ben", lambda p: {"id": "p1"})
    gorulen = {}
    monkeypatch.setattr(ps, "oturum_yenile", lambda p, ilk=None: gorulen.update({"ilk": ilk}) or {"token": "t2", "rol": "sahip", "email": "s@pvq", "iki_adim_kurulmali": False})
    c = TestClient(api_main.app)
    simdi = int(_t.time())
    assert c.get("/v1/yonetim/ben", headers=_jeton(ilk=simdi - 3600)).status_code == 200              # 1 saatlik oturum
    assert c.get("/v1/yonetim/ben", headers=_jeton()).status_code == 200                              # eski jeton (ilk yok) doğal ömrüyle
    y = c.get("/v1/yonetim/ben", headers=_jeton(ilk=simdi - 13 * 3600))
    assert y.status_code == 401 and "üst sınırı" in y.json()["detail"]                                 # 13 saat → 401
    assert c.post("/v1/yonetim/oturum/yenile", headers=_jeton(ilk=simdi - 7200)).status_code == 200
    assert gorulen["ilk"] == simdi - 7200                                                              # ilk yenilemede taşınır


# ---------------- 26.10 D2: iş kayıtları santral süzgeci ----------------
def test_isler_plant_id_suzgeci(monkeypatch):
    from pvquant.services import sistem_service as ss
    monkeypatch.setattr(ps, "oturum_durumu", lambda p: {"sv": 0, "aktif": True, "rol": "operator", "email": "o@pvq", "totp_aktif": True})
    gorulen = {}
    monkeypatch.setattr(ss, "isler", lambda a, **k: gorulen.update(k) or {"isler": [], "pencere_saat": k["saat"], "is_turleri": []})
    c = TestClient(api_main.app)
    assert c.get(f"/v1/yonetim/isler?saat=720&yalniz_hata=true&plant_id={PL1}", headers=_jeton(rol="operator")).status_code == 200
    assert gorulen["plant_id"] == PL1 and gorulen["saat"] == 720 and gorulen["yalniz_hata"] is True


# ---------------- 26.10 Faz 5: planlar + kimliğe bürünme ----------------
def test_planlar_uclari(monkeypatch, _ortam):
    monkeypatch.setattr(ps, "oturum_durumu", lambda p: {"sv": 0, "aktif": True, "rol": "operator", "email": "o@pvq", "totp_aktif": True})
    monkeypatch.setattr(ps, "plan_listesi", lambda: [{"ad": "pilot", "santral_limit": 3}])
    gorulen = {}
    monkeypatch.setattr(ps, "plan_guncelle", lambda ad, **k: gorulen.update({"ad": ad, **k}) or {"ad": ad})
    c = TestClient(api_main.app)
    assert c.get("/v1/yonetim/planlar", headers=_jeton(rol="operator")).json()["planlar"][0]["ad"] == "pilot"   # operatör okur
    assert c.put("/v1/yonetim/planlar/pilot", json={"santral_limit": 5}, headers=_jeton(rol="operator")).status_code == 403   # yazma sahip
    monkeypatch.setattr(ps, "oturum_durumu", lambda p: {"sv": 0, "aktif": True, "rol": "sahip", "email": "s@pvq", "totp_aktif": True})
    y = c.put("/v1/yonetim/planlar/pilot", json={"santral_limit": 5, "sinirsiz": ["api_rpm_limit"]}, headers=_jeton())
    assert y.status_code == 200 and gorulen == {"ad": "pilot", "baslik": None, "notlar": None, "santral_limit": 5, "api_rpm_limit": None}
    assert any(a[1] == "plan_guncelle" for a, k in _ortam)


def test_temsil_jetonu_salt_okunur(monkeypatch, _ortam):
    import time as _t
    monkeypatch.setattr(ps, "oturum_durumu", lambda p: {"sv": 0, "aktif": True, "rol": "sahip", "email": "s@pvq", "totp_aktif": True})
    monkeypatch.setattr(ps, "kiraci_durumu", lambda t: "active")
    from pvquant.services import plant_service
    monkeypatch.setattr(plant_service, "listele", lambda t: [])
    c = TestClient(api_main.app)
    # uç: yalnız sahip; gerçek jeton üretimi (DB'siz: tenant araması monkeypatch)
    monkeypatch.setattr(ps, "temsil_jetonu", lambda a, t: {"token": _jwt.encode({"sub": a, "tenant_id": t, "role": "viewer", "sv": 0, "temsil": a,
                        "exp": dt.datetime.utcnow() + dt.timedelta(minutes=15)}, au._sir(), algorithm="HS256"), "tenant_id": t, "kiraci": "F", "sure_dk": 15, "bitis": "x"})
    y = c.post(f"/v1/yonetim/kiracilar/{T1}/temsil", headers=_jeton())
    assert y.status_code == 200 and y.json()["sure_dk"] == 15
    kayit = [k for a, k in _ortam if a[1] == "kiraci_temsil"][0]
    assert kayit["tenant_id"] == T1 and "token" not in str(kayit)                       # jeton denetim izine yazılmaz
    tj = {"Authorization": "Bearer " + y.json()["token"]}
    assert c.get("/v1/plants", headers=tj).status_code == 200                              # GET açık (viewer)
    assert c.post("/v1/oturum/yenile", headers=tj).status_code == 403                      # POST kapalı
    assert c.get("/v1/api-anahtarlari", headers=tj).status_code == 403                     # yönetici ucu: rol viewer → 403
    assert c.get("/v1/plants/p1/report?fmt=html", headers=tj).status_code == 403             # 26.10 denetim-2: GET ama yazan (rapor) → 403
    assert c.get("/v1/plants/p1/scada/disa", headers=tj).status_code == 403                 # 26.10 denetim-3: ham dışa aktarım görüntüleme değil
    assert c.get("/v1/yonetim/ben", headers=tj).status_code == 403                         # platform ucu: kapsam yok
    monkeypatch.setattr(ps, "oturum_durumu", lambda p: {"sv": 0, "aktif": True, "rol": "operator", "email": "o@pvq", "totp_aktif": True})
    assert c.post(f"/v1/yonetim/kiracilar/{T1}/temsil", headers=_jeton(rol="operator")).status_code == 403   # operatör açamaz
    monkeypatch.setattr(ps, "kiraci_durumu", lambda t: "suspended")
    assert c.get("/v1/plants", headers=tj).status_code == 403                               # kiracı askıya alınınca görüntüleme de düşer


# ---------------- 26.10 Faz 6: kuruluş uçları + yönetici 2FA politikası kapısı ----------------
def test_kurulus_uclari_ve_2fa_politikasi(monkeypatch, _ortam):
    from pvquant.services import kurulus_service as kr, plant_service
    durum = {"sv": 0, "aktif": True, "kiraci_durum": "active", "iki_adim_kurulmali": False}
    monkeypatch.setattr(au, "oturum_durumu", lambda u: dict(durum))
    monkeypatch.setattr(plant_service, "listele", lambda t: [])
    gorulen = {}
    monkeypatch.setattr(dz, "listele", lambda **k: gorulen.update(k) or [])
    monkeypatch.setattr(kr, "ayarlar", lambda t: {"yonetici_2fa_zorunlu": False, "iki_adimsiz_yonetici": 1})
    monkeypatch.setattr(kr, "ayar_guncelle", lambda t, **k: {"yonetici_2fa_zorunlu": k["yonetici_2fa_zorunlu"], "iki_adimsiz_yonetici": 1})
    c = TestClient(api_main.app)
    assert c.get("/v1/kurulus/denetim?once_id=5", headers=_musteri_jeton()).status_code == 200
    assert gorulen["tenant_id"] == T1 and gorulen["once_id"] == 5                      # kiracı jetondan, sorgudan değil
    assert c.get("/v1/kurulus/ayarlar", headers=_musteri_jeton()).json()["yonetici_2fa_zorunlu"] is False
    y = c.put("/v1/kurulus/ayarlar", json={"yonetici_2fa_zorunlu": True}, headers=_musteri_jeton())
    assert y.status_code == 200 and y.json()["yonetici_2fa_zorunlu"] is True
    assert any(a[0] == "musteri" and a[1] == "kurulus_ayar" and k["tenant_id"] == T1 for a, k in _ortam)
    editor = {"Authorization": "Bearer " + _jwt.encode({"sub": "u2", "tenant_id": T1, "role": "editor", "sv": 0,
                                                         "exp": dt.datetime.utcnow() + dt.timedelta(hours=1)}, au._sir(), algorithm="HS256")}
    assert c.get("/v1/kurulus/ayarlar", headers=editor).status_code == 403                 # yalnız yönetici
    # politika açık + yönetici 2FA'sız → yalnız kurulum uçları
    durum["iki_adim_kurulmali"] = True
    monkeypatch.setattr(au, "oturum_yenile", lambda u: {"token": "t", "role": "admin", "firma": "F", "email": "a@b", "iki_adim_kurulmali": True})
    assert c.post("/v1/oturum/yenile", headers=_musteri_jeton()).json()["iki_adim_kurulmali"] is True
    from pvquant.services import iki_adim_service
    monkeypatch.setattr(iki_adim_service, "durum", lambda u: {"aktif": False})
    assert c.get("/v1/iki-adim", headers=_musteri_jeton()).status_code == 200                # kurulum ucu açık
    y = c.get("/v1/plants", headers=_musteri_jeton())
    assert y.status_code == 403 and "iki adımlı" in y.json()["detail"]                      # veri ucu kapalı
    durum["iki_adim_kurulmali"] = False
    assert c.get("/v1/plants", headers=_musteri_jeton()).status_code == 200


# ---------------- 26.10 denetim-2 (3 aşamalı denetim, 1. aşama) ----------------
def test_kurulus_denetim_personel_kimligi_maskelenir(monkeypatch):
    durum = {"sv": 0, "aktif": True, "kiraci_durum": "active", "iki_adim_kurulmali": False}
    monkeypatch.setattr(au, "oturum_durumu", lambda u: dict(durum))
    monkeypatch.setattr(dz, "listele", lambda **k: [
        {"id": 2, "zaman": "z", "kapsam": "platform", "aktor_id": "p1", "aktor_eposta": "personel@pvquant.com", "tenant_id": T1, "eylem": "kiraci_guncelle",
         "nesne_tur": "tenant", "nesne_id": T1, "ayrinti": {"eski": {"status": "active"}, "yeni": {"status": "suspended"}, "notlar_degisti": True}, "ip": "1.2.3.4"},
        {"id": 1, "zaman": "z", "kapsam": "musteri", "aktor_id": "u1", "aktor_eposta": "a@b.c", "tenant_id": T1, "eylem": "giris", "nesne_tur": None, "nesne_id": None, "ayrinti": {}, "ip": "5.6.7.8"}])
    c = TestClient(api_main.app)
    k = c.get("/v1/kurulus/denetim", headers=_musteri_jeton()).json()["kayitlar"]
    assert k[0]["aktor_eposta"] is None and k[0]["ip"] is None and k[0]["aktor_id"] is None        # personel kimliği müşteriye gitmez
    assert k[0]["ayrinti"] == {"eski": {"status": "active"}, "yeni": {"status": "suspended"}}       # not işareti bile gitmez, durum değişimi kalır
    assert k[1]["aktor_eposta"] == "a@b.c" and k[1]["ip"] == "5.6.7.8"                              # ekibin kendi satırı aynen


def test_bilinmeyen_plan_422(monkeypatch, _ortam):
    monkeypatch.setattr(ps, "oturum_durumu", lambda p: {"sv": 0, "aktif": True, "rol": "sahip", "email": "s@pvq", "totp_aktif": True})
    monkeypatch.setattr(ps, "_plan_dogrula", lambda plan: (_ for _ in ()).throw(ps.PlatformHata(f"plan yok: {plan}")) if plan != "pilot" else None)
    monkeypatch.setattr(ps, "kiraci_olustur", ps.kiraci_olustur)   # gerçek fonksiyon: doğrulama DB'den önce koşar
    c = TestClient(api_main.app)
    y = c.post("/v1/yonetim/kiracilar", json={"firma": "Firma", "yonetici_eposta": "a@b.c", "plan": "yok"}, headers=_jeton())
    assert y.status_code == 422 and "plan yok" in y.json()["detail"]


# ---------------- 26.10 denetim-3 (bağımsız denetim bulguları) ----------------
P1 = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
P2 = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
U1 = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"


def _sahip(monkeypatch):
    monkeypatch.setattr(ps, "oturum_durumu", lambda p: {"sv": 0, "aktif": True, "rol": "sahip", "email": "s@pvq", "totp_aktif": True})


def test_d3_kendi_iki_adimini_sifirlayamaz(monkeypatch, _ortam):
    _sahip(monkeypatch)
    gorulen = {}
    monkeypatch.setattr(ps, "operator_guncelle", lambda pid, **k: gorulen.update({"pid": pid, **k}) or True)
    c = TestClient(api_main.app)
    assert c.put(f"/v1/yonetim/operatorler/{P1}", json={"iki_adim_sifirla": True}, headers=_jeton(sub=P1)).status_code == 403   # kendi → 403
    assert gorulen == {}                                                                                                  # servise inmez
    assert c.put(f"/v1/yonetim/operatorler/{P1}", json={"aktif": False}, headers=_jeton(sub=P1)).status_code == 200       # başka alan serbest
    monkeypatch.setattr(ps, "yeniden_dogrula", lambda pid, sifre, kod: sifre == "p" and kod == "1")
    assert c.put(f"/v1/yonetim/operatorler/{P2}", json={"iki_adim_sifirla": True, "sifre": "p", "kod": "1"}, headers=_jeton(sub=P1)).status_code == 200   # başkası → yeniden doğrulamayla
    assert gorulen["pid"] == P2 and gorulen["iki_adim_sifirla"] is True


def test_d3_parola_baglantisi_yalniz_sahibe(monkeypatch, _ortam):
    """Posta gitmezse bağlantı yalnız sahibe; operatöre yalnız not. Denetim satırı tenant_id ve baglanti_gosterildi taşır."""
    _sahip(monkeypatch)
    monkeypatch.setattr(ps, "kullanici_getir", lambda a, uid: {"id": uid, "email": "a@b.c", "tenant_id": T1, "rol": "admin", "aktif": True, "firma": "F"})
    monkeypatch.setattr(ps, "_davet_baglantisi", lambda s, uid, saat: "https://x/parola-yenile?jeton=GIZLI")
    monkeypatch.setattr(ps, "_davet_postala", lambda *a, **k: False)
    class _S:
        def __enter__(self): return None
        def __exit__(self, *a): return False
    monkeypatch.setattr(ps, "platform_baglami", lambda a: _S())
    c = TestClient(api_main.app)
    y = c.post(f"/v1/yonetim/kullanicilar/{U1}/parola-sifirlama", headers=_jeton())
    assert y.status_code == 200 and y.json()["gonderildi"] is False and "GIZLI" in y.json()["baglanti"]          # sahip görür
    k = [k for a, k in _ortam if a[1] == "parola_sifirlama_gonder"][-1]
    assert k["tenant_id"] == T1 and k["ayrinti"] == {"gonderildi": False, "baglanti_gosterildi": True} and "GIZLI" not in str(k)
    monkeypatch.setattr(ps, "oturum_durumu", lambda p: {"sv": 0, "aktif": True, "rol": "operator", "email": "o@pvq", "totp_aktif": True})
    y = c.post(f"/v1/yonetim/kullanicilar/{U1}/parola-sifirlama", headers=_jeton(rol="operator"))
    assert y.status_code == 200 and "baglanti" not in y.json() and "sahip" in y.json()["not"]                     # operatör görmez
    k = [k for a, k in _ortam if a[1] == "parola_sifirlama_gonder"][-1]
    assert k["ayrinti"]["baglanti_gosterildi"] is False
    # kiracı oluşturma aynı kural (gerçek servis yardımcı fonksiyonu)
    assert "davet_baglantisi" in ps._baglanti_yaniti(False, "L", "sahip", "davet_baglantisi")
    assert ps._baglanti_yaniti(False, "L", "operator", "davet_baglantisi").keys() == {"not"}
    assert ps._baglanti_yaniti(True, "L", "operator", "davet_baglantisi") == {}


def test_d3_giris_paylasimli_pencere_429(monkeypatch, _ortam):
    """slowapi süreç başına sayar; hiz_pencere tabanlı sayaç işçiler arası 5/dk/IP — 6. istek 429, DB yoksa (0) kapı açık."""
    from pvquant.services import kullanim_service as ks
    sayim = iter([1, 2, 3, 4, 5, 6, 0])
    anahtarlar = []
    monkeypatch.setattr(ks, "pencere_say", lambda a, saniye=60, simdi=None: anahtarlar.append(a) or next(sayim))
    monkeypatch.setattr(ps, "giris", lambda e, s, k=None: None)
    monkeypatch.setattr(au, "giris", lambda e, s, k=None: None)
    api_main.limiter.enabled = False           # süreç içi katmanı kapat: yalnız paylaşımlı pencere ölçülür
    try:
        c = TestClient(api_main.app)
        kodlar = [c.post("/v1/yonetim/giris", json={"email": "x@y", "sifre": "z"}).status_code for _ in range(6)]
        assert kodlar == [401, 401, 401, 401, 401, 429]
        assert c.post("/v1/auth/login", json={"email": "x@y", "sifre": "z"}).status_code == 401    # pencere_say 0 → kapı açık
        assert anahtarlar[0].startswith("ygiris:") and anahtarlar[-1].startswith("giris:")
    finally:
        api_main.limiter.enabled = True


def test_d3_bicimsiz_uuid_422(monkeypatch, _ortam):
    """Biçimsiz kimlik DB'de CAST hatasına (500) dönüyordu → uçta 422; servis hiç çağrılmaz."""
    _sahip(monkeypatch)
    for ad in ("kiraci_detay", "kullanici_getir", "operator_guncelle", "temsil_jetonu"):
        monkeypatch.setattr(ps, ad, lambda *a, **k: pytest.fail(f"{ad} çağrıldı"))
    from pvquant.services import sistem_service as ss, kullanim_service as ks
    monkeypatch.setattr(ss, "isler", lambda *a, **k: pytest.fail("isler çağrıldı"))
    monkeypatch.setattr(ks, "gunler", lambda *a, **k: pytest.fail("gunler çağrıldı"))
    monkeypatch.setattr(dz, "listele", lambda **k: pytest.fail("listele çağrıldı"))
    monkeypatch.setattr(dz, "goruntule_kaydet", lambda *a, **k: pytest.fail("goruntule çağrıldı"))
    c = TestClient(api_main.app); h = _jeton()
    assert c.get("/v1/yonetim/kiracilar/abc", headers=h).status_code == 422
    assert c.put("/v1/yonetim/kiracilar/abc", json={"durum": "active"}, headers=h).status_code == 422
    assert c.put("/v1/yonetim/kullanicilar/abc", json={"aktif": True}, headers=h).status_code == 422
    assert c.post("/v1/yonetim/kullanicilar/abc/parola-sifirlama", headers=h).status_code == 422
    assert c.post("/v1/yonetim/kullanicilar/abc/iki-adim-sifirla", headers=h).status_code == 422
    assert c.put("/v1/yonetim/operatorler/abc", json={"aktif": True}, headers=h).status_code == 422
    assert c.post("/v1/yonetim/kiracilar/abc/temsil", headers=h).status_code == 422
    assert c.get("/v1/yonetim/isler?tenant_id=abc", headers=h).status_code == 422
    assert c.get("/v1/yonetim/isler?plant_id=zzz", headers=h).status_code == 422
    assert c.get("/v1/yonetim/denetim?tenant_id=abc", headers=h).status_code == 422
    assert c.get("/v1/yonetim/kullanim?tenant_id=abc", headers=h).status_code == 422
    # büyük harf/küme ayracı gibi geçerli varyantlar kanonik biçime iner
    monkeypatch.setattr(ss, "isler", lambda a, **k: {"isler": [], "tenant_id": k["tenant_id"]})
    assert c.get(f"/v1/yonetim/isler?tenant_id={{{T1.upper()}}}", headers=h).json()["tenant_id"] == T1


def test_d3_plan_sinirlari_ve_baslik():
    """plan_guncelle: INTEGER taşması ve boş başlık DB'ye inmeden 422 (PlatformHata)."""
    with pytest.raises(ValueError, match="en çok"):
        ps.plan_guncelle("pilot", santral_limit=10 ** 12)
    with pytest.raises(ValueError, match="başlık"):
        ps.plan_guncelle("pilot", baslik="   ")
    with pytest.raises(ValueError, match="negatif"):
        ps.plan_guncelle("pilot", kullanici_limit=-1)


def test_d3_hassas_islemler_yeniden_dogrulama(monkeypatch, _ortam):
    """Bağımsız kontrol 1.1: çalınmış sahip jetonu ikinci sahip açıp kurbanın 2FA'sını sıfırlayamasın — sahip hesabı açma / sahip yapma /
    başkasının 2FA'sını sıfırlama aktörün parolası + kodunu ister; parola/kod denetim izine yazılmaz."""
    _sahip(monkeypatch)
    gorulen = []
    monkeypatch.setattr(ps, "operator_guncelle", lambda pid, **k: gorulen.append(("g", pid, k)) or True)
    monkeypatch.setattr(ps, "operator_ekle", lambda e, r: gorulen.append(("e", e, r)) or {"id": P2, "email": e, "rol": r, "gecici_parola": "GECICI"})
    dogru = {"sifre": "parola-1", "kod": "123456"}
    monkeypatch.setattr(ps, "yeniden_dogrula", lambda pid, sifre, kod: pid == P1 and sifre == dogru["sifre"] and kod == dogru["kod"])
    c = TestClient(api_main.app); h = _jeton(sub=P1)
    # jeton tek başına yetmez
    assert c.post("/v1/yonetim/operatorler", json={"email": "y@pvq", "rol": "sahip"}, headers=h).status_code == 403
    assert c.put(f"/v1/yonetim/operatorler/{P2}", json={"iki_adim_sifirla": True}, headers=h).status_code == 403
    assert c.put(f"/v1/yonetim/operatorler/{P2}", json={"rol": "sahip"}, headers=h).status_code == 403
    assert c.put(f"/v1/yonetim/operatorler/{P2}", json={"rol": "sahip", "sifre": "yanlis", "kod": "000000"}, headers=h).status_code == 403
    assert gorulen == []
    # hassas olmayanlar doğrulamasız
    assert c.post("/v1/yonetim/operatorler", json={"email": "y@pvq", "rol": "operator"}, headers=h).status_code == 201
    assert c.put(f"/v1/yonetim/operatorler/{P2}", json={"aktif": False}, headers=h).status_code == 200
    assert c.put(f"/v1/yonetim/operatorler/{P2}", json={"rol": "operator"}, headers=h).status_code == 200
    # doğru parola + kod ile geçer; iz parola/kod taşımaz
    assert c.post("/v1/yonetim/operatorler", json={"email": "s2@pvq", "rol": "sahip", **dogru}, headers=h).status_code == 201
    assert c.put(f"/v1/yonetim/operatorler/{P2}", json={"iki_adim_sifirla": True, **dogru}, headers=h).status_code == 200
    assert gorulen[-1] == ("g", P2, {"rol": None, "aktif": None, "iki_adim_sifirla": True})
    izler = [k for a, k in _ortam if a[1] in ("operator_guncelle", "operator_ekle")]
    assert izler and all("parola-1" not in str(k) and "123456" not in str(k) and "sifre" not in str(k["ayrinti"]) for k in izler)


def test_d3_basvuru_kimligi_422(monkeypatch, _ortam):
    _sahip(monkeypatch)
    monkeypatch.setattr(basvuru_service, "okundu_isaretle", lambda b: pytest.fail("servis çağrıldı"))
    assert TestClient(api_main.app).post("/v1/yonetim/basvurular/abc/okundu", headers=_jeton()).status_code == 422
