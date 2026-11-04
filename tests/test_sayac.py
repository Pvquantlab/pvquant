"""v2.523 (P4a) — Sayaç izleme: OSOS/MASS/EPYS dosya tanıma (15 dk → saat, nitelik, ayrı tarih+saat, XLSX, MWh), kayıt + yeniden yükleme (RLS'li
tablo, test DB), SCADA ↔ sayaç farkı (saf), veri geliş beklentisi ve 12. gün geri sayımı, lisanssız SCADA durumu + Karar 14909 göstergesi,
ayar doğrulama, olay türü «uzaktan açma yapılamadı», API uçları."""
from __future__ import annotations

import io
import uuid
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from pvquant.db import sistem_baglami
from pvquant.services import sayac_service as ss

IST = ZoneInfo("Europe/Istanbul")

# BEDAŞ OSOS portalı benzeri: 15 dk profil, Türkçe sayı, durum kodu (06-46: Estimated / FilledByDiff / ManuelData / NoData)
CSV_OSOS = ("Profil Tarihi;Aktif Üretim (kWh);Aktif Tüketim (kWh);Durum\n"
            "01.10.2026 08:00;120,5;0,2;Measured\n01.10.2026 08:15;130,0;0,1;Measured\n01.10.2026 08:30;140,0;0,0;Estimated\n01.10.2026 08:45;150,5;0,0;Measured\n"
            "01.10.2026 09:00;160,0;0,0;Measured\n01.10.2026 09:15;170,0;0,0;Measured\n01.10.2026 09:30;180,0;0,0;FilledByDiff\n01.10.2026 09:45;190,0;0,0;Measured\n"
            "01.10.2026 10:00;200,0;0,0;NoData\n").encode("utf-8")
# MASS benzeri: ayrı tarih ve saat sütunu, saatlik, İngilizce ondalık
CSV_MASS = "Tarih,Saat,Üretim (kWh)\n2026-10-02,00:00,0\n2026-10-02,08:00,512.25\n2026-10-02,09:00,640.0\n2026-10-02,10:00-11:00,700.5\n".encode("utf-8")


@pytest.fixture()
def kiraci():
    tid, pid = str(uuid.uuid4()), str(uuid.uuid4())
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO tenants(id, name, status) VALUES(:t, 'sayac-test', 'active')"), {"t": tid})
        s.execute(text("INSERT INTO plants(id, tenant_id, name, capacity_kwp, ac_limit_kw, lat, lon, tz, params_json) "
                       "VALUES(:p, :t, 'Sayaç GES', 1200, 1000, 37.0, 32.0, 'Europe/Istanbul', '{\"segment\": \"lisanssiz_dagitim\"}')"), {"p": pid, "t": tid})
    yield tid, {"id": pid, "name": "Sayaç GES", "capacity_kwp": 1200.0, "ac_limit_kw": 1000.0, "params_json": {"segment": "lisanssiz_dagitim"}}
    with sistem_baglami() as s:
        for t in ("sayac_saatlik", "sayac_yukleme", "olay", "scada_hourly", "ingestion_batches"):
            s.execute(text(f"DELETE FROM {t} WHERE tenant_id=:t"), {"t": tid})
        s.execute(text("DELETE FROM plants WHERE id=:p"), {"p": pid})
        s.execute(text("DELETE FROM tenants WHERE id=:t"), {"t": tid})


def test_dosya_oku_osos_15dk_nitelik():
    o = ss.dosya_oku(CSV_OSOS, "osos.csv")
    assert o["bicim"] == "csv" and o["cozunurluk_dk"] == 15 and o["n_satir"] == 9 and o["n_saat"] == 3
    r = {x["ts_utc"].astimezone(IST).hour: x for x in o["satirlar"]}
    assert r[8]["veris_kwh"] == 541.0 and r[8]["n_dilim"] == 4 and r[8]["nitelik"] == "tahmini" and r[8]["cekis_kwh"] == 0.3
    assert r[9]["veris_kwh"] == 700.0 and r[9]["nitelik"] == "doldurulmus" and r[10]["nitelik"] == "yok" and r[10]["n_dilim"] == 1
    assert o["nitelik_sayim"] == {"tahmini": 1, "doldurulmus": 1, "yok": 1} and o["kolonlar"]["veris"] == "Aktif Üretim (kWh)" and o["kolonlar"]["nitelik"] == "Durum"
    assert any("dilim eksik" in u for u in o["uyarilar"]) and o["bas"].tzinfo is not None and o["bas"] == datetime(2026, 10, 1, 5, tzinfo=timezone.utc)


