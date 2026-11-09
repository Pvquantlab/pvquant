"""v2.547 (P4b-3): inverter bulutu bağlayıcıları (FusionSolar, SolarEdge — httpx.MockTransport, ağ yok), bulut sınaması (anahtar saklanmaz),
IEC 60870-5-104 ulaşılabilirlik (sahte TCP sunucu). v2.548 (Aşama 0): SolarEdge V1 kapandı → devre dışı; FusionSolar /thirdData/stations sayfalı + 401 yedeği +
bölge listesi (au1 yok, au5/jp5/kr5 var, Huawei alan adı deseni); IEC 104 varsayılan yalnız TCP, STARTDT yalnız sahip onayıyla. Dış sisteme dokunulmaz."""
from __future__ import annotations

import json
import socket
import threading
from datetime import date, datetime, timezone

import httpx
import pytest

from pvquant.io.bulut import AKTIF_SAGLAYICILAR, HENUZ_YOK, SAGLAYICILAR, FusionSolar, SolarEdge
from pvquant.io.bulut.fusionsolar import BOLGELER, FusionSolarHata, kok_adres
from pvquant.io.bulut.solaredge import SolarEdgeHata
from pvquant.io.canli import iec104
from pvquant.services import bulut_sinama_service as bs
from pvquant.services import canli_alim_service as ca
from pvquant.services import veri_yolu_service as vy


def _fusion(h, eski_hesap: bool = False):
    """Sahte NBI: yeni sayfalı /thirdData/stations (capacity kWp, 2 sayfa) ya da eski_hesap=True ise yeni uç 401 → eski getStationList (capacity MWp)."""
    def tasiyici(req: httpx.Request) -> httpx.Response:
        g = json.loads(req.content or b"{}")
        if req.url.path == "/thirdData/login":
            if g.get("systemCode") != "dogru":
                return httpx.Response(200, json={"success": False, "failCode": 305, "data": None})
            return httpx.Response(200, json={"success": True, "failCode": 0, "data": None}, headers={"xsrf-token": "TOK"})
        assert req.headers.get("XSRF-TOKEN") == "TOK", "oturum belirteci gönderilmeli"
        if req.url.path == "/thirdData/stations":
            if eski_hesap:
                return httpx.Response(200, json={"success": False, "failCode": 401, "data": None})
            assert g.get("pageNo") in (1, 2) and g.get("pageSize") == 100
            sayfa = [{"plantCode": "NE=1", "plantName": "Edikli", "capacity": 15230.0, "timeZone": "Europe/Istanbul"}] if g["pageNo"] == 1 else [{"plantCode": "NE=2", "plantName": "Bor", "capacity": 990.5}]
            return httpx.Response(200, json={"success": True, "failCode": 0, "data": {"total": 2, "pageCount": 2, "pageNo": g["pageNo"], "pageSize": 100, "list": sayfa}})
        if req.url.path == "/thirdData/getStationList":
            assert eski_hesap, "yeni uç varken tarihsel uç çağrılmamalı"
            return httpx.Response(200, json={"success": True, "failCode": 0, "data": [{"stationCode": "NE=1", "stationName": "Edikli", "capacity": 15.23}]})
        if req.url.path == "/thirdData/getKpiStationHour":
            return httpx.Response(200, json={"success": True, "failCode": 0, "data": [{"collectTime": 1760000000000, "stationCode": "NE=1", "dataItemMap": {"inverter_power": 98.76, "radiation_intensity": 0.81}}]})
        return httpx.Response(404)
    return httpx.MockTransport(tasiyici)


