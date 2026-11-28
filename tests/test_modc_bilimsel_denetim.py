"""Faz 1 Mod C bilimsel denetim (28.11.2026) — HybridResidualModel.calibrate değerlendirme metodolojisi için
KUSUR KANITI testleri (sentetik veri yalnız mekanizmayı gösterir; metrik kanıtı değildir).

Her test bir hükmü pinler; davranış (sözleşme) değişirse test kırılır ve karar görünür olur:
  K1  fizik parametreleri (η_BoS/BG) TÜM pencereyle uydurulur, sonra son %20 «holdout» ilan edilir → fizik için holdout örneklem içi.
  K2  LightGBM erken durdurma (model seçimi) AYNI holdout üzerinde yapılır → raporlanan holdout metriği seçimden bağımsız değil.
  K3  konformal q̂ aynı holdout'tan hesaplanır ve kapsama aynı holdout'ta raporlanır → kapsama inşa gereği hedefe oturur (bilgi taşımaz).
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
    son_olcum = pd.Timestamp(hist["timestamp"].max())
    # Fizik uydurması pencerenin SON damgasına kadar görür; oysa holdout = temiz saatlerin son %20'si (aynı kuyruk).
    assert gorulen["son"] == son_olcum, "fizik uydurması holdout kuyruğunu görmüyorsa bu test (ve K1 hükmü) güncellenmeli"
    assert r["holdout_hours"] > 0 and gorulen["n"] >= r["train_hours"] + r["holdout_hours"], \
        "fizik uydurma örneklemi eğitim+holdout toplamından küçük olmalıydı (dürüst bölme) — değil"


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
    assert len(ix) == int(r["holdout_hours"]), "erken durdurma kümesi raporlanan holdout boyutunda değil → hüküm K2 değişti"
    assert all(len(j) == len(ix) and j.equals(ix) for j in yakalanan[1:]), "kuantil boosterlar da aynı holdout'ta seçiliyor"
    assert r["best_iteration"] > 0, "en iyi iterasyon bu kümede seçildi (model seçimi = rapor kümesi)"


# ---------------------------------------------------------------- K3: konformal q̂ ve kapsama aynı veride
def test_k3_konformal_kapsama_hedefe_insa_geregi_oturur():
    from pvquant.config import get_settings
    hedef = float(get_settings().quantile_coverage_target_pct)
    sonuc = {}
    for ad, gurultu in (("az", 0.03), ("cok", 0.20)):
        _, hist = _veri(gurultu=gurultu, tohum=11)
        r = _egit(hist)._training_report
        sonuc[ad] = (r["coverage_p10_p90_raw_pct"], r["coverage_p10_p90_holdout_pct"], r["conformal_offset_kw"])
    for ad, (_ham, kal, _ofs) in sonuc.items():
        assert kal >= hedef - 0.5, f"{ad}: q̂ aynı holdout'tan alındığı için kapsama ≥ hedef olmalıydı (inşa gereği); {kal:.1f} < {hedef}"
    # Ham kapsamalar gürültüye göre ayrışır ama kalibre kapsama ikisinde de hedefe oturur → metrik model kalitesini ayırt etmez.
    assert abs(sonuc["az"][1] - sonuc["cok"][1]) < 5.0, "kalibre kapsama iki gürültü düzeyinde de ~hedef olmalı"
    assert sonuc["az"][2] != sonuc["cok"][2], "ofsetler farklı → kapsamayı eşitleyen şey veri değil, aynı veriden alınan q̂"


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