def test_dosya_oku_mass_ayri_saat_ve_xlsx_mwh():
    o = ss.dosya_oku(CSV_MASS, "mass.csv")
    assert o["cozunurluk_dk"] == 60 and o["n_saat"] == 4 and o["nitelik_sayim"] == {"olculmus": 4}
    r = {x["ts_utc"].astimezone(IST).hour: x["veris_kwh"] for x in o["satirlar"]}
    assert r[8] == 512.25 and r[10] == 700.5 and r[0] == 0.0
    from openpyxl import Workbook
    wb = Workbook(); ws = wb.active
    ws.append(["Sayaç Verisi", "UEVÇB 40X..."]); ws.append(["Zaman", "Veriş (MWh)", "Çekiş (MWh)"])
    ws.append([datetime(2026, 10, 3, 12, 0), 0.65, 0.001]); ws.append([datetime(2026, 10, 3, 13, 0), 0.7, 0]); ws.append(["toplam", 1.35, 0.001])
    buf = io.BytesIO(); wb.save(buf)
    x = ss.dosya_oku(buf.getvalue(), "epys.xlsx")
    assert x["bicim"] == "xlsx" and x["n_saat"] == 2 and x["toplam_veris_kwh"] == 1350.0 and any("1 satır okunamadı" in u for u in x["uyarilar"])
    assert x["satirlar"][0]["veris_kwh"] == 650.0 and x["satirlar"][0]["cekis_kwh"] == 1.0
    with pytest.raises(ValueError, match="başlık satırı tanınmadı"):
        ss.dosya_oku("Sayaç No;Endeks\n1;12345\n".encode("utf-8"), "endeks.csv")   # başlık yok, satırlar zaman+kWh değil → alınmaz
    # belirsiz veriş sütunu: iki enerji sütunu, hiçbiri «veriş/üretim» demiyor → ilk seçilir, uyarı
    b = ss.dosya_oku("Tarih;Enerji A (kWh);Enerji B (kWh)\n01.10.2026 08:00;10;20\n".encode("utf-8"), "belirsiz.csv")
    assert b["satirlar"][0]["veris_kwh"] == 10.0 and any("ad ipucu olmadan" in u for u in b["uyarilar"])
    with pytest.raises(ValueError, match="boş"):
        ss.dosya_oku(b"", "bos.csv")
    # başlıksız: zaman + sayı
    h = ss.dosya_oku("2026-10-04 08:00;100\n2026-10-04 09:00;110\n".encode("utf-8"), "ham.csv")
    assert h["n_saat"] == 2 and any("başlık satırı tanınmadı" in u for u in h["uyarilar"])
    # yinelenen dilim (son satır geçerli, iki kez toplanmaz), gelecek tarih ve negatif değer alınmaz
    d = ss.dosya_oku(("Zaman;Veriş (kWh)\n2026-10-04 08:00;100\n2026-10-04 08:15;100\n2026-10-04 08:15;120\n2026-10-04 08:30;-5\n2026-10-04 08:45;100\n2026-12-01 08:00;50\n").encode("utf-8"),
                     "yinelenen.csv", simdi=datetime(2026, 11, 2, 9, tzinfo=timezone.utc))
    assert d["n_saat"] == 1 and d["satirlar"][0]["veris_kwh"] == 320.0 and d["satirlar"][0]["n_dilim"] == 3
    assert d["atlanan"] == {"okunamayan": 0, "gelecek": 1, "negatif": 1, "yinelenen": 1} and any("son satır alındı" in u for u in d["uyarilar"]) and any("gelecek tarihli" in u for u in d["uyarilar"])


def test_zaman_ve_nitelik():
    z = ss._zaman("01.10.2026", "24:00")
    assert z == datetime(2026, 10, 1, 21, tzinfo=timezone.utc)   # 24:00 → ertesi gün 00:00 TSİ
    assert ss._zaman("2026-10-01 00:00:00", "8") == datetime(2026, 10, 1, 5, tzinfo=timezone.utc)   # Excel tarih hücresi + ayrı saat
    assert ss._zaman("saat") is None and ss._zaman("31.02.2026 10:00") is None
    assert ss._nitelik("ManuelData") == "elle" and ss._nitelik("BackupMeterData") == "olculmus" and ss._nitelik("") == "olculmus" and ss._nitelik("Tahmini") == "tahmini"