def test_fusionsolar_giris_liste_saatlik_ve_kimlik_hatasi():
    c = FusionSolar("eu5", transport=_fusion(None))
    c.giris("u", "dogru")
    s = c.santraller()   # v2.548: sayfalı /thirdData/stations, capacity kWp, iki sayfa birleşir
    assert s == [{"kimlik": "NE=1", "ad": "Edikli", "kapasite_kwp": 15230.0, "saat_dilimi": "Europe/Istanbul", "uc": "stations"},
                 {"kimlik": "NE=2", "ad": "Bor", "kapasite_kwp": 990.5, "saat_dilimi": None, "uc": "stations"}]
    h = c.saatlik("NE=1", datetime(2026, 10, 9, tzinfo=timezone.utc))
    assert h[0]["dataItemMap"]["inverter_power"] == 98.76 and "collectTime" in h[0]   # v2.557: ham data[] döner; yorum bulut_cekis_service.satirlar
    from pvquant.services import bulut_cekis_service as bc
    assert bc.satirlar(h)[0]["ts_utc"].tzinfo is not None and bc.satirlar(h)[0]["alanlar"]["inverter_power"] == 98.76
    c2 = FusionSolar("eu5", transport=_fusion(None))
    with pytest.raises(FusionSolarHata, match="305"):
        c2.giris("u", "yanlis")
    with pytest.raises(ValueError, match="bölge"):
        FusionSolar("mars")


def test_fusionsolar_eski_hesap_yedegi_bolgeler_ve_sistem_siniri():
    c = FusionSolar("intl", transport=_fusion(None, eski_hesap=True))   # yeni uç 401 → tarihsel getStationList, capacity MWp → kWp
    c.giris("u", "dogru")
    assert c.santraller() == [{"kimlik": "NE=1", "ad": "Edikli", "kapasite_kwp": 15230.0, "saat_dilimi": None, "uc": "getStationList"}]
    assert "au1" not in BOLGELER and {"au5", "jp5", "kr5", "intl", "eu5"} <= set(BOLGELER)          # A tur 2 HW-18/19: au1 NXDOMAIN
    assert kok_adres("region01eu5.fusionsolar.huawei.com") == "https://region01eu5.fusionsolar.huawei.com"
    for kotu in ("evil.com", "eu5.fusionsolar.huawei.com.evil.net", "http://x", "a b.fusionsolar.huawei.com"):
        with pytest.raises(ValueError):
            kok_adres(kotu)
    def sinir(req):
        return httpx.Response(429, text="too many")
    c3 = FusionSolar("eu5", transport=httpx.MockTransport(sinir))
    with pytest.raises(FusionSolarHata, match="429"):
        c3.giris("u", "x")
    def gunluk(req):
        return httpx.Response(200, json={"success": False, "failCode": 20618})
    with pytest.raises(FusionSolarHata, match="20618"):
        FusionSolar("eu5", transport=httpx.MockTransport(gunluk)).giris("u", "x")


def test_solaredge_v1_sinifi_referans_ve_kapandi():
    """v2.548 (H1): V1 sicilde «kapandi», sınama reddeder, arayüzde seçilemez. v2.562 (K4): V1 sınıfı kaldırıldı; aynı anahtar altında V2 filo bağlayıcısı
    (test_k3_k4_v2562); anahtar URL'de değil başlıkta."""
    from pvquant.io.bulut.solaredge import KAPANDI
    assert KAPANDI == "2026-11-03" and SAGLAYICILAR["solaredge_v1"]["durum"] == "kapandi" and "solaredge_v1" not in AKTIF_SAGLAYICILAR
    assert "solaredge" in AKTIF_SAGLAYICILAR and set(AKTIF_SAGLAYICILAR) == {"fusionsolar", "solaredge", "solis", "sungrow", "growatt"}
    c = SolarEdge(); c.giris({"api_anahtari": "ABCDEFGH12"})
    assert c._c.headers["X-API-Key"] == "ABCDEFGH12" and c.kok.endswith("/v2")
    c.kapat()


