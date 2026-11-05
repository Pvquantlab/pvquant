"""v2.539 — EK-3 II: DSG gruplaması santral kaydındaki koda göre (DK-258), toplayıcı portföyü dışlama (DK-261), iletime bağlı lisanssız portföy dışı
(DK-653/785 devamı), katılımcı düzeyi eşik notu (DK-252), YAL/YAT/acil kesme saatlerinin dökümde işaretlenmesi (DK-056)."""
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from pvquant.ext.turkiye import dengesizlik as d
from pvquant.services import dengesizlik_service as dz

IST = ZoneInfo("Europe/Istanbul")


def _p(ad, **pj):
    return {"id": ad, "name": ad, "params_json": pj}


def test_dsg_gruplari_varsayim_ve_disi():
    g = dz.dsg_gruplari([_p("A", segment="lisansli_serbest"), _p("B", segment="lisansli_yekdem"), _p("C", segment="lisanssiz_dagitim"),
                         _p("D", segment="lisanssiz_iletim"), _p("E", segment="lisansli_serbest", toplayici_portfoyu=True), _p("F")])
    assert g["grup_kaynagi"] == "varsayim" and g["gruplar"] == {None: ["A", "B", "F"]}
    assert set(g["disi_nedenleri"]) == {"C", "D", "E"} and "m.20(4)" in g["disi_nedenleri"]["E"] and "GTŞ/toplayıcı" in g["disi_nedenleri"]["D"]


def test_dsg_gruplari_beyan_kodlu_ve_kodsuz():
    g = dz.dsg_gruplari([_p("A", segment="lisansli_serbest", dsg_kodu="DSG-1"), _p("B", segment="lisansli_serbest", dsg_kodu=" DSG-1 "),
                         _p("C", segment="lisansli_serbest", dsg_kodu="DSG-2"), _p("D", segment="lisansli_serbest")])
    assert g["grup_kaynagi"] == "beyan" and g["gruplar"] == {"DSG-1": ["A", "B"], "DSG-2": ["C"]}
    assert list(g["disi_nedenleri"]) == ["D"] and "DSG kodu girilmedi" in g["disi_nedenleri"]["D"]
    assert dz.dsg_gruplari([]) == {"gruplar": {}, "disi_nedenleri": {}, "grup_kaynagi": "varsayim"}
    b = dz.segment_bilgisi({"segment": "lisansli_serbest", "dsg_kodu": " X ", "toplayici_portfoyu": 1})
    assert b["dsg_kodu"] == "X" and b["toplayici_portfoyu"] is True and dz.segment_bilgisi({})["dsg_kodu"] is None


def test_dsg_saatlik_iletim_lisanssiz_portfoy_disi():
    idx = pd.date_range("2026-11-01", periods=48, freq="h", tz="UTC")
    prog = {"A": pd.Series(5.0, index=idx), "B": pd.Series(5.0, index=idx), "I": pd.Series(5.0, index=idx)}
    ger = {"A": pd.Series(5.2, index=idx), "B": pd.Series(4.8, index=idx), "I": pd.Series(4.0, index=idx)}
    ptf = pd.Series(2000.0, index=idx); smf = pd.Series(2100.0, index=idx)
    r = d.dsg_saatlik(prog, ger, ptf, smf, yon="dengede", segmentler={"A": "lisansli_serbest", "B": "lisansli_serbest", "I": "lisanssiz_iletim"})
    assert r["disi"] == ["I"] and set(r["uyeler"]) == {"A", "B"}


def test_talimat_isareti():
    idx = pd.date_range("2026-11-01 00:00", periods=24, freq="h", tz=IST).tz_convert("UTC")
    olaylar = [{"tur": "talimat_yat", "baslangic": datetime(2026, 11, 1, 10, 30, tzinfo=IST), "bitis": datetime(2026, 11, 1, 12, 15, tzinfo=IST)},
               {"tur": "acil_kesme", "baslangic": datetime(2026, 11, 1, 20, 0, tzinfo=IST), "bitis": None},
               {"tur": "talimat_yal", "baslangic": datetime(2026, 11, 1, 12, 30, tzinfo=IST), "bitis": datetime(2026, 11, 1, 14, 0, tzinfo=IST)},
               {"tur": "planli_bakim", "baslangic": datetime(2026, 11, 1, 1, 0, tzinfo=IST), "bitis": datetime(2026, 11, 1, 3, 0, tzinfo=IST)}]
    t = dz.talimat_isareti(olaylar, idx)
    saat = {k.tz_convert(IST).hour: v for k, v in t.items() if v}
    assert saat == {10: "yat", 11: "yat", 12: "yat", 13: "yal", 20: "acil", 21: "acil", 22: "acil", 23: "acil"}   # yat 10:30–12:15 → 10–12; yal 12:30–14 → 12 dolu, 13; açık acil kesme sona kadar
    assert (dz.talimat_isareti([], idx) == "").all() and dz.talimat_isareti(olaylar, idx[:0]).empty
    assert "m.75(3)" in dz.DOKUM_NOTU_TALIMAT and "talimat" in dz.dokum_notu(pd.DataFrame(columns=dz.DOKUM_KOLONLAR + ["talimat"]))
    assert dz.DOKUM_NOTU_TALIMAT not in dz.dokum_notu(pd.DataFrame(columns=dz.DOKUM_KOLONLAR))
