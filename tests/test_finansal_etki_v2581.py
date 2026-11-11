"""v2.581 (Faz 2 F2-C, Stage 3B–D ve G) — uzlaştırma bileşenleri: EDT (EDTA/EDTB aylık toplama kuralı), KÜPST, nitelik (senaryo saat), segment kapısı
(lisanssız dağıtım: santral taşımaz, KÜPST uygulanmaz), segment yok uyarısı, DSG yerine-koyma satırı, çift sayım bekçisi, boş çerçeve, resmî eşleme
(mutabakat satırları → resmî satırlar, FEM farkı, B4 notu, gün dönemi / bildirim yok), test DB uçtan uca (gün + ay özeti, birleşik toplam)."""
from __future__ import annotations

from datetime import date

from pvquant.ext.platform import finans as fn
from pvquant.ext.turkiye import dengesizlik as d
from pvquant.services import dengesizlik_service as ds
from pvquant.services import finansal_etki_service as fe
from tests.test_finansal_etki_v2580 import _df, _fiyat, _izgara
from tests.test_finansal_etki_v2580 import santral as _santral

santral = _santral   # pytest fixture'ı bu modülde ad olarak tanıtır (noqa'sız; ruff --fix içe aktarmayı silmesin)

POZ = {"kaynak": "program", "sabit_mwh": None}


def _g(kod: str, segment: str | None = "lisansli_serbest", senaryo: list[int] | None = None, df_fn=None) -> dict:
    dn, iz = _izgara(kod)
    df = (df_fn or _df)(iz)
    pj = {"segment": segment} if segment else {}
    return {"donem": dn, "izgara": iz, "df": df, "fiyat": _fiyat(iz, senaryo), "kat": ds.katsayilar(pj), "segment": segment, "ariza_sayisi": 0,
            "luy_istisna": False, "bildirilen": None, "pozisyon": POZ, "pj": pj, "uretim": "scada", "pencere_gun": 45}


def _bil(out: dict, kod: str) -> dict:
    return next(b for b in out["bilesenler"] if b["kod"] == kod)


def test_edt_edta_edtb_ve_kupst_toplamlari():
    g = _g("2026-10")
    pv, fo = fe.saatlik(g)
    seg = ds.segment_bilgisi(g["pj"])
    out = fe.uzlastirma_bilesenleri_saf(g["donem"], g["izgara"], pv, fo, seg, g["kat"], False, None, fe.dayanaklar(g["donem"], "lisansli_serbest"))
    a = d.aylik_karne(pv)
    edt = _bil(out, "dengesizlik")
    assert edt["tutar_tl"] == round(float(a["edta"].sum() - a["edtb"].sum()), 2) == round(float(pv["edt_net"].sum()), 2)
    assert edt["alacak_tl"] == round(float(a["edta"].sum()), 2) and edt["borc_tl"] == round(float(a["edtb"].sum()), 2)
    assert edt["nitelik"] == "hesaplanan" and edt["toplanir"] is True and edt["kapsam_saat"] == int(pv["edt_net"].notna().sum()) and edt["beklenen_saat"] == 744
    assert (edt["kural_surumu"] and edt["dayanak"] and "m.110" in (edt["dayanak"] or "")) or edt["dayanak"]
    k = _bil(out, "kupst")
    if pv["kupst"].notna().any():
        assert k["tutar_tl"] == round(-float(pv["kupst"].sum()), 2) and k["nitelik"] == "hesaplanan" and k["kaynak"] == "kural tablosu" and k["borc_tl"] >= 0
        assert out["toplam"]["giren"] == ["dengesizlik", "kupst"] and out["toplam"]["tutar_tl"] == round(edt["tutar_tl"] + k["tutar_tl"], 2)
    else:
        assert k["nitelik"] == "eksik" and out["toplam"]["giren"] == ["dengesizlik"] and out["toplam"]["nitelik"] == "senaryo"
    assert out["fiyat"]["senaryo_saat"] == 0 and out["hesaplanamayan_saat"] == int((pv["durum"] != "ok").sum()) and fe.NOT_UZLASTIRMA in out["notlar"]


