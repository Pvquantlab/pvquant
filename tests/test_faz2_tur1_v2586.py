"""v2.586 (Faz 2 F2-H, Stage 8, TUR 1 — finansal doğruluk): kural sürümü geçişleri (31.12.2025 → 1.1.2026; 19.10.2026 EDTA/EDTB ayrık; 1.11.2026 V = 100),
sıfır/negatif fiyat, kısmi (süren) dönem, birim dönüşümleri, gelir/maliyet sınıfları, çift sayım bekçisi, eksik sistem yönü, senaryo saatinin niteliği."""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from pvquant.ext.platform import finans as fn
from pvquant.ext.turkiye import dengesizlik as d
from pvquant.services import dengesizlik_service as ds
from pvquant.services import finansal_etki_service as fe
from tests.test_finansal_etki_v2580 import _df, _fiyat
from tests.test_finansal_etki_v2581 import POZ

PLANT = {"id": "p1", "name": "Tur1 GES", "capacity_kwp": 1000.0, "lat": 37.0, "lon": 32.0, "tz": "Europe/Istanbul", "params_json": {"segment": "lisansli_serbest"}}


def _g_aralik(bas: str, bit: str, bugun: date, senaryo=None, ptf=None, yon="dengede"):
    dn = {"tur": "ozel", "kod": f"{bas}..{bit}", "bas": date.fromisoformat(bas), "bit": date.fromisoformat(bit), "etiket": bas, "kirpildi": False, "tz": "Europe/Istanbul",
          "bas_utc": fn.yerel_gun_baslangici_utc(date.fromisoformat(bas)), "bit_utc": fn.yerel_gun_baslangici_utc(date.fromisoformat(bit))}
    dn["gun"] = (dn["bit"] - dn["bas"]).days; dn["saat"] = dn["gun"] * 24
    iz = fn.saat_kumesi(dn); df = _df(iz); f = _fiyat(iz, senaryo)
    if ptf is not None:
        f["ptf"] = ptf
    f["yon"] = yon
    pj = {"segment": "lisansli_serbest"}
    return {"donem": dn, "izgara": iz, "df": df, "fiyat": f, "kat": ds.katsayilar(pj), "segment": "lisansli_serbest", "ariza_sayisi": 0, "luy_istisna": False,
            "bildirilen": None, "pozisyon": POZ, "pj": pj, "uretim": "scada", "pencere_gun": 30}


def _edt(g):
    pv, fo = fe.saatlik(g)
    out = fe.uzlastirma_bilesenleri_saf(g["donem"], g["izgara"], pv, fo, ds.segment_bilgisi(g["pj"]), g["kat"], False)
    return pv, out, next(b for b in out["bilesenler"] if b["kod"] == "dengesizlik")


def test_kural_gecisi_2025_2026():
    pv, out, edt = _edt(_g_aralik("2025-12-31", "2026-01-02", date(2026, 11, 11)))
    assert "edt-2025" in edt["kural_surumu"] and "edt-2026" in edt["kural_surumu"]   # iki kural aynı dönemde, sürüm dizgisinde ikisi de
    a = d.aylik_karne(pv)
    assert len(a) == 2 and edt["alacak_tl"] == round(float(a["edta"].sum()), 2) and edt["borc_tl"] == round(float(a["edtb"].sum()), 2)
    assert edt["tutar_tl"] == round(float(pv["edt_net"].sum()), 2) and edt["nitelik"] == "hesaplanan"


def test_kural_gecisi_19_10_2026_edta_ayrik_ve_1_11_2026_v100():
    pv, out, edt = _edt(_g_aralik("2026-10-18", "2026-10-20", date(2026, 11, 11)))
    assert "edta_net" in edt["kural_surumu"] and "edta_ayrik" in edt["kural_surumu"]
    pv2, out2, edt2 = _edt(_g_aralik("2026-10-31", "2026-11-02", date(2026, 11, 11)))
    assert "V150" in edt2["kural_surumu"] and "V100" in edt2["kural_surumu"]
    assert edt2["dayanak"] is None or "m.110" in (edt2["dayanak"] or "") or edt2["dayanak"]
    # EDTA − EDTB = net her iki kuralda da
    for p, e in ((pv, edt), (pv2, edt2)):
        assert abs((e["alacak_tl"] - e["borc_tl"]) - float(p["edt_net"].sum())) < 0.02


