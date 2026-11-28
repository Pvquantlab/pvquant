"""Faz 1 Mod C bilimsel denetim (28.11.2026) — HybridResidualModel.calibrate değerlendirme metodolojisi için
KUSUR KANITI testleri (sentetik veri yalnız mekanizmayı gösterir; metrik kanıtı değildir).

Her test bir hükmü pinler; davranış (sözleşme) değişirse test kırılır ve karar görünür olur:
  K1  fizik parametreleri (η_BoS/BG) yalnız EĞİTİM dilimiyle uydurulur (holdout + doğrulama dışarıda) — 28.11 KAPANDI.
  K2  LightGBM erken durdurma DOĞRULAMA diliminde; raporlanan holdout seçimde kullanılmaz — 28.11 KAPANDI.
  K3  konformal q̂ doğrulama diliminden; PICP holdout'ta bağımsız ölçülür — 28.11 KAPANDI.
  K4  `kt_referans` ayarı özellik üretimini değiştirir; 28.11 düzeltmesiyle artefakta yazılır ve bekçi servis ayarıyla kıyaslar (KAPANDI).
Üretim parametreleri, eşikler ve denklemler DEĞİŞMEZ; bu dosya yalnız gözlemler.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pvquant.models_v2 import hybrid_residual as hr
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

pytest.importorskip("lightgbm")

TZ = "Europe/Istanbul"


def _profil() -> PlantProfile:
    return PlantProfile(plant_id="DENETIM_C", name="Denetim C", location=Location(latitude=37.87, longitude=32.49, timezone=TZ, elevation_m=1000),
                        dc_capacity_kwp=4514, panel_count=8280,
                        panel=PanelSpec(technology="bifacial", nominal_power_w=545, temperature_coefficient_gamma=-0.34, noct_celsius=45, bifaciality_factor=0.7),
                        mounting=MountingSpec(mount_type="ground_fixed", tilt_degrees=20, azimuth_degrees=180, height_above_ground_m=2.0),
                        inverter=InverterSpec(ac_capacity_kw=215, count=18, efficiency=0.98))


def _veri(gun: int = 90, gurultu: float = 0.03, tohum: int = 7) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Sentetik (meteo, geçmiş): fizik çıktısı saat-bağımlı sapma + gürültüyle bozulur (test_altin_cekirdek kalıbı)."""
    ix = pd.date_range("2025-03-01", periods=gun * 24, freq="h", tz="UTC")
    saat = np.arange(len(ix)) % 24
    g = np.arange(len(ix)) // 24
    rng = np.random.default_rng(tohum)
    bulut = np.repeat(0.6 + 0.4 * rng.random(gun), 24)
    ghi = np.clip(950.0 * np.sin(np.pi * (saat - 3.5) / 13.0), 0, None) * bulut
    meteo = pd.DataFrame({"timestamp": ix, "ghi": ghi, "t_air": 12.0 + 12.0 * np.sin(np.pi * (saat - 6) / 12.0) + 0.1 * g,
                          "wind_speed": 2.0 + rng.random(len(ix))})
    fiz = hr.HybridResidualModel(_profil()).predict(ForecastInput(source="scada", resolution_minutes=60, data=meteo),
                                                   OperationConfig(operation_mode="pure_forecast")).timeseries
    p = pd.Series(fiz["ac_power_kw"].values, index=ix)
    yerel = ix.tz_convert(TZ).hour
    gercek = p * (1.0 - 0.12 * np.exp(-((yerel - 9) ** 2) / 8.0) + 0.08 * np.exp(-((yerel - 15) ** 2) / 8.0)) * (1.0 + rng.normal(0, gurultu, len(p)))
    hist = pd.DataFrame({"timestamp": ix, "power_kw": gercek.clip(lower=0).values}).merge(meteo, on="timestamp")
    return meteo, hist


def _egit(hist: pd.DataFrame) -> hr.HybridResidualModel:
    m = hr.HybridResidualModel(_profil())
    m.calibrate(HistoricalData(plant_id="DENETIM_C", data=hist))
    return m


# ---------------------------------------------------------------- K1: fizik uydurması holdout'u görür
def test_k1_fizik_uydurmasi_holdout_penceresini_icerir(monkeypatch):
    import pvquant.pipeline.calibration as cal
    gorulen: dict = {}
    orijinal = cal.calibrate_from_scada

    def sarmal(*a, **k):
        pw = k["scada"].power_kw.dropna()
        gorulen["n"], gorulen["son"] = len(pw), pw.index.max()
        return orijinal(*a, **k)

    monkeypatch.setattr(cal, "calibrate_from_scada", sarmal)
    _, hist = _veri()
    m = _egit(hist)
    r = m._training_report
    kesim_dog, kesim_hold = pd.Timestamp(m._bolme["kesim_dogrulama"]), pd.Timestamp(m._bolme["kesim_holdout"])
    assert kesim_dog < kesim_hold < pd.Timestamp(hist["timestamp"].max())
    # K1 kapandı: fizik uydurması yalnız eğitim dilimini görür (doğrulama ve holdout kuyruğu dışarıda).
    assert gorulen["son"] < kesim_dog, "fizik uydurması doğrulama/holdout damgası görüyor → K1 yeniden açıldı"
    assert gorulen["n"] <= 0.66 * int(hist["power_kw"].notna().sum()) and r["holdout_hours"] > 0 and r["validation_hours"] > 0


