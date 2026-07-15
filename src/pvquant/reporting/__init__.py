"""pvquant.reporting — 7 günlük tahmin raporu üreticileri.

Kullanım (frontend/raporlar.py):
    from pvquant.reporting import from_results, build_pdf, build_excel, build_json
    ctx = from_results(forecast_result, calibration_result, plant_name=..., mode=...)
    pdf_bytes  = build_pdf(ctx)
    xlsx_bytes = build_excel(ctx)
    json_str   = build_json(ctx)
"""
from .contracts import ReportContext, apply_hybrid_session, from_results
from .pdf import build_pdf
from .excel import build_excel
from .schemas import build_json, ForecastReport

__all__ = ["ReportContext", "apply_hybrid_session", "from_results", "build_pdf", "build_excel",
           "build_json", "ForecastReport"]
