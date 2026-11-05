"""v2.541 — EK-3 DK-741 (LÜY m.21(8) sona erme bildirimi, 15 dk) ve DK-743 (DUY m.71/A(1) gerekçe 3 iş günü) + talimat miktarı (MW, kayıt)."""
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from pvquant.services import olay_service as os_
from tests.test_olay import kiraci  # noqa: F401 — kiracı/santral fikstürü (DB)

IST = ZoneInfo("Europe/Istanbul")


def test_dogrula_yeni_alanlar():
    v = os_.dogrula({"tur": "acil_kesme", "baslangic": "2026-10-28T14:10", "bitis": "2026-10-28T16:45", "bildirim_zamani": "2026-10-28T16:52"}, 40000)
    assert v["bildirim_zamani"] is not None and v["talimat_mw"] is None
    with pytest.raises(ValueError, match="başlangıçtan önce"):
        os_.dogrula({"tur": "acil_kesme", "baslangic": "2026-10-28T14:10", "bildirim_zamani": "2026-10-28T13:00"}, 40000)
    # bildirim yalnız acil kesmede, talimat miktarı yalnız YAL/YAT'ta saklanır
    assert os_.dogrula({"tur": "ariza", "baslangic": "2026-10-28T14:10", "bildirim_zamani": "2026-10-28T16:52", "talimat_mw": 5}, 40000)["bildirim_zamani"] is None
    v2 = os_.dogrula({"tur": "talimat_yat", "baslangic": "2026-10-19T12:00", "bitis": "2026-10-19T14:00", "talimat_mw": "5,5".replace(",", ".")}, 40000)
    assert v2["talimat_mw"] == 5.5 and v2["bildirim_zamani"] is None
    with pytest.raises(ValueError, match="talimat_mw"):
        os_.dogrula({"tur": "talimat_yal", "baslangic": "2026-10-19T12:00", "talimat_mw": -1}, 40000)
    with pytest.raises(ValueError, match="talimat_mw"):
        os_.dogrula({"tur": "talimat_yal", "baslangic": "2026-10-19T12:00", "talimat_mw": "beş"}, 40000)


def test_ekle_guncelle_turetilmis_alanlar(kiraci):
    tid, plant = kiraci
    a = os_.ekle(tid, plant, {"tur": "acil_kesme", "baslangic": "2026-10-28T14:10", "bitis": "2026-10-28T16:45", "bildirim_zamani": "2026-10-28T17:05"})
    assert a["bildirim_zamani"].startswith("2026-10-28T17:05") and a["bildirim_gecikme_dk"] == 20 and a["bildirim_15dk_asildi"] is True and a["gerekce_son_gunu"] is None
    b = os_.ekle(tid, plant, {"tur": "acil_kesme", "baslangic": "2026-10-29T10:00", "bitis": "2026-10-29T11:00"})
    assert b["bildirim_zamani"] is None and b["bildirim_gecikme_dk"] is None and b["bildirim_15dk_asildi"] is None
    b2 = os_.guncelle(tid, plant, b["id"], {"bildirim_zamani": "2026-10-29T11:08"})
    assert b2["bildirim_gecikme_dk"] == 8 and b2["bildirim_15dk_asildi"] is False
    # talimat: miktar + gerekçe son günü (Pazartesi 19.10.2026 → 3 iş günü → Perşembe 22.10.2026)
    t = os_.ekle(tid, plant, {"tur": "talimat_yat", "baslangic": "2026-10-19T12:00", "bitis": "2026-10-19T14:00", "talimat_mw": 5})
    assert t["talimat_mw"] == 5.0 and t["gerekce_son_gunu"] == "2026-10-22" and t["bildirim_zamani"] is None
    # Cuma 30.10.2026 → 3 iş günü: Pzt 2, Sal 3, Çar 4 Kasım
    t2 = os_.ekle(tid, plant, {"tur": "talimat_yal", "baslangic": "2026-10-30T09:00", "bitis": "2026-10-30T10:00"})
    assert t2["gerekce_son_gunu"] == "2026-11-04" and t2["talimat_mw"] is None
    # güncellemede miktar değişir; CSV yeni sütunlar
    t3 = os_.guncelle(tid, plant, t["id"], {"talimat_mw": 6.5}); assert t3["talimat_mw"] == 6.5
    dosya = os_.csv_metni(os_.listele(tid, plant["id"], 400), plant["name"])
    bas = dosya.split("\n")[0]
    assert bas.endswith(";bildirim_zamani;bildirim_gecikme_dk;talimat_mw;gerekce_son_gunu") and ";6.5;2026-10-22" in dosya.replace(";6,5;", ";6.5;") and ";20;" in dosya
    o = os_.ozet(tid, plant, gun=30)
    assert "m.21(8)" in o["aciklama"]["bildirim"] and "m.71/A" in o["aciklama"]["bildirim"] and "3 iş günü" in o["turler"][2]["not"]


