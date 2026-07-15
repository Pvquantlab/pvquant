"""PVQuant rapor stil katmanı — renk, tipografi, matplotlib teması, font kaydı.

Tasarım dili: beyaz zemin, tek marka rengi (petrol yeşili), disiplinli
nötr griler, amber yalnız vurguda. Tipografi DejaVu Sans — Türkçe tam
destek + matplotlib ile birlikte gelir (dağıtımda ek font dosyası yok).
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt


class RENK:
    METIN = "#111827"
    IKINCIL = "#6B7280"
    CIZGI = "#E5E7EB"
    ZEMIN_SOLUK = "#F8FAFC"
    MARKA = "#0F6E56"
    VURGU = "#F59E0B"
    POZITIF = "#15803D"
    NEGATIF = "#B91C1C"
    GECE = "#F3F4F6"


class TIPO:
    BASLIK = 19
    ALT_BASLIK = 9.5
    KPI = 24
    KPI_BIRIM = 8
    KPI_ETIKET = 6.8
    BOLUM = 8.0
    GOVDE = 8.5
    KUCUK = 6.8


def dejavu_yollari() -> dict[str, str]:
    """matplotlib paketindeki DejaVu TTF yolları (ReportLab'e gömmek için)."""
    kok = Path(fm.findfont("DejaVu Sans")).parent
    return {
        "normal": str(kok / "DejaVuSans.ttf"),
        "bold": str(kok / "DejaVuSans-Bold.ttf"),
    }


def pdf_fontlarini_kaydet() -> tuple[str, str]:
    """ReportLab'e DejaVu ailesini kaydeder; (normal, bold) adlarını döner."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    y = dejavu_yollari()
    if "PVQ" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("PVQ", y["normal"]))
        pdfmetrics.registerFont(TTFont("PVQ-Bold", y["bold"]))
    return "PVQ", "PVQ-Bold"


def tema_uygula() -> None:
    """Yayın-infografiği matplotlib teması (rapor grafikleri için)."""
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 8.5,
        "text.color": RENK.METIN,
        "axes.edgecolor": RENK.CIZGI,
        "axes.linewidth": 0.8,
        "axes.labelcolor": RENK.IKINCIL,
        "axes.titlesize": 10,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.titlecolor": RENK.METIN,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "grid.color": RENK.CIZGI,
        "grid.linewidth": 0.6,
        "xtick.color": RENK.IKINCIL,
        "ytick.color": RENK.IKINCIL,
        "xtick.labelsize": 7.5,
        "ytick.labelsize": 7.5,
        "figure.dpi": 100,
        "savefig.dpi": 300,
        "legend.frameon": False,
        "axes.unicode_minus": False,
    })
