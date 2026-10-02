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
    # v2.382: fikstür sözleşmeye uyar — damga = saatin başı, GHI = o saatin
    # açık-gök ortalaması (Ineichen, 4 × 15 dk). Eski sinüs fikstürü UTC 11:00'de
    # tepe yapıyordu; bu konumda güneş öğlesi ~09:50 UTC, yani güneşten ~1.2 sa kaymıştı.
    import pvlib
    idx = pd.date_range("2026-06-10", periods=24 * n_gun, freq="h", tz="UTC")
    alt = pd.date_range(idx[0] + pd.Timedelta(minutes=7.5), periods=len(idx) * 4, freq="15min")
    cs = pvlib.location.Location(37.87, 32.49).get_clearsky(alt, model="ineichen")["ghi"]
    ghi = cs.to_numpy().reshape(len(idx), 4).mean(axis=1)
    g = ghi / ghi.max()
    return MeteoData(ghi=pd.Series(ghi, index=idx),
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
    # gece ikisi de sıfır — 10 Haziran'da doğuş ~02:28, batış ~17:11 UTC; doğuşu içeren
    # 02:00–03:00 saati gündüzdür (aralık ortası güneşi, v2.382)
    gece = izl.index.hour.isin([0, 1, 18, 19, 20, 21, 22, 23])
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


def test_capraz_egim_varsayilan_birebir_ve_yonu():
    """v2.382 — eksene dik eğim: 0 birebir eski; doğuya inen yamaç (pozitif)
    sabahı artırır, akşamı azaltır (geri-izleme komşu sıranın alçakta olduğunu bilir)."""
    m = _meteo()
    duz = forecast_7day(m, _spec(izleyici="tek_eksen")).hourly["p_ac_kw"].fillna(0)
    sifir = forecast_7day(m, _spec(izleyici="tek_eksen", izleyici_capraz_egim=0.0)).hourly["p_ac_kw"].fillna(0)
    assert np.allclose(duz, sifir)
    dogu = forecast_7day(m, _spec(izleyici="tek_eksen", izleyici_capraz_egim=5.0)).hourly["p_ac_kw"].fillna(0)
    sabah = duz.index.hour.isin([3, 4])      # UTC; yerel 06–08
    aksam = duz.index.hour.isin([15, 16])    # UTC; yerel 18–20
    assert dogu[sabah].sum() > duz[sabah].sum()
    assert dogu[aksam].sum() < duz[aksam].sum()


def test_capraz_egim_params_json_eslemesi():
    plant = {"capacity_kwp": 1000.0, "lat": 37.87, "lon": 32.49, "ac_limit_kw": None,
             "params_json": {"izleyici": "tek_eksen", "izleyici_capraz_egim": 4.0}}
    assert _plant_spec(plant).izleyici_capraz_egim == 4.0
    plant["params_json"] = {"izleyici": "tek_eksen"}
    assert _plant_spec(plant).izleyici_capraz_egim == 0.0
