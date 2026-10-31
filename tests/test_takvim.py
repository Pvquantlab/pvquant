"""v2.518 (P3a) — piyasa ve mevzuat takvimi: iş günü, DUY m.132 zinciri (02-01 doğrulaması), YEKDEM süreleri (5905-27), künye türevleri,
segment süzgeci; API doğrulaması (DB'siz)."""
from datetime import date

import pytest
from fastapi.testclient import TestClient

from pvquant.ext.turkiye import takvim as tk
from pvquant.services import takvim_service as ts


def _k(olaylar, kod):
    return next(o for o in olaylar if o["kod"] == kod)


def test_is_gunu_ve_tatil():
    assert not tk.is_gunu(date(2026, 11, 15))          # Pazar
    assert not tk.is_gunu(date(2027, 1, 1))            # yılbaşı
    assert not tk.is_gunu(date(2026, 5, 28))           # Kurban Bayramı
    assert tk.is_gunu(date(2026, 10, 28))              # arife yarım gün → iş günü
    assert tk.is_gununa_kaydir(date(2026, 11, 15)) == date(2026, 11, 16)
    assert tk.is_gunu_ekle(date(2026, 12, 31), 1) == date(2027, 1, 4)   # 1.1 tatil, 2–3 hafta sonu


def test_ekim_2026_donemi_02_01_ile_birebir():
    o = tk.donem_takvimi(2026, 10)
    assert _k(o, "on_bildirim")["tarih"] == "2026-11-11"
    assert _k(o, "itiraz_son")["tarih"] == "2026-11-12" and _k(o, "itiraz_son")["saat"] == "17:30"
    n = _k(o, "nihai_bildirim"); assert n["tarih"] == "2026-11-16" and n["kaynak_turu"] == "hesaplanan" and n["kaydirma"] == "is_gunu"
    assert _k(o, "borc_odeme")["tarih"] == "2026-11-24"
    assert _k(o, "alacak_tahsil")["tarih"] == "2026-11-25"
    assert _k(o, "gts_odeme")["tarih"] == "2026-12-07"      # 02-16: Aralık'ın 5. iş günü
    assert _k(o, "itiraz_60")["tarih"] == "2027-01-15"


def test_kasim_2026_donemi_cumartesi_itiraz_belirsiz():
    o = tk.donem_takvimi(2026, 11)
    assert _k(o, "on_bildirim")["tarih"] == "2026-12-11"
    i = _k(o, "itiraz_son"); assert i["tarih"] == "2026-12-12" and i["hafta_sonu"] and i["kaydirma"] == "belirsiz" and i["not"]
    n = _k(o, "nihai_bildirim"); assert n["tarih"] == "2026-12-15" and n["kaynak_turu"] == "mevzuat"
    assert _k(o, "borc_odeme")["tarih"] == "2026-12-23"
    assert _k(o, "alacak_tahsil")["tarih"] == "2026-12-24"
    # 01.11 incelemesi: müşterinin son tarihi olup metinde hafta sonu kuralı bulunmayan adımlar «belirsiz» (13.2.2027 Cumartesi rozet alır)
    i60 = _k(o, "itiraz_60"); assert i60["tarih"] == "2027-02-13" and i60["hafta_sonu"] and i60["kaydirma"] == "belirsiz"
    assert _k(o, "fatura_duzenleme")["kaydirma"] == "belirsiz"


def test_aralik_doneminde_yilbasi_atlanir():
    o = tk.donem_takvimi(2026, 12)      # olaylar Ocak 2027'de
    assert _k(o, "nihai_bildirim")["tarih"] == "2027-01-15"
    assert _k(o, "borc_odeme")["tarih"] == "2027-01-25"      # 18,19,20,21,22,25


def test_yekdem_suresi_5905_27_ve_7189():
    assert tk.yekdem_suresi(date(2015, 11, 1))["son_yil"] == 2026 and tk.yekdem_suresi(date(2016, 10, 31))["son_yil"] == 2026
    assert tk.yekdem_suresi(date(2016, 11, 1))["son_yil"] == 2027
    assert tk.yekdem_suresi(date(2014, 11, 1))["ilk_yil"] == 2016
    assert tk.yekdem_suresi(date(2020, 12, 1))["son_yil"] == 2031
    y = tk.yekdem_suresi(date(2022, 3, 15)); assert y["rejim"] == "7189" and y["yek_bitis"] == "2032-03-15" and y["yerli_katki_bitis"] == "2027-03-15"
    assert tk.yekdem_suresi(None, 2020)["son_yil"] == 2029
    assert tk.yekdem_suresi(None) is None


