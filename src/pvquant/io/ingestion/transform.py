"""Aşama 3 — Dönüştürme: ham kolonlardan kanonik saatlik UTC frame'e.

Dört klasik tuzağı burada çözüyoruz:

  (a) Saat dilimi: dosyadaki zaman yerelse UTC'ye çevrilir. Yaz saati
      (DST) geçişlerinde ileri alınan saat 'yok' (nonexistent), geri
      alınan saat 'çift' (ambiguous) olur — bunlar NaT yapılıp
      bayraklanır, sessizce tahmin edilmez.
  (b) Birim: kW/MW/W tespiti kurulu güce oranla yapılır.
  (c) Güç mü enerji mi: yalnız enerji varsa güç türetilir
      (P[kW] = E[kWh] / adım_saat). İkisi de varsa güç esas alınır.
  (d) Çözünürlük: sub-saatlik veri saatliğe indirgenir — güç ORTALAMA,
      enerji TOPLAM ile (karıştırmak 4x/12x hataya yol açar).
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from .contracts import ColumnMapping, TransformSpec

#: Kurulu güce oranla birim tespiti eşikleri.
#: max/kapasite < bu → değerler MW olmalı (4.5 MW santralden max "4.4" gelirse).
_MW_RATIO_MAX = 0.005
#: max/kapasite > bu → değerler W olmalı (max "4.400.000" gelirse).
_W_RATIO_MIN = 200.0


def _parse_datetime_robust(raw: pd.Series) -> pd.Series:
    """Tarih parse stratejisi: önce ISO, sonra gün-önce (TR/EU).

    dayfirst=True'yu ISO tarihlere körlemesine uygulamak tehlikelidir
    (pandas 'mixed' modda ay/günü karıştırabilir). Bu yüzden iki aday
    ayrı denenir ve daha çok satırı çözen kazanır; eşitlikte ISO
    tercih edilir (uluslararası dosyalarda daha yaygın).
    """
    s = raw.astype(str).str.strip()
    try:
        iso = pd.to_datetime(s, format="ISO8601", errors="coerce")
    except (ValueError, TypeError):
        iso = pd.to_datetime(s, errors="coerce", dayfirst=False, format="mixed")
    eu = pd.to_datetime(s, errors="coerce", dayfirst=True, format="mixed")
    return iso if iso.notna().sum() >= eu.notna().sum() else eu


def parse_timestamps(
    raw: pd.Series,
    source_timezone: str,
) -> tuple[pd.DatetimeIndex, pd.Series]:
    """Zaman kolonunu tz-aware UTC index'e çevirir.

    Returns:
        (utc_index, dst_flag): dst_flag=True olan satırlar DST geçişinde
        belirsiz/yok saatlerdir; doğrulamada DST_AMBIGUOUS bayrağı alır.
    """
    parsed = _parse_datetime_robust(raw)
    if source_timezone.upper() == "UTC":
        idx = pd.DatetimeIndex(parsed).tz_localize("UTC")
        return idx, pd.Series(False, index=range(len(idx)))

    # Yerel → UTC. ambiguous/nonexistent NaT: sessiz varsayım yok.
    localized = pd.DatetimeIndex(parsed).tz_localize(
        source_timezone, ambiguous="NaT", nonexistent="NaT"
    )
    dst_flag = pd.Series(localized.isna() & parsed.notna().values,
                         index=range(len(localized)))
    return localized.tz_convert("UTC"), dst_flag


def coerce_numeric(series: pd.Series, decimal: str) -> pd.Series:
    """Metin sayıları güvenle float'a çevirir (binlik ayraç dahil).

    '1.234,56' (TR) → 1234.56 ; '1,234.56' (EN) → 1234.56
    Çevrilemeyen → NaN (doğrulamada UNPARSEABLE bayrağı).
    """
    s = series.astype(str).str.strip()
    if decimal == ",":
        s = s.str.replace(".", "", regex=False)      # binlik noktaları at
        s = s.str.replace(",", ".", regex=False)     # ondalık virgül → nokta
    else:
        s = s.str.replace(",", "", regex=False)      # binlik virgülleri at
    return pd.to_numeric(s, errors="coerce")


def detect_power_unit(power: pd.Series, capacity_kwp: float,
                      column_name: str = "") -> str:
    """Güç birimini tespit eder: önce kolon adı, sonra büyüklük oranı.

    Kolon adında açık birim varsa ("(MW)") o kazanır; yoksa serinin
    tepe değeri kurulu güçle oranlanır.
    """
    name = column_name.lower()
    if "mw" in name and "kw" not in name:
        return "MW"
    if "(w)" in name or "[w]" in name or re.search(r"\bw\b", name):
        return "W"
    if "kw" in name:
        return "kW"

    peak = float(power.dropna().quantile(0.999)) if power.notna().any() else 0.0
    if capacity_kwp <= 0 or peak <= 0:
        return "kW"
    ratio = peak / capacity_kwp
    if ratio < _MW_RATIO_MAX:
        return "MW"
    if ratio > _W_RATIO_MIN:
        return "W"
    return "kW"



_UNIT_FACTORS = {"kW": 1.0, "MW": 1000.0, "W": 0.001}


def detect_timestep_minutes(index: pd.DatetimeIndex) -> int:
    """Zaman adımı: ardışık farkların medyanı (io/scada.py ile aynı mantık)."""
    if len(index) < 2:
        return 60
    diffs = index.to_series().diff().dropna()
    return max(int(diffs.median().total_seconds() / 60), 1)


def transform_to_canonical(
    df: pd.DataFrame,
    mapping: ColumnMapping,
    capacity_kwp: float,
    source_timezone: str,
    decimal: str = ".",
) -> tuple[pd.DataFrame, TransformSpec, pd.Series]:
    """Eşlenmiş ham frame'i kanonik saatlik UTC frame'e dönüştürür.

    Kanonik kolonlar: power_kw (+ opsiyonel energy_kwh, poa_global,
    t_air, t_module, wind_speed, ghi). Index: saatlik, UTC, tz-aware.

    Returns:
        (canonical_df, TransformSpec, dst_flag_hourly)

    Not: Bu fonksiyon satır SİLMEZ; çevrilemeyenler NaN kalır ve
    doğrulama aşaması bayraklar. Tek istisna zamanı çözülemeyen
    satırlardır (index'siz satır var olamaz).
    """
    utc_index, dst_flag = parse_timestamps(df[mapping.timestamp], source_timezone)

    work = pd.DataFrame(index=utc_index)
    opt_map = {
        "poa_global": mapping.poa_irradiance,
        "t_air": mapping.temp_ambient,
        "t_module": mapping.temp_module,
        "wind_speed": mapping.wind_speed,
        "ghi": mapping.ghi,
    }

    spec = TransformSpec(source_timezone=source_timezone)

    # --- Güç kaynağı: doğrudan güç mü, enerjiden türetme mi? ---
    if mapping.power is not None:
        power_raw = coerce_numeric(df[mapping.power], decimal)
        power_raw.index = utc_index
        unit = detect_power_unit(power_raw, capacity_kwp, mapping.power)
        work["power_kw"] = power_raw * _UNIT_FACTORS[unit]
        spec.power_unit = unit
        if mapping.energy is not None:
            e = coerce_numeric(df[mapping.energy], decimal)
            e.index = utc_index
            work["energy_kwh"] = e
    else:
        # Yalnız enerji var: P[kW] = E[kWh] / adım_saat
        energy = coerce_numeric(df[mapping.energy], decimal)
        energy.index = utc_index
        step_min = detect_timestep_minutes(utc_index.dropna())
        work["energy_kwh"] = energy
        work["power_kw"] = energy / (step_min / 60.0)
        spec.energy_to_power = True
        spec.power_unit = "kW"

    for canon, src in opt_map.items():
        if src is not None:
            s = coerce_numeric(df[src], decimal)
            s.index = utc_index
            work[canon] = s

    # DST bayrağını index'e taşı (NaT'ler birazdan düşecek)
    dst_series = pd.Series(dst_flag.values, index=utc_index)

    # Zamanı çözülemeyen satırlar index'lenemez → düş (rapora yazılır)
    valid_time = work.index.notna()
    work = work[valid_time].sort_index()
    dst_series = dst_series[valid_time].sort_index()

    # --- Saatliğe indirgeme ---
    spec.timestep_minutes = detect_timestep_minutes(work.index)
    if spec.timestep_minutes < 60:
        agg = {c: "mean" for c in work.columns}
        if "energy_kwh" in work.columns:
            agg["energy_kwh"] = "sum"           # enerji TOPLANIR
        work = work.resample("1h").agg(agg)     # güç/ölçümler ORTALANIR
        dst_series = dst_series.resample("1h").max().fillna(False)
        spec.timestep_minutes = 60

    return work, spec, dst_series.astype(bool)