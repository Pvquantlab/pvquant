"""v2.256 — kirlenme/kar çarpanı (varsayılan kapalı), meteo yağış/kar alanları, saglik_service SAF + kapı."""
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.io.meteo import MeteoData
from pvquant.pipeline.forecast import PlantSpec, forecast_7day
from pvquant.services.saglik_service import gunluk_indeks, saglik_hesapla

PLANT = "22222222-2222-2222-2222-222222222222"


def _meteo(n_gun=15, yagis=False, kar=False):
    idx = pd.date_range("2026-01-10", periods=24 * n_gun, freq="h", tz="UTC")
    g = np.clip(np.sin((np.asarray(idx.hour) - 5) / 12 * np.pi), 0, None)
    pr = pd.Series(0.0, index=idx)
    if yagis: pr.iloc[24 * 10: 24 * 10 + 3] = 5.0                   # 11. gün 15 mm → temizler
    sn = pd.Series(0.0, index=idx)
    if kar: sn.iloc[24 * 3: 24 * 3 + 4] = 2.0                        # 4. gün 8 cm kar
    return MeteoData(ghi=pd.Series(600 * g, index=idx), temp_air=pd.Series(-2.0 + 6 * g, index=idx), wind_speed_10m=pd.Series(2.0, index=idx),
                     relative_humidity=None, cloud_cover=None, latitude=37.87, longitude=32.49, timezone="UTC",
                     precipitation=pr if yagis or kar else None, snowfall=sn if kar else None)


def _spec(**k):
    return PlantSpec(p_nom_kwp=1000.0, latitude=37.87, longitude=32.49, tilt=25.0, azimuth=180.0, **k)


def test_meteo_alanlari_ve_varsayilan_kapali():
    m = _meteo(yagis=True); assert "precipitation" in m.to_dataframe().columns
    a = forecast_7day(m, _spec()).hourly["p_ac_kw"]; b = forecast_7day(m, _spec(soiling_model="none", kar_model="none")).hourly["p_ac_kw"]
    assert np.allclose(a.fillna(0), b.fillna(0))


def test_kimber_birikir_ve_yagis_temizler():
    m = _meteo(yagis=True)
    kapali = forecast_7day(m, _spec()).hourly["p_ac_kw"]; acik = forecast_7day(m, _spec(soiling_model="kimber", soiling_gunluk_kayip=0.005)).hourly["p_ac_kw"]
    oran = (acik / kapali.replace(0, np.nan))
    g9 = oran[(oran.index.day == 19)].dropna().mean(); g12 = oran[(oran.index.day == 22)].dropna().mean()   # 10. gün (yağış öncesi) vs 13. gün (yağış sonrası)
    assert g9 < 0.97 and g12 > g9                                                    # birikim sonra temizlik
    yagissiz = forecast_7day(_meteo(), _spec(soiling_model="kimber")).hourly["p_ac_kw"]
    assert np.allclose(yagissiz.fillna(0), kapali.fillna(0))                         # yağış serisi yok → atlanır


def test_kar_ortusu_ureti_dusurur():
    m = _meteo(kar=True)
    kapali = forecast_7day(m, _spec()).hourly["p_ac_kw"]; acik = forecast_7day(m, _spec(kar_model="nrel")).hourly["p_ac_kw"]
    kar_gunu = (acik.index.day == 13) | (acik.index.day == 14)
    assert acik[kar_gunu].sum() < kapali[kar_gunu].sum() and (acik <= kapali + 1e-9).all()
    assert np.allclose(acik[acik.index.day >= 20].fillna(0), kapali[kapali.index.day >= 20].fillna(0))   # erimiş → birebir


def test_saglik_indeks_ve_egilim():
    ts = pd.date_range("2024-01-01", periods=24 * 500, freq="h", tz="UTC"); rng = np.random.default_rng(0)
    g = np.clip(np.sin((np.asarray(ts.hour) - 6) / 12 * np.pi), 0, None); bek = 1000 * g
    gun = np.arange(len(ts)) / 24 / 365.25
    ger = bek * 0.9 * (1 - 0.02 * gun) * (1 + rng.normal(0, 0.03, len(ts)))       # −2 %/yıl bozunma
    df = pd.DataFrame({"ts_utc": ts, "power_kw": ger, "beklenen_kw": bek})
    idx = gunluk_indeks(df, 1000.0); assert 400 <= len(idx) <= 500 and 0.8 < idx.mean() < 0.95
    s = saglik_hesapla(idx)
    assert s["bozunma_yuzde_yil"] is not None and -3.0 < s["bozunma_yuzde_yil"] < -1.0 and s["egim_yuzde_yil"] < 0
    kisa = saglik_hesapla(idx.iloc[:200]); assert kisa["bozunma_yuzde_yil"] is None and "13 ay" in kisa["not"] and kisa["egim_yuzde_yil"] is not None   # ~7 ay: egilim var, YoY yok
    assert saglik_hesapla(idx.iloc[:10])["not"] == "en az 60 gün gerekir"
    assert gunluk_indeks(df.assign(beklenen_kw=np.nan), 1000.0).empty


@pytest.fixture()
def istemci(monkeypatch):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "viewer", "exp": 0}
    from pvquant.services import plant_service, saglik_service
    monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": p, "capacity_kwp": 1000.0})
    monkeypatch.setattr(saglik_service, "saglik", lambda t, pl, gun=800: {"bozunma_yuzde_yil": -0.7, "pencere_gun": gun})
    yield TestClient(api_main.app)
    api_main.app.dependency_overrides.clear()


def test_saglik_kapisi(istemci):
    assert istemci.get(f"/v1/plants/{PLANT}/saglik").json()["bozunma_yuzde_yil"] == -0.7
    assert istemci.get(f"/v1/plants/{PLANT}/saglik?gun=10").status_code == 422
