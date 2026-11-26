"""G4 hazırlık (26.11.2026) — NREL PVDAQ (OEDI, CC BY 4.0) dakikalık CSV → PVQuant saatlik ölçüm çerçevesi (SAF; DB/ağ yok).

Golden 33 (system 33, Golden CO; 2,4 kWdc, SMA SB3000US; `timezone_or_utc_offset` = 7 → **Etc/GMT+7**, yani UTC−7 sabit, yaz saati
YOK — `America/Denver` yanlış) 1 dk CSV'leri: `measured_on` yerel damga, `ac_power__584` W, `dc_power__583` W, `poa_irradiance__582` W/m²,
`ambient_temp__589` / `module_temp_1__590` °C. Saatliğe: güç ORTALANIR (kW), enerji = ortalama güç × kapsama/60 (kWh), ışınım/sıcaklık
ortalanır; `kapsama_dk` = saatteki geçerli dakika; kapsama < `asgari_dk` ise saat NaN (sayı uydurulmaz). Negatif gece gücü (−1,3 W gibi
ölçüm gürültüsü) 0'a kırpılır; ışınım < 0 → 0. Araştırma havuzu: 06_PVDAQ_Golden33 (GOLDEN33_KALITE.csv, metadata_33/KAYNAK.md).
Bu modül yalnız test DB / yerel deney içindir: canlı santral değildir (`santral_turu = sanal_test`, `veri_turu = tarihsel_arsiv`).
"""
from __future__ import annotations

import glob
import os

import numpy as np
import pandas as pd

GOLDEN33 = {"ad": "PVDAQ Golden 33", "lat": 39.7404, "lon": -105.1772, "tz": "Etc/GMT+7", "capacity_kwp": 2.4, "tilt": 40.0, "azimuth": 180.0,
            "panel_tech": None, "yukseklik_m": 1794, "kaynak": "NREL PVDAQ system 33 (OEDI, CC BY 4.0, DOI 10.25984/1846021)"}
KOLONLAR = {"ac_power__584": "power_w", "dc_power__583": "dc_power_w", "poa_irradiance__582": "poa_wm2", "ambient_temp__589": "t_air",
            "module_temp_1__590": "t_module"}
ASGARI_DK = 45          # saatte ≥45 geçerli dakika yoksa saat NaN (kapsama %75)


def dakikalik_oku(yol: str) -> pd.DataFrame:
    """Tek PVDAQ günlük CSV → yerel damgalı dakikalık çerçeve (yalnız KOLONLAR)."""
    df = pd.read_csv(yol, usecols=lambda c: c == "measured_on" or c in KOLONLAR)
    df = df.rename(columns=KOLONLAR)
    df["measured_on"] = pd.to_datetime(df["measured_on"], errors="coerce")
    df = df.dropna(subset=["measured_on"]).set_index("measured_on").sort_index()
    return df[~df.index.duplicated(keep="first")]


def saatlige_indir(dakika: pd.DataFrame, tz: str = GOLDEN33["tz"], asgari_dk: int = ASGARI_DK) -> pd.DataFrame:
    """Yerel dakikalık çerçeve → UTC saatlik (ts_utc index): power_kw, energy_kwh, poa_wm2, t_air, t_module, kapsama_dk, dc_power_kw.
    Saat damgası saat BAŞI (aralik_basi; 12:00 = 12:00–12:59 ortalaması)."""
    if dakika.empty:
        return pd.DataFrame(columns=["power_kw", "energy_kwh", "poa_wm2", "t_air", "t_module", "dc_power_kw", "kapsama_dk"])
    d = dakika.copy()
    d.index = d.index.tz_localize(tz).tz_convert("UTC")
    d["power_w"] = d["power_w"].clip(lower=0.0)
    if "poa_wm2" in d:
        d["poa_wm2"] = d["poa_wm2"].clip(lower=0.0)
    if "dc_power_w" in d:
        d["dc_power_w"] = d["dc_power_w"].clip(lower=0.0)
    g = d.resample("1h")
    out = pd.DataFrame({"power_kw": g["power_w"].mean() / 1000.0, "kapsama_dk": g["power_w"].count()})
    for k in ("poa_wm2", "t_air", "t_module"):
        if k in d:
            out[k] = g[k].mean()
    if "dc_power_w" in d:
        out["dc_power_kw"] = g["dc_power_w"].mean() / 1000.0
    az = out["kapsama_dk"] < asgari_dk
    out.loc[az, [c for c in out.columns if c != "kapsama_dk"]] = np.nan
    out["energy_kwh"] = out["power_kw"] * (out["kapsama_dk"].clip(upper=60) / 60.0)
    out.index.name = "ts_utc"
    return out[["power_kw", "energy_kwh", "poa_wm2", "t_air", "t_module", "dc_power_kw", "kapsama_dk"]] if "dc_power_kw" in out else out


def dizin_donustur(dizin: str, desen: str = "system_33__date_*.csv", tz: str = GOLDEN33["tz"]) -> tuple[pd.DataFrame, dict]:
    """Bir yıl dizini → saatlik çerçeve + özet {dosya, dakika_satir, saat, gecerli_saat, gun, ilk, son, kapsama_dk_ort}."""
    dosyalar = sorted(glob.glob(os.path.join(dizin, desen)))
    parcalar = [dakikalik_oku(p) for p in dosyalar]
    dak = pd.concat(parcalar).sort_index() if parcalar else pd.DataFrame()
    saat = saatlige_indir(dak, tz) if len(dak) else saatlige_indir(dak)
    ozet = {"dosya": len(dosyalar), "dakika_satir": len(dak), "saat": len(saat), "gecerli_saat": int(saat["power_kw"].notna().sum()) if len(saat) else 0,
            "gun": int(saat.index.normalize().nunique()) if len(saat) else 0,
            "ilk": saat.index.min().isoformat() if len(saat) else None, "son": saat.index.max().isoformat() if len(saat) else None,
            "kapsama_dk_ort": round(float(saat["kapsama_dk"].mean()), 1) if len(saat) else None,
            "tz": tz, "not": "yerel damga Etc/GMT+7 → UTC; güç ortalaması kW; saat başı damga; kapsama<45 dk → NaN"}
    return saat, ozet
