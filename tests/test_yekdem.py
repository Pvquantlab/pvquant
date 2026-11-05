"""v2.520 (P5a) — YEKDEM katmanı: TCMB kur arşivi (çözümleme, tatil taşıması, aylık ortalama, eksik iş günü, worker işi), fiyat rejimi
türetme, 7189 aylık ilan + USD band konumu, gün bazlı fiyat serisi (Cetvel I günlük kur / 7189 ilan + yerli katkı süresi / elle kur yedeği),
m.23(6) saat işareti, döküm ek sütunları, tarife doğrulama/yapı, müşteri ve platform API uçları, iş kayıtları.
DB'li testler yerel test DB'sini kullanır (2099 ve 2040 yılları; test sonunda silinir)."""
from __future__ import annotations

import datetime as dt
from datetime import date

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from pvquant.db import sistem_baglami
from pvquant.services import kur_service as ks, yekdem_service as ys, tarife_service as tsv, dengesizlik_service as dz, piyasa_service as ps

XML = """<?xml version="1.0" encoding="UTF-8"?>
<Tarih_Date Tarih="30.10.2026" Date="10/30/2026"  Bulten_No="2026/204" >
  <Currency CrossOrder="0" Kod="USD" CurrencyCode="USD"><Unit>1</Unit><Isim>ABD DOLARI</Isim><ForexBuying>49.7747</ForexBuying><ForexSelling>49.8644</ForexSelling></Currency>
  <Currency CrossOrder="9" Kod="EUR" CurrencyCode="EUR"><Unit>1</Unit><Isim>EURO</Isim><ForexBuying>55.7149</ForexBuying></Currency>
  <Currency CrossOrder="3" Kod="JPY" CurrencyCode="JPY"><Unit>100</Unit><ForexBuying>32.1</ForexBuying></Currency>
</Tarih_Date>"""


def _xml(gun: date, usd: float = 50.0) -> str:
    return XML.replace("30.10.2026", gun.strftime("%d.%m.%Y")).replace("10/30/2026", gun.strftime("%m/%d/%Y")).replace("49.7747", f"{usd:.4f}")


def _temizle():
    with sistem_baglami() as s:
        s.execute(text("DELETE FROM doviz_kuru WHERE gun >= '2098-01-01'"))
        s.execute(text("DELETE FROM yekdem_fiyat WHERE ay >= '2040-01-01' OR ay = '2026-07-01'"))


# ---------------- kur ----------------
def test_xml_coz_ve_indir_sahte_istemci():
    k = ks.xml_coz(XML)
    assert k == {"gun": date(2026, 10, 30), "usd_alis": 49.7747, "eur_alis": 55.7149, "bulten": "2026/204"}
    assert ks.xml_coz("<bozuk") is None and ks.xml_coz(XML.replace("ForexBuying>49.7747", "ForexBuying>")) is None   # USD yoksa None
    def istemci(url):
        if url.endswith("today.xml"):
            return 200, XML
        if url.endswith("/202610/30102026.xml"):
            return 200, XML
        if url.endswith("/202610/29102026.xml"):
            return 200, XML                                   # dosya adı 29.10, içerik 30.10 → yazılmaz
        if url.endswith("/202610/31102026.xml"):
            return 404, ""                                    # cumartesi
        return 500, "hata"
    assert ks.indir(None, istemci)["gun"] == date(2026, 10, 30)
    assert ks.indir(date(2026, 10, 30), istemci)["usd_alis"] == 49.7747
    assert ks.indir(date(2026, 10, 31), istemci) is None and ks.indir(date(2026, 10, 29), istemci) is None
    with pytest.raises(RuntimeError):
        ks.indir(date(2026, 10, 1), istemci)


def test_kur_serisi_tatil_ve_hafta_sonu_onceki_is_gunu():
    """Bülteni olmayan gün (hafta sonu, tatil, henüz yayımlanmamış) önceki iş gününün kurunu taşır ve işaretlenir; hiç veri yoksa kur_yok."""
    arsiv = pd.DataFrame({"usd_alis": [49.6, 49.7747], "eur_alis": [55.0, 55.7], "bulten": ["a", "b"]}, index=pd.to_datetime(["2026-10-29", "2026-10-30"]))
    s = ks.kur_serisi(date(2026, 10, 29), date(2026, 11, 2), arsiv=arsiv)
    assert list(s["kaynak"]) == ["tcmb", "tcmb", "tcmb_onceki_gun", "tcmb_onceki_gun", "tcmb_onceki_gun"]
    assert s.loc["2026-11-01", "kur"] == 49.7747 and s.loc["2026-11-01", "kur_gunu"] == pd.Timestamp("2026-10-30") and bool(s.loc["2026-11-01", "onceki_gun"])
    assert not bool(s.loc["2026-10-30", "onceki_gun"])
    bos = ks.kur_serisi(date(2026, 10, 1), date(2026, 10, 3), arsiv=arsiv.iloc[0:0])
    assert list(bos["kaynak"]) == ["kur_yok"] * 3 and bos["kur"].isna().all()


