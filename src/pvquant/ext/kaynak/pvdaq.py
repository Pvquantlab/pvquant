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


# --- G6-P1 (26.11.2026): mevsimsel kapsama tablosu — G4 kapısının «DJF ≥ %95» ön koşulu için yıl dosyası başına dürüst sayım
MEVSIMLER = {"djf": (12, 1, 2), "mam": (3, 4, 5), "jja": (6, 7, 8), "son": (9, 10, 11)}
KAPSAMA_ESIK_PCT = 95.0   # G4 kalibrasyon kapısı: kış (DJF) geçerli saat oranı ≥ %95 (eşik burada yalnız RAPORLANIR, değiştirilmez)


def mevsim_kapsama(saat: pd.DataFrame, yil: int, tz: str = GOLDEN33["tz"]) -> dict:
    """SAF. UTC saatlik ölçüm çerçevesi (ts_utc index, power_kw) → takvim yılı `yil` için mevsim kapsaması.
    Beklenen saat = o yılın takvimindeki saat sayısı (yerel saatle, `tz`); eksik günler de eksik sayılır (dosyada olmayan saat
    «var» sayılmaz). Geçerli = power_kw NaN değil (kapsama_dk ≥ asgari zaten uygulandı). Döner: {yil, saat, gecerli, gecerli_pct,
    djf_pct, mam_pct, jja_pct, son_pct, djf_esik_pct, djf_uygun, maks_kw, kwh, ilk, son}. Sayı uydurulmaz: boş çerçeve → 0."""
    if saat.empty or "power_kw" not in saat:
        beklenen = pd.date_range(f"{yil}-01-01", f"{yil + 1}-01-01", freq="1h", tz=tz, inclusive="left")
        out = {"yil": int(yil), "saat": 0, "gecerli": 0, "gecerli_pct": 0.0, "djf_esik_pct": KAPSAMA_ESIK_PCT, "djf_uygun": False,
               "maks_kw": None, "kwh": None, "ilk": None, "son": None, "tz": tz, "beklenen_saat": len(beklenen)}
        for m in MEVSIMLER:
            out[f"{m}_pct"] = 0.0
        return out
    idx = saat.index
    if idx.tz is None:
        idx = idx.tz_localize("UTC")
    yerel = idx.tz_convert(tz)
    gecerli = saat["power_kw"].notna().to_numpy()
    yil_maske = (yerel.year == yil)
    beklenen = pd.date_range(f"{yil}-01-01", f"{yil + 1}-01-01", freq="1h", tz=tz, inclusive="left")
    out = {"yil": int(yil), "saat": int(yil_maske.sum()), "gecerli": int((gecerli & yil_maske).sum()), "beklenen_saat": len(beklenen), "tz": tz}
    out["gecerli_pct"] = round(100.0 * out["gecerli"] / len(beklenen), 1)
    for m, aylar in MEVSIMLER.items():
        bek = int(np.isin(beklenen.month, aylar).sum())
        var = int((gecerli & yil_maske & np.isin(yerel.month, aylar)).sum())
        out[f"{m}_pct"] = round(100.0 * var / bek, 1) if bek else 0.0
    out["djf_esik_pct"] = KAPSAMA_ESIK_PCT
    out["djf_uygun"] = bool(out["djf_pct"] >= KAPSAMA_ESIK_PCT)
    g = saat.loc[yil_maske, "power_kw"]
    out["maks_kw"] = round(float(g.max()), 3) if g.notna().any() else None
    out["kwh"] = round(float(saat.loc[yil_maske, "energy_kwh"].sum())) if "energy_kwh" in saat and g.notna().any() else None
    out["ilk"] = idx[yil_maske].min().isoformat() if yil_maske.any() else None
    out["son"] = idx[yil_maske].max().isoformat() if yil_maske.any() else None
    return out
