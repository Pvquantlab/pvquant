"""v2.594 (Faz 3 F3-G, saf) — portföy finansal birleştirme: bileşen toplamları = Σ santral, çift sayım bekçisi (bağımsız EDT ve DSG içi EDT aynı listede değil),
DSG içi toplamın yerine koyması, nitelik en zayıf ve eksik santralda senaryo + not, resmî fark, sınıflar (gerçekleşen / hesaplanan / varsayımsal), B13 MWh toplamları."""
from __future__ import annotations

import pytest

from pvquant.ext.platform import finans as fn
from pvquant.ext.platform import portfoy_finans as pf


def _b(kod, tutar, nitelik="hesaplanan", toplanir=True, kapsam=24):
    return fn.Bilesen(kod, kod, tutar_tl=tutar, nitelik=nitelik, toplanir=toplanir, kapsam_saat=kapsam, beklenen_saat=24, kural_surumu="k1").sozluk()


def _ozet(gelir, edt, kupst, plan, ger, nit="hesaplanan", resmi=None, kayitli=False, ekstra=()):
    bil = [_b("satis_geliri", gelir, "sozlesme_tahmini"), _b("dengesizlik", edt, nit), _b("kupst", kupst, nit), _b("uretim_dusuklugu", -100.0, "sozlesme_tahmini", False),
           _b("ileri_maruziyet", -50.0, "senaryo", False), *ekstra]
    if resmi is not None:
        bil += [_b("dengesizlik_resmi", resmi, "resmi", False), _b("kupst_resmi", kupst, "resmi", False)]
    return {"uretim": {"planlanan": {"mwh": plan}, "gerceklesen": {"mwh": ger, "kapsama": {"kapsama_pct": 99.0}}, "sapma": {"mwh": ger - plan, "pct": 1.0}},
            "uzlastirma": {"santral_tasir": True}, "meta": {"segment": "lisansli_serbest", "hesap_zamani": "t", "fiyat": {"epias_saat": 24, "senaryo_saat": 0}},
            "bilesenler": bil, "toplam": fn.toplam([fn.Bilesen(**{k: v for k, v in x.items() if k in ("kod", "ad", "tutar_tl", "nitelik", "toplanir")}) for x in bil]),
            "donem": {"kod": "2026-09-10"}, "kayitli": kayitli}


