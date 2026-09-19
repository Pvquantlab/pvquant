"""pvquant.reporting — tahmin raporu üreticileri (Excel/JSON + bağlam).

Kullanım (report_service.uret):
    from pvquant.reporting import from_results, build_excel, build_json
    ctx = from_results(forecast_result, calibration_result, plant_name=..., mode=...)
    xlsx_bytes = build_excel(ctx)
    json_str   = build_json(ctx)

v2.344 (E.4): build_pdf (reportlab yönetici özeti) EMEKLİ — PDF'ler artık
16 sayfalık HTML/WeasyPrint motorundan çıkar (reporting/kopru.py); yönetici
özeti o motorun 6 sayfalık seçkisidir (report_html_service.OZET_SECKISI).
"""
from .contracts import ReportContext, apply_hybrid_session, from_results
from .excel import build_excel
from .schemas import build_json, ForecastReport

__all__ = ["ReportContext", "apply_hybrid_session", "from_results", "build_excel",
           "build_json", "ForecastReport"]
