"""v2.591 (Faz 3 F3-D, saf) — sözleşmesel dağılım: beş anahtar, Σ üye payı = grup tutarı, KÜPST dağılıma girmez, bireysel EDT üyede kalır, ücretler,
sözleşme payı eksik/toplam ≠ 1 → hesap yok (sessiz eşitleme yok), «Varsayımsal maliyet dağılımı» etiketi yalnız doğrulanmış belgeli sözleşmede kalkar, üç perspektif."""
from __future__ import annotations

import pytest

from pvquant.ext.platform import dagitim as dg

UY = {"A": {"edt_tek_tl": -1200.0, "edt_bireysel_tl": -300.0, "kupst_tl": -150.0, "grup_payi_mwh": 6.0, "uretim_mwh": 40.0, "sapma_mwh": 9.0},
      "B": {"edt_tek_tl": 500.0, "edt_bireysel_tl": 0.0, "kupst_tl": None, "grup_payi_mwh": 4.0, "uretim_mwh": 60.0, "sapma_mwh": 4.0}}
GRUP = -400.0   # grup EDT (artı = lehte); bireysel −300 + grup −400 = DSG içi −700; Σ tek = −700 → bu örnekte fark 0
SOZ_OK = {"id": "s1", "dogrulama": "dogrulandi", "belge_adi": "dsg.pdf"}


@pytest.mark.parametrize("yontem, beklenen", [("sapma", {"A": 60.0, "B": 40.0}), ("esit", {"A": 50.0, "B": 50.0}), ("uretim", {"A": 40.0, "B": 60.0}),
                                              ("sabit_pay", {"A": 70.0, "B": 30.0}), ("ozel", {"A": 70.0, "B": 30.0})])
def test_anahtarlar_ve_toplam_kontrolu(yontem, beklenen):
    d = dg.dagit(GRUP, UY, yontem, {"paylar": {"A": 0.7, "B": 0.3}} if yontem in ("sabit_pay", "ozel") else None)
    assert d["kontrol"] is True and {s["santral"]: s["pay_pct"] for s in d["satirlar"]} == beklenen
    assert d["toplam"]["grup_payi_tl"] == pytest.approx(GRUP) and sum(s["grup_payi_tl"] for s in d["satirlar"]) == pytest.approx(GRUP)
    a = next(s for s in d["satirlar"] if s["santral"] == "A")
    assert a["edt_bireysel_tl"] == -300.0 and a["dsg_ici_tl"] == pytest.approx(GRUP * beklenen["A"] / 100 - 300.0) and a["kupst_tl"] == -150.0 and a["kupst_dahil_degil"]
    assert a["toplam_tl"] == a["dsg_ici_tl"] and d["etiket"] == "Varsayımsal maliyet dağılımı" and d["nitelik"] == "senaryo" and dg.NOT_KUPST in d["notlar"]


def test_ucretler_ve_sozlesme_etiketi():
    d = dg.dagit(GRUP, UY, "ozel", {"paylar": {"A": 0.5, "B": 0.5}, "yonetim_ucreti_tl": 1000.0, "ucret_tl_mwh": 10.0}, SOZ_OK)
    assert d["etiket"] == "Sözleşmeye dayalı dağılım" and d["nitelik"] == "hesaplanan" and d["sozlesme"]["belge_adi"] == "dsg.pdf"
    a, b = (next(s for s in d["satirlar"] if s["santral"] == x) for x in ("A", "B"))
    assert a["ucret_tl"] == -(500.0 + 400.0) and b["ucret_tl"] == -(500.0 + 600.0) and d["toplam"]["ucret_tl"] == -2000.0
    assert a["toplam_tl"] == pytest.approx(-200.0 - 300.0 - 900.0) and d["toplam"]["grup_payi_tl"] == pytest.approx(GRUP)   # ücret grup toplamına girmez
    d2 = dg.dagit(GRUP, UY, "ozel", {"paylar": {"A": 0.5, "B": 0.5}, "yonetim_ucreti_tl": 1000.0, "ucret_paylari": {"A": 1.0, "B": 0.0}}, SOZ_OK)
    assert next(s for s in d2["satirlar"] if s["santral"] == "A")["ucret_tl"] == -1000.0
    # doğrulandı ama belge yok / belgeli ama doğrulanmadı → varsayımsal
    assert dg.dagit(GRUP, UY, "sapma", None, {"dogrulama": "dogrulandi"})["etiket"] == "Varsayımsal maliyet dağılımı"
    assert dg.dagit(GRUP, UY, "sapma", None, {"dogrulama": "belgeli", "belge_adi": "x.pdf"})["etiket"] == "Varsayımsal maliyet dağılımı"


