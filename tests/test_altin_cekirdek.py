"""v2.597 (Faz 4 F4-A, Stage 2) — korunan çekirdeğin ALTIN testleri (DB'siz, ağsız, deterministik).

Üç referans dondurulur (tests/data/altin/*.json):
  1. forecast_7day — sabit MeteoData + sabit PlantSpec → saatlik p_ac_kw (rel 1e-6).
  2. Katman zinciri — `forecast_service.tahmin_uret` saf yolu: fizik → sentetik GEFS üyeleriyle ensemble bandı → ufuk σ →
     sapma oranı → konformal q̂ → kırpma; p50/p10/p25/p75/p90/p10_ham/p90_ham dondurulur (rel 1e-6).
  3. Hibrit predict — deterministik sentetik eğitim (lightgbm random_state=42) → 3 günlük p50 (rel 1e-6).
Kasıtlı bir çekirdek değişikliği referansı bilerek yeniler: `PVQ_ALTIN_YENILE=1 pytest tests/test_altin_cekirdek.py` ve
commit mesajında NEDEN yazılır. Fixture meta'sı kütüphane sürümlerini taşır; 3. referans lightgbm/sklearn sürümüne duyarlıdır.
"""
from __future__ import annotations

import json
import os
import platform
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from pvquant.io.meteo import MeteoData
from pvquant.pipeline.forecast import forecast_7day
from pvquant.services import ensemble_service as es
from pvquant.services import forecast_service as fs
from pvquant.services.plant_spec_service import plant_spec_kur

ALTIN = Path(__file__).resolve().parent / "data" / "altin"
YENILE = os.environ.get("PVQ_ALTIN_YENILE") == "1"
RTOL = 1e-6

PLANT = {"id": "altin-ges", "name": "Altın GES", "capacity_kwp": 1000.0, "ac_limit_kw": 900.0, "lat": 37.9, "lon": 32.5,
         "tz": "Europe/Istanbul", "tilt": 25.0, "azimuth": 180.0, "panel_tech": "bifacial",
         "params_json": {"iam_model": "ashrae", "spectral_model": "first_solar"}}
KALIBRASYON = {"eta_bos": 0.9, "bg": 0.1}
BAS, GUN = "2026-06-21", 3


def _meteo(bas: str = BAS, gun: int = GUN, carpan: float = 1.0) -> MeteoData:
    ix = pd.date_range(bas, periods=gun * 24, freq="h", tz="UTC")
    saat = np.arange(len(ix)) % 24; g = np.arange(len(ix)) // 24
    ghi = np.clip(900.0 * np.sin(np.pi * (saat - 3.5) / 13.0), 0, None) * (0.95 ** g) * carpan
    temp = 18.0 + 10.0 * np.sin(np.pi * (saat - 6) / 12.0)
    return MeteoData(ghi=pd.Series(ghi, index=ix), temp_air=pd.Series(temp, index=ix), wind_speed_10m=pd.Series(2.5, index=ix),
                     relative_humidity=pd.Series(50.0, index=ix), cloud_cover=pd.Series(20.0, index=ix),
                     latitude=PLANT["lat"], longitude=PLANT["lon"], timezone="UTC", kaynak="acik-nwp", nwp_model="altin-test",
                     kosu_zamani=pd.Timestamp("2026-06-20 18:00", tz="UTC"))


def _meta() -> dict:
    import sklearn
    try:
        import lightgbm
        lgb = lightgbm.__version__
    except Exception:
        lgb = None
    return {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
            "sklearn": sklearn.__version__, "lightgbm": lgb}