def test_kur_db_kaydet_aylik_ortalama_eksik_ve_gunluk_isi():
    try:
        _temizle()
        assert ks.kaydet({"gun": date(2099, 1, 5), "usd_alis": 100.0, "eur_alis": 110.0, "bulten": "2099/1"}) == 1     # pazartesi
        ks.kaydet({"gun": date(2099, 1, 6), "usd_alis": 102.0, "eur_alis": None, "bulten": "2099/2"})
        ks.kaydet({"gun": date(2099, 1, 6), "usd_alis": 104.0, "eur_alis": None, "bulten": "2099/2b"})                # üzerine yazar
        df = ks.oku(date(2099, 1, 1), date(2099, 1, 31)); assert list(df["usd_alis"]) == [100.0, 104.0] and pd.isna(df["eur_alis"].iloc[1])
        o = ks.aylik_ortalama(date(2099, 1, 15)); assert (o["ay"], o["ortalama"], o["gun"], o["beklenen"]) == ("2099-01", 102.0, 2, 21) and "2099-01-07" in o["eksik_gun"] and "2099-01-01" not in o["eksik_gun"]
        assert ks.aylik_ortalama(date(2098, 12, 1)) is None
        assert ks.eksik_is_gunleri(date(2099, 1, 5), date(2099, 1, 11)) == [date(2099, 1, 7), date(2099, 1, 8), date(2099, 1, 9)]   # 10–11 hafta sonu
        s = ks.kur_serisi(date(2099, 1, 5), date(2099, 1, 8)); assert list(s["kaynak"]) == ["tcmb", "tcmb", "tcmb_onceki_gun", "tcmb_onceki_gun"]
        # worker işi: today.xml 9.1.2099 bültenini verir, arşivde 7–8 Ocak yok (404) → bulunamayan listesi; ikinci koşu 0 yeni
        def istemci(url):
            if url.endswith("today.xml"):
                return 200, _xml(date(2099, 1, 9), 106.0)
            return 404, ""
        m = ks.gunluk(bugun=date(2099, 1, 10), geri_gun=5, istemci=istemci)
        assert m.startswith("yeni 1 bülten") and "2099-01-07, 2099-01-08" in m and "106.0000" in m
        assert ks.gunluk(bugun=date(2099, 1, 10), geri_gun=5, istemci=istemci).startswith("yeni 0 bülten")
        d = ks.durum(date(2099, 1, 12)); assert d["son_gun"] == "2099-01-09" and d["son_usd_alis"] == 106.0 and "2099-01-07" in d["eksik_is_gunu_30"]
        with pytest.raises(ValueError):
            ks.geri_doldur(date(2099, 1, 1), date(2097, 1, 1))
        with pytest.raises(ValueError):
            ks.geri_doldur(date(2098, 1, 1), date(2099, 12, 31))
    finally:
        _temizle()


def test_bulten_gunu_yarim_gunler():
    """TCMB yarım gün tatillerde (28 Ekim, bayram arefesi) bülten yayımlamaz; takvim modülü bunları iş günü sayar, kur arşivi beklemez."""
    assert ks.bulten_gunu(date(2026, 10, 30)) and ks.bulten_gunu(date(2026, 3, 18))                      # cuma, çarşamba
    assert not ks.bulten_gunu(date(2026, 10, 28)) and not ks.bulten_gunu(date(2026, 10, 29))            # arefe yarım gün, Cumhuriyet Bayramı
    assert not ks.bulten_gunu(date(2026, 3, 19)) and not ks.bulten_gunu(date(2026, 5, 26))              # Ramazan ve Kurban arefesi
    assert not ks.bulten_gunu(date(2026, 10, 31)) and not ks.bulten_gunu(date(2026, 5, 27))             # cumartesi, bayram


