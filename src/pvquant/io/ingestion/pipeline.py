"""Ingestion orkestrasyonu: iki fazlı akış (preview → commit).

UI sihirbazının arka ucu tam olarak bu iki fonksiyondur:

  preview_file(path, plant)
      → algılama + eşleme önerisi + ilk satırların önizlemesi.
        HİÇBİR ŞEY kaydedilmez; kullanıcıya onay ekranı beslenir.

  ingest_file(path, plant, ... onaylanmış kararlar ...)
      → dönüştürme + doğrulama + IngestionResult.
        Sonuç kullanıcıya kalite karnesiyle gösterilir; kullanıcı
        onaylarsa result.to_clean_frame() kalibrasyona gider ve
        result.to_template() şablon olarak saklanır.

CLI/script kullanımı için ikisini arka arkaya çağırmak da mümkündür
(varsayılanlara güvenerek).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pandas as pd

from .contracts import (
    ColumnMapping, FileFormat, IngestionResult, TransformSpec,
)
from .detection import detect_file_format
from .mapping import suggest_mapping
from .templates import TemplateStore
from .transform import transform_to_canonical
from .validate import validate


@dataclass
class IngestionPreview:
    """Onay ekranını besleyen paket."""

    file_format: FileFormat
    mapping: ColumnMapping
    unmapped_columns: list[str]
    sample_rows: pd.DataFrame          # ilk ~10 satır, ham haliyle
    matched_template: Optional[str] = None
    notes: list[str] = field(default_factory=list)


def _read_raw(path: Path, fmt: FileFormat) -> pd.DataFrame:
    """Formata göre ham DataFrame okur (dönüşümsüz, her şey string)."""
    if path.suffix.lower() in (".xlsx", ".xls"):
        return pd.read_excel(path, sheet_name=fmt.sheet_name or 0,
                             header=fmt.header_row, dtype=str)
    return pd.read_csv(
        path, encoding=fmt.encoding, delimiter=fmt.delimiter,
        header=fmt.header_row, dtype=str, skip_blank_lines=True,
    )


def preview_file(
    path: str | Path,
    template_store: TemplateStore | None = None,
) -> IngestionPreview:
    """Faz 1: algıla, eşle, öner — kaydetme.

    Şablon deposu verildiyse önce şablon eşleşmesi denenir; bulunan
    şablon otomatik algılamayı ezer (ama yine kullanıcı onayına gider).
    """
    path = Path(path)
    fmt = detect_file_format(path)
    raw = _read_raw(path, fmt)
    raw.columns = [str(c).strip() for c in raw.columns]

    matched_name: Optional[str] = None
    notes: list[str] = []

    if template_store is not None:
        hit = template_store.find_matching(list(raw.columns))
        if hit is not None:
            matched_name, tpl = hit
            fmt, mapping, _ = TemplateStore.parse(tpl)
            raw = _read_raw(path, fmt)  # şablonun formatıyla yeniden oku
            raw.columns = [str(c).strip() for c in raw.columns]
            notes.append(f"'{matched_name}' şablonu otomatik eşleşti.")
            return IngestionPreview(
                file_format=fmt, mapping=mapping, unmapped_columns=[],
                sample_rows=raw.head(10), matched_template=matched_name,
                notes=notes,
            )

    mapping, unmapped = suggest_mapping(raw)
    if fmt.confidence < 0.7:
        notes.append(
            "Format algılama güveni düşük — ayraç/başlık satırını kontrol edin."
        )
    low_conf = [f for f, c in mapping.confidence.items() if c < 0.6]
    if low_conf:
        notes.append(f"Düşük güvenli eşlemeler: {', '.join(low_conf)} — onaylayın.")

    return IngestionPreview(
        file_format=fmt, mapping=mapping, unmapped_columns=unmapped,
        sample_rows=raw.head(10), notes=notes,
    )


def ingest_file(
    path: str | Path,
    capacity_kwp: float,
    latitude: float,
    longitude: float,
    source_timezone: str,
    file_format: FileFormat | None = None,
    mapping: ColumnMapping | None = None,
) -> IngestionResult:
    """Faz 2: onaylanmış kararlarla dönüştür + doğrula.

    Args:
        path: Ham dosya.
        capacity_kwp: DC kurulu güç (birim tespiti + kapasite kuralı).
        latitude, longitude: gece üretimi kuralı için.
        source_timezone: Dosyadaki zamanların dilimi (IANA, örn.
            "Europe/Istanbul" veya "UTC"). Sihirbazda kullanıcı seçer;
            varsayılan olarak santralin dilimi önerilir.
        file_format, mapping: Preview'dan gelen (gerekirse kullanıcı
            tarafından düzeltilmiş) kararlar. None ise otomatik.

    Returns:
        IngestionResult — data, karar izleri ve kalite karnesi.
    """
    path = Path(path)
    fmt = file_format or detect_file_format(path)
    raw = _read_raw(path, fmt)
    raw.columns = [str(c).strip() for c in raw.columns]

    if mapping is None:
        mapping, _ = suggest_mapping(raw)

    canonical, spec, dst_flags = transform_to_canonical(
        raw, mapping,
        capacity_kwp=capacity_kwp,
        source_timezone=source_timezone,
        decimal=fmt.decimal,
    )
    flagged, report = validate(
        canonical,
        capacity_kwp=capacity_kwp,
        latitude=latitude,
        longitude=longitude,
        dst_flags=dst_flags,
    )
    return IngestionResult(
        data=flagged, file_format=fmt, mapping=mapping,
        transform=spec, report=report,
    )