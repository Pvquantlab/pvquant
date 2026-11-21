"""Faz 0 §24 #3 (21.11.2026) — paylaşımlı hız sayacı (hiz_pencere) arızasında davranış: süreç içi yedek sayaç, uyarı/sağlık durumu,
eş zamanlılık, toparlanma. Çoğu test DB'siz (sayaç arızası monkeypatch ile); toparlanma testi test DB ister."""
from __future__ import annotations

import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy.exc import OperationalError, ProgrammingError

from apps.api import hiz
from pvquant.services import kullanim_service as ks

DB_VAR = bool(os.environ.get("PVQ_DB_URL"))


class _Kopuk:
    """sistem_baglami yerine: her girişte DB bağlantı hatası (yalnız hiz_pencere/sayaç yolu için)."""
    def __enter__(self):
        raise OperationalError("connect", {}, Exception("hiz_pencere erişilemez (sentetik)"))
    def __exit__(self, *a):
        return False


class _TabloYok:
    """S2 taklidi: ifade hatası — SQLAlchemy str(e) içine ifadeyi ve parametreleri (hesap anahtarı = e-posta) ekler (R3 QA itiraz 1)."""
    def __enter__(self):
        raise ProgrammingError("INSERT INTO hiz_pencere(anahtar, pencere, adet) VALUES (:a, :p, 1)",
                               {"a": "ygiris-hesap:sahip-gizli@example.invalid", "p": "2026-11-21"},
                               Exception('relation "hiz_pencere" does not exist\nLINE 1: INSERT INTO hiz_pencere'))
    def __exit__(self, *a):
        return False


@pytest.fixture(autouse=True)
def _temiz():
    hiz.yedek_sifirla()
    ks._SAYAC.update({"hata_sayisi": 0, "son_hata": None, "son_hata_turu": None, "son_basari": None, "_son_uyari": 0.0})
    yield
    hiz.yedek_sifirla()


def _istemci(monkeypatch, giris, *, ip_siniri=False):
    from fastapi.testclient import TestClient

    from apps.api import main as api_main
    from apps.api import yonetim as yo
    from pvquant.services import platform_service as ps
    if not ip_siniri:
        monkeypatch.setattr(yo, "paylasimli_sinir", lambda *a, **k: None)
    monkeypatch.setattr(yo.limiter, "enabled", False)
    monkeypatch.setattr(ps, "giris", giris)
    monkeypatch.setattr(yo.dz, "kaydet", lambda *a, **k: True)
    return TestClient(api_main.app)


def test_1_sayac_arizasi_0_doner_durum_sagliksiz_uyari_tek(monkeypatch, caplog):
    monkeypatch.setattr(ks, "sistem_baglami", lambda: _Kopuk())
    with caplog.at_level("WARNING", logger="pvq.hiz"):
        assert ks.pencere_say("r3:x", 60) == 0 and ks.pencere_oku("r3:x", 60) == 0
        ks.pencere_azalt("r3:x", 60)
    d = ks.sayac_durumu()
    assert d["saglikli"] is False and d["hata_sayisi"] == 3 and d["son_hata_turu"] == "OperationalError" and d["son_hata"]
    assert sum("[hiz] pencere" in r.message for r in caplog.records) == 1          # dakikada en çok bir uyarı
    assert "sentetik" in caplog.text and "yedek sayaç devrede" in caplog.text
    n, yedek = hiz._say("r3:x", 60)
    assert (n, yedek) == (1, True)