# ---------------- rejim ----------------
def test_ilk_doldurma_arsiv_kisaysa(monkeypatch):
    """Worker ilk koşuda arşiv 13 aydan kısaysa geriye tamamlar (sahte istemci: arşiv dosyaları 404 → istek sayısı bülten günü sayısı); yeterince
    geriye gidiyorsa hiç istek yapmaz."""
    istekler = []
    def istemci(url):
        istekler.append(url); return (200, _xml(date(2099, 6, 12), 101.0)) if url.endswith("today.xml") else (404, "")
    monkeypatch.setattr(ks, "ilk_gun", lambda: date(2099, 6, 1))                       # arşiv 11 gün geriye gidiyor → tamamla
    monkeypatch.setattr(ks, "mevcut_gunler", lambda bas, bit: set())
    monkeypatch.setattr(ks, "kaydet", lambda k: 1)
    r = ks.ilk_doldurma(date(2099, 6, 12), istemci)
    assert r is not None and r["bas"] == "2098-05-09" and r["bit"] == "2099-06-11" and r["yazilan"] == 0 and len(r["bulunamayan"]) == len(istekler) > 250
    monkeypatch.setattr(ks, "ilk_gun", lambda: date(2098, 5, 1))                       # yeterince geriye gidiyor → None
    istekler.clear(); assert ks.ilk_doldurma(date(2099, 6, 12), istemci) is None and not istekler
    monkeypatch.setattr(ks, "ilk_gun", lambda: None)                                   # boş arşiv → tamamla
    assert ks.ilk_doldurma(date(2099, 6, 12), istemci)["bas"] == "2098-05-09"


def test_rejim_turet():
    assert ys.rejim_turet({"isletmeye_giris": "2017-05-10"})["rejim"] == "cetvel1"
    assert ys.rejim_turet({"isletmeye_giris": "2021-06-30"})["rejim"] == "cetvel1"
    r = ys.rejim_turet({"isletmeye_giris": "2021-07-01"}); assert r["rejim"] == "7189" and r["kaynak_turu"] == "hesaplanan" and "1.7.2021" in r["kaynak"]
    assert ys.rejim_turet({"isletmeye_giris": "2030-12-31"})["rejim"] == "7189"
    assert ys.rejim_turet({"isletmeye_giris": "2031-01-01"})["rejim"] is None and ys.rejim_turet({})["etiket"] == "belirsiz"
    r = ys.rejim_turet({"isletmeye_giris": "2017-05-10", "tarife": {"tip": "yekdem", "rejim": "7189", "tesis_tipi": "gunes_depolamali"}})
    assert r["rejim"] == "7189" and r["kaynak_turu"] == "kullanici" and r["tesis_tipi"] == "gunes_depolamali"     # elle seçim tarihi ezer
    assert ys.rejim_turet({"params_json": '{"isletmeye_giris": "2019-01-01"}'})["rejim"] == "cetvel1"             # plant satırı / str json


