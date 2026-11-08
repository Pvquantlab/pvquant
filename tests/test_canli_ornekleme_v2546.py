"""v2.546 (P4b-2): Modbus TCP / SunSpec düzenli örnekleme + saatlik toplama; son temizlik tarihi referansı; dosya yükleme sıklığı eşiği.
Dış sisteme dokunulmaz: cihaz sahte istemciyle, DB yazımları sahte fonksiyonlarla."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pandas as pd
import pytest

from pvquant.services import canli_ornekleme_service as co
from pvquant.services import kirlenme_service as ks
from pvquant.services import veri_yolu_service as vy

T0 = datetime(2026, 11, 8, 9, 0, tzinfo=timezone.utc)


def _plant(**vyk):
    vyb = {"tur": "modbus_sunspec", "baglanti": {"host": "10.8.0.12", "port": 502, "birim": 1}, "salt_okuma_onayi": True, "ornekleme_acik": True, "periyot_dk": 15}
    vyb.update(vyk)
    return {"id": "p1", "tenant_id": "t1", "name": "X", "params_json": {"veri_yolu": vyb}}


def test_uygun_sartlari_ve_periyot():
    assert co.uygun(_plant())[0]
    assert co.uygun(_plant(ornekleme_acik=False))[1] == "düzenli veri çekişi başlatılmadı"
    assert co.uygun(_plant(salt_okuma_onayi=False))[1] == "yalnızca veri okuma onayı yok"
    assert co.uygun(_plant(baglanti=None))[1] == "bağlantı ayarı yok"
    assert co.uygun({"params_json": {}})[1] == "hedef Modbus TCP / SunSpec değil"
    assert co.periyot_dk({"periyot_dk": None}) == 15 and co.periyot_dk({"periyot_dk": "5"}) == 5 and co.periyot_dk({"periyot_dk": 99999}) == 1440


def test_saatlik_ozet_sayac_farki_ortalama_ve_yetersiz():
    saat = T0
    ts = [saat + timedelta(minutes=m) for m in (0, 15, 30, 45)]
    df = pd.DataFrame({"ts_utc": ts, "guc_w": [100000, 110000, 120000, 130000], "enerji_wh": [5_000_000, 5_025_000, 5_052_000, 5_085_000]})
    oz = co.saatlik_ozet(df, saat)
    assert oz["nitelik"] == "sayac" and oz["energy_kwh"] == pytest.approx(85.0) and oz["power_kw"] == pytest.approx(115.0) and oz["n"] == 4 and oz["kapsama_dk"] == 45.0
    df2 = df.assign(enerji_wh=None)                                       # sayaç yok → ortalama güç × kapsanan süre
    oz2 = co.saatlik_ozet(df2, saat)
    assert oz2["nitelik"] == "ortalama" and oz2["energy_kwh"] == pytest.approx(115.0 * 45 / 60)
    df3 = df.copy(); df3.loc[2, "enerji_wh"] = 4_000_000                    # sayaç geri sayıyor (sıfırlama) → sayaç farkı kullanılmaz
    assert co.saatlik_ozet(df3, saat)["nitelik"] == "ortalama"
    assert co.saatlik_ozet(df.head(1), saat) is None                      # tek örnek
    assert co.saatlik_ozet(df.head(2), saat) is None                      # 15 dk kapsama < 40
    assert co.saatlik_ozet(df, saat + timedelta(hours=1)) is None          # başka saat


def test_tur_periyot_ve_hata_izolasyonu():
    yazilan, son = [], {"ts": None}
    class SahteIstemci:
        def __init__(self, host, port, birim, za): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def oku(self, adres, adet):
            if adres == 40000: return [0x5375, 0x6E53]
            if adres == 40002: return [1, 66]
            if adres == 40070: return [103, 50]
            if adres == 40122: return [0xFFFF, 0]
            if adres == 40004: return [0] * 66
            if adres == 40072:   # model 103: A, AphA,B,C, A_SF, PPV×3, PhV×3, V_SF, W, W_SF, Hz, Hz_SF, VA, VA_SF, VAr, VAr_SF, PF, PF_SF, WH hi/lo, WH_SF, DCA, DCA_SF, DCV, DCV_SF, DCW, DCW_SF, Tmp×4, Tmp_SF, St, StVnd, Evt1 hi/lo
                r = [1500, 500, 500, 500, 0xFFFF, 400, 400, 400, 230, 230, 230, 0, 9876, 1, 5000, 0xFFFE, 0, 0, 0, 0, 0, 0,
                     0x7A, 0x1200, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4, 0, 0, 0]   # W 98.760 W (sf 1), Hz 50,00, WH 8.000.000, St 4 (MPPT)
                return r + [0] * (adet - len(r))
            return [0] * adet
    co_son = lambda t, p: son["ts"]
    co_yaz = lambda t, p, o: (yazilan.append(o), son.__setitem__("ts", o["ts_utc"]))
    topla = lambda t, p, simdi: {"durum": "yeni_saat_yok", "n_yazilan": 0}
    plants = [_plant(), _plant(ornekleme_acik=False)]
    r = co.tur(plants, T0, SahteIstemci, yaz=co_yaz, son=co_son, topla=topla)
    assert r and "örnek" in r and len(yazilan) == 1 and yazilan[0]["guc_w"] == pytest.approx(98760.0) and yazilan[0]["durum_kodu"] == 4
    r2 = co.tur(plants, T0 + timedelta(minutes=5), SahteIstemci, yaz=co_yaz, son=co_son, topla=topla)
    assert "periyot dolmadı" in r2 and len(yazilan) == 1
    r3 = co.tur(plants, T0 + timedelta(minutes=15), SahteIstemci, yaz=co_yaz, son=co_son, topla=topla)
    assert len(yazilan) == 2 and "örnek" in r3
    assert co.tur([_plant(ornekleme_acik=False)], T0, SahteIstemci, yaz=co_yaz, son=co_son, topla=topla) is None   # uygun santral yok → günlük satırı düşmez
    class Kopuk(SahteIstemci):
        def __enter__(self): raise OSError("bağlantı reddedildi")
    r4 = co.tur([_plant(name="A"), _plant(baglanti={"host": "127.0.0.1"})], T0 + timedelta(hours=1), Kopuk, yaz=co_yaz, son=co_son, topla=topla)
    assert r4.count("HATA") == 2 and "OSError" in r4 and "yerel/ayrılmış" in r4   # biri kopuk, biri reddedilen adres; tur durmaz


def test_dogrula_ornekleme_sarti_ve_asamalar():
    b = vy.dogrula({"tur": "modbus_sunspec", "salt_okuma_onayi": True, "ornekleme_acik": True, "baglanti": {"host": "10.8.0.12"}})["veri_yolu"]
    assert b["ornekleme_acik"] is True
    assert vy.dogrula({"tur": "modbus_sunspec", "salt_okuma_onayi": False, "ornekleme_acik": True, "baglanti": {"host": "10.8.0.12"}})["veri_yolu"]["ornekleme_acik"] is False   # onay yok
    assert vy.dogrula({"tur": "modbus_sunspec", "salt_okuma_onayi": True, "ornekleme_acik": True})["veri_yolu"]["ornekleme_acik"] is False                                      # bağlantı yok
    assert vy.dogrula({"tur": "opc_ua", "salt_okuma_onayi": True, "ornekleme_acik": True})["veri_yolu"]["ornekleme_acik"] is False                                              # Modbus değil
    a = vy.asamalar({**b, "beyan_zamani": "t", "son_sinama": {"durum": "ok", "zaman": "z"}}, [])
    assert [x["kod"] for x in a] == ["secildi", "ayar", "sinama", "cekis", "akis"] and a[3]["tamam"] and not a[4]["tamam"]
    a2 = vy.asamalar({**b, "beyan_zamani": "t", "son_sinama": {"durum": "ok", "zaman": "z"}}, [{"tur": "modbus_sunspec", "son": "2026-11-08T09:00:00+00:00"}])
    assert a2[4]["tamam"] and a2[4]["etiket"] == "veri alınıyor"


def test_tazelik_esik_ve_dosya_sikligi():
    simdi = datetime(2026, 11, 8, 12, 0, tzinfo=timezone.utc)
    # protokol: eşik 3 × 15 dk → en az 1 saat
    assert vy.tazelik(simdi - timedelta(minutes=50), simdi, "protokol", esik_saat=1.0)["tazelik"] == "guncel"
    assert vy.tazelik(simdi - timedelta(minutes=70), simdi, "protokol", esik_saat=1.0)["tazelik"] == "gecikmis"
    # dosya: beyan edilen sıklık 7 gün → eşik 14 gün
    g = vy.tazelik(simdi - timedelta(days=10), simdi, "dosya", dosya_eski_gun=7); assert g["tazelik"] == "dosya" and g["esik_gun"] == 14
    e = vy.tazelik(simdi - timedelta(days=17), simdi, "dosya", dosya_eski_gun=7); assert e["tazelik"] == "dosya_eski" and e["tazelik_etiketi"] == "yükleme 14 günden eski"
    assert vy.tazelik(simdi - timedelta(days=17), simdi, "dosya")["tazelik"] == "dosya"   # beyan yoksa 30 gün


def test_kayip_referansi_son_temizlige_baglanir():
    bitis = date(2026, 10, 30)
    gunler = pd.date_range("2026-10-01", "2026-10-30", freq="D").date
    pr = [0.80] * 20 + [0.86, 0.87, 0.86, 0.87, 0.86, 0.85, 0.85, 0.84, 0.84, 0.83]     # 21 Ekim temizlik → PR sıçrar, sonra yavaş düşer
    g = pd.DataFrame({"gun": gunler, "pr_acik": pr})
    ur = pd.Series(20000.0, index=gunler)
    k0 = ks.kayip_tahmini(g, ur, None, bitis, None, "modul")
    k1 = ks.kayip_tahmini(g, ur, None, bitis, None, "modul", temizlik_tarihi=date(2026, 10, 20))
    assert k1["referans_pr"] >= k0["referans_pr"] and "son temizlik (2026-10-20) sonrası 10 açık gün" in k1["referans_kaynak"]
    k2 = ks.kayip_tahmini(g, ur, None, bitis, None, "modul", temizlik_tarihi=date(2026, 10, 29))   # sonrası 1 açık gün → pencere kantili, not düşer
    assert k2["referans_pr"] == k0["referans_pr"] and "açık gün yetersiz (1 < 3)" in k2["referans_kaynak"]