def _idx(bas: datetime, n: int):
    return pd.date_range(bas, periods=n, freq="1h", tz="UTC")


def test_fark_df_saf():
    idx = _idx(datetime(2026, 10, 1, 5, tzinfo=timezone.utc), 6)   # 08:00–13:00 TSİ
    scada = pd.DataFrame({"kwh": [100, 200, 300, 400, 500, 600], "flag": "valid", "kaynak": ["scada_dosya"] * 5 + ["epias_seffaflik"]}, index=idx)
    sayac = pd.DataFrame({"veris_kwh": [95.0, 190.0, 285.0, 380.0], "nitelik": ["olculmus", "olculmus", "tahmini", "olculmus"], "kaynak": "osos"}, index=idx[:4])
    f = ss.fark_df(scada, sayac)
    assert len(f) == 1 and f.loc[0, "gun"] == "2026-10-01" and f.loc[0, "scada_kwh"] == 2100 and f.loc[0, "sayac_kwh"] == 950
    assert f.loc[0, "ortak_scada_kwh"] == 1000 and f.loc[0, "fark_kwh"] == -50 and f.loc[0, "fark_pct"] == -5.0
    assert f.loc[0, "saat_scada"] == 6 and f.loc[0, "saat_sayac"] == 4 and f.loc[0, "saat_ortak"] == 4 and f.loc[0, "saat_tahmini"] == 1
    assert f.loc[0, "saat_olculmus"] == 3 and f.loc[0, "olc_fark_pct"] == -5.0   # (95+190+380 − (100+200+400)) / 700
    assert f["saat_olculmus"].sum() == f["saat_ortak"].sum() - f["saat_tahmini"].sum()   # ölçülmüş ortak = ortak − tahmini/doldurulmuş/yok (elle de ölçülmüş sayılmaz)
    e = ss.fark_df(scada, sayac.assign(nitelik=["olculmus", "elle", "tahmini", "olculmus"]))
    assert e.loc[0, "saat_olculmus"] == 2 and e.loc[0, "saat_tahmini"] == 1 and e.loc[0, "saat_ortak"] == 4
    bos = ss.fark_df(scada.iloc[:0], sayac.iloc[:0]); assert bos.empty
    # yalnız sayaç varsa fark yok (ortak saat 0), yüzde NaN
    g = ss.fark_df(scada.iloc[:0], sayac); assert g.loc[0, "saat_ortak"] == 0 and pd.isna(g.loc[0, "fark_pct"])