# ---------------- 7189 ilan + band ----------------
def test_fiyat_kaydet_listele_ve_bant():
    try:
        _temizle()
        y = ys.fiyat_kaydet("2040-03", "gunes", 500, 120, "EPİAŞ duyurusu 01.03.2040 deneme", bugun=date(2040, 3, 2))
        assert y["ay"] == "2040-03" and y["fiyat_kr_kwh"] == 500.0 and y["yerli_katki_kr_kwh"] == 120.0 and y["kaynak"] == "EPİAŞ duyurusu 01.03.2040 deneme"
        y2 = ys.fiyat_kaydet("2040-03-01", "gunes", 510, None, "EPİAŞ duyurusu 2040-03-01", bugun=date(2040, 3, 2)); assert y2["fiyat_kr_kwh"] == 510.0 and y2["yerli_katki_kr_kwh"] is None   # üzerine yazar
        # kaynak zorunlu, tarihli ve bugünden sonra olamaz (01.11 incelemesi: «kaynak 02.11.2026, kayıt 01.11.2026» satırı)
        for kaynak in (None, "", "EPİAŞ duyurusu", "EPİAŞ duyurusu 02.11.2026"):
            with pytest.raises(ValueError):
                ys.fiyat_kaydet("2040-03", "gunes", 500, None, kaynak, bugun=date(2026, 11, 1))
        assert ys.kayit_durumu({"kaynak": "EPİAŞ duyurusu 01.10.2026", "guncelleme": "2026-11-01T00:00:00+00:00"}, date(2026, 11, 1))["durum"] == "resmi"
        assert ys.kayit_durumu({"kaynak": "EPİAŞ duyurusu 02.11.2026", "guncelleme": "2026-11-01T00:00:00+00:00"}, date(2026, 11, 5))["durum"] == "dogrulanmamis"
        assert ys.kayit_durumu({"kaynak": "EPİAŞ duyurusu 02.11.2026", "guncelleme": "2026-11-02T00:00:00+00:00"}, date(2026, 11, 1))["neden"].startswith("kaynak tarihi")
        assert ys.kayit_durumu({"kaynak": "telefonla alındı 01.10.2026", "guncelleme": None}, date(2026, 11, 1))["durum"] == "elle"
        assert ys.kayit_durumu({"kaynak": None}, date(2026, 11, 1))["durum"] == "dogrulanmamis" and ys.kayit_durumu({"kaynak": "EPİAŞ"}, date(2026, 11, 1))["neden"] == "kaynakta duyuru tarihi yok"
        # 01.11 ikinci inceleme: 01.10.2026 duyurusu Kasım 2026 fiyatını içeremez → kayıtta reddedilir, durumda «doğrulanmadı»
        with pytest.raises(ValueError, match="geçerli dönemden"):
            ys.fiyat_kaydet("2040-03", "gunes", 500, None, "EPİAŞ duyurusu 01.10.2026", bugun=date(2040, 3, 2))
        assert ys.kayit_durumu({"ay": "2026-11", "kaynak": "EPİAŞ duyurusu 01.10.2026", "guncelleme": "2026-11-01T00:00:00+00:00"}, date(2026, 11, 1))["durum"] == "dogrulanmamis"
        assert ys.kayit_durumu({"ay": "2026-10", "kaynak": "EPİAŞ duyurusu 01.10.2026", "guncelleme": "2026-11-01T00:00:00+00:00"}, date(2026, 11, 1))["durum"] == "resmi"
        assert ys.kayit_durumu({"ay": "2026-08", "kaynak": "EPİAŞ duyurusu 01.10.2026", "guncelleme": "2026-11-01T00:00:00+00:00"}, date(2026, 11, 1))["durum"] == "resmi"   # geriye dönük sütun
        assert ys.aylik_fiyat(date(2040, 3, 15), "gunes")["fiyat_kr_kwh"] == 510.0 and ys.aylik_fiyat("2040-04", "gunes") is None
        assert [f["ay"] for f in ys.fiyat_listesi("gunes")][0] == "2040-03"
        for kotu in (("2040-3", "gunes", 500), ("2020-01", "gunes", 500), ("2040-03", "ruzgar", 500), ("2040-03", "gunes", 0), ("2040-03", "gunes", "x")):
            with pytest.raises(ValueError):
                ys.fiyat_kaydet(*kotu, None, "EPİAŞ duyurusu 01.03.2040", bugun=date(2040, 3, 2))
        with pytest.raises(ValueError):
            ys.fiyat_kaydet("2040-03", "gunes", 500, -1, "EPİAŞ duyurusu 01.03.2040", bugun=date(2040, 3, 2))
    finally:
        _temizle()
    # band: kr/kWh ÷ (TL/USD) = ¢/kWh; sınırlar 4,95–6,05 (depolamalı 5,85–7,15)
    assert ys.bant_kontrol(date(2026, 10, 1), "gunes", 289.74, kur_ort=49.0)["durum"] == "icinde"
    b = ys.bant_kontrol("2026-10", "gunes", 296.45, kur_ort=49.0); assert b["durum"] == "tavanda" and b["kur_ayi"] == "2026-09" and b["tavan_kr"] == 296.45
    assert ys.bant_kontrol("2026-10", "gunes", 240.0, kur_ort=49.0)["durum"] == "tabanda"
    assert ys.bant_kontrol("2026-10", "gunes_depolamali", 341.74, kur_ort=49.0)["durum"] == "icinde"
    assert ys.bant_kontrol("2026-10", "gunes", 289.74, kur_ort=None, kur_ara=False)["durum"] == "kur_yok"


