"""Ingestion orkestrasyonu: iki fazlı akış (preview → commit).

UI sihirbazının arka ucu tam olarak bu iki fonksiyondur:

  preview_file(path, plant)
      → algılama + eşleme önerisi + ilk satırların önizlemesi.
        HİÇBİR ŞEY kaydedilmez; kullanıcıya onay ekranı beslenir.
        Otomatik eşleme başarısız olursa MappingFailedError fırlatır
        (kolonlar + örnek satırlar ile) → UI manuel eşleme kurar.

  ingest_file(path, plant, ... onaylanmış kararlar ...)
      → dönüştürme + doğrulama + IngestionResult.
        Sonuç kullanıcıya kalite karnesiyle gösterilir; kullanıcı
        onaylarsa result.to_clean_frame() kalibrasyona gider ve
        result.to_template() şablon olarak saklanır.

Self-healing prensibi (Fable 5, Temmuz 2026):
  İlk format tespiti eşlemeyi çalıştırmazsa pipeline pes etmez —
  başlık satırlarını 0-10 arası ve CSV'de alternatif ayraçları
  tarayıp eşlemeyi başarılı kılan varyantı bulur. "Doğru başlık,
  eşlemeyi çalıştıran satırdır" en güçlü sinyaldir.

Hiçbir şey tutmazsa MappingFailedError fırlatılır — ölü uç yerine
yapılandırılmış istisna, UI kırmızı kutu yerine manuel eşleme kurar.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pandas as pd

from .contracts import (
    ColumnMapping, FileFormat, IngestionResult, TransformSpec,
)
from .detection import DELIMITER_CANDIDATES, detect_file_format
from .mapping import suggest_mapping
from .templates import TemplateStore
from .transform import transform_to_canonical
from .validate import validate


class MappingFailedError(Exception):
    """Otomatik kolon eşleme başarısız oldu.

    UI bunu yakalayıp manuel eşleme ekranı kurar. Ham hata metni
    yerine yapılandırılmış bilgi taşır:

    Attributes:
        columns: Dosyada bulunan tüm kolonlar
        sample_rows: İlk ~10 satır (kullanıcıya gösterilecek)
        file_format: Denenmiş son format (kullanıcı düzeltebilir)
        original_error: Sözlük eşlemesinin ham ValueError'ı
    """

    def __init__(
        self,
        columns: list[str],
        sample_rows: pd.DataFrame,
        file_format: FileFormat,
        original_error: Exception,
    ):
        self.columns = columns
        self.sample_rows = sample_rows
        self.file_format = file_format
        self.original_error = original_error
        super().__init__(
            f"Otomatik kolon eşleme başarısız. Kolonlar: {columns}. "
            f"Manuel eşleme gerekli."
        )


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


def _try_mapping_variants(
    path: Path,
    initial_fmt: FileFormat,
) -> tuple[FileFormat, pd.DataFrame, ColumnMapping, list[str], list[str]]:
    """Self-healing: eşlemeyi başarılı kılan format varyantını bulur.

    Strateji:
      1. Önce initial_fmt ile dene
      2. Excel için: header_row 0-10 arası tara
      3. CSV için: header_row 0-10 × delimiter (,;\t) arası tara
      4. En yüksek isim güveni skorlu eşlemeyi seçen varyant kazanır

    Returns:
        (uygun format, ham df, mapping, unmapped kolonlar, denemenoteları)

    Raises:
        MappingFailedError: hiçbir varyant eşlemeyi çalıştıramazsa
    """
    is_excel = path.suffix.lower() in (".xlsx", ".xls")
    notes: list[str] = []
    best: Optional[tuple[float, FileFormat, pd.DataFrame, ColumnMapping, list[str]]] = None
    last_error: Optional[Exception] = None
    last_read_df: Optional[pd.DataFrame] = None
    last_fmt: FileFormat = initial_fmt

    # Varyant seti oluştur (initial önce)
    variants: list[FileFormat] = [initial_fmt]
    for hr in range(0, 11):
        if is_excel:
            v = FileFormat(
                encoding=initial_fmt.encoding,
                delimiter=initial_fmt.delimiter,
                decimal=initial_fmt.decimal,
                header_row=hr,
                sheet_name=initial_fmt.sheet_name,
                confidence=max(initial_fmt.confidence - 0.1, 0.3),
            )
            if v.header_row != initial_fmt.header_row:
                variants.append(v)
        else:
            for delim in DELIMITER_CANDIDATES:
                v = FileFormat(
                    encoding=initial_fmt.encoding,
                    delimiter=delim,
                    decimal=initial_fmt.decimal,
                    header_row=hr,
                    confidence=max(initial_fmt.confidence - 0.1, 0.3),
                )
                if (v.header_row, v.delimiter) != (
                    initial_fmt.header_row, initial_fmt.delimiter
                ):
                    variants.append(v)

    for i, fmt in enumerate(variants):
        try:
            df = _read_raw(path, fmt)
            df.columns = [str(c).strip() for c in df.columns]
        except Exception as e:
            last_error = e
            continue

        last_read_df = df
        last_fmt = fmt

        try:
            mapping, unmapped = suggest_mapping(df)
        except ValueError as e:
            last_error = e
            continue

        # Skor: eşlenen alanların ortalama güveni + kolon bonusu
        if mapping.confidence:
            score = (
                sum(mapping.confidence.values()) / len(mapping.confidence)
                + 0.05 * len(mapping.confidence)
            )
        else:
            score = 0.0

        if best is None or score > best[0]:
            best = (score, fmt, df, mapping, unmapped)
            if i > 0:
                notes.append(
                    f"Otomatik format düzeltme: başlık satırı "
                    f"{fmt.header_row + 1}"
                    + (f", ayraç {repr(fmt.delimiter)}" if not is_excel else "")
                )
            # Erken çıkış: çok güçlü eşleme
            if score >= 1.10:
                break

    if best is None:
        # Hiçbir varyant eşleme kuramadı → MappingFailedError
        sample = (last_read_df.head(10) if last_read_df is not None
                  else pd.DataFrame())
        columns = list(map(str, last_read_df.columns)) if last_read_df is not None else []
        raise MappingFailedError(
            columns=columns,
            sample_rows=sample,
            file_format=last_fmt,
            original_error=last_error or ValueError("Bilinmeyen eşleme hatası"),
        )

    _, fmt, df, mapping, unmapped = best
    return fmt, df, mapping, unmapped, notes


def preview_file(
    path: str | Path,
    template_store: TemplateStore | None = None,
) -> IngestionPreview:
    """Faz 1: algıla, eşle, öner — kaydetme.

    Şablon deposu verildiyse önce şablon eşleşmesi denenir; bulunan
    şablon otomatik algılamayı ezer (ama yine kullanıcı onayına gider).

    Şablon yoksa self-healing devreye girer (bkz. _try_mapping_variants).

    Raises:
        MappingFailedError: otomatik eşleme kurulamazsa
            (UI manuel eşleme ekranı kurmalı)
    """
    path = Path(path)
    fmt = detect_file_format(path)

    # 1) Şablon eşleşmesi
    if template_store is not None:
        try:
            raw_first = _read_raw(path, fmt)
            raw_first.columns = [str(c).strip() for c in raw_first.columns]
            hit = template_store.find_matching(list(raw_first.columns))
        except Exception:
            hit = None
        if hit is not None:
            matched_name, tpl = hit
            fmt, mapping, _ = TemplateStore.parse(tpl)
            raw = _read_raw(path, fmt)
            raw.columns = [str(c).strip() for c in raw.columns]
            return IngestionPreview(
                file_format=fmt, mapping=mapping, unmapped_columns=[],
                sample_rows=raw.head(10), matched_template=matched_name,
                notes=[f"'{matched_name}' şablonu otomatik eşleşti."],
            )

    # 2) Self-healing eşleme (MappingFailedError yükseltebilir)
    fmt, raw, mapping, unmapped, variant_notes = _try_mapping_variants(path, fmt)

    notes = list(variant_notes)
    if fmt.confidence < 0.7 and not variant_notes:
        notes.append(
            "Format algılama güveni düşük — ayraç/başlık satırını kontrol edin."
        )
    low_conf = [f for f, c in mapping.confidence.items() if c < 0.6]
    if low_conf:
        notes.append(
            f"Düşük güvenli eşlemeler: {', '.join(low_conf)} — onaylayın."
        )

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
            tarafından düzeltilmiş) kararlar. None ise otomatik
            (self-healing dahil).

    Returns:
        IngestionResult — data, karar izleri ve kalite karnesi.

    Raises:
        MappingFailedError: file_format/mapping None ve otomatik
            eşleme kurulamazsa
    """
    path = Path(path)

    if file_format is None or mapping is None:
        initial = detect_file_format(path)
        fmt, raw, auto_mapping, _, _ = _try_mapping_variants(path, initial)
        fmt = file_format or fmt
        mapping = mapping or auto_mapping
    else:
        fmt = file_format
        raw = _read_raw(path, fmt)
        raw.columns = [str(c).strip() for c in raw.columns]

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