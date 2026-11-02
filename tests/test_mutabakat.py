"""v2.522 (P2b-1) — EPİAŞ uzlaştırma bildirimiyle mutabakat: dosya tanıma (CSV bölümlü / alacak-borç sütunlu / XLSX), kalem eşleme, sayı
biçimleri, kayıt + dönem listesi (RLS'li tablo, test DB), kalem kalem mutabakat (sahte döküm), teminat göstergesi (mevzuat formülü),
DSG/portföyde bildirilen KGÜP, DSG üye belgesi, API uçları."""
from __future__ import annotations

import io
import uuid
from datetime import date

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from pvquant.db import sistem_baglami
from pvquant.services import dengesizlik_service as dz
from pvquant.services import mutabakat_service as ms

CSV_BOLUMLU = ("Uzlaştırma Bildirimi;Fatura Dönemi: 10.2026;Uzlaştırma Durumu: Nihai Bildirim\n"
               "Aylık Alacak Özet Listeleme\nUzlaştırma Kalemleri;Tutar (TL)\nGÖP;1.250.000,50\nYEK Alacak;0,00\nDengesizlik;151.234,10\nToplam;1.401.234,60\n"
               "Aylık Borç Özet Listeleme\nUzlaştırma Kalemleri;Tutar (TL)\nDengesizlik;262.100,00\nKÜPST;14.320,75\nPİÜ;1.200,00\nGecikme Zammı;0\nÖdenmeyen Alacak İade Faiz;5,00\nToplam;277.625,75\n").encode("utf-8")
CSV_SUTUNLU = "Kalem,Alacak (TL),Borç (TL)\nDengesizlik,\"151,234.10\",\"262,100.00\"\nKÜPST,,\"14,320.75\"\nGÖP,\"1,250,000.50\",\n".encode("utf-8")


@pytest.fixture()
def kiraci():
    tid, pid = str(uuid.uuid4()), str(uuid.uuid4())
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO tenants(id, name, status) VALUES(:t, 'mutabakat-test', 'active')"), {"t": tid})
        s.execute(text("INSERT INTO plants(id, tenant_id, name, capacity_kwp, lat, lon, tz) VALUES(:p, :t, 'Mutabakat GES', 10000, 37.0, 32.0, 'Europe/Istanbul')"), {"p": pid, "t": tid})
    yield tid, {"id": pid, "name": "Mutabakat GES", "capacity_kwp": 10000.0, "params_json": {}}
    with sistem_baglami() as s:
        s.execute(text("DELETE FROM uzlastirma_bildirimi WHERE tenant_id=:t"), {"t": tid})
        s.execute(text("DELETE FROM plants WHERE id=:p"), {"p": pid})
        s.execute(text("DELETE FROM tenants WHERE id=:t"), {"t": tid})


def test_dosya_oku_bolumlu_csv():
    o = ms.dosya_oku(CSV_BOLUMLU, "bildirim.csv")
    assert o["donem"] == date(2026, 10, 1) and o["surum"] == "nihai" and o["bicim"] == "csv"
    k = {(x["kod"], x["yon"]): x["tutar_tl"] for x in o["kalemler"]}
    assert k[("dam", "alacak")] == 1250000.5 and k[("imbalance", "alacak")] == 151234.1 and k[("imbalance", "borc")] == 262100.0
    assert k[("kupst", "borc")] == 14320.75 and k[("mof", "borc")] == 1200.0 and k[("refund_overdue_interest", "borc")] == 5.0 and k[("summary", "borc")] == 277625.75
    assert not o["taninmayan"] and all("tanınmayan" not in u for u in o["uyarilar"])


