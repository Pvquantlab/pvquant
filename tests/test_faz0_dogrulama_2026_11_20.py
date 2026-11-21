# -*- coding: utf-8 -*-
"""Faz 0 derin doğrulama (20.11.2026) — düşük riskli düzeltmelerin regresyon testleri:
P0-01 veri sınıfı + santral günü, P0-02 koordinat–dilim uyumu, P0-03 segment yokken EDT senaryo, P0-04 kalibrasyon damgası,
P0-06 boş «ok» sayımı, P0-07 durağan kota aşımı izi + iki kip, P0-08 başarısız giriş izi / 2FA yöntemi / önbellek düşürme."""
from __future__ import annotations

import datetime as dt
import re
import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from apps.api import main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant import zaman
from pvquant.services import durum_sozlugu as ds


# ------------------------------------------------------------------ P0-02
def test_tz_koordinat_uyumu():
    u = zaman.tz_koordinat_uyumu(-105.1772, "Europe/Istanbul", date(2026, 11, 20))   # Golden 33: Colorado + İstanbul
    assert u and u["fark_saat"] == 10.0 and "uyuşmuyor" in u["metin"] and "ölçümleri kaydırmaz" in u["metin"]
    assert zaman.tz_koordinat_uyumu(33.574, "Europe/Istanbul") is None            # Karapınar
    assert zaman.tz_koordinat_uyumu(-105.1772, "America/Denver") is None          # doğru dilim
    assert zaman.tz_koordinat_uyumu(None, "Europe/Istanbul") is None and zaman.tz_koordinat_uyumu(10, "Mars/Olympus") is None
    assert zaman.tz_koordinat_uyumu(0.0, "America/Denver", date(2026, 11, 20))["tz_ofset_saat"] == -7.0 and zaman.tz_koordinat_uyumu(0.0, "Australia/Sydney", date(2026, 11, 20))["tz_ofset_saat"] == 10.0   # QA Z-1: standart ofset işaretli küçük
    assert zaman.tz_koordinat_uyumu(float("nan"), "Europe/Istanbul") is None and zaman.tz_koordinat_uyumu(200, "Europe/Istanbul") is None   # inceleme: NaN/aralık dışı


# ------------------------------------------------------------------ P0-01
def test_santral_sinifi_sozlugu_ve_uygulanmiyor():
    # yeni iki alan + eski tek alanlı beyanın eşlenmesi
    g = ds.santral_sinifi({"santral_turu": "sanal_test", "veri_turu": "tarihsel_arsiv"})
    assert (g["santral_turu"], g["veri_turu"], g["tazelik_izlenir"]) == ("sanal_test", "tarihsel_arsiv", False) and "sanal test" in g["santral_turu_etiketi"]
    assert ds.santral_sinifi('{"veri_sinifi": "demo"}') == ds.santral_sinifi({"santral_turu": "sanal_test", "veri_turu": "yok"})
    assert ds.santral_sinifi({"veri_sinifi": "tarihsel"})["tazelik_izlenir"] is True and ds.santral_sinifi({"veri_sinifi": "tarihsel"})["veri_turu"] == "tarihsel_arsiv"
    assert ds.santral_sinifi({"santral_turu": "uydurma", "veri_turu": "x"}) == ds.santral_sinifi(None) and ds.santral_sinifi(None)["santral_turu"] == "operasyonel"
    simdi = dt.datetime(2026, 11, 20, 12, tzinfo=dt.timezone.utc)
    v = ds.veri_durumu_uygulanmiyor(g, dt.datetime(2019, 1, 1, tzinfo=dt.timezone.utc), None, simdi, kapsama_saat_7g=0)
    assert v["durum"] == "uygulanmiyor" and "sanal test santralı" in v["neden"] and "tarihsel arşiv" in v["neden"] and v["yas_saat"] and v["santral_turu"] == "sanal_test"
    # aynı damga operasyonel santralda KRİTİK (senaryo 1 korunur); en_kotu: uygulanmıyor hükme girmez
    assert ds.veri_durumu(dt.datetime(2019, 1, 1, tzinfo=dt.timezone.utc), None, simdi)["durum"] == "kritik"
    assert ds.en_kotu(["uygulanmiyor", "saglikli"]) == ds.Durum.SAGLIKLI
    src = open("src/pvquant/services/hizmet_sagligi_service.py", encoding="utf-8").read()
    assert 'if vsinif["tazelik_izlenir"]' in src and "veri_durumu_uygulanmiyor" in src
    assert "bugun_yerel = datetime.now(ZoneInfo(tz)).date()" in open("src/pvquant/services/ozet_service.py", encoding="utf-8").read()