# ---------------- gün bazlı fiyat serisi ----------------
def test_gunluk_fiyat_serisi_cetvel1_7189_ve_yedek_kur():
    try:
        _temizle()
        ks.kaydet({"gun": date(2099, 1, 5), "usd_alis": 100.0, "eur_alis": None, "bulten": "x"})
        # Cetvel I: 13,3 ¢ × 10 × kur; 6 Ocak bülteni yok → önceki iş günü; yerli katkı 5 yıl (giriş 2094-01-05 → 2099-01-05'ten sonra düşer)
        pj = {"isletmeye_giris": "2094-01-06", "tarife": {"tip": "yekdem", "yerli_katki_usd_cent": 1.0}}
        pj["tarife"]["rejim"] = "cetvel1"
        s = ys.gunluk_fiyat_serisi(pj, date(2099, 1, 5), date(2099, 1, 6))
        assert list(s["kaynak"]) == ["tcmb", "tcmb_onceki_gun"] and list(s["yek_tl_mwh"]) == [13300.0, 13300.0] and list(s["yerli_tl_mwh"]) == [1000.0, 0.0]   # 13,3 ¢ × 10 × 100 TL
        assert list(s["toplam_tl_mwh"]) == [14300.0, 13300.0] and s["kur_gunu"].iloc[1] == "2099-01-05"
        g = ys.gun_fiyati(pj, date(2099, 1, 6)); assert g["toplam_tl_mwh"] == 13300.0 and g["onceki_gun"] and g["kur"] == 100.0
        # kur yok, elle kur 40 → yedek
        s2 = ys.gunluk_fiyat_serisi({**pj, "tarife": {**pj["tarife"], "kur_tl_usd": 40}}, date(2098, 6, 1), date(2098, 6, 1))
        assert s2["kaynak"].iloc[0] == "elle" and s2["yek_tl_mwh"].iloc[0] == 5320.0
        assert ys.gunluk_fiyat_serisi(pj, date(2098, 6, 1), date(2098, 6, 1))["kaynak"].iloc[0] == "kur_yok" and ys.gun_fiyati(pj, date(2098, 6, 1))["toplam_tl_mwh"] is None
        # 7189: ayın ilanı × 10 (+ yerli katkı 5 yıl); ilan edilmemiş ay → önceki ay; tohum Ekim 2026 (göç)
        ekim = ys.aylik_fiyat("2026-10", "gunes"); assert ekim and ekim["fiyat_kr_kwh"] == 289.74 and ekim["yerli_katki_kr_kwh"] == 78.74
        pj7 = {"isletmeye_giris": "2022-03-01", "tarife": {"tip": "yekdem", "yerli_katki": True}}
        s7 = ys.gunluk_fiyat_serisi(pj7, date(2026, 10, 31), date(2026, 10, 31))
        assert s7["kaynak"].iloc[0] == "epias_ilan" and abs(s7["toplam_tl_mwh"].iloc[0] - (2897.4 + 787.4)) < 1e-6 and s7["ay_fiyat_kr_kwh"].iloc[0] == 289.74
        pj7b = {"isletmeye_giris": "2021-08-01", "tarife": {"tip": "yekdem", "yerli_katki": True}}     # yerli katkı 1.8.2026'da bitti
        assert ys.gunluk_fiyat_serisi(pj7b, date(2026, 10, 31), date(2026, 10, 31))["toplam_tl_mwh"].iloc[0] == 2897.4
        s31 = ys.gunluk_fiyat_serisi(pj7, date(2031, 12, 1), date(2031, 12, 1)); assert s31["kaynak"].iloc[0] == "onceki_ay" and s31["yek_tl_mwh"].iloc[0] > 0
        assert ys.gunluk_fiyat_serisi(pj7, date(2045, 1, 1), date(2045, 1, 1))["kaynak"].iloc[0] == "sure_doldu"   # v2.532: 10 yıl doldu (DK-285)
        assert ys.gunluk_fiyat_serisi({"tarife": {"tip": "yekdem"}}, date(2026, 10, 31), date(2026, 10, 31))["kaynak"].iloc[0] == "rejim_yok"
        assert ys.saatlik_yek_fiyati(pj7, pd.date_range("2026-10-30 21:00", periods=3, freq="h", tz="UTC")).round(1).tolist() == [3684.8] * 3
    finally:
        _temizle()


# ---------------- m.23(6) ----------------
def _pv():
    idx = pd.date_range("2026-10-20 06:00", periods=7, freq="h", tz="UTC")
    return pd.DataFrame({"ptf": [50, 50, 2000, 50, 50, 50, 10], "smf": [40, 40, 1900, 40, 40, 40, 5], "yon": ["fazla", "acik", "fazla", "fazla", "fazla", "fazla", "fazla"],
                         "kgup": [5.0] * 7, "gerceklesen": [6, 6, 6, 4, 6, 6, 7], "program_kaynak": ["bildirilen", "oneri", "oneri", "oneri", "oneri", "oneri", "oneri"]}, index=idx)


