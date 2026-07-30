"""HybridResidualModel uçtan uca test (ağ erişimi gerektirmez).

Strateji: "Gerçek" SCADA'yı, fizik modelinin çıktısını bilinen sistematik
hatalarla bozarak sentetik üretiriz:

  - saat-bağımlı bias (sabah az, öğleden sonra çok üretim),
  - mevsimsel kirlenme (yaz aylarında %4 kayıp),
  - rastgele gürültü,
  - birkaç curtailment günü.

Hibrit model bu sistematik hataları öğrenmeli; holdout MAPE'si saf fizikten
belirgin düşük çıkmalıdır. Bu, residual-learning kurgusunun uçtan uca
çalıştığının kanıtıdır.

Çalıştırma: pytest tests/test_hybrid_residual.py -v
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pvquant.models_v2.contracts import (
    PlantProfile, Location, PanelSpec, MountingSpec, InverterSpec,
    ForecastInput, HistoricalData, OperationConfig,
)
from pvquant.models_v2.hybrid_residual import HybridResidualModel


RNG = np.random.default_rng(42)


@pytest.fixture(scope="module")
def plant() -> PlantProfile:
    return PlantProfile(
        plant_id="TEST_HYBRID",
        name="Test GES",
        location=Location(
            latitude=37.87, longitude=32.49,
            timezone="Europe/Istanbul", elevation_m=1000,
        ),
        dc_capacity_kwp=4514, panel_count=8280,
        panel=PanelSpec(
            technology="bifacial", nominal_power_w=545,
            temperature_coefficient_gamma=-0.34,
            noct_celsius=45, bifaciality_factor=0.7,
        ),
        mounting=MountingSpec(
            mount_type="ground_fixed", tilt_degrees=20,
            azimuth_degrees=180, height_above_ground_m=2.0,
        ),
        inverter=InverterSpec(ac_capacity_kw=215, count=18, efficiency=0.98),
    )


def _synthetic_meteo(n_days: int = 200) -> pd.DataFrame:
    """Basit ama gerçekçi sentetik meteoroloji: clear-sky × bulut süreci."""
    times = pd.date_range(
        "2025-01-01", periods=n_days * 24, freq="h", tz="UTC"
    )
    doy = times.dayofyear.values
    hour = times.hour.values + 2  # ~yerel saat kaydırması (kaba)

    # Clear-sky benzeri GHI: mevsimsel genlik × gün içi çan eğrisi
    seasonal = 550 + 400 * np.sin(2 * np.pi * (doy - 81) / 365.25)
    daily = np.clip(np.sin(np.pi * (hour - 5) / 14), 0, None) ** 1.5
    # Bulutluluk: yavaş değişen AR(1) süreci
    cloud = np.zeros(len(times))
    c = 0.3
    for i in range(len(times)):
        c = 0.95 * c + 0.05 * RNG.uniform(0, 1)
        cloud[i] = c
    ghi = seasonal * daily * (1 - 0.75 * cloud)
    ghi = np.clip(ghi, 0, 1100)

    t_air = (
        12
        + 12 * np.sin(2 * np.pi * (doy - 105) / 365.25)
        + 6 * np.sin(np.pi * (hour - 6) / 14)
    )
    wind = np.clip(2.5 + RNG.normal(0, 1.2, len(times)), 0.2, None)

    return pd.DataFrame(
        {"timestamp": times, "ghi": ghi, "t_air": t_air, "wind_speed": wind}
    )


def _make_synthetic_scada(
    plant: PlantProfile, meteo: pd.DataFrame
) -> pd.DataFrame:
    """Fizik çıktısını bilinen sistematik hatalarla bozarak 'gerçek' üret."""
    base = HybridResidualModel(plant)
    fi = ForecastInput(source="scada", resolution_minutes=60, data=meteo)
    cfg = OperationConfig(operation_mode="pure_forecast")
    physics = base.predict(fi, cfg)
    ts = physics.timeseries.set_index(
        pd.to_datetime(physics.timeseries["timestamp_utc"])
    )
    p = ts["ac_power_kw"].copy()

    local_hour = p.index.tz_convert("Europe/Istanbul").hour
    doy = p.index.dayofyear

    hour_bias = 1.0 - 0.12 * np.exp(-((local_hour - 9) ** 2) / 8.0) \
                    + 0.08 * np.exp(-((local_hour - 15) ** 2) / 8.0)
    soiling = 1.0 - 0.04 * np.clip(np.sin(2 * np.pi * (doy - 150) / 365.25), 0, None)
    noise = 1.0 + RNG.normal(0, 0.03, len(p))

    actual = p * hour_bias * soiling * noise

    # 5 curtailment günü: öğlen saatlerinde üretim %10'a düşür
    curtail_days = pd.to_datetime(
        ["2025-03-10", "2025-04-02", "2025-05-15", "2025-06-01", "2025-06-20"]
    ).dayofyear
    mask = pd.Series(doy, index=p.index).isin(curtail_days) & (
        pd.Series(local_hour, index=p.index).between(11, 15)
    )
    actual[mask.values] = actual[mask.values] * 0.08

    return pd.DataFrame(
        {"timestamp": p.index, "power_kw": actual.clip(lower=0).values}
    )


@pytest.fixture(scope="module")
def calibrated_model(plant):
    meteo = _synthetic_meteo(n_days=200)
    scada = _make_synthetic_scada(plant, meteo)
    hist_df = scada.merge(meteo, on="timestamp")  # ghi/t_air/wind → OM çağrısı atlanır

    model = HybridResidualModel(plant)
    params = model.calibrate(
        HistoricalData(plant_id=plant.plant_id, data=hist_df)
    )
    return model, params, meteo


def test_calibration_improves_holdout_mape(calibrated_model):
    """Hibritin holdout MAPE'si fizikten anlamlı şekilde düşük olmalı."""
    _, params, _ = calibrated_model
    q = params.quality_metrics
    assert q["mape_pct_hybrid_holdout"] < q["mape_pct_physics_holdout"], (
        f"Hibrit ({q['mape_pct_hybrid_holdout']:.2f}%) fizikten "
        f"({q['mape_pct_physics_holdout']:.2f}%) iyi olmalıydı"
    )
    # Sentetik hata sistematik olduğu için iyileşme belirgin olmalı
    assert q["mape_improvement_pct"] > 1.0