def test_dosya_oku_sutunlu_ve_xlsx():
    o = ms.dosya_oku(CSV_SUTUNLU, "x.csv")
    k = {(x["kod"], x["yon"]): x["tutar_tl"] for x in o["kalemler"]}
    assert k[("imbalance", "alacak")] == 151234.1 and k[("imbalance", "borc")] == 262100.0 and k[("kupst", "borc")] == 14320.75 and ("kupst", "alacak") not in k
    assert o["donem"] is None and o["surum"] is None
    from openpyxl import Workbook
    wb = Workbook(); ws = wb.active
    ws.append(["Uzlaştırma Bildirimi", "Fatura Dönemi", "Eylül 2026"]); ws.append(["Uzlaştırma Durumu", "Ön Uzlaştırma Bildirim"])
    ws.append(["Aylık Alacak Özet"]); ws.append(["Uzlaştırma Kalemleri", "Tutar (TL)"]); ws.append(["Dengesizlik", 1000.5]); ws.append(["Bilinmeyen Kalem", 7])
    ws.append(["Aylık Borç Özet"]); ws.append(["Uzlaştırma Kalemleri", "Tutar (TL)"]); ws.append(["KÜPST", 300])
    buf = io.BytesIO(); wb.save(buf)
    x = ms.dosya_oku(buf.getvalue(), "b.xlsx")
    assert x["bicim"] == "xlsx" and x["donem"] == date(2026, 9, 1) and x["surum"] == "on" and x["taninmayan"] == ["Bilinmeyen Kalem"]
    k2 = {(a["kod"], a["yon"]): a["tutar_tl"] for a in x["kalemler"]}
    assert k2[("imbalance", "alacak")] == 1000.5 and k2[("kupst", "borc")] == 300 and k2[("diger", "alacak")] == 7
    with pytest.raises(ValueError):
        ms.dosya_oku(b"a;b\n1;2\n", "bos.csv")


def test_sayi_ve_kalem_tani():
    assert ms._sayi("1.234.567,89") == 1234567.89 and ms._sayi("1,234,567.89") == 1234567.89 and ms._sayi("(12,5)") == -12.5 and ms._sayi("-7") == -7.0
    assert ms._sayi("") is None and ms._sayi("Kalem") is None and ms._sayi(3) == 3.0
    assert ms.kalem_tani("Ödenmeyen Alacak İade Faiz") == "refund_overdue_interest" and ms.kalem_tani("Ödenmeyen Alacak") == "overdue"
    assert ms.kalem_tani("PİÜ") == "mof" and ms.kalem_tani("Gün Öncesi Piyasası") == "dam" and ms.kalem_tani("IMBALANCE") == "imbalance" and ms.kalem_tani("xyz") == "diger"
    assert ms.kalem_tani("KGÜP Sapma Tutarı") == "kupst" and ms.kalem_tani("Net Alacak (TL)") == "summary"
    # 02.11 inceleme: dönem etiketi ve değeri ayrı hücrelerde; gün.ay.yıl tam tarihler (kesinleşme) dönem sanılmaz
    assert ms._donem_bul([["Uzlaştırma Bildirimi"], ["Fatura Dönemi", "10.2026"], ["Uzlaştırma Kesinleşme Tarihi", "15.11.2026"]]) == date(2026, 10, 1)
    assert ms._donem_bul([["Dönem Kesinleşme 15.11.2026, Fatura Dönemi 10.2026"]]) == date(2026, 10, 1)
    assert ms._donem_bul([["Fatura Dönemi", "Eylül 2026", "Çalışma Tarihi", "03.10.2026"]]) == date(2026, 9, 1) and ms._donem_bul([["Kesinleşme Tarihi", "15.11.2026"]]) is None


