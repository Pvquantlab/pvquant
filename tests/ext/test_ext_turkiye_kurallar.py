"""F-01/F-02/F-03/F-17 kabul testleri — F_PRD §5 vektörleri (beklenen değerler ürün kodundan DEĞİL, bağımsız Decimal hesabından;
scratch `vektorler.py`, 29.10.2026, 54/54 PRD ile birebir). Fiyatlar EPİAŞ bültenlerinden (C iş kolu serisi), program/gerçekleşen varsayımsal.
İşaret: edt_neg katılımcının ödediği (≥0); edt_poz katılımcının aldığı (negatifse öder). Tolerans ±0,01 TL."""
from datetime import date

import numpy as np
import pandas as pd
import pytest

from pvquant.ext.tahmin import alt_saatlik
from pvquant.ext.turkiye import dengesizlik as d, kurallar as kr

IST = "Europe/Istanbul"


def _saat(ts: str) -> pd.DatetimeIndex:
    return pd.DatetimeIndex([pd.Timestamp(ts, tz=IST).tz_convert("UTC")])


def _vek(ts, ptf, smf, yon, F, A, segment="lisansli_serbest", **ek) -> pd.Series:
    i = _saat(ts)
    s = d.saatlik(pd.Series([F], index=i), pd.Series([A], index=i), pd.Series([ptf], index=i), pd.Series([smf], index=i),
                  yon=yon, segment=segment, **ek)
    return s.iloc[0]


def _yakin(a, b):
    assert a == pytest.approx(b, abs=0.011), (a, b)


# ---------------------------------------------------------------- F-01: sınır günleri --------------------------------
def test_f01_sinir_gunleri():
    assert kr.kural(date(2025, 12, 31)).edt.rejim == "2025" and kr.kural(date(2026, 1, 1)).edt.rejim == "2026"
    assert kr.kural(date(2026, 10, 31)).edt.V == 150.0 and kr.kural(date(2026, 11, 1)).edt.V == 100.0          # Karar 14911
    assert kr.kural(date(2026, 4, 3)).edt.AFL == 3400.0 and kr.kural(date(2026, 4, 4)).edt.AFL == 4500.0       # Karar 14459
    assert kr.kural(date(2026, 10, 18)).edt.toplama == "edta_net" and kr.kural(date(2026, 10, 19)).edt.toplama == "edta_ayrik"
    assert kr.kural(date(2026, 10, 31)).kupst.net_sapma is False and kr.kural(date(2026, 11, 1)).kupst.net_sapma is True   # 14907
    assert kr.kural(date(2025, 6, 1)).dsg_esik == 0.10 and kr.kural(date(2026, 6, 1)).dsg_esik == 0.05                  # 13869
    k27 = kr.kural(date(2027, 1, 1)); assert k27.belirsiz_2027 and "VARSAYILDI" in k27.dsg_dayanak
    # UTC damgası İstanbul gününe göre seçilir: 31.10.2026 23:00 IST = 20:00 UTC → V 150; 01.11 00:00 IST → V 100
    c = kr.parametre_cercevesi(pd.date_range("2026-10-31 20:00", periods=2, freq="h", tz="UTC"))
    assert list(c["V"]) == [150.0, 100.0]
    # her satırda dayanak dolu
    for r in kr.tablo("lisansli_serbest"):
        assert r["edt_dayanak"] and r["kupst"]["dayanak"] and r["dsg_dayanak"]
    assert kr.kural(date(2026, 2, 1), "lisansli_serbest").kupst.n_etkin(29) == 0.05 and kr.kural(date(2026, 2, 1), "lisansli_serbest").kupst.n_etkin(30) == 0.08


def test_yon_normalize():
    assert kr.yon_normalize("Enerji Açığı") == "acik" and kr.yon_normalize("Enerji Fazlası") == "fazla" and kr.yon_normalize("Dengede") == "dengede"
    assert kr.yon_normalize(None) is None and kr.yon_normalize(float("nan")) is None and kr.yon_normalize("bilinmeyen") is None


# ---------------------------------------------------------------- F-02: EDT vektörleri -------------------------------
def test_t01_t02_2025_rejimi():
    r = _vek("2025-07-15 12:00", 999.99, 2000.00, "acik", 4.0, 3.4)
    _yakin(r.p_neg, 2060.00); _yakin(r.edt_neg, 1236.00); _yakin(r.dengesizlik_maliyeti, 636.01); _yakin(r.kupst, 12.00)
    assert r.rejim == "2025" and r.dal == "2025"
    r = _vek("2025-07-15 12:00", 999.99, 2000.00, "acik", 4.0, 4.6)
    _yakin(r.p_poz, 969.99); _yakin(r.edt_poz, 581.99); _yakin(r.dengesizlik_maliyeti, 18.00); _yakin(r.kupst, 12.00)