def test_1b_gunluk_ifade_ve_parametre_sizdirmaz(monkeypatch, caplog):
    """R3 QA itiraz 1: tablo/GRANT/kilit hatasında günlük yalnız DBAPI iç hatasının ilk satırını yazar; anahtar/e-posta/[SQL:/[parameters: yok."""
    monkeypatch.setattr(ks, "sistem_baglami", lambda: _TabloYok())
    with caplog.at_level("WARNING", logger="pvq.hiz"):
        assert ks.pencere_say("ygiris-hesap:sahip-gizli@example.invalid", 60) == 0
    assert 'relation "hiz_pencere" does not exist' in caplog.text and "ProgrammingError" in caplog.text
    for yasak in ("sahip-gizli", "example.invalid", "[SQL:", "[parameters:", "INSERT INTO", "LINE 1"):
        assert yasak not in caplog.text, yasak
    assert ks.sayac_durumu()["son_hata_turu"] == "ProgrammingError"
    assert ks.hata_ozeti(ProgrammingError("SELECT 1", {"a": "gizli@x"}, Exception("x [SQL: SELECT 1] [parameters: {'a': 'gizli@x'}]"))) == "x"
    assert len(ks.hata_ozeti(Exception("a" * 500))) == 200
    assert ks.hata_ozeti(Exception("\n\n  gercek satir\nikinci")) == "gercek satir" and ks.hata_ozeti(Exception("")) == "Exception"   # QA r3b notu


def test_2_hesap_siniri_yedekte_calisir_kapı_kapanmaz(monkeypatch):
    monkeypatch.setattr(ks, "sistem_baglami", lambda: _Kopuk())
    e = f"r3-{uuid.uuid4().hex[:6]}@example.invalid"
    def _giris(email, sifre, kod=None):
        return {"token": "t", "rol": "sahip", "email": email, "iki_adim_kurulmali": False} if sifre == "dogru" else None
    c = _istemci(monkeypatch, _giris)
    assert all(c.post("/v1/yonetim/giris", json={"email": e, "sifre": "dogru"}).status_code == 200 for _ in range(5))   # kapı açık, başarı sayılmaz
    kodlar = [c.post("/v1/yonetim/giris", json={"email": e, "sifre": "yanlis"}).status_code for _ in range(11)]
    assert kodlar == [401] * 10 + [429]                                                  # yedek sayaç aynı tavanı uygular
    assert c.post("/v1/yonetim/giris", json={"email": e, "sifre": "dogru"}).status_code == 429   # kilitliyken doğru parola da 429
    anahtar = ks.hesap_anahtari("ygiris-hesap", e)
    assert hiz._YEDEK[anahtar][1] == 10                                                  # reddedilenler eklenmedi


def test_3_yedekte_es_zamanli_denemeler_tavani_asamaz(monkeypatch):
    monkeypatch.setattr(ks, "sistem_baglami", lambda: _Kopuk())
    e = f"r3-yaris-{uuid.uuid4().hex[:6]}@example.invalid"
    c = _istemci(monkeypatch, lambda email, sifre, kod=None: None)
    with ThreadPoolExecutor(max_workers=20) as ex:
        kodlar = sorted(ex.map(lambda _: c.post("/v1/yonetim/giris", json={"email": e, "sifre": "x"}).status_code, range(20)))
    assert kodlar == [401] * 10 + [429] * 10


def test_4_ip_penceresi_yedekte_calisir(monkeypatch):
    monkeypatch.setattr(ks, "sistem_baglami", lambda: _Kopuk())
    c = _istemci(monkeypatch, lambda email, sifre, kod=None: None, ip_siniri=True)
    kodlar = [c.post("/v1/yonetim/giris", json={"email": f"r3-ip-{i}@example.invalid", "sifre": "x"}).status_code for i in range(6)]
    assert kodlar == [401] * 5 + [429]                                                   # 5/dk/IP yedekte de uygulanır


def test_5_pencere_hizasi_ve_sure_sonu():
    assert hiz._yedek_say("r3:p", 1) == 1 and hiz._yedek_say("r3:p", 1) == 2
    hiz._yedek_azalt("r3:p", 1)
    assert hiz._YEDEK["r3:p"][1] == 1
    time.sleep(1.1)
    assert hiz._yedek_say("r3:p", 1) == 1                                                # yeni pencere → sıfırdan
    assert hiz._pencere_basi(900) == int(ks.pencere_basi(__import__("datetime").datetime.now(__import__("datetime").timezone.utc), 900).timestamp())


