# -*- coding: utf-8 -*-
"""v2.641 — Santralim denetimi Parti 3 (düşük bulgular): sensör gelecek tarih + tekillik, EAK 0,1 kW, geçici kısıt eksik alan/geçmiş bitiş,
sabit pozisyon MWh'siz, referans CSV 31 gün, G05/G06 test referansı, toplayıcı listesi göç ayrımı, bulut hata sınıfı, adres filtresi."""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from apps.api import main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.services import bulut_sinama_service as bs
from pvquant.services import canli_alim_service as ca
from pvquant.services import edge_service as es
from pvquant.services import performans_service as ps
from pvquant.services import pilot_service as pls


# ---------------------------------------------------------------- sensör
def test_sensor_gelecek_tarih_ve_tekillik():
    yarin = (date.today() + timedelta(days=1)).isoformat()
    with pytest.raises(ValueError, match="gelecekte olamaz"):
        ps.sensor_dogrula({"tur": "piranometre", "olcum": "poa", "kalibrasyon_tarihi": yarin})
    ps.sensor_dogrula({"tur": "piranometre", "olcum": "poa", "kalibrasyon_tarihi": date.today().isoformat()})   # bugün olur
    a = {"tur": "piranometre", "olcum": "poa", "seri_no": "SN-1"}
    with pytest.raises(ValueError, match="yinelenen sensör: piranometre/poa seri no sn-1"):
        ps.sensorler_dogrula([a, {**a, "seri_no": "sn-1"}])   # büyük/küçük harf duyarsız
    # seri numarasız iki aynı tür sensör serbest; farklı ölçüm aynı seri serbest
    assert len(ps.sensorler_dogrula([{"tur": "piranometre", "olcum": "poa"}, {"tur": "piranometre", "olcum": "poa"},
                                     {"tur": "meteo_istasyonu", "olcum": "t_air", "seri_no": "M1"}, {"tur": "meteo_istasyonu", "olcum": "wind", "seri_no": "M1"}])) == 4


# ---------------------------------------------------------------- referans 31 gün
def test_referans_csv_31_gun_siniri():
    satirlar = ["zaman,kwh"] + [f"2026-10-{g:02d}T10:00:00+03:00,1" for g in range(1, 32)]
    out, _ = pls.referans_csv_coz("\n".join(satirlar))
    assert len(out) == 31
    with pytest.raises(ValueError, match="en çok 31 gün"):
        pls.referans_csv_coz("zaman,kwh\n2026-10-01T10:00:00+03:00,1\n2026-11-02T10:00:00+03:00,1\n")


# ---------------------------------------------------------------- G05/G06 referansı
def test_kod_kapilari_test_referansi_tasir():
    d = pls.durum({"params_json": {}})
    kod = {k["kod"]: k for k in d["kapilar"]}
    assert kod["G05"]["tamam"] and "tests/test_sunspec_7xx_v2551.py" in kod["G05"]["not"] and "CI" in kod["G05"]["not"]
    assert "tests/test_v3_v5_v2558.py" in kod["G06"]["not"]
    assert kod["G01"]["not"] is None   # saha kapısının notu sahibin beyanı


# ---------------------------------------------------------------- toplayıcı listesi
def test_toplayici_listele_goc_yoksa_bos_baska_hata_yukselir(monkeypatch):
    from pvquant import db as _db
    class _Ctx:
        def __init__(self, e): self.e = e
        def __enter__(self): raise self.e
        def __exit__(self, *a): return False
    monkeypatch.setattr(_db, "tenant_baglami", lambda t: _Ctx(RuntimeError('relation "edge_toplayici" does not exist')))
    assert es.toplayici_listele("t", "p") == []
    monkeypatch.setattr(_db, "tenant_baglami", lambda t: _Ctx(RuntimeError("connection refused")))
    with pytest.raises(RuntimeError, match="connection refused"):
        es.toplayici_listele("t", "p")


# ---------------------------------------------------------------- bulut hata sınıfı
def test_bulut_hata_sinifi_ham_mesaj_sizmaz():
    class ReadTimeout(Exception):
        pass
    assert bs.hata_sinifi(ReadTimeout("https://user:parola@api.x/giris timed out")) == "zaman aşımı"
    assert bs.hata_sinifi(ConnectionError("x")) == "bağlantı kurulamadı"
    assert bs.hata_sinifi(KeyError("data")) == "yanıt beklenen biçimde değil"
    assert bs.hata_sinifi(RuntimeError("token=gizli")) == "beklenmeyen hata: RuntimeError"
    class _Istemci:
        def __init__(self, bolge, transport=None): pass
        def giris(self, k): raise RuntimeError("https://api.x/?token=GIZLI")
        def kapat(self): pass
    import pvquant.services.bulut_sinama_service as m
    kod = next(iter(m.AKTIF_SAGLAYICILAR))
    sg = {**m.AKTIF_SAGLAYICILAR[kod], "sinif": _Istemci}
    orijinal = m.AKTIF_SAGLAYICILAR[kod]
    m.AKTIF_SAGLAYICILAR[kod] = sg
    try:
        r = bs.sina(kod, {a: "x" for a in sg["kimlik_alanlari"]}, True)
    finally:
        m.AKTIF_SAGLAYICILAR[kod] = orijinal
    assert r["durum"] == "baglanti_hatasi" and "GIZLI" not in r["aciklama"] and r["hata_sinifi"] == "RuntimeError"


