"""v2.381 — tek eksenli izleyici fiziği (yol haritası B4).

Katalogdaki 15 gerçek santralın yarısı izleyicili; fizik hepsini sabit
varsayıyordu. Desen v2.255 ile aynı: VARSAYILAN SABİT → zincir birebir
eski; params_json.izleyici="tek_eksen" ile açılır. Gerçek imza (katalog
§0h): izleyicide omuz saatleri yüksek, ≥%95 plato geniş (Karapınar Eylül
omuz 0.91/0.98, 8 saat; sabit Teksin 0.44/0.57, 3 saat)."""
import numpy as np
import pandas as pd

from pvquant.io.meteo import MeteoData
from pvquant.pipeline.forecast import PlantSpec, forecast_7day
from pvquant.services.calib_service import _plant_spec


def _meteo(n_gun=2):
    idx = pd.date_range("2026-06-10", periods=24 * n_gun, freq="h", tz="UTC")
    g = np.clip(np.sin((np.asarray(idx.hour) - 4) / 14 * np.pi), 0, None)
    return MeteoData(ghi=pd.Series(900 * g, index=idx),
                     temp_air=pd.Series(25.0 + 8 * g, index=idx),
                     wind_speed_10m=pd.Series(2.0, index=idx),
                     relative_humidity=None, cloud_cover=None,
                     latitude=37.87, longitude=32.49, timezone="UTC")


def _spec(**k):
    return PlantSpec(p_nom_kwp=1000.0, latitude=37.87, longitude=32.49,
                     tilt=25.0, azimuth=180.0, **k)


def test_varsayilan_sabit_zincir_birebir():
    m = _meteo()
    eski = forecast_7day(m, _spec()).hourly["p_ac_kw"]
    sabit = forecast_7day(m, _spec(izleyici="sabit")).hourly["p_ac_kw"]
    assert np.allclose(eski.fillna(0), sabit.fillna(0))


def test_izleyici_enerjiyi_artirir_ve_omuzlari_yukseltir():
    m = _meteo()
    sabit = forecast_7day(m, _spec()).hourly["p_ac_kw"].fillna(0)
    izl = forecast_7day(m, _spec(izleyici="tek_eksen")).hourly["p_ac_kw"].fillna(0)
    # yaz günü enerji kazancı: literatür/PVGIS bandı (+%10–40)
    kazanc = izl.sum() / sabit.sum() - 1
    assert 0.10 < kazanc < 0.45, f"kazanç bandın dışında: {kazanc:.2%}"
    # omuz imzası: tepeye oranlanmış üretim, öğleden uzak saatlerde yüksek
    gun = izl.index.hour.isin(range(5, 16))
    o_s, o_i = sabit[gun] / sabit.max(), izl[gun] / izl.max()
    omuz = izl.index[gun].hour.isin([5, 6, 14, 15])
    assert o_i[omuz].mean() > o_s[omuz].mean() + 0.08
    # ≥%95 plato imzası KIRPMAYLA birleşik doğar (gerçek santrallerde DC/AC
    # ~1.3-1.5): AC tavanlı kıyasta izleyicinin tavan-saati sayısı artar
    # (katalog §0h: izleyici 7-8 saat, sabit 3-4 saat)
    s_k = forecast_7day(m, _spec(p_ac_clip_kw=750.0)).hourly["p_ac_kw"].fillna(0)
    i_k = forecast_7day(m, _spec(izleyici="tek_eksen", p_ac_clip_kw=750.0)).hourly["p_ac_kw"].fillna(0)
    assert (i_k >= 0.95 * 750).sum() > (s_k >= 0.95 * 750).sum()
    # gece ikisi de sıfır
    gece = izl.index.hour.isin([0, 1, 2, 22, 23])
    assert izl[gece].abs().max() < 1e-6


def test_plant_spec_izleyici_eslemesi():
    p = {"capacity_kwp": 1000.0, "lat": 37.9, "lon": 32.5,
         "params_json": {"izleyici": "tek_eksen", "izleyici_max_aci": 50}}
    s = _plant_spec(p)
    assert s.izleyici == "tek_eksen" and s.izleyici_max_aci == 50.0
    assert _plant_spec({"capacity_kwp": 1.0, "lat": 37.9, "lon": 32.5}).izleyici == "sabit"


def test_izleyici_acilari_sinirlar_icinde():
    from pvquant.models.irradiance import solar_position, tek_eksen_izleyici_acilari
    idx = pd.date_range("2026-06-10", periods=48, freq="h", tz="UTC")
    sp = solar_position(idx, 37.87, 32.49)
    tilt, azi = tek_eksen_izleyici_acilari(sp["apparent_zenith"], sp["azimuth"], max_aci=60)
    assert tilt.between(0, 60 + 1e-6).all() and not tilt.isna().any()
    # öğlende yatay yakın, sabah/akşam dik yakın
    ogle = tilt[idx.hour == 10].mean()      # Konya güneş öğlesi ~09:50 UTC
    sabah = tilt[idx.hour == 5].mean()
    assert sabah > ogle
