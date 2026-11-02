"""v2.521 (P1a) — olay kaydı: doğrulama, ekleme/güncelleme/listeleme (RLS'li tablo, gerçek test DB), saatlik EAK etkisi ve gerekçe
paylaşımı (EAK.csv), kullanılabilirlik istisna saatleri, aylık arıza sayacı (olay ∨ elle), dâhilî bilgi eşiği, hasar dosyası CSV, API uçları."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from pvquant.db import sistem_baglami
from pvquant.ext.turkiye import kgup as kg
from pvquant.services import olay_service as os_

IST = ZoneInfo("Europe/Istanbul")


@pytest.fixture()
def kiraci():
    tid, pid = str(uuid.uuid4()), str(uuid.uuid4())
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO tenants(id, name, status) VALUES(:t, 'olay-test', 'active')"), {"t": tid})
        s.execute(text("INSERT INTO plants(id, tenant_id, name, capacity_kwp, lat, lon, tz) VALUES(:p, :t, 'Olay GES', 40000, 37.0, 32.0, 'Europe/Istanbul')"), {"p": pid, "t": tid})
    yield tid, {"id": pid, "name": "Olay GES", "capacity_kwp": 40000.0, "params_json": {"ariza_sayisi_ay": 2}}
    with sistem_baglami() as s:
        s.execute(text("DELETE FROM olay WHERE tenant_id=:t"), {"t": tid})
        s.execute(text("DELETE FROM plants WHERE id=:p"), {"p": pid})
        s.execute(text("DELETE FROM tenants WHERE id=:t"), {"t": tid})


def test_dogrula():
    v = os_.dogrula({"tur": "ariza", "baslangic": "2026-11-02T09:30", "bitis": "2026-11-02T12:00", "etkilenen_kw": "1500", "neden": "invertör 3"}, 40000)
    assert v["baslangic"].tzinfo is timezone.utc and v["baslangic"].astimezone(IST).hour == 9 and v["etkilenen_kw"] == 1500.0 and v["eak_gerekcesi"] == "kaynak_yetersizligi"
    assert os_.dogrula({"tur": "sebeke_kesintisi", "baslangic": "2026-11-02T09:30"}, 40000)["eak_gerekcesi"] == "dissal"
    assert os_.dogrula({"tur": "talimat_yat", "baslangic": "2026-11-02T09:30", "eak_gerekcesi": "mucbir"}, 40000)["eak_gerekcesi"] is None   # talimat EAK'yi değiştirmez
    # 02.11 üçüncü inceleme: hasar «mücbir sebep»i otomatik seçmez (varsayılan kaynak yetersizliği; açıkça seçilirse kalır); sınır AC (kWp değil)
    assert os_.dogrula({"tur": "hasar", "baslangic": "2026-11-02T09:30"}, 40000)["eak_gerekcesi"] == "kaynak_yetersizligi"
    assert os_.dogrula({"tur": "hasar", "baslangic": "2026-11-02T09:30", "eak_gerekcesi": "mucbir"}, 40000)["eak_gerekcesi"] == "mucbir"
    assert os_._sinir_kw({"capacity_kwp": 15230.0, "ac_limit_kw": 12000.0}) == 12000.0 and os_._sinir_kw({"capacity_kwp": 15230.0}) == 15230.0
    with pytest.raises(ValueError, match="AC"):
        os_.dogrula({"tur": "planli_bakim", "baslangic": "2026-11-02T09:30", "etkilenen_kw": 15230}, 12000.0)
    for kotu in ({"tur": "x", "baslangic": "2026-11-02T09:30"}, {"tur": "ariza"}, {"tur": "ariza", "baslangic": "2026-11-02T09:30", "bitis": "2026-11-02T09:00"},
                 {"tur": "ariza", "baslangic": "2026-11-02T09:30", "etkilenen_kw": 50000}, {"tur": "ariza", "baslangic": "2026-11-02T09:30", "etkilenen_kw": -1},
                 {"tur": "ariza", "baslangic": "2026-11-02T09:30", "eak_gerekcesi": "yok"}, {"tur": "ariza", "baslangic": "2030-01-01T00:00"}, {"tur": "ariza", "baslangic": "dün"}):
        with pytest.raises(ValueError):
            os_.dogrula(kotu, 40000, bugun=datetime(2026, 11, 1, tzinfo=timezone.utc))


def test_ekle_guncelle_listele_ve_sayac(kiraci):
    tid, plant = kiraci
    # 02.11 v2.525: test saat bağımlıydı (02.11 09:30 sabit; o saat geçince «planlı» → «sürüyor»). Gelecek olaylar gelecek ayın
    # ilk günlerine (aynı ay içinde kalır, en az 1 gün ileride); geçmiş olaylar Ekim 2026 sabit.
    bugun = datetime.now(IST).date()
    g1 = (bugun.replace(day=1) + timedelta(days=32)).replace(day=1)   # gelecek ayın 1'i
    G = lambda n, hm: f"{(g1 + timedelta(days=n)).isoformat()}T{hm}"
    o1 = os_.ekle(tid, plant, {"tur": "ariza", "baslangic": G(0, "09:30"), "etkilenen_kw": 1500, "neden": "invertör 3"})
    assert o1["acik"] and o1["durum"] == "acik" and o1["baslangic"].startswith(G(0, "09:30")) and o1["tur_etiket"] == "Arıza"
    o2 = os_.ekle(tid, plant, {"tur": "planli_bakim", "baslangic": "2026-11-05T08:00", "bitis": "2026-11-05T17:00", "etkilenen_kw": 40000})
    o3 = os_.ekle(tid, plant, {"tur": "ariza", "baslangic": "2026-10-20T09:30", "bitis": "2026-10-20T11:00"})
    assert o3["durum"] == "kapali"
    o4 = os_.ekle(tid, plant, {"tur": "ariza", "baslangic": "2026-10-25T09:30"}); assert o4["durum"] == "acik"   # geçmişte başlayan açık olay
    assert o4["evre"] == "suruyor" and o1["evre"] == "planli" and o3["evre"] == "bitti"   # evre: görünen; DB durumu acik/kapali
    assert os_.ariza_sayisi(tid, plant["id"], g1) == 1 and os_.ariza_sayisi(tid, plant["id"], date(2026, 10, 1)) == 2
    e = os_.ariza_sayisi_etkin(tid, plant, g1); assert e == {"sayi": 2, "olay": 1, "elle": 2, "kaynak": "elle giriş"}
    os_.ekle(tid, plant, {"tur": "ariza", "baslangic": G(1, "09:30"), "bitis": G(1, "10:00")}); os_.ekle(tid, plant, {"tur": "ariza", "baslangic": G(2, "09:30"), "bitis": G(2, "10:00")})
    assert os_.ariza_sayisi_etkin(tid, plant, g1) == {"sayi": 3, "olay": 3, "elle": 2, "kaynak": "olay kaydı"}
    # kapatma, iptal, geçersiz güncelleme
    k = os_.guncelle(tid, plant, o4["id"], {"bitis": "2026-10-25T12:00", "kanit": "servis raporu 1234"}); assert k["durum"] == "kapali" and k["kanit"] == "servis raporu 1234"
    k2 = os_.guncelle(tid, plant, o1["id"], {"bitis": G(0, "12:00")}); assert k2["durum"] == "acik"   # bitiş gelecekte → hâlâ açık
    with pytest.raises(ValueError):
        os_.guncelle(tid, plant, o1["id"], {"bitis": G(0, "09:00")})
    ip = os_.guncelle(tid, plant, o2["id"], {"durum": "iptal"}); assert ip["durum"] == "iptal"
    assert os_.guncelle(tid, plant, str(uuid.uuid4()), {"neden": "x"}) is None
    liste = os_.listele(tid, plant["id"], 400); assert len(liste) == 5 and all(x["durum"] != "iptal" for x in liste)
    assert len(os_.listele(tid, plant["id"], 400, iptal_dahil=True)) == 6 and liste[0]["baslangic"] > liste[-1]["baslangic"]
    dosya = os_.csv_metni(os_.listele(tid, plant["id"], 400, iptal_dahil=True), "Olay GES")   # 02.11: dosyadaki evre ekranla aynı («geçersiz», «iptal» değil)
    assert ";geçersiz;" in dosya and ";iptal;" not in dosya
    # RLS: başka kiracı görmez
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO tenants(id, name, status) VALUES(:t, 'baska', 'active')"), {"t": "00000000-0000-4000-8000-000000000099"})
    try:
        assert os_.listele("00000000-0000-4000-8000-000000000099", plant["id"], 400) == []
    finally:
        with sistem_baglami() as s:
            s.execute(text("DELETE FROM tenants WHERE id='00000000-0000-4000-8000-000000000099'"))


def test_saatlik_etki_istisna_ve_dahili(kiraci):
    tid, plant = kiraci
    os_.ekle(tid, plant, {"tur": "ariza", "baslangic": "2026-11-10T09:30", "bitis": "2026-11-10T11:10", "etkilenen_kw": 10000})
    os_.ekle(tid, plant, {"tur": "sebeke_kesintisi", "baslangic": "2026-11-10T10:00", "bitis": "2026-11-10T12:00"})      # tesisin tamamı, dışsal
    os_.ekle(tid, plant, {"tur": "talimat_yat", "baslangic": "2026-11-10T13:00", "bitis": "2026-11-10T14:00", "etkilenen_kw": 5000})   # EAK'yi değiştirmez
    e = os_.saatlik_etki(tid, plant, date(2026, 11, 10))
    # kısmi saat orantılı: 09:30–11:10 arıza 10 MW → 9. saat 5.000, 10. saat 10.000, 11. saat 1.667; 10:00–12:00 kesinti tesisin tamamı → EAK tabanı 40.000 ile sınır
    assert sorted(e["saatler"]) == [9, 10, 11] and e["saatler"][9]["toplam_kw"] == 5000 and e["saatler"][10]["toplam_kw"] == 40000 and e["saatler"][11]["toplam_kw"] == 40000
    assert e["saatler"][9]["oran"] == 0.5 and e["saatler"][10]["oran"] == 1.0 and e["taban_kw"] == 40000
    assert e["saatler"][10]["gerekce"] == {"kaynak_yetersizligi": 10000.0, "dissal": 40000.0} and e["saatler"][11]["gerekce"] == {"kaynak_yetersizligi": 1666.7, "dissal": 40000.0}
    assert e["olay_sayisi"] == 2 and 13 not in e["saatler"]
    # AC sınırı: tesisin tamamı = günün EAK tabanı (12 MW AC), kWp değil
    e2 = os_.saatlik_etki(tid, {**plant, "ac_limit_kw": 12000.0}, date(2026, 11, 10)); assert e2["taban_kw"] == 12000 and e2["saatler"][10]["toplam_kw"] == 12000
    # çakışma uyarısı: aynı saatlerde ikinci kayıt engellenmez, uyarı döner
    c = os_.ekle(tid, plant, {"tur": "hasar", "baslangic": "2026-11-10T10:30", "bitis": "2026-11-10T11:00", "etkilenen_kw": 500})
    assert c["uyari"].startswith("Aynı saatlerde 2 kayıt daha var") and len(c["cakisan"]) == 2 and "iki kez düşürür" in c["uyari"]   # 02.11: dürüst — kayıtlar toplanır
    assert "uyari" not in os_.ekle(tid, plant, {"tur": "ariza", "baslangic": "2026-11-20T10:30", "bitis": "2026-11-20T11:00"})
    # EAK.csv gerekçe paylaşımı: kurulu 40 MW, saat 10 EAK 0 → eksik 40 → dışsal 40 (kaynak yetersizliğine kalan 0); saat 9 EAK 30 → eksik 10 → kaynak yetersizliği
    tablo = pd.DataFrame({"saat": [9, 10, 23], "eak_mw": [30.0, 0.0, 0.0], "kgup_mwh": [20.0, 0.0, 0.0]})
    metin = kg.eak_csv_metni(tablo, 40.0, gerekce_saat={9: {"kaynak_yetersizligi": 10.0}, 10: {"kaynak_yetersizligi": 10.0, "dissal": 40.0}})
    satir = {h.split(",")[0]: h.split(",") for h in metin.strip().split("\r\n")[1:]}
    assert satir["9"][3] == "10" and satir["9"][6] == "" and satir["10"][6] == "40" and satir["10"][3] == "" and satir["23"][3] == "40"
    # kullanılabilirlik istisnası: şebeke kesintisi ve talimat saatleri; arıza istisna değil
    bas = datetime(2026, 11, 10, 0, tzinfo=IST).astimezone(timezone.utc); bit = bas + timedelta(days=1)
    ist = os_.istisna_saatleri(tid, plant["id"], bas, bit)
    saatler = sorted(t.astimezone(IST).hour for t in ist); assert saatler == [10, 11, 13]
    # dâhilî bilgi: 10 MW tesis eşiği altı; 30 MW üstü eşik; portföy 50 MW
    assert os_.dahili_bilgi({"tur": "ariza", "etkilenen_kw": 10000, "baslangic": datetime(2026, 11, 10, 9, 30, tzinfo=IST)}, 40000) is None
    d = os_.dahili_bilgi({"tur": "ariza", "etkilenen_kw": None, "baslangic": datetime(2026, 11, 10, 9, 30, tzinfo=IST)}, 40000, simdi=datetime(2026, 11, 10, 9, 50, tzinfo=IST))
    assert d["esik"] == "tesis 30 MW" and d["son_saat"].startswith("2026-11-10T10:30") and d["kalan_dk"] == 40 and not d["gecti"] and d["yururluk"] == "belirsiz"
    assert os_.dahili_bilgi({"tur": "ariza", "etkilenen_kw": 10000, "baslangic": datetime(2026, 11, 10, 9, 30, tzinfo=IST)}, 40000, portfoy_kw=52000)["esik"] == "portföy 50 MW"
    assert os_.dahili_bilgi({"tur": "talimat_yat", "etkilenen_kw": None, "baslangic": datetime(2026, 11, 10, 9, 30, tzinfo=IST)}, 40000) is None
    o = os_.ozet(tid, plant, 90, bugun=date(2026, 11, 10))
    assert o["acik"] == 0 and o["planli"] == 5 and o["eak_bugun"]["saat_sayisi"] == 3 and o["eak_bugun"]["kismi_saat"] == 1 and o["eak_bugun"]["en_cok_kw"] == 40000   # 10.11 kayıtları «planlı»
    assert o["ariza_sayaci"]["sayi"] == 2 and len(o["turler"]) == 8 and set(o["aciklama"]) == {"kapasite", "sayac", "kullanilabilirlik", "islem", "gerekce"} and o["eak_bugun"]["suren"] == 0
    csv = os_.csv_metni(o["olaylar"], "Olay GES"); assert csv.startswith("\ufeffsantral;tur;") and "Şebeke kesintisi" in csv and csv.count("\n") == 6 and ";evre;" in csv and "planlı" in csv


def test_kgup_uret_olayla_eak_duser(kiraci, monkeypatch):
    """Arıza olayı KGÜP tavanını ve EAK dosyasını saat bazında düşürür; olay olmayan gün eski davranış."""
    from pvquant.services import kgup_service as ks
    tid, plant = kiraci
    gun = date(2026, 11, 12)
    idx = pd.date_range(pd.Timestamp(gun).tz_localize(IST), periods=24, freq="h").tz_convert("UTC")
    df = pd.DataFrame({"ts_utc": idx, "kw": [0] * 7 + [8000, 20000, 30000, 36000, 38000, 38000, 36000, 30000, 20000, 8000] + [0] * 7})
    monkeypatch.setattr(ks, "kaynak_kosu_df", lambda t, p, g, k: (df, {"run_at": "2026-11-11T09:00:00Z", "mode": "C"}))
    p = {**plant, "ac_limit_kw": None, "uevcb": "UEVCB-1"}
    r0 = ks.uret(tid, p, gun)
    assert r0["eak"]["kaynak"] == "kurulu_guc" and r0["satirlar"][11]["kgup_mwh"] == 38.0
    os_.ekle(tid, plant, {"tur": "ariza", "baslangic": "2026-11-12T10:00", "bitis": "2026-11-12T13:00", "etkilenen_kw": 20000, "eak_gerekcesi": "mucbir"})
    r1 = ks.uret(tid, p, gun)
    assert r1["eak"]["kaynak"] == "kurulu_guc+olay" and r1["eak"]["olay_saat"] == 3 and r1["satirlar"][11]["eak_mw"] == 20.0 and r1["satirlar"][11]["kgup_mwh"] == 20.0
    assert r1["satirlar"][14]["kgup_mwh"] == 30.0 and r1["satirlar"][9]["eak_mw"] == 40.0
    satir = {h.split(",")[0]: h.split(",") for h in r1["eak_csv"].strip().split("\r\n")[1:]}
    assert satir["11"][1] == "20" and satir["11"][5] == "20" and satir["11"][3] == "" and satir["9"][1] == "40"


PLANT = "33333333-3333-4333-8333-333333333333"


def test_api_olay_uclari(kiraci, monkeypatch):
    import apps.api.main as api_main
    from apps.api.deps import gecerli_kullanici, yazma_yetkisi
    from pvquant.services import plant_service
    tid, plant = kiraci
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": tid, "role": "admin", "exp": 0}
    monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": plant["id"], "name": "Olay GES", "capacity_kwp": 40000.0, "params_json": {}} if p == plant["id"] else None)
    kayit = []
    monkeypatch.setattr(api_main._denetim, "kaydet", lambda *a, **k: kayit.append((a, k)))
    c = TestClient(api_main.app)
    try:
        r = c.post(f"/v1/plants/{plant['id']}/olaylar", json={"tur": "ariza", "baslangic": "2026-10-30T09:30", "etkilenen_kw": 1500, "neden": "invertör"})
        assert r.status_code == 201, r.text
        oid = r.json()["id"]; assert kayit[-1][0][:2] == ("musteri", "olay_ekle")
        assert c.post(f"/v1/plants/{plant['id']}/olaylar", json={"tur": "ariza", "baslangic": "2026-11-02T09:30", "etkilenen_kw": 99999}).status_code == 422
        g = c.get(f"/v1/plants/{plant['id']}/olaylar?gun=30"); assert g.status_code == 200 and g.json()["acik"] == 1 and len(g.json()["olaylar"]) == 1 and g.json()["ariza_sayaci"]["esik"] == 30
        u = c.put(f"/v1/plants/{plant['id']}/olaylar/{oid}", json={"bitis": "2026-10-30T12:00"}); assert u.status_code == 200 and u.json()["durum"] == "kapali"
        assert c.put(f"/v1/plants/{plant['id']}/olaylar/{uuid.uuid4()}", json={"neden": "x"}).status_code == 404
        csv = c.get(f"/v1/plants/{plant['id']}/olaylar.csv"); assert csv.status_code == 200 and "attachment" in csv.headers["content-disposition"] and "Arıza" in csv.text
        assert c.get(f"/v1/plants/{plant['id']}/olaylar?gun=2").status_code == 422
        assert c.get(f"/v1/plants/{PLANT}/olaylar").status_code == 404
    finally:
        api_main.app.dependency_overrides.clear()


def test_eylem_sozlugu_ve_turler():
    from pvquant.services import denetim_service
    assert {"olay_ekle", "olay_guncelle"} <= set(denetim_service.EYLEMLER_MUSTERI)
    assert set(os_.TUR_KURAL) == set(os_.TURLER) and all(k["gerekce"] in os_.GEREKCELER for k in os_.TUR_KURAL.values() if k["eak_dusur"])
