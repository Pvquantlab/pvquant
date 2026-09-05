"""DWD ICON-EU Open Data okuyucu — CC BY 4.0 ("Quelle: Deutscher Wetterdienst").

Kaynak: https://opendata.dwd.de/weather/nwp/icon-eu/grib/{RR}/{param}/
Dosya adı: icon-eu_europe_regular-lat-lon_single-level_{YYYYMMDDRR}_{SSS}_{PARAM}.grib2.bz2
Işınım: ASWDIR_S (direkt, aşağı, W/m² — koşu başından ortalama), ASWDIFD_S (difüz),
sıcaklık T_2M (K), rüzgar U_10M/V_10M, bulut CLCT (%). Adım: 0–78 s saatlik, sonra 3 s.
ICON-EU alanı 23,5°B–45°D / 29,5–70,5°K → Türkiye tamamen içinde. 0.0625° (~7 km).
NOT: ASWDIR_S/ASWDIFD_S "koşu başından ortalama" gelir; aralık ortalamasına
çevirmek için `ortalamadan_aralik()` kullanılır.
"""
from __future__ import annotations

import bz2
from pathlib import Path

import httpx
import numpy as np
import pandas as pd

from .atif import KAYNAKLAR
from .ortak import MeteoCerceve, ruzgar_hizi

KOK = "https://opendata.dwd.de/weather/nwp/icon-eu/grib"
PARAMLAR = {"aswdir_s": "ASWDIR_S", "aswdifd_s": "ASWDIFD_S", "t_2m": "T_2M", "u_10m": "U_10M", "v_10m": "V_10M", "clct": "CLCT"}
ADIMLAR = list(range(0, 79)) + list(range(81, 121, 3))


def son_kosu(simdi: pd.Timestamp | None = None, gecikme_saat: int = 4) -> pd.Timestamp:
    t = (simdi or pd.Timestamp.utcnow()) - pd.Timedelta(hours=gecikme_saat)
    t = t.tz_localize("UTC") if t.tz is None else t.tz_convert("UTC")
    saat = (t.hour // 3) * 3
    return t.floor("D") + pd.Timedelta(hours=saat)


def indir(hedef_dizin: str | Path, kosu: pd.Timestamp | None = None, adimlar: list[int] | None = None,
          timeout: float = 60.0) -> list[Path]:
    """Seçili parametre ve adımların .grib2.bz2 dosyalarını indirip açar."""
    kosu = kosu or son_kosu()
    rr = f"{kosu.hour:02d}"; damga = kosu.strftime("%Y%m%d") + rr
    hedef = Path(hedef_dizin) / f"icon_eu_{damga}"; hedef.mkdir(parents=True, exist_ok=True)
    dosyalar = []
    with httpx.Client(timeout=timeout, follow_redirects=True) as c:
        for kucuk, buyuk in PARAMLAR.items():
            for s in (adimlar or ADIMLAR):
                ad = f"icon-eu_europe_regular-lat-lon_single-level_{damga}_{s:03d}_{buyuk}.grib2"
                yol = hedef / ad
                if yol.exists():
                    dosyalar.append(yol); continue
                r = c.get(f"{KOK}/{rr}/{kucuk}/{ad}.bz2")
                if r.status_code == 404:
                    continue
                r.raise_for_status()
                yol.write_bytes(bz2.decompress(r.content)); dosyalar.append(yol)
    return dosyalar


def ortalamadan_aralik(ort: pd.Series) -> pd.Series:
    """Koşu başından ortalama (W/m²) → aralık ortalaması: A_i = (m_i·t_i − m_{i−1}·t_{i−1})/(t_i − t_{i−1})."""
    t = (ort.index - ort.index[0]) / pd.Timedelta(hours=1)
    t = np.asarray(t, dtype=float)
    kum = ort.values * t
    fark = np.diff(kum, prepend=0.0); dt = np.diff(t, prepend=0.0); dt[0] = 1.0
    return pd.Series(np.clip(fark / dt, 0.0, None), index=ort.index)


def oku(dizin: str | Path, lat: float, lon: float) -> MeteoCerceve:
    """İndirilmiş dizindeki GRIB2'leri okuyup saatlik çerçeve döner (cfgrib gerekir)."""
    try:
        import xarray as xr
    except ImportError as e:  # pragma: no cover
        raise ImportError("pip install xarray cfgrib") from e
    dizin = Path(dizin)
    seriler: dict[str, dict[pd.Timestamp, float]] = {k: {} for k in PARAMLAR}
    kosu = None
    for kucuk, buyuk in PARAMLAR.items():
        for f in sorted(dizin.glob(f"*_{buyuk}.grib2")):
            ds = xr.open_dataset(f, engine="cfgrib", backend_kwargs={"indexpath": ""})
            n = ds.sel(latitude=lat, longitude=lon, method="nearest")
            var = list(ds.data_vars)[0]
            kosu = kosu or pd.Timestamp(n.time.values).tz_localize("UTC")
            gecerli = pd.Timestamp(n.valid_time.values).tz_localize("UTC")
            seriler[kucuk][gecerli] = float(n[var].values)
    S = {k: pd.Series(v).sort_index() for k, v in seriler.items()}
    idx = S["aswdir_s"].index
    df = pd.DataFrame(index=idx)
    dir_ = ortalamadan_aralik(S["aswdir_s"]); dif = ortalamadan_aralik(S["aswdifd_s"].reindex(idx))
    df["ghi"] = (dir_ + dif).clip(lower=0.0)
    df["dhi"] = dif
    # DNI = direkt yatay / cos(zenit); zenit>85° için sınırla
    from .ortak import gunes_konumu
    z = np.radians(gunes_konumu(idx, lat, lon)["apparent_zenith"].values)
    cosz = np.clip(np.cos(z), 0.0872, None)  # ≥ cos(85°)
    df["dni"] = np.where(np.degrees(z) < 88, dir_.values / cosz, 0.0)
    df["temp_air"] = S["t_2m"].reindex(idx) - 273.15
    df["wind_speed_10m"] = ruzgar_hizi(S["u_10m"].reindex(idx), S["v_10m"].reindex(idx))
    df["cloud_cover"] = S["clct"].reindex(idx)
    df = df.resample("h").interpolate(limit=3)
    return MeteoCerceve(df, lat, lon, KAYNAKLAR["icon"], kosu)
