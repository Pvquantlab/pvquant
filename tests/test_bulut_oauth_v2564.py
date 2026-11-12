"""v2.564 — sahip onayı (OAuth) yolu, SAF (DB'siz): başlatma kapıları ve adresler, tek kullanımlık state, belirteç değişimi (sahte sunucu), kasaya yazım
(düz metin yok), çok santralda ertelenmiş seçim, SolarEdge OAuth bağlayıcısı (Bearer, 401 → yenileme), yönlendirme adresi, çekiş turu seçim bekçisi."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from pvquant.guvenlik import kasa
from pvquant.io.bulut import SAGLAYICILAR, BulutHata
from pvquant.io.bulut.solaredge_oauth import SolarEdgeOAuth
from pvquant.io.bulut.sungrow import Sungrow
from pvquant.services import bulut_cekis_service as bc
from pvquant.services import bulut_oauth_service as bo

T = datetime(2026, 11, 10, 9, 0, tzinfo=timezone.utc)
PLANT = {"id": "11111111-1111-1111-1111-111111111111"}
ONAY2 = {"yalniz_okuma": True, "sifreli_saklama": True}
SUNGROW_ENV = {"PVQ_SUNGROW_APPKEY": "APPKEY-1", "PVQ_SUNGROW_ACCESS_KEY": "Gizli-Access-Key-9", "PVQ_SUNGROW_APP_ID": "app42"}
SE_ENV = {"PVQ_SOLAREDGE_CLIENT_ID": "cid-1", "PVQ_SOLAREDGE_CLIENT_SECRET": "Cok-Gizli-Secret"}


def _env(monkeypatch, *gruplar, kek=True):
    for e in ("PVQ_SUNGROW_APPKEY", "PVQ_SUNGROW_ACCESS_KEY", "PVQ_SUNGROW_APP_ID", "PVQ_SOLAREDGE_CLIENT_ID", "PVQ_SOLAREDGE_CLIENT_SECRET", "PVQ_OAUTH_GERI_DONUS_KOK", "PVQ_KEK_ID"):
        monkeypatch.delenv(e, raising=False)
    for g in gruplar:
        for k, v in g.items():
            monkeypatch.setenv(k, v)
    if kek:
        monkeypatch.setenv("PVQ_KEK", kasa.anahtar_uret())
    else:
        monkeypatch.delenv("PVQ_KEK", raising=False)


def test_sicil_ve_uygulama_ozeti(monkeypatch):
    _env(monkeypatch)
    assert SAGLAYICILAR["sungrow"]["oauth"] and SAGLAYICILAR["solaredge_oauth"]["oauth"] and not SAGLAYICILAR["fusionsolar"]["oauth"] and not SAGLAYICILAR["solaredge"]["oauth"]
    oz = bo.uygulamalar_ozeti()
    assert set(oz) == {"sungrow", "solaredge_oauth"} and not oz["sungrow"]["yapilandirildi"] and "PVQ_SUNGROW_APPKEY" in oz["sungrow"]["eksik"]
    assert oz["sungrow"]["geri_donus"] == "https://pvquant.com/v1/bulut/oauth/sungrow/geri-donus"
    assert "gizli" not in json.dumps(oz) and "Gizli" not in json.dumps(oz)
    monkeypatch.setenv("PVQ_OAUTH_GERI_DONUS_KOK", "http://127.0.0.1:8000/")
    assert bo.geri_donus_adresi("solaredge_oauth") == "http://127.0.0.1:8000/v1/bulut/oauth/solaredge_oauth/geri-donus"


def test_baslat_kapilari_ve_adresler(monkeypatch):
    _env(monkeypatch)
    yazilan: list = []
    yaz = yazilan.append
    assert bo.baslat("t", PLANT, "fusionsolar", "intl", ONAY2, "u", T, yaz)["durum"] == "oauth_yok"
    r = bo.baslat("t", PLANT, "sungrow", "eu", {"yalniz_okuma": True}, "u", T, yaz)
    assert r["durum"] == "onay_yok" and "şifreli saklanmasını" in r["aciklama"]
    r = bo.baslat("t", PLANT, "sungrow", "eu", ONAY2, "u", T, yaz)
    assert r["durum"] == "uygulama_yok" and "PVQ_SUNGROW_APP_ID" in r["eksik"]
    _env(monkeypatch, SUNGROW_ENV, kek=False)
    assert bo.baslat("t", PLANT, "sungrow", "eu", ONAY2, "u", T, yaz)["durum"] == "kasa_kapali"
    _env(monkeypatch, SUNGROW_ENV, SE_ENV)
    assert bo.baslat("t", PLANT, "sungrow", "mars", ONAY2, "u", T, yaz)["durum"] == "ayar_hatasi"
    assert yazilan == []
    r = bo.baslat("t", PLANT, "sungrow", "eu", ONAY2, "u7", T, yaz)
    assert r["durum"] == "yonlendir" and r["bitis"] == (T + timedelta(minutes=15)).isoformat(timespec="seconds")
    url = r["yetki_url"]
    assert url.startswith("https://web3.isolarcloud.eu/?state=") and "#/authorized-app?cloudId=3&applicationId=app42&redirectUrl=https%3A%2F%2Fpvquant.com%2Fv1%2Fbulut%2Foauth%2Fsungrow%2Fgeri-donus" in url
    assert url.index("state=") < url.index("#")   # SPA nedeniyle state # öncesinde
    satir = yazilan[-1]
    state = url.split("state=")[1].split("#")[0]
    assert len(satir["state_hash"]) == 64 and state not in json.dumps(satir, default=str) and satir["aktor_id"] == "u7" and satir["onay_json"]["onaylar"] == ONAY2
    assert "Gizli-Access-Key-9" not in json.dumps(r) and "Gizli-Access-Key-9" not in json.dumps(satir, default=str)
    r = bo.baslat("t", PLANT, "solaredge_oauth", None, ONAY2, "u", T, yaz)
    assert r["durum"] == "yonlendir" and r["yetki_url"].startswith("https://connect.solaredge.com/authorize?client_id=cid-1&external_id=") and "Cok-Gizli-Secret" not in r["yetki_url"]


def _satir(saglayici="sungrow", bolge="eu"):
    return {"id": "s1", "tenant_id": "t1", "plant_id": PLANT["id"], "saglayici": saglayici, "bolge": bolge, "onay_json": {"onaylar": ONAY2}, "aktor_id": "u7"}


def test_geri_donus_state_ve_hata_yollari(monkeypatch):
    _env(monkeypatch, SUNGROW_ENV)
    sonuclar: list = []
    son = lambda sid, t, so: sonuclar.append(so)   # noqa: E731
    assert bo.geri_donus("sungrow", {"code": "c"}, T)["durum"] == "durum_yok"
    kullanim = {"n": 0}

    def bul(h, simdi, *_):   # ilk arama bulur, ikincisi (yeniden oynatma) bulamaz
        kullanim["n"] += 1
        return _satir() if kullanim["n"] == 1 else None
    r0 = bo.geri_donus("sungrow", {"state": "abc", "error": "user_cancelled"}, T, bul=lambda h, s, *_: _satir(), sonuclandir=son)
    assert r0["durum"] == "sahip_reddetti" and r0["aciklama"] == bo.DURUM_ETIKET["sahip_reddetti"]   # 10.11 inceleme: cancel de red; açıklama durumla aynı
    r = bo.geri_donus("sungrow", {"state": "abc", "error": "access_denied"}, T, bul=bul, sonuclandir=son)
    assert r["durum"] == "sahip_reddetti" and r["plant_id"] == PLANT["id"] and sonuclar[-1]["durum"] == "sahip_reddetti"
    r = bo.geri_donus("sungrow", {"state": "abc", "code": "c"}, T, bul=bul, sonuclandir=son)
    assert r["durum"] == "durum_gecersiz" and "plant_id" not in r
    assert bo.geri_donus("solaredge_oauth", {"external_id": "x", "code": "c"}, T, bul=lambda h, s, *_: _satir("sungrow"), sonuclandir=son)["durum"] == "durum_gecersiz"   # sağlayıcı uyuşmazlığı
    assert bo.geri_donus("sungrow", {"state": "x"}, T, bul=lambda h, s, *_: _satir(), sonuclandir=son)["durum"] == "kod_yok"
    _env(monkeypatch)
    assert bo.geri_donus("sungrow", {"state": "x", "code": "c"}, T, bul=lambda h, s, *_: _satir(), sonuclandir=son)["durum"] == "uygulama_yok"
    _env(monkeypatch, SUNGROW_ENV)
    r = bo.geri_donus("sungrow", {"state": "x", "code": "c"}, T, bul=lambda h, s, *_: _satir(), sonuclandir=son,
                      token_degis=lambda *a, **k: (_ for _ in ()).throw(BulutHata("belirteç alınamadı (yetkilendirme kodu geçersiz ya da kullanılmış, 2)")))
    assert r["durum"] == "belirtec_hatasi" and "kullanılmış" in r["aciklama"]


def _sungrow_transport(istekler: list):
    def h(req: httpx.Request):
        istekler.append(req)
        if req.url.path == "/openapi/apiManage/token":
            g = json.loads(req.content)
            assert g["grant_type"] == "authorization_code" and g["appkey"] == "APPKEY-1" and g["redirect_uri"].endswith("/v1/bulut/oauth/sungrow/geri-donus") and req.headers["x-access-key"] == "Gizli-Access-Key-9"
            if g["code"] == "kotu":
                return httpx.Response(200, json={"result_code": "2", "result_msg": "invalid code"})
            return httpx.Response(200, json={"result_code": "1", "result_data": {"access_token": "AT-Gizli-1", "refresh_token": "RT-Gizli-1", "expires_in": 172799, "auth_ps_list": ["5001"], "token_type": "bearer"}})
        return httpx.Response(404)
    return httpx.MockTransport(h)


def test_geri_donus_sungrow_belirtec_kasaya_duz_metinsiz(monkeypatch):
    _env(monkeypatch, SUNGROW_ENV)
    istekler: list = []; yazilan: list = []; sonuclar: list = []
    tr = _sungrow_transport(istekler)
    with pytest.raises(BulutHata):
        Sungrow.token_degis("eu", {"appkey": "APPKEY-1", "access_key": "Gizli-Access-Key-9"}, "kotu", bo.geri_donus_adresi("sungrow"), transport=tr)
    sina = lambda kod, kimlik, onay, bolge: {"durum": "ok", "zaman": "z", "ozet": {"santraller": [{"kimlik": "5001", "ad": "Bor GES", "kapasite_kwp": 990.0}]}}   # noqa: E731
    r = bo.geri_donus("sungrow", {"state": "x", "code": "iyi"}, T, bul=lambda h, s, *_: _satir(), sina=sina, yaz_kimlik=lambda t, p, s: yazilan.append((t, p, s)),
                      sonuclandir=lambda sid, t, so: sonuclar.append(so),
                      token_degis=lambda bolge, uyg, code, rd: Sungrow.token_degis(bolge, uyg, code, rd, transport=tr))
    assert r["durum"] == "tamam" and r["dis_kimlik"] == "5001" and r["dis_ad"] == "Bor GES" and r["etiket_hesap"] == "APP…-1" and r["plant_id"] == PLANT["id"]
    t, p, satir = yazilan[0]
    assert (t, p) == ("t1", PLANT["id"]) and satir["saglayici"] == "sungrow" and satir["bolge"] == "eu" and satir["dis_kimlik"] == "5001"
    for gizli in ("AT-Gizli-1", "RT-Gizli-1", "Gizli-Access-Key-9"):
        assert gizli not in json.dumps(r, default=str) and gizli not in json.dumps(sonuclar, default=str)
        assert gizli not in json.dumps({k: v for k, v in satir.items() if k not in ("sifreli", "dek_sarili")}, default=str) and gizli.encode() not in satir["sifreli"]
    assert kasa.coz_json(satir, "t1:" + PLANT["id"] + ":sungrow") == {"appkey": "APPKEY-1", "access_key": "Gizli-Access-Key-9", "access_token": "AT-Gizli-1", "refresh_token": "RT-Gizli-1"}
    assert len(istekler) == 2 and all(i.url.host == "gateway.isolarcloud.eu" for i in istekler)


def test_geri_donus_cok_santral_secim_ertelenir(monkeypatch):
    _env(monkeypatch, SUNGROW_ENV)
    yazilan: list = []
    sina = lambda kod, kimlik, onay, bolge: {"durum": "ok", "zaman": "z", "ozet": {"santraller": [{"kimlik": "1", "ad": "A", "kapasite_kwp": 1.0}, {"kimlik": "2", "ad": "B", "kapasite_kwp": 2.0}]}}   # noqa: E731
    r = bo.geri_donus("sungrow", {"state": "x", "code": "c"}, T, bul=lambda h, s, *_: _satir(), sina=sina, yaz_kimlik=lambda t, p, s: yazilan.append(s), sonuclandir=lambda *a: None,
                      token_degis=lambda *a, **k: {"appkey": "APPKEY-1", "access_key": "k", "access_token": "a", "refresh_token": "r", "auth_ps_list": ["1", "2"]})
    assert r["durum"] == "secim_bekliyor" and [x["kimlik"] for x in r["santraller"]] == ["1", "2"] and yazilan[0]["dis_kimlik"] is None
    # çekiş turu: santral seçilmemiş kayıt sağlayıcıya çağrı yapmaz
    gunc: list = []
    kayit = {"tenant_id": "t1", "plant_id": PLANT["id"], "saglayici": "sungrow", "bolge": "eu", "dis_kimlik": None, "santral_adi": "P", "cekis_acik": True}
    oz = bc.tur(T, kayitlar=[kayit], coz=lambda k: {"x": 1}, guncelle=lambda k, d, h, *a: gunc.append(d), istemci_fabrikasi=lambda *a, **k: (_ for _ in ()).throw(AssertionError("çağrı olmamalı")))
    assert gunc == ["santral_secilmedi"] and "santral seçilmedi" in oz


def test_solaredge_oauth_baglayici_bearer_ve_yenileme(monkeypatch):
    _env(monkeypatch, SE_ENV)
    kayit: dict = {"n401": 0, "token": 0}; yenilenen: list = []

    def h(req: httpx.Request):
        if req.url.host == "monitoringapi.solaredge.com" and req.url.path == "/v2/oauth2/token":
            g = json.loads(req.content)
            assert g["client_id"] == "cid-1" and g["client_secret"] == "Cok-Gizli-Secret"
            if g.get("code") == "kotu":
                return httpx.Response(400, json={"error": "invalid_request", "error_description": "Invalid code"})
            kayit["token"] += 1
            return httpx.Response(200, json={"access_token": "AT-" + str(kayit["token"]), "token_type": "Bearer", "expires_in": 7200, "refresh_token": "RT-" + str(kayit["token"])})
        if req.url.path == "/v2/sites/2951500":
            if req.headers.get("Authorization") == "Bearer AT-eski":
                kayit["n401"] += 1; return httpx.Response(401, json={"error": "token_expired"})
            assert req.headers.get("Authorization", "").startswith("Bearer AT-") and "X-API-Key" not in req.headers
            return httpx.Response(200, json={"site": {"siteId": 2951500, "name": "Çatı GES", "peakPower": 480.5, "location": {"timezone": "Europe/Istanbul"}, "activationStatus": "ACTIVE"}})
        return httpx.Response(404)
    tr = httpx.MockTransport(h)
    with pytest.raises(BulutHata, match="kullanılmış"):
        SolarEdgeOAuth.token_degis(None, {"client_id": "cid-1", "client_secret": "Cok-Gizli-Secret"}, "kotu", "r", transport=tr, site_id="2951500")
    with pytest.raises(BulutHata, match="site_id"):
        SolarEdgeOAuth.token_degis(None, {"client_id": "cid-1", "client_secret": "Cok-Gizli-Secret"}, "iyi", "r", transport=tr)
    k = SolarEdgeOAuth.token_degis(None, {"client_id": "cid-1", "client_secret": "Cok-Gizli-Secret"}, "iyi", "r", transport=tr, site_id="2951500")
    assert k["access_token"] == "AT-1" and k["refresh_token"] == "RT-1" and k["site_id"] == "2951500"
    c = SolarEdgeOAuth(transport=tr); c.kimlik_yenile = yenilenen.append
    from pvquant.services.bulut_oauth_service import uygulama as _uyg
    c.uygulama_getir = _uyg   # v2.603 (F4-I): io katmanı servisi içe aktarmaz; çağıran enjekte eder (bulut_cekis_service böyle kurar)
    c.giris({"access_token": "AT-eski", "refresh_token": "RT-eski", "site_id": "2951500"})
    st = c.santraller()
    assert st == [{"kimlik": "2951500", "ad": "Çatı GES", "kapasite_kwp": 480.5, "saat_dilimi": "Europe/Istanbul", "uc": "sites/{id}", "durum": "ACTIVE"}]
    assert kayit["n401"] == 1 and yenilenen and yenilenen[0]["access_token"] == "AT-2" and yenilenen[0]["refresh_token"] == "RT-2" and yenilenen[0]["site_id"] == "2951500"
    c.kapat()
    # geri dönüş: external_id state taşır, site_id kayda iner, etiket site kimliğinden (belirteç maskelenmez)
    yazilan: list = []
    r = bo.geri_donus("solaredge_oauth", {"external_id": "st", "code": "iyi", "site_id": "2951500"}, T, bul=lambda h_, s, *_: _satir("solaredge_oauth", None),
                      sina=lambda kod, kimlik, onay, bolge: {"durum": "ok", "zaman": "z", "ozet": {"santraller": [{"kimlik": kimlik["site_id"], "ad": "Çatı GES", "kapasite_kwp": 480.5}]}},
                      yaz_kimlik=lambda t, p, s: yazilan.append(s), sonuclandir=lambda *a: None,
                      token_degis=lambda bolge, uyg, code, rd, **ek: SolarEdgeOAuth.token_degis(bolge, uyg, code, rd, transport=tr, **ek))
    assert r["durum"] == "tamam" and r["dis_kimlik"] == "2951500" and r["etiket_hesap"] == "295…00" and "AT-" not in json.dumps(r)


def test_yonlendirme_adresi(monkeypatch):
    _env(monkeypatch)
    assert bo.yonlendirme(PLANT["id"], "sungrow", "tamam") == f"https://pvquant.com/?bulut_oauth=sungrow:tamam#santralim/{PLANT['id']}"
    assert bo.yonlendirme(None, "solaredge_oauth", "durum_gecersiz") == "https://pvquant.com/?bulut_oauth=solaredge_oauth:durum_gecersiz#santralim"
    assert bo.yonlendirme("x/../y", "s<g", 'tamam"><script>') == "https://pvquant.com/?bulut_oauth=sg:tamamscript#santralim"
    monkeypatch.setenv("PVQ_OAUTH_GERI_DONUS_KOK", "http://localhost:4273")
    assert bo.yonlendirme("p1", "sungrow", "hata").startswith("http://localhost:4273/?bulut_oauth=sungrow:hata#santralim/p1")


def test_api_baslat_ve_geri_donus_yonlendirmesi(monkeypatch):
    """API: başlatma ucu kapılar + yetki adresi; geri dönüş ucu kimliksiz, yalnız durum koduyla 303; kod/belirteç yanıtta ve izde yok."""
    import apps.api.main as api_main
    from fastapi.testclient import TestClient
    from apps.api.deps import gecerli_kullanici
    from pvquant.services import plant_service
    _env(monkeypatch, SUNGROW_ENV)
    durum = {"pj": {"veri_yolu": {"tur": "inverter_bulut_api", "salt_okuma_onayi": True}}}
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "admin", "exp": 0}
    monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": p, "name": "X", "capacity_kwp": 1000.0, "params_json": dict(durum["pj"])})
    monkeypatch.setattr(plant_service, "params_birlestir", lambda t, p, **an: durum["pj"].update(an) or durum["pj"])
    izler: list = []
    monkeypatch.setattr(api_main._denetim, "kaydet", lambda *a, **k: izler.append(k.get("ayrinti")))
    yazilan: list = []
    monkeypatch.setattr(bo, "_yaz_db", yazilan.append)
    for r in api_main.app.routes:
        if getattr(r, "path", "").startswith("/v1/plants/{plant_id}/bulut-kimlik") and ({"POST", "PATCH", "DELETE"} & getattr(r, "methods", set())):
            for d in r.dependant.dependencies:
                api_main.app.dependency_overrides[d.call] = lambda: {"sub": "u", "tenant_id": "t", "role": "admin", "exp": 0}
    c = TestClient(api_main.app)
    try:
        r = c.post(f"/v1/plants/{PLANT['id']}/bulut-kimlik/oauth/baslat", json={"saglayici": "sungrow", "bolge": "eu", "onaylar": {"sifreli_saklama": False}})
        assert r.status_code == 200 and r.json()["durum"] == "onay_yok" and yazilan == []
        r = c.post(f"/v1/plants/{PLANT['id']}/bulut-kimlik/oauth/baslat", json={"saglayici": "sungrow", "bolge": "eu", "onaylar": {"sifreli_saklama": True}})
        g = r.json()
        assert g["durum"] == "yonlendir" and g["yetki_url"].startswith("https://web3.isolarcloud.eu/?state=") and len(yazilan) == 1
        state = g["yetki_url"].split("state=")[1].split("#")[0]
        assert state not in json.dumps(izler) and "Gizli-Access-Key-9" not in json.dumps(g) and izler[-1]["durum"] == "yonlendir"
        # geri dönüş: kimliksiz; state geçersiz → panele 303 durum koduyla
        monkeypatch.setattr(bo, "_bul_ve_isaretle_db", lambda h, s, *_: None)
        r = c.get("/v1/bulut/oauth/sungrow/geri-donus", params={"code": "Gizli-Kod", "state": "yok"}, follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"] == "https://pvquant.com/?bulut_oauth=sungrow:durum_gecersiz#santralim" and r.headers["cache-control"] == "no-store"
        # geçerli state → belirteç değişimi (sahte) → kasaya yazım → 303 tamam, ayna güncellenir, iz kodu/belirteci içermez
        monkeypatch.setattr(bo, "_bul_ve_isaretle_db", lambda h, s, *_: {"id": "s1", "tenant_id": "t", "plant_id": PLANT["id"], "saglayici": "sungrow", "bolge": "eu", "onay_json": {"onaylar": ONAY2}, "aktor_id": "u"})
        monkeypatch.setattr(bo, "_sonuc_yaz_db", lambda *a: None)
        monkeypatch.setattr(Sungrow, "token_degis", classmethod(lambda cls, bolge, uyg, code, rd, **ek: {"appkey": "APPKEY-1", "access_key": "Gizli-Access-Key-9", "access_token": "AT-Gizli", "refresh_token": "RT-Gizli", "auth_ps_list": ["5001"]}))
        from pvquant.services import bulut_kimlik_service as bk, bulut_sinama_service as bs
        monkeypatch.setattr(bs, "sina", lambda kod, kimlik, onay, bolge=None, transport=None: {"durum": "ok", "zaman": "z", "ozet": {"santraller": [{"kimlik": "5001", "ad": "Bor GES", "kapasite_kwp": 990.0}]}})
        kasaya: list = []
        monkeypatch.setattr(bk, "_yaz_db", lambda t, p, s: kasaya.append(s))
        monkeypatch.setattr(bk, "listele", lambda t, p: [{"saglayici": "sungrow", "etiket": "APP…-1", "cekis_acik": False, "birim_dogrulandi": False, "guncelleme": "z"}])
        r = c.get("/v1/bulut/oauth/sungrow/geri-donus", params={"code": "Gizli-Kod", "state": "gecerli"}, follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"] == f"https://pvquant.com/?bulut_oauth=sungrow:tamam#santralim/{PLANT['id']}"
        assert kasaya and kasaya[0]["dis_kimlik"] == "5001" and b"AT-Gizli" not in kasaya[0]["sifreli"]
        assert durum["pj"]["veri_yolu"]["bulut_kimlik"]["kayitli"] and durum["pj"]["veri_yolu"]["son_sinama"]["ozet"]["uc"] == "oauth"
        tum = json.dumps(izler) + json.dumps(durum, default=str) + r.text
        assert "Gizli-Kod" not in tum and "AT-Gizli" not in tum and "RT-Gizli" not in tum and izler[-1]["durum"] == "tamam"
    finally:
        api_main.app.dependency_overrides.clear()
