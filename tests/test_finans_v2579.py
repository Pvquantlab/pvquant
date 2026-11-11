"""v2.579 (Faz 2 F2-A, Stage 2 temeli) — Finansal Etki Merkezi sözlüğü: nitelik sırası, işaret eşlemesi (her kaynak alan), bileşen/toplam
ve çift sayım bekçisi, birim yardımcıları, dönem çözümleyici (gün/hafta/ay/çeyrek/yıl; 23/25 saatlik gün; kırpma; gelecek dönem)."""
from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from pvquant.ext.platform import finans as f
from pvquant.services import aylik_rapor_service as ar

N = f.Nitelik


# ---------------- nitelik ----------------
def test_nitelik_sirasi_ve_en_zayif():
    assert f.NITELIK_SIRA == (N.RESMI, N.HESAPLANAN, N.SOZLESME_TAHMINI, N.SENARYO, N.EKSIK)
    assert f.en_zayif(N.RESMI, N.HESAPLANAN) == N.HESAPLANAN
    assert f.en_zayif("resmi", "senaryo", None) == N.SENARYO
    assert f.en_zayif(N.SOZLESME_TAHMINI, N.EKSIK) == N.EKSIK
    assert f.en_zayif() == N.EKSIK
    assert set(f.NITELIK_AD) == set(N) == set(f.NITELIK_ACIKLAMA)


# ---------------- işaret ----------------
@pytest.mark.parametrize("alan,deger,beklenen", [
    ("dengesizlik.edt_neg", 100.0, -100.0), ("dengesizlik.edt_borc_tl", 10.0, -10.0), ("dengesizlik.edtb_tl", 7.0, -7.0),
    ("dengesizlik.edt_poz", 50.0, 50.0), ("dengesizlik.edt_alacak_tl", 5.0, 5.0), ("dengesizlik.edta_tl", 6.0, 6.0),
    ("dengesizlik.edt_poz", -3.0, -3.0),   # B dalı: kaynakta eksi alacak → FEM'de de eksi (lehte değil)
    ("dengesizlik.edt_net", 20.0, 20.0), ("dengesizlik.dengesizlik_tl", 30.0, -30.0), ("dengesizlik.kupst_tl", 20.0, -20.0),
    ("dengesizlik.pvquant_tl", 40.0, -40.0), ("dengesizlik.referans_fark_tl", 9.0, 9.0),
    ("dsg.edt_tek_tl", 40.0, 40.0), ("dsg.edt_dsg_tl", 45.0, 45.0), ("dsg.netlesme_farki_tl", 10.0, 10.0), ("dsg.kupst_uye_tl", 4.0, -4.0),
    ("mutabakat.alacak_tl", 8.0, 8.0), ("mutabakat.borc_tl", 8.0, -8.0), ("mutabakat.fark_tl", 5.0, 5.0),
    ("mutabakat.kiyas.kupst_fark_tl", 5.0, -5.0), ("mutabakat.kiyas.dengesizlik_fark_tl", 5.0, 5.0),
    ("saatlik_detay.edt_net_fark_tl", 2.0, 2.0), ("saatlik_detay.edt_neg_tl", 2.0, -2.0),
    ("tarife.gelir_tl", 1000.0, 1000.0), ("yekdem.yek_alacagi_tl", 900.0, 900.0), ("yekdem.yekdem_disi_tl", 3.0, -3.0),
    ("kayip.kayip_tl", 7.0, -7.0), ("kullanilabilirlik.acik_tl", 1.0, -1.0), ("sayac.bedel_toplam_tl", 1.0, -1.0), ("dengesizlik.teminat_tl", 1.0, -1.0),
])
def test_fem_isareti_kaynak_alanlar(alan, deger, beklenen):
    assert f.fem_isareti(alan, deger) == beklenen


def test_fem_isareti_bilinmeyen_alan_ve_bos():
    with pytest.raises(KeyError):
        f.fem_isareti("bilinmeyen.alan", 1.0)
    assert f.fem_isareti("dengesizlik.kupst_tl", None) is None
    assert f.fem_isareti("dengesizlik.kupst_tl", float("nan")) is None
    assert all(c in (+1, -1) and isinstance(a, str) and a for c, a in f.ISARET_ESLEMESI.values())


