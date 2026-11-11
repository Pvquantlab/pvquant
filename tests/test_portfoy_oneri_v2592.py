"""v2.592 (Faz 3 F3-E, saf) — revizyon karar desteği: 12 kural tek tek, etiketler (doğrulanmış / tahmini / eksik / geçti), pencere geçmiş, fiyat yok metni,
brief örnek cümleleri, sakin durum, sıralama (eylem › öneri › bilgi), maruziyet oranı."""
from __future__ import annotations

import numpy as np
import pandas as pd

from pvquant.ext.platform import portfoy_oneri as po


def _g(**k):
    g = {"hedef": "yarin", "gun": "2026-09-12", "risk": {"etiket": "tahmini", "beklenen_sapma_pct": -8.0, "beklenen_sapma_mwh": -12.0, "program_mwh": 150.0, "tahmin_mwh": 138.0, "saat": 24, "riskli_saat": 0, "saatler": []},
         "program_kaynak": {"bildirilen": 24, "oneri": 0, "yok": 0}, "santraller": [], "tahmin_yok": [], "belirsizlik": {"durum": "dogrulandi"}, "tazelik": {"en_eski_yas_saat": 2.0, "farkli_yayin": False},
         "olcum_yas_saat": 1.0, "pencere": {"durum": "pencere_acik", "dakika_kaldi": 40, "hedef_gun": "2026-09-12", "teyit_saati": "17:00:00"}, "gun_ici": {}, "fiyat": {"epias_saat": 24, "senaryo_saat": 0}, "maruziyet": None}
    g.update(k); return g


def _kodlar(g):
    return {o["kod"]: o for o in po.oneriler(g)}


def test_brief_ornekleri_ve_etiketler():
    o = _kodlar(_g())
    assert o["sapma_orta"]["metin"].startswith("Portföyünüzün yarınki üretim beklentisi, mevcut üretim programından %8,0 düşük") and o["sapma_orta"]["etiket"] == "tahmini"
    assert o["pencere"]["tur"] == "eylem" and "40 dakika" in o["pencere"]["metin"] and "maruziyet" in o and o["maruziyet"]["etiket"] == "eksik"
    g = _g(risk={**_g()["risk"], "beklenen_sapma_pct": -12.0, "etiket": "dogrulanmis"})
    o = _kodlar(g)
    assert o["sapma_buyuk"]["tur"] == "eylem" and o["sapma_buyuk"]["etiket"] == "dogrulanmis" and o["sapma_buyuk"]["etiket_ad"] == "Doğrulanmış risk" and "sapma_orta" not in o
    assert po.oneriler(g)[0]["tur"] == "eylem" and po.ozet_cumlesi(g, po.oneriler(g)).startswith("Yarın portföy beklentisi programdan %12,0 düşük; ")
    # santral değişimi ve ofset
    s = [{"santral": "A", "degisim_pct": -20.0, "fark_mwh": -5.0}, {"santral": "B", "degisim_pct": 18.0, "fark_mwh": 3.0}, {"santral": "C", "degisim_pct": -16.0, "fark_mwh": -2.0}, {"santral": "D", "degisim_pct": 1.0, "fark_mwh": 0.1}]
    o = _kodlar(_g(santraller=s))
    assert o["santral_degisim"]["metin"].startswith("Üç santralde üretim beklentisi belirgin şekilde değişti. Programınızı kontrol etmeniz önerilir.")
    assert o["ofset"]["metin"].startswith("Üç santralin sapmaları portföy toplamında birbirini kısmen dengeliyor") and o["ofset"]["dayanak"]["netlesen_mwh"] == 6.0
    o2 = _kodlar(_g(santraller=[{"santral": "A", "degisim_pct": -20.0, "fark_mwh": -5.0}, {"santral": "B", "degisim_pct": 18.0, "fark_mwh": 3.0}]))
    assert o2["ofset"]["metin"].startswith("İki santralin sapmaları")


def test_program_yok_fiyat_yok_tahmin_yok_belirsizlik_tazelik():
    o = _kodlar(_g(risk={"etiket": "eksik"}, program_kaynak={"bildirilen": 0, "oneri": 0, "yok": 24}))
    assert o["program_yok"]["tur"] == "eylem" and o["program_yok"]["etiket"] == "eksik" and "sakin" not in o and "sapma_orta" not in o
    assert po.ozet_cumlesi(_g(risk={"etiket": "eksik"}), []) == "Program bulunmadığından portföy sapması değerlendirilemedi."
    o = _kodlar(_g(program_kaynak={"bildirilen": 0, "oneri": 24, "yok": 0}))
    assert o["program_yok"]["tur"] == "bilgi" and "PVQuant önerisine göre" in o["program_yok"]["metin"]
    o = _kodlar(_g(fiyat={"epias_saat": 0, "senaryo_saat": 24}))
    assert o["fiyat_yok"]["metin"] == "Finansal etki hesabı için güncel piyasa fiyatı bulunamadı." and o["fiyat_yok"]["etiket"] == "eksik"
    assert _kodlar(_g(fiyat={"epias_saat": 20, "senaryo_saat": 4}))["fiyat_yok"]["etiket"] == "tahmini"
    o = _kodlar(_g(tahmin_yok=["GES D"], belirsizlik={"durum": "yetersiz_veri"}, tazelik={"en_eski_yas_saat": 20.0, "farkli_yayin": True}, olcum_yas_saat=9.0))
    assert o["tahmin_yok"]["metin"].startswith("Bir santralin güncel tahmini yok (GES D)") and o["belirsizlik"]["etiket"] == "eksik" and "20 saatten eski" in o["tazelik"]["metin"]
    assert o["olcum_tazelik"]["etiket"] == "eksik" and _kodlar(_g(belirsizlik={"durum": "dogrulanmadi"}))["belirsizlik"]["etiket"] == "tahmini"
    assert "tazelik" not in _kodlar(_g()) and "olcum_tazelik" not in _kodlar(_g())


