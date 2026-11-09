"""v2.562 (Aşama 3, K3/K4) — SolarEdge V2, SolisCloud, Sungrow, Growatt bağlayıcıları (sahte taşıyıcı), ortak sicil, genel sınama ve çekiş. Belgeden; gerçek hesapla doğrulanmadı."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from pvquant.io.bulut import AKTIF_SAGLAYICILAR, SAGLAYICILAR, Growatt, SolarEdge, Solis, Sungrow
from pvquant.io.bulut import solis as solis_mod
from pvquant.io.bulut.temel import BulutHata, saatlik_fark
from pvquant.services import bulut_cekis_service as bc
from pvquant.services import bulut_sinama_service as bs

GUN = datetime(2026, 11, 9, tzinfo=timezone.utc)


def test_sicil_tutarli():
    for kod, v in AKTIF_SAGLAYICILAR.items():
        assert v["sinif"].KOD == kod and v["kimlik_alanlari"] and set(v["kimlik_etiketleri"]) >= set(v["kimlik_alanlari"]) and v["gunluk_tavan"] > 0
        assert v["durum"] == "uygulandi_dogrulanmadi" and "doğrulanmadı" in v["durum_etiketi"] and "enerji_kwh_belge" in v["alanlar"] or kod == "growatt"
    assert SAGLAYICILAR["solaredge_v1"]["durum"] == "kapandi" and "solaredge_v1" not in AKTIF_SAGLAYICILAR
    assert Sungrow.cagri_tahmini(1) == 8 and Sungrow.cagri_tahmini(51) == 16 and SolarEdge.cagri_tahmini(3) == 3 and Solis.TOPLU is False


def test_solis_imza_belge_ornegi_ve_yasak_uc():
    bayt = solis_mod.govde_bayt({"pageNo": 1, "pageSize": 10})
    assert bayt == b'{"pageNo":1,"pageSize":10}' and solis_mod.icerik_md5(bayt) == "kxdxk7rbAsrzSIWgEwhH4w=="   # belge §2.4 değeri
    sign = solis_mod.imza("gizli", "kxdxk7rbAsrzSIWgEwhH4w==", "application/json;charset=UTF-8", "Fri, 26 Jul 2019 06:00:46 GMT", "/v1/api/userStationList")
    assert len(sign) == 28 and sign.endswith("=")   # Base64(HmacSHA1) 20 bayt
    assert solis_mod.tarih_gmt(datetime(2019, 7, 26, 6, 0, 46, tzinfo=timezone.utc)) == "Fri, 26 Jul 2019 06:00:46 GMT"
    c = Solis("www"); c.giris({"api_id": "id", "api_secret": "gizli"})
    with pytest.raises(BulutHata, match="yazma ucu yasak"):
        c._post("/v1/api/addStation", {})
    c.kapat()
    with pytest.raises(ValueError, match="bölge"):
        Solis("eu")


def _solis_tasiyici(req: httpx.Request) -> httpx.Response:
    assert req.headers["Authorization"].startswith("API id:") and req.headers["Content-MD5"] and req.headers["Date"].endswith("GMT")
    if req.url.path == "/v1/api/userStationList":
        return httpx.Response(200, json={"success": True, "code": "0", "data": {"page": {"records": [{"id": 501, "stationName": "Edikli", "capacity": 1000.0, "capacityStr": "kWp", "timeZone": 3, "timeZoneName": "Europe/Istanbul"}]}}})
    if req.url.path == "/v1/api/stationDay":
        b = json.loads(req.content); assert b["timeZone"] == 3 and b["money"] == "EUR" and b["time"] == "2026-11-09"
        bas = datetime(2026, 11, 9, 6, 0, tzinfo=timezone.utc)   # 09:00 TSİ
        rows = [{"time": int((bas + timedelta(minutes=5 * i)).timestamp() * 1000), "power": 100.0 + i, "produceEnergy": 10.0 + i * 0.5} for i in range(25)]   # 06:00–08:00
        return httpx.Response(200, json={"success": True, "code": "0", "data": rows})
    return httpx.Response(200, json={"success": False, "code": "R0000", "msg": "no authority"})


def test_solis_liste_ve_saatlik_fark():
    c = Solis("www", transport=httpx.MockTransport(_solis_tasiyici)); c.giris({"api_id": "id", "api_secret": "gizli"}); c._son = 0.0
    s = c.santraller(); assert s[0]["kimlik"] == "501" and s[0]["kapasite_kwp"] == 1000.0 and s[0]["saat_dilimi"] == "Europe/Istanbul"
    c._son = 0.0
    h = c.saatlik_ham(["501"], GUN)
    saat6 = next(r for r in h if r["ts_utc"] == datetime(2026, 11, 9, 6, 0, tzinfo=timezone.utc))
    assert saat6["alanlar"]["enerji_kwh_belge"] == 6.0 and saat6["alanlar"]["n_nokta"] == 12 and saat6["alanlar"]["guc_kw_ort"] == pytest.approx(105.5)   # 12 nokta × 0,5 kWh
    saat8 = next(r for r in h if r["ts_utc"] == datetime(2026, 11, 9, 8, 0, tzinfo=timezone.utc))
    assert saat8["alanlar"]["enerji_kwh_belge"] is None   # 09:00 noktası yok → fark yok
    c._son = 0.0
    with pytest.raises(BulutHata, match="yetki yok"):
        c._post("/v1/api/stationDetail", {"id": 1})
    assert c.cagri == 3   # liste + gün + hatalı çağrı


def _se_tasiyici(req: httpx.Request) -> httpx.Response:
    assert req.headers.get("X-API-Key") == "FLEET-KEY" and "api_key" not in str(req.url)
    if req.url.path == "/v2/sites":
        return httpx.Response(200, json={"sites": {"count": 1, "site": [{"siteId": 2951500, "name": "Bor", "peakPower": 990.5, "activationStatus": "ACTIVE", "location": {"timezone": "Europe/Istanbul"}}]}})
    if req.url.path == "/v2/sites/2951500/energy":
        assert req.url.params["resolution"] == "HOUR" and req.url.params["unit"] == "KWH" and "+03:00" in req.url.params["from"]
        return httpx.Response(200, json={"unit": "KWH", "resolution": "HOUR", "values": [{"timestamp": "2026-11-09T09:00:00+03:00", "value": 412.5}, {"timestamp": "2026-11-09T10:00:00+03:00", "value": None}]})
    if req.url.path == "/v2/sites/1/energy":
        return httpx.Response(429, headers={"x-ratelimit-remaining-minute": "0", "retry-after": "30"}, json={"message": "API rate limit exceeded"})
    if req.url.path == "/v2/sites/2/energy":
        return httpx.Response(401, json={"error": "invalid_api_key"})
    return httpx.Response(404, json={"title": "Unknown endpoint"})


def test_solaredge_v2_filo():
    c = SolarEdge(transport=httpx.MockTransport(_se_tasiyici)); c.giris({"api_anahtari": "FLEET-KEY"})
    s = c.santraller(); assert s == [{"kimlik": "2951500", "ad": "Bor", "kapasite_kwp": 990.5, "saat_dilimi": "Europe/Istanbul", "uc": "sites", "durum": "ACTIVE"}]
    h = c.saatlik_ham(["2951500"], GUN)
    assert h[0]["ts_utc"] == datetime(2026, 11, 9, 6, 0, tzinfo=timezone.utc) and h[0]["alanlar"]["enerji_kwh_belge"] == 412.5 and h[1]["alanlar"]["enerji_kwh_belge"] is None
    with pytest.raises(BulutHata, match="dakikalık"):
        c.saatlik_ham(["1"], GUN)
    with pytest.raises(BulutHata, match="geçersiz"):
        c.saatlik_ham(["2"], GUN)
    assert c.cagri == 4


class _SungrowSahte:
    def __init__(self):
        self.token_denemeleri = []
    def __call__(self, req: httpx.Request) -> httpx.Response:
        b = json.loads(req.content) if req.content else {}
        if req.url.path == "/openapi/apiManage/refreshToken":
            assert b["refresh_token"] == "R1" and b["appkey"] == "APP"
            return httpx.Response(200, json={"result_code": "1", "result_data": {"code": 1, "access_token": "T2", "refresh_token": "R2"}})
        assert req.headers["x-access-key"] == "AK" and b["appkey"] == "APP"
        tok = req.headers["Authorization"]; self.token_denemeleri.append(tok)
        if tok == "Bearer T1":
            return httpx.Response(200, json={"result_code": "E00003", "result_msg": "token expired"})
        if req.url.path == "/openapi/platform/queryPowerStationList":
            return httpx.Response(200, json={"result_code": "1", "result_data": {"row_count": 1, "pageList": [{"ps_id": 700688188, "ps_name": "Kıvanç", "online_status": 1, "ps_type": 3}]}})
        if req.url.path == "/openapi/platform/getPowerStationPointMinuteDataList":
            bas = datetime.strptime(b["start_time_stamp"], "%Y%m%d%H%M%S")
            rows = [{"time_stamp": (bas + timedelta(minutes=15 * i)).strftime("%Y%m%d%H%M%S"), "p83022": str(1000 * (bas.hour * 4 + i)), "p83033": "50000"} for i in range(13)]
            return httpx.Response(200, json={"result_code": "1", "result_data": {"700688188": rows}})
        return httpx.Response(200, json={"result_code": "E900"})


def test_sungrow_token_yenileme_ve_saatlik_fark():
    sahte = _SungrowSahte(); yeni = []
    c = Sungrow("eu", transport=httpx.MockTransport(sahte)); c.kimlik_yenile = yeni.append
    c.giris({"appkey": "APP", "access_key": "AK", "access_token": "T1", "refresh_token": "R1"})
    s = c.santraller(); assert s[0]["kimlik"] == "700688188" and yeni == [{"appkey": "APP", "access_key": "AK", "access_token": "T2", "refresh_token": "R2"}]   # E00003 → yenilendi → saklandı
    assert sahte.token_denemeleri[:2] == ["Bearer T1", "Bearer T2"]
    h = c.saatlik_ham(["700688188"], GUN)
    assert len(h) >= 20 and all(r["alanlar"]["enerji_kwh_belge"] == pytest.approx(4.0) for r in h if r["alanlar"]["enerji_kwh_belge"] is not None)   # 4 × 1000 Wh = 4 kWh/saat
    assert c.cagri == 1 + 1 + 1 + 8   # başarısız liste + yenileme + liste + 8 pencere
    with pytest.raises(BulutHata, match="erişim yetkilendirilmemiş"):
        c._post("/openapi/platform/getPowerStationDetail", {})


def _growatt_tasiyici(req: httpx.Request) -> httpx.Response:
    assert req.headers["token"] == "TOK"
    if req.url.path == "/v1/plant/list":
        return httpx.Response(200, json={"error_code": 0, "data": {"plants": [{"plant_id": 77, "name": "Format Lab", "peak_power": 12.5, "timezone": "Europe/Istanbul"}]}})
    if req.url.path == "/v1/plant/power":
        assert req.url.params["plant_id"] == "77" and req.url.params["date"] == "2026-11-09"
        return httpx.Response(200, json={"error_code": 0, "data": {"powers": [{"time": "2026-11-09 10:00:00", "power": 8.0}, {"time": "2026-11-09 10:05:00", "power": 9.0}, {"time": "2026-11-09 11:00:00", "power": 10.0}]}})
    return httpx.Response(200, json={"error_code": 10012, "error_msg": "frequency"})


def test_growatt_liste_ve_guc_serisi():
    c = Growatt("intl", transport=httpx.MockTransport(_growatt_tasiyici)); c.giris({"token": "TOK"})
    assert c.santraller()[0] == {"kimlik": "77", "ad": "Format Lab", "kapasite_kwp": 12.5, "saat_dilimi": "Europe/Istanbul", "uc": "plant/list"}
    h = c.saatlik_ham(["77"], GUN)
    assert h[0]["ts_utc"] == datetime(2026, 11, 9, 7, 0, tzinfo=timezone.utc) and h[0]["alanlar"] == {"guc_kw_ort": 8.5, "n_nokta": 2} and "enerji_kwh_belge" not in h[0]["alanlar"]
    with pytest.raises(BulutHata, match="sıklığı"):
        c._kontrol(c._c.get("/v1/plant/energy"))


def test_genel_sinama_ve_cekis_toplu_olmayan():
    r = bs.sina("solis", {"api_id": "id", "api_secret": "gizli"}, True, "www", transport=httpx.MockTransport(_solis_tasiyici))
    assert r["durum"] == "ok" and r["ozet"]["santraller"][0]["kimlik"] == "501" and "saklanmadı" in r["not"]
    assert bs.sina("solis", {"api_id": "id"}, True)["durum"] == "ayar_hatasi" and "Key Secret" in bs.sina("solis", {"api_id": "id"}, True)["aciklama"]
    assert bs.sina("solaredge_v1", {"api_anahtari": "x"}, True)["durum"] == "saglayici_kapandi"
    # genel çekiş: santral başına çağrı (TOPLU değil), tavan sicilden (SolarEdge 60), token yenileme geri çağrısı bağlanır
    class Sahte(SolarEdge):
        def __init__(self, bolge=None, transport=None, zaman_asimi=None):
            super().__init__(bolge, httpx.MockTransport(_se_tasiyici), zaman_asimi)
    kayitlar = [{"id": i, "tenant_id": "t", "plant_id": f"p{i}", "saglayici": "solaredge", "bolge": None, "dis_kimlik": "2951500", "birim_dogrulandi": i == 2, "kota_gun": None, "kota_sayac": 0, "tz": "Europe/Istanbul"} for i in (1, 2)]
    ham, golge, gunc = [], [], []
    out = bc.tur(simdi=datetime(2026, 11, 9, 10, 30, tzinfo=timezone.utc), kayitlar=kayitlar, coz=lambda k: {"api_anahtari": "FLEET-KEY"}, istemci_fabrikasi=Sahte,
                 ham_yaz=lambda k, st: (ham.append(k["plant_id"]), len(st))[1], golge_yaz=lambda k, st, s: (golge.append(k["plant_id"]), 1)[1], guncelle=lambda k, d, h, z, g, s: gunc.append((k["plant_id"], d, s)))
    assert sorted(ham) == ["p1", "p2"] and golge == ["p2"] and gunc == [("p1", "ok", 1), ("p2", "ok", 1)] and "çağrı 1/60" in out
    # kota: SolarEdge tavanı 60 → 60 dolu ise atlanır
    kayitlar[0]["kota_gun"] = "2026-11-09"; kayitlar[0]["kota_sayac"] = 60; gunc.clear()
    out = bc.tur(simdi=datetime(2026, 11, 9, 10, 30, tzinfo=timezone.utc), kayitlar=kayitlar, coz=lambda k: {"api_anahtari": "FLEET-KEY"}, istemci_fabrikasi=Sahte,
                 ham_yaz=lambda *a: 0, golge_yaz=lambda *a: 0, guncelle=lambda k, d, h, z, g, s: gunc.append(d))
    assert gunc == ["kota_doldu", "kota_doldu"] and "60/60" in out
    assert saatlik_fark([(GUN, 10.0), (GUN + timedelta(hours=1), 12.5), (GUN + timedelta(hours=2), 3.0)]) == {GUN: 2.5}   # geri giden sayaç atlanır


def test_portfoy_baglanti_ozeti():
    from pvquant.services import portfoy_service as ps
    assert ps._baglanti({}) is None and ps._baglanti({"veri_yolu": {"tur": None}}) is None
    b = ps._baglanti({"veri_yolu": {"tur": "modbus_sunspec", "salt_okuma_onayi": True, "ornekleme_acik": True, "baglanti": {"host": "10.0.0.5", "port": 502, "birim": 1, "cihazlar": [{"birim": 2}, {"birim": 3}]}}})
    assert b["tur_kisa"] == "Modbus TCP / SunSpec" and b["kod"] == "cekis_acik" and b["cekis_acik"] and b["n_cihaz"] == 3
    b = ps._baglanti({"veri_yolu": {"tur": "inverter_bulut_api", "saglayici": "solis", "salt_okuma_onayi": True, "bulut_kimlik": {"kayitli": True, "cekis_acik": True}}})
    assert b["kod"] == "cekis_acik" and b["saglayici"] == "solis"
    assert ps._baglanti({"veri_yolu": {"tur": "scada_dosya"}})["kod"] == "dosya"