def test_kaydet_oku_fark_gelis(kiraci):
    tid, plant = kiraci
    k = ss.kaydet(tid, plant, CSV_OSOS, "osos_ekim.csv", "osos", yukleyen=None)
    assert k["n_saat"] == 3 and k["kaynak_etiket"].startswith("OSOS") and len(k["sha256"]) == 64
    # yeniden yükleme aynı saati günceller (düzeltme), tarihçe iki kayıt
    k2 = ss.kaydet(tid, plant, CSV_OSOS.replace(b"120,5", b"220,5"), "osos_ekim_v2.csv", "osos")
    y = ss.yuklemeler(tid, plant["id"]); assert len(y) == 2 and y[0]["yukleme_id"] == k2["yukleme_id"] and y[0]["n_saat"] == 3
    bas, bit = datetime(2026, 10, 1, tzinfo=timezone.utc), datetime(2026, 10, 3, tzinfo=timezone.utc)
    df = ss.sayac_oku(tid, plant["id"], bas, bit); assert len(df) == 3 and df.iloc[0]["veris_kwh"] == 641.0
    # ikinci kaynak (epys) aynı saat: öncelik epys
    ss.kaydet(tid, plant, "Zaman;Veriş (kWh)\n01.10.2026 08:00;600\n".encode("utf-8"), "epys.csv", "epys")
    df = ss.sayac_oku(tid, plant["id"], bas, bit); assert df.iloc[0]["veris_kwh"] == 600.0 and df.iloc[0]["kaynak"] == "epys" and len(df) == 3
    with pytest.raises(ValueError, match="kaynak"):
        ss.kaydet(tid, plant, CSV_OSOS, "x.csv", "bilinmeyen")
    # SCADA satırları (dosya + Şeffaflık partisi) → fark ve kaynak sayımı
    with sistem_baglami() as s:
        bid = s.execute(text("INSERT INTO ingestion_batches(tenant_id, plant_id, filename) VALUES(:t, :p, 'epias_realtime') RETURNING id"), {"t": tid, "p": plant["id"]}).scalar()
        for h, kwh, b in ((5, 700.0, None), (6, 750.0, None), (7, 800.0, bid)):
            s.execute(text("INSERT INTO scada_hourly(tenant_id, plant_id, ts_utc, power_kw, energy_kwh, flag, batch_id) VALUES(:t, :p, :ts, :k, :k, 'valid', :b)"),
                      {"t": tid, "p": plant["id"], "ts": datetime(2026, 10, 1, h, tzinfo=timezone.utc), "k": kwh, "b": bid if b else None})
    f = ss.fark(tid, plant, gun=30, bugun=date(2026, 10, 20))
    assert f["toplam"]["saat_ortak"] == 3 and f["toplam"]["ortak_scada_kwh"] == 2250.0 and f["toplam"]["ortak_sayac_kwh"] == 1500.0 and f["toplam"]["fark_pct"] == -33.3
    assert f["kaynak_sayim"]["scada_dosya"] == 2 and f["kaynak_sayim"]["epias_seffaflik"] == 1 and f["kaynak_sayim"]["sayac_tahmini"] == 0 and f["kaynak_sayim"]["sayac_doldurulmus"] == 1 and f["kaynak_sayim"]["sayac_yok"] == 1   # 08:00 epys ölçülmüş osos tahminiyi geçer
    assert f["sayac_kaynak_sayim"] == {"osos": 2, "epys": 1} and f["en_buyuk_fark"]["gun"] == "2026-10-01" and f["gunler"][0]["saat_tahmini"] == 2
    # yalnız ölçülmüş: 08:00 epys 600 ↔ 700 → −14,3 %; tahmini dâhil: 1500 ↔ 2250 → −33,3 %; kapsam 3/720
    assert f["olculmus"] == {"saat": 1, "scada_kwh": 700.0, "sayac_kwh": 600.0, "fark_kwh": -100.0, "fark_pct": -14.3}
    assert f["tahmini_dahil"]["saat"] == 3 and f["tahmini_dahil"]["fark_pct"] == -33.3 and f["kapsam"]["ortak_saat"] == 3 and f["kapsam"]["ortak_pct"] == 0.4 and f["kapsam"]["yalniz_scada_saat"] == 0
    csv = ss.fark_csv(f, "Sayaç GES"); assert csv.startswith("﻿santral;gun;") and "Sayaç GES;2026-10-01;2250,0;1500,0" in csv
    # geliş: 15 dk sayaç, şimdi 02.10.2026 12:00 TSİ → ay başından 10:00'a kadar 34 beklenen saat, 3 sayaç saati var → 31 eksik; dönem Eylül → 12.10 17:30
    pj = {"sayac_turu": "15dk_endeks"}
    g = ss.gelis(tid, plant, pj, simdi=datetime(2026, 10, 2, 9, tzinfo=timezone.utc))
    assert g["ay_beklenen_saat"] == 34 and g["ay_sayac_saat"] == 3 and g["ay_eksik_saat"] == 31 and g["beklenen"]["kesinlik"] == "belirsiz"
    assert g["beklenen"]["son_beklenen_dilim"] == "09:00–10:00" and g["beklenen"]["son_beklenen_saat"].startswith("2026-10-02T09:00")   # 12:00 TSİ − 2 sa = 10:00 sınırı; son dilim 09–10
    sn = g["siniflama"]; assert sn["gecen_saat"] == 36 and sn["vadesi_gelen"] == 34 and sn["vadesi_gelmemis"] == 2 and sn["yuklu"] == 3 and sn["yuklu_tahmini"] == 2 and sn["yuklu_olculmus"] == 1 and sn["eksik"] == 31
    k = g["donemler"][0]["kapsam"]; assert k == {"vadesi_gelen": 720, "yuklu": 0, "olculmus": 0, "tahmini": 0, "eksik": 720, "tam_ay": True}   # Eylül: tam ay, yüklü yok
    # ay sınırı: 1 Ekim 00:30 TSİ → vadesi gelen 0, eksik 0, geçen 0
    g0 = ss.gelis(tid, plant, pj, simdi=datetime(2026, 9, 30, 21, 30, tzinfo=timezone.utc)); assert g0["ay"] == "2026-10" and g0["siniflama"]["vadesi_gelen"] == 0 and g0["ay_eksik_saat"] == 0
    assert f["pencere_saat"] == 720 and f["bas"] == "2026-09-21" and f["bit"] == "2026-10-20"   # bugün dâhil 30 gün
    assert g["son_sayac"].startswith("2026-10-01T07:00") and g["son_scada"].startswith("2026-10-01T07:00") and g["donemler"][0]["donem"] == "2026-09"
    assert g["donemler"][0]["itiraz_son"] == "2026-10-12 17:30" and g["donemler"][0]["sayac_veri"] == "2026-10-10" and not g["donemler"][0]["gecti"] and len(g["donemler"]) == 1
    g2 = ss.gelis(tid, plant, {"sayac_turu": "diger"}, simdi=datetime(2026, 10, 20, 9, tzinfo=timezone.utc))
    assert g2["ay_eksik_saat"] is None and g2["beklenen"]["kesinlik"] == "belirsiz" and g2["donemler"][0]["gecti"] and g2["donemler"][1]["donem"] == "2026-10"
    assert g2["donemler"][1]["kapsam"]["vadesi_gelen"] == 0 and not g2["donemler"][1]["kapsam"]["tam_ay"]   # diğer sayaç: süren ay henüz vadesi gelmedi
    g3 = ss.gelis(tid, plant, {}, simdi=datetime(2026, 10, 20, 9, tzinfo=timezone.utc)); assert g3["sayac_turu"] is None and "seçin" in g3["beklenen"]["not"]