# --- v2.541 ek: DK-252 katılımcı birleştirme, DK-056 talimat miktarı sütunları, DK-804 YEÜM, DK-206 topluluk notu
import pandas as pd
import numpy as np
from pvquant.services import dengesizlik_service as dz


def _prog(kw, n=48, bas="2026-11-01"):
    ts = pd.date_range(bas, periods=n, freq="h", tz="UTC")
    return pd.DataFrame({"ts_utc": ts, "gercek_kw": [kw * 1.1] * n, "kgup_kw": [kw] * n})


def test_katilimci_birlestir():
    P = {"A": _prog(1000), "B": _prog(500), "C": _prog(2000)}
    kb = dz.katilimci_birlestir(P, {"A": "X", "B": "X", "C": ""}, {"A": None, "B": None}, {"A": "lisansli_serbest", "B": "lisansli_yekdem", "C": "lisansli_serbest"},
                                {"A": 3, "B": 7, "C": 1}, {"A": True, "B": False, "C": True})
    assert kb["gruplar"] == {"X": ["A", "B"]} and set(kb["programlar"]) == {"C", "X (A + B)"} and kb["ad_haritasi"] == {"X (A + B)": ["A", "B"]}
    m = kb["programlar"]["X (A + B)"]
    assert len(m) == 48 and float(m["kgup_kw"].iloc[0]) == 1500.0 and abs(float(m["gercek_kw"].iloc[0]) - 1650.0) < 1e-9 and list(m.columns) == ["ts_utc", "gercek_kw", "kgup_kw"]
    assert kb["segmentler"]["X (A + B)"] == "lisansli_serbest" and kb["ariza"]["X (A + B)"] == 7 and kb["luy"]["X (A + B)"] is False and kb["luy"]["C"] is True
    # tek santralli kod birleşmez; kodsuz dokunulmaz; pozisyon ayarı olan üye varsa toplam pozisyon
    kb2 = dz.katilimci_birlestir(P, {"A": "Y"}, {})
    assert kb2["gruplar"] == {} and set(kb2["programlar"]) == {"A", "B", "C"}
    poz = {"A": pd.Series(0.9, index=pd.DatetimeIndex(P["A"]["ts_utc"]))}
    kb3 = dz.katilimci_birlestir(P, {"A": "X", "B": "X"}, poz)
    assert abs(float(kb3["pozisyonlar"]["X (A + B)"].iloc[0]) - (0.9 + 0.5)) < 1e-9
    # ortak saat kesişimi: B'nin yarısı eksikse birleşik üye yalnız ortak saatleri taşır
    kb4 = dz.katilimci_birlestir({"A": _prog(1000), "B": _prog(500, n=24)}, {"A": "X", "B": "X"})
    assert len(kb4["programlar"]["X (A + B)"]) == 24
    assert "piyasa katılımcısı" in dz.DSG_KATILIMCI_NOTU and dz.segment_bilgisi({"segment": "lisansli_serbest", "piyasa_katilimcisi": " X "})["piyasa_katilimcisi"] == "X"


def test_talimat_miktari_ve_budup():
    idx = pd.date_range("2026-11-01 09:00", periods=6, freq="h", tz=IST).tz_convert("UTC")
    olaylar = [{"tur": "talimat_yat", "baslangic": datetime(2026, 11, 1, 10, 0, tzinfo=IST), "bitis": datetime(2026, 11, 1, 12, 0, tzinfo=IST), "talimat_mw": 5},
               {"tur": "talimat_yal", "baslangic": datetime(2026, 11, 1, 11, 0, tzinfo=IST), "bitis": datetime(2026, 11, 1, 13, 0, tzinfo=IST), "talimat_mw": 2},
               {"tur": "talimat_yal", "baslangic": datetime(2026, 11, 1, 13, 0, tzinfo=IST), "bitis": None},   # miktar yok → NaN
               {"tur": "acil_kesme", "baslangic": datetime(2026, 11, 1, 9, 0, tzinfo=IST), "bitis": datetime(2026, 11, 1, 10, 0, tzinfo=IST), "talimat_mw": 9}]
    mw = dz.talimat_miktari(olaylar, idx)
    got = {k.tz_convert(IST).hour: (None if np.isnan(v) else v) for k, v in mw.items()}
    assert got == {9: None, 10: -5.0, 11: -3.0, 12: 2.0, 13: None, 14: None}   # 11: −5 + 2; acil kesme sayılmaz; miktarsız YAL NaN
    assert dz.talimat_miktari([], idx).isna().all() and "budup_mwh" in dz.DOKUM_NOTU_TALIMAT and "doğrulanmadı" in dz.DOKUM_NOTU_TALIMAT