def test_kaydet_donemler_bildirim(kiraci):
    tid, plant = kiraci
    k = ms.kaydet(tid, plant, CSV_BOLUMLU, "ekim.csv", yukleyen="u")
    assert k["donem"] == "2026-10" and k["surum"] == "nihai" and k["kalem_sayisi"] == 10 and k["surum_kaynagi"] == "dosya"
    assert k["surum_dogrulama"]["resmi_durum"] == "dogrulanmadi" and k["surum_dogrulama"]["nihai_bildirim"] == "2026-11-16"   # 15.11 Pazar → 16.11
    k2 = ms.kaydet(tid, plant, CSV_SUTUNLU, "ekim-on.csv", donem="2026-10", surum="on")
    assert k2["surum"] == "on" and k2["surum_kaynagi"] == "kullanici" and k2["yukleme_id"] != k["yukleme_id"]
    # dosyadaki durum «nihai» iken kullanıcı «ön» seçerse dosya kazanır, uyarı verilir; dosyadaki dönemle seçilen dönem çelişirse 422
    k3 = ms.kaydet(tid, plant, CSV_BOLUMLU, "ekim2.csv", surum="on"); assert k3["surum"] == "nihai" and any("dosyadaki uzlaştırma durumu" in u for u in k3["uyarilar"])
    with pytest.raises(ValueError, match="uyuşmuyor"):
        ms.kaydet(tid, plant, CSV_BOLUMLU, "x.csv", donem="2026-09")
    k4 = ms.kaydet(tid, plant, CSV_SUTUNLU, "eylul.csv", donem="2026-09"); assert k4["surum_kaynagi"] == "varsayilan" and any("varsayıldı" in u for u in k4["uyarilar"])
    with pytest.raises(ValueError, match="dönem"):
        ms.kaydet(tid, plant, CSV_SUTUNLU, "x.csv")   # dönem dosyada yok, verilmedi
    with pytest.raises(ValueError, match="gelecek"):
        ms.kaydet(tid, plant, CSV_SUTUNLU, "x.csv", donem="2099-01")
    d = ms.donemler(tid, plant["id"])   # tarihçe: 4 yükleme; dönem+sürüm başına en yeni «geçerli»
    assert len(d) == 4 and [x["gecerli"] for x in d if x["donem"] == "2026-10" and x["surum"] == "nihai"] == [True, False]
    assert all("surum_dogrulama" in x for x in d) and d[0]["donem"] == "2026-10"
    b = ms.bildirim(tid, plant["id"], date(2026, 10, 1)); assert b["surum"] == "nihai" and len(b["kalemler"]) == 10 and b["yukleme_id"] == k3["yukleme_id"]   # nihai > ön, en yeni
    assert ms.bildirim(tid, plant["id"], date(2026, 10, 1), "on")["kalemler"][0]["kod"] == "imbalance"
    assert ms.bildirim(tid, plant["id"], date(2026, 8, 1)) is None
    assert ms.donemler(str(uuid.uuid4()), plant["id"]) == []   # başka kiracı görmez (RLS)


def _dokum(ay="2026-10", saat=48, edt_borc=5000.0, edt_alacak=3000.0, kupst=300.0, bildirilen=None):
    z = pd.date_range(f"{ay}-10 00:00", periods=saat, freq="h"); b = saat // 2 if bildirilen is None else bildirilen
    return pd.DataFrame({"zaman": [t.strftime("%Y-%m-%d %H:%M") for t in z], "program_kaynak": ["bildirilen"] * b + ["oneri"] * (saat - b),
                         "gerceklesen_mwh": 2.0, "edt_borc_tl": edt_borc, "edt_alacak_tl": edt_alacak, "kupst_tl": kupst, "durum": "ok", "kural_surumu": "edt-2026"})