def test_bildirim_isareti_ve_alacak_borc():
    assert f.bildirim_isareti(250.5, "alacak") == 250.5
    assert f.bildirim_isareti(250.5, "borc") == -250.5
    assert f.bildirim_isareti(-250.5, "borc") == -250.5   # mutlak değer saklanır, yön belirler
    assert f.bildirim_isareti(1.0, "x") is None and f.bildirim_isareti(None, "alacak") is None
    assert f.alacak_borc(120.0) == (120.0, 0.0)
    assert f.alacak_borc(-80.0) == (0.0, 80.0)
    assert f.alacak_borc(0.0) == (0.0, 0.0)
    assert f.alacak_borc(None) == (None, None)


# ---------------- bileşen / toplam ----------------
def test_bilesen_turetme_ve_sozluk():
    b = f.Bilesen("edt", "Enerji dengesizlik tutarı", tutar_tl=-1500.0, nitelik="hesaplanan", kaynak="dengesizlik_service.dokum",
                  kapsam_saat=700, beklenen_saat=744, kural_surumu="edt-2026-V100-edta_ayrik")
    assert (b.alacak_tl, b.borc_tl) == (0.0, 1500.0) and b.nitelik == N.HESAPLANAN and b.kapsam_orani() == 0.9409
    d = b.sozluk(); assert d["tutar_tl"] == -1500.0 and d["nitelik_ad"] == "hesaplanan" and d["toplanir"] is True
    c = f.Bilesen("gelir", "Enerji satışı", alacak_tl=10000.0, borc_tl=0.0, nitelik=N.SOZLESME_TAHMINI)
    assert c.tutar_tl == 10000.0
    e = f.Bilesen.eksik("kupst", "KGÜP sapma tutarı", "KÜPST katsayısı yok")
    assert e.nitelik == N.EKSIK and e.tutar_tl is None and e.notlar == ["KÜPST katsayısı yok"]
    g = f.Bilesen("x", "x", nitelik="resmi")   # tutar yoksa nitelik resmî kalamaz
    assert g.nitelik == N.EKSIK


def test_toplam_ve_cift_sayim_bekcisi():
    b = [f.Bilesen("gelir", "Enerji satışı", 10000.0, nitelik=N.SOZLESME_TAHMINI),
         f.Bilesen("edt", "EDT", -1500.0, nitelik=N.HESAPLANAN),
         f.Bilesen("kupst", "KÜPST", -200.0, nitelik=N.HESAPLANAN),
         f.Bilesen("teminat", "Teminat göstergesi", -5000.0, nitelik=N.SENARYO, toplanir=False),
         f.Bilesen("kayip", "Üretim düşüklüğü", -900.0, nitelik=N.SOZLESME_TAHMINI, toplanir=False)]
    t = f.toplam(b)
    assert t["tutar_tl"] == 8300.0 and t["alacak_tl"] == 8300.0 and t["borc_tl"] == 0.0
    assert t["nitelik"] == "sozlesme_tahmini" and t["giren"] == ["gelir", "edt", "kupst"] and t["eksik"] == []
    b.append(f.Bilesen.eksik("dsg", "DSG", "grup yok"))
    t2 = f.toplam(b)
    assert t2["tutar_tl"] == 8300.0 and t2["eksik"] == ["dsg"] and t2["nitelik"] == "senaryo"   # eksik kalem toplamı senaryo düzeyine düşürür
    with pytest.raises(ValueError):
        f.toplam([*b, f.Bilesen("edt", "EDT yine", -1.0, nitelik=N.HESAPLANAN)])
    bos = f.toplam([f.Bilesen.eksik("a", "a", "yok")])
    assert bos["tutar_tl"] is None and bos["nitelik"] == "eksik" and bos["eksik"] == ["a"]


# ---------------- birim ----------------
def test_birim_yardimcilari():
    assert f.kwh_mwh(1500.0) == 1.5 and f.mwh_kwh(1.5) == 1500.0 and f.kwh_mwh(None) is None and f.kwh_mwh(float("nan")) is None
    assert f.tl_per_mwh(3000.0, 1.5) == 2000.0
    assert f.tl_per_mwh(3000.0, 0.0) is None and f.tl_per_mwh(None, 1.0) is None and f.tl_per_mwh("x", 1.0) is None
    assert f.bin_tl(184_600.0) == 185_000.0 and f.bin_tl(-1499.0) == -1000.0 and f.bin_tl(None) is None


# ---------------- dönem ----------------
BUGUN = date(2026, 11, 11)