def test_program_df_sayac_girdisi(kiraci):
    """v2.526 (P4a-2): uzlaştırma girdisi «sayaç» — sayaç satırı olan saatlerde gerçekleşen sayaçtan (öncelik epys), niteliğe göre kaynak etiketi; kalan saat SCADA."""
    from pvquant.services import dengesizlik_service as dz
    tid, plant = kiraci
    ss.kaydet(tid, plant, CSV_OSOS, "osos_ekim.csv", "osos")                                                   # 08–10 TSİ = 05–07 UTC
    ss.kaydet(tid, plant, "Zaman;Veriş (kWh)\n01.10.2026 08:00;600\n".encode("utf-8"), "epys.csv", "epys")   # 08 TSİ epys öncelikli, ölçülmüş
    with sistem_baglami() as s:
        for h, kwh in ((5, 700.0), (6, 750.0), (7, 800.0), (8, 900.0)):
            s.execute(text("INSERT INTO scada_hourly(tenant_id, plant_id, ts_utc, power_kw, energy_kwh, flag) VALUES(:t, :p, :ts, :k, :k, 'valid')"),
                      {"t": tid, "p": plant["id"], "ts": datetime(2026, 10, 1, h, tzinfo=timezone.utc), "k": kwh})
    d0 = dz.program_df(tid, plant["id"], 30); assert list(d0["gercek_kw"]) == [700.0, 750.0, 800.0, 900.0] and set(d0["uretim_kaynak"]) == {"scada"}
    d1 = dz.program_df(tid, plant["id"], 30, uretim="sayac")
    assert list(d1["gercek_kw"]) == [600.0, 700.0, 200.0, 900.0] and list(d1["uretim_kaynak"]) == ["sayac_olculmus", "sayac_tahmini", "sayac_tahmini", "scada"]
    assert d0["cekis_kw"].isna().all() and d1["cekis_kw"].notna().sum() >= 1 and d1["cekis_kw"].iloc[3] != d1["cekis_kw"].iloc[3]   # v2.532: çekiş → UEÇM; SCADA saatinde NaN
    assert dz.uretim_secimi({"uzlastirma_girdi": "sayac"}) == "sayac" and dz.uretim_secimi({}) == "scada" and dz.uretim_secimi({"uzlastirma_girdi": "x"}) == "scada"
    # ayar: santral seçimi döküm girdilerine iner
    g = dz._girdiler(tid, {**plant, "params_json": {**plant["params_json"], "uzlastirma_girdi": "sayac"}}, 30)
    assert g["uretim"] == "sayac" and list(g["df"]["gercek_kw"])[:3] == [600.0, 700.0, 200.0]
    assert ss.ayar_dogrula({"uzlastirma_girdi": "sayac"}) == {"uzlastirma_girdi": "sayac"} and ss.ayar_dogrula({"uzlastirma_girdi": ""}) == {"uzlastirma_girdi": None}
    with pytest.raises(ValueError, match="uzlastirma_girdi"):
        ss.ayar_dogrula({"uzlastirma_girdi": "uevm"})
    o = ss.ozet(tid, {**plant, "params_json": {**plant["params_json"], "uzlastirma_girdi": "sayac"}}, 30)
    assert o["ayar"]["uzlastirma_girdi"] == "sayac" and [x["kod"] for x in o["uretim_secenekleri"]] == ["scada", "sayac"]