def test_kunye_turet_ve_olaylar():
    pj = {"lisans_bitis": "2064-03-31", "kabul_tarihi": "2016-05-10", "isletmeye_giris": "2016-05-10", "police_bitis": "2026-12-20"}
    k = tk.kunye_turet(pj, date(2026, 10, 31)); t = k["turetilen"]
    assert t["lisans_bedeli_muafiyet_bitis"] == "2024-05-10" and t["lisans_kalan_gun"] == 13666
    assert "lisans_son_basvuru" not in t                       # 01.11: «bitiş − 6 ay» türetmesi kaldırıldı (m.26(2) erken sona erdirme süresidir)
    assert t["yekdem"]["son_yil"] == 2026 and t["police_kalan_gun"] == 50
    ol = tk.kunye_olaylari(pj, date(2026, 10, 31), "lisansli_yekdem"); kodlar = {o["kod"] for o in ol}
    assert {"lisans_bitis", "police_bitis", "lisans_bedeli_muafiyet", "yekdem_son_yil"} == kodlar
    assert all(o["kaynak_turu"] == "kunye" for o in ol)        # tarih müşterinin girdisi → «santral tarihi» rozeti
    assert "yekdem_son_yil" not in {o["kod"] for o in tk.kunye_olaylari(pj, date(2026, 10, 31), "lisansli_serbest")}
    assert tk.kunye_turet({"lisans_bitis": "bozuk"}, date(2026, 10, 31))["alanlar"]["lisans_bitis"] is None
    assert tk.KUNYE_ETIKET["kabul_tarihi"].startswith("İlk kabul")   # Lisans Yön. m.43(4): «kısmen veya tamamen kabulünün yapıldığı ilk tarih»


def test_yaklasan_segment_suzgeci_ve_siralama():
    b = date(2026, 10, 31)
    y = tk.yaklasan(b, {}, "lisansli_yekdem", 60)
    kodlar = [o["kod"] for o in y]
    assert kodlar == sorted(kodlar, key=lambda k: next(o["tarih"] for o in y if o["kod"] == k)) or True
    assert "yekdem_basvuru" in kodlar and "dsg_2027_orani" in kodlar and "on_bildirim" in kodlar
    assert "aym_luy_10yil" not in kodlar and "gts_odeme" not in kodlar
    assert next(o for o in y if o["kod"] == "yekdem_basvuru")["kalan_gun"] == 30
    ls = tk.yaklasan(b, {}, "lisanssiz_dagitim", 60)
    k2 = {o["kod"] for o in ls}
    assert "aym_luy_10yil" in k2 and "luy_gecici14" in k2 and "gts_odeme" in k2 and "on_bildirim" not in k2 and "yekdem_basvuru" not in k2
    assert all(o["kalan_gun"] >= 0 for o in y)
    assert [o["tarih"] for o in y] == sorted(o["tarih"] for o in y)


def test_gunluk_saatler_siralı_ve_kapsamli():
    g = tk.gunluk_saatler()
    saatler = [x["saat"] for x in g if x["saat"] != "gün içi"]
    assert saatler == sorted(saatler)
    assert any(x["saat"] == "11:00" and "lisansli_serbest" in x["kapsam"] for x in g)
    # 01.11 incelemesi: KGÜP/EAK/GİP adımları her gün (DUY m.69(1) «her gün»), avans/teminat adımları iş günü (m.132(1) «her işgünü»)
    gunler = {x["ad"].split(" ")[0] + "@" + x["saat"]: x["gunler"] for x in g}
    assert gunler["Program@15:30"] == "her gün" and gunler["EAK@09:00"] == "her gün" and gunler["GİP@gün içi"] == "her gün"
    assert gunler["Günlük@14:30"] == "iş günü" and gunler["Teminat@10:30"] == "iş günü" and gunler["Avans@15:00"] == "iş günü"
    assert {x["gunler"] for x in g} == {"her gün", "iş günü"}
    bytm = next(x for x in g if "BYTM" in x["ad"]); assert bytm["kaynak"] == "DUY m.69(1)"        # (4) değil: m.69(1) «saat 14:30'a kadar … BYTM'ye»
    teyit = next(x for x in g if "teyidi" in x["ad"]); assert teyit["kaynak"] == "DUY m.69(4)"    # «17:00'a kadar teyit edilir»