@pytest.fixture()
def istemci(monkeypatch):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "editor", "exp": 0}
    from pvquant.services import plant_service
    depo = {"params_json": {}}
    monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": p, "name": "Deneme GES", "capacity_kwp": 2.4, "lat": 39.74, "lon": -105.18, "tz": "Europe/Istanbul", **depo})
    def birlestir(t, p, **k):
        depo["params_json"] = {**depo["params_json"], **k}; return depo["params_json"]
    monkeypatch.setattr(plant_service, "params_birlestir", birlestir)
    izler = []
    monkeypatch.setattr(api_main._denetim, "kaydet", lambda *a, **k: izler.append((a, k)) or True)
    monkeypatch.setattr(api_main._denetim, "ayar_degisikligi_kaydet", lambda *a, **k: izler.append((a, k)) or True)
    yield TestClient(api_main.app), depo, izler
    api_main.app.dependency_overrides.clear()


def test_santral_sinifi_ucu(istemci):
    c, depo, izler = istemci
    assert c.put("/v1/plants/p1/santral-sinifi", json={}).status_code == 422
    assert c.put("/v1/plants/p1/santral-sinifi", json={"santral_turu": "uydurma"}).status_code == 422
    assert c.put("/v1/plants/p1/santral-sinifi", json={"veri_turu": "uydurma"}).status_code == 422
    y = c.put("/v1/plants/p1/santral-sinifi", json={"santral_turu": "sanal_test", "veri_turu": "tarihsel_arsiv"})
    assert y.status_code == 200 and y.json()["santral_turu"] == "sanal_test" and y.json()["veri_turu"] == "tarihsel_arsiv" and y.json()["tazelik_izlenir"] is False
    assert depo["params_json"] == {"santral_turu": "sanal_test", "veri_turu": "tarihsel_arsiv"}
    y = c.put("/v1/plants/p1/santral-sinifi", json={"veri_turu": "sentetik"})   # kısmi: santral türü korunur
    assert y.status_code == 200 and y.json()["santral_turu"] == "sanal_test" and depo["params_json"]["veri_turu"] == "sentetik"
    assert any(a[0] == "santral_sinifi" for a, _ in izler)
    from pvquant.services.dengesizlik_service import segment_bilgisi
    sb = segment_bilgisi(depo["params_json"]); assert sb["santral_turu"] == "sanal_test" and sb["veri_turu"] == "sentetik"
    sb2 = segment_bilgisi({"segment": "lisansli_serbest"}); assert sb2["santral_turu"] == "operasyonel" and sb2["veri_turu"] == "canli"
    # QA C1-4: eski tek alanlı beyan varsa yazımda düşürülür, eşlenmiş değerler yeni alanlara taşınır
    depo["params_json"] = {"veri_sinifi": "demo"}
    y = c.put("/v1/plants/p1/santral-sinifi", json={"veri_turu": "sentetik"})
    assert y.status_code == 200 and depo["params_json"].get("veri_sinifi") is None and depo["params_json"]["santral_turu"] == "sanal_test" and depo["params_json"]["veri_turu"] == "sentetik"


# ------------------------------------------------------------------ P0-08
def test_giris_basarisiz_izi_ve_ikinci_adim_ayrintisi(istemci, monkeypatch):
    c, _, izler = istemci
    from pvquant.services import auth_service
    monkeypatch.setattr(auth_service, "giris", lambda e, s, k=None: None)
    monkeypatch.setattr(auth_service, "eposta_kiracisi", lambda e: "t-bulundu")
    monkeypatch.setattr(api_main, "paylasimli_sinir", lambda *a, **k: None)
    y = c.post("/v1/auth/login", json={"email": "x@y.z", "sifre": "p", "kod": "123456"})
    assert y.status_code == 401 and y.json()["detail"] == "hatali"   # yanıt değişmedi
    iz = next(k for a, k in izler if a == ("musteri", "giris_basarisiz"))
    assert iz["tenant_id"] == "t-bulundu" and iz["ayrinti"] == {"ikinci_adim_denendi": True} and "sifre" not in str(iz)
    # kurtarma koduyla başarılı giriş: ayrıntı + kalan sayısı
    from pvquant.services import iki_adim_service
    monkeypatch.setattr(auth_service, "giris", lambda e, s, k=None: {"token": "t", "user_id": "u1", "tenant_id": "t1", "role": "admin", "ikinci_adim": "kurtarma"})
    monkeypatch.setattr(iki_adim_service, "kurtarma_kalan", lambda u: 2)
    assert c.post("/v1/auth/login", json={"email": "x@y.z", "sifre": "p", "kod": "abcd-efgh"}).status_code == 200
    iz = next(k for a, k in izler if a == ("musteri", "giris"))
    assert iz["ayrinti"] == {"ikinci_adim": "kurtarma", "kurtarma_kalan": 2}
    assert "giris_basarisiz" in api_main._denetim.EYLEMLER_MUSTERI and "santral_sinifi" in api_main._denetim.EYLEMLER_MUSTERI and "abonelik_kota_asimi" in api_main._denetim.EYLEMLER_PLATFORM