def test_m23_6_isaretle_ve_ozet():
    pv = _pv(); yek = pd.Series([3000.0, 3000.0, 3000.0, 3000.0, 40.0, np.nan, 3000.0], index=pv.index)
    e = ys.m23_6_isaretle(pv, yek)
    assert list(e["m23_6"]) == ["evet", "hayir", "hayir", "hayir", "ptf_yek_ustu", "fiyat_yok", "evet"]   # yön açık / fiyat V üstü / program altı / PTF ≥ YEK / fiyat yok
    assert e["yekdem_disi_mwh"].tolist() == [1.0, 0, 0, 0, 0, 0, 2.0]
    assert abs(e["yekdem_disi_tl"].iloc[0] - 1.0 * (3000 - 0.98 * 50)) < 1e-9 and abs(e["yekdem_disi_tl"].iloc[6] - 2.0 * (3000 - 0.98 * 10)) < 1e-9
    o = ys.m23_6_ozeti(pv, e, 30)
    assert o["saat"] == 2 and o["aday_saat"] == 4 and o["yekdem_disi_mwh"] == 3.0 and o["bildirilmemis_saat"] == 1 and o["etiket"] == "belirsiz"
    assert o["ilk_saat"] == "2026-10-20 09:00" and o["son_saat"] == "2026-10-20 15:00" and "19.10.2026" in o["not"]
    # 19.10.2026 öncesi kapsam dışı
    pv2 = pv.copy(); pv2.index = pv2.index - pd.Timedelta(days=10)
    assert set(ys.m23_6_isaretle(pv2, yek.set_axis(pv2.index))["m23_6"]) == {"kapsam_disi"}
    assert ys.m23_6_isaretle(pv.iloc[0:0], yek.iloc[0:0]).empty


def test_dokum_yekdem_sutunlari():
    """Döküm: YEKDEM eki varsa 25 sütun (CSV/XLSX/not dâhil); yoksa 21 sütun değişmez."""
    ts = pd.date_range("2026-10-20", periods=48, freq="h", tz="Europe/Istanbul").tz_convert("UTC")
    g = np.clip(np.sin((np.asarray(ts.tz_convert("Europe/Istanbul").hour) - 6) / 12 * np.pi), 0, None) * 8000
    df = pd.DataFrame({"ts_utc": ts, "gercek_kw": g * 1.1, "kgup_kw": g, "naif_kw": g})
    f = ps.senaryo_fiyat(ts); f["ptf"] = 50.0; f["smf"] = 40.0; f["yon"] = "fazla"; f["kaynak"] = "epias"
    pv, _, _, _ = dz.saatlik_hesap(df, f, segment="lisansli_yekdem")
    ek = ys.m23_6_isaretle(pv, pd.Series(3000.0, index=pv.index))
    dk = dz.dokum_df(pv, ek)
    assert list(dk.columns) == dz.DOKUM_KOLONLAR + dz.YEKDEM_KOLONLAR and (dk["yekdem_disi_mwh"] >= 0).all() and "evet" in set(dk["m23_6"])
    assert dk["yekdem_disi_mwh"].sum() > 0 and dz.dokum_notu(dk).endswith("yaklaşık.") and "m23_6" not in dz.dokum_notu(dz.dokum_df(pv))
    csv = dz.dokum_csv(dk); assert ";m23_9_tl\n" in csv.split("\n")[1] + "\n" and csv.count("\n") == len(dk) + 2
    x = dz.dokum_xlsx(dk, "test"); assert x[:2] == b"PK"
    assert list(dz.dokum_df(pv).columns) == dz.DOKUM_KOLONLAR and list(dz.dokum_df(pv, ek.iloc[0:0]).columns) == dz.DOKUM_KOLONLAR
    assert dz.yekdem_eki({"tarife": {"tip": "sabit"}}, "lisansli_yekdem", pv) is None and dz.yekdem_eki({"tarife": {"tip": "yekdem"}}, "lisansli_serbest", pv) is None