def test_t03_t04_afl_dali():
    r = _vek("2026-01-26 08:00", 3400.00, 3400.00, "fazla", 10, 8)
    _yakin(r.p_neg, 3677.10); _yakin(r.edt_neg, 7354.20); _yakin(r.dengesizlik_maliyeti, 554.20); _yakin(r.kupst, 204.00); assert r.dal == "AFL"
    _yakin(_vek("2026-01-26 08:00", 3400.00, 3400.00, "fazla", 10, 8, ariza_sayisi=30).kupst, 326.40)
    r = _vek("2026-01-26 08:00", 3400.00, 3400.00, "fazla", 10, 12)
    _yakin(r.p_poz, 3196.00); _yakin(r.edt_poz, 6392.00); _yakin(r.dengesizlik_maliyeti, 408.00); _yakin(r.kupst, 204.00)


def test_t05_t06_yon_bagli_katsayi():
    r = _vek("2026-01-26 00:00", 2876.00, 3170.00, "acik", 10, 8)
    _yakin(r.p_neg, 3360.20); _yakin(r.p_poz, 2789.72); _yakin(r.edt_neg, 6720.40); _yakin(r.dengesizlik_maliyeti, 968.40)
    r = _vek("2026-10-26 17:00", 4500.00, 4500.00, "acik", 10, 8)
    _yakin(r.p_neg, 5008.50); _yakin(r.p_poz, 4365.00); _yakin(r.edt_neg, 10017.00); _yakin(r.dengesizlik_maliyeti, 1017.00); _yakin(r.kupst, 270.00)


def test_t07_t08_b_dali_fazla_uretim_borc():
    r = _vek("2026-02-01 09:00", 1547.40, 0.00, "fazla", 3.0, 3.5)
    _yakin(r.p_poz, -106.00); _yakin(r.edt_poz, -53.00); _yakin(r.dengesizlik_maliyeti, 826.70); _yakin(r.kupst, 20.12); assert r.dal == "B"
    r = _vek("2026-02-01 09:00", 1547.40, 0.00, "fazla", 3.0, 2.5)
    _yakin(r.p_neg, 1593.82); _yakin(r.edt_neg, 796.91); _yakin(r.dengesizlik_maliyeti, 23.21); _yakin(r.kupst, 20.12); assert r.dal == "normal"


def test_t09_t10_v_tabani_ve_750():
    r = _vek("2026-03-07 12:00", 100.00, 3000.00, "acik", 2, 3)
    _yakin(r.p_poz, -103.00); _yakin(r.edt_poz, -103.00); _yakin(r.dengesizlik_maliyeti, 203.00); assert r.dal == "B"
    r = _vek("2026-11-07 12:00", 100.00, 3000.00, "acik", 2, 3)            # V = 100 → normal dal (karşı-olgu tarihi 1.11 sonrası)
    _yakin(r.p_poz, 97.00); _yakin(r.dengesizlik_maliyeti, 3.00); assert r.dal == "normal"
    r = _vek("2026-03-20 10:00", 100.01, 100.01, "fazla", 3, 2)
    _yakin(r.p_neg, 154.50); _yakin(r.edt_neg, 154.50); _yakin(r.dengesizlik_maliyeti, 54.49); _yakin(r.kupst, 28.50); assert r.dal == "V"
    _yakin(_vek("2026-11-20 10:00", 100.01, 100.01, "fazla", 3, 2).p_neg, 103.01)


def test_t11_iki_rejim_ocak_gecisi():
    r = _vek("2026-01-25 12:00", 1655.01, 5.00, "fazla", 10, 12)
    _yakin(r.p_poz, -106.00); _yakin(r.edt_poz, -212.00); _yakin(r.dengesizlik_maliyeti, 3522.02); _yakin(r.kupst, 99.30)
    f = d.birim_fiyatlar(pd.Series([1655.01], index=_saat("2025-12-25 12:00")), pd.Series([5.00], index=_saat("2025-12-25 12:00")), "fazla")
    _yakin(float(f.p_poz.iloc[0]), 4.85)          # bülten yapısı (eski formül) = 2025 rejimi