def test_scada_durumu_ve_gosterge():
    plant = {"id": "x", "capacity_kwp": 1200.0, "ac_limit_kw": 1000.0}
    assert ss.scada_durumu(plant, {}, "lisansli_serbest", date(2026, 11, 2)) is None
    d = ss.scada_durumu(plant, {}, "lisanssiz_dagitim", date(2026, 11, 2))
    assert d["yukumlu"] and d["kurulu_kw"] == 1000.0 and d["durum"] is None and d["kalemler"] == [] and d["toplam_tl"] is None and d["aski_kalan_gun"] == 179 and not d["aski_gecti"]
    assert d["durum_kaynagi"] == "beyan" and d["tutar_niteligi"] == "varsayimsal" and d["anlasma"] == "dagitim" and d["m75_kapsam"]
    kucuk = ss.scada_durumu({"id": "y", "capacity_kwp": 40.0}, {"scada_durum": "yok", "sistem_kullanim_bedeli_tl_ay": 5000}, "lisanssiz_dagitim", date(2026, 11, 2))
    assert not kucuk["yukumlu"] and kucuk["kalemler"] == [] and kucuk["kurulu_kaynak"] == "kurulu güç (kWp)"
    # (f) yalnız m.75(4) kapsamı (900 kW+): 500 kW tesiste entegrasyon yok → gösterge yok, açıklama var
    orta = ss.scada_durumu({"id": "z", "capacity_kwp": 600.0, "ac_limit_kw": 500.0}, {"scada_durum": "yok", "sistem_kullanim_bedeli_tl_ay": 5000}, "lisanssiz_dagitim", date(2026, 11, 2))
    assert orta["yukumlu"] and not orta["m75_kapsam"] and orta["kalemler"] == [] and "m.75(4) kapsamı dışı" in orta["uygulanmayan"][0]
    # v2.538 (DK-656): kopuk 18.09'dan beri (45 gün); dağıtım şirketi uyarısı 18.09 → bir aylık süre 18.10'da dolar; (ç) bu ayın süre sonrası günleri
    # (Kasım 1–2 = 2 gün), (g) uygulanan 1 Kasım hariç → 1 gün; (ç) askıda değil
    pj = {"scada_durum": "kopuk", "scada_kopukluk_baslangic": "2026-09-18", "scada_uyari_tarihi": "2026-09-18", "sistem_kullanim_bedeli_tl_ay": 12000, "uzaktan_acma_var": True}
    e = ss.scada_durumu(plant, pj, "lisanssiz_dagitim", date(2026, 11, 2), uzaktan_acma_ay=2, uzaktan_acma_gunleri={date(2026, 11, 1)})
    assert e["kopukluk_gun"] == 45 and {k["kod"] for k in e["kalemler"]} == {"uzaktan_acma", "onarim_gecikti"} and e["uyari_sure_sonu"] == "2026-10-18"
    k = {x["kod"]: x for x in e["kalemler"]}
    assert k["uzaktan_acma"]["tutar_tl"] == 24000.0 and k["onarim_gecikti"]["tutar_tl"] == 120.0 and k["onarim_gecikti"]["kesinlik"] == "belirsiz" and e["toplam_tl"] == 24120.0
    assert k["uzaktan_acma"]["aski"] == "kapsamda" and k["onarim_gecikti"]["aski"] == "askida_degil" and e["toplam_aski_tl"] == 24000.0 and e["toplam_aski_disi_tl"] == 120.0
    assert e["aski_kesinlik"] == "teyit" and "(ç) bendi" in e["aski_kapsami"]
    # uyarı tarihi girilmemişse (ç) üretilmez, eksik girdi notu düşer; uyarı yeni ise süre dolmamış → (ç) yok
    u = ss.scada_durumu(plant, {k2: v for k2, v in pj.items() if k2 != "scada_uyari_tarihi"}, "lisanssiz_dagitim", date(2026, 11, 2))
    assert [x["kod"] for x in u["kalemler"]] == [] and any("uyarı tarihi girilmedi" in n for n in u["uygulanmayan"])
    assert [x["kod"] for x in ss.scada_durumu(plant, {**pj, "scada_uyari_tarihi": "2026-10-20"}, "lisanssiz_dagitim", date(2026, 11, 2))["kalemler"]] == []
    # iletime bağlı lisanssız: anlaşma TEİAŞ'la, gösterge uygulanmaz
    y = ss.scada_durumu(plant, {"scada_durum": "yok", "sistem_kullanim_bedeli_tl_ay": 12000}, "lisanssiz_iletim", date(2026, 11, 2), uzaktan_acma_ay=5)
    assert y["kalemler"] == [] and y["anlasma"] == "iletim" and "TEİAŞ" in y["uygulanmayan"][0]
    # dağıtıma bağlı, 1.000 kW, 5 olay → (g) en çok 3 kat
    z = ss.scada_durumu(plant, {"scada_durum": "yok", "sistem_kullanim_bedeli_tl_ay": 12000}, "lisanssiz_dagitim", date(2026, 11, 2), uzaktan_acma_ay=5)
    assert {x["kod"]: x["tutar_tl"] for x in z["kalemler"]} == {"entegrasyon_yok": 12000.0, "uzaktan_acma": 36000.0}
    b = ss.scada_durumu(plant, {"scada_durum": "yok"}, "lisanssiz_dagitim", date(2026, 11, 2)); assert b["kalemler"][0]["tutar_tl"] is None and b["toplam_tl"] is None