def test_bulut_sinama_durumlari_ve_anahtar_saklanmaz():
    assert bs.sina("fusionsolar", {"kullanici": "u", "sistem_kodu": "dogru"}, onay=False)["durum"] == "onay_yok"
    assert bs.sina("isolarcloud", {}, onay=True)["durum"] == "saglayici_desteklenmiyor"
    kap = bs.sina("solaredge_v1", {"api_anahtari": "ABCDEFGH12"}, onay=True); assert kap["durum"] == "saglayici_kapandi" and "3 Kasım 2026" in kap["aciklama"]   # v2.548 H1
    r = bs.sina("fusionsolar", {"kullanici": "u"}, onay=True); assert r["durum"] == "ayar_hatasi" and "systemCode" in r["aciklama"]
    ok = bs.sina("fusionsolar", {"kullanici": "u", "sistem_kodu": "dogru"}, onay=True, bolge="eu5", transport=_fusion(None))
    assert ok["durum"] == "ok" and ok["ozet"]["santral_sayisi"] == 2 and ok["ozet"]["ilk_kapasite_kwp"] == 15230.0 and ok["ozet"]["uc"] == "stations" and "saklanmadı" in ok["not"]
    assert "dogru" not in json.dumps(ok) and "kullanici" not in json.dumps(ok)   # anahtar/şifre sonuçta yok
    kh = bs.sina("fusionsolar", {"kullanici": "u", "sistem_kodu": "yanlis"}, onay=True, bolge="eu5", transport=_fusion(None))
    assert kh["durum"] == "kimlik_hatasi"
    def kopuk(req):
        raise httpx.ConnectError("boom")
    assert bs.sina("fusionsolar", {"kullanici": "u", "sistem_kodu": "dogru"}, onay=True, transport=httpx.MockTransport(kopuk))["durum"] == "baglanti_hatasi"
    assert bs.sina("fusionsolar", {"kullanici": "u", "sistem_kodu": "dogru"}, onay=True, bolge="evil.com")["durum"] == "ayar_hatasi"   # alan adı dışı bölge reddi
    assert set(SAGLAYICILAR) == {"fusionsolar", "solaredge_v1", "solaredge", "solis", "sungrow", "growatt"}   # v2.562


def _iec_sunucu(cevap: bytes | None):
    srv = socket.socket(); srv.bind(("127.0.0.1", 0)); srv.listen(1); port = srv.getsockname()[1]
    def kos():
        c, _ = srv.accept()
        try:
            veri = c.recv(6)
            if veri == iec104.STARTDT_ACT and cevap is not None:
                c.sendall(cevap)
            try:
                c.settimeout(1.0); c.recv(6)
            except OSError:
                pass
        finally:
            c.close(); srv.close()
    threading.Thread(target=kos, daemon=True).start()
    return port


def test_iec104_ulasilabilirlik_con_ve_yanitsiz():
    p0 = _iec_sunucu(iec104.STARTDT_CON)   # v2.548 H2: varsayılan kip STARTDT göndermez
    assert iec104.ulasilabilirlik("127.0.0.1", p0, 2.0) == {"tcp": True, "startdt_con": None, "startdt_gonderildi": False, "yanit_hex": None}
    p = _iec_sunucu(iec104.STARTDT_CON)
    r = iec104.ulasilabilirlik("127.0.0.1", p, 2.0, startdt=True)
    assert r == {"tcp": True, "startdt_con": True, "startdt_gonderildi": True, "yanit_hex": "68040b000000"}
    p2 = _iec_sunucu(b"HTTP/1")   # başka hizmet
    assert iec104.ulasilabilirlik("127.0.0.1", p2, 2.0, startdt=True)["startdt_con"] is False
    with pytest.raises(OSError):
        iec104.ulasilabilirlik("127.0.0.1", 1, 1.0)