# ---------------- tarife ----------------
def test_tarife_dogrula_ve_yapi_yekdem():
    assert tsv.dogrula({"tip": "yekdem", "usd_cent_kwh": 7.3, "kur_tl_usd": 40}) == {"tip": "yekdem", "rejim": "otomatik", "tesis_tipi": "gunes", "usd_cent_kwh": 7.3, "kur_tl_usd": 40.0, "yerli_katki": False, "eskalasyon_yillik": 0.0}
    t = tsv.dogrula({"tip": "yekdem", "rejim": "7189", "tesis_tipi": "gunes_depolamali", "yerli_katki": True}); assert t["rejim"] == "7189" and t["yerli_katki"] and "usd_cent_kwh" not in t
    assert tsv.dogrula({"tip": "yekdem", "rejim": "cetvel1", "yerli_katki_usd_cent": 0})["yerli_katki_usd_cent"] == 0.0
    for kotu in ({"tip": "yekdem", "rejim": "x"}, {"tip": "yekdem", "tesis_tipi": "ruzgar"}, {"tip": "yekdem", "usd_cent_kwh": 150}, {"tip": "yekdem", "kur_tl_usd": -1}, {"tip": "yekdem", "yerli_katki_usd_cent": 25}, {"tip": "yekdem", "usd_cent_kwh": "abc"}):
        with pytest.raises(ValueError):
            tsv.dogrula(kotu)
    # yapı: plant yok → ¢ × elle kur (eski); ikisi de yok → anlaşılır hata; plant + ilan → gün bazlı seri
    from pvquant.ext.platform import tarife as tf
    assert isinstance(tsv.yapi({"tip": "yekdem", "usd_cent_kwh": 7.3, "kur_tl_usd": 40}).tarife, tf.Yekdem)
    with pytest.raises(ValueError, match="TCMB kuru"):
        tsv.yapi({"tip": "yekdem", "rejim": "otomatik"})
    plant = {"id": "p", "params_json": {"isletmeye_giris": "2022-03-01", "tarife": {"tip": "yekdem"}}}
    y = tsv.yapi({"tip": "yekdem"}, plant=plant, bas=date(2026, 10, 30), bit=date(2026, 10, 31)); assert isinstance(y.tarife, tf.YekdemSeri)
    idx = pd.date_range("2026-10-30 21:00", periods=4, freq="h", tz="UTC")
    g = tsv.gelir_df(pd.Series(1000.0, index=idx), {"tip": "yekdem"}, plant=plant)
    assert g["fiyat_tl_mwh"].round(2).tolist() == [2897.4] * 4 and abs(g["gelir_tl"].sum() - 4 * 2897.4) < 1e-6
    assert tsv.ortalama_fiyat_tl_mwh({"tip": "yekdem", "usd_cent_kwh": 7.3, "kur_tl_usd": 40}) == 2920.0 and tsv.ortalama_fiyat_tl_mwh({"tip": "yekdem"}) is None
    assert tsv.ortalama_fiyat_tl_mwh({"tip": "yekdem"}, plant=plant) == 2897.4 or tsv.ortalama_fiyat_tl_mwh({"tip": "yekdem"}, plant=plant) > 0   # bugünün ilanı (ay ilan edilmemişse önceki ay)


# ---------------- API ----------------
PLANT = "22222222-2222-2222-2222-222222222222"


@pytest.fixture()
def istemci(monkeypatch):
    import apps.api.main as api_main
    from apps.api.deps import gecerli_kullanici
    from pvquant.services import plant_service
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "admin", "exp": 0}
    depo = {"params_json": {"segment": "lisansli_yekdem", "isletmeye_giris": "2022-03-01", "tarife": {"tip": "yekdem", "yerli_katki": True}}}
    monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": p, "name": "X", "params_json": depo["params_json"]} if p == PLANT else None)
    monkeypatch.setattr(dz, "saatlik_pv", lambda tenant_id, plant, gun=90: _pv())   # DB'siz: sentetik saatlik hesap
    yield TestClient(api_main.app)
    api_main.app.dependency_overrides.clear()


def test_api_yekdem_ucu(istemci):
    r = istemci.get(f"/v1/plants/{PLANT}/yekdem?gun=30"); assert r.status_code == 200, r.text
    j = r.json()
    assert j["uygulanir"] and j["tarife_yekdem"] and j["rejim"]["rejim"] == "7189" and j["fiyat"]["kaynak"] in ("epias_ilan", "onceki_ay") and j["fiyat"]["toplam_tl_mwh"] > 0
    assert j["m23_6"]["etiket"] == "belirsiz" and j["m23_6"]["pencere_gun"] == 30 and j["m23_6"]["saat"] >= 1 and j["aylar"] and j["sabitler"]["j"] == 0.98
    assert istemci.get(f"/v1/plants/{PLANT}/yekdem?gun=5").status_code == 422
    assert istemci.get("/v1/plants/00000000-0000-0000-0000-000000000000/yekdem").status_code == 404


