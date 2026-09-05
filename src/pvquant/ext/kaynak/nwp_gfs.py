"""NOAA GFS / GEFS 0.25° okuyucu (NOMADS grib filter) — kamu malı.

Alt bölge + değişken süzgeciyle küçük GRIB2 indirir:
https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl
Değişkenler: DSWRF (yüzey, W/m² — 0–120 s'de 1 saatlik/3 saatlik ortalama, sonra 6 s),
TMP 2 m (K), UGRD/VGRD 10 m, TCDC (toplam bulut, %). Adım: 0–120 s saatlik, 123–384 3 s.
GEFS için filter_gefs_atmos_0p25s.pl (31 üye; ışınım 'pgrb2s').
"""
from __future__ import annotations

from pathlib import Path

import httpx
import numpy as np
import pandas as pd

from .atif import KAYNAKLAR
from .ortak import MeteoCerceve, kaba_adimi_saatlige_indir, ruzgar_hizi, saatlik_utc_index

GFS_FILTRE = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl"
GEFS_FILTRE = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gefs_atmos_0p25s.pl"
ADIMLAR = list(range(0, 121)) + list(range(123, 385, 3))


def son_kosu(simdi: pd.Timestamp | None = None, gecikme_saat: int = 5) -> pd.Timestamp:
    t = (simdi or pd.Timestamp.utcnow()) - pd.Timedelta(hours=gecikme_saat)
    t = t.tz_localize("UTC") if t.tz is None else t.tz_convert("UTC")
    return t.floor("D") + pd.Timedelta(hours=(t.hour // 6) * 6)


def indir(hedef_dizin: str | Path, lat: float, lon: float, kosu: pd.Timestamp | None = None,
          adimlar: list[int] | None = None, yarim_genislik: float = 0.5, uye: int | None = None,
          timeout: float = 120.0) -> list[Path]:
    """Nokta çevresinde küçük kutu (±yarim_genislik°) ve gerekli değişkenler; adım başına bir dosya."""
    kosu = kosu or son_kosu()
    hedef = Path(hedef_dizin) / f"{'gefs' if uye is not None else 'gfs'}_{kosu.strftime('%Y%m%d%H')}"
    hedef.mkdir(parents=True, exist_ok=True)
    tarih = kosu.strftime("%Y%m%d"); hh = f"{kosu.hour:02d}"
    dosyalar = []
    with httpx.Client(timeout=timeout) as c:
        for s in (adimlar or ADIMLAR):
            if uye is None:
                dosya = f"gfs.t{hh}z.pgrb2.0p25.f{s:03d}"
                params = {"dir": f"/gfs.{tarih}/{hh}/atmos", "file": dosya, "var_DSWRF": "on", "var_TMP": "on",
                          "var_UGRD": "on", "var_VGRD": "on", "var_TCDC": "on", "lev_surface": "on",
                          "lev_2_m_above_ground": "on", "lev_10_m_above_ground": "on", "lev_entire_atmosphere": "on"}
                url = GFS_FILTRE
            else:
                ad = "gec00" if uye == 0 else f"gep{uye:02d}"
                dosya = f"{ad}.t{hh}z.pgrb2s.0p25.f{s:03d}"
                params = {"dir": f"/gefs.{tarih}/{hh}/atmos/pgrb2sp25", "file": dosya, "var_DSWRF": "on",
                          "var_TMP": "on", "var_UGRD": "on", "var_VGRD": "on", "var_TCDC": "on", "all_lev": "on"}
                url = GEFS_FILTRE
            params.update({"subregion": "", "leftlon": lon - yarim_genislik, "rightlon": lon + yarim_genislik,
                           "toplat": lat + yarim_genislik, "bottomlat": lat - yarim_genislik})
            yol = hedef / dosya
            if yol.exists():
                dosyalar.append(yol); continue
            r = c.get(url, params=params)
            if r.status_code == 404:
                continue
            r.raise_for_status(); yol.write_bytes(r.content); dosyalar.append(yol)
    return dosyalar


def oku(dizin: str | Path, lat: float, lon: float) -> MeteoCerceve:
    try:
        import xarray as xr
    except ImportError as e:  # pragma: no cover
        raise ImportError("pip install xarray cfgrib") from e
    dizin = Path(dizin)
    kayit: dict[pd.Timestamp, dict[str, float]] = {}
    kosu = None
    for f in sorted(dizin.glob("*.f*")):
        for filtre, ad, hedef in (({"typeOfLevel": "surface", "shortName": "dswrf"}, "dswrf", "ghi_kaba"),
                                  ({"typeOfLevel": "heightAboveGround", "level": 2}, "t2m", "temp_air"),
                                  ({"typeOfLevel": "heightAboveGround", "level": 10, "shortName": "10u"}, "u10", "u"),
                                  ({"typeOfLevel": "heightAboveGround", "level": 10, "shortName": "10v"}, "v10", "v"),
                                  ({"typeOfLevel": "atmosphere", "shortName": "tcc"}, "tcc", "cloud_cover")):
            try:
                ds = xr.open_dataset(f, engine="cfgrib", backend_kwargs={"filter_by_keys": filtre, "indexpath": ""})
            except Exception:
                continue
            n = ds.sel(latitude=lat, longitude=lon % 360, method="nearest")
            kosu = kosu or pd.Timestamp(n.time.values).tz_localize("UTC")
            gecerli = pd.Timestamp(n.valid_time.values).tz_localize("UTC")
            var = ad if ad in n else list(ds.data_vars)[0]
            kayit.setdefault(gecerli, {})[hedef] = float(n[var].values)
    ham = pd.DataFrame(kayit).T.sort_index()
    hedef_idx = saatlik_utc_index(ham.index[0], int((ham.index[-1] - ham.index[0]) / pd.Timedelta(hours=1)) + 1)
    df = pd.DataFrame(index=hedef_idx)
    df["ghi"] = kaba_adimi_saatlige_indir(ham["ghi_kaba"], lat, lon, hedef_idx)
    df["temp_air"] = (ham["temp_air"] - 273.15).reindex(hedef_idx).interpolate()
    df["wind_speed_10m"] = ruzgar_hizi(ham["u"], ham["v"]).reindex(hedef_idx).interpolate()
    df["cloud_cover"] = ham["cloud_cover"].reindex(hedef_idx).interpolate()
    return MeteoCerceve(df, lat, lon, KAYNAKLAR["gfs"], kosu)


def gefs_uyeleri(hedef_dizin: str | Path, lat: float, lon: float, kosu: pd.Timestamp | None = None,
                 uye_sayisi: int = 30) -> dict[int, pd.DataFrame]:
    """GEFS 0–30 üyelerinin GHI'sını indirip okur; harman.harmanla için `uyeler` sözlüğü."""
    out = {}
    for n in range(0, uye_sayisi + 1):
        indir(hedef_dizin, lat, lon, kosu, uye=n, adimlar=list(range(0, 121, 3)) + list(range(123, 385, 3)))
        c = oku(Path(hedef_dizin) / f"gefs_{(kosu or son_kosu()).strftime('%Y%m%d%H')}", lat, lon)
        out[n] = c.df[["ghi"]]
    return out
