# -*- coding: utf-8 -*-
"""Faz 0 P0-04, karar C4-1 (21.11.2026): kronolojik holdout ÖLÇÜMÜ — üretim kalibrasyonundan bağımsız, yalnız quality_json'a yazılır."""
from __future__ import annotations

import time
from types import SimpleNamespace

from pvquant.pipeline.calibration import calibrate_from_scada
from pvquant.pipeline.forecast import forecast_7day
from pvquant.services import calib_service as cs
from test_calibration_multi_resolution import _make_synthetic_meteo, _make_synthetic_plant, _make_synthetic_scada


def _veri():
    meteo = _make_synthetic_meteo("1h"); plant = _make_synthetic_plant()
    fc = forecast_7day(meteo, plant).hourly["p_ac_kw"]
    return meteo, plant, _make_synthetic_scada(fc, scale=0.88, noise_std=0.06)


def test_holdout_hesaplanir_ve_uretim_uydurmasi_degismez():
    meteo, plant, scada = _veri()
    pw_once = scada.power_kw.copy(); plant_once = plant
    cr1 = calibrate_from_scada(scada=scada, historical_meteo=meteo, plant=plant, fit_bg=True, fit_eta_bos=True, clean_outliers=False)
    t0 = time.perf_counter()
    h = cs._kronolojik_holdout(scada, meteo, plant, temizle=False, asgari_saat=48)   # 30 günlük sentetik pencerede son %20 ≈ 66 gündüz saati
    sure = time.perf_counter() - t0
    cr2 = calibrate_from_scada(scada=scada, historical_meteo=meteo, plant=plant, fit_bg=True, fit_eta_bos=True, clean_outliers=False)
    # bağımsızlık: girdiler ve üretim uydurması birebir aynı
    assert scada.power_kw.equals(pw_once) and plant == plant_once
    assert cr1.eta_bos == cr2.eta_bos and cr1.bg == cr2.bg and cr1.n_valid_hours == cr2.n_valid_hours
    assert cr1.validation_after.mape_pct == cr2.validation_after.mape_pct
    # holdout sözlüğü
    assert h["holdout_not"] is None and h["mape_holdout_pct"] is not None and h["mape_holdout_pct"] >= 0 and h["holdout_saat"] >= 48
    # varsayılan eşik (72 geçerli saat) bu kısa pencerede sayı uydurmaz
    h72 = cs._kronolojik_holdout(scada, meteo, plant, temizle=False)
    assert h72["mape_holdout_pct"] is None and "geçerli saat yetersiz" in h72["holdout_not"]
    assert h["holdout_bas"] > "2024-06-01" and h["holdout_bit"] > h["holdout_bas"] and h["holdout_egitim_saat"] > h["holdout_saat"]
    assert h["holdout_pay"] == 0.2 and h["holdout_sure_sn"] is not None
    # holdout dilimi son %20: eğitim saatleri kesimden önce
    import pandas as pd
    pw = scada.power_kw.dropna().sort_index(); kesim = pd.Timestamp(h["holdout_bas"])
    assert kesim == pw.index[int(len(pw) * 0.8)]
    # performans: holdout = bir ek uydurma + bir tahmin; tam kalibrasyonun makul katı (ölçülür, raporlanır)
    t1 = time.perf_counter(); calibrate_from_scada(scada=scada, historical_meteo=meteo, plant=plant, fit_bg=True, fit_eta_bos=True, clean_outliers=False); tam = time.perf_counter() - t1
    print(f"\nPERFORMANS holdout {sure:.2f} s / tam kalibrasyon {tam:.2f} s (oran {sure / max(tam, 1e-6):.2f})")
    assert sure < 5 * max(tam, 0.2)


def test_holdout_temizlik_bosluk_yaratirsa_not_doner_istisna_firlatmaz():
    """Üretim bayrağı (temizle=True) sentetik seride satır düşürüp zaman adımı denetimine takılır → holdout None + not; kalibrasyon düşmez."""
    meteo, plant, scada = _veri()
    h = cs._kronolojik_holdout(scada, meteo, plant, temizle=True)
    assert h["mape_holdout_pct"] is None and "uydurulamadı" in h["holdout_not"]


