"""ECMWF Open Data okuyucu (IFS HRES / ENS / AIFS) — CC BY 4.0.

Bağımlılık: `ecmwf-opendata` (pip) + `cfgrib`/`xarray` (eccodes gerekir).
Kaynak: https://www.ecmwf.int/en/forecasts/datasets/open-data
Değişkenler: ssrd (biriktirilmiş J/m²), 2t (K), 10u/10v (m/s), tcc (0–1).
Zaman adımı: 0–144 s 3 saatlik, sonra 6 saatlik (0.25°). Saatliğe indirgeme
`ortak.kaba_adimi_saatlige_indir` ile (gök açıklığı sabit, açık gök profili).
ECMWF yalnız son ~2–3 günün koşularını tutar → `kosu_arsivle()` ile GRIB'i sakla.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .atif import KAYNAKLAR
from .ortak import MeteoCerceve, biriktirilmisten_saatlik, kaba_adimi_saatlige_indir, ruzgar_hizi, saatlik_utc_index

ADIMLAR_HRES = list(range(0, 145, 3)) + list(range(150, 241, 6))
ADIMLAR_ENS = list(range(0, 145, 3)) + list(range(150, 361, 6))


def indir(hedef_dizin: str | Path, kosu: pd.Timestamp | None = None, tip: str = "fc",
          model: str = "ifs", adimlar: list[int] | None = None, uye: bool = False) -> Path:
    """GRIB2'yi indirir. tip='fc' HRES, uye=True → 'pf' (perturbed) + 'cf' (control) ENS."""
    try:
        from ecmwf.opendata import Client
    except ImportError as e:  # pragma: no cover
        raise ImportError("pip install ecmwf-opendata") from e
    hedef = Path(hedef_dizin); hedef.mkdir(parents=True, exist_ok=True)
    istek = dict(param=["ssrd", "2t", "10u", "10v", "tcc"], step=adimlar or ADIMLAR_HRES,
                 type="pf" if uye else tip, stream="enfo" if uye else "oper")
    if kosu is not None:
        istek["date"] = pd.Timestamp(kosu).strftime("%Y%m%d"); istek["time"] = int(pd.Timestamp(kosu).hour)
    if uye:
        istek["number"] = list(range(1, 51))
    dosya = hedef / f"ecmwf_{model}_{'ens' if uye else 'hres'}_{istek.get('date','latest')}{istek.get('time','')}.grib2"
    Client(source="ecmwf", model=model).retrieve(target=str(dosya), **istek)
    return dosya


def _grib_ac(dosya: Path, lat: float, lon: float, sayi: int | None = None):
    try:
        import xarray as xr
    except ImportError as e:  # pragma: no cover
        raise ImportError("pip install xarray cfgrib (eccodes kütüphanesi gerekir)") from e
    filtre = {"typeOfLevel": "surface"}
    ds = xr.open_dataset(dosya, engine="cfgrib", backend_kwargs={"filter_by_keys": filtre, "indexpath": ""})
    lon_ds = lon % 360 if float(ds.longitude.max()) > 180 else lon
    nokta = ds.sel(latitude=lat, longitude=lon_ds, method="nearest")
    if sayi is not None and "number" in nokta.dims:
        nokta = nokta.sel(number=sayi)
    return nokta


def oku(dosya: str | Path, lat: float, lon: float, uye_sayisi: int = 0) -> MeteoCerceve:
    """İndirilmiş GRIB2 → MeteoCerceve (saatlik UTC). uye_sayisi>0 ise ENS üyeleri de eklenir."""
    dosya = Path(dosya)
    nokta = _grib_ac(dosya, lat, lon, sayi=None if uye_sayisi == 0 else 1)
    kosu = pd.Timestamp(nokta.time.values).tz_localize("UTC")
    gecerli = pd.DatetimeIndex(pd.to_datetime(nokta.valid_time.values)).tz_localize("UTC")
    adim_saat = pd.Series(np.diff(np.r_[gecerli[0].value, gecerli.values.astype("int64")]) / 3.6e12, index=gecerli)
    adim_saat.iloc[0] = adim_saat.iloc[1] if len(adim_saat) > 1 else 3

    def seri(ad):
        return pd.Series(np.asarray(nokta[ad].values, dtype=float), index=gecerli)

    ssrd_W = biriktirilmisten_saatlik(seri("ssrd"), adim_saat)
    hedef = saatlik_utc_index(gecerli[0], int((gecerli[-1] - gecerli[0]) / pd.Timedelta(hours=1)) + 1)
    df = pd.DataFrame(index=hedef)
    df["ghi"] = kaba_adimi_saatlige_indir(ssrd_W, lat, lon, hedef)
    df["temp_air"] = (seri("t2m") - 273.15).reindex(hedef).interpolate()
    df["wind_speed_10m"] = ruzgar_hizi(seri("u10"), seri("v10")).reindex(hedef).interpolate()
    df["cloud_cover"] = (seri("tcc") * 100.0).reindex(hedef).interpolate()
    uyeler = {}
    for n in range(1, uye_sayisi + 1):
        u = _grib_ac(dosya, lat, lon, sayi=n)
        s = pd.Series(np.asarray(u["ssrd"].values, dtype=float), index=gecerli)
        uyeler[n] = pd.DataFrame({"ghi": kaba_adimi_saatlige_indir(biriktirilmisten_saatlik(s, adim_saat), lat, lon, hedef)})
    return MeteoCerceve(df, lat, lon, KAYNAKLAR["ecmwf"], kosu, uyeler)


def kosu_arsivle(hedef_dizin: str | Path, gun_tut: int = 400) -> list[Path]:
    """Günlük cron: son koşuyu indir, `gun_tut` günden eskileri sil. Kalibrasyon/backtest arşivi."""
    hedef = Path(hedef_dizin)
    yeni = indir(hedef)
    esik = pd.Timestamp.utcnow() - pd.Timedelta(days=gun_tut)
    silinen = []
    for f in hedef.glob("ecmwf_*.grib2"):
        if pd.Timestamp(f.stat().st_mtime, unit="s", tz="UTC") < esik:
            f.unlink(); silinen.append(f)
    return [yeni] + silinen
