"""v2.596 (Faz 3 F3-I, Tur 1 — hesap): DSG üye eşiği geçişi 2025 %10 → 2026 %5 (İstanbul gün sınırı) F3-D zincirinde; yirmi üyeli sözleşmesel dağılım (Σ pay = grup,
sabit pay 20 oran); güçlü / zayıf korelasyonun portföy bant genişliğine etkisi (ρ↑ → naife yaklaşır) ve «aynı meteoroloji bölgesi» göstergesi; gün içi düzeltme penceresi."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pvquant.ext.platform import dagitim as dg
from pvquant.ext.tahmin import portfoy_belirsizlik as pb
from pvquant.ext.turkiye import dengesizlik as d
from pvquant.services import portfoy_revizyon_service as rv


def test_dsg_esik_gecisi_2025_2026_istanbul_gun_sinirinda():
    idx = pd.date_range("2025-12-30 21:00", "2026-01-02 21:00", freq="h", tz="UTC", inclusive="left")   # 31.12.2025 – 2.1.2026 TSİ
    rng = np.random.default_rng(2)
    prog = {a: pd.Series(1.0, index=idx) for a in ("A", "B")}
    ger = {"A": pd.Series(1.0 + rng.normal(0, 0.08, len(idx)), index=idx), "B": pd.Series(1.0 - rng.normal(0, 0.08, len(idx)), index=idx)}
    ptf = pd.Series(2000.0, index=idx); smf = pd.Series(2100.0, index=idx)
    r = d.dsg_saatlik(prog, ger, ptf, smf, yon="dengede", segmentler={"A": "lisansli_serbest", "B": "lisansli_serbest"})
    sa = r["saatlik"]
    assert sa.loc[pd.Timestamp("2025-12-31 20:00", tz="UTC"), "esik"] == pytest.approx(0.10) and sa.loc[pd.Timestamp("2025-12-31 21:00", tz="UTC"), "esik"] == pytest.approx(0.05)
    assert sorted(sa["esik"].unique()) == [0.05, 0.10]
    assert abs(sum(v["edt_dsg"].sum() for v in r["uyeler"].values()) - sa["edt_dsg"].sum()) < 1e-6   # Σ üye = grup, kural değişse de


def test_yirmi_uyeli_dagilim_sapma_ve_sabit_pay():
    rng = np.random.default_rng(4)
    uy = {f"S{i:02d}": {"edt_tek_tl": float(rng.normal(-500, 300)), "edt_bireysel_tl": float(rng.normal(-100, 50)), "kupst_tl": -10.0 * i, "grup_payi_mwh": float(rng.uniform(0.5, 8)),
                        "uretim_mwh": float(rng.uniform(20, 400)), "sapma_mwh": float(rng.uniform(1, 10))} for i in range(20)}
    grup = -12345.6
    for yontem in ("sapma", "esit", "uretim"):
        r = dg.dagit(grup, uy, yontem)
        assert r["kontrol"] is True and len(r["satirlar"]) == 20 and sum(s["grup_payi_tl"] for s in r["satirlar"]) == pytest.approx(grup, abs=0.05) and r["etiket"] == "Varsayımsal maliyet dağılımı"
    paylar = rng.dirichlet(np.ones(20)); paylar = {a: float(p) for a, p in zip(uy, paylar, strict=True)}
    r = dg.dagit(grup, uy, "sabit_pay", {"paylar": paylar}, {"dogrulama": "dogrulandi", "belge_adi": "dsg.pdf"})
    assert r["kontrol"] is True and r["etiket"] == "Sözleşmeye dayalı dağılım" and all(s["kupst_dahil_degil"] for s in r["satirlar"])
    assert abs(sum(s["pay_pct"] for s in r["satirlar"]) - 100.0) < 0.5 and sum(s["edt_bireysel_tl"] for s in r["satirlar"]) == pytest.approx(sum(u["edt_bireysel_tl"] for u in uy.values()), abs=0.1)


def test_guclu_zayif_korelasyon_bant_genisligi_ve_bolge():
    idx = pd.date_range("2026-07-01", periods=24, freq="h", tz="Europe/Istanbul").tz_convert("UTC")
    h = idx.tz_convert("Europe/Istanbul").hour.values
    p50 = 800.0 * np.clip(np.sin((h - 6) / 12 * np.pi), 0, None)
    tah = {a: pd.DataFrame({"p50": p50, "p10": p50 * 0.8, "p90": p50 * 1.2}, index=idx) for a in ("A", "B", "C", "D", "E")}
    hz = pb.hizala(tah); kaps = dict.fromkeys(tah, 1000.0)
    def rho(r):
        R = np.full((5, 5), r); np.fill_diagonal(R, 1.0); return pd.DataFrame(R, index=list(tah), columns=list(tah))
    g = pb.saatlik_bant(hz, rho(0.9), kaps); z = pb.saatlik_bant(hz, rho(0.2), kaps); n = pb.saatlik_bant(hz, rho(-0.2), kaps)
    m = g["p50"] > 0
    assert (g["sigma_ust"][m] > z["sigma_ust"][m]).all() and (z["sigma_ust"][m] > n["sigma_ust"][m]).all()      # ρ↑ → bant genişler
    assert ((g["p90"] - g["p10"])[m] <= (g["p90_naif"] - g["p10_naif"])[m] + 1e-9).all()                             # naif en geniş
    assert np.allclose(g["sigma_ust"][m] / (g["p90_naif"] - g["p50"])[m], np.sqrt((5 + 20 * 0.9) / 25))               # kapalı biçim: √(Σρ)/n
    b = pb.bolge_gostergesi({"A": (37.0, 32.0), "B": (37.1, 32.1), "C": (37.2, 32.0), "D": (39.9, 32.9), "E": (41.0, 29.0)}, esik_km=50)
    assert b["bolge_sayisi"] == 3 and sorted(b["bolgeler"], key=len)[-1] == ["A", "B", "C"]


def test_gun_ici_duzeltme_penceresi():
    t = pd.Timestamp("2026-09-11 14:20", tz="Europe/Istanbul")
    g = rv.gun_ici_penceresi(t)
    assert g["acik"] is True and g["teslimat"].startswith("2026-09-11T15:00") and g["kgup_revizyon_son"].startswith("2026-09-11T14:30") and g["dakika_kaldi"] == 10
    g2 = rv.gun_ici_penceresi(pd.Timestamp("2026-09-11 14:40", tz="Europe/Istanbul"))
    assert g2["acik"] is False and g2["sonraki_revizyon_son"].startswith("2026-09-11T15:30") and g2["dakika_kaldi"] == 50
