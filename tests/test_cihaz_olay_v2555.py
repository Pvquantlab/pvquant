"""v2.555 (Aşama 5, V2): cihaz durumundan olay adayları — arıza koşusu, alarm bitleri, sürüyor/bitti, mevcut olayla çakışma, iletişim kopukluğu; otomatik kayıt yok."""
from datetime import datetime, timedelta, timezone

from pvquant.services import cihaz_olay_service as co

T0 = datetime(2026, 11, 9, 8, 0, tzinfo=timezone.utc)


def _o(m, durum=4, olaylar=None, cihaz="SN-A"):
    return {"ts_utc": T0 + timedelta(minutes=m), "cihaz_id": cihaz, "durum_kodu": durum, "olaylar": olaylar or [], "guc_w": 1000.0}


def test_ariza_kosusu_ve_kopukluk():
    ornekler = [_o(0), _o(15), _o(30, 7), _o(45, 7, ["AC kesici açık"]), _o(60, 7), _o(75), _o(90), _o(180), _o(195, 7)]   # 30–75 arıza; 90→180 boşluk; 195 sürüyor
    a = co.adaylar(ornekler, [], periyot_dk=15, simdi=T0 + timedelta(minutes=215))
    turler = [(x["tur"], x["durum"]) for x in a]
    assert ("ariza", "bitti") in turler and ("iletisim_kopuklugu", "bitti") in turler and ("ariza", "suruyor") in turler
    ar = next(x for x in a if x["tur"] == "ariza" and x["durum"] == "bitti")
    assert ar["bas"] == (T0 + timedelta(minutes=30)).isoformat() and ar["bit"] == (T0 + timedelta(minutes=75)).isoformat() and ar["ornek_sayisi"] == 3 and ar["kodlar"] == ["AC kesici açık"] and ar["sure_dk"] == 45.0
    kop = next(x for x in a if x["tur"] == "iletisim_kopuklugu")
    assert kop["sure_dk"] == 90.0 and kop["ornek_sayisi"] == 0
    sur = next(x for x in a if x["durum"] == "suruyor")
    assert sur["bit"] is None and sur["ornek_sayisi"] == 1 and sur["sure_dk"] == 20.0   # tek örnek, şimdiye kadar 20 dk ≥ 10 → sürüyor
    assert not [x for x in co.adaylar([_o(0), _o(15, 7), _o(30)], [], 15, T0 + timedelta(minutes=40)) if x["tur"] == "ariza"]   # tek arıza örneği, 15 dk sonra normal → aday değil (gürültü)


def test_mevcut_olayla_cakisma_ve_cihaz_ayrimi():
    ornekler = [_o(0, 7), _o(15, 7), _o(30), _o(0, 7, cihaz="SN-B"), _o(15, 7, cihaz="SN-B"), _o(30, cihaz="SN-B")]
    mevcut = [{"baslangic": T0 - timedelta(minutes=10), "bitis": T0 + timedelta(minutes=20), "tur": "ariza"}]
    a = co.adaylar(ornekler, mevcut, 15, T0 + timedelta(hours=1))
    assert len(a) == 2 and all(x["kayitli"] for x in a) and {x["cihaz_id"] for x in a} == {"SN-A", "SN-B"}
    assert all(x["tur"] == "ariza" and x["durum"] == "bitti" for x in a)
    b = co.adaylar(ornekler, [], 15, T0 + timedelta(hours=1))
    assert not any(x["kayitli"] for x in b)