def test_sina_iec104_durumlari():
    assert ca.sina_iec104({"host": "10.0.0.9"}, onay=False)["durum"] == "onay_yok"
    assert ca.sina_iec104({"host": "127.0.0.1"}, onay=True)["durum"] == "adres_reddedildi"          # adres kuralı Modbus ile aynı
    assert ca.sina_iec104({"host": "10.0.0.9", "port": 99999}, onay=True)["durum"] == "ayar_hatasi"
    gonderilen = []
    def ulas(h, p, za, st):
        gonderilen.append(st); return {"tcp": True, "startdt_con": (True if st else None), "startdt_gonderildi": st}
    tcp = ca.sina_iec104({"host": "10.0.0.9"}, onay=True, ulas=ulas)                      # v2.548 H2: varsayılan yalnız TCP
    assert tcp["durum"] == "ok" and tcp["hedef"]["port"] == 2404 and tcp["ozet"]["yontem"] == "tcp" and tcp["ozet"]["startdt_con"] is None and "STARTDT gönderilmedi" in tcp["not"]
    ok = ca.sina_iec104({"host": "10.0.0.9"}, onay=True, ulas=ulas, startdt_onayi=True)   # sahip onayıyla STARTDT
    assert ok["durum"] == "ok" and ok["ozet"]["yontem"] == "startdt" and ok["ozet"]["startdt_con"] is True and "komut gönderilmedi" in ok["not"]
    assert gonderilen == [False, True]
    assert ca.sina_iec104({"host": "10.0.0.9", "port": 2404}, onay=True, startdt_onayi=True, ulas=lambda h, p, za, st: {"tcp": True, "startdt_con": False, "startdt_gonderildi": True})["durum"] == "protokol_yaniti_yok"
    def kopuk(h, p, za, st):
        raise ConnectionRefusedError("reddedildi")
    assert ca.sina_iec104({"host": "10.0.0.9"}, onay=True, ulas=kopuk)["durum"] == "baglanti_hatasi"
    a = vy.asamalar({"tur": "iec104", "beyan_zamani": "t", "baglanti": {"host": "h", "port": 2404}, "son_sinama": {"durum": "protokol_yaniti_yok", "zaman": "z"}}, [])
    assert [x["kod"] for x in a] == ["secildi", "ayar", "sinama", "nokta", "cekis", "akis"] and a[2]["etiket"] == "istasyona ulaşıldı, 104 onayı yok" and not a[2]["tamam"]   # v2.554: nokta + çekiş aşamaları
    t = vy.asamalar({"tur": "iec104", "beyan_zamani": "t", "baglanti": {"host": "h"}, "son_sinama": {"durum": "ok", "zaman": "z", "ozet": {"yontem": "tcp"}}}, [])
    assert t[2]["etiket"] == "TCP bağlantısı açıldı (STARTDT sınanmadı)" and t[2]["tamam"]   # v2.548 H2


PLANT = "22222222-2222-2222-2222-222222222222"


