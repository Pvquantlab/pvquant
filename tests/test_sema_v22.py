"""v2.189 (K-B uygulama mührü): şema v2.2 — beş alan + bump + D26.

Kararlar (kullanıcı, bu oturum): v2.2 = matrix + plant.lat/lon/tz +
run.model/meteo_source; bump bu mühürde; D26 dahil; contracts.SCHEMA_VERSION
("1.1.0", AYRI soy) bilinçli DOKUNULMADI — o şema alanları zaten taşıyor.

ctx stub'u test_bantsiz_rapor kalıbından (v2.178 ailesi): alan listesi
ctx_to_json'un gerçek tüketiminden, uydurma imza yok.
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "reporting" / "html"))
from pvquant.services.report_html_service import ctx_to_json  # noqa: E402
import denetim  # noqa: E402


def _ctx(ufuk=15, **ez):
    from types import SimpleNamespace as NS
    gunler = pd.date_range("2026-08-20", periods=ufuk, freq="D")
    saat = pd.date_range("2026-08-20 00:00", periods=48, freq="h", tz="UTC")
    p50h = (pd.Series([0] * 6 + [50, 200, 400, 500, 520, 480, 300, 100] + [0] * 10,
                      index=saat[:24]).reindex(saat, fill_value=0.0).astype(float))
    karne = pd.DataFrame({
        "date": [gunler[0].date()] * 2, "horizon_bucket": ["0-24", "24-72"],
        "mape": [8.0, 11.0], "rmse": [1.0, 1.5],
        "skill_vs_naive": [30.0, 20.0], "naive_wmape": [12.0, 14.0]})
    n = NS(
        plant_name="Stub GES", capacity_kwp=1000.0, mode="C",
        model_name="hybrid_residual", meteo_source="open-meteo",
        run_at_utc=dt.datetime(2026, 8, 20, 6, 0),
        plant_tz="Europe/Istanbul", latitude=37.87, longitude=32.49,
        tilt_deg=20, azimuth_deg=180,
        daily_kwh=pd.Series([5000.0] * ufuk, index=gunler),
        hourly=pd.DataFrame({"p50_kw": p50h}), karne=karne, karne_kapsama=None,
        uninterrupted_days=12,
        error_dist={"prof_mw": [], "mae24": [], "mae72": [],
                    "mu": 0.1, "sd": 1.0, "ndays": 30},
        coverage_pct=90.0, flag_dagilimi={"valid": 100},
        holdout_mape_pct=9.0, holdout_physics_mape_pct=13.0, kal_pencere_gun=120,
        ilk_scada_ts=None, son_scada_ts=None, albedo=None,
        iklim=pd.DataFrame({"yil": [2024] * 12 + [2025] * 12,
                            "ay": list(range(1, 13)) * 2, "mwh": [100.0] * 24}),
        quality_monthly={"aylar": ["Tem", "Ağu"], "gecerli": [90, 92]},
        kosu_evrim=pd.DataFrame({
            "run_at": pd.to_datetime(["2026-08-18", "2026-08-19"]),
            "p50_mwh": [70.0, 71.0], "half_mwh": [4.0, 4.1]}),
    )
    for k, v in ez.items():
        setattr(n, k, v)
    return n


def _J(**ez):
    from pvquant.config import get_settings
    return ctx_to_json(_ctx(get_settings().forecast_horizon_days, **ez),
                       {"customer": "Stub AŞ", "capacity_kwp": 1000.0})


# ------------------------------------------------------------ üretici (5 alan)
def test_sema_surumu_2_2():
    assert _J()["schema_version"] == "2.2"


def test_plant_kunye_alanlari():
    J = _J()
    assert J["plant"]["lat"] == 37.87
    assert J["plant"]["lon"] == 32.49
    assert J["plant"]["tz"] == "Europe/Istanbul"


def test_run_model_ve_meteo_ayrimi():
    J = _J()
    assert J["run"]["model"] == "hybrid_residual"          # GÜÇ modeli
    assert J["run"]["meteo_source"] == "open-meteo"        # sağlayıcı
    # hava MODELİ ayrı adreste yaşamaya devam eder (§4 ayrımı):
    # üretici sources bloğunu ctx'ten ayrı kurar; burada yalnız run
    # bloğunun hava-modeli taşımadığını kilitliyoruz.
    assert "weather" not in J["run"]


def test_eski_stub_toleransi_meteo_yoksa_null():
    """Yokluk tolere (additive-only kuralı): meteo_source'suz eski ctx
    üreticiyi düşürmez, alan null yazılır."""
    from pvquant.config import get_settings
    ctx = _ctx(get_settings().forecast_horizon_days)
    delattr(ctx, "meteo_source")
    J = ctx_to_json(ctx, {"customer": "Stub AŞ", "capacity_kwp": 1000.0})
    assert J["run"]["meteo_source"] is None
    assert J["schema_version"] == "2.2"


# ------------------------------------------------------------ D26 birim dalları
def _d26_kayit(yuzey):
    kayitlar = []
    denetim._d26(yuzey, lambda *a: kayitlar.append(a))
    assert len(kayitlar) == 1                              # tek-kayıt sözleşmesi
    return kayitlar[0]


def test_d26_alanlar_yoksa_iddia_yok_gecti():
    kod, durum, *_ = _d26_kayit({})
    assert (kod, durum) == ("D26", "gecti")


def test_d26_gecerli_kunye_gecti():
    kod, durum, *_ = _d26_kayit({"PLANT_LAT": 37.87, "PLANT_LON": 32.49,
                                 "PLANT_TZ": "Europe/Istanbul",
                                 "RUN_MODEL": "hybrid_residual"})
    assert (kod, durum) == ("D26", "gecti")


def test_d26_lat_aralik_disi_hata():
    kod, durum, _m, _b, bulunan = _d26_kayit({"PLANT_LAT": 123.4})
    assert (kod, durum) == ("D26", "hata")
    assert "lat" in bulunan


def test_d26_bos_tz_ve_model_hata():
    kod, durum, _m, _b, bulunan = _d26_kayit({"PLANT_TZ": "  ", "RUN_MODEL": ""})
    assert (kod, durum) == ("D26", "hata")
    assert "tz" in bulunan and "model" in bulunan