def test_t12_t13_kupst_net_ve_dagitim_lisanssiz():
    i = _saat("2026-11-05 08:00")
    r = _vek("2026-11-05 08:00", 3400.00, 3400.00, "fazla", 10, 12, uecm_mwh=pd.Series([0.3], index=i))
    _yakin(r.kupst, 153.00)                      # 14907 net sapma; brüt tanımla 204,00 olurdu
    _yakin(_vek("2026-10-05 08:00", 3400.00, 3400.00, "fazla", 10, 12, uecm_mwh=pd.Series([0.3], index=_saat("2026-10-05 08:00"))).kupst, 204.00)
    r = _vek("2026-11-05 08:00", 3400.00, 3400.00, "fazla", 100, 70, segment="lisanssiz_dagitim", portfoy=True)
    _yakin(r.kupst, 170.00)
    assert _vek("2026-11-05 08:00", 3400.00, 3400.00, "fazla", 100, 70, segment="lisanssiz_dagitim").kupst == 0.0   # santral sahibinde 0


def test_t15_aylik_toplama_18_19_ekim():
    def ay(gunler):
        i = pd.DatetimeIndex([pd.Timestamp(g, tz=IST).tz_convert("UTC") for g in gunler])
        s = d.saatlik(pd.Series([10.0, 3.0], index=i), pd.Series([12.0, 3.5], index=i), pd.Series([3400.0, 1547.40], index=i),
                      pd.Series([3400.0, 0.0], index=i), yon="fazla")
        _yakin(float(s.edt_poz.iloc[0]), 6392.00); _yakin(float(s.edt_poz.iloc[1]), -53.00)
        return d.aylik_karne(s).iloc[0]
    eski = ay(["2026-10-10 08:00", "2026-10-11 09:00"]); _yakin(eski.edta, 6339.00); _yakin(eski.edtb, 0.00)
    yeni = ay(["2026-10-20 08:00", "2026-10-21 09:00"]); _yakin(yeni.edta, 6392.00); _yakin(yeni.edtb, 53.00)


def test_t16_smf_n_p_15dk():
    i = _saat("2026-06-01 12:00")
    f = d.birim_fiyatlar(pd.Series([2800.0], index=i), pd.Series([3000.0], index=i), "acik",
                         smf_n=pd.Series([3200.0], index=i), smf_p=pd.Series([2900.0], index=i))
    _yakin(float(f.p_neg.iloc[0]), 3392.00); _yakin(float(f.p_poz.iloc[0]), 2716.00)
    # çeyrek SMF verilmezse F-02 ile aynı (geri uyumluluk)
    g = d.birim_fiyatlar(pd.Series([2800.0], index=i), pd.Series([3000.0], index=i), "acik")
    _yakin(float(g.p_neg.iloc[0]), 3180.00); _yakin(float(g.p_poz.iloc[0]), 2716.00)
    # alt_saatlik: çeyrek SMF'lerden SMF_N/SMF_P
    q = pd.Series([3000.0, 3200.0, 3100.0, 2900.0], index=pd.date_range(i[0], periods=4, freq="15min"))
    np_ = alt_saatlik.smf_n_p(q)
    assert float(np_["smf_n"].iloc[0]) == 3200.0 and float(np_["smf_p"].iloc[0]) == 2900.0
    u = alt_saatlik.uzlastirma_15dk(pd.Series([8.0], index=i), pd.Series([10.0], index=i), pd.Series([2800.0], index=i), q, yon="acik", segment="lisansli_serbest")
    _yakin(float(u.p_neg.iloc[0]), 3392.00); _yakin(float(u.edt_neg.iloc[0]), 2 * 3392.00)


def test_t17_sifir_fiyat_b_dali():
    r = _vek("2026-10-25 13:00", 0.0, 0.0, "fazla", 4, 5)
    _yakin(r.p_poz, -106.00); _yakin(r.edt_poz, -106.00); _yakin(r.kupst, 25.50); assert r.dal == "B"


# ---------------------------------------------------------------- dürüstlük: eksik yön / segment / birim ------------
def test_yon_eksik_hesap_durur_ve_smf_ptf_den_cikarilmaz():
    r = _vek("2026-02-01 09:00", 1547.40, 0.0, None, 3.0, 3.5)
    assert np.isnan(r.p_poz) and np.isnan(r.edt_poz) and r.durum == "yon_eksik"
    r25 = _vek("2025-02-01 09:00", 1547.40, 0.0, None, 3.0, 3.5)        # 2025'te yön gerekmez
    assert r25.durum == "ok" and r25.p_poz == pytest.approx(0.0)