def test_mutabakat_kalemler(kiraci, monkeypatch):
    tid, plant = kiraci
    ms.kaydet(tid, plant, CSV_BOLUMLU, "ekim.csv")
    # PVQuant: 48 saat × (alacak 3.150, borç 5.460) → EDT alacak 151.200, borç 262.080 (bildirim 151.234,10 / 262.100 → uyumlu); KÜPST 48 × 300 = 14.400 (bildirim 14.320,75 → %0,6 uyumlu)
    monkeypatch.setattr(dz, "dokum", lambda t, p, gun: (_dokum(edt_borc=5460.0, edt_alacak=3150.0, kupst=300.0), {"fiyat": {"senaryo_saat": 0}}))
    m = ms.mutabakat(tid, plant, "2026-10", bugun=date(2026, 11, 2))
    s = {r["kod"]: r for r in m["satirlar"]}
    assert s["imbalance"]["durum"] == "uyumlu" and abs(s["imbalance"]["fark_tl"] - ((151200 - 262080) - (151234.1 - 262100))) < 0.01
    assert s["kupst"]["durum"] == "uyumlu" and s["kupst"]["pvquant_borc_tl"] == 14400.0 and s["kupst"]["fark_pct"] == -0.6
    assert s["dam"]["durum"] == "hesaplanamaz" and s["dam"]["bildirim_alacak_tl"] == 1250000.5 and s["dam"]["pvquant_alacak_tl"] is None
    assert s["res"]["durum"] == "hesap_yok" and s["mof"]["durum"] == "hesaplanamaz"
    assert m["ozet"]["uyumlu"] == 2 and m["ozet"]["farkli"] == 0 and m["ozet"]["kiyaslanan"] == 2 and m["bildirim"]["surum"] == "nihai"
    assert m["ozet"]["bildirim_alacak_tl"] == round(1250000.5 + 0 + 151234.1, 2) and m["pvquant"]["bildirilen_saat"] == 24 and m["program_notu"] is None
    # aynı kapsam: karşılaştırılan kalemlerin bildirim neti (151.234,10 − 262.100 − 14.320,75) ve PVQuant neti (151.200 − 262.080 − 14.400); fark = ikisinin farkı
    assert m["ozet"]["bildirim_kiyas_net_tl"] == round(151234.1 - 262100 - 14320.75, 2) and m["ozet"]["pvquant_net_tl"] == round(151200 - 262080 - 14400, 2)
    assert abs(m["ozet"]["fark_tl"] - (m["ozet"]["pvquant_net_tl"] - m["ozet"]["bildirim_kiyas_net_tl"])) < 0.01 and m["ozet"]["kapsam"] == "Dengesizlik, KÜPST"
    # güvenilirlik: 48/744 saat → kısmi (eksik saat + 24 saatte öneri); sürüm doğrulaması: 02.11 yüklemesi nihai takviminden (16.11) önce
    assert m["guvenilirlik"]["durum"] == "kismi" and len(m["guvenilirlik"]["nedenler"]) == 2 and m["eylem"].startswith("Karşılaştırılan kalemler uyum") and "kapsam kısmi" in m["eylem"]
    # 02.11 inceleme: kısmi kapsamda hüküm «kısmi» nitelikli (özet ve satır); hesaplanamayan satırda nitelik yok
    assert m["ozet"]["dogrulama"] == "kismi" and m["ozet"]["kapsam_saat"] == 48 and m["ozet"]["beklenen_saat"] == 744 and s["imbalance"]["dogrulama"] == "kismi" and s["dam"]["dogrulama"] is None
    assert m["bildirim"]["surum_dogrulama"]["durum"] == "takvimden_once" and m["bildirim"]["surum_dogrulama"]["beklenen_tarih"] == "2026-11-16"
    # bileşen eşiği: net eşleşse de alacak ve borç ayrı ayrı sapıyorsa «fark» (alacak 100k / borç 211k → net aynı)
    monkeypatch.setattr(dz, "dokum", lambda t, p, gun: (_dokum(edt_borc=4397.6, edt_alacak=2087.6, kupst=300.0), {"fiyat": {"senaryo_saat": 0}}))
    mb = ms.mutabakat(tid, plant, "2026-10", bugun=date(2026, 11, 2)); sb = {r["kod"]: r for r in mb["satirlar"]}
    assert sb["imbalance"]["durum"] == "fark" and abs(sb["imbalance"]["fark_tl"]) <= 50 and sb["imbalance"]["bilesen_notu"] and sb["imbalance"]["fark_alacak_tl"] < -50000
    assert mb["eylem"].startswith("Kapsam kısmi (48/744 saat") and "fark doğrulanmış sayılmaz" in mb["eylem"] and "Fark var:" in mb["eylem"]
    # senaryo fiyatı (dönem içinde) → satır durumu «senaryo», uyumlu/fark verilmez; KÜPST hesaplanamıyor → hesap_yok
    df3 = _dokum(edt_borc=9000.0, edt_alacak=100.0, kupst=None)
    monkeypatch.setattr(dz, "dokum", lambda t, p, gun: (df3, {"fiyat": {"senaryo_saat": 10}, "saat_fiyat_kaynak": ["senaryo"] * 10 + ["epias"] * (len(df3) - 10)}))
    m2 = ms.mutabakat(tid, plant, "2026-10", bugun=date(2026, 11, 2)); s2 = {r["kod"]: r for r in m2["satirlar"]}
    assert s2["imbalance"]["durum"] == "senaryo" and s2["kupst"]["durum"] == "hesap_yok" and m2["ozet"]["senaryo"] == 1 and m2["ozet"]["farkli"] == 0
    assert m2["guvenilirlik"]["durum"] == "senaryo" and m2["pvquant"]["senaryo_saat"] == 10 and m2["pvquant"]["senaryo_kapsam"] == "donem" and m2["eylem"].startswith("Senaryo")
    # tam ay, EPİAŞ fiyatı, hepsi bildirilen → «gerçek»
    df4 = _dokum(saat=744, bildirilen=744); df4["zaman"] = [t.strftime("%Y-%m-%d %H:%M") for t in pd.date_range("2026-10-01 00:00", periods=744, freq="h")]
    monkeypatch.setattr(dz, "dokum", lambda t, p, gun: (df4, {"fiyat": {"senaryo_saat": 0}, "saat_fiyat_kaynak": ["epias"] * 744}))
    m4 = ms.mutabakat(tid, plant, "2026-10", bugun=date(2026, 11, 2)); assert m4["guvenilirlik"]["durum"] == "gercek" and m4["pvquant"]["saat"] == 744
    assert m4["ozet"]["dogrulama"] == "tam" and {r["dogrulama"] for r in m4["satirlar"] if r["hesaplanir"] and r["durum"] in ("uyumlu", "fark")} == {"tam"} and not m4["eylem"].startswith("Kapsam kısmi")   # tam ay: fark var ama kapsam niteliği yok
    assert m2["ozet"]["dogrulama"] == "senaryo" and s2["imbalance"]["dogrulama"] == "senaryo"
    # bildirimi olmayan dönem: yalnız PVQuant satırları «bildirimde_yok»
    m3 = ms.mutabakat(tid, plant, "2026-09", bugun=date(2026, 11, 2)); assert m3["bildirim"] is None and all(r["durum"] == "bildirimde_yok" for r in m3["satirlar"])
    m5 = ms.mutabakat(tid, plant, "2026-06", bugun=date(2026, 11, 2)); assert m5["guvenilirlik"]["durum"] == "veri_yok" and m5["satirlar"] == [] and m5["eylem"] is None
    o = ms.ozet(tid, plant, bugun=date(2026, 11, 2)); assert o["secili"]["donem"] == "2026-10" and len(o["kalemler"]) == 16 and o["donemler"][0]["donem"] == "2026-10"


