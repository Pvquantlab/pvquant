"""Uydu türevli ışınım — CAMS Solar Radiation Time-Series ve PVGIS (SARAH-3).

İkisi de ücretsiz, CC BY 4.0, Türkiye Meteosat alanında. pvlib.iotools üzerinden:
  - CAMS: e-posta kaydı gerekir (SoDa); 1 dk–1 saat; 2004→; ~2 gün gecikme.
  - PVGIS: kayıt yok; SARAH-3 2005–2023 saatlik; TMY.
Kullanım alanı: kalibrasyon dönemi ışınımı (ölçüm yoksa "sanal piranometre"),
20 yıllık iklim beklentisi ve NWP sapma düzeltmesi için gerçekleşen referans.
"""
from __future__ import annotations

import pandas as pd
import pvlib

from .atif import KAYNAKLAR
from .ortak import MeteoCerceve


def cams(lat: float, lon: float, baslangic: str, bitis: str, email: str, adim: str = "1h",
         yukseklik: float | None = None) -> MeteoCerceve:
    """CAMS radiation (McClear tabanlı, uydu bulut düzeltmeli). adim: '1min','15min','1h','1d'."""
    df, meta = pvlib.iotools.get_cams(lat, lon, pd.Timestamp(baslangic), pd.Timestamp(bitis), email,
                                      identifier="cams_radiation", time_step=adim, altitude=yukseklik,
                                      map_variables=True)
    out = pd.DataFrame({"ghi": df["ghi"], "dni": df["dni"], "dhi": df["dhi"]})
    # CAMS sıcaklık/rüzgar vermez; harman/NWP'den ya da ERA5'ten tamamlanır → NaN
    out["temp_air"] = float("nan"); out["wind_speed_10m"] = float("nan")
    if adim != "1h":
        out = out.resample("h").mean()
    return MeteoCerceve(out, lat, lon, KAYNAKLAR["cams"])


def pvgis_saatlik(lat: float, lon: float, yil_bas: int = 2005, yil_son: int = 2023,
                  veri_tabani: str = "PVGIS-SARAH3") -> MeteoCerceve:
    """PVGIS saatlik seri (SARAH-3 2005–2023 ya da PVGIS-ERA5). Yatay düzlem, W/m²."""
    df, meta = pvlib.iotools.get_pvgis_hourly(lat, lon, start=yil_bas, end=yil_son, raddatabase=veri_tabani,
                                              components=True, surface_tilt=0, surface_azimuth=180,
                                              outputformat="json", map_variables=True)
    out = pd.DataFrame(index=df.index)
    # poa_* yatay düzlemde: global = ghi; direct ≈ dni·cosθ (yatay → beam yatay); diffuse+ground ≈ dhi
    out["ghi"] = df["poa_global"]
    out["dhi"] = df["poa_sky_diffuse"] + df.get("poa_ground_diffuse", 0.0)
    out["temp_air"] = df["temp_air"]; out["wind_speed_10m"] = df["wind_speed"]
    out = out.drop(columns=[c for c in ("dni",) if c in out])
    return MeteoCerceve(out, lat, lon, KAYNAKLAR["pvgis"])


def pvgis_tmy(lat: float, lon: float) -> tuple[pd.DataFrame, dict]:
    """PVGIS TMY (SARAH tabanlı, ISO 15927-4 yöntemi). Bankable karşılaştırma için hazır TMY."""
    df, months, inputs, meta = pvlib.iotools.get_pvgis_tmy(lat, lon, outputformat="json", map_variables=True)
    return df, {"aylar": months, "girdi": inputs, "meta": meta}


def nasa_power_saatlik(lat: float, lon: float, baslangic: str, bitis: str) -> MeteoCerceve:
    """NASA POWER saatlik (2001→, 1° — kaba; yalnız son çare/kıyas)."""
    import httpx
    url = "https://power.larc.nasa.gov/api/temporal/hourly/point"
    p = {"parameters": "ALLSKY_SFC_SW_DWN,ALLSKY_SFC_SW_DNI,ALLSKY_SFC_SW_DIFF,T2M,WS10M,CLOUD_AMT",
         "community": "RE", "latitude": lat, "longitude": lon,
         "start": pd.Timestamp(baslangic).strftime("%Y%m%d"), "end": pd.Timestamp(bitis).strftime("%Y%m%d"),
         "format": "JSON", "time-standard": "UTC"}
    r = httpx.get(url, params=p, timeout=120); r.raise_for_status()
    par = r.json()["properties"]["parameter"]
    idx = pd.to_datetime(list(par["ALLSKY_SFC_SW_DWN"].keys()), format="%Y%m%d%H", utc=True)
    df = pd.DataFrame({"ghi": list(par["ALLSKY_SFC_SW_DWN"].values()), "dni": list(par["ALLSKY_SFC_SW_DNI"].values()),
                       "dhi": list(par["ALLSKY_SFC_SW_DIFF"].values()), "temp_air": list(par["T2M"].values()),
                       "wind_speed_10m": list(par["WS10M"].values()), "cloud_cover": list(par["CLOUD_AMT"].values())},
                      index=idx).replace(-999.0, float("nan"))
    return MeteoCerceve(df, lat, lon, KAYNAKLAR["nasa_power"])
