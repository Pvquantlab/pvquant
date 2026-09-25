"""Aşama 3 — Dönüştürme: ham kolonlardan kanonik saatlik UTC frame'e.

Beş klasik tuzağı burada çözüyoruz:

  (a) Saat dilimi: dosyadaki zaman yerelse UTC'ye çevrilir. Yaz saati
      (DST) geçişlerinde ileri alınan saat 'yok' (nonexistent), geri
      alınan saat 'çift' (ambiguous) olur — bunlar NaT yapılıp
      bayraklanır, sessizce tahmin edilmez.
  (b) Birim: kW/MW/W tespiti kurulu güce oranla yapılır.
  (c) Güç mü enerji mi: yalnız enerji varsa güç türetilir
      (P[kW] = E[kWh] / adım_saat). İkisi de varsa güç esas alınır.
  (d) Çözünürlük: sub-saatlik veri saatliğe indirgenir — güç ORTALAMA,
      enerji TOPLAM ile (karıştırmak 4x/12x hataya yol açar).
  (e) Kümülatif ömür sayacı: SolarEdge Etotal, Enphase whLifetime gibi
      kolonlar ARALIK enerjisi değil TOPLAM üretimdir — monoton artan
      sayaç olarak tespit edilip diff() alınır. Yakalanmasa güç 
      hesabı sessizce yüzlerce kat yanlış çıkar.
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

#: Kümülatif tespiti: seri örnekleminin bu kadarı monoton artıyorsa
#: kolonu ömür sayacı say. NaN ve geri sayım (sayaç sıfırlama)
#: durumlarına karşı tolerans.
_CUMULATIVE_MONOTONE_FRACTION = 0.90


class DuplicateTimestampsError(ValueError):
    """v2.363 — cihaz/invertör bazlı dosya freni, TİPLİ.

    v2.356 freni düz ValueError'dı; API onu yakalamayıp 500'e çeviriyordu ve
    kusursuz Türkçe mesaj müşteriye hiç ulaşmıyordu (25 Eyl canlı, Kaggle 22
    invertör dosyası). Alanlar API'nin yapılandırılmış 422'sini ve panelin
    "Topla / Ortala" seçimini besler; ValueError mirası eski except'leri kırmaz."""

    def __init__(self, *, rows: int, timestamps: int, ratio: float):
        self.rows, self.timestamps, self.ratio = rows, timestamps, ratio
        super().__init__(
            f"Zaman damgası başına {ratio:.1f} satır var ({rows} satır, "
            f"{timestamps} zaman damgası): dosya cihaz/invertör bazlı görünüyor. "
            "Sessizce birleştirilmez — santral toplamı için duplicate_policy='sum', "
            "ortalama için 'mean' verin.")


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
                      column_name: str = "", return_source: bool = False):
    """Güç birimini tespit eder: önce kolon adı, sonra büyüklük oranı.

    Kolon adında açık birim varsa ("(MW)") o kazanır; yoksa serinin
    tepe değeri kurulu güçle oranlanır.
    """
    def _don(unit, kaynak):
        return (unit, kaynak) if return_source else unit

    name = column_name.lower()
    if "mw" in name and "kw" not in name:
        return _don("MW", "ad")
    if "(w)" in name or "[w]" in name or re.search(r"\bw\b", name):
        return _don("W", "ad")
    if "kw" in name:
        return _don("kW", "ad")

    peak = float(power.dropna().quantile(0.999)) if power.notna().any() else 0.0
    if capacity_kwp <= 0 or peak <= 0:
        return _don("kW", "varsayilan")
    ratio = peak / capacity_kwp
    if ratio < _MW_RATIO_MAX:
        return _don("MW", "oran")
    if ratio > _W_RATIO_MIN:
        return _don("W", "oran")
    return _don("kW", "oran")


_UNIT_FACTORS = {"kW": 1.0, "MW": 1000.0, "W": 0.001}


