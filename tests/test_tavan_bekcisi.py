"""Faz 1 G2-A1 (22.11.2026) — AC tavan bekçisi: sapma katmanı sonrası hiçbir kantil fiziksel tavanı aşamaz; sıralama korunur;
tavan yok/geçersiz → değişmez; gece/bant NaN korunur; Mod C konformal aktifken de tavan geçerli; tavan altı değerler birebir aynı."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pvquant.services import forecast_service as fs
from pvquant.services import konformal_service as kf
from pvquant.services import sapma_service as sp
from pvquant.services import ufuk_service as uf

TAVAN = 200_000.0
IDX = pd.date_range("2026-11-22 03:00", periods=24, freq="1h", tz="UTC")
PLATO = [0.0] * 4 + [40_000, 120_000, 180_000, 200_000, 200_000, 200_000, 200_000, 190_000, 120_000, 40_000] + [0.0] * 10


def _plato() -> pd.DataFrame:
    p50 = pd.Series(PLATO, index=IDX, dtype=float)
    g = p50 > 0
    return pd.DataFrame({"p50_kw": p50, "physics_kw": p50, "p10_kw": (p50 * 0.8).where(g), "p25_kw": (p50 * 0.9).where(g),
                         "p75_kw": p50.where(g), "p90_kw": p50.where(g)}, index=IDX)


def _sirali(h: pd.DataFrame) -> bool:
    d = h.dropna(subset=["p10_kw", "p90_kw"])
    return bool(((d.p10_kw <= d.p25_kw) & (d.p25_kw <= d.p50_kw) & (d.p50_kw <= d.p75_kw) & (d.p75_kw <= d.p90_kw)).all())


def _sapma_12() -> dict:
    return {"aktif": True, "oran_saat": {str(s): 1.2 for s in range(24)}}


def test_1_plato_ve_oran_12_tavanda_kirpilir_siralama_korunur():
    h = uf.uygula_df(_plato(), {"sigma_kw": {"0": 15_000.0}, "kova_saat": 24}, IDX[0], TAVAN)
    h = sp.uygula_df(h, _sapma_12(), "Europe/Istanbul")
    assert h.p50_kw.max() == 240_000.0 and h.p90_kw.max() == 240_000.0   # kusurun yeniden üretimi (bekçi öncesi)
    b = fs.tavan_bekcisi(h, TAVAN)
    for k in fs.TAVAN_KANTILLERI:
        assert b[k].max() <= TAVAN
    assert int((b.p50_kw > TAVAN).sum()) == 0 and int((b.p90_kw > TAVAN).sum()) == 0 and _sirali(b)
    # tavan altı değerler birebir aynı (altın testler değişmez)
    alt = h.p50_kw <= TAVAN
    assert np.allclose(b.p50_kw[alt], h.p50_kw[alt]) and np.allclose(b.p10_kw[alt & h.p10_kw.notna()], h.p10_kw[alt & h.p10_kw.notna()])


def test_2_tavan_yok_veya_gecersiz_degismez():
    h = sp.uygula_df(_plato(), _sapma_12(), "Europe/Istanbul")
    for t in (None, 0, -5.0, float("nan"), float("inf"), "abc"):
        assert fs.ac_tavani({"ac_limit_kw": t, "capacity_kwp": 260_000}) is None      # AC sınırı bilinmiyor → bekçi çalışmaz
        assert fs.tavan_degeri({"ac_limit_kw": t, "capacity_kwp": t}) is None
        for tv in (t, fs.ac_tavani({"ac_limit_kw": t})):
            b = fs.tavan_bekcisi(h, tv)
            pd.testing.assert_frame_equal(b, h)   # değişmez, istisna yok
    # QA İ-1: kurulu DC gücü AC sınırı değildir — ac_limit yokken bekçi kWp'de KIRPMAZ (fizik P50 kWp'yi aşabilir)
    assert fs.ac_tavani({"ac_limit_kw": None, "capacity_kwp": 260_000}) is None
    assert fs.tavan_degeri({"ac_limit_kw": None, "capacity_kwp": 260_000}) == 260_000.0   # bant tavanı (ufuk σ) eski davranış
    assert fs.ac_tavani({"ac_limit_kw": "200000", "capacity_kwp": 260_000}) == 200_000.0   # metin sayı


def test_3_gece_ve_bantsiz_nan_korunur_ic_bant_dokunulmaz():
    h = _plato()
    h["p25_kw"] = np.nan
    h["p75_kw"] = np.nan   # Mod A, GEFS yok: iç bant yok
    h = sp.uygula_df(h, _sapma_12(), "Europe/Istanbul")
    b = fs.tavan_bekcisi(h, TAVAN)
    assert b.p25_kw.isna().all() and b.p75_kw.isna().all()
    gece = b.physics_kw == 0
    assert (b.loc[gece, "p50_kw"] == 0).all() and b.loc[gece, "p10_kw"].isna().all() and b.loc[gece, "p90_kw"].isna().all()
    assert len(b) == len(h) and list(b.columns) == list(h.columns)


def test_4_konformal_aktif_mod_c_ile_p90_tavani_asamaz():
    h = sp.uygula_df(uf.uygula_df(_plato(), {"sigma_kw": {"0": 15_000.0}, "kova_saat": 24}, IDX[0], TAVAN), _sapma_12(), "Europe/Istanbul")
    # bekçi OLMADAN konformal (q̂=0) p50 240.000 → max(yeni90, p50) p90'ı yeniden tavan üstüne taşır (kusur)
    k0 = kf.uygula_df(h.copy(), {"q_hat": {"_genel": 0.0}}, TAVAN, run_at=IDX[0])
    assert k0.p90_kw.max() > TAVAN and k0.p50_kw.max() > TAVAN
    # bekçi İLE: zincir sapma → bekçi → konformal → hiçbir kantil tavanı aşmaz, sıralama korunur, ham kopyalar kırpık
    k1 = kf.uygula_df(fs.tavan_bekcisi(h, TAVAN), {"q_hat": {"_genel": 5_000.0}}, TAVAN, run_at=IDX[0])
    assert k1.p90_kw.max() <= TAVAN and k1.p50_kw.max() <= TAVAN and k1.p10_ham_kw.max() <= TAVAN and _sirali(k1)


def test_5_tahmin_uret_zinciri_oran_12_ile_tavan_altinda_ve_altin_fizik_degismez(monkeypatch):
    from test_altin_cekirdek import (  # altın kurgu: capacity 1000 kWp, ac_limit 900 kW
        PLANT,
        _girdi,
        _meteo,
    )
    simdi = pd.Timestamp("2026-06-21", tz="UTC")
    g = _girdi()
    g.sapma_ayar = {"aktif": False, "neden": "test"}
    ref = fs.tahmin_uret(PLANT, _meteo(carpan=1.6), g, simdi=simdi).h          # sapma kapalı: fizik 900 kW'ta plato
    assert ref.p50_kw.max() <= 900.0
    g2 = _girdi()
    g2.sapma_ayar = {"aktif": True, "oran_saat": {str(s): 1.2 for s in range(24)}}
    s2 = fs.tahmin_uret(PLANT, _meteo(carpan=1.6), g2, simdi=simdi)
    assert s2.h.p50_kw.max() <= 900.0 and _sirali(s2.h)   # bekçi: aşım yok
    p90 = s2.h.p90_kw.dropna()
    assert p90.empty or p90.max() <= 900.0   # altın kurguda GEFS üyesi yoksa bant NaN kalır (uydurulmaz)
    # tavan altı saatlerde sapma etkisi aynen (bekçi yalnız aşan saatlere dokunur): oran 1,2 → p50 = 1,2 × fizik (fizik < 750 iken)
    dusuk = (ref.p50_kw > 0) & (ref.p50_kw * 1.2 < 900.0)
    assert np.allclose(s2.h.p50_kw[dusuk], ref.p50_kw[dusuk] * 1.2)
    # QA İ-1/İ-2: AC sınırı yok (yalnız kWp) → bekçi dokunmaz: sapma 1,2 ile P50 kWp'yi aşabilir (HEAD davranışı korunur, sanal santraller)
    p_ac_yok = {**PLANT, "ac_limit_kw": None}
    s3 = fs.tahmin_uret(p_ac_yok, _meteo(carpan=1.6), g2, simdi=simdi)
    assert s3.h.p50_kw.max() > 1000.0 and _sirali(s3.h)   # kırpılmadı (fizik ~1.089 kW × 1,2); sıralama yine korunur
    s4 = fs.tahmin_uret(p_ac_yok, _meteo(carpan=1.6), g, simdi=simdi)   # sapma pasif + AC yok: HEAD ile birebir (kWp'de kırpma YOK)
    assert s4.h.p50_kw.max() > 1000.0