def test_api_bulut_ve_iec104_kapilari(monkeypatch):
    import apps.api.main as api_main
    from fastapi.testclient import TestClient
    from apps.api.deps import gecerli_kullanici
    from pvquant.services import plant_service
    durum = {"pj": {"segment": "lisansli_serbest"}}
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "admin", "exp": 0}
    monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": p, "name": "X", "capacity_kwp": 1000.0, "params_json": dict(durum["pj"])})
    def _birlestir(t, p, **an):
        durum["pj"] = {**durum["pj"], **an}; return durum["pj"]
    monkeypatch.setattr(plant_service, "params_birlestir", _birlestir)
    izler = []
    monkeypatch.setattr(api_main._denetim, "kaydet", lambda *a, **k: izler.append(k.get("ayrinti")))
    monkeypatch.setattr(bs, "sina", lambda s, k, onay, bolge=None, transport=None: {"durum": "ok" if onay and k.get("api_anahtari") else "onay_yok", "zaman": "z", "ozet": {"santral_sayisi": 1}})
    startdt_gelen = []
    def _sahte_iec(ayar, onay, ulas=None, startdt_onayi=False, **kw):
        startdt_gelen.append(startdt_onayi); return {"durum": "ok" if onay else "onay_yok", "zaman": "z", "hedef": ayar, "ozet": {"yontem": "startdt" if startdt_onayi else "tcp"}}
    monkeypatch.setattr(ca, "sina_iec104", _sahte_iec)
    monkeypatch.setattr(vy, "etkin_yollar", lambda t, p, simdi=None: [])
    for r in api_main.app.routes:
        if getattr(r, "path", "").startswith("/v1/plants/{plant_id}/veri-yolu") and ({"PUT", "POST"} & getattr(r, "methods", set())):
            for d in r.dependant.dependencies:
                api_main.app.dependency_overrides[d.call] = lambda: {"sub": "u", "tenant_id": "t", "role": "admin", "exp": 0}
    c = TestClient(api_main.app)
    try:
        assert c.post(f"/v1/plants/{PLANT}/veri-yolu/bulut-sinama", json={"saglayici": "fusionsolar", "kimlik": {"api_anahtari": "ABCDEFGH12"}}).status_code == 422   # hedef bulut değil
        c.put(f"/v1/plants/{PLANT}/veri-yolu", json={"tur": "inverter_bulut_api", "salt_okuma_onayi": True})
        r = c.post(f"/v1/plants/{PLANT}/veri-yolu/bulut-sinama", json={"saglayici": "fusionsolar", "kimlik": {"api_anahtari": "ABCDEFGH12"}})
        assert r.status_code == 200 and r.json()["durum"] == "ok"
        g = c.get(f"/v1/plants/{PLANT}/veri-yolu").json()
        assert g["beyan"]["son_sinama"]["durum"] == "ok" and g["beyan"]["saglayici"] == "fusionsolar" and "ABCDEFGH12" not in json.dumps(g)   # anahtar yazılmadı
        assert "ABCDEFGH12" not in json.dumps(izler)                                                                                             # denetim izinde de yok
        assert g["bulut"]["saglayicilar"][0]["kod"] == "fusionsolar" and "SEMS Portal (GoodWe)" in g["bulut"]["henuz_yok"]
        se = next(x for x in g["bulut"]["saglayicilar"] if x["kod"] == "solaredge_v1")
        assert se["durum"] == "kapandi" and "3 Kasım 2026" in se["durum_etiketi"] and "au1" not in g["bulut"]["bolgeler"] and "au5" in g["bulut"]["bolgeler"]   # v2.548 H1/H3
        c.put(f"/v1/plants/{PLANT}/veri-yolu", json={"tur": "iec104", "salt_okuma_onayi": True, "baglanti": {"host": "10.0.0.9", "port": 2404}})
        assert c.post(f"/v1/plants/{PLANT}/veri-yolu/sinama").json()["ozet"]["yontem"] == "tcp"                                                 # v2.548 H2: varsayılan TCP
        c.put(f"/v1/plants/{PLANT}/veri-yolu", json={"tur": "iec104", "salt_okuma_onayi": True, "startdt_onayi": True, "baglanti": {"host": "10.0.0.9", "port": 2404}})
        assert c.post(f"/v1/plants/{PLANT}/veri-yolu/sinama").json()["ozet"]["yontem"] == "startdt" and startdt_gelen == [False, True]
        c.put(f"/v1/plants/{PLANT}/veri-yolu", json={"tur": "modbus_sunspec", "salt_okuma_onayi": True, "startdt_onayi": True, "baglanti": {"host": "10.0.0.9"}})
        assert c.get(f"/v1/plants/{PLANT}/veri-yolu").json()["beyan"]["startdt_onayi"] is False                                                 # yalnız IEC 104 hedefinde anlamlı
        c.put(f"/v1/plants/{PLANT}/veri-yolu", json={"tur": "opc_ua", "salt_okuma_onayi": True, "baglanti": {"host": "10.0.0.9"}})
        assert c.post(f"/v1/plants/{PLANT}/veri-yolu/sinama").status_code == 422                                                              # OPC UA sınaması yok
    finally:
        api_main.app.dependency_overrides.clear()
