"""Aşama 2 — Kolon eşleme.

Dosya kolonlarını kanonik alanlara (timestamp, power, energy, ...)
eşler. Üç katmanlı strateji:

  1. Sözlük eşleşmesi: 16+ vendor'un CSV/API formatlarından derlenmiş
     çok dilli sözlük (marka referans dokümanından). Tam eşleşme > 
     kelime-sınırlı içerme > düz içerme.
  2. Fuzzy yedeği: rapidfuzz varsa Levenshtein, yoksa difflib. Sadece
     biçim varyantlarını (büyük/küçük harf, alt çizgi, birim eki)
     yakalar — anlamsal çeviri YAPMAZ.
  3. İçerik doğrulaması: aday kolonun İÇERİĞİ iddiaya uymalı —
     "timestamp" diye eşlenen kolon gerçekten tarihe çevrilebiliyor mu,
     "power" eşlenen kolon sayısal mı? İçerik tutmuyorsa güven düşer.

ÖNEMLİ TASARIM NOTU (GHI vs POA):
  GHI (Global Horizontal Irradiance) yatay düzlem ışınımıdır;
  POA (Plane of Array) eğik panel düzlemi ışınımıdır. Kalibrasyon
  fizik zinciri POA bekler; GHI'yi POA sanıp beslemek modeli bozar.
  Bu yüzden iki alan AYRI sözlüklerde tutulur; marka referansındaki
  öneriye rağmen 'ghi' asla poa_irradiance'a alias olarak eklenmez.
"""
from __future__ import annotations

import re
import unicodedata

import pandas as pd

from .contracts import ColumnMapping

#: Kanonik alan → eşanlamlılar. Küçük harf, aksansız karşılaştırılır.
#: Birime dair ekler ("(kW)", "[MW]") karşılaştırmadan önce soyulur.
SYNONYMS: dict[str, list[str]] = {
    "timestamp": [
        "timestamp", "time", "datetime", "date time", "date", "tarih",
        "zaman", "tarih saat", "saat", "period", "interval start",
        "zeit", "fecha", "data", "collection time", "statistical period",
        # Marka referansı
        "reading_time", "measured_at", "sample time", "log time",
        "date_time", "log date", "record time",
    ],
    "power": [
        "power", "active power", "ac power", "ac active power", "p_ac",
        "pac", "guc", "aktif guc", "cikis gucu", "uretim gucu",
        "leistung", "wirkleistung", "potencia", "puissance",
        "grid power", "output power", "total active power", "power kw",
        # Marka referansı (SolarEdge, Fronius, Enphase, SMA, Sungrow)
        "powerreal_p_sum", "wnow", "w_now", "pac_total", "p_total",
        "ac_power", "invout_power", "power_ac", "inverter power",
        "instant power", "current power", "actual power", "pv power",
    ],
    "energy": [
        "energy", "yield", "production", "generation", "enerji",
        "uretim", "gunluk uretim", "toplam uretim", "ertrag",
        "energia", "total yield", "daily yield", "inverter yield",
        "feed-in energy", "on-grid energy", "kwh",
        # Marka referansı (SolarEdge, Enphase, Fronius, Sungrow)
        "etotal", "e_total", "e-total", "whlifetime", "wh_lifetime",
        "wh lifetime", "lifetime energy", "cumulative energy",
        "energyreal_wac_sum_produced", "day_energy", "energy_today",
        "eday", "e_day", "ac_energy", "total_energy_generated",
    ],
    "poa_irradiance": [
        "poa", "poa irradiance", "plane of array", "tilted irradiance",
        "gpoa", "g_poa", "isinim", "panel isinimi", "egik isinim",
        "einstrahlung", "irradiancia", "pyranometer tilted",
        # Marka referansı
        "irradiation", "irradiance_poa", "gti", "g_tilted",
        "poa_global", "poa global", "irradiance tilted",
        # DİKKAT: 'ghi', 'global horizontal' BURAYA EKLENMEZ (bkz. modül docstring)
    ],
    "ghi": [
        "ghi", "global horizontal", "horizontal irradiance",
        "yatay isinim", "global isinim", "pyranometer horizontal",
        "g_horizontal", "horizontal_irradiance", "irradiance_ghi",
        "solar_ghi", "shortwave_radiation",
    ],
    "temp_ambient": [
        "ambient", "ambient temperature", "air temperature", "t_amb",
        "tamb", "ortam sicakligi", "hava sicakligi", "dis sicaklik",
        "umgebungstemperatur", "temperatura ambiente", "temp",
        # Marka referansı
        "ambient_temperature", "outdoor_temp", "environment temp",
        "t_ambient", "air_temp",
    ],
    "temp_module": [
        "module temperature", "panel temperature", "cell temperature",
        "t_mod", "tmod", "modul sicakligi", "panel sicakligi",
        "back sheet temperature", "bom temperature",
        # Marka referansı
        "module_temp", "panel_temp", "t_module", "temp_module",
        "backsheet_temp", "cell_temp", "pv_temp",
    ],
    "wind_speed": [
        "wind", "wind speed", "ws", "ruzgar", "ruzgar hizi",
        "windgeschwindigkeit", "velocidad del viento",
        # Marka referansı
        "wind_speed", "windspeed", "ws_10m", "wind_ms",
    ],
}

#: Birim/parantez eklerini soyan desen: "Active Power(kW)" → "active power"
_UNIT_SUFFIX = re.compile(r"[\(\[\{].*?[\)\]\}]")