def test_predict_calibrated_shapes_and_constraints(calibrated_model, plant):
    model, _, meteo = calibrated_model
    future = meteo.tail(7 * 24).copy()
    fi = ForecastInput(source="open_meteo", resolution_minutes=60, data=future)
    cfg = OperationConfig(
        operation_mode="calibrated",
        confidence_intervals=True,
        include_debug_info=True,
    )
    result = model.predict(fi, cfg)

    ts = result.timeseries
    assert {"ac_power_kw", "ac_power_physics_kw", "ml_residual_kw"} <= set(ts.columns)
    assert (ts["ac_power_kw"] >= 0).all()
    clip = plant.inverter.count * plant.inverter.ac_capacity_kw
    assert (ts["ac_power_kw"] <= clip + 1e-6).all()
    # Gece kilidi
    night = ts["poa_global"] < 5.0
    assert (ts.loc[night, "ac_power_kw"] == 0).all()
    # Quantile sıralaması
    c = result.confidence
    assert c is not None and c.p10_total_kwh <= c.p50_total_kwh <= c.p90_total_kwh
    assert result.model_name == "hybrid_residual"


def test_pure_forecast_without_calibration(plant):
    """Mod A: kalibre edilmemiş model pure_forecast'ta hata vermeden çalışır."""
    meteo = _synthetic_meteo(n_days=8)
    model = HybridResidualModel(plant)
    fi = ForecastInput(source="open_meteo", resolution_minutes=60, data=meteo)
    result = model.predict(fi, OperationConfig(operation_mode="pure_forecast"))
    assert result.model_name == "hybrid_residual"
    assert result.summary.total_energy_kwh > 0


def test_calibrated_mode_requires_calibration(plant):
    meteo = _synthetic_meteo(n_days=8)
    model = HybridResidualModel(plant)
    fi = ForecastInput(source="open_meteo", resolution_minutes=60, data=meteo)
    with pytest.raises(RuntimeError):
        model.predict(fi, OperationConfig(operation_mode="calibrated"))


def test_save_and_load_ml_layer(calibrated_model, plant, tmp_path):
    model, _, meteo = calibrated_model
    model.save_ml_layer(tmp_path)

    fresh = HybridResidualModel(plant)
    assert fresh.load_ml_layer(tmp_path) is True
    # Fizik parametreleri de taşınmalı (gerçekte storage'dan gelir);
    # test için base spec'i kopyala:
    fresh._base._plant_spec = model._base._plant_spec
    fresh._base._calibrated = True
    fresh._calibrated = True

    future = meteo.tail(48)
    fi = ForecastInput(source="open_meteo", resolution_minutes=60, data=future)
    cfg = OperationConfig(operation_mode="calibrated")
    a = model.predict(fi, cfg).summary.total_energy_kwh
    b = fresh.predict(fi, cfg).summary.total_energy_kwh
    assert abs(a - b) < 1e-6


def test_negatif_konformal_ofset_kucaklamayi_bozamaz(calibrated_model, plant):
    """v2.58-C: daraltici (negatif) ofset omuz saatlerinde p10 > p50
    uretebiliyordu (16g kosusunda 137/384 satir; ilacsiz bu test 39 satir
    gecisme ile kirmizi yanar). Asiri negatif ofsetle bile siralama
    her satirda korunmali."""
    from pvquant.models_v2.contracts import ForecastInput, OperationConfig

    model, _, meteo = calibrated_model
    model._conformal_offset_kw = -1e6  # kasitli asiri daraltma
    future = meteo.tail(3 * 24).copy()
    fi = ForecastInput(source="open_meteo", resolution_minutes=60, data=future)
    res = model.predict(fi, OperationConfig(
        operation_mode="calibrated", confidence_intervals=True))
    ts = res.timeseries
    assert "ac_power_p10_kw" in ts.columns
    ok = ((ts["ac_power_p10_kw"] <= ts["ac_power_kw"]) &
          (ts["ac_power_kw"] <= ts["ac_power_p90_kw"]))
    assert ok.all(), f"gecisme: {int((~ok).sum())} satir"