def test_yeum_hesabi_ve_izleme():
    assert dz.yeum_hesabi(None) is None and dz.yeum_hesabi(0) is None and dz.yeum_hesabi(28000) == 28000.0
    assert abs(dz.yeum_hesabi(28000, kabul_orani=0.5, toplayici_disi_gun=73) - 28000 * 0.5 * 73 / 365) < 1e-9
    idx = pd.date_range("2026-11-01 09:00", periods=4, freq="h", tz=IST).tz_convert("UTC")
    pv = pd.DataFrame({"sapma": [-1.5, 2.0, -0.5, 0.0]}, index=idx)
    y = dz.yeum_izleme(pv, {"lisans_yillik_uretim_mwh": "400"}, bugun=date(2026, 11, 5))
    assert y["yil"] == 2026 and y["negatif_dengesizlik_mwh"] == 2.0 and y["saat"] == 4 and y["yeum_mwh"] == 400.0 and y["oran_pct"] == 0.5 and y["kapsam"] == "kismi"
    assert "Karar 14626" in y["not"] and "33272" in y["not"] and len(y["kalemler_disinda"]) == 4
    y0 = dz.yeum_izleme(None, {}, bugun=date(2026, 11, 5)); assert y0["yeum_mwh"] is None and y0["oran_pct"] is None and y0["negatif_dengesizlik_mwh"] is None
    pv2 = pv.copy(); pv2.index = pv2.index - pd.Timedelta(days=400)   # geçen yıl → yıl içi 0 saat
    assert dz.yeum_izleme(pv2, {"lisans_yillik_uretim_mwh": 400}, bugun=date(2026, 11, 5))["saat"] == 0
    assert "Karar 14907 Md.4(1)" in dz.TOPLULUK_NOTU


# --- v2.541 ek: EK-2 DK-659 LÜY rejimi, Mutabakat KÜPST katsayı kaynağı
from pvquant.ext.turkiye import takvim as tk


def test_luy_rejimi():
    a = tk.luy_rejimi({"cagri_mektubu_tarihi": "2018-03-01", "isletmeye_giris": "2020-01-01"})
    assert a["rejim"] == "m25" and a["kesinlik"] == "teyit" and "m.23(3)" in a["not"] and a["tarih"] == "2018-03-01"
    b = tk.luy_rejimi({"isletmeye_giris": "2021-06-01"})
    assert b["rejim"] == "m26" and b["kesinlik"] == "yorum" and "yorum" in b["olcut"] and "m.26" in b["not"]
    c = tk.luy_rejimi({}); assert c["rejim"] is None and c["kesinlik"] == "belirsiz"
    assert tk.luy_rejimi({"cagri_mektubu_tarihi": "2019-05-12"})["rejim"] == "m26" and tk.luy_rejimi({"cagri_mektubu_tarihi": "2019-05-11"})["rejim"] == "m25"
    assert "cagri_mektubu_tarihi" in tk.KUNYE_TARIH_ALANLARI and "Çağrı mektubu" in tk.KUNYE_ETIKET["cagri_mektubu_tarihi"]


# --- v2.541 ek: DK-267 GTŞ/toplayıcı adına göre birim, Diyanet 2028
def test_gts_adi_ile_birim_ve_2028_bayram():
    b = dz.segment_bilgisi({"segment": "lisanssiz_dagitim", "gts_toplayici_adi": " Başkent GTŞ "})
    assert b["gts_toplayici_adi"] == "Başkent GTŞ" and dz.GTS_AD_ONEKI == "GTŞ/toplayıcı: "
    assert tk.resmi_tatil(date(2028, 2, 26)) and tk.resmi_tatil(date(2028, 5, 8)) and not tk.resmi_tatil(date(2028, 2, 25)) and not tk.resmi_tatil(date(2028, 5, 9))
    assert tk.resmi_tatil(date(2027, 3, 9)) and tk.resmi_tatil(date(2027, 5, 19)) and 2028 in tk.DINI_BAYRAM and "diyanet" in tk.TATIL_KAYNAK