def test_hatali_paylar_hesap_yok_ve_bos_durumlar():
    d = dg.dagit(GRUP, UY, "sabit_pay", {"paylar": {"A": 1.0}})
    assert d["satirlar"] == [] and d["nitelik"] == "eksik" and "kapsamıyor" in d["hata"]
    assert "toplamı 1" in dg.dagit(GRUP, UY, "sabit_pay", {"paylar": {"A": 0.7, "B": 0.7}})["hata"]
    assert "gerekli" in dg.dagit(GRUP, UY, "sabit_pay", None)["hata"]
    with pytest.raises(ValueError):
        dg.agirliklar(UY, "yok")
    assert dg.dagit(None, UY, "sapma")["nitelik"] == "eksik" and dg.dagit(GRUP, {}, "sapma")["satirlar"] == []
    # ağırlık toplamı sıfır → eşit pay + not
    uy0 = {a: {**v, "grup_payi_mwh": 0.0} for a, v in UY.items()}
    d0 = dg.dagit(GRUP, uy0, "sapma")
    assert {s["santral"]: s["pay_pct"] for s in d0["satirlar"]} == {"A": 50.0, "B": 50.0} and any("eşit pay" in n for n in d0["notlar"])
    assert dg.dagit(GRUP, UY, "ozel")["notlar"][-1].startswith("özel kuralda pay tablosu yok")


def test_uc_perspektif_ve_nitelik():
    dsg = {"uyeler": {"A": {"edt_tek_tl": -1200.0, "kupst_tl": 150.0, "sapma_mwh": 9.0}, "B": {"edt_tek_tl": 500.0, "kupst_tl": None, "sapma_mwh": 4.0}},
           "edt_tek_tl": -700.0, "edt_dsg_tl": -500.0, "edt_grup_tl": -200.0, "edt_bireysel_tl": -300.0, "kupst_uye_tl": 150.0, "esik": 0.05, "esik_kaynak": "Karar 13869",
           "sapma_net_mwh": 5.0, "sapma_ayri_mwh": 13.0}
    dag = dg.dagit(-200.0, UY, "sapma")
    p = dg.perspektifler(dsg, dag, {"A": "dogrulandi", "B": "beyan"})
    assert p["bagimsiz"]["toplam_edt_tl"] == -700.0 and p["bagimsiz"]["toplam_kupst_tl"] == -150.0 and p["bagimsiz"]["satirlar"][0]["kupst_tl"] == -150.0
    assert p["dsg_ici"]["netlesme_farki_tl"] == 200.0 and "DSG lehine" in p["dsg_ici"]["aciklama"] and p["dsg_ici"]["nitelik"] == "senaryo" and p["dsg_ici"]["uyelik_hepsi_dogrulandi"] is False
    assert p["ozet"]["etiket"] == "Varsayımsal maliyet dağılımı" and p["ozet"]["nitelik"] == "senaryo"
    p2 = dg.perspektifler(dsg, dg.dagit(-200.0, UY, "sabit_pay", {"paylar": {"A": 0.5, "B": 0.5}}, SOZ_OK), {"A": "dogrulandi", "B": "dogrulandi"})
    assert p2["dsg_ici"]["nitelik"] == "hesaplanan" and p2["ozet"]["nitelik"] == "hesaplanan" and p2["ozet"]["etiket"] == "Sözleşmeye dayalı dağılım"
    assert dg.perspektifler(dsg, dag, {"A": "dogrulandi", "B": "dogrulandi"}, fiyat_senaryo_saat=3)["dsg_ici"]["nitelik"] == "senaryo"