def test_donem_gun_hafta_ay_ceyrek_yil():
    g = f.donem_cozumle("2026-11-10", BUGUN)
    assert g["tur"] == "gun" and g["bas"] == date(2026, 11, 10) and g["bit"] == date(2026, 11, 11) and g["saat"] == 24 and g["gun"] == 1
    assert g["bas_utc"] == datetime(2026, 11, 9, 21, tzinfo=timezone.utc) and g["etiket"] == "10 Kasım 2026" and not g["kirpildi"]
    h = f.donem_cozumle("2026-W45", BUGUN)
    assert h["tur"] == "hafta" and h["bas"] == date.fromisocalendar(2026, 45, 1) == date(2026, 11, 2) and h["bit"] == date(2026, 11, 9)
    assert h["saat"] == 168 and "45. hafta" in h["etiket"] and "2–8 Kasım" in h["etiket"]
    h2 = f.donem_cozumle("2026-w44", BUGUN)   # küçük harf, ay sınırı aşan hafta
    assert h2["bas"] == date(2026, 10, 26) and "26 Ekim – 1 Kasım" in h2["etiket"]
    a = f.donem_cozumle("2026-10", BUGUN)
    assert a["tur"] == "ay" and a["saat"] == 744 and a["etiket"] == "Ekim 2026" and len(f.saat_kumesi(a)) == 744
    assert f.saat_kumesi(a)[0] == a["bas_utc"] and f.saat_kumesi(a)[-1] == a["bit_utc"] - __import__("datetime").timedelta(hours=1)
    c = f.donem_cozumle("2026-Q3", BUGUN)
    assert c["tur"] == "ceyrek" and c["bas"] == date(2026, 7, 1) and c["bit"] == date(2026, 10, 1) and c["gun"] == 92
    y = f.donem_cozumle("2025", BUGUN)
    assert y["tur"] == "yil" and y["gun"] == 365 and y["saat"] == 8760


def test_donem_kirpma_gelecek_varsayilan_ve_hatali():
    s = f.donem_cozumle("2026-11", BUGUN)
    assert s["kirpildi"] and s["bit"] == date(2026, 11, 12) and "süren dönem" in s["etiket"] and s["gun"] == 11
    bugun_gun = f.donem_cozumle("2026-11-11", BUGUN)
    assert not bugun_gun["kirpildi"] and bugun_gun["gun"] == 1   # bugün: tam gün sınırı, veri kadar saat gelir
    assert f.donem_cozumle(None, BUGUN)["kod"] == "2026-10"
    for kod in ("2026-11-12", "2026-W47", "2026-12", "2027-Q1", "2027"):
        with pytest.raises(ValueError):
            f.donem_cozumle(kod, BUGUN)
    for kod in ("2026-02-30", "2026-W54", "2026/11", "11-2026", "abc"):
        with pytest.raises(ValueError):
            f.donem_cozumle(kod, BUGUN)


def test_donem_yaz_saati_gecisli_dilimde_23_ve_25_saat():
    assert f.donem_cozumle("2026-03-29", BUGUN, tz="Europe/Berlin")["saat"] == 23
    assert f.donem_cozumle("2026-10-25", BUGUN, tz="Europe/Berlin")["saat"] == 25
    assert f.donem_cozumle("2026-03-29", BUGUN, tz="Europe/Istanbul")["saat"] == 24   # Türkiye: yaz saati yok
    a = f.donem_cozumle("2026-10", BUGUN, tz="Europe/Berlin")
    assert a["saat"] == 745 and len(f.saat_kumesi(a)) == 745


def test_donem_ay_ceyrek_yil_aylik_raporla_ayni():
    for kod in ("2026-10", "2026-Q2", "2025", None):
        x, y = f.donem_cozumle(kod, BUGUN), ar.donem_cozumle(kod, BUGUN)
        assert (x["tur"], x["kod"], x["bas"], x["bit"], x["saat"], x["kirpildi"]) == (y["tur"], y["kod"], y["bas"], y["bit"], y["saat"], y["kirpildi"])
        assert x["etiket"] == y["etiket"]


def test_donem_kodu_tersine():
    d = date(2026, 11, 11)
    assert f.donem_kodu(d, "gun") == "2026-11-11" and f.donem_kodu(d, "hafta") == "2026-W46" and f.donem_kodu(d, "ay") == "2026-11"
    assert f.donem_kodu(d, "ceyrek") == "2026-Q4" and f.donem_kodu(d, "yil") == "2026"
    assert f.donem_kodu(date(2027, 1, 1), "hafta") == "2026-W53"   # ISO: 1.1.2027 bir önceki yılın 53. haftasında
    for tur in f.DONEM_TURLERI:
        k = f.donem_kodu(date(2026, 5, 17), tur)
        assert f.donem_cozumle(k, BUGUN)["tur"] == tur
    with pytest.raises(ValueError):
        f.donem_kodu(d, "saat")