def test_giris_dogrula_yontem_ve_onbellek(monkeypatch):
    from pvquant.services import iki_adim_service as ia
    monkeypatch.setattr(ia, "giris_dogrula_yontem", lambda u, k: "kurtarma")
    assert ia.giris_dogrula("u", "x") is True
    monkeypatch.setattr(ia, "giris_dogrula_yontem", lambda u, k: None)
    assert ia.giris_dogrula("u", "x") is False
    src = open(ia.__file__, encoding="utf-8").read()
    g = src[src.index("def giris_dogrula_yontem"):]; g = g[:g.find("\ndef ", 10)]
    assert 'return "yok"' in g and 'return "totp"' in g and 'return "kurtarma"' in g and "return True" not in g
    assert src.count("oturum_onbellegi_dusur(user_id)") >= 3   # dogrula_ve_ac, kapat, yonetici_sifirla
    a = open("src/pvquant/services/auth_service.py", encoding="utf-8").read()
    from pvquant.services import auth_service as au
    assert au.iki_adim_kurulmali("admin", False, True) is True and au.iki_adim_kurulmali("editor", False, True) is False and au.iki_adim_kurulmali("admin", True, True) is False
    assert a.count("iki_adim_kurulmali(") >= 3   # tek formül: tanım + giriş yanıtı + oturum_durumu


# ------------------------------------------------------------------ P0-03
def test_segment_yokken_edt_senaryo_niteliginde():
    from pvquant.services import dengesizlik_service as dsv
    from pvquant.services import finansal_etki_service as fe
    from test_finansal_etki_v2580 import _df, _fiyat, _izgara
    dn, iz = _izgara("2026-10"); pj = {}
    g = {"donem": dn, "izgara": iz, "df": _df(iz), "fiyat": _fiyat(iz), "kat": dsv.katsayilar(pj), "segment": None, "ariza_sayisi": 0,
         "luy_istisna": False, "bildirilen": None, "pozisyon": {"kaynak": "program", "sabit_mwh": None}, "pj": pj, "uretim": "scada", "pencere_gun": 45}
    pv, fo = fe.saatlik(g)
    out = fe.uzlastirma_bilesenleri_saf(g["donem"], g["izgara"], pv, fo, dsv.segment_bilgisi(pj), g["kat"], False, None, fe.dayanaklar(g["donem"], "lisansli_serbest"))
    edt = next(b for b in out["bilesenler"] if b["kod"] == fe.KOD_EDT)
    assert edt["nitelik"] == "senaryo" and any("segmenti seçilmedi" in n for n in edt["notlar"])
    kupst = next(b for b in out["bilesenler"] if b["kod"] == fe.KOD_KUPST)
    assert kupst["nitelik"] == "eksik" and kupst["toplanir"] is False
    # inceleme: veri yokken (bos) segment None → EDT «eksik» kalır, senaryo yazılmaz
    import pandas as pd
    out0 = fe.uzlastirma_bilesenleri_saf(g["donem"], g["izgara"], pd.DataFrame(), fo, dsv.segment_bilgisi(pj), g["kat"], False, None, fe.dayanaklar(g["donem"], "lisansli_serbest"))
    assert next(b for b in out0["bilesenler"] if b["kod"] == fe.KOD_EDT)["nitelik"] == "eksik"
    # segment varken EDT hesaplanan kalır
    pj2 = {"segment": "lisansli_serbest"}; g2 = {**g, "pj": pj2, "segment": "lisansli_serbest", "kat": dsv.katsayilar(pj2)}
    pv2, fo2 = fe.saatlik(g2)
    out2 = fe.uzlastirma_bilesenleri_saf(g2["donem"], g2["izgara"], pv2, fo2, dsv.segment_bilgisi(pj2), g2["kat"], False, None, fe.dayanaklar(g2["donem"], "lisansli_serbest"))
    assert next(b for b in out2["bilesenler"] if b["kod"] == fe.KOD_EDT)["nitelik"] == "hesaplanan"