def test_gorunur_metinde_arastirma_numarasi_yok():
    """Panelde okunan «ad», «kaynak», «not» alanlarına bulgu numarası (02-02, 03-10 …) ya da «araştırma» sızmaz; iç kısaltma U&E / ESY yok."""
    import re
    desen = re.compile(r"\b0[1-8]-\d\d\b|araştırma|U&E|\bESY\b")
    b = date(2026, 11, 1)
    havuz = tk.donem_takvimi(2026, 11) + tk.sabit_tarihler(b) + tk.gunluk_saatler() + \
        tk.kunye_olaylari({"lisans_bitis": "2064-03-31", "kabul_tarihi": "2016-05-10", "isletmeye_giris": "2016-05-10", "police_bitis": "2026-12-20"}, b, "lisansli_yekdem")
    for o in havuz:
        for alan in ("ad", "kaynak", "not"):
            v = o.get(alan)
            assert not (v and desen.search(v)), (o.get("kod"), alan, v)
    assert "2026" not in tk.TATIL_KAYNAK                      # yıllar DINI_BAYRAM'dan türetilir, sabit metinde tekrarlanmaz
    y = tk.yekdem_suresi(date(2022, 3, 15)); assert not desen.search(y["kaynak"])


def test_servis_ozet_dbsiz():
    o = ts.ozet({"id": "p", "params_json": {"segment": "lisansli_yekdem", "isletmeye_giris": "2016-05-10"}}, gun=45, bugun=date(2026, 10, 31))
    assert o["segment"] == "lisansli_yekdem" and o["kunye"]["turetilen"]["yekdem"]["son_yil"] == 2026
    assert len(o["donemler"]) == 3 and o["donemler"][1]["donem"] == "2026-10"
    assert all("lisansli_yekdem" in g["kapsam"] for g in o["gunluk"])
    assert o["yaklasan"] and o["yaklasan"][0]["tarih"] >= "2026-10-31"


def test_kunye_dogrula():
    assert ts.kunye_dogrula({"lisans_bitis": "2064-03-31", "yekdem_baslangic_yili": "2017", "police_bitis": ""}) == \
        {"lisans_bitis": "2064-03-31", "yekdem_baslangic_yili": 2017, "police_bitis": None}
    with pytest.raises(ValueError, match="kabul_tarihi"):
        ts.kunye_dogrula({"kabul_tarihi": "10.05.2016"})
    with pytest.raises(ValueError, match="yekdem_baslangic_yili"):
        ts.kunye_dogrula({"yekdem_baslangic_yili": 1999})
    with pytest.raises(ValueError, match="lisans_bitis"):
        ts.kunye_dogrula({"lisans_yururluk": "2020-01-01", "lisans_bitis": "2019-01-01"})


PLANT = "22222222-2222-2222-2222-222222222222"


@pytest.fixture()
def istemci(monkeypatch):
    import apps.api.main as api_main
    from apps.api.deps import gecerli_kullanici
    from pvquant.services import plant_service
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "admin", "exp": 0}
    depo = {"params_json": {"segment": "lisansli_serbest"}}
    monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": p, "name": "X", "params_json": depo["params_json"]} if p == PLANT else None)

    def birlestir(t, p, **a):
        depo["params_json"] = {**depo["params_json"], **a}; return depo["params_json"]
    monkeypatch.setattr(plant_service, "params_birlestir", birlestir)
    monkeypatch.setattr(api_main._denetim, "kaydet", lambda *a, **k: None)
    yield TestClient(api_main.app)
    api_main.app.dependency_overrides.clear()


def test_api_takvim_ve_kunye(istemci):
    r = istemci.get(f"/v1/plants/{PLANT}/takvim?gun=45"); assert r.status_code == 200, r.text
    j = r.json(); assert j["segment"] == "lisansli_serbest" and j["yaklasan"] and j["donemler"] and j["kunye"]["alanlar"]["lisans_bitis"] is None
    assert istemci.get(f"/v1/plants/{PLANT}/takvim?gun=5").status_code == 422
    r = istemci.put(f"/v1/plants/{PLANT}/kunye-tarihler", json={"lisans_bitis": "2064-03-31", "isletmeye_giris": "2016-05-10", "yekdem_baslangic_yili": None})
    assert r.status_code == 200, r.text
    k = r.json()["kunye"]; assert k["alanlar"]["lisans_bitis"] == "2064-03-31" and k["turetilen"]["lisans_kalan_gun"] > 13000 and k["turetilen"]["yekdem"]["son_yil"] == 2026
    assert istemci.put(f"/v1/plants/{PLANT}/kunye-tarihler", json={"kabul_tarihi": "10/05/2016"}).status_code == 422
    assert istemci.get("/v1/plants/00000000-0000-0000-0000-000000000000/takvim").status_code == 404
