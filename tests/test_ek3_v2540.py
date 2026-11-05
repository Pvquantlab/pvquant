"""v2.540 — EK-3 birincil metin okumaları: DK-612 (Karar 14967 Ek sıra 17, YEK-G eşiksiz), DK-333 (YEK Yön. m.23(9) 1.1–18.10.2026),
DK-1019 (ETKB 2022 üretim emisyon faktörü 0,438 tCO₂/MWh)."""
from datetime import date, datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from pvquant.reporting import excel
from pvquant.services import dengesizlik_service as dz, olay_service as os_, yekdem_service as ys

IST = ZoneInfo("Europe/Istanbul")


def test_dk1019_co2_faktoru_etkb():
    assert excel.CO2_T_MWH == 0.438 and "ETKB" in excel.CO2_KAYNAK and "2022" in excel.CO2_KAYNAK and "06.12.2024" in excel.CO2_KAYNAK
    assert "tasarruf" not in excel.CO2_KAYNAK.lower() and "yaklaşım" in excel.CO2_KAYNAK_KISA


def test_dk333_m23_9_gunu():
    assert ys.m23_9_gunu(date(2026, 5, 19)) and ys.m23_9_gunu(date(2026, 1, 1)) and ys.m23_9_gunu(date(2026, 3, 20))   # Salı 19 Mayıs, Perşembe 1 Ocak, Ramazan Bayramı Cuma
    assert not ys.m23_9_gunu(date(2026, 5, 17)) and not ys.m23_9_gunu(date(2026, 3, 22))   # Pazar hariç (17 Mayıs Pazar; 22 Mart Pazar)
    assert not ys.m23_9_gunu(date(2026, 10, 29)) and not ys.m23_9_gunu(date(2025, 5, 19)) and not ys.m23_9_gunu(date(2026, 5, 20))   # 19.10.2026 sonrası / 2026 öncesi / tatil değil
    assert "33122" in ys.M23_9_NOTU and "33405" in ys.M23_9_NOTU and "yorum" in ys.M23_9_NOTU


def _pv_tatil():
    idx = pd.date_range("2026-05-19 09:00", periods=4, freq="h", tz=IST).tz_convert("UTC")   # 19 Mayıs 2026 Salı (tatil)
    return pd.DataFrame({"ptf": [2000.0] * 4, "smf": [2100.0] * 4, "yon": ["dengede"] * 4, "kgup": [5.0, 5.0, 5.0, 5.0], "gerceklesen": [6.0, 4.0, 7.0, 5.0],
                         "program_kaynak": ["bildirilen", "bildirilen", "oneri", "bildirilen"]}, index=idx)


def test_dk333_m23_9_isaret_ve_ozet():
    pv = _pv_tatil(); yek = pd.Series(3000.0, index=pv.index)
    e = ys.m23_6_isaretle(pv, yek)
    assert list(e["m23_6"]) == ["kapsam_disi"] * 4   # m.23(6) 19.10.2026'dan
    assert list(e["m23_9"]) == ["evet", "hayir", "kgup_yok", "hayir"] and e["m23_9_mwh"].tolist() == [1.0, 0, 0, 0]
    assert abs(e["m23_9_tl"].iloc[0] - 1.0 * (3000 - 2000)) < 1e-9
    o = ys.m23_6_ozeti(pv, e, 30)["m23_9"]
    assert o["kapsam_saat"] == 4 and o["saat"] == 1 and o["kgup_yok_saat"] == 1 and o["mwh"] == 1.0 and o["tl"] == 1000.0 and o["ilk_saat"] == "2026-05-19 09:00"
    # Pazar (17 Mayıs) ve 19.10 sonrası kapsam dışı
    pv2 = pv.copy(); pv2.index = pv2.index - pd.Timedelta(days=2)
    assert set(ys.m23_6_isaretle(pv2, yek.set_axis(pv2.index))["m23_9"]) == {"kapsam_disi"}
    dk = dz.dokum_df(ys_pv := pv.assign(pozisyon=pv["kgup"], sapma=pv["gerceklesen"] - pv["kgup"], k=0.03, l=0.03, p_neg=2100.0, p_poz=2000.0, edt_neg=0.0, edt_poz=0.0, edt_net=0.0,
                                        kupsm=0.0, kupst=0.0, toplam_maliyet=0.0, kural_surumu="t", durum="ok"), e)
    assert list(dk.columns) == dz.DOKUM_KOLONLAR + dz.YEKDEM_KOLONLAR and list(dk["m23_9"]) == ["evet", "hayir", "kgup_yok", "hayir"] and "m23_9" in dz.dokum_notu(dk)
    assert len(ys_pv) == 4


def test_dk612_yek_g_sira17():
    olay = {"tur": "ariza", "etkilenen_kw": 10000, "baslangic": datetime(2027, 2, 10, 9, 30, tzinfo=IST)}
    assert os_.dahili_bilgi(olay, 40000) is None   # eşik altı, YEK-G değil
    d = os_.dahili_bilgi(olay, 40000, simdi=datetime(2027, 2, 10, 9, 50, tzinfo=IST), yek_g=True)
    assert d["esik"] == "YEK-G sıra 17 (eşik yok)" and d["kalan_dk"] == 40 and d["basladi"] is True and "sıra 17" in d["kosul"] and "3(b)" in d["kosul"]
    assert os_.dahili_bilgi({**olay, "tur": "planli_bakim"}, 40000, yek_g=True) is None   # yalnız arıza (plansız bakım türü yok)
    ust = os_.dahili_bilgi({**olay, "etkilenen_kw": 35000}, 40000, yek_g=True)
    assert ust["esik"] == "tesis 30 MW" and ust["kosul"] is None
    assert dz.segment_bilgisi({"segment": "lisansli_yekdem", "yek_g_kayitli": True})["yek_g_kayitli"] is True and dz.segment_bilgisi({})["yek_g_kayitli"] is False
    assert "sıra 17" in os_.DAHILI_NOTU and "DK-" not in os_.DAHILI_YEK_G_NOTU