def test_senaryo_saat_nitelik_dusurur_ve_not():
    g = _g("2026-10-05", senaryo=[9, 10, 11])
    pv, fo = fe.saatlik(g)
    out = fe.uzlastirma_bilesenleri_saf(g["donem"], g["izgara"], pv, fo, ds.segment_bilgisi(g["pj"]), g["kat"], False)
    edt = _bil(out, "dengesizlik")
    assert fo["senaryo_saat"] == 3 and fo["yon_varsayilan_saat"] == 3 and edt["nitelik"] == "senaryo" and any("3 saatte senaryo fiyatı" in n for n in edt["notlar"])
    assert out["toplam"]["nitelik"] == "senaryo"


def test_segment_kapisi_lisanssiz_dagitim_ve_segment_yok():
    g = _g("2026-10-05", segment="lisanssiz_dagitim")
    pv, fo = fe.saatlik(g)
    seg = ds.segment_bilgisi(g["pj"])
    assert seg["santral_tasir"] is False and seg["kgup_yukumlu"] is False
    out = fe.uzlastirma_bilesenleri_saf(g["donem"], g["izgara"], pv, fo, seg, g["kat"], False)
    edt, k = _bil(out, "dengesizlik"), _bil(out, "kupst")
    assert edt["toplanir"] is False and any("santral hesabına girmez" in n for n in edt["notlar"]) and out["santral_tasir"] is False
    assert k["toplanir"] is False and k["nitelik"] == "eksik" and any("uygulanmaz" in n for n in k["notlar"])
    assert out["toplam"]["giren"] == [] and out["toplam"]["tutar_tl"] is None and out["toplam"]["eksik"] == []
    g2 = _g("2026-10-05", segment=None)
    pv2, fo2 = fe.saatlik(g2)
    out2 = fe.uzlastirma_bilesenleri_saf(g2["donem"], g2["izgara"], pv2, fo2, ds.segment_bilgisi({}), g2["kat"], False)
    assert fe.NOT_SEGMENT_YOK in _bil(out2, "dengesizlik")["notlar"] and _bil(out2, "dengesizlik")["toplanir"] is True


def test_dsg_yerine_koyma_ve_bos_cerceve():
    g = _g("2026-10-05")
    pv, fo = fe.saatlik(g)
    dsg = {"grup": "DSG-A", "santral": 3, "n_saat": 24, "dagitim_anahtari": "sapma", "dagitim_etiket": "sapma payına göre", "esik": 0.05,
           "uye": {"edt_tek_tl": -1200.0, "edt_dsg_tl": -700.0, "netlesme_farki_tl": 500.0, "pay_pct": 41.2, "kupst_tl": 50.0}}
    out = fe.uzlastirma_bilesenleri_saf(g["donem"], g["izgara"], pv, fo, ds.segment_bilgisi(g["pj"]), g["kat"], False, dsg)
    b = _bil(out, "dsg")
    assert b["tutar_tl"] == -700.0 and b["nitelik"] == "senaryo" and b["toplanir"] is False and fe.NOT_DSG in b["notlar"] and "DSG-A" in b["kaynak"]
    assert any("Tek başına" in n and "+500" in n for n in b["notlar"]) and any("%5" in n for n in b["notlar"])
    assert "dsg" not in out["toplam"]["giren"]
    out2 = fe.uzlastirma_bilesenleri_saf(g["donem"], g["izgara"], pv, fo, ds.segment_bilgisi(g["pj"]), g["kat"], False, {"neden": "DSG kodu girilmedi; …"})
    assert not any(b["kod"] == "dsg" for b in out2["bilesenler"]) and any("DSG kodu girilmedi" in n for n in out2["notlar"])
    bos = fe.uzlastirma_bilesenleri_saf(g["donem"], g["izgara"], None, {}, ds.segment_bilgisi(g["pj"]), g["kat"], False)
    assert _bil(bos, "dengesizlik")["nitelik"] == "eksik" and _bil(bos, "kupst")["nitelik"] == "eksik" and bos["toplam"]["eksik"] == ["dengesizlik", "kupst"]
    assert bos["toplam"]["tutar_tl"] is None and bos["kural_surumu"] is None