def test_ayar_dogrula():
    a = ss.ayar_dogrula({"sayac_turu": "15dk_endeks", "scada_durum": "kopuk", "scada_kopukluk_baslangic": "2026-10-01T00:00", "uzaktan_acma_var": True, "sistem_kullanim_bedeli_tl_ay": "12000"})
    assert a == {"sayac_turu": "15dk_endeks", "scada_durum": "kopuk", "scada_kopukluk_baslangic": "2026-10-01", "uzaktan_acma_var": True, "sistem_kullanim_bedeli_tl_ay": 12000.0}
    assert ss.ayar_dogrula({"sayac_turu": "", "sistem_kullanim_bedeli_tl_ay": None}) == {"sayac_turu": None, "sistem_kullanim_bedeli_tl_ay": None} and ss.ayar_dogrula({}) == {}
    for g in ({"sayac_turu": "x"}, {"scada_durum": "bilinmez"}, {"scada_kopukluk_baslangic": "dün"}, {"scada_kopukluk_baslangic": "2099-01-01"}, {"uzaktan_acma_var": "evet"}, {"sistem_kullanim_bedeli_tl_ay": -1}):
        with pytest.raises(ValueError):
            ss.ayar_dogrula(g)


def test_olay_turu_uzaktan_acma(kiraci):
    from pvquant.services import olay_service as os_
    tid, plant = kiraci
    assert "uzaktan_acma" in os_.TURLER and not os_.TUR_KURAL["uzaktan_acma"]["eak_dusur"] and not os_.TUR_KURAL["uzaktan_acma"]["istisna"]
    o = os_.ekle(tid, plant, {"tur": "uzaktan_acma", "baslangic": "2026-11-01T14:00+03:00", "bitis": "2026-11-01T14:10+03:00", "neden": "RTU yanıt vermedi"})
    assert o["tur_etiket"] == "Uzaktan açma yapılamadı" and o["eak_gerekcesi"] is None
    oz = ss.ozet(tid, {**plant, "params_json": {"segment": "lisanssiz_dagitim", "scada_durum": "bagli", "sistem_kullanim_bedeli_tl_ay": 1000}}, gun=30,
                 simdi=datetime(2026, 11, 2, 9, tzinfo=timezone.utc))
    assert oz["scada"]["uzaktan_acma_ay"] == 1 and oz["scada"]["kalemler"][0]["kod"] == "uzaktan_acma" and oz["scada"]["kalemler"][0]["tutar_tl"] == 1000.0 and oz["segment"] == "lisanssiz_dagitim"
    assert oz["ayar"]["scada_durum"] == "bagli" and oz["gelis"]["sayac_turu"] is None and oz["fark"]["pencere_gun"] == 30 and len(oz["kaynaklar"]) == 4 and oz["scada_notu"] is None
    lis = ss.ozet(tid, {**plant, "params_json": {"segment": "lisansli_serbest", "scada_durum": "yok"}}, gun=30, simdi=datetime(2026, 11, 2, 9, tzinfo=timezone.utc))
    assert lis["scada"] is None and lis["scada_notu"].startswith("Lisanslı santral")
    assert ss.ozet(tid, {**plant, "params_json": {}}, gun=30, simdi=datetime(2026, 11, 2, 9, tzinfo=timezone.utc))["scada_notu"].startswith("Segment seçilmedi")
    # EAK dosyasını etkilemez
    etki = os_.saatlik_etki(tid, plant, date(2026, 11, 1)); assert etki["saatler"] == {}