def test_pvquant_kalemleri_sayac_girdisi(kiraci, monkeypatch):
    """v2.526 (P4a-2): uretim='sayac' → döküm sayaçla; saat sayımı, güvenilirlik nedeni ve SCADA'lı hesapla fark (kiyas)."""
    tid, plant = kiraci
    suk = ["sayac_olculmus"] * 40 + ["sayac_tahmini"] * 4 + ["scada"] * 4
    def dok(t, p, gun, uretim=None):
        if uretim == "sayac":
            return _dokum(edt_borc=5460.0, edt_alacak=3300.0, kupst=310.0), {"fiyat": {"senaryo_saat": 0}, "saat_uretim_kaynak": suk, "uretim_kaynak": {"secim": "sayac"}}
        return _dokum(edt_borc=5460.0, edt_alacak=3150.0, kupst=300.0), {"fiyat": {"senaryo_saat": 0}, "saat_uretim_kaynak": ["scada"] * 48}
    monkeypatch.setattr(dz, "dokum", dok)
    pv = ms.pvquant_kalemleri(tid, plant, date(2026, 10, 1), bugun=date(2026, 11, 2), uretim="sayac")
    uk = pv["uretim_kaynak"]; assert uk["secim"] == "sayac" and (uk["sayac_olculmus_saat"], uk["sayac_tahmini_saat"], uk["scada_saat"]) == (40, 4, 4)
    assert uk["kiyas"]["edt_net_fark_tl"] == 7200.0 and uk["kiyas"]["kupst_fark_tl"] == 480.0 and uk["kiyas"]["scada_saat"] == 48 and uk["sayac_kullanilmayan_saat"] == 0
    # 02.11 inceleme: yüklü sayaç saatlerinin hesaba giremeyeni sayılır ve nedenlerde söylenir
    monkeypatch.setattr(ms, "_sayac_kapsami", lambda t, p, d: {"toplam_saat": 744, "yuklu": 60, "olculmus": 55, "tahmini": 5, "olc_fark_pct": -3.0})
    pvk = ms.pvquant_kalemleri(tid, plant, date(2026, 10, 1), bugun=date(2026, 11, 2), uretim="sayac")
    assert pvk["uretim_kaynak"]["sayac_kullanilmayan_saat"] == 16 and any("60 sayaç saatinden 16 saat hesaba girmedi" in n for n in pvk["guvenilirlik"]["nedenler"])
    monkeypatch.setattr(ms, "_sayac_kapsami", lambda t, p, d: None)
    assert pv["kalemler"]["imbalance"]["alacak_tl"] == 48 * 3300.0 and pv["guvenilirlik"]["durum"] == "kismi" and any(n.startswith("hesap 44 saatte sayaç") for n in pv["guvenilirlik"]["nedenler"])
    # santral ayarı da aynı yolu seçer; varsayılan SCADA'da kıyas yok, sayaç notu ayara yönlendirir
    pv2 = ms.pvquant_kalemleri(tid, {**plant, "params_json": {"uzlastirma_girdi": "sayac"}}, date(2026, 10, 1), bugun=date(2026, 11, 2)); assert pv2["uretim_kaynak"]["secim"] == "sayac"
    pv3 = ms.pvquant_kalemleri(tid, plant, date(2026, 10, 1), bugun=date(2026, 11, 2)); assert pv3["uretim_kaynak"]["secim"] == "scada" and pv3["uretim_kaynak"]["kiyas"] is None and pv3["uretim_kaynak"]["scada_saat"] == 48
    # sayaç seçili ama dönemde sayaç saati yok → SCADA ile, dürüst neden
    monkeypatch.setattr(dz, "dokum", lambda t, p, gun, uretim=None: (_dokum(), {"fiyat": {"senaryo_saat": 0}, "saat_uretim_kaynak": ["scada"] * 48}))
    pv4 = ms.pvquant_kalemleri(tid, plant, date(2026, 10, 1), bugun=date(2026, 11, 2), uretim="sayac")
    assert pv4["uretim_kaynak"]["sayac_olculmus_saat"] == 0 and any("sayaç verisi yok" in n for n in pv4["guvenilirlik"]["nedenler"])
    o = ms.ozet(tid, plant, "2026-10", bugun=date(2026, 11, 2), uretim="sayac"); assert o["uretim_ayari"] == "scada" and o["secili"]["pvquant"]["uretim_kaynak"]["secim"] == "sayac" and len(o["uretim_secenekleri"]) == 2