def detect_timestep_minutes(index: pd.DatetimeIndex) -> int:
    """Zaman adımı: ardışık farkların medyanı (io/scada.py ile aynı mantık)."""
    if len(index) < 2:
        return 60
    diffs = index.to_series().diff().dropna()
    return max(int(diffs.median().total_seconds() / 60), 1)


def _is_cumulative_energy(series: pd.Series, column_name: str = "") -> bool:
    """Enerji kolonu monoton artan bir ömür sayacı mı?

    İki güçlü sinyal:
      - İsim: 'total', 'lifetime', 'cumulative', 'etotal', 'wh_lifetime'
      - İçerik: değerlerin >90%'ı önceki satırdan büyük/eşit

    İçerik sinyali baskındır; isim yalnızca sınır durumları çözer
    (%88-92 aralığında).
    """
    name = column_name.lower()
    name_hits = any(k in name for k in (
        "total", "lifetime", "cumulative", "etotal", "e_total",
        "whlifetime", "wh_lifetime", "e-total",
    ))

    values = pd.to_numeric(series, errors="coerce").dropna()
    if len(values) < 20:
        return name_hits

    diffs = values.diff().dropna()
    if len(diffs) == 0:
        return name_hits

    monotone_frac = float((diffs >= 0).mean())
    if monotone_frac >= _CUMULATIVE_MONOTONE_FRACTION + 0.02:
        return True
    if monotone_frac < _CUMULATIVE_MONOTONE_FRACTION - 0.02:
        return False
    # Sınır: isim ipucu karar verir
    return name_hits


def energy_to_power_kw(energy_kwh_per_interval: pd.Series,
                       step_minutes: int) -> pd.Series:
    """Aralık enerjisinden aralık ortalama gücünü türetir.

    P[kW] = E[kWh] / (adım_saat)
    Örn 15 dk için: P = E / 0.25 = 4 × E.
    """
    hours = step_minutes / 60.0
    return energy_kwh_per_interval / hours


_IRR_KWH_P99_MAX = 3.0  # gunduz p99 bunun altindaysa kWh/m2 suphesi (W/m2 icin imkansiz dusuk)


def normalize_irradiance_wm2(
    s: pd.Series, column_name: str, step_minutes: int
) -> tuple[pd.Series, str, str]:
    """Isinim serisini W/m2'ye normalize eder.

    Vendor exportlari isinimi uc birimde verir ve W/m2 disindakiler
    1000x olcek hatasi yaratir (yasandi: 'Toplam Isima (kWh/m2)' kolonu
    0.5 girdi, fizik olu sensor sandi).

    Oncelik sirasi:
      1. Kolon ADINDAKI birim: kWh/m2 -> x(1000/saat), Wh/m2 -> x(1/saat),
         W/m2 -> oldugu gibi.
      2. Ad birimsizse ICERIK sezgiseli: p99 < 3 ise kWh/m2 varsayilir
         (saatlik kWh/m2 fiziksel tavani ~1.4; W/m2 gunduzu yuzlerdedir).
      3. Hicbiri degilse W/m2 varsayilir.

    Returns:
        (seri_wm2, birim_etiketi, karar_kaynagi)  kaynak: 'ad'|'icerik'|'varsayilan'
    """
    name = (column_name or "").lower().replace(" ", "").replace("²", "2")
    hours = step_minutes / 60.0
    if "kwh/m" in name:
        return s * (1000.0 / hours), "kWh/m2", "ad"
    if "wh/m" in name:  # kwh yukarida yakalandi; bu saf Wh
        return s * (1.0 / hours), "Wh/m2", "ad"
    if "w/m" in name:
        return s, "W/m2", "ad"
    vals = pd.to_numeric(s, errors="coerce").dropna()
    if len(vals) >= 24:
        p99 = float(vals.quantile(0.99))
        if 0.0 < p99 < _IRR_KWH_P99_MAX:
            return s * (1000.0 / hours), "kWh/m2", "icerik"
    return s, "W/m2", "varsayilan"


#: Zaman damgası başına birden çok satır için izin verilen politikalar.
DUPLICATE_POLICIES = ("error", "sum", "mean")


