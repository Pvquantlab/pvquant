# -*- coding: utf-8 -*-
"""v2.640 — Santralim derin işlevsel denetimi (20.11.2026), Parti 1: kritik + yüksek bulgular.
1 İşletme ayarları: GET /eak + yalnız dokunulan alan (form ön doldurması) · 2 UEVÇB boş dize siler ·
3 Referans CSV: atlanan satır bildirimi, yinelenen damga, saat içi toplama, negatif ret, UTC uyarısı, saat sonu ·
4 Saha toplayıcısı: damga makullüğü, negatif/aşırı değer, hatalı örnek ack'i durdurur; toplayıcı ≠ sunucu çekişi durumu; çekiş için sınama şartı."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from apps.api import main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.services import edge_service as es
from pvquant.services import pilot_service as ps
from pvquant.services import veri_yolu_service as vys

T0 = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------- 3 · referans CSV
def test_referans_csv_coz_bildirir_ve_toplar():
    metin = ("zaman,kwh\n"
             "abc,0.9\n"                               # çözümlenemeyen zaman → atlanır, bildirilir
             "2026-11-10T10:00:00+03:00,0.9\n"
             "2026-11-10T10:30:00+03:00,0.5\n"         # aynı saate düşen farklı damga → toplanır
             "2026-11-10T10:30:00+03:00,0.5\n"         # aynı dakika damgası → yinelenen, atlanır
             "2026-11-10T11:00:00+03:00,-1\n"          # negatif → reddedilir
             "2026-11-10 12:00,2\n"                    # saat dilimsiz → UTC varsayılır, sayılır
             ",\n")                                    # boş satır → sayılmaz
    out, meta = ps.referans_csv_coz(metin)
    assert [(r["ts_utc"].isoformat(), r["kwh"]) for r in out] == [("2026-11-10T07:00:00+00:00", 1.4), ("2026-11-10T12:00:00+00:00", 2.0)]
    assert meta["atlanan"] == 3 and meta["cift_satir"] == 1 and meta["negatif"] == 1 and meta["tzsiz"] == 1
    assert meta["toplanan_saat"] == 1 and meta["toplanan_satir"] == 2
    assert [e["satir"] for e in meta["atlanan_ornek"]] == [2, 5, 6]
    u = " | ".join(meta["uyarilar"])
    assert "3 satır atlandı" in u and "2. satır zaman çözümlenemedi" in u and "negatif kWh" in u and "UTC varsayıldı" in u and "saat içinde toplandı" in u
    # geriye uyumlu sarmal: uyarılar ilk satırda
    eski = ps.referans_csv_oku(metin)
    assert len(eski) == 2 and "3 satır atlandı" in eski[0]["_uyari"]


def test_referans_csv_saat_sonu_ve_hepsi_bozuk():
    out, meta = ps.referans_csv_coz("ts;kwh\n2026-11-10T11:00:00+03:00;1,5\n", saat_sonu=True)
    assert out[0]["ts_utc"].isoformat() == "2026-11-10T07:00:00+00:00" and "saat sonu" in meta["uyarilar"][0]
    with pytest.raises(ValueError, match="okunabilir satır yok .*2 satır atlandı: zaman çözümlenemedi"):
        ps.referans_csv_coz("ts,kwh\nx,1\ny,2\n")


# ---------------------------------------------------------------- 4 · edge örnek makullüğü ve ack
def _o(sira, **ek):
    return {"sira": sira, "ts_utc": (T0 - timedelta(minutes=5 * sira)).isoformat(), "cihaz_id": "inv1", "guc_w": 1000.0, **ek}


def test_ornek_dogrula_makulluk():
    es.ornek_dogrula(_o(1), T0, kap_w=2400.0)
    es.ornek_dogrula({**_o(1), "ts_utc": (T0 + timedelta(minutes=10)).isoformat()}, T0)          # 15 dk payı içinde
    for kotu, msg in (({**_o(1), "ts_utc": "2031-01-01T00:00:00Z"}, "gelecekte"),
                      ({**_o(1), "ts_utc": (T0 - timedelta(days=31)).isoformat()}, "30 günden eski"),
                      ({**_o(1), "guc_w": -5}, "negatif"), ({**_o(1), "enerji_wh": -1}, "negatif"),
                      ({**_o(1), "enerji_wh": 1e9}, "1,5 katını"), ({**_o(1), "kisit_yuzde": 140}, "kurulu gücün|negatif")):
        with pytest.raises(ValueError, match=msg):
            es.ornek_dogrula(kotu, T0, kap_w=2400.0)
    assert es.ornek_dogrula({**_o(1), "guc_w": 1e9}, T0)["guc_w"] == 1e9   # kap_w yoksa üst sınır yok (saf; al() santral kapasitesini verir)
    assert es.ornek_dogrula({**_o(1), "ts_utc": "2031-01-01T00:00:00Z"})["ts_utc"].year == 2031   # simdi yoksa pencere yok (eski saf çağrılar)


class _Defter:
    def __init__(self): self.d = {}
    def oku(self, siralar): return {s: self.d[s][0] for s in siralar if s in self.d}
    def yaz(self, sira, oz, ts): self.d[sira] = (oz, ts)


def test_al_hatali_ornek_acki_durdurur_ve_kapasite():
    top = {"id": "t1", "tenant_id": "ten", "plant_id": "pl", "ad": "saha"}; plant = {"id": "pl", "capacity_kwp": 2.4}
    yazilan = []
    r = es.al(top, plant, [_o(0), _o(1), {**_o(2), "guc_w": -3}, _o(3), {**_o(4), "guc_w": 50000}], T0, defter=_Defter(), yaz=yazilan.append, topla=False, guncelle=lambda *a: None)
    assert r["kabul"] == 3 and [h["sira"] for h in r["hatali"]] == [2, 4] and r["ack_sira"] == 1   # 2 hatalı → ack 1'de durur (3 kabul ama ack'e girmez)
    assert "1,5 katını" in r["hatali"][1]["hata"] and "negatif" in r["hatali"][0]["hata"]
    assert "Hatalı örnek ack'i durdurur" in r["not"]
    r2 = es.al(top, plant, [_o(5)], T0, defter=_Defter(), yaz=yazilan.append, topla=False, guncelle=lambda *a: None)
    assert r2["ack_sira"] == 5 and r2["hatali"] == []


def test_baglanti_durumu_toplayici_sunucu_cekisi_degil():
    beyan = {"tur": "modbus_sunspec", "baglanti": {"host": "10.0.0.2", "port": 502}, "ornekleme_acik": True}
    edge = [{"tur": "saha_toplayici", "son": "2026-11-20T11:55:00+00:00"}]
    d = vys.baglanti_durumu(beyan, edge)
    assert d["kod"] == "veri_akisi_toplayici" and "saha toplayıcısından" in d["etiket"] and "sunucu çekişi değil" in d["etiket"]
    assert vys.baglanti_durumu(beyan, [{"tur": "modbus_sunspec", "son": "2026-11-20T11:55:00+00:00"}])["kod"] == "veri_akisi"
    assert vys.baglanti_durumu({**beyan, "ornekleme_acik": False}, [])["kod"] == "sinanmadi"
    assert vys.baglanti_durumu({"tur": "scada_dosya"}, edge)["kod"] == "dosya"   # dosya kaynağında toplayıcı satırı durumu değiştirmez


# ---------------------------------------------------------------- 1 · 2 · 4 (api) — TestClient, DB'siz
@pytest.fixture()
def istemci(monkeypatch):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "editor", "exp": 0}
    from pvquant.services import plant_service
    depo = {"params_json": {"eak_kw": 2.0, "temizlik_maliyeti_tl": 100.0, "veri_yolu": {
        "tur": "modbus_sunspec", "baglanti": {"host": "10.0.0.2", "port": 502, "birim": 1}, "salt_okuma_onayi": True, "ornekleme_acik": False,
        "son_sinama": {"durum": "ok", "zaman": "2026-11-20T10:00:00+00:00", "ozet": {"yontem": "modbus"}}}}}
    monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": p, "capacity_kwp": 2.4, "ac_limit_kw": None, "lat": 39.0, "lon": 32.0, "tz": "Europe/Istanbul", **depo})
    def birlestir(t, p, **k):
        depo["params_json"] = {**depo["params_json"], **k}; return depo["params_json"]
    monkeypatch.setattr(plant_service, "params_birlestir", birlestir)
    monkeypatch.setattr(vys, "ozet", lambda t, row: {"beyan": (row.get("params_json") or {}).get("veri_yolu")})
    monkeypatch.setattr(api_main, "_ayar_izi", lambda *a, **k: None)
    monkeypatch.setattr(api_main._denetim, "kaydet", lambda *a, **k: None)
    yield TestClient(api_main.app), depo
    api_main.app.dependency_overrides.clear()


def test_eak_get_ve_yalniz_dokunulan_alan(istemci):
    c, depo = istemci
    g = c.get("/v1/plants/p1/eak").json()
    assert g["eak_kw"] == 2.0 and g["temizlik_maliyeti_tl"] == 100.0 and g["eak_bugun"]["kaynak"] == "eak_alani" and "pozisyon" in g
    # yalnız temizlik maliyeti gönderilir → EAK korunur (kritik bulgunun api tarafı: istek geçmeyen alan değişmez)
    y = c.put("/v1/plants/p1/eak", json={"temizlik_maliyeti_tl": 45000}).json()
    assert y["eak_kw"] == 2.0 and y["temizlik_maliyeti_tl"] == 45000.0 and y["eak_bugun"]["kaynak"] == "eak_alani"
    assert c.get("/v1/plants/p1/eak").json() == y


def test_uevcb_bos_dize_siler(istemci):
    c, depo = istemci
    assert c.put("/v1/plants/p1/segment", json={"segment": "lisansli_serbest", "uevcb": "40X000000000123"}).status_code == 200
    assert depo["params_json"]["uevcb"] == "40X000000000123"
    assert c.put("/v1/plants/p1/segment", json={"segment": "lisansli_serbest", "uevcb": "  "}).status_code == 200
    assert depo["params_json"]["uevcb"] is None
    c.put("/v1/plants/p1/segment", json={"segment": "lisansli_serbest"})            # verilmeyen alan dokunmaz
    assert "uevcb" in depo["params_json"] and depo["params_json"]["uevcb"] is None


def test_veri_yolu_son_sinama_korunur_ve_cekis_sarti(istemci):
    c, depo = istemci
    b = {"tur": "modbus_sunspec", "baglanti": {"host": "10.0.0.2", "port": 502, "birim": 1}, "salt_okuma_onayi": True}
    r = c.put("/v1/plants/p1/veri-yolu", json=b).json()                      # aynı tür + aynı bağlantı → sınama korunur
    assert r["beyan"]["son_sinama"]["durum"] == "ok"
    r = c.put("/v1/plants/p1/veri-yolu", json={**b, "ornekleme_acik": True}).json()   # sınama ok → çekiş açılır
    assert r["beyan"]["ornekleme_acik"] is True and r["beyan"]["son_sinama"]["durum"] == "ok"
    r = c.put("/v1/plants/p1/veri-yolu", json={**b, "baglanti": {"host": "10.0.0.9", "port": 502, "birim": 1}}).json()   # bağlantı değişti → sınama düşer
    assert "son_sinama" not in r["beyan"]
    y = c.put("/v1/plants/p1/veri-yolu", json={**b, "baglanti": {"host": "10.0.0.9", "port": 502, "birim": 1}, "ornekleme_acik": True})
    assert y.status_code == 422 and "önce bağlantı sınaması" in y.json()["detail"]


def test_edge_ornekler_hiz_siniri_ve_istek_parametresi():
    import inspect
    src = inspect.getsource(api_main.edge_ornekler)
    assert "request: Request" in src
    kaynak = open(api_main.__file__, encoding="utf-8").read()
    assert '@limiter.limit("120/minute")' in kaynak.split('def edge_ornekler(')[0][-400:]