def test_segment_yoksa_kupst_sifir_degil_hesaplanamaz():
    r = _vek("2026-02-01 09:00", 1547.40, 0.0, "fazla", 3.0, 3.5, segment=None)
    assert np.isnan(r.kupst) and r.durum == "kupst_hesaplanamaz" and r.p_poz == pytest.approx(-106.00)
    r = _vek("2025-06-01 09:00", 1547.40, 0.0, "fazla", 3.0, 3.5, segment="lisanssiz_iletim")   # 2025 katsayısı doğrulanamadı
    assert np.isnan(r.kupst) and r.durum == "kupst_hesaplanamaz"
    # santral bazında geçersiz kılma (params_json.kupst_n) tabloyu ezer
    r = _vek("2026-02-01 09:00", 1547.40, 0.0, "fazla", 3.0, 3.5, kat=d.Katsayilar(kupst_n=0.10, kupst_tolerans=0.0))
    _yakin(r.kupst, 0.5 * 1547.40 * 0.10)


def test_birim_ve_isaret_kurallari():
    """MWh girdisi; EDT(−) ≥ 0; EDT(+) işaretli; kayıp = poz·(PTF−P(+)) + neg·(P(−)−PTF); toplam = kayıp + KÜPST."""
    i = pd.date_range("2026-06-01 09:00", periods=3, freq="h", tz=IST).tz_convert("UTC")
    s = d.saatlik(pd.Series([10.0, 10.0, 10.0], index=i), pd.Series([8.0, 12.0, 10.0], index=i),
                  pd.Series([2000.0, 2000.0, 2000.0], index=i), pd.Series([2500.0, 1500.0, 2000.0], index=i),
                  yon=pd.Series(["Enerji Açığı", "Enerji Fazlası", "Dengede"], index=i), segment="lisansli_serbest")
    assert (s.edt_neg >= 0).all() and s.edt_poz.iloc[0] == 0 and s.edt_neg.iloc[1] == 0 and s.edt_neg.iloc[2] == 0 and s.edt_poz.iloc[2] == 0
    _yakin(float(s.p_neg.iloc[0]), 2500 * 1.06); _yakin(float(s.p_poz.iloc[1]), 1500 * 0.94)
    _yakin(float(s.dengesizlik_maliyeti.iloc[0]), 2 * (2500 * 1.06 - 2000)); _yakin(float(s.dengesizlik_maliyeti.iloc[1]), 2 * (2000 - 1500 * 0.94))
    assert (s.toplam_maliyet == s.dengesizlik_maliyeti + s.kupst).all() and (s.durum == "ok").all()
    assert set(s.kural_surumu) == {"edt-2026-V150-edta_net+kupst-14029"}


def test_optimal_kantil_tarihli():
    assert d.optimal_teklif_kantili(2650, 2650, 2650, tarih=date(2026, 6, 1)) == pytest.approx(0.5, abs=0.01)
    assert d.optimal_teklif_kantili(2650, 2650, 2650, tarih=date(2025, 6, 1)) == pytest.approx(0.5, abs=0.01)
    assert 0.05 <= d.optimal_teklif_kantili(2650, 3400, 2500, tarih=date(2026, 6, 1)) < 0.5


# ---------------------------------------------------------------- F-08: DSG netleşmesi (T-14) ---------------------------
def test_t14_dsg_esik_ve_kupst_netlesmez():
    """T-14: 26.01.2026 00:00, PTF 2.876 / SMF 3.170, açık; 4 üye F 5,0; A 4,6 / 5,2 / 5,5 / 4,0; eşik %5, PH = max(A, F).
    Tek başına −2.751,48; grup net EDM −0,025 → −84,01; bireysel −2.396,49; DSG −2.480,50; fark 270,98; Σ üye KÜPST 110,95 (netleşmez)."""
    i = _saat("2026-01-26 00:00")
    A = {"u1": 4.6, "u2": 5.2, "u3": 5.5, "u4": 4.0}
    r = d.dsg_saatlik({u: pd.Series([5.0], index=i) for u in A}, {u: pd.Series([a], index=i) for u, a in A.items()},
                      pd.Series([2876.0], index=i), pd.Series([3170.0], index=i), yon="acik", segmentler={u: "lisansli_serbest" for u in A})
    s = r["saatlik"].iloc[0]
    _yakin(s.p_neg, 3360.20); _yakin(s.p_poz, 2789.72); assert s.esik == 0.05
    _yakin(s.edt_tek, -2751.48); _yakin(s.edt_grup, -84.01); _yakin(s.edt_bireysel, -2396.49); _yakin(s.edt_dsg, -2480.50); _yakin(s.netlesme_farki, 270.98)
    _yakin(s.kupst_uye, 110.95)
    k = {u: float(r["uyeler"][u]["kupst"].iloc[0]) for u in A}; _yakin(k["u1"], 0); _yakin(k["u2"], 0); _yakin(k["u3"], 15.85); _yakin(k["u4"], 95.10)
    assert s.durum == "ok" and r["disi"] == []
    # grup sapmasından KÜPST hesaplanmaz: tek sayı 0 değil üyelerin toplamı
    assert s.kupst_uye > 0
    # kayıp tutarlılığı: tek başına kayıp = Σ üye kayıp; DSG kaybı daha küçük, fark = netlesme_farki
    _yakin(float(s.kayip_tek - s.kayip_dsg), 270.98)