# ---------------------------------------------------------------- adres filtresi
def test_adres_izinli_docker_blogu_ve_sunucu_adresi(monkeypatch):
    monkeypatch.delenv("PVQ_SAHA_YASAK_CIDR", raising=False); monkeypatch.delenv("PVQ_SAHA_IZINLI_CIDR", raising=False)
    monkeypatch.setattr(ca, "_sunucu_adresleri", lambda: {ca.ipaddress.ip_address("10.9.9.9")})
    assert ca.adres_izinli("172.17.0.2")[0] is False and "docker" in ca.adres_izinli("172.17.0.2")[1]
    assert ca.adres_izinli("100.64.1.1")[0] is False
    assert ca.adres_izinli("10.9.9.9") == (False, "hedef adres sunucunun kendi adresi; sahadaki cihaz ya da VPN adresi gerekir")
    assert ca.adres_izinli("10.8.0.12") == (True, "özel ağ (VPN) adresi") and ca.adres_izinli("8.8.8.8") == (True, "genel adres")
    monkeypatch.setenv("PVQ_SAHA_IZINLI_CIDR", "172.20.0.0/16")   # sahanın VPN'i docker bloğunda → delik
    assert ca.adres_izinli("172.20.5.5") == (True, "izinli özel ağ (VPN) adresi") and ca.adres_izinli("172.17.0.2")[0] is False
    monkeypatch.setenv("PVQ_SAHA_YASAK_CIDR", "")   # yasak liste boşaltılabilir
    assert ca.adres_izinli("172.17.0.2")[0] is True


# ---------------------------------------------------------------- api: EAK / geçici kısıt / pozisyon / sensör ucu
@pytest.fixture()
def istemci(monkeypatch):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "editor", "exp": 0}
    from pvquant.services import plant_service
    depo = {"params_json": {"eak_gecici": {"kw": 1500.0, "bitis": "2099-01-01"}, "pozisyon_kaynagi": "program"}}
    monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": p, "name": "Deneme GES", "capacity_kwp": 2400.0, "ac_limit_kw": None, "lat": 39.0, "lon": 32.0, "tz": "Europe/Istanbul", **depo})
    def birlestir(t, p, **k):
        depo["params_json"] = {**depo["params_json"], **k}; return depo["params_json"]
    monkeypatch.setattr(plant_service, "params_birlestir", birlestir)
    monkeypatch.setattr(api_main._denetim, "kaydet", lambda *a, **k: None)
    yield TestClient(api_main.app), depo
    api_main.app.dependency_overrides.clear()


def test_eak_hassasiyet_gecici_kisit_ve_sabit_pozisyon(istemci):
    c, depo = istemci
    r = c.put("/v1/plants/p1/eak", json={"eak_kw": 1234.5678})
    assert r.status_code == 200 and depo["params_json"]["eak_kw"] == 1234.6
    # yalnız kW değişir → mevcut bitişle birleşir (sessiz silme yok)
    assert c.put("/v1/plants/p1/eak", json={"gecici_kw": 1000}).status_code == 200 and depo["params_json"]["eak_gecici"] == {"kw": 1000.0, "bitis": "2099-01-01"}
    # ikisi de boş → kaldır
    assert c.put("/v1/plants/p1/eak", json={"gecici_kw": None, "gecici_bitis": None}).status_code == 200 and depo["params_json"]["eak_gecici"] is None
    # mevcut kısıt yokken yalnız kW → 422
    r = c.put("/v1/plants/p1/eak", json={"gecici_kw": 900})
    assert r.status_code == 422 and "birlikte gerekir" in r.json()["detail"]
    r = c.put("/v1/plants/p1/eak", json={"gecici_kw": 900, "gecici_bitis": "2020-01-01"})
    assert r.status_code == 422 and "geçmişte" in r.json()["detail"]
    yarin = (date.today() + timedelta(days=2)).isoformat()
    assert c.put("/v1/plants/p1/eak", json={"gecici_kw": 900.04, "gecici_bitis": yarin}).status_code == 200 and depo["params_json"]["eak_gecici"] == {"kw": 900.0, "bitis": yarin}
    # sabit pozisyon MWh'siz
    r = c.put("/v1/plants/p1/eak", json={"pozisyon_kaynagi": "sabit"})
    assert r.status_code == 422 and "pozisyon_sabit_mwh" in r.json()["detail"]
    r = c.put("/v1/plants/p1/eak", json={"pozisyon_kaynagi": "sabit", "pozisyon_sabit_mwh": None})
    assert r.status_code == 422
    assert c.put("/v1/plants/p1/eak", json={"pozisyon_kaynagi": "sabit", "pozisyon_sabit_mwh": 1.2}).status_code == 200
    r = c.put("/v1/plants/p1/eak", json={"pozisyon_sabit_mwh": None})   # kaynak sabitken MWh silinemez
    assert r.status_code == 422
    assert c.put("/v1/plants/p1/eak", json={"pozisyon_kaynagi": "program", "pozisyon_sabit_mwh": None}).status_code == 200


def test_sensorler_ucu_tekillik_422(istemci):
    c, _ = istemci
    s = {"tur": "piranometre", "olcum": "poa", "seri_no": "A1", "sinif": "A"}
    r = c.put("/v1/plants/p1/sensorler", json={"sensorler": [s, s]})
    assert r.status_code == 422 and "yinelenen sensör" in r.json()["detail"]
    assert c.put("/v1/plants/p1/sensorler", json={"sensorler": [s]}).status_code == 200
