"""ERA5 (Copernicus CDS) saatlik arşiv — uzun homojen iklim serisi.

Bağımlılık: `cdsapi` + ~/.cdsapirc (ücretsiz kayıt). Değişkenler: ssrd (J/m² saatlik
biriktirilmiş), 2t, 10u, 10v, tcc. 0.25°, 1940→, ~5 gün gecikme.
ERA5 ışınımı uyduya göre sistematik sapabilir (özellikle bulutlu iklimde);
PVGIS-SARAH3 ile çapraz kontrol önerilir (`belirsizlik.kaynak_sapmasi`).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .atif import KAYNAKLAR
from .ortak import MeteoCerceve, ruzgar_hizi


def indir(hedef: str | Path, lat: float, lon: float, yil_bas: int, yil_son: int, kenar: float = 0.25) -> Path:
    try:
        import cdsapi
    except ImportError as e:  # pragma: no cover
        raise ImportError("pip install cdsapi ve ~/.cdsapirc") from e
    hedef = Path(hedef); hedef.parent.mkdir(parents=True, exist_ok=True)
    cdsapi.Client().retrieve("reanalysis-era5-single-levels", {
        "product_type": ["reanalysis"], "data_format": "netcdf", "download_format": "unarchived",
        "variable": ["surface_solar_radiation_downwards", "2m_temperature", "10m_u_component_of_wind",
                     "10m_v_component_of_wind", "total_cloud_cover"],
        "year": [str(y) for y in range(yil_bas, yil_son + 1)], "month": [f"{m:02d}" for m in range(1, 13)],
        "day": [f"{d:02d}" for d in range(1, 32)], "time": [f"{h:02d}:00" for h in range(24)],
        "area": [lat + kenar, lon - kenar, lat - kenar, lon + kenar],
    }, str(hedef))
    return hedef


def oku(dosya: str | Path, lat: float, lon: float) -> MeteoCerceve:
    try:
        import xarray as xr
    except ImportError as e:  # pragma: no cover
        raise ImportError("pip install xarray netCDF4") from e
    ds = xr.open_dataset(dosya)
    zaman = "valid_time" if "valid_time" in ds.dims else "time"
    n = ds.sel(latitude=lat, longitude=lon, method="nearest")
    idx = pd.DatetimeIndex(pd.to_datetime(n[zaman].values)).tz_localize("UTC")
    # ERA5 saatlik ssrd: o saatin sonunda biten 1 saatlik birikim (J/m²) → /3600 = ortalama W/m²
    ghi = pd.Series(np.asarray(n["ssrd"].values, dtype=float) / 3600.0, index=idx).clip(lower=0.0)
    # Bizim sözleşme: damga = saatin başı → bir saat geri kaydır
    ghi.index = ghi.index - pd.Timedelta(hours=1)
    df = pd.DataFrame({"ghi": ghi})
    df["temp_air"] = pd.Series(np.asarray(n["t2m"].values, dtype=float) - 273.15, index=idx).reindex(df.index)
    df["wind_speed_10m"] = ruzgar_hizi(pd.Series(np.asarray(n["u10"].values, dtype=float), index=idx),
                                       pd.Series(np.asarray(n["v10"].values, dtype=float), index=idx)).reindex(df.index)
    df["cloud_cover"] = pd.Series(np.asarray(n["tcc"].values, dtype=float) * 100.0, index=idx).reindex(df.index)
    return MeteoCerceve(df.dropna(subset=["ghi"]), lat, lon, KAYNAKLAR["era5"])
