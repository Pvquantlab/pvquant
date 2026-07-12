"""PVQuant ingestion katmanı — ham kullanıcı dosyasından temiz SCADA'ya.

Genel kullanım (iki fazlı, UI sihirbazına uygun):

    >>> from pvquant.io.ingestion import preview_file, ingest_file, TemplateStore
    >>> store = TemplateStore("ingestion_templates")
    >>> pv = preview_file("upload.csv", template_store=store)
    >>> # ... kullanıcı pv.mapping'i onaylar/düzeltir ...
    >>> result = ingest_file(
    ...     "upload.csv", capacity_kwp=4514,
    ...     latitude=37.87, longitude=32.49,
    ...     source_timezone="Europe/Istanbul",
    ...     file_format=pv.file_format, mapping=pv.mapping,
    ... )
    >>> print(result.report.summary_tr())
    >>> clean = result.to_clean_frame()      # → HistoricalData.data
    >>> store.save("fusionsolar_v1", result.to_template())
"""
from .contracts import (
    ColumnMapping,
    FileFormat,
    IngestionResult,
    QualityReport,
    RowFlag,
    TransformSpec,
)
from .pipeline import IngestionPreview, ingest_file, preview_file
from .templates import TemplateStore

__all__ = [
    "ColumnMapping",
    "FileFormat",
    "IngestionPreview",
    "IngestionResult",
    "QualityReport",
    "RowFlag",
    "TemplateStore",
    "TransformSpec",
    "ingest_file",
    "preview_file",
]