def test_6_bellek_tavani_kilitli_anahtari_korur(monkeypatch):
    """R3 QA itiraz 2: tavan aşımında en düşük adetli anahtarlar atılır; 10 başarısızlıkla kilitli hesap anahtarı (adet 10) ve o anki anahtar korunur."""
    monkeypatch.setattr(hiz, "YEDEK_AZAMI_ANAHTAR", 50)
    for _ in range(10):
        hiz._yedek_say("ygiris-hesap:kilitli-sahip@example.invalid", 900)                    # saldırgan sahibi kilitledi
    for i in range(80):
        hiz._yedek_say(f"r3:tavan:{i}", 900)                                                 # sonra sözlüğü farklı e-postalarla doldurdu
    assert len(hiz._YEDEK) <= 50
    assert hiz._YEDEK["ygiris-hesap:kilitli-sahip@example.invalid"][1] == 10                  # kilit sıfırlanmadı (en eski olmasına rağmen)
    assert "r3:tavan:79" in hiz._YEDEK                                                        # o anki anahtar hiç atılmaz
    assert hiz._yedek_say("ygiris-hesap:kilitli-sahip@example.invalid", 900) == 11


def test_7_sistem_sagligi_bileseni():
    from pvquant.services import sistem_service as ss
    from tests.test_sistem_sagligi_v2608 import ISLER_OK, SIMDI, _ozet
    o = _ozet()
    o["hiz_sayaci"] = {"saglikli": True, "son_hata": None, "son_hata_turu": None, "hata_sayisi": 0, "son_basari": "2026-11-21T04:00:00+00:00"}
    r = ss.sinifla(o, ISLER_OK, SIMDI)["bilesenler"]["veritabani"]
    assert r["hiz_sayaci"]["durum"] == "saglikli"
    o["hiz_sayaci"] = {"saglikli": False, "son_hata": "2026-11-21T04:01:00+00:00", "son_hata_turu": "OperationalError", "hata_sayisi": 7, "son_basari": None}
    r = ss.sinifla(o, ISLER_OK, SIMDI)["bilesenler"]["veritabani"]
    assert r["hiz_sayaci"]["durum"] == "dikkat" and "yedek sayaç devrede" in r["hiz_sayaci"]["neden"] and r["durum"] == "dikkat"
    assert "yanıtı üreten işçi" in r["hiz_sayaci"]["neden"] and "4×" not in r["hiz_sayaci"]["neden"]   # QA itiraz 4
    assert "OperationalError" in r["neden"]                                              # özet nedeni sayaç arızasını söyler
    o2 = _ozet()
    o2.pop("hiz_sayaci", None)
    assert "hiz_sayaci" not in ss.sinifla(o2, ISLER_OK, SIMDI)["bilesenler"]["veritabani"]   # eski özet biçimi bozulmaz


@pytest.mark.skipif(not DB_VAR, reason="test DB gerekir")
def test_8_toparlanma_db_donunce_paylasimli_sayac_surer(monkeypatch):
    anahtar = f"r3:topar:{uuid.uuid4().hex[:6]}"
    orijinal = ks.sistem_baglami
    monkeypatch.setattr(ks, "sistem_baglami", lambda: _Kopuk())
    assert hiz._say(anahtar, 900) == (1, True) and ks.sayac_durumu()["saglikli"] is False
    monkeypatch.setattr(ks, "sistem_baglami", orijinal)                                   # DB döndü
    try:
        n, yedek = hiz._say(anahtar, 900)
        assert (n, yedek) == (1, False) and ks.sayac_durumu()["saglikli"] is True       # paylaşımlı sayaç sürer; durum düzelir
        assert hiz._say(anahtar, 900) == (2, False)
    finally:
        ks.pencere_sil(anahtar)