def test_dsg_esik_tarihe_gore_ve_dengesizlik_tasimayan_uye_disi():
    i = _saat("2025-06-10 12:00")
    r = d.dsg_saatlik({"a": pd.Series([10.0], index=i), "b": pd.Series([10.0], index=i)}, {"a": pd.Series([9.0], index=i), "b": pd.Series([11.0], index=i)},
                      pd.Series([2000.0], index=i), pd.Series([2500.0], index=i), yon="acik",
                      segmentler={"a": "lisansli_serbest", "b": "lisanssiz_dagitim"})
    assert r["disi"] == ["b"] and r["saatlik"].iloc[0].esik == 0.10 and "%10" in r["esik_kaynak"]
    r27 = d.dsg_saatlik({"a": pd.Series([10.0], index=_saat("2027-02-01 12:00"))}, {"a": pd.Series([9.0], index=_saat("2027-02-01 12:00"))},
                        pd.Series([2000.0], index=_saat("2027-02-01 12:00")), pd.Series([2500.0], index=_saat("2027-02-01 12:00")), yon="acik")
    assert r27["saatlik"].iloc[0].esik == 0.05 and "VARSAYILDI" in r27["esik_kaynak"]
    r_p = d.dsg_saatlik({"a": pd.Series([10.0], index=i)}, {"a": pd.Series([9.0], index=i)}, pd.Series([2000.0], index=i), pd.Series([2500.0], index=i), esik_oran=0.2)
    assert r_p["saatlik"].iloc[0].esik == 0.2 and r_p["esik_kaynak"] == "parametre"


# ---------------------------------------------------------------- v2.510: araştırma (31.10.2026) çelişkileri Ç1–Ç3, Ç5 ----------
def test_c1_afl_zinciri_2015_2022():
    """Ç1: 1.9.2022 öncesi AFL tek değer (4.800) değil; RG kararları + EPİAŞ aylık duyuruları (bulgular/08.md §8.2)."""
    bekl = {date(2022, 9, 1): 4800.0, date(2022, 8, 31): 4000.0, date(2022, 8, 1): 4000.0, date(2022, 7, 1): 3750.0, date(2022, 6, 1): 3200.0,
            date(2022, 5, 20): 2750.0, date(2022, 5, 19): 2500.0, date(2022, 4, 1): 2500.0, date(2022, 3, 31): 1745.0, date(2022, 3, 1): 1745.0,
            date(2022, 1, 1): 1345.0, date(2021, 12, 1): 1217.0, date(2021, 10, 16): 1078.0, date(2021, 10, 15): 718.0, date(2021, 10, 1): 718.0,
            date(2021, 5, 1): 578.0, date(2020, 11, 1): 566.0, date(2020, 10, 7): 563.0, date(2020, 10, 6): 2000.0, date(2020, 4, 1): 2000.0,
            date(2020, 3, 31): 600.0, date(2020, 1, 1): 600.0, date(2019, 12, 31): 2000.0, date(2015, 7, 1): 2000.0}
    for g, v in bekl.items():
        assert kr.afl(g) == v, (g, kr.afl(g), v)
    assert kr.afl(date(2023, 1, 1)) == 4200.0 and kr.afl(date(2026, 4, 4)) == 4500.0      # mevcut zincir bozulmadı
    assert "doğrulanmadı" in kr.afl_dayanak(date(2018, 1, 1)) and "11083" in kr.afl_dayanak(date(2022, 8, 15))


