"""v2.590 (Faz 3 F3-C, saf) — portföy sapma ve risk: üç kavram ayrı (program sapması / tahmin hatası / fizik sapması), eksik saat 0 sayılmaz,
santral katkıları Σ = portföy, karşıt sapma ofseti (fiziksel netleşme), farklı ölçüm zaman damgaları, maruziyet saatleri sıralaması (gösterge),
kapsama güvenilirliği, gelecek risk etiketleri."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pvquant.ext.platform import portfoy_sapma as ps

IDX = pd.date_range("2026-09-10 03:00", periods=12, freq="h", tz="UTC")   # 06–17 TSİ


def _santral(prog, ger, tah=None, fiz=None, idx=IDX):
    return pd.DataFrame({"program_mwh": prog, "gercek_mwh": ger, "tahmin_mwh": tah if tah is not None else prog, "fizik_mwh": fiz if fiz is not None else prog}, index=idx)


def test_uc_kavram_ayri_ve_eksik_saat_sifir_sayilmaz():
    a = _santral([1.0] * 12, [1.2] * 12, tah=[1.1] * 12, fiz=[1.3] * 12)
    b = _santral([0.5] * 12, [0.4] * 11 + [np.nan], tah=[0.5] * 12, fiz=[0.5] * 12)   # son saat ölçüm yok
    p, st = ps.saatlik({"A": a, "B": b})
    assert len(p) == 12 and int(p["olcum_tam"].sum()) == 11 and int(p["sapma_tam"].sum()) == 11 and int(p["hesap_disi_n"].sum()) == 1
    # son saat: B ölçümsüz → portföy sapması yalnız A (0 sayılmadı), gerçek toplam yalnız A
    assert p["program_sapma_mwh"].iloc[-1] == pytest.approx(0.2) and p["gercek_mwh"].iloc[-1] == pytest.approx(1.2) and p["program_mwh"].iloc[-1] == pytest.approx(1.5)
    o = ps.ozet(p, st, {"A": 1000, "B": 500})
    assert o["program_sapma"]["mwh"] == pytest.approx(0.2 * 12 - 0.1 * 11) and o["program_sapma"]["tam_saat"] == 11 and o["gerceklesen"]["eksik_saat"] == 1
    assert o["tahmin_hata"]["mwh"] == pytest.approx((1.1 - 1.2) * 12 + (0.5 - 0.4) * 11) and o["fizik_sapma"]["mwh"] == pytest.approx((1.2 - 1.3) * 12 + (0.4 - 0.5) * 11)
    assert o["program_sapma"]["etiket"].startswith("gerçekleşen − program") and o["tahmin_hata"]["etiket"].startswith("tahmin − gerçekleşen")
    assert o["program_sapma"]["pct"] == pytest.approx(100 * (0.2 * 12 - 0.1 * 11) / (12 + 5.5), abs=0.01)


def test_katkilar_toplami_portfoy_ve_karsit_sapma_ofseti():
    a = _santral([1.0] * 12, [1.5] * 12)            # +0,5 × 12 = +6
    b = _santral([1.0] * 12, [0.7] * 12)            # −0,3 × 12 = −3,6
    c = _santral([0.8] * 12, [0.8] * 12)            # dengede
    p, st = ps.saatlik({"A": a, "B": b, "C": c})
    k = ps.katkilar(p, st, {"A": 1, "B": 1, "C": 1})
    assert k["toplam_mwh"] == pytest.approx(2.4) and sum(r["mwh"] for r in k["satirlar"]) == pytest.approx(k["toplam_mwh"])
    assert k["mutlak_toplam_mwh"] == pytest.approx(9.6) and k["netlesen_mwh"] == pytest.approx(7.2) and k["netlesme_orani_pct"] == 75.0
    assert k["satirlar"][0]["santral"] == "A" and k["fazla"] == ["A"] and k["eksik"] == ["B"] and "kısmen dengeliyor" in k["not"] and "7,2 MWh" in k["not"]
    assert k["satirlar"][2]["yon"] == "dengede" and k["satirlar"][0]["mutlak_pay_pct"] == 62.5
    # karşıt sapma yoksa not yok
    p2, st2 = ps.saatlik({"A": a, "C": c}); k2 = ps.katkilar(p2, st2)
    assert k2["not"] is None and k2["netlesen_mwh"] == 0.0


def test_farkli_olcum_zaman_damgalari_birlik_uzerinde():
    a = _santral([1.0] * 12, [1.0] * 12)
    idx_b = IDX[2:] .append(pd.date_range(IDX[-1] + pd.Timedelta(hours=1), periods=2, freq="h"))   # 2 saat geç başlar, 2 saat uzar
    b = _santral([0.5] * 12, [0.6] * 12, idx=idx_b)
    p, st = ps.saatlik({"A": a, "B": b})
    assert len(p) == 14 and int(p["sapma_tam"].sum()) == 10 and p["program_sapma_n"].iloc[0] == 1 and p["program_sapma_n"].iloc[-1] == 1
    assert p["program_sapma_mwh"].iloc[-1] == pytest.approx(0.1) and np.isnan(st["A"]["gercek_mwh"].iloc[-1])
    kp = ps.kapsama(p)
    assert kp["beklenen_saat"] == 14 and kp["sapma_tam_saat"] == 10 and kp["guvenilirlik"] == "kismi" and kp["hesap_disi_santral_saat"] == 4
    assert ps.kapsama(p.iloc[2:12])["guvenilirlik"] == "tam" and ps.kapsama(p.iloc[:0])["guvenilirlik"] == "yok"
    assert ps.kapsama(pd.concat([p.iloc[:2]] * 5))["guvenilirlik"] == "yetersiz"


def test_maruziyet_saatleri_siralama_ve_fiyat_kaynagi():
    a = _santral([1.0] * 12, [1.0 + 0.1 * i for i in range(12)])   # sapma artan
    b = _santral([1.0] * 12, [1.0 - 0.05 * i for i in range(12)])
    p, st = ps.saatlik({"A": a, "B": b})
    fiyat = pd.DataFrame({"ptf": [2000.0] * 11 + [100.0], "kaynak": ["epias"] * 6 + ["senaryo"] * 6}, index=IDX)
    m = ps.maruziyet_saatleri(p, st, fiyat, n=3)
    assert m["olcut"].startswith("|program sapması| × PTF") and len(m["saatler"]) == 3
    assert m["saatler"][0]["ts"] == IDX[10].isoformat(timespec="minutes") and m["saatler"][0]["baskin_santral"] == "A" and m["saatler"][0]["fiyat_kaynak"] == "senaryo"
    assert m["saatler"][0]["gosterge"] == pytest.approx(abs(0.5 * 10) * 2000.0 / 10 * 10 / 10 * 10 / 10, rel=0.3)   # ≈ |sapma| × PTF (0,5 × 2000)
    m2 = ps.maruziyet_saatleri(p, st, None, n=2)
    assert m2["olcut"] == "|program sapması|" and m2["saatler"][0]["ts"] == IDX[11].isoformat(timespec="minutes") and m2["saatler"][0]["ptf"] is None
    assert ps.maruziyet_saatleri(p.assign(program_sapma_mwh=np.nan), st, fiyat)["saatler"] == []


def test_korelasyon_sapma_ve_gelecek_risk():
    rng = np.random.default_rng(0)
    idx = pd.date_range("2026-08-01 03:00", periods=24 * 20, freq="h", tz="UTC")
    z = rng.standard_normal((len(idx), 2)) @ np.linalg.cholesky(np.array([[1, 0.6], [0.6, 1]])).T
    gun = (idx.hour >= 3) & (idx.hour <= 14)
    a = _santral(np.where(gun, 1.0, 0), np.where(gun, 1.0 + 0.1 * z[:, 0], np.nan), idx=idx); b = _santral(np.where(gun, 0.8, 0), np.where(gun, 0.8 + 0.1 * z[:, 1], np.nan), idx=idx)
    p, st = ps.saatlik({"A": a, "B": b})
    ko = ps.korelasyon_sapma(st)
    assert ko["durum"] == "yeterli" and 0.4 < ko["rho"]["A"]["B"] < 0.8
    # gelecek risk: bant içinde/dışında saatler, etiketler
    t = pd.DataFrame({"p50": [1000.0] * 6, "p10": [800.0] * 6, "p90": [1200.0] * 6}, index=IDX[:6])
    prog = pd.Series([1.0, 0.9, 1.3, 0.7, 1.1, 1.0], index=IDX[:6]); kay = pd.Series(["bildirilen"] * 6, index=IDX[:6])
    r = ps.gelecek_risk(t, prog, "dogrulandi", kay, 1500.0)
    assert r["etiket"] == "dogrulanmis" and r["riskli_saat"] == 2 and r["saatler"][0]["program_mwh"] == 1.3 and r["beklenen_sapma_mwh"] == pytest.approx(6.0 - 6.0)
    assert r["aralik_mwh"]["p10"] == pytest.approx(4.8 - 6.0) and r["aralik_mwh"]["p90"] == pytest.approx(7.2 - 6.0)
    r2 = ps.gelecek_risk(t, prog, "dogrulandi", kay.replace("bildirilen", "oneri"), None)
    assert r2["etiket"] == "tahmini" and r2["program_bildirilen"] is False
    assert ps.gelecek_risk(t, prog, "dogrulanmadi", kay)["etiket"] == "tahmini" and ps.gelecek_risk(t, None, "dogrulandi")["etiket"] == "eksik"
    assert ps.gelecek_risk(pd.DataFrame(), prog, "dogrulandi")["etiket"] == "eksik" and r["etiket_ad"] == "Doğrulanmış risk"