# ---------------------------------------------------------------- K2: erken durdurma = raporlanan holdout
def test_k2_erken_durdurma_kumesi_raporlanan_holdout_ile_ayni(monkeypatch):
    import lightgbm as lgb
    yakalanan: list = []
    orijinal_fit = lgb.LGBMRegressor.fit

    def fit_sarmal(self, x_df, y, **k):
        es = k.get("eval_set")
        if es:
            yakalanan.append(es[0][0].index)
        return orijinal_fit(self, x_df, y, **k)

    monkeypatch.setattr(lgb.LGBMRegressor, "fit", fit_sarmal)
    _, hist = _veri()
    m = _egit(hist)
    r = m._training_report
    assert len(yakalanan) == 4, "L2 + 3 kuantil booster bekleniyordu"
    ix = yakalanan[0]
    kesim_dog, kesim_hold = pd.Timestamp(m._bolme["kesim_dogrulama"]), pd.Timestamp(m._bolme["kesim_holdout"])
    # K2 kapandı: erken durdurma kümesi = doğrulama dilimi; holdout ile kesişmez.
    assert len(ix) == int(r["validation_hours"]) and ix.min() >= kesim_dog and ix.max() < kesim_hold, "erken durdurma holdout'a değiyor → K2 yeniden açıldı"
    assert all(j.equals(ix) for j in yakalanan[1:]), "kuantil boosterlar da aynı doğrulama diliminde durmalı"
    assert r["best_iteration"] > 0 and r["holdout_hours"] > 0


# ---------------------------------------------------------------- K3: konformal q̂ ve kapsama aynı veride
def test_k3_konformal_q_hat_dogrulamadan_picp_holdoutta(monkeypatch):
    # K3 kapandı: q̂ kuantili DOĞRULAMA dilimi boyutundaki skor dizisinden alınır; kapsama HOLDOUT'ta ölçülür (bağımsız PICP).
    import numpy as _np
    boylar: list = []
    orijinal = _np.quantile

    def sarmal(a, q, *args, **k):
        boylar.append(len(_np.asarray(a)))
        return orijinal(a, q, *args, **k)

    monkeypatch.setattr(_np, "quantile", sarmal)
    _, hist = _veri(gurultu=0.08, tohum=11)
    m = _egit(hist)
    r = m._training_report
    assert boylar and boylar[-1] == int(r["validation_hours"]) and boylar[-1] != int(r["holdout_hours"]), "q̂ doğrulama diliminden gelmiyor → K3 yeniden açıldı"
    assert r["coverage_p10_p90_holdout_pct"] == r["coverage_p10_p90_holdout_pct"] and r["coverage_p10_p90_raw_pct"] == r["coverage_p10_p90_raw_pct"]  # NaN değil
    assert m._bolme["yontem"] == "kronolojik_uc_yollu"


# ---------------------------------------------------------------- K4: kt_referans artefakta yazılmaz
def test_k4_kt_referans_ozellik_degistirir_ama_artefakta_yazilmaz(monkeypatch, tmp_path):
    import pvquant.config as cfg
    meteo, _hist = _veri(gun=10)
    m = _egit(_veri()[1])
    fizik = pd.DataFrame({"ghi": meteo["ghi"].values, "poa_global": meteo["ghi"].values * 1.05, "temp_cell": meteo["t_air"].values + 20,
                          "wind_speed_10m": meteo["wind_speed"].values, "p_ac_kw": meteo["ghi"].values * 3.5},
                         index=pd.DatetimeIndex(meteo["timestamp"]))
    gercek_ayar = cfg.get_settings()

    class _A:
        def __getattr__(self, k):
            return getattr(gercek_ayar, k)

    import pvquant.services.mod_c_bekcisi as bek

    def _ayar(kt):
        a = _A()
        a.__dict__["kt_referans"] = kt
        monkeypatch.setattr(cfg, "get_settings", lambda: a)
        monkeypatch.setattr(bek, "get_settings", lambda: a)   # modül düzeyi import — servis ayarı

    _ayar("toa")
    kt_toa = hr.build_features(fizik, 37.87, 32.49, 1000, TZ)["kt"]
    _ayar("ineichen")
    kt_ine = hr.build_features(fizik, 37.87, 32.49, 1000, TZ)["kt"]
    gunduz = fizik["poa_global"] > 50
    assert (kt_toa[gunduz] - kt_ine[gunduz]).abs().max() > 0.05, "kt_referans özelliği değiştirmiyorsa K4 anlamsız"
    # K4 KAPANDI (28.11): artefakt eğitim ayarını taşır; bekçi servis ayarıyla kıyaslar → farklıysa uyumsuz (B'ye düşüş), aynıysa uyumlu.
    from pvquant.services.mod_c_bekcisi import artefakt_uyumlu
    assert m.kt_referans == "toa"
    _ayar("toa")
    assert artefakt_uyumlu(m) == (True, None)
    _ayar("ineichen")
    uyumlu, neden = artefakt_uyumlu(m)
    assert uyumlu is False and "kt_referans" in neden
    m.save_ml_layer(tmp_path)
    import joblib
    yuk = joblib.load(next(tmp_path.glob("*.joblib")))
    assert yuk["kt_referans"] == "toa", "joblib yükü de eğitim ayarını taşımalı"
    # Eski artefakt (alan yok) serbest kalır — geriye uyumluluk
    m.kt_referans = None
    assert artefakt_uyumlu(m) == (True, None)