def test_pencere_gecti_gun_ici_riskli_saat_maruziyet_sakin():
    o = _kodlar(_g(pencere={"durum": "gecikti", "dakika_kaldi": 0, "hedef_gun": "2026-09-12", "teyit_saati": "17:00:00"}))
    assert o["pencere"]["etiket"] == "gecti" and o["pencere"]["etiket_ad"] == "Revizyon fırsatı geçti" and "15:30" in o["pencere"]["metin"]
    assert _kodlar(_g(pencere={"durum": "erken", "dakika_kaldi": 300, "hedef_gun": "2026-09-12"}))["pencere"]["tur"] == "bilgi"
    gi = {"acik": True, "teslimat": "2026-09-11T14:00+03:00", "kgup_revizyon_son": "2026-09-11T13:30+03:00", "dakika_kaldi": 12}
    o = _kodlar(_g(hedef="bugun", gun_ici=gi))
    assert o["pencere"]["tur"] == "eylem" and "14:00" in o["pencere"]["metin"] and "13:30" in o["pencere"]["metin"] and "bugünkü kalan saatlerdeki" in o["sapma_orta"]["metin"]
    o = _kodlar(_g(hedef="bugun", gun_ici={"acik": False, "teslimat": "2026-09-11T14:00+03:00", "sonraki_revizyon_son": "2026-09-11T14:30+03:00"}))
    assert o["pencere"]["etiket"] == "gecti" and "14:30" in o["pencere"]["metin"]
    r = {**_g()["risk"], "riskli_saat": 3, "saatler": [{"ts": "2026-09-12T09:00+00:00", "fark_mwh": -4.5}]}
    o = _kodlar(_g(risk=r))
    assert o["riskli_saat"]["metin"].startswith("3 saatte program, tahmin aralığının dışında") and "4,5 MWh" in o["riskli_saat"]["metin"]
    mar = {"gecmis_gun": 20, "oran_tl_mwh": {"p25": 500.0, "p50": 800.0, "p75": 1200.0}}
    o = _kodlar(_g(maruziyet=mar))
    assert o["maruziyet"]["dayanak"]["aralik_tl"] == {"p25": 6000.0, "p50": 10000.0, "p75": 14000.0} and "6.000 … 14.000 TL" in o["maruziyet"]["metin"] and o["maruziyet"]["etiket"] == "tahmini"
    o = _kodlar(_g(risk={**_g()["risk"], "beklenen_sapma_pct": 1.2, "beklenen_sapma_mwh": 1.8}, maruziyet=mar))
    assert o["sakin"]["metin"].startswith("Portföyünüzün yarınki üretim beklentisi programla uyumlu") and "sapma_orta" not in o
    assert [x["tur"] for x in po.oneriler(_g(maruziyet=mar))] == sorted([x["tur"] for x in po.oneriler(_g(maruziyet=mar))], key=lambda t: {"eylem": 0, "oneri": 1, "bilgi": 2}[t])


def test_maruziyet_orani():
    idx = pd.date_range("2026-08-01", periods=24 * 10, freq="h", tz="Europe/Istanbul")
    rng = np.random.default_rng(1)
    edm = rng.normal(0, 1.0, len(idx)); pv = pd.DataFrame({"sapma": edm, "edt_net": -edm * 900.0 + rng.normal(0, 50, len(idx)), "kupst": 0.0}, index=idx)
    m = po.maruziyet_orani(pv)
    assert m and m["gecmis_gun"] == 10 and 700 < m["oran_tl_mwh"]["p50"] < 1100 and m["nitelik"] == "senaryo"
    assert po.maruziyet_orani(pv.iloc[: 24 * 5]) is None and po.maruziyet_orani(None) is None and po.maruziyet_orani(pd.DataFrame({"x": [1]})) is None
    assert po.maruziyet_orani(pv.rename(columns={"sapma": "edm"}))["gecmis_gun"] == 10   # eski ad da kabul