def test_holdout_yetersiz_veride_sayi_uydurmaz():
    meteo, plant, scada = _veri()
    kucuk = scada.power_kw.iloc[:100]
    from pvquant.io.scada import SCADAData
    s2 = SCADAData(power_kw=kucuk, energy_kwh=None, poa_irradiance=None, temp_ambient=None, temp_module=None, wind_speed=None, plant_name="k", timestep_minutes=60)
    h = cs._kronolojik_holdout(s2, meteo, plant)
    assert h["mape_holdout_pct"] is None and h["holdout_saat"] is None and "yetersiz" in h["holdout_not"]


def test_ozet_holdout_alanlari_ve_eski_kayit(monkeypatch):
    q_yeni = {"mape_pct": 4.1, "mape_before_pct": 9.0, "degerlendirme": "orneklem_ici+holdout", "mape_holdout_pct": 11.7, "wmape_holdout_pct": 9.9,
              "holdout_saat": 140, "holdout_bas": "2024-06-25T00:00:00", "holdout_bit": "2024-06-30T23:00:00", "holdout_not": None}
    satir = SimpleNamespace(mode="B", quality_json=q_yeni, params_json={"eta_bos": 0.9, "bg": 0.3}, n_valid_hours=700, created_at=None)
    monkeypatch.setattr(cs, "aktif_kalibrasyon", lambda t, p: satir)
    monkeypatch.setattr(cs, "fizik_terimleri", lambda t, p: {})
    o = cs.kalibrasyon_ozeti("t", "p")
    assert o["mape_holdout"] == 11.7 and o["holdout_saat"] == 140 and o["degerlendirme"] == "orneklem_ici+holdout" and o["mape_sonra"] == 4.1
    satir.quality_json = {"mape_pct": 4.1}   # eski kayıt: alanlar yok → None, UI «—»
    o2 = cs.kalibrasyon_ozeti("t", "p")
    assert o2["mape_holdout"] is None and o2["holdout_not"] is None and o2["degerlendirme"] is None
    src = open(cs.__file__, encoding="utf-8").read()
    i_cr = src.index("    cr = calibrate_from_scada(\n        scada=scada, historical_meteo=meteo, plant=_plant_spec(plant),")
    i_h = src.index("holdout = _kronolojik_holdout(scada, meteo, _plant_spec(plant))")
    assert i_cr < i_h and "except Exception as e:   # ölçüm yardımcı; kalibrasyonu düşürmez" in src   # üretim uydurması önce, holdout sonra ve korumalı


def test_holdout_gunduz_nan_bosluklu_seride_sayi_uretir():
    """QA C4-6: üretim ızgarası gündüz boşluklarını NaN olarak tutar ve kalibrasyon geçer; holdout eğitim dilimi de NaN'lı seriden kesilmeli
    (dropna ızgarayı delip zaman adımı denetimini düşürüyordu)."""
    import numpy as np
    meteo, plant, scada = _veri()
    pw = scada.power_kw.copy()
    rng = np.random.default_rng(7); gunduz = pw.index[pw > 1.0]
    delik = rng.choice(len(gunduz), size=int(len(gunduz) * 0.12), replace=False)
    pw.loc[gunduz[delik]] = np.nan
    from pvquant.io.scada import SCADAData
    s2 = SCADAData(power_kw=pw, energy_kwh=None, poa_irradiance=None, temp_ambient=None, temp_module=None, wind_speed=None, plant_name="nanli", timestep_minutes=60)
    cr = calibrate_from_scada(scada=s2, historical_meteo=meteo, plant=plant, fit_bg=True, fit_eta_bos=True, clean_outliers=False)   # üretim geçer
    h = cs._kronolojik_holdout(s2, meteo, plant, temizle=False, asgari_saat=48)
    assert cr.n_valid_hours > 0 and h["holdout_not"] is None and h["mape_holdout_pct"] is not None and h["holdout_saat"] >= 48