def test_toplamlar_cift_sayim_dsg_yerine_koyma_ve_siniflar():
    oz = {"A": _ozet(9000.0, -1200.0, -150.0, 10.0, 9.5, resmi=-1100.0, kayitli=True), "B": _ozet(5000.0, 500.0, 0.0, 6.0, 6.2)}
    dsg = {"durum": "ok", "kural": {"dsg_dayanak": "DUY m.111"}, "sozlesme": None,
           "perspektifler": {"dsg_ici": {"nitelik": "senaryo", "edt_dsg_tl": -500.0, "netlesme_farki_tl": 200.0, "esik": 0.05, "uyelik_hepsi_dogrulandi": False, "aciklama": "x"},
                             "sozlesmesel": {"etiket": "Varsayımsal maliyet dağılımı", "nitelik": "senaryo", "yontem_ad": "sapma payına göre", "toplam": {"toplam_tl": -500.0},
                                             "notlar": ["n1", "n2"], "satirlar": [{"santral": "A", "toplam_tl": -400.0}, {"santral": "B", "toplam_tl": -100.0}]},
                             "bagimsiz": {"satirlar": [{"santral": "A", "edt_tek_tl": -1200.0, "kupst_tl": -150.0, "uyelik_dogrulama": "dogrulandi"}, {"santral": "B", "edt_tek_tl": 500.0, "kupst_tl": 0.0, "uyelik_dogrulama": "beyan"}]},
                             "ozet": {"nitelik": "senaryo"}}}
    r = pf.birlestir(oz, dsg, {"A": 1000.0, "B": 600.0}, "2026-09-10")
    kod = {b["kod"]: b for b in r["bilesenler"]}
    assert kod["satis_geliri"]["tutar_tl"] == 14000.0 and kod["dengesizlik"]["tutar_tl"] == -700.0 and kod["kupst"]["tutar_tl"] == -150.0 and kod["dengesizlik"]["kapsam_saat"] == 48
    assert r["toplam"]["tutar_tl"] == pytest.approx(14000.0 - 700.0 - 150.0) and r["toplam"]["giren"] == ["satis_geliri", "dengesizlik", "kupst"] and r["toplam"]["nitelik"] == "sozlesme_tahmini"
    assert r["toplam_dsg"]["tutar_tl"] == pytest.approx(14000.0 - 500.0 - 150.0) and "dengesizlik" not in r["toplam_dsg"]["giren"] and "dengesizlik_dsg" in r["toplam_dsg"]["giren"] and r["toplam_dsg"]["nitelik"] == "senaryo"
    assert kod["dengesizlik_dsg"]["toplanir"] is False and kod["netlesme_farki"]["tutar_tl"] == 200.0 and kod["sozlesmesel_dagilim"]["ad"].endswith("Varsayımsal maliyet dağılımı")
    assert kod["resmi_fark"]["tutar_tl"] == pytest.approx(-1100.0 - (-1200.0)) and kod["resmi_fark"]["nitelik"] == "resmi" and kod["dengesizlik_resmi"]["tutar_tl"] == -1100.0
    assert kod["dengesizlik_resmi"]["nitelik"] == "senaryo" and "B" in kod["dengesizlik_resmi"]["notlar"][0]   # B'de resmî yok → eksik 0 sayılmaz, nitelik düşer
    s = r["siniflar"]
    assert "resmi_fark" in s["gerceklesen_resmi"]["kodlar"] and "dengesizlik" in s["hesaplanan"]["kodlar"] and {"satis_geliri", "dengesizlik_dsg", "ileri_maruziyet"} <= set(s["varsayimsal"]["kodlar"])
    assert r["mwh"]["toplanan"] == {"planlanan": 16.0, "gerceklesen": 15.7, "santral": 2} and r["kayitli_santral"] == 1 and r["dsg"]["netlesme_farki_tl"] == 200.0
    assert r["dsg_santraller"][0]["sozlesmesel"]["toplam_tl"] == -400.0 and pf.NOT_DSG in r["notlar"]
    # çift sayım bekçisi: aynı kod iki kez toplanmaya çalışılırsa ValueError (saf toplam)
    with pytest.raises(ValueError):
        fn.toplam([fn.Bilesen("dengesizlik", "a", 1.0), fn.Bilesen("dengesizlik", "b", 2.0)])


def test_eksik_santral_hata_ve_b13():
    oz = {"A": _ozet(9000.0, -1200.0, -150.0, 10.0, 9.5), "B": {"hata": "x"}, "C": _ozet(None, None, None, 3.0, 2.0)}   # C: bütün kalemler eksik → toplamı yok → toplama girmez
    r = pf.birlestir(oz, None, {"A": 1, "B": 1, "C": 1})
    kod = {b["kod"]: b for b in r["bilesenler"]}
    assert kod["dengesizlik"]["nitelik"] == "senaryo" and "C" in kod["dengesizlik"]["notlar"][0] and kod["satis_geliri"]["tutar_tl"] == 9000.0 and kod["satis_geliri"]["nitelik"] == "senaryo"
    assert r["toplam_dsg"] is None and r["dsg"] is None and r["toplama_girmeyen"] == ["B", "C"] and r["santraller"][1]["hata"] == "x"
    assert r["mwh"]["toplanan"] == {"planlanan": 10.0, "gerceklesen": 9.5, "santral": 1} and r["mwh"]["tum"] == {"planlanan": 13.0, "gerceklesen": 11.5, "santral": 2}   # B13
    assert kod["resmi_fark"]["nitelik"] == "eksik" and pf.birlestir({}, None)["toplam"]["tutar_tl"] is None and pf.birlestir({}, None)["bilesenler"][0]["nitelik"] == "eksik"