# ------------------------------------------------------------------ P0-04
def test_kalibrasyon_kalite_kaydi_damgasi():
    src = open("src/pvquant/services/calib_service.py", encoding="utf-8").read()
    assert '"degerlendirme":       ("orneklem_ici+holdout" if holdout.get("mape_holdout_pct") is not None else "orneklem_ici")' in src and '"yazilim_surumu":      _ys()' in src   # C4-1: holdout varsa damga ikisini söyler
    web = open("web/src/features/sayfalar/Digerleri.tsx", encoding="utf-8").read()
    assert "Kalibrasyon uyum hatası (örneklem içi MAPE)" in web and "Kalibre model hatası (MAPE)" not in web


# ------------------------------------------------------------------ P0-06
def test_bos_ok_sayimi_siniflama():
    from pvquant.services import sistem_service as ss
    from test_sistem_sagligi_v2608 import ISLER_OK, SIMDI, _ozet
    o = _ozet(); o["isler_24"] = {"toplam": 40, "hata": 0, "bos_ok": 12}
    r = ss.sinifla(o, ISLER_OK, SIMDI)
    ih = r["bilesenler"]["sunucu"]["is_hatalari"]
    assert ih["durum"] == "dogrulanamadi" and "12 iş çıktı yazmadan bitti" in ih["neden"]
    assert "çıktı yazmadan bitti" in r["bilesenler"]["sunucu"]["neden"]   # inceleme: özet nedeni boş-ok'u söyler
    o["isler_24"] = {"toplam": 40, "hata": 0, "bos_ok": 0}
    assert ss.sinifla(o, ISLER_OK, SIMDI)["bilesenler"]["sunucu"]["is_hatalari"]["durum"] == "saglikli"
    o["isler_24"] = {"toplam": 40, "hata": 2, "bos_ok": 12}
    assert ss.sinifla(o, ISLER_OK, SIMDI)["bilesenler"]["sunucu"]["is_hatalari"]["durum"] == "dikkat"   # istisna önce gelir
    assert "AS bos_ok" in open(ss.__file__, encoding="utf-8").read()


@pytest.mark.skipif(not __import__("os").environ.get("PVQ_DB_URL"), reason="test DB gerekir")
def test_bos_ok_ozet_db():
    from pvquant.db import sistem_baglami
    from pvquant.services import sistem_service as ss
    ad = f"faz0_bos_{uuid.uuid4().hex[:6]}"
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO jobs_log(job, started, finished, status, detail) VALUES (:a, now(), now(), 'ok', ''), (:b, now(), now(), 'ok', 'dolu')"), {"a": ad + "_bos", "b": ad + "_dolu"})
    try:
        o = ss.ozet("faz0-test")
        assert o["isler_24"]["bos_ok"] >= 1 and o["isler_24"]["toplam"] >= 2
    finally:
        with sistem_baglami() as s:
            s.execute(text("DELETE FROM jobs_log WHERE job LIKE :j"), {"j": ad + "%"})