def _collapse_duplicate_timestamps(
    raw: pd.DataFrame, dst_series: pd.Series, policy: str
) -> tuple[pd.DataFrame, pd.Series]:
    """Aynı zaman damgasındaki satırları tek satıra indirger.

    "sum": güç ve enerji TOPLANIR (cihaz → santral), ölçümler ortalanır.
    "mean": hepsi ortalanır (eski örtük davranış; artık yalnız açıkça).
    Tamamı NaN olan bir zaman damgası NaN kalır (min_count=1) — 0 uydurulmaz.
    """
    if policy == "sum":
        sum_cols = [c for c in ("power_raw", "energy_raw") if c in raw.columns]
        mean_cols = [c for c in raw.columns if c not in sum_cols]
        parts = []
        if sum_cols:
            parts.append(raw[sum_cols].groupby(level=0).sum(min_count=1))
        if mean_cols:
            parts.append(raw[mean_cols].groupby(level=0).mean())
        raw = pd.concat(parts, axis=1)[list(raw.columns)]
    else:  # "mean"
        raw = raw.groupby(level=0).mean()
    return raw, dst_series.groupby(level=0).max()


def transform_to_canonical(
    df: pd.DataFrame,
    mapping: ColumnMapping,
    capacity_kwp: float,
    source_timezone: str,
    decimal: str = ".",
    duplicate_policy: str = "error",
) -> tuple[pd.DataFrame, TransformSpec, pd.Series]:
    """Eşlenmiş ham frame'i kanonik saatlik UTC frame'e dönüştürür.

    Kanonik kolonlar: power_kw (+ opsiyonel energy_kwh, poa_global,
    t_air, t_module, wind_speed, ghi). Index: saatlik, UTC, tz-aware.

    Args:
        duplicate_policy: Zaman damgası başına birden çok satır varsa
            (cihaz/invertör bazlı dosya) ne yapılacağı. "error" (varsayılan):
            durur ve kullanıcıya sorar — hiçbir aşama sessiz karar vermez.
            "sum": güç/enerji toplanır (santral toplamı). "mean": ortalanır.

    Returns:
        (canonical_df, TransformSpec, dst_flag_hourly)

    Raises:
        ValueError: duplicate_policy="error" iken çift zaman damgası varsa.

    Not: Bu fonksiyon satır SİLMEZ; çevrilemeyenler NaN kalır ve
    doğrulama aşaması bayraklar. Tek istisna zamanı çözülemeyen
    satırlardır (index'siz satır var olamaz).

    Sıra ÖNEMLİDİR (20 Eyl 2026, Bulgu 1): cihaz satırları önce santral
    serisine birleştirilir, birim ve kümülatif tespiti ONDAN SONRA yapılır.
    Eskiden 22 invertörlü bir dosya resample'da sessizce ORTALANIYOR,
    santral 23x küçük çıkıyor, iç içe geçmiş sayaçlar kümülatif tespitini
    bozuyor ve tepe/kapasite oranı birimi yanlış seçtiriyordu — sıfır uyarıyla.
    """
    if duplicate_policy not in DUPLICATE_POLICIES:
        raise ValueError(
            f"duplicate_policy {duplicate_policy!r} tanınmıyor; "
            f"seçenekler: {DUPLICATE_POLICIES}"
        )

    utc_index, dst_flag = parse_timestamps(df[mapping.timestamp], source_timezone)
    opt_map = {
        "poa_global": mapping.poa_irradiance,
        "t_air": mapping.temp_ambient,
        "t_module": mapping.temp_module,
        "wind_speed": mapping.wind_speed,
        "ghi": mapping.ghi,
    }
    spec = TransformSpec(source_timezone=source_timezone,
                         duplicate_policy=duplicate_policy)

    # --- 1. Ham sayısal seriler: henüz birim/kümülatif kararı YOK ---
    raw = pd.DataFrame(index=utc_index)
    if mapping.power is not None:
        raw["power_raw"] = coerce_numeric(df[mapping.power], decimal).values
    if mapping.energy is not None:
        raw["energy_raw"] = coerce_numeric(df[mapping.energy], decimal).values
    for canon, src in opt_map.items():
        if src is not None:
            raw[canon] = coerce_numeric(df[src], decimal).values
    dst_series = pd.Series(dst_flag.values, index=utc_index)

    # Zamanı çözülemeyen satırlar index'lenemez → düş (rapora yazılır)
    valid_time = raw.index.notna()
    raw = raw[valid_time].sort_index(kind="stable")
    dst_series = dst_series[valid_time].sort_index(kind="stable")

    # --- 2. Zaman damgası başına birden çok satır? (cihaz/invertör bazlı) ---
    n_rows, n_ts = len(raw), raw.index.nunique()
    spec.rows_per_timestamp = round(n_rows / n_ts, 3) if n_ts else 1.0
    if n_rows > n_ts:
        if duplicate_policy == "error":
            # v2.363: tipli hata — API 422 + panel "Topla/Ortala" seçimi bu
            # alanlardan beslenir (25 Eyl canlı: mesaj 500'ün içinde kayboluyordu).
            raise DuplicateTimestampsError(
                rows=n_rows, timestamps=n_ts, ratio=spec.rows_per_timestamp)
        raw, dst_series = _collapse_duplicate_timestamps(raw, dst_series, duplicate_policy)

    # --- 3. Güç kaynağı: artık SANTRAL düzeyinde seri ---
    work = pd.DataFrame(index=raw.index)
    if "power_raw" in raw.columns:
        unit, birim_kaynak = detect_power_unit(
            raw["power_raw"], capacity_kwp, mapping.power, return_source=True)
        work["power_kw"] = raw["power_raw"] * _UNIT_FACTORS[unit]
        spec.power_unit = unit
        spec.power_unit_source = birim_kaynak
        if "energy_raw" in raw.columns:
            e_raw = raw["energy_raw"]
            # Kümülatif tespiti güç varken de kayda geçer (denetim izi)
            if _is_cumulative_energy(e_raw, mapping.energy):
                spec.energy_cumulative = True
                work["energy_kwh"] = e_raw.diff().clip(lower=0)
            else:
                work["energy_kwh"] = e_raw
    else:
        # Yalnız enerji var: kümülatif mi kontrol et
        energy_raw = raw["energy_raw"]
        if _is_cumulative_energy(energy_raw, mapping.energy):
            spec.energy_cumulative = True
            interval_energy = energy_raw.diff().clip(lower=0)   # ömür sayacı → aralık
        else:
            interval_energy = energy_raw
        work["energy_kwh"] = interval_energy
        step_min = detect_timestep_minutes(raw.index)
        work["power_kw"] = energy_to_power_kw(interval_energy, step_min)
        spec.energy_to_power = True
        spec.power_unit = "kW"

    for canon in opt_map:
        if canon in raw.columns:
            s = raw[canon]
            # --- 14 Tem 2026: isinim birim normalizasyonu (B1) ---
            if canon in ("poa_global", "ghi"):
                _step_irr = detect_timestep_minutes(raw.index)
                s, _iu, _isrc = normalize_irradiance_wm2(s, mapping.poa_irradiance
                                                         if canon == "poa_global" else mapping.ghi,
                                                         _step_irr)
                if canon == "poa_global":
                    spec.irradiance_unit = _iu
                    spec.irradiance_unit_source = _isrc
            work[canon] = s

    # --- 4. Saatliğe indirgeme — KAYNAK adımı kaybolmasın (Bulgu 2) ---
    source_step = detect_timestep_minutes(work.index)
    spec.source_timestep_minutes = source_step
    spec.timestep_minutes = source_step
    if source_step < 60:
        agg = {c: "mean" for c in work.columns}
        if "energy_kwh" in work.columns:
            agg["energy_kwh"] = "sum"           # enerji TOPLANIR
        work = work.resample("1h").agg(agg)     # güç/ölçümler ORTALANIR
        dst_series = dst_series.resample("1h").max().fillna(False)
        spec.timestep_minutes = 60

    return work, spec, dst_series.astype(bool)