def test_api_sayac_uclari(kiraci, monkeypatch):
    import apps.api.main as api_main
    from apps.api.deps import gecerli_kullanici
    from pvquant.services import plant_service
    tid, plant = kiraci
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": tid, "role": "admin", "exp": 0}
    satir = {"id": plant["id"], "name": "Sayaç GES", "capacity_kwp": 1200.0, "ac_limit_kw": 1000.0, "params_json": {"segment": "lisanssiz_dagitim"}}
    monkeypatch.setattr(plant_service, "getir", lambda t, p: satir if p == plant["id"] else None)
    kayit = []
    monkeypatch.setattr(api_main._denetim, "kaydet", lambda *a, **k: kayit.append((a, k)))
    c = TestClient(api_main.app)
    try:
        r = c.post(f"/v1/plants/{plant['id']}/sayac?kaynak=osos", files={"dosya": ("osos.csv", CSV_OSOS, "text/csv")})
        assert r.status_code == 201, r.text
        assert r.json()["n_saat"] == 3 and r.json()["cozunurluk_dk"] == 15 and kayit[-1][0][:2] == ("musteri", "sayac_yukle")
        assert c.post(f"/v1/plants/{plant['id']}/sayac?kaynak=yok", files={"dosya": ("x.csv", CSV_OSOS, "text/csv")}).status_code == 422
        assert c.post(f"/v1/plants/{plant['id']}/sayac", files={"dosya": ("x.csv", b"a;b\n1;2\n", "text/csv")}).status_code == 422
        a = c.put(f"/v1/plants/{plant['id']}/sayac-ayar", json={"sayac_turu": "15dk_endeks", "scada_durum": "yok", "sistem_kullanim_bedeli_tl_ay": 8000})
        assert a.status_code == 200, a.text
        j = a.json(); assert j["ayar"]["sayac_turu"] == "15dk_endeks" and j["scada"]["durum"] == "yok" and j["scada"]["kalemler"][0]["tutar_tl"] == 8000.0 and kayit[-1][0][1] == "sayac_ayar"
        assert c.put(f"/v1/plants/{plant['id']}/sayac-ayar", json={"scada_durum": "x"}).status_code == 422
        g = c.get(f"/v1/plants/{plant['id']}/sayac?gun=30"); assert g.status_code == 200 and g.json()["gelis"]["sayac_turu"] == "15dk_endeks" and len(g.json()["yuklemeler"]) == 1
        assert c.get(f"/v1/plants/{plant['id']}/sayac?gun=3").status_code == 422
        csv = c.get(f"/v1/plants/{plant['id']}/sayac.csv?gun=30"); assert csv.status_code == 200 and csv.text.startswith("﻿santral;gun;")
        assert c.get("/v1/plants/00000000-0000-0000-0000-000000000000/sayac").status_code == 404
    finally:
        api_main.app.dependency_overrides.clear()