# ------------------------------------------------------------------ P0-07
@pytest.mark.skipif(not __import__("os").environ.get("PVQ_DB_URL"), reason="test DB gerekir")
def test_pilot_santral_kotasi_iki_kip_ve_duragan_asim_izi(monkeypatch):
    from apps.api import deps
    from pvquant.db import bakim_baglami, sistem_baglami
    from pvquant.services import abonelik_service as ab
    from pvquant.services import yetki_service as ys
    t, u = str(uuid.uuid4()), str(uuid.uuid4())
    try:
        with bakim_baglami() as s:   # CI tam takımı pvq_api rolüyle koşar; kurulum/temizlik DB sahibiyle (v2.606 kalıbı)
            s.execute(text("INSERT INTO tenants(id, name, status, plan) VALUES(:t, 'Faz0 kota', 'active', 'pilot')"), {"t": t})
            s.execute(text("INSERT INTO users(id, tenant_id, email, pw_hash, role, aktif, oturum_surumu) VALUES(:u, CAST(:t AS uuid), :e, 'x', 'admin', true, 0)"), {"u": u, "t": t, "e": f"faz0-{t[:8]}@example.invalid"})
            ab.varsayilan_olustur(s, t, "pilot", aktor="faz0", bugun=date.today())
            for i in range(4):   # göç öncesi oluşturulmuş 4 etkin santral kalıbı
                s.execute(text("INSERT INTO plants(tenant_id,name,lat,lon,tz,capacity_kwp) VALUES(CAST(:t AS uuid), :n, 37.5, 33.5, 'Europe/Istanbul', 1000)"), {"t": t, "n": f"faz0 s{i+1}"})
            s.execute(text("INSERT INTO plants(tenant_id,name,lat,lon,tz,capacity_kwp,archived) VALUES(CAST(:t AS uuid), 'faz0 arsiv', 37.5, 33.5, 'Europe/Istanbul', 1000, true)"), {"t": t})
        ys.onbellek_dusur(t)
        k = ys.haklar(t, taze=True)["kotalar"]["santral"]
        assert (k["limit"], k["kullanim"], k["durum"]) == (3, 4, "asildi")   # arşivli sayılmaz
        # durağan aşım: gece izi gün başına bir kez
        with sistem_baglami() as s:
            y1 = ab.kota_asimi_izi(s, tenant_id=t); y2 = ab.kota_asimi_izi(s, tenant_id=t)   # QA F-1: yalnız kendi kiracısı (öteki kiracılara iz yazılmaz)
            n_iz = s.execute(text("SELECT count(*) FROM denetim_izi WHERE eylem='abonelik_kota_asimi' AND tenant_id=CAST(:t AS uuid)"), {"t": t}).scalar()
        assert any(x["tenant_id"] == t and x["asilan"]["santral"]["kullanim"] == 4 for x in y1) and not any(x["tenant_id"] == t for x in y2) and n_iz == 1
        # uyarı kipi: iş yapılır + başlık + iz; zorla kipi: 409
        api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": u, "tenant_id": t, "role": "admin", "exp": 0}
        deps._uyari_izi.clear()
        c = TestClient(api_main.app)
        g = {"name": "faz0 s5 (uyari)", "lat": 37.5, "lon": 33.5, "tz": "Europe/Istanbul", "capacity_kwp": 1000}
        assert ys.zorlama_kipi() == "uyari"
        r = c.post("/v1/plants", json=g)
        assert r.status_code == 200 and r.headers.get("X-PVQuant-Abonelik-Kod") == "kota_asildi"
        ys.onbellek_dusur(t)
        monkeypatch.setattr(ys, "zorlama_kipi", lambda: "zorla")
        r = c.post("/v1/plants", json={**g, "name": "faz0 s6 (zorla)"})
        assert r.status_code == 409 and "kota" in str(r.json()["detail"]).lower()
    finally:
        api_main.app.dependency_overrides.pop(gecerli_kullanici, None)
        ys.onbellek_dusur()
        with bakim_baglami() as s:
            for tbl in ("santral_kunye", "plants", "denetim_izi", "abonelik_gecmisi", "kiraci_abonelik", "users"):
                s.execute(text(f"DELETE FROM {tbl} WHERE tenant_id = CAST(:t AS uuid)"), {"t": t})
            s.execute(text("DELETE FROM tenants WHERE id = CAST(:t AS uuid)"), {"t": t})


# ------------------------------------------------------------------ 21.11 demo bağlamı: sanal test santralında veri gecikmesi alarm değildir
def test_sanal_test_santralinda_veri_gelmedi_alarmi_uretilmez(monkeypatch):
    from pvquant.services import alarm_service as al
    class _S:
        def __init__(self, son): self.son = son
        def execute(self, q, *a, **k):
            class _R:
                def __init__(s_, v): s_.v = v
                def scalar(s_): return s_.v
                def fetchall(s_): return []
            sq = str(q)
            if "max(ts_utc)" in sq: return _R(self.son)
            if "interval '48 hours'" in sq: return _R(dt.datetime(2026, 11, 19, tzinfo=dt.timezone.utc))
            return _R(None)
        def __enter__(self): return self
        def __exit__(self, *a): return False
    eski = dt.datetime(2019, 1, 1, tzinfo=dt.timezone.utc)
    monkeypatch.setattr(al, "tenant_baglami", lambda tid: _S(eski))
    uretilen = []
    monkeypatch.setattr(al, "_kaydet_ve_gonder", lambda s, tid, pid, rule, msg, severity="uyari", plant=None: uretilen.append(rule))
    al.tara({"tenant_id": "t", "id": "p", "name": "PVDAQ Golden 33", "params_json": {"santral_turu": "sanal_test", "veri_turu": "tarihsel_arsiv"}})
    assert "veri_gelmedi" not in uretilen
    al.tara({"tenant_id": "t", "id": "p", "name": "eski beyan", "params_json": {"veri_sinifi": "demo"}})   # eski tek alanlı beyan da sanal test sayılır
    assert "veri_gelmedi" not in uretilen
    al.tara({"tenant_id": "t", "id": "p", "name": "operasyonel arşiv", "params_json": {"santral_turu": "operasyonel", "veri_turu": "tarihsel_arsiv"}})   # operasyonel santralda tazelik izlenir
    assert uretilen == ["veri_gelmedi"]
    al.tara({"tenant_id": "t", "id": "p", "name": "Gerçek GES", "params_json": {}})
    assert "veri_gelmedi" in uretilen