def test_c2_lisanssiz_net_sapma_yok():
    """Ç2: Karar 14907 Md.1(3) — lisanssızlarda hesap yalnız üretim miktarıyla (UEÇM düşülmez)."""
    g = date(2026, 11, 5)
    assert kr.kural(g, "lisansli_serbest").kupst.net_sapma is True
    assert kr.kural(g, "lisanssiz_iletim").kupst.net_sapma is False
    assert kr.kural(g, "lisanssiz_dagitim", portfoy=True).kupst.net_sapma is False
    i = _saat("2026-11-05 08:00")
    r = _vek("2026-11-05 08:00", 3400.00, 3400.00, "fazla", 10, 12, segment="lisanssiz_iletim", uecm_mwh=pd.Series([0.3], index=i))
    _yakin(r.kupst, 0.0)          # |12 − 10| = 2 ≤ 0,20·10 → KÜPSM 0 (brüt); net tanımla |11,7 − 10| = 1,7 de 0 verirdi — ayırt edici örnek:
    r = _vek("2026-11-05 08:00", 3400.00, 3400.00, "fazla", 10, 12.5, segment="lisanssiz_iletim", uecm_mwh=pd.Series([0.3], index=i))
    _yakin(r.kupst, 0.5 * 3400.0 * 0.02)   # brüt: |12,5 − 10| − 2 = 0,5 MWh; net olsaydı |12,2 − 10| − 2 = 0,2


def test_c5_kupst_7524_etiketi():
    """Ç5: 1.8.2020 öncesi Karar 7524 (m 0,1 / n 0,03; ilk 3 ay 0,015 penceresi tarihi bulunamadı)."""
    assert kr.kural(date(2020, 7, 31), "lisansli_serbest").kupst.surum == "kupst-7524"
    assert kr.kural(date(2020, 8, 1), "lisansli_serbest").kupst.surum == "kupst-9422"
    assert kr.kural(date(2020, 7, 31), "lisansli_serbest").kupst.m == 0.10


def test_c3_luy_istisnasi():
    """Ç3: Karar 14907 Md.5 — LÜY m.5(1)(ç),(d),(e) kapsamındaki iletime bağlı lisanssız tesislere karar uygulanmaz (1.11.2026'dan)."""
    g = date(2026, 11, 5)
    k = kr.kural(g, "lisanssiz_iletim", luy_istisna=True).kupst
    assert k.surum == "kupst-14907-luy-istisna" and k.m == 0.0 and k.n == 0.0 and "Md.5" in k.dayanak
    assert kr.kural(date(2026, 10, 5), "lisanssiz_iletim", luy_istisna=True).kupst.surum == "kupst-14029-iletim"   # 14907 öncesi etkisiz
    assert kr.kural(g, "lisansli_serbest", luy_istisna=True).kupst.surum == "kupst-14907"                       # yalnız iletim lisanssız
    i = _saat("2026-11-05 08:00")
    s = d.saatlik(pd.Series([10.0], index=i), pd.Series([13.0], index=i), pd.Series([3400.0], index=i), pd.Series([3400.0], index=i),
                  yon="fazla", segment="lisanssiz_iletim", luy_istisna=True)
    assert float(s.kupst.iloc[0]) == 0.0 and s.durum.iloc[0] == "ok"
    c = kr.parametre_cercevesi(i, "lisanssiz_iletim", luy_istisna=True)
    assert float(c["m"].iloc[0]) == 0.0 and float(c["n"].iloc[0]) == 0.0


def test_dsg_2027_etiketi():
    _, day = kr.dsg_esigi(date(2027, 3, 1))
    assert "13869" in day and "1.12.2026" in day and "VARSAYILDI" in day
    assert "1.1.2025" in kr.dsg_esigi(date(2025, 6, 1))[1]


def test_gecici_m39_notu():
    """v2.513 (bulgular/10.md (e)): dağıtım/GTŞ DSG'lerinde üye eşiği 1.1.2027'ye kadar %100 — ekran notu yalnız 2027 öncesi."""
    from datetime import date
    from pvquant.ext.turkiye import kurallar as kr
    assert kr.gecici_m39_notu(date(2026, 12, 31)) == kr.GECICI_M39_NOT and "%100" in kr.GECICI_M39_NOT and "32755" in kr.GECICI_M39_NOT
    assert kr.gecici_m39_notu(date(2027, 1, 1)) is None
    assert "Geçici m.39" in kr.GECICI_M39_DIPNOT and "%100" in kr.GECICI_M39_DIPNOT