def test_teminat_gostergesi():
    idx = pd.date_range("2026-01-01", "2026-10-31 23:00", freq="h", tz="Europe/Istanbul").tz_convert("UTC")
    rng = np.random.default_rng(1)
    pv = pd.DataFrame({"sapma": rng.normal(0, 1.0, len(idx)), "smf": 2000.0 + rng.normal(0, 50, len(idx))}, index=idx)
    pv.loc[(idx.tz_convert("Europe/Istanbul").month == 8), "sapma"] = -3.0   # Ağustos en kötü ay: 744 × 3 = 2.232 MWh
    t = dz.teminat_gostergesi(pv, None)
    assert t["tutar_tl"] is None and t["dogrulanmis"] is False and t["smf_ay_sayisi"] == 10 and t["edm_ay"] == "2026-08" and t["edm_neg_max_mwh"] == 2232.0
    t2 = dz.teminat_gostergesi(pv, 1.5)
    assert abs(t2["tutar_tl"] - 2232.0 * t2["smf_ort_tl_mwh"] * 1.5) < 10 and 1900 < t2["smf_ort_tl_mwh"] < 2100
    assert dz.teminat_gostergesi(pd.DataFrame(), 1.0)["tutar_tl"] is None
    assert dz._risk_katsayisi({"teminat_risk_katsayisi": 1.5}) == 1.5 and dz._risk_katsayisi({"teminat_risk_katsayisi": 0}) is None and dz._risk_katsayisi({}) is None