def test_askidaki_kiraci_girisi_izlenir(istemci, monkeypatch):
    c, _, izler = istemci
    from pvquant.services import auth_service
    def _giris(e, s, k=None): raise auth_service.KiraciAskida()
    monkeypatch.setattr(auth_service, "giris", _giris)
    monkeypatch.setattr(auth_service, "eposta_kiracisi", lambda e: "t-askida")
    monkeypatch.setattr(api_main, "paylasimli_sinir", lambda *a, **k: None)
    assert c.post("/v1/auth/login", json={"email": "x@y.z", "sifre": "p"}).status_code == 403
    iz = next(k for a, k in izler if a == ("musteri", "giris_basarisiz"))
    assert iz["ayrinti"] == {"neden": "kiraci_askida"} and iz["tenant_id"] == "t-askida"


# ------------------------------------------------------------------ 21.11 (onay): sanal test santralı durum göstergeleri
def test_sistem_listesi_sanal_test_bayraklari():
    from pvquant.services import sistem_service as ss
    simdi = dt.datetime(2026, 11, 21, 3, tzinfo=dt.timezone.utc)
    eski = dt.datetime(2019, 1, 1, tzinfo=dt.timezone.utc); taze = simdi - dt.timedelta(hours=1)
    sanal = ds.santral_sinifi({"santral_turu": "sanal_test", "veri_turu": "tarihsel_arsiv"}); sanal["segment"] = None
    op = ds.santral_sinifi({}); op["segment"] = None
    assert ss.sorun_bayraklari(sanal, eski, taze, "active", simdi) == ["sanal_test", "veri_tarihsel_arsiv"]
    assert ss.sorun_bayraklari(op, eski, taze, "active", simdi) == ["segment_yok", "scada_bayat"]   # operasyonel: değişmedi
    assert ss.sorun_bayraklari(op, None, None, "suspended", simdi) == ["segment_yok", "scada_yok", "kosu_yok", "kiraci_askida"]
    assert ss.sorun_bayraklari(sanal, None, None, "active", simdi) == ["sanal_test", "veri_tarihsel_arsiv", "kosu_yok"]   # tahmin bayrağı her türde
    op2 = ds.santral_sinifi({"veri_turu": "tarihsel_arsiv"}); op2["segment"] = "lisansli_serbest"
    assert ss.sorun_bayraklari(op2, eski, taze, "active", simdi) == ["veri_tarihsel_arsiv", "scada_bayat"]   # veri türü ≠ santral türü
    assert all(b in ss.BILGI_BAYRAKLARI for b in ("sanal_test", "veri_tarihsel_arsiv"))
    src = open(ss.__file__, encoding="utf-8").read()
    assert "sorunlar = sorun_bayraklari(sb," in src and "if x not in BILGI_BAYRAKLARI" in src


def test_nowcast_sanal_test_santralinda_katman_uygulanmaz():
    from pvquant.services import nowcast_service as ns
    y = ns.bayat_yaniti({"params_json": {"santral_turu": "sanal_test", "veri_turu": "tarihsel_arsiv"}})
    assert y["durum"] == "sanal_test" and "canlı SCADA beklenmez" in y["not"] and "tarihsel arşiv" in y["not"] and y["ufuk"] == []
    z = ns.bayat_yaniti({"params_json": {}})
    assert z["durum"] == "scada_bayat" and "katman devre dışı" in z["not"]   # operasyonel: değişmedi
    assert 'return {**ortak, **bayat_yaniti(plant)}' in open(ns.__file__, encoding="utf-8").read()
