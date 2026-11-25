"""K9-B (25.11.2026) — santral türü beyan edilmediyse etiket bunu açıkça söyler; hesap/tazelik davranışı ve beyanlı yollar değişmez."""
from pvquant.services import durum_sozlugu as ds


def test_beyansiz_varsayilan_etiketlenir_davranis_degismez():
    b = ds.santral_sinifi(None)
    assert b["santral_turu"] == "operasyonel" and b["veri_turu"] == "canli" and b["tazelik_izlenir"] is True and b["rozet"] is None
    assert b["beyan_edildi"] is False and "beyan edilmedi" in b["santral_turu_etiketi"] and "beyan edilmedi" in b["veri_turu_etiketi"]
    assert ds.santral_sinifi({"santral_turu": "uydurma", "veri_turu": "x"}) == b          # geçersiz değer = beyansız
    assert ds.santral_sinifi({"params": 1}) == b


def test_beyanli_ve_eski_beyan_etiketi_temiz():
    for pj in ({"santral_turu": "sanal_test", "veri_turu": "tarihsel_arsiv"}, {"santral_turu": "kamu_referans"},
               {"santral_turu": "operasyonel", "veri_turu": "canli"}, {"veri_sinifi": "demo"}, {"veri_sinifi": "tarihsel"}):
        g = ds.santral_sinifi(pj)
        assert g["beyan_edildi"] is True and "beyan edilmedi" not in g["santral_turu_etiketi"] and "beyan edilmedi" not in g["veri_turu_etiketi"]
    assert ds.santral_sinifi({"santral_turu": "kamu_referans"})["santral_turu_etiketi"] == ds.SANTRAL_TURLERI["kamu_referans"]
    assert ds.santral_sinifi({"santral_turu": "operasyonel", "veri_turu": "canli"})["tazelik_izlenir"] is True
    assert ds.santral_sinifi({"santral_turu": "sanal_test"})["tazelik_izlenir"] is False
