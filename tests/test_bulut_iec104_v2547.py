"""v2.547 (P4b-3): inverter bulutu bağlayıcıları (FusionSolar, SolarEdge — httpx.MockTransport, ağ yok), bulut sınaması (anahtar saklanmaz),
IEC 60870-5-104 ulaşılabilirlik (sahte TCP sunucu; yalnız STARTDT). Dış sisteme dokunulmaz."""
from __future__ import annotations

import json
import socket
import threading
from datetime import date, datetime, timezone

import httpx
import pytest

from pvquant.io.bulut import SAGLAYICILAR, FusionSolar, SolarEdge
from pvquant.io.bulut.fusionsolar import FusionSolarHata
from pvquant.io.bulut.solaredge import SolarEdgeHata
from pvquant.io.canli import iec104
from pvquant.services import bulut_sinama_service as bs
from pvquant.services import canli_alim_service as ca
from pvquant.services import veri_yolu_service as vy


def _fusion(h):
    def tasiyici(req: httpx.Request) -> httpx.Response:
        g = json.loads(req.content or b"{}")
        if req.url.path == "/thirdData/login":
            if g.get("systemCode") != "dogru":
                return httpx.Response(200, json={"success": False, "failCode": 305, "data": None})
            return httpx.Response(200, json={"success": True, "failCode": 0, "data": None}, headers={"xsrf-token": "TOK"})
        assert req.headers.get("XSRF-TOKEN") == "TOK", "oturum belirteci gönderilmeli"
        if req.url.path == "/thirdData/getStationList":
            return httpx.Response(200, json={"success": True, "failCode": 0, "data": [{"stationCode": "NE=1", "stationName": "Edikli", "capacity": 15.23}]})
        if req.url.path == "/thirdData/getKpiStationHour":
            return httpx.Response(200, json={"success": True, "failCode": 0, "data": [{"collectTime": 1760000000000, "stationCode": "NE=1", "dataItemMap": {"inverter_power": 98.76, "radiation_intensity": 0.81}}]})
        return httpx.Response(404)
    return httpx.MockTransport(tasiyici)


def test_fusionsolar_giris_liste_saatlik_ve_kimlik_hatasi():
    c = FusionSolar("eu5", transport=_fusion(None))
    c.giris("u", "dogru")
    s = c.santraller()
    assert s == [{"kimlik": "NE=1", "ad": "Edikli", "kapasite_kwp": 15230.0, "saat_dilimi": None}]
    h = c.saatlik("NE=1", datetime(2026, 10, 9, tzinfo=timezone.utc))
    assert h[0]["guc_kw"] == 98.76 and h[0]["ts"].tzinfo is not None
    c2 = FusionSolar("eu5", transport=_fusion(None))
    with pytest.raises(FusionSolarHata, match="305"):
        c2.giris("u", "yanlis")
    with pytest.raises(ValueError, match="bölge"):
        FusionSolar("mars")


def test_solaredge_liste_saatlik_ve_403():
    def tasiyici(req: httpx.Request) -> httpx.Response:
        if req.url.params.get("api_key") != "ABCDEFGH12":
            return httpx.Response(403, json={"String": "Invalid token"})
        if req.url.path == "/sites/list":
            return httpx.Response(200, json={"sites": {"count": 1, "site": [{"id": 42, "name": "Çatı", "peakPower": 480.5, "location": {"timeZone": "Europe/Istanbul"}}]}})
        if req.url.path == "/site/42/energy":
            assert req.url.params["timeUnit"] == "HOUR"
            return httpx.Response(200, json={"energy": {"unit": "Wh", "values": [{"date": "2026-10-09 10:00:00", "value": 123456.0}, {"date": "2026-10-09 11:00:00", "value": None}]}})
        return httpx.Response(404)
    c = SolarEdge("ABCDEFGH12", transport=httpx.MockTransport(tasiyici))
    assert c.santraller()[0] == {"kimlik": 42, "ad": "Çatı", "kapasite_kwp": 480.5, "saat_dilimi": "Europe/Istanbul"}
    e = c.saatlik(42, date(2026, 10, 9), date(2026, 10, 9))
    assert len(e) == 1 and e[0]["enerji_kwh"] == pytest.approx(123.456)
    with pytest.raises(SolarEdgeHata, match="403"):
        SolarEdge("YANLISANAHTAR", transport=httpx.MockTransport(tasiyici)).santraller()
    with pytest.raises(ValueError):
        SolarEdge("kisa")