def test_api_yonetim_yekdem_uclari(monkeypatch):
    import jwt as _jwt
    import apps.api.main as api_main
    from pvquant.services import auth_service as au, platform_service as pls, denetim_service as dsv
    monkeypatch.setenv("PVQ_JWT_SECRET", "test-sirri-0123456789abcdef-uzun")
    kayitlar = []
    monkeypatch.setattr(dsv, "kaydet", lambda *a, **k: kayitlar.append((a, k)) or True)
    monkeypatch.setattr(pls, "oturum_durumu", lambda p: {"sv": 0, "aktif": True, "rol": "operator", "email": "o@pvq", "totp_aktif": True})
    jeton = {"Authorization": "Bearer " + _jwt.encode({"sub": "p1", "kapsam": "platform", "rol": "operator", "sv": 0, "exp": dt.datetime.utcnow() + dt.timedelta(hours=1)}, au._sir(), algorithm="HS256")}
    c = TestClient(api_main.app)
    try:
        _temizle()
        assert c.put("/v1/yonetim/yekdem-fiyat", json={"ay": "2026-07", "tesis_tipi": "gunes", "fiyat_kr_kwh": 600, "kaynak": "EPİAŞ duyurusu"}, headers=jeton).status_code == 422   # tarihsiz kaynak
        assert c.put("/v1/yonetim/yekdem-fiyat", json={"ay": "2040-05", "tesis_tipi": "gunes", "fiyat_kr_kwh": 600, "kaynak": "EPİAŞ duyurusu 01.10.2026"}, headers=jeton).status_code == 422   # dönemden önceki duyuru
        r = c.put("/v1/yonetim/yekdem-fiyat", json={"ay": "2026-07", "tesis_tipi": "gunes", "fiyat_kr_kwh": 600, "yerli_katki_kr_kwh": 150, "kaynak": "EPİAŞ duyurusu 01.10.2026"}, headers=jeton)
        assert r.status_code == 200, r.text
        assert r.json()["fiyat_kr_kwh"] == 600.0
        assert kayitlar and kayitlar[-1][0][:2] == ("platform", "yekdem_fiyat") and kayitlar[-1][1]["ayrinti"]["ay"] == "2026-07"
        assert c.put("/v1/yonetim/yekdem-fiyat", json={"ay": "2026-07", "tesis_tipi": "ruzgar", "fiyat_kr_kwh": 600, "kaynak": "EPİAŞ duyurusu 01.10.2026"}, headers=jeton).status_code == 422
        g = c.get("/v1/yonetim/yekdem", headers=jeton); assert g.status_code == 200
        satir = next(f for f in g.json()["fiyatlar"] if f["ay"] == "2026-07"); assert satir["bant"]["durum"] in ("kur_yok", "icinde", "tavanda") and satir["kayit"]["durum"] == "resmi" and g.json()["kur"]["kaynak"].startswith("TCMB")
        assert isinstance(g.json()["bekleyen"], list)
        assert g.json()["kaynaklar"]["epias_url"].startswith("https://www.epias.com.tr/") and g.json()["kaynaklar"]["tcmb_url"].startswith("https://www.tcmb.gov.tr/")
        assert c.get("/v1/yonetim/yekdem").status_code in (401, 422)                                       # jetonsuz
        monkeypatch.setattr(ks, "geri_doldur", lambda bas, bit, istemci=None: {"yazilan": 2, "bulunamayan": [], "bas": bas.isoformat(), "bit": bit.isoformat()})
        d = c.post("/v1/yonetim/kur-doldur", json={"bas": "2026-10-01", "bit": "2026-10-31"}, headers=jeton); assert d.status_code == 200 and d.json()["yazilan"] == 2
        assert kayitlar[-1][0][:2] == ("platform", "kur_doldur")
        monkeypatch.setattr(ks, "geri_doldur", lambda bas, bit, istemci=None: (_ for _ in ()).throw(RuntimeError("TCMB 503")))
        assert c.post("/v1/yonetim/kur-doldur", json={"bas": "2026-10-01", "bit": "2026-10-31"}, headers=jeton).status_code == 502
    finally:
        _temizle()
        pls.oturum_onbellegi_dusur(); au.oturum_onbellegi_dusur()


def test_isci_isi_sozluk_ve_izleme():
    from pvquant.services import isler_service, sistem_service, denetim_service
    assert "gece_kur" in isler_service.ISIM_TR and any(k == "gece_kur" for k, *_ in sistem_service.IZLENEN_ISLER)
    assert {"yekdem_fiyat", "kur_doldur"} <= set(denetim_service.EYLEMLER_PLATFORM)
