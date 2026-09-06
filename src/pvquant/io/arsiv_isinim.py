"""v2.269 — Dalga 0: kalibrasyon/iklim için AÇIK arşiv ışınım yolu (Open-Meteo arşivinin yerine).

Sıra (kapsama yeterliyse ilk uyan kazanır; her sonuç MeteoData.kaynak ile etiketlenir):
  1. meteo_arsiv — kendi NWP koşularımızın ≤24 s öncülü saatleri ('servis meteosu'; eğitim = servis, kayma yok)
  2. CAMS Radiation (Copernicus, CC BY 4.0; ~2 gün gecikme; PVQUANT_CAMS_EMAIL kayıtlı e-posta ister)
  3. PVGIS-SARAH3 (JRC, CC BY 4.0; 2005–2023 saatlik; kayıt istemez) — yalnız 2023 sonuna kadar
  4. NASA POWER — ışınımı aylar gecikmeli gelir; yalnız eski dönem ve son çare (kaba 1°)
Hiçbiri kapsamıyorsa None: çağıran dürüstçe hata verir ("CAMS e-postası tanımlayın ya da arşiv biriksin"),
sessizce Open-Meteo'ya dönmez (v2.270 ile kapatıldı).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from pvquant.config import get_settings

PVGIS_ILK_YIL, PVGIS_SON_YIL = 2005, 2023
NASA_GECIKME_GUN = 120


def _md(df: pd.DataFrame, lat: float, lon: float, kaynak: str, etiket: str):
    from pvquant.io.meteo import MeteoData
    df = df.sort_index()
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    return MeteoData(ghi=df["ghi"].astype(float), temp_air=df["temp_air"].astype(float), wind_speed_10m=df["wind_speed_10m"].astype(float),
                     relative_humidity=None, cloud_cover=df["cloud_cover"] if "cloud_cover" in df else None,
                     latitude=float(lat), longitude=float(lon), timezone="UTC",
                     precipitation=df["precipitation"] if "precipitation" in df else None, snowfall=None,
                     kaynak=kaynak, nwp_model=etiket)


def pvgis_df(lat: float, lon: float, yil_bas: int, yil_son: int) -> pd.DataFrame:
    """PVGIS-SARAH3 saatlik, yatay düzlem (pvlib 0.15 kolonları: poa_direct = yatay direkt, poa_sky_diffuse = DHI).
    Damgalar :09/:10 (uydu tarama anı) → saat başına yuvarlanır."""
    import pvlib
    yil_bas = max(yil_bas, PVGIS_ILK_YIL); yil_son = min(yil_son, PVGIS_SON_YIL)
    if yil_bas > yil_son:
        return pd.DataFrame()
    df, _ = pvlib.iotools.get_pvgis_hourly(lat, lon, start=yil_bas, end=yil_son, raddatabase="PVGIS-SARAH3", components=True,
                                           surface_tilt=0, surface_azimuth=180, outputformat="json", map_variables=True)
    idx = pd.DatetimeIndex(df.index).round("h")
    out = pd.DataFrame(index=idx)
    bhi = df["poa_direct"].values.astype(float); dhi = df["poa_sky_diffuse"].values.astype(float)
    zemin = df["poa_ground_diffuse"].values.astype(float) if "poa_ground_diffuse" in df else 0.0
    out["ghi"] = np.clip(bhi + dhi + zemin, 0.0, None)     # .values: :09 damgalı Series yuvarlanmış indekse hizalanmaz
    out["dhi"] = dhi
    z = np.radians(90.0 - df["solar_elevation"].values.astype(float))
    cosz = np.clip(np.cos(z), 0.0872, None)
    out["dni"] = np.where(df["solar_elevation"].values > 2.0, bhi / cosz, 0.0)
    out["temp_air"] = df["temp_air"].values.astype(float)
    out["wind_speed_10m"] = df["wind_speed"].values.astype(float)
    return out[~out.index.duplicated(keep="first")]


def cams_df(lat: float, lon: float, start: str, end: str, email: str) -> pd.DataFrame:
    """CAMS radiation (uydu bulut düzeltmeli); sıcaklık/rüzgar vermez → NaN (kalibrasyon sıcaklığı NWP arşivinden tamamlanır)."""
    import pvlib
    df, _ = pvlib.iotools.get_cams(lat, lon, pd.Timestamp(start), pd.Timestamp(end), email, identifier="cams_radiation",
                                   time_step="1h", map_variables=True)
    out = pd.DataFrame({"ghi": df["ghi"], "dni": df["dni"], "dhi": df["dhi"]})
    out.index = pd.DatetimeIndex(out.index).floor("h")
    out["temp_air"] = np.nan; out["wind_speed_10m"] = np.nan
    return out


def _sicaklik_tamamla(df: pd.DataFrame, lat: float, lon: float, start: str, end: str) -> pd.DataFrame:
    """CAMS'ın vermediği sıcaklık/rüzgarı NWP arşivinden (varsa) ya da PVGIS'ten doldurur; kalanı iklim ortalaması değil NaN kalır
    (kalibrasyon NaN saatleri atar — uydurma yok)."""
    from pvquant.io import acik_nwp
    try:
        ars = acik_nwp.arsivden_gecmis(lat, lon, start, end, asgari_kapsama=0.0)
    except Exception:   # noqa: BLE001
        ars = None
    if ars is not None:
        df["temp_air"] = df["temp_air"].fillna(ars.temp_air.reindex(df.index))
        df["wind_speed_10m"] = df["wind_speed_10m"].fillna(ars.wind_speed_10m.reindex(df.index))
    return df


def gecmis(lat: float, lon: float, start_date: str, end_date: str, asgari_kapsama: float = 0.9):
    """Kalibrasyon dönemi meteosu; kaynak sırası modül başlığında. Kapsama yetersizse None."""
    from pvquant.io import acik_nwp
    a = pd.Timestamp(start_date); b = pd.Timestamp(end_date)
    beklenen = int((b - a) / pd.Timedelta(hours=1)) + 24
    md = None
    try:
        md = acik_nwp.arsivden_gecmis(lat, lon, start_date, end_date, asgari_kapsama)
    except Exception:   # noqa: BLE001
        md = None
    if md is not None:
        return md
    email = get_settings().cams_email
    if email:
        try:
            df = cams_df(lat, lon, start_date, end_date, email)
            if len(df.dropna(subset=["ghi"])) >= asgari_kapsama * beklenen:
                return _md(_sicaklik_tamamla(df, lat, lon, start_date, end_date), lat, lon, "cams", "CAMS Radiation (Copernicus)")
        except Exception as e:   # noqa: BLE001
            print(f"[meteo][uyari] CAMS alınamadı: {type(e).__name__}: {e}")
    if b.year <= PVGIS_SON_YIL:
        try:
            df = pvgis_df(lat, lon, a.year, b.year).loc[str(a.date()):str(b.date())]
            if len(df) >= asgari_kapsama * beklenen:
                return _md(df, lat, lon, "pvgis-sarah3", "PVGIS-SARAH3 (JRC)")
        except Exception as e:   # noqa: BLE001
            print(f"[meteo][uyari] PVGIS alınamadı: {type(e).__name__}: {e}")
    if (pd.Timestamp.now() - b).days > NASA_GECIKME_GUN:
        try:
            from pvquant.ext.kaynak import uydu_isinim
            c = uydu_isinim.nasa_power_saatlik(lat, lon, start_date, end_date)
            df = c.df
            if df["ghi"].notna().sum() >= asgari_kapsama * beklenen:
                return _md(df, lat, lon, "nasa-power", "NASA POWER (1°, kaba)")
        except Exception as e:   # noqa: BLE001
            print(f"[meteo][uyari] NASA POWER alınamadı: {type(e).__name__}: {e}")
    return None


def iklim_serisi(lat: float, lon: float, yil_sayisi: int = 20) -> tuple[pd.DataFrame, int, int]:
    """Aylık iklim beklentisi için uzun saatlik GHI: PVGIS-SARAH3 (2005–2023). Döner (df, ilk_yil, son_yil)."""
    son = PVGIS_SON_YIL; ilk = max(PVGIS_ILK_YIL, son - yil_sayisi + 1)
    df = pvgis_df(lat, lon, ilk, son)
    return df, ilk, son