def test_luy_istisnasi_notu():
    g = _g("2026-11-05", segment="lisanssiz_iletim")
    g["luy_istisna"] = True; g["kat"] = ds.katsayilar({"segment": "lisanssiz_iletim"})
    pv, fo = fe.saatlik(g)
    out = fe.uzlastirma_bilesenleri_saf(g["donem"], g["izgara"], pv, fo, ds.segment_bilgisi(g["pj"]), g["kat"], True)
    k = _bil(out, "kupst")
    assert (k["tutar_tl"] == 0.0 and any("LÜY istisnası" in n for n in k["notlar"])) or k["nitelik"] == "eksik"


def test_resmi_kiyas_saf():
    dn, _ = _izgara("2026-10")
    m = {"bildirim": {"surum": "nihai", "surum_etiket": "nihai bildirim", "zaman": "2026-11-16T10:00", "surum_kaynagi": "dosya"},
         "satirlar": [{"kod": "imbalance", "bildirim_alacak_tl": 1000.0, "bildirim_borc_tl": 4000.0, "fark_tl": -200.0, "durum": "fark", "dogrulama": "kismi"},
                      {"kod": "kupst", "bildirim_alacak_tl": 0.0, "bildirim_borc_tl": 300.0, "fark_tl": 5.0, "durum": "uyumlu", "dogrulama": "tam"},
                      {"kod": "dam", "bildirim_alacak_tl": 50000.0, "bildirim_borc_tl": 0.0, "fark_tl": None, "durum": "hesaplanamaz"}],
         "guvenilirlik": {"durum": "kismi", "etiket": "Kısmi karşılaştırma"}, "saatlik_detay": {"yuklu": True, "ortak_saat": 500, "toplam": {"edt_net_fark_tl": -12.0}},
         "eylem": "Fark var: …"}
    r = fe.resmi_kiyas_saf(m, dn, edt_tutar_tl=-3250.0, kupst_tutar_tl=-295.0)
    kod = {b["kod"]: b for b in r["bilesenler"]}
    assert kod["dengesizlik_resmi"]["tutar_tl"] == -3000.0 and kod["dengesizlik_resmi"]["alacak_tl"] == 1000.0 and kod["dengesizlik_resmi"]["borc_tl"] == 4000.0
    assert kod["dengesizlik_resmi"]["nitelik"] == "resmi" and kod["dengesizlik_resmi"]["toplanir"] is False and "nihai bildirim" in kod["dengesizlik_resmi"]["kaynak"]
    assert any("fark var · kismi" in n for n in kod["dengesizlik_resmi"]["notlar"])
    assert r["fark"] == {"dengesizlik": -250.0, "kupst": 5.0} and r["durum"] == {"dengesizlik": "fark", "kupst": "uyumlu"}
    assert fe.NOT_B4 in kod["dengesizlik_resmi"]["notlar"] and fe.NOT_B4 not in kod["kupst_resmi"]["notlar"]   # −250 ≠ −200 (B4), 5 = 5
    assert r["guvenilirlik"]["durum"] == "kismi" and r["saatlik_detay"]["ortak_saat"] == 500 and r["bildirim"]["surum"] == "nihai" and r["eylem"].startswith("Fark var")
    assert fe.resmi_kiyas_saf(None, dn, -1.0, None)["not"] == fe.NOT_BILDIRIM_YOK
    assert fe.resmi_kiyas_saf({"bildirim": None, "satirlar": []}, dn, -1.0, None)["bilesenler"] == []
    dg, _ = _izgara("2026-10-05")
    assert fe.resmi_kiyas_saf(m, dg, -1.0, None)["not"] == fe.NOT_RESMI_AY
    m2 = {"bildirim": m["bildirim"], "satirlar": [m["satirlar"][2]]}
    r2 = fe.resmi_kiyas_saf(m2, dn, -1.0, -1.0)
    assert r2["bilesenler"] == [] and r2["durum"] == {"dengesizlik": "bildirimde_yok", "kupst": "bildirimde_yok"}