#: Fuzzy eşleşme eşiği (0-100). Marka biçim varyantlarını yakalar
#: ("AC_POWER" ↔ "ac power"), anlamsal çeviri yapmaz.
_FUZZY_THRESHOLD = 88

# rapidfuzz yoksa difflib'e düş
try:
    from rapidfuzz import fuzz as _rapidfuzz
    def _fuzzy_score(a: str, b: str) -> float:
        return _rapidfuzz.ratio(a, b)
except ImportError:
    from difflib import SequenceMatcher
    def _fuzzy_score(a: str, b: str) -> float:
        return SequenceMatcher(None, a, b).ratio() * 100.0


def normalize_name(name: str) -> str:
    """Kolon adını karşılaştırma formuna indirger.

    Küçük harf, Türkçe/aksanlı karakterler sadeleştirilir (İ→i, ş→s),
    birim ekleri ve fazla boşluklar atılır, alt çizgi boşluğa çevrilir.
    """
    s = str(name)
    s = _UNIT_SUFFIX.sub(" ", s)
    s = s.replace("_", " ").replace("-", " ").replace(".", " ")
    # Türkçe özel: 'ı' aksan ayrıştırmasında kaybolur, önce elle çevir
    s = s.replace("ı", "i").replace("İ", "i")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", s).strip().lower()


def _match_score(col_norm: str, synonyms: list[str]) -> float:
    """Eşleşme gücü: tam=1.0, kelime sınırlı içerme=0.8, düz içerme=0.6,
    fuzzy yedek=0.5 (biçim varyantı yakalar)."""
    for syn in synonyms:
        if col_norm == syn:
            return 1.0
    for syn in synonyms:
        if re.search(rf"\b{re.escape(syn)}\b", col_norm):
            return 0.8
    for syn in synonyms:
        if syn in col_norm and len(syn) >= 4:
            return 0.6
    # Fuzzy yedek — sadece biçim varyantları için (case, underscore, birim)
    best_fuzzy = 0.0
    for syn in synonyms:
        if len(syn) < 4:
            continue
        s = _fuzzy_score(col_norm, syn)
        if s > best_fuzzy:
            best_fuzzy = s
    return 0.5 if best_fuzzy >= _FUZZY_THRESHOLD else 0.0


def _content_check(series: pd.Series, field: str) -> float:
    """İçerik iddiaya uyuyor mu? 0-1 arası çarpan döner."""
    sample = series.dropna().head(50)
    if sample.empty:
        return 0.5
    if field == "timestamp":
        from .transform import _parse_datetime_robust
        return float(_parse_datetime_robust(sample).notna().mean())
    # Sayısal alanlar: ondalık virgül ihtimaline karşı çevirip dene
    as_num = pd.to_numeric(
        sample.astype(str).str.replace(",", ".", regex=False), errors="coerce"
    )
    return float(as_num.notna().mean())


def suggest_mapping(df: pd.DataFrame) -> tuple[ColumnMapping, list[str]]:
    """Kolon eşlemesi önerir.

    Her kanonik alan için en yüksek skorlu kolon seçilir; skor =
    isim eşleşmesi × içerik doğrulaması. Bir kolon yalnızca bir alana
    eşlenir (en güçlü iddia kazanır).

    Returns:
        (ColumnMapping, eşlenemeyen kolonların listesi)

    Raises:
        ValueError: timestamp veya güç/enerji kaynağı bulunamazsa —
            bu durumda UI kullanıcıdan manuel eşleme istemelidir.
    """
    candidates: list[tuple[float, str, str]] = []  # (skor, alan, kolon)
    for col in df.columns:
        col_norm = normalize_name(col)
        for field, syns in SYNONYMS.items():
            name_score = _match_score(col_norm, syns)
            if name_score == 0.0:
                continue
            score = name_score * max(_content_check(df[col], field), 0.1)
            if score > 0.10:  # fuzzy yedeğine izin vermek için eşiği düşürdük
                candidates.append((score, field, str(col)))

    # Güçlü iddialar önce; her alan ve her kolon en fazla bir kez
    candidates.sort(reverse=True)
    assigned_fields: dict[str, tuple[str, float]] = {}
    used_columns: set[str] = set()
    for score, field, col in candidates:
        if field in assigned_fields or col in used_columns:
            continue
        assigned_fields[field] = (col, round(score, 2))
        used_columns.add(col)

    if "timestamp" not in assigned_fields:
        raise ValueError(
            "Zaman kolonu otomatik bulunamadı. "
            f"Mevcut kolonlar: {list(df.columns)}"
        )
    if "power" not in assigned_fields and "energy" not in assigned_fields:
        raise ValueError(
            "Güç veya enerji kolonu otomatik bulunamadı. "
            f"Mevcut kolonlar: {list(df.columns)}"
        )

    mapping = ColumnMapping(
        timestamp=assigned_fields["timestamp"][0],
        power=assigned_fields.get("power", (None,))[0],
        energy=assigned_fields.get("energy", (None,))[0],
        poa_irradiance=assigned_fields.get("poa_irradiance", (None,))[0],
        temp_ambient=assigned_fields.get("temp_ambient", (None,))[0],
        temp_module=assigned_fields.get("temp_module", (None,))[0],
        wind_speed=assigned_fields.get("wind_speed", (None,))[0],
        ghi=assigned_fields.get("ghi", (None,))[0],
        confidence={f: s for f, (_, s) in assigned_fields.items()},
    )
    unmapped = [str(c) for c in df.columns if str(c) not in used_columns]
    return mapping, unmapped