def _oku_ya_da_yaz(ad: str, uret) -> dict:
    yol = ALTIN / f"{ad}.json"
    if YENILE or not yol.exists():
        veri = uret()
        veri["meta"] = _meta()
        yol.write_text(json.dumps(veri, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        if not YENILE:
            pytest.fail(f"altın referans yoktu, yazıldı: {yol.relative_to(ALTIN.parents[1])} — gözden geçirip yeniden koş")
    return json.loads(yol.read_text(encoding="utf-8"))


def _karsilastir(ref: dict, yeni: dict, kolonlar):
    assert ref["ts"] == yeni["ts"], "zaman ekseni değişti"
    for k in kolonlar:
        a = np.array(ref[k], dtype=float); b = np.array(yeni[k], dtype=float)
        assert np.isnan(a).tolist() == np.isnan(b).tolist(), f"{k}: NaN deseni değişti"
        m = ~np.isnan(a)
        fark = np.abs(a[m] - b[m]) / np.maximum(np.abs(a[m]), 1e-9)
        assert np.allclose(a[m], b[m], rtol=RTOL, atol=1e-9), f"{k}: en büyük göreli fark {fark.max():.3e} (ilk saat {int(np.argmax(fark))})"


def _seri(df: pd.DataFrame, kolonlar) -> dict:
    return {"ts": [t.isoformat() for t in df.index], **{k: [None if pd.isna(v) else float(v) for v in df[k]] for k in kolonlar}}


# 1 ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_altin_forecast_7day_p_ac():
    spec = plant_spec_kur(PLANT, KALIBRASYON)
    assert spec.eta_bos == 0.9 and spec.bifacial_gain_geometric == 0.1 and spec.bifacial_factor == 0.7 and spec.p_ac_clip_kw == 900.0
    fr = forecast_7day(_meteo(), spec)
    yeni = _seri(fr.hourly, ["p_ac_kw", "p_dc_kw", "poa_global", "temp_cell"])
    yeni["toplam_kwh"] = float(fr.total_kwh)
    ref = _oku_ya_da_yaz("forecast_7day", lambda: dict(yeni))
    _karsilastir(ref, yeni, ["p_ac_kw", "p_dc_kw", "poa_global", "temp_cell"])
    assert abs(ref["toplam_kwh"] - yeni["toplam_kwh"]) <= RTOL * max(abs(ref["toplam_kwh"]), 1.0)
    assert (fr.hourly["p_ac_kw"] <= 900.0 + 1e-9).all() and fr.hourly["p_ac_kw"].max() > 0


# 2 ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def _uyeler(n: int = 8) -> dict:
    """Sentetik GEFS üyeleri: temel GHI'nin ±%15 ölçeklenmiş kopyaları (sabit çarpanlar — zar yok)."""
    out = {}
    for i in range(n):
        c = 0.85 + 0.30 * i / (n - 1)
        m = _meteo(carpan=c)
        out[f"uye{i:02d}"] = pd.DataFrame({"ghi": m.ghi, "temp_air": m.temp_air, "wind_speed_10m": m.wind_speed_10m})
    return out


def _girdi() -> fs.TahminGirdisi:
    saat_oran = {h: (0.92 if 6 <= h <= 10 else 1.04 if 12 <= h <= 16 else 1.0) for h in range(24)}
    return fs.TahminGirdisi(
        mode="B", kalibrasyon_id="kal-altin", kalibrasyon_params=KALIBRASYON, uyeler=_uyeler(),
        ufuk_ayar={"sigma_kw": {"0": 20.0, "24": 45.0, "48": 70.0}, "kova_saat": 24, "n": 120},
        sapma_ayar={"aktif": True, "neden": "test", "oran_genel": 0.99, "oran_saat": saat_oran},
        konformal_ayar=None)


@pytest.fixture()
def ensemble_ayari(monkeypatch):
    monkeypatch.setattr(es, "get_settings", lambda: SimpleNamespace(bant_kaynagi="otomatik", ensemble_min_uye=5))


KOLONLAR = ["p50_kw", "physics_kw", "p10_kw", "p25_kw", "p75_kw", "p90_kw", "p10_ham_kw", "p90_ham_kw"]


def test_altin_katman_zinciri_tahmin_uret(ensemble_ayari):
    simdi = pd.Timestamp("2026-06-21 00:00", tz="UTC")
    sonuc = fs.tahmin_uret(PLANT, _meteo(), _girdi(), simdi=simdi)
    assert sonuc.mode == "B" and sonuc.model_adi == "barhdadi_bennis" and sonuc.ml_model_id is None and sonuc.geri_dusus is None
    assert sonuc.bant["kaynak"] == "gefs" and sonuc.bant["uye"] == 8 and sonuc.n_eksik == 0
    h = sonuc.h
    gunduz = h["p50_kw"] > 0
    assert (h.loc[gunduz, "p10_kw"] <= h.loc[gunduz, "p50_kw"] + 1e-9).all() and (h.loc[gunduz, "p90_kw"] >= h.loc[gunduz, "p50_kw"] - 1e-9).all()
    assert (h["p90_kw"].dropna() <= 900.0 + 1e-9).all()
    yeni = _seri(h, KOLONLAR); yeni["bant"] = sonuc.bant
    ref = _oku_ya_da_yaz("katman_zinciri", lambda: dict(yeni))
    _karsilastir(ref, yeni, KOLONLAR)


def test_altin_katman_zinciri_konformal_ile(ensemble_ayari):
    g = _girdi(); g.mode = "C"
    g.konformal_ayar = {"grup": "saat", "q_hat": {"_genel": 12.0, "6": 20.0, "9": 30.0, "12": 35.0, "15": 25.0}, "hesap_zamani": "2026-06-20T03:00:00+00:00"}
    # model yok → M2 ailesi: C diye yazılmaz, konformal atlanır; ham = servis
    sonuc = fs.tahmin_uret(PLANT, _meteo(), g, simdi=pd.Timestamp("2026-06-21 00:00", tz="UTC"))
    assert sonuc.mode == "B" and sonuc.geri_dusus == "hibrit_artefakt_yok" and sonuc.konformal_ayar is None
    h = sonuc.h
    assert np.allclose(h["p10_kw"].fillna(-1), h["p10_ham_kw"].fillna(-1)) and np.allclose(h["p90_kw"].fillna(-1), h["p90_ham_kw"].fillna(-1))
    # konformal saf uygulayıcı tek başına: aynı ayarla ham banttan servis bandı (dondurulmuş)
    from pvquant.services import konformal_service as kf
    y = kf.uygula_df(h[["p50_kw", "p10_kw", "p90_kw"]].copy(), g.konformal_ayar, 900.0, run_at=pd.Timestamp("2026-06-21 00:00", tz="UTC"))
    yeni = _seri(y, ["p50_kw", "p10_kw", "p90_kw", "p10_ham_kw", "p90_ham_kw"])
    ref = _oku_ya_da_yaz("konformal_uygula", lambda: dict(yeni))
    _karsilastir(ref, yeni, ["p10_kw", "p90_kw", "p10_ham_kw", "p90_ham_kw"])
    gunduz = y["p50_kw"] > 0
    assert (y.loc[gunduz, "p10_kw"] <= y.loc[gunduz, "p10_ham_kw"] + 1e-9).all() and (y.loc[gunduz, "p90_kw"] >= y.loc[gunduz, "p90_ham_kw"] - 1e-9).all()


# 3 ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def _hibrit_model():
    from pvquant.models_v2.contracts import (
        ForecastInput,
        HistoricalData,
        InverterSpec,
        Location,
        MountingSpec,
        OperationConfig,
        PanelSpec,
        PlantProfile,
    )
    from pvquant.models_v2.hybrid_residual import HybridResidualModel
    plant = PlantProfile(plant_id="ALTIN_HIBRIT", name="Altın hibrit", location=Location(latitude=37.87, longitude=32.49, timezone="Europe/Istanbul", elevation_m=1000),
                         dc_capacity_kwp=4514, panel_count=8280,
                         panel=PanelSpec(technology="bifacial", nominal_power_w=545, temperature_coefficient_gamma=-0.34, noct_celsius=45, bifaciality_factor=0.7),
                         mounting=MountingSpec(mount_type="ground_fixed", tilt_degrees=20, azimuth_degrees=180, height_above_ground_m=2.0),
                         inverter=InverterSpec(ac_capacity_kw=215, count=18, efficiency=0.98))
    n = 90
    ix = pd.date_range("2025-03-01", periods=n * 24, freq="h", tz="UTC")
    saat = np.arange(len(ix)) % 24; g = np.arange(len(ix)) // 24
    rng = np.random.default_rng(7)
    bulut = np.repeat(0.6 + 0.4 * rng.random(n), 24)
    ghi = np.clip(950.0 * np.sin(np.pi * (saat - 3.5) / 13.0), 0, None) * bulut
    meteo = pd.DataFrame({"timestamp": ix, "ghi": ghi, "t_air": 12.0 + 12.0 * np.sin(np.pi * (saat - 6) / 12.0) + 0.1 * g, "wind_speed": 2.0 + rng.random(len(ix))})
    base = HybridResidualModel(plant)
    fiz = base.predict(ForecastInput(source="scada", resolution_minutes=60, data=meteo), OperationConfig(operation_mode="pure_forecast")).timeseries
    p = pd.Series(fiz["ac_power_kw"].values, index=ix)
    yerel = ix.tz_convert("Europe/Istanbul").hour
    gercek = p * (1.0 - 0.12 * np.exp(-((yerel - 9) ** 2) / 8.0) + 0.08 * np.exp(-((yerel - 15) ** 2) / 8.0)) * (1.0 + rng.normal(0, 0.03, len(p)))
    hist = pd.DataFrame({"timestamp": ix, "power_kw": gercek.clip(lower=0).values}).merge(meteo, on="timestamp")
    model = HybridResidualModel(plant)
    model.calibrate(HistoricalData(plant_id=plant.plant_id, data=hist))
    return model


def test_altin_hibrit_predict_p50():
    pytest.importorskip("lightgbm")
    from pvquant.pipeline.hybrid_ui import hybrid_forecast_hourly
    model = _hibrit_model()
    m = _meteo(bas="2025-06-10", gun=3)
    m = MeteoData(ghi=m.ghi, temp_air=m.temp_air, wind_speed_10m=m.wind_speed_10m, relative_humidity=None, cloud_cover=None,
                  latitude=37.87, longitude=32.49, timezone="UTC", kaynak="acik-nwp", nwp_model="altin-test")
    hh = hybrid_forecast_hourly(model, m)
    assert hh is not None and "p10_kw" in hh.columns and "p90_kw" in hh.columns
    yeni = _seri(hh, ["p50_kw", "p10_kw", "p90_kw"])
    ref = _oku_ya_da_yaz("hibrit_predict", lambda: dict(yeni))
    if ref["meta"].get("lightgbm") != yeni_meta_lgb():
        pytest.skip(f"lightgbm sürümü referanstan farklı ({ref['meta'].get('lightgbm')} → {yeni_meta_lgb()}); referansı bilinçli yenile")
    _karsilastir(ref, yeni, ["p50_kw", "p10_kw", "p90_kw"])


def yeni_meta_lgb():
    return _meta()["lightgbm"]
