"""Aşama 2 — Kolon eşleme.

Dosya kolonlarını kanonik alanlara (timestamp, power, energy, ...)
eşler. İki katmanlı strateji:

  1. Sözlük eşleşmesi: io/scada.py'deki COLUMN_ALIASES'ın genişletilmiş,
     çok dilli hali. Tam eşleşme > normalize eşleşme > içerme.
  2. İçerik doğrulaması: aday kolonun İÇERİĞİ de iddiaya uymalı —
     "timestamp" diye eşlenen kolon gerçekten tarihe çevrilebiliyor mu,
     "power" eşlenen kolon sayısal mı? İçerik tutmuyorsa güven düşer.

Sözlükte karşılık bulunamayan kolonlar `unmapped` listesinde döner;
UI bunları kullanıcıya "elle eşle veya yoksay" diye sunar. (İleride
bu listeye LLM destekli öneri eklenebilir — bkz. entegrasyon rehberi.)
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
    ],
    "power": [
        "power", "active power", "ac power", "ac active power", "p_ac",
        "pac", "guc", "aktif guc", "cikis gucu", "uretim gucu",
        "leistung", "wirkleistung", "potencia", "puissance",
        "grid power", "output power", "total active power", "power kw",
    ],
    "energy": [
        "energy", "yield", "production", "generation", "enerji",
        "uretim", "gunluk uretim", "toplam uretim", "ertrag",
        "energia", "total yield", "daily yield", "inverter yield",
        "feed-in energy", "on-grid energy", "kwh",
    ],
    "poa_irradiance": [
        "poa", "poa irradiance", "plane of array", "tilted irradiance",
        "gpoa", "g_poa", "isinim", "panel isinimi", "egik isinim",
        "einstrahlung", "irradiancia", "pyranometer tilted",
    ],
    "ghi": [
        "ghi", "global horizontal", "horizontal irradiance",
        "yatay isinim", "global isinim", "pyranometer horizontal",
    ],
    "temp_ambient": [
        "ambient", "ambient temperature", "air temperature", "t_amb",
        "tamb", "ortam sicakligi", "hava sicakligi", "dis sicaklik",
        "umgebungstemperatur", "temperatura ambiente", "temp",
    ],
    "temp_module": [
        "module temperature", "panel temperature", "cell temperature",
        "t_mod", "tmod", "modul sicakligi", "panel sicakligi",
        "back sheet temperature", "bom temperature",
    ],
    "wind_speed": [
        "wind", "wind speed", "ws", "ruzgar", "ruzgar hizi",
        "windgeschwindigkeit", "velocidad del viento",
    ],
}

#: Birim/parantez eklerini soyan desen: "Active Power(kW)" → "active power"
_UNIT_SUFFIX = re.compile(r"[\(\[\{].*?[\)\]\}]")


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
    """Eşleşme gücü: tam=1.0, kelime sınırlı içerme=0.8, düz içerme=0.6."""
    for syn in synonyms:
        if col_norm == syn:
            return 1.0
    for syn in synonyms:
        if re.search(rf"\b{re.escape(syn)}\b", col_norm):
            return 0.8
    for syn in synonyms:
        if syn in col_norm and len(syn) >= 4:
            return 0.6
    return 0.0


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
            if score > 0.15:
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