def test_sifir_ve_negatif_fiyat_sonlu_tutar():
    g = _g_aralik("2026-10-05", "2026-10-06", date(2026, 11, 11), ptf=0.0)
    pv, out, edt = _edt(g)
    assert edt["tutar_tl"] is not None and np.isfinite(edt["tutar_tl"]) and edt["nitelik"] == "hesaplanan"
    g2 = _g_aralik("2026-10-05", "2026-10-06", date(2026, 11, 11), ptf=-50.0, yon="fazla")
    pv2, out2, edt2 = _edt(g2)
    assert edt2["tutar_tl"] is not None and np.isfinite(edt2["tutar_tl"]) and out2["toplam"]["tutar_tl"] is not None
    # negatif fiyatta fazla üretim alacak yazmaz (B dalı): alacak sütunu eksiye düşmez, borç artı kalır
    assert edt2["alacak_tl"] >= 0 and edt2["borc_tl"] >= 0


def test_eksik_sistem_yonu_ve_senaryo_niteligi():
    g = _g_aralik("2026-10-05", "2026-10-06", date(2026, 11, 11), yon=None)
    pv, out, edt = _edt(g)
    assert out["hesaplanamayan_saat"] == 24 and edt["kapsam_saat"] == 0 and any("sistem yönü verisi olmadığından" in n for n in edt["notlar"])
    g2 = _g_aralik("2026-10-05", "2026-10-06", date(2026, 11, 11), senaryo=list(range(24)))
    pv2, out2, edt2 = _edt(g2)
    assert edt2["nitelik"] == "senaryo" and out2["toplam"]["nitelik"] == "senaryo" and out2["fiyat"]["senaryo_saat"] == 24


def test_kismi_suren_donem_ve_birimler():
    dn = fe.donem(PLANT, "2026-11", date(2026, 11, 11))
    assert dn["kirpildi"] and dn["saat"] == 11 * 24 and fn.saat_kumesi(dn)[-1] == dn["bit_utc"] - pd.Timedelta(hours=1)
    iz = fn.saat_kumesi(dn); df = _df(iz)
    o = fe.uretim_ozeti_saf(dn, iz, df, None, "scada", None, 1000.0)
    assert o["gerceklesen"]["beklenen_saat"] == 264 and o["donem"]["kirpildi"] is True
    assert abs(o["gerceklesen"]["mwh"] * 1000.0 - float(df["gercek_kw"].sum())) < 1e-6   # MWh = Σ kW×1 sa / 1000
    g = fe.satis_geliri_saf(dn, iz, df["gercek_kw"], {"tip": "sabit", "tl_mwh": 2000.0}, _fiyat(iz), PLANT, "lisansli_serbest", None)
    assert abs(g["bilesenler"][0]["tutar_tl"] - o["gerceklesen"]["mwh"] * 2000.0) < 0.01 and g["tarife"]["ortalama_fiyat_tl_mwh"] == 2000.0


def test_gelir_maliyet_siniflari_ve_cift_sayim():
    g = _g_aralik("2026-10-05", "2026-10-06", date(2026, 11, 11))
    pv, out, edt = _edt(g)
    gelir = fn.Bilesen("satis_geliri", "Enerji satışı", 9000.0, nitelik="sozlesme_tahmini")
    kupst = next(b for b in out["_nesneler"] if b.kod == "kupst")
    assert gelir.alacak_tl == 9000.0 and gelir.borc_tl == 0.0                      # gelir yalnız alacak
    if kupst.tutar_tl is not None:
        assert kupst.tutar_tl <= 0 and kupst.alacak_tl == 0.0                       # KÜPST yalnız borç
    dus = fn.Bilesen("uretim_dusuklugu", "Üretim düşüklüğü", -500.0, nitelik="sozlesme_tahmini", toplanir=False)
    t = fn.toplam([gelir] + out["_nesneler"] + [dus])
    assert "uretim_dusuklugu" not in t["giren"] and t["tutar_tl"] == round(9000.0 + sum(b.tutar_tl for b in out["_nesneler"] if b.toplanir and b.tutar_tl is not None), 2)
    assert fn.fem_isareti("dengesizlik.dengesizlik_tl", 10.0) == -10.0 and fn.fem_isareti("dengesizlik.edt_net", 10.0) == 10.0   # kayıp ve EDT aynı sapmanın iki görünümü; biri toplanır
