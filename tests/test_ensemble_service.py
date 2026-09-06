"""v2.273 — ensemble bandı: üye kantilleri (SAF), bant_uret yolları, GEFS üye okuyucu (sentetik)."""
import numpy as np
import pandas as pd
import pytest
import xarray as xr

from pvquant import config
from pvquant.io import acik_nwp
from pvquant.services import ensemble_service as es

LAT, LON = 37.87, 32.49


def _uyeler(n=31, seed=0):
    rng = np.random.default_rng(seed)
    ix = pd.date_range("2026-09-07", periods=24, freq="h", tz="UTC")
    taban = np.clip(3000 * np.sin(np.pi * (ix.hour - 3) / 12), 0, None)
    G = pd.DataFrame({u: taban * rng.uniform(0.7, 1.1) for u in range(n)}, index=ix)
    return ix, taban, G


def test_uye_kantilleri_oran_ve_sira():
    ix, taban, G = _uyeler()
    fizik = pd.Series(taban, index=ix); hibrit = fizik * 1.2          # hibrit fiziğin %20 üstü → bant da ölçeklenir
    q = es.uye_kantilleri(G, hibrit, fizik, 4000.0)
    og = ix[10]
    assert q.loc[og, "p10"] <= q.loc[og, "p25"] <= hibrit[og] <= q.loc[og, "p75"] <= q.loc[og, "p90"]
    assert q.loc[og, "p90"] > 1.2 * G.loc[og].quantile(0.9) * 0.99          # oran taşındı
    assert (q.loc[ix[0], ["p10", "p90"]] == 0).all() and q["yayilim"].max() > 0   # gece sıfır, gündüz yayılım var


def test_bant_uret_yollari(monkeypatch):
    config.get_settings.cache_clear()
    plant = {"lat": LAT, "lon": LON, "capacity_kwp": 4000.0}
    ix, taban, G = _uyeler()
    h = pd.DataFrame({"p50_kw": taban * 1.1, "physics_kw": taban}, index=ix)
    class Temel:  # deterministik meteo (nem/yağış yedeği)
        temp_air = pd.Series(25.0, index=ix); wind_speed_10m = pd.Series(2.0, index=ix); cloud_cover = pd.Series(10.0, index=ix); precipitation = None
    monkeypatch.setenv("PVQUANT_BANT_KAYNAGI", "model")
    assert es.bant_uret(plant, None, Temel(), h, 10)[1]["kaynak"] == "model"
    config.get_settings.cache_clear(); monkeypatch.setenv("PVQUANT_BANT_KAYNAGI", "otomatik")
    monkeypatch.setattr(acik_nwp, "arsivden_uyeler", lambda *a, **k: None)
    assert es.bant_uret(plant, None, Temel(), h, 10)[0] is None                        # üye yok → model
    uyeler = {u: pd.DataFrame({"ghi": taban * (0.7 + u / 100), "temp_air": 25.0, "wind_speed_10m": 2.0}, index=ix) for u in range(31)}
    monkeypatch.setattr(acik_nwp, "arsivden_uyeler", lambda *a, **k: uyeler)
    import pvquant.pipeline.forecast as pf
    class FR:  # fizik koşusu sahtesi: güç = ghi × 3 kW/(W/m²)
        def __init__(self, md): self.hourly = pd.DataFrame({"p_ac_kw": md.ghi.values * 3.0}, index=md.ghi.index)
    monkeypatch.setattr(pf, "forecast_7day", lambda md, spec: FR(md))
    q, meta = es.bant_uret(plant, None, Temel(), h, 10)
    assert meta["kaynak"] == "gefs" and meta["uye"] == 31 and q is not None and (q["p90"] >= q["p10"]).all()
    config.get_settings.cache_clear()


def test_gefs_uye_oku(monkeypatch, tmp_path):
    """Sentetik GEFS adım dosyaları (cfgrib yerine bellek içi veri kümeleri): 3 s ortalama → saatlik, K→°C, rüzgar."""
    kosu = np.datetime64("2026-09-07T00:00:00")
    lat = np.array([37.5, 37.75, 38.0]); lon = np.array([32.25, 32.5, 32.75])
    def ds_for(step_h, sdswrf, t2m):
        c = {"latitude": lat, "longitude": lon, "time": kosu, "step": np.timedelta64(step_h, "h"), "valid_time": kosu + np.timedelta64(step_h, "h")}
        al = lambda v: xr.DataArray(np.full((3, 3), v), dims=("latitude", "longitude"), coords=c)
        return [xr.Dataset({"sdswrf": al(sdswrf)}), xr.Dataset({"t2m": al(t2m)}), xr.Dataset({"u10": al(3.0), "v10": al(4.0)}), xr.Dataset({"tcc": al(20.0)})]
    dosyalar = {}
    for s in range(3, 27, 3):
        f = tmp_path / f"gep01.t00z.pgrb2s.0p25.f{s:03d}"; f.write_bytes(b"x")
        dosyalar[str(f)] = ds_for(s, 500.0 if 6 <= s <= 15 else 0.0, 300.15)
    import cfgrib
    monkeypatch.setattr(cfgrib, "open_datasets", lambda p, **k: dosyalar[str(p)])
    df = acik_nwp._gefs_uye_oku(list(tmp_path.glob("gep01*")), LAT, LON)
    assert df is not None and df.index.tz is not None and abs(df["temp_air"].iloc[0] - 27.0) < 1e-6 and abs(df["wind_speed_10m"].iloc[0] - 5.0) < 1e-6
    assert df["ghi"].max() > 100 and df["ghi"].min() >= 0
    monkeypatch.setattr(acik_nwp, "GEFS_ADIMLAR", list(range(3, 27, 3)))
    out = acik_nwp.gefs_uye_noktalar(tmp_path, LAT, LON)
    assert set(out) == {1}                                                       # yalnız yeterli dosyası olan üye