def test_bulut_sinama_durumlari_ve_anahtar_saklanmaz():
    assert bs.sina("fusionsolar", {"kullanici": "u", "sistem_kodu": "dogru"}, onay=False)["durum"] == "onay_yok"
    assert bs.sina("isolarcloud", {}, onay=True)["durum"] == "saglayici_desteklenmiyor"
    r = bs.sina("fusionsolar", {"kullanici": "u"}, onay=True); assert r["durum"] == "ayar_hatasi" and "systemCode" in r["aciklama"]
    ok = bs.sina("fusionsolar", {"kullanici": "u", "sistem_kodu": "dogru"}, onay=True, bolge="eu5", transport=_fusion(None))
    assert ok["durum"] == "ok" and ok["ozet"]["santral_sayisi"] == 1 and ok["ozet"]["ilk_kapasite_kwp"] == 15230.0 and "saklanmadı" in ok["not"]
    assert "dogru" not in json.dumps(ok) and "kullanici" not in json.dumps(ok)   # anahtar/şifre sonuçta yok
    kh = bs.sina("fusionsolar", {"kullanici": "u", "sistem_kodu": "yanlis"}, onay=True, bolge="eu5", transport=_fusion(None))
    assert kh["durum"] == "kimlik_hatasi"
    def kopuk(req):
        raise httpx.ConnectError("boom")
    assert bs.sina("solaredge", {"api_anahtari": "ABCDEFGH12"}, onay=True, transport=httpx.MockTransport(kopuk))["durum"] == "baglanti_hatasi"
    assert set(SAGLAYICILAR) == {"fusionsolar", "solaredge"}


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
    p = _iec_sunucu(iec104.STARTDT_CON)
    r = iec104.ulasilabilirlik("127.0.0.1", p, 2.0)
    assert r == {"tcp": True, "startdt_con": True, "yanit_hex": "68040b000000"}
    p2 = _iec_sunucu(b"HTTP/1")   # başka hizmet
    assert iec104.ulasilabilirlik("127.0.0.1", p2, 2.0)["startdt_con"] is False
    with pytest.raises(OSError):
        iec104.ulasilabilirlik("127.0.0.1", 1, 1.0)


def test_sina_iec104_durumlari():
    assert ca.sina_iec104({"host": "10.0.0.9"}, onay=False)["durum"] == "onay_yok"
    assert ca.sina_iec104({"host": "127.0.0.1"}, onay=True)["durum"] == "adres_reddedildi"          # adres kuralı Modbus ile aynı
    assert ca.sina_iec104({"host": "10.0.0.9", "port": 99999}, onay=True)["durum"] == "ayar_hatasi"
    ok = ca.sina_iec104({"host": "10.0.0.9"}, onay=True, ulas=lambda h, p, za: {"tcp": True, "startdt_con": True})
    assert ok["durum"] == "ok" and ok["hedef"]["port"] == 2404 and "komut gönderilmedi" in ok["not"]
    assert ca.sina_iec104({"host": "10.0.0.9", "port": 2404}, onay=True, ulas=lambda h, p, za: {"tcp": True, "startdt_con": False})["durum"] == "protokol_yaniti_yok"
    def kopuk(h, p, za):
        raise ConnectionRefusedError("reddedildi")
    assert ca.sina_iec104({"host": "10.0.0.9"}, onay=True, ulas=kopuk)["durum"] == "baglanti_hatasi"
    a = vy.asamalar({"tur": "iec104", "beyan_zamani": "t", "baglanti": {"host": "h", "port": 2404}, "son_sinama": {"durum": "protokol_yaniti_yok", "zaman": "z"}}, [])
    assert [x["kod"] for x in a] == ["secildi", "ayar", "sinama", "akis"] and a[2]["etiket"] == "istasyona ulaşıldı, 104 onayı yok" and not a[2]["tamam"]


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
    monkeypatch.setattr(ca, "sina_iec104", lambda ayar, onay, ulas=None: {"durum": "ok" if onay else "onay_yok", "zaman": "z", "hedef": ayar})
    monkeypatch.setattr(vy, "etkin_yollar", lambda t, p, simdi=None: [])
    for r in api_main.app.routes:
        if getattr(r, "path", "").startswith("/v1/plants/{plant_id}/veri-yolu") and ({"PUT", "POST"} & getattr(r, "methods", set())):
            for d in r.dependant.dependencies:
                api_main.app.dependency_overrides[d.call] = lambda: {"sub": "u", "tenant_id": "t", "role": "admin", "exp": 0}
    c = TestClient(api_main.app)
    try:
        assert c.post(f"/v1/plants/{PLANT}/veri-yolu/bulut-sinama", json={"saglayici": "solaredge", "kimlik": {"api_anahtari": "ABCDEFGH12"}}).status_code == 422   # hedef bulut değil
        c.put(f"/v1/plants/{PLANT}/veri-yolu", json={"tur": "inverter_bulut_api", "salt_okuma_onayi": True})
        r = c.post(f"/v1/plants/{PLANT}/veri-yolu/bulut-sinama", json={"saglayici": "solaredge", "kimlik": {"api_anahtari": "ABCDEFGH12"}})
        assert r.status_code == 200 and r.json()["durum"] == "ok"
        g = c.get(f"/v1/plants/{PLANT}/veri-yolu").json()
        assert g["beyan"]["son_sinama"]["durum"] == "ok" and g["beyan"]["saglayici"] == "solaredge" and "ABCDEFGH12" not in json.dumps(g)   # anahtar yazılmadı
        assert "ABCDEFGH12" not in json.dumps(izler)                                                                                             # denetim izinde de yok
        assert g["bulut"]["saglayicilar"][0]["kod"] == "fusionsolar" and "iSolarCloud (Sungrow)" in g["bulut"]["henuz_yok"]
        c.put(f"/v1/plants/{PLANT}/veri-yolu", json={"tur": "iec104", "salt_okuma_onayi": True, "baglanti": {"host": "10.0.0.9", "port": 2404}})
        assert c.post(f"/v1/plants/{PLANT}/veri-yolu/sinama").json()["durum"] == "ok"
        c.put(f"/v1/plants/{PLANT}/veri-yolu", json={"tur": "opc_ua", "salt_okuma_onayi": True, "baglanti": {"host": "10.0.0.9"}})
        assert c.post(f"/v1/plants/{PLANT}/veri-yolu/sinama").status_code == 422                                                              # OPC UA sınaması yok
    finally:
        api_main.app.dependency_overrides.clear()
