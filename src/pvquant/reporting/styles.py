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


# ---------------------------------------------------------------- Türkçe format
AYLAR_TR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
            "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]


def sayi_tr(x: float, ondalik: int = 1) -> str:
    """Türkçe sayı biçimi: binlik ayracı nokta, ondalık virgül.
    4514 -> '4.514' · 218.9 -> '218,9' · 1234.5 -> '1.234,5'
    (Önceki tek-replace yaklaşımı binlikli ondalıklarda '1.234.5'
    üretiyordu — bu yardımcı o hata sınıfını kapatır.)"""
    metin = f"{x:,.{ondalik}f}"
    return metin.replace(",", "\u00a7").replace(".", ",").replace("\u00a7", ".")


BANT_BASLIK = "P10-P90 (kWh)"       # v2.71-B: baslik ile hucre tek kaynakta


def bant_araligi(alt: float, ust: float) -> str:
    """P10-P90 bandinin hucre metni - sira BANT_BASLIK ile ayni.

    v2.71-B: onceki halinde baslik tahminler.py'de 'P90-P10' yaziyor,
    hucre ise P10 -> P90 sirasiyla basiliyordu (ekranda P50=30.356 iken
    '29.076 - 33.287'). Iki yer ayri tanimliydi; ikisi de buradan gelir.
    """
    return f"{sayi_tr(alt, 0)} - {sayi_tr(ust, 0)}"

def donem_tr(t1, t2) -> str:
    """Dönem metni, Türkçe ay adlarıyla:
    aynı ay  -> '14 – 21 Temmuz 2026'
    ay geçişi-> '14 Temmuz – 3 Ağustos 2026'
    yıl geçişi-> '28 Aralık 2026 – 3 Ocak 2027'"""
    a1, a2 = AYLAR_TR[t1.month - 1], AYLAR_TR[t2.month - 1]
    if t1.year == t2.year and t1.month == t2.month:
        return f"{t1.day} – {t2.day} {a1} {t1.year}"
    if t1.year == t2.year:
        return f"{t1.day} {a1} – {t2.day} {a2} {t1.year}"
    return f"{t1.day} {a1} {t1.year} – {t2.day} {a2} {t2.year}"