def test_program_bildirilenle_ve_uye_csv(monkeypatch):
    ts = pd.date_range("2026-10-01", periods=48, freq="h", tz="UTC")
    df = pd.DataFrame({"ts_utc": ts, "gercek_kw": 5000.0, "kgup_kw": 4000.0, "naif_kw": 4500.0})
    monkeypatch.setattr(dz, "bildirilen_serisi", lambda t, p, pj, gun: pd.Series(6.0, index=ts[:24]))   # ilk gün bildirilen 6 MWh
    x, k = dz.program_bildirilenle("t", "p", {}, df, 30)
    assert k == {"bildirilen_saat": 24, "oneri_saat": 24} and x["kgup_kw"].iloc[0] == 6000.0 and x["kgup_kw"].iloc[30] == 4000.0 and df["kgup_kw"].iloc[0] == 4000.0
    monkeypatch.setattr(dz, "bildirilen_serisi", lambda t, p, pj, gun: pd.Series(dtype=float))
    assert dz.program_bildirilenle("t", "p", {}, df, 30)[1] == {"bildirilen_saat": 0, "oneri_saat": 48}
    assert dz._pozisyon_serisi({"pozisyon_kaynagi": "uretim"}, df).iloc[0] == 5.0 and dz._pozisyon_serisi({}, df) is None and dz._pozisyon_serisi({"pozisyon_kaynagi": "sabit", "pozisyon_sabit_mwh": 2.5}, df).iloc[3] == 2.5
    csv = dz.dsg_uye_csv({"pencere_gun": 30, "dagitim_etiket": "sapma payına göre", "esik": 0.05, "kural_surumu": "edt-2026",
                          "uyeler": {"A GES": {"edt_tek_tl": -100.0, "edt_bireysel_tl": -80.0, "edt_dsg_tl": -90.0, "netlesme_farki_tl": 10.0, "kupst_tl": 5.0, "pay_pct": 60.0, "sapma_mwh": 1.5, "grup_payi_mwh": 0.4}}})
    assert csv.startswith("﻿# PVQuant DSG") and "santral;edt_tek_basina_tl" in csv and "A GES;-100,0;-80,0;-90,0;10,0;5,0;60,0;1,5;0,4" in csv


