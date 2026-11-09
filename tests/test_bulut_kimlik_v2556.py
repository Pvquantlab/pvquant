"""v2.556 (Aşama 3, K1) — kimlik saklama akışı (SAF, DB'siz): onaylar, kasa kapalı, sınama geçmeden yazılmaz, santral seçimi, zarf düz metin içermez."""
from __future__ import annotations

import json

from pvquant.guvenlik import kasa
from pvquant.services import bulut_kimlik_service as bk

PLANT = {"id": "p1"}
ONAY2 = {"yalniz_okuma": True, "sifreli_saklama": True}
KIMLIK = {"kullanici": "nbi_edikli", "sistem_kodu": "Cok-Gizli-42"}


def _sina_ok(kod, kimlik, onay, bolge):
    return {"durum": "ok", "zaman": "z", "saglayici": kod, "ozet": {"santral_sayisi": 1, "santraller": [{"kimlik": "NE=1", "ad": "Edikli", "kapasite_kwp": 1000.0}]}}


def _sina_coklu(kod, kimlik, onay, bolge):
    return {"durum": "ok", "zaman": "z", "ozet": {"santraller": [{"kimlik": "A", "ad": "a"}, {"kimlik": "B", "ad": "b"}]}}


def _hic(*a):
    return None


def test_onaylar_kasa_ve_kapanan_saglayici(monkeypatch):
    monkeypatch.setenv("PVQ_KEK", kasa.anahtar_uret()); monkeypatch.delenv("PVQ_KEK_ID", raising=False)
    r = bk.kaydet("t", PLANT, "fusionsolar", KIMLIK, "intl", {"yalniz_okuma": True}, "a", sina=_sina_ok, yaz=_hic)
    assert r["durum"] == "onay_yok" and not r["kaydedildi"] and "şifreli saklanmasını" in r["aciklama"]
    assert bk.kaydet("t", PLANT, "solaredge_v1", {"api_anahtari": "k"}, None, ONAY2, "a", sina=_sina_ok, yaz=_hic)["durum"] == "saglayici_kapandi"
    assert bk.kaydet("t", PLANT, "sems", {"api_anahtari": "k"}, None, ONAY2, "a", sina=_sina_ok, yaz=_hic)["durum"] == "saglayici_desteklenmiyor"
    assert bk.kaydet("t", PLANT, "fusionsolar", {"kullanici": "u"}, None, ONAY2, "a", sina=_sina_ok, yaz=_hic)["durum"] == "ayar_hatasi"
    monkeypatch.delenv("PVQ_KEK")
    r = bk.kaydet("t", PLANT, "fusionsolar", KIMLIK, "intl", ONAY2, "a", sina=_sina_ok, yaz=_hic)
    assert r["durum"] == "kasa_kapali" and not r["kaydedildi"]


def test_sinama_gecmeden_yazilmaz_ve_santral_secimi(monkeypatch):
    monkeypatch.setenv("PVQ_KEK", kasa.anahtar_uret())
    yazilan: list = []
    yaz = lambda t, p, s: yazilan.append(s)   # noqa: E731
    r = bk.kaydet("t", PLANT, "fusionsolar", KIMLIK, "intl", ONAY2, "a", sina=lambda *a: {"durum": "kimlik_hatasi", "zaman": "z", "aciklama": "(305)"}, yaz=yaz)
    assert r["durum"] == "kimlik_hatasi" and not r["kaydedildi"] and yazilan == []
    r = bk.kaydet("t", PLANT, "fusionsolar", KIMLIK, "intl", ONAY2, "a", sina=_sina_coklu, yaz=yaz)
    assert r["durum"] == "santral_secimi_gerekli" and len(r["santraller"]) == 2 and yazilan == []
    assert bk.kaydet("t", PLANT, "fusionsolar", KIMLIK, "intl", ONAY2, "a", dis_kimlik="C", sina=_sina_coklu, yaz=yaz)["durum"] == "santral_bulunamadi"
    r = bk.kaydet("t", PLANT, "fusionsolar", KIMLIK, "intl", ONAY2, "a", dis_kimlik="B", sina=_sina_coklu, yaz=yaz)
    assert r["kaydedildi"] and r["dis_kimlik"] == "B" and len(yazilan) == 1
    assert bk.kaydet("t", PLANT, "fusionsolar", KIMLIK, "intl", ONAY2, "a", sina=lambda *a: {"durum": "ok", "ozet": {"santraller": []}}, yaz=yaz)["durum"] == "santral_yok"


def test_zarf_duz_metin_icermez_ve_worker_cozer(monkeypatch):
    monkeypatch.setenv("PVQ_KEK", kasa.anahtar_uret()); monkeypatch.delenv("PVQ_KEK_ID", raising=False)
    yazilan: list = []
    r = bk.kaydet("t", PLANT, "fusionsolar", KIMLIK, "eu5", ONAY2, "aktor", sina=_sina_ok, yaz=lambda t, p, s: yazilan.append(s))
    assert r["durum"] == "kaydedildi" and r["etiket"] == "nbi…li" and r["dis_kimlik"] == "NE=1" and r["dis_ad"] == "Edikli" and r["kek_id"] == "k1"
    assert "Cok-Gizli-42" not in json.dumps(r, default=str)
    s = yazilan[0]
    assert "Cok-Gizli-42" not in json.dumps({k: v for k, v in s.items() if k not in ("sifreli", "dek_sarili")}, default=str)
    assert b"Cok-Gizli-42" not in s["sifreli"] and b"nbi_edikli" not in s["sifreli"]
    assert s["onay_json"]["metinler"]["sifreli_saklama"] == bk.ONAY_METNI["sifreli_saklama"] and s["onay_json"]["aktor_id"] == "aktor"
    assert bk.coz_kimlik({**s, "tenant_id": "t", "plant_id": "p1"}) == KIMLIK
    assert bk.maskele("ab") == "a…" and bk.maskele("abcdef") == "ab…f" and bk.maskele(None) is None
    assert bk.params_ozeti([{"saglayici": "fusionsolar", "etiket": "nbi…li", "cekis_acik": False, "birim_dogrulandi": False, "guncelleme": "z"}])["kayitli"] is True
