"""Tur 5 — hibrit UI entegrasyonu kabul testleri (Streamlit'siz).

Streamlit'i test etmek yerine, UI'nın çağırdığı köprü katmanı test edilir:
run_hybrid_training / session_ozeti / apply_hybrid_session / adaptör.
Ağ YOK: meteo sentetik ve HistoricalData'ya enjekte edildiği için
HybridResidualModel kendi API çağrısını atlar.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pvquant.pipeline.hybrid_ui import (
    HybridUIResult, hybrid_forecast_hourly, run_hybrid_training, session_ozeti,
)
from pvquant.reporting import apply_hybrid_session, from_results


LAT, LON, KWP = 37.87, 32.49, 4514.0
PLANT_CTX = {"capacity_kwp": KWP, "latitude": LAT, "longitude": LON,
             "timezone": "Europe/Istanbul", "tilt": 20, "azimuth": 180}


# ------------------------------------------------------------------ fixtures
def _sentetik_scada_ve_meteo(saat=1440):
    """60 günlük saha verisi: fizik + sistematik hata (LGBM'in öğreneceği)."""
    import pvlib
    from types import SimpleNamespace

    idx = pd.date_range("2025-04-01", periods=saat, freq="1h", tz="UTC")
    yerel = idx.tz_convert("Europe/Istanbul")
    cs = pvlib.location.Location(LAT, LON).get_clearsky(idx)["ghi"].values
    ghi = cs * 0.88
    # gerçek üretim: kaba fizik + öğrenilebilir sistematik sapmalar
    taban = ghi / 1000 * KWP * 0.8
    sabah = np.where(yerel.hour < 12, 0.93, 1.0)       # sabah bias
    yaz_kir = 0.97                                      # kirlenme
    rng = np.random.default_rng(42)
    power = (taban * sabah * yaz_kir *
             (1 + rng.normal(0, 0.02, saat))).clip(0)

    scada = SimpleNamespace(
        power_kw=pd.Series(power, index=idx),
        poa_irradiance=pd.Series(ghi * 1.08, index=idx),
        temp_module=None,
    )
    meteo = SimpleNamespace(
        ghi=pd.Series(ghi, index=idx),
        temp_air=pd.Series(22.0 + 8 * (ghi / max(ghi.max(), 1)), index=idx),
        wind_speed_10m=pd.Series(2.5, index=idx),
    )
    return scada, meteo


@pytest.fixture(scope="module")
def egitim():
    scada, meteo = _sentetik_scada_ve_meteo()
    res = run_hybrid_training(scada, meteo, PLANT_CTX, plant_name="Test GES")
    return res, meteo


# ------------------------------------------------------------------ eğitim yolu
def test_hibrit_egitim_basarili(egitim):
    res, _ = egitim
    assert res.ok, f"eğitim başarısız: {res.error}"
    assert res.model is not None
    assert res.holdout_mape_pct is not None and res.holdout_mape_pct > 0
    assert res.holdout_rmse_kw is not None and res.holdout_rmse_kw > 0
    assert res.physics_mape_pct is not None
    assert res.holdout_hours and res.holdout_hours > 50
    assert res.trained_at is not None


def test_sistematik_hata_ogrenildi(egitim):
    """Sentetik sapmalar sistematik -> hibrit fizikten iyi olmalı."""
    res, _ = egitim
    assert res.holdout_mape_pct < res.physics_mape_pct
    assert res.improvement_pct is not None and res.improvement_pct > 0


def test_session_ozeti_sozlesmesi(egitim):
    res, _ = egitim
    oz = session_ozeti(res)
    for anahtar in ("holdout_mape_pct", "holdout_rmse_kw",
                    "physics_mape_pct", "improvement_pct",
                    "holdout_hours", "trained_at"):
        assert anahtar in oz


# ------------------------------------------------------------------ fallback
def test_bozuk_girdide_istisna_yukselmez():
    """Hibrit patlarsa ok=False döner, raise ETMEZ (UI fiziğe düşer)."""
    from types import SimpleNamespace
    bozuk_scada = SimpleNamespace(power_kw=pd.Series(dtype=float),
                                  poa_irradiance=None, temp_module=None)
    bozuk_meteo = SimpleNamespace(ghi=pd.Series(dtype=float),
                                  temp_air=pd.Series(dtype=float),
                                  wind_speed_10m=pd.Series(dtype=float))
    res = run_hybrid_training(bozuk_scada, bozuk_meteo, PLANT_CTX)
    assert res.ok is False
    assert res.error


# ------------------------------------------------------------------ rapor bağlantısı
def _sentetik_forecast():
    from types import SimpleNamespace
    idx = pd.date_range("2026-07-14", periods=168, freq="1h", tz="UTC")
    g = np.clip(np.sin((idx.tz_convert("Europe/Istanbul").hour.values - 5)
                       / 14 * np.pi), 0, None)
    h = pd.DataFrame({"poa": g * 1050, "temp_cell": 25 + 25 * g,
                      "p_dc_kw": g * 3900, "p_ac_kw": g * 3800,
                      "energy_kwh": g * 3800}, index=idx)
    return SimpleNamespace(
        hourly=h, meta={"power_model": "barhdadi_bennis",
                        "meteo_source": "open-meteo"},
        plant=SimpleNamespace(p_nom_kwp=KWP, latitude=LAT, longitude=LON,
                              tilt=20.0, azimuth=180.0))


def test_apply_hybrid_session_hibrit_varken():
    ctx = from_results(_sentetik_forecast(), None, plant_name="Test", mode="B")
    session = {"hybrid_active": True,
               "hybrid_report": {"holdout_mape_pct": 18.5,
                                 "holdout_rmse_kw": 48.6}}
    ctx = apply_hybrid_session(ctx, session)
    assert ctx.mode == "C"                      # rozet Mod C'ye döner
    assert ctx.holdout_mape_pct == 18.5         # PDF kutusu canlanır
    assert ctx.holdout_rmse_kw == 48.6


def test_apply_hybrid_session_hibrit_yokken_dokunmaz():
    ctx = from_results(_sentetik_forecast(), None, plant_name="Test", mode="B")
    ctx = apply_hybrid_session(ctx, {})         # boş session
    assert ctx.mode == "B"
    assert ctx.holdout_mape_pct is None         # kutu görünmez


def test_hibrit_pdf_de_kutu_ve_mod_c():
    from pvquant.reporting import build_pdf
    ctx = from_results(_sentetik_forecast(), None, plant_name="Test")
    ctx = apply_hybrid_session(ctx, {
        "hybrid_active": True,
        "hybrid_report": {"holdout_mape_pct": 18.5, "holdout_rmse_kw": 48.6}})
    pdf = build_pdf(ctx)
    assert pdf[:4] == b"%PDF"


# ------------------------------------------------------------------ tahmin adaptörü
# ------------------------------------------------- v2.178 oransal yedek öldü
def test_eski_model_ciktisinda_sahte_bant_uretilmez():
    """Kuantil kolonları olmayan (v2.58 öncesi) model çıktısı → h'de
    p10/p90 YOK. Eski dünyada oransal yedek sabit-oranlı sahte bant
    basardı; artık dürüst bantsızlık (yanlış bant, bantsızlıktan kötü).
    confidence dolu olsa bile uydurma yok — yedeğin öldüğünün kanıtı."""
    import types
    import pandas as pd
    from pvquant.pipeline.hybrid_ui import hybrid_forecast_hourly

    i = pd.date_range("2026-06-01", periods=24, freq="1h", tz="UTC")
    ts = pd.DataFrame({"timestamp_utc": i, "ac_power_kw": 100.0})

    class _EskiRes:
        timeseries = ts
        confidence = types.SimpleNamespace(
            p50_total_kwh=2400.0, p10_total_kwh=1900.0, p90_total_kwh=2900.0)

    class _EskiModel:
        def predict(self, fi, cfg):
            return _EskiRes()

    h = hybrid_forecast_hourly(_EskiModel(), _sentetik_meteo_kucuk())
    assert h is not None and "p50_kw" in h.columns
    assert "p10_kw" not in h.columns and "p90_kw" not in h.columns


def _sentetik_meteo_kucuk():
    """Adaptörün beklediği en küçük MeteoData-benzeri nesne: ghi/temp_air/
    wind_speed_10m Series öznitelikleri (bozuk_girdi testindeki
    SimpleNamespace kalıbının sağlıklı eşi — üreticiye bak: hybrid_ui
    ForecastInput'u bu üç öznitelikten kurar)."""
    import pandas as pd
    from types import SimpleNamespace
    i = pd.date_range("2026-06-01", periods=24, freq="1h", tz="UTC")
    return SimpleNamespace(
        ghi=pd.Series(400.0, index=i),
        temp_air=pd.Series(25.0, index=i),
        wind_speed_10m=pd.Series(2.0, index=i))


def test_hibrit_tahmin_adaptorü(egitim):
    res, meteo = egitim
    h = hybrid_forecast_hourly(res.model, meteo)
    assert h is not None
    assert {"p50_kw", "p10_kw", "p90_kw", "energy_kwh"} <= set(h.columns)
    gunduz = h["p50_kw"] > 10
    assert (h.loc[gunduz, "p10_kw"] <= h.loc[gunduz, "p50_kw"] + 1e-6).all()
    assert (h.loc[gunduz, "p50_kw"] <= h.loc[gunduz, "p90_kw"] + 1e-6).all()
    assert h.index.tz is not None               # UTC, tz-aware