def test_api_mutabakat_uclari(kiraci, monkeypatch):
    import apps.api.main as api_main
    from apps.api.deps import gecerli_kullanici
    from pvquant.services import plant_service
    tid, plant = kiraci
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": tid, "role": "admin", "exp": 0}
    monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": plant["id"], "name": "Mutabakat GES", "capacity_kwp": 10000.0, "params_json": {}} if p == plant["id"] else None)
    monkeypatch.setattr(dz, "dokum", lambda t, p, gun: (_dokum(edt_borc=5460.0, edt_alacak=3150.0, kupst=300.0), {"fiyat": {"senaryo_saat": 0}}))
    kayit = []
    monkeypatch.setattr(api_main._denetim, "kaydet", lambda *a, **k: kayit.append((a, k)))
    c = TestClient(api_main.app)
    try:
        r = c.post(f"/v1/plants/{plant['id']}/mutabakat", files={"dosya": ("ekim.csv", CSV_BOLUMLU, "text/csv")})
        assert r.status_code == 201, r.text
        assert r.json()["donem"] == "2026-10" and r.json()["kalem_sayisi"] == 10 and kayit[-1][0][:2] == ("musteri", "mutabakat_yukle")
        assert r.json()["surum_dogrulama"]["resmi_durum"] == "dogrulanmadi"
        assert c.post(f"/v1/plants/{plant['id']}/mutabakat?donem=2026-10&surum=on", files={"dosya": ("x.csv", b"a;b\n1;2\n", "text/csv")}).status_code == 422
        assert c.get(f"/v1/plants/{plant['id']}/mutabakat?surum=yok").status_code == 422
        g = c.get(f"/v1/plants/{plant['id']}/mutabakat?donem=2026-10"); assert g.status_code == 200
        j = g.json(); assert j["secili"]["donem"] == "2026-10" and j["secili"]["ozet"]["uyumlu"] == 2 and len(j["donemler"]) == 1 and j["surumler"][0]["kod"] == "on"
        assert j["secili"]["guvenilirlik"]["durum"] == "kismi" and j["guvenilirlik_etiketleri"]["senaryo"] == "Senaryo hesabı"
        assert c.get("/v1/plants/00000000-0000-0000-0000-000000000000/mutabakat").status_code == 404
        assert c.get(f"/v1/plants/{plant['id']}/mutabakat?uretim=uevm").status_code == 422   # v2.526
        monkeypatch.setattr(dz, "dokum", lambda t, p, gun, uretim=None: (_dokum(edt_borc=5460.0, edt_alacak=3150.0, kupst=300.0), {"fiyat": {"senaryo_saat": 0}, "saat_uretim_kaynak": ["sayac_olculmus"] * 48}))
        g2 = c.get(f"/v1/plants/{plant['id']}/mutabakat?donem=2026-10&uretim=sayac"); assert g2.status_code == 200 and g2.json()["secili"]["pvquant"]["uretim_kaynak"]["secim"] == "sayac" and g2.json()["uretim_ayari"] == "scada"
    finally:
        api_main.app.dependency_overrides.clear()


def test_surum_dogrulama_takvim():
    from datetime import datetime, timezone
    # Ekim 2026: ön bildirim 11.11.2026, nihai 15.11 Pazar → 16.11.2026 (02-01); 02.11 yüklemesi her iki sürüm için takvimden önce
    sd = ms.surum_dogrulama(date(2026, 10, 1), "nihai", datetime(2026, 11, 2, 6, 12, tzinfo=timezone.utc))
    assert sd["durum"] == "takvimden_once" and sd["beklenen_tarih"] == "2026-11-16" and sd["on_bildirim"] == "2026-11-11" and sd["resmi_durum"] == "dogrulanmadi"
    assert sd["itiraz_son"] == "2026-11-12 17:30" and sd["itiraz_60"] == "2027-01-15" and "çelişiyor" in sd["aciklama"]
    assert ms.surum_dogrulama(date(2026, 10, 1), "on", datetime(2026, 11, 11, 9, tzinfo=timezone.utc))["durum"] == "takvim_uyumlu"
    assert ms.surum_dogrulama(date(2026, 10, 1), "nihai", datetime(2026, 11, 16, 9, tzinfo=timezone.utc))["durum"] == "takvim_uyumlu"
    assert ms.surum_dogrulama(date(2026, 10, 1), "nihai", datetime(2026, 11, 15, 22, tzinfo=timezone.utc))["durum"] == "takvim_uyumlu"   # 16.11 01:00 TSİ
    # Kasım 2026: nihai 15.12 Salı
    assert ms.surum_dogrulama(date(2026, 11, 1), "nihai", datetime(2026, 12, 14, 9, tzinfo=timezone.utc))["beklenen_tarih"] == "2026-12-15"