def test_cift_sayim_bekcisi_birlesik_toplam():
    g = _g("2026-10-05")
    pv, fo = fe.saatlik(g)
    uz = fe.uzlastirma_bilesenleri_saf(g["donem"], g["izgara"], pv, fo, ds.segment_bilgisi(g["pj"]), g["kat"], False)
    gelir = fn.Bilesen("satis_geliri", "Enerji satışı", 9000.0, nitelik="sozlesme_tahmini")
    resmi = fn.Bilesen("dengesizlik_resmi", "EDT (EPİAŞ)", -100.0, nitelik="resmi", toplanir=False)
    t = fn.toplam([gelir] + uz["_nesneler"] + [resmi])
    beklenen = 9000.0 + sum(b.tutar_tl for b in uz["_nesneler"] if b.toplanir and b.tutar_tl is not None)
    assert t["tutar_tl"] == round(beklenen, 2) and "dengesizlik_resmi" not in t["giren"] and t["giren"][0] == "satis_geliri"
    import pytest
    with pytest.raises(ValueError):
        fn.toplam([gelir] + uz["_nesneler"] + [fn.Bilesen("dengesizlik", "EDT yine", -1.0, nitelik="hesaplanan")])


# ---------------------------------------------------------------- test DB
def test_db_uzlastirma_ve_birlesik_ozet(santral):
    tid, plant = santral
    uz = fe.uzlastirma(tid, plant, "2026-09-05", bugun=date(2026, 9, 11))
    kod = [b["kod"] for b in uz["bilesenler"]]
    assert kod[:2] == ["dengesizlik", "kupst"] and uz["uretim"] == "scada" and uz["donem"]["kod"] == "2026-09-05"
    edt = uz["bilesenler"][0]
    assert edt["nitelik"] in ("hesaplanan", "senaryo") and edt["beklenen_saat"] == 24 and edt["kapsam_saat"] == 23 and edt["toplanir"] is True
    assert uz["resmi"]["not"] == fe.NOT_RESMI_AY and uz["resmi"]["bilesenler"] == [] and any("DSG kodu girilmedi" in n for n in uz["notlar"]) is False
    assert isinstance(uz["gostergeler"]["bilesenler"], list)
    o = fe.ozet(tid, plant, "2026-09", bugun=date(2026, 9, 11))
    assert set(o) >= {"donem", "uretim", "gelir", "uzlastirma", "bilesenler", "toplam"} and "_nesneler" not in o["uzlastirma"]
    kodlar = [b["kod"] for b in o["bilesenler"]]
    assert kodlar[0] == "satis_geliri" and kodlar[1] == "dengesizlik" and kodlar[2] == "kupst"
    assert o["toplam"]["giren"][0] == "satis_geliri" and "dengesizlik" in o["toplam"]["giren"]
    gelir, edt = o["bilesenler"][0], o["bilesenler"][1]
    giren = [b for b in o["bilesenler"] if b["kod"] in o["toplam"]["giren"]]
    assert o["toplam"]["tutar_tl"] == round(sum(b["tutar_tl"] for b in giren), 2) and gelir["tutar_tl"] > 0 and edt["tutar_tl"] <= 0
    assert o["uzlastirma"]["resmi"]["not"] == fe.NOT_BILDIRIM_YOK or o["uzlastirma"]["resmi"]["not"] is None
    assert o["uretim"]["gerceklesen"]["saat"] == 239 and o["gelir"]["bilesenler"][0]["kod"] == "satis_geliri"
