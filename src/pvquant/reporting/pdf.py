"""Tek sayfa A4 yönetici özeti — ReportLab canvas, mm hassasiyetli bant düzeni.

BANT HARİTASI (A4 210×297, kenar 12mm, kullanılabilir genişlik 186mm):
    12–34   Header: marka + rapor başlığı + santral | sağ: dönem/koşu/mod
    36–62   KPI şeridi: 4 kart (Toplam P50 · P10–P90 · Kapasite F. · Güven)
    66–128  Grafikler: sol günlük barlar 91×60 · sağ tipik gün 91×60
    132–164 Kalibrasyon notları (amber kare madde imleri; en çok 4 satır)
    166–278 Metadata kutusu: santral + model + kalibrasyon çift kolon
    283–285 Footer: IEC/P90 dipnotu + üretim damgası + sayfa

Gömme tekniği: matplotlib Figure → PNG 300dpi (BytesIO) → ImageReader →
canvas.drawImage. 300 dpi, 91mm genişlikte ~1075 px = baskıda pikselsiz.
"""
from __future__ import annotations

from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as rl_canvas

from .charts import fig_gunluk_barlar, fig_tipik_gun, fig_to_png
from .styles import RENK, TIPO, pdf_fontlarini_kaydet

SAYFA_W, SAYFA_H = A4          # pt
KENAR = 12 * mm
IC_W = SAYFA_W - 2 * KENAR


def _y(mm_ustten: float) -> float:
    """Üstten mm → ReportLab pt (alt-orijinli)."""
    return SAYFA_H - mm_ustten * mm


def _hex(c: rl_canvas.Canvas, hexrenk: str):
    c.setFillColor(hexrenk)
    c.setStrokeColor(hexrenk)


def build_pdf(ctx) -> bytes:
    F, FB = pdf_fontlarini_kaydet()
    buf = BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"PVQuant — {ctx.plant_name} 7 Günlük Tahmin")

    _header(c, ctx, F, FB)
    _kpi_seridi(c, ctx, F, FB)
    _grafikler(c, ctx)
    y_son = _notlar(c, ctx, F, FB)
    _metadata(c, ctx, F, FB, y_ust=y_son + 6)
    _footer(c, ctx, F)

    c.showPage()
    c.save()
    return buf.getvalue()


# ---------------------------------------------------------------- bantlar
def _header(c, ctx, F, FB):
    _hex(c, RENK.MARKA)
    c.setFont(FB, 13)
    c.drawString(KENAR, _y(17), "PVQuant")
    _hex(c, RENK.METIN)
    c.setFont(FB, TIPO.BASLIK)
    c.drawString(KENAR, _y(25.5), "7 Günlük Üretim Tahmini")
    c.setFont(F, TIPO.ALT_BASLIK)
    _hex(c, RENK.IKINCIL)
    c.drawString(KENAR, _y(31), ctx.plant_name)

    # sağ blok
    c.setFont(F, 8)
    sag = SAYFA_W - KENAR
    c.drawRightString(sag, _y(16), f"Dönem: {ctx.period_str}")
    c.drawRightString(sag, _y(20.5),
                      f"Koşu: {ctx.run_at_utc:%d.%m.%Y %H:%M} UTC")
    # mod rozeti
    rozet = {"A": "Mod A — saf fizik", "B": "Mod B — kalibre fizik",
             "C": "Mod C — hibrit"}.get(ctx.mode, ctx.mode)
    rw = c.stringWidth(rozet, FB, 8) + 8
    _hex(c, RENK.MARKA)
    c.roundRect(sag - rw, _y(28.8), rw, 4.6 * mm, 3, stroke=1, fill=0)
    c.setFont(FB, 8)
    c.drawRightString(sag - 4, _y(27.2), rozet)

    _hex(c, RENK.MARKA)
    c.setLineWidth(1.1)
    c.line(KENAR, _y(34), SAYFA_W - KENAR, _y(34))


def _kpi_seridi(c, ctx, F, FB):
    kutu_w = IC_W / 4.0
    y_et, y_num, y_alt = _y(41.5), _y(51.5), _y(57)

    def kart(i, etiket, deger, birim, alt=None, renk=RENK.METIN):
        x = KENAR + i * kutu_w
        _hex(c, RENK.IKINCIL)
        c.setFont(FB, TIPO.KPI_ETIKET)
        c.drawString(x, y_et, etiket)
        _hex(c, renk)
        c.setFont(FB, TIPO.KPI)
        c.drawString(x, y_num, deger)
        if birim:
            c.setFont(F, TIPO.KPI_BIRIM)
            _hex(c, RENK.IKINCIL)
            c.drawString(x + c.stringWidth(deger, FB, TIPO.KPI) + 3,
                         y_num, birim)
        if alt:
            c.setFont(F, 7.2)
            _hex(c, RENK.IKINCIL)
            c.drawString(x, y_alt, alt)
        if i > 0:  # soluk ayraç
            _hex(c, RENK.CIZGI)
            c.setLineWidth(0.7)
            c.line(x - 4 * mm, _y(40), x - 4 * mm, _y(58))

    t = f"{ctx.total_mwh:,.1f}".replace(",", ".")
    kart(0, "TOPLAM BEKLENEN ÜRETİM", t, "MWh", f"P50 · {len(ctx.daily_kwh)} gün")

    if ctx.has_band:
        p90, p10 = ctx.band_mwh
        kart(1, "GÜVEN ARALIĞI", f"{p90:,.0f}–{p10:,.0f}".replace(",", "."),
             "MWh", "P90 – P10 (IEA-PVPS)")
    else:
        kart(1, "GÜVEN ARALIĞI", "—", "",
             "Mod C'de P10–P90 eklenir")

    kart(2, "KAPASİTE FAKTÖRÜ", f"%{ctx.capacity_factor_pct:.1f}", "",
         f"özgül verim {ctx.specific_yield:.1f} kWh/kWp")

    if ctx.mape_pct is not None:
        kart(3, "KALİBRASYON İSABETİ", f"%{ctx.mape_pct:.1f}", "MAPE",
             f"sapma %{ctx.deviation_pct:+.2f}" if ctx.deviation_pct is not None else None)
    else:
        kart(3, "KALİBRASYON İSABETİ", "—", "", "doğruluk geçmişi birikiyor")


def _grafikler(c, ctx):
    img_w = 91 * mm
    img_h = 60 * mm
    y_alt_pt = _y(128)
    sol = fig_to_png(fig_gunluk_barlar(ctx))
    sag = fig_to_png(fig_tipik_gun(ctx))
    c.drawImage(ImageReader(sol), KENAR, y_alt_pt, width=img_w, height=img_h,
                preserveAspectRatio=True, anchor="sw")
    c.drawImage(ImageReader(sag), KENAR + 95 * mm, y_alt_pt, width=img_w,
                height=img_h, preserveAspectRatio=True, anchor="sw")


def _notlar(c, ctx, F, FB) -> float:
    """Kalibrasyon notları; döner: bandın bittiği üstten-mm."""
    y0 = 134
    _hex(c, RENK.IKINCIL)
    c.setFont(FB, TIPO.BOLUM)
    c.drawString(KENAR, _y(y0), "KALİBRASYON NOTLARI")
    uyarilar = (ctx.warnings or [])[:4]
    if not uyarilar:
        c.setFont(F, TIPO.GOVDE)
        c.drawString(KENAR, _y(y0 + 6), "Uyarı yok — kalibrasyon temiz.")
        return y0 + 10
    y = y0 + 6
    c.setFont(F, TIPO.GOVDE)
    for u in uyarilar:
        _hex(c, RENK.VURGU)
        c.rect(KENAR, _y(y) , 2.2, 2.2, stroke=0, fill=1)
        _hex(c, RENK.METIN)
        metin = u if len(u) <= 118 else u[:115] + "…"
        c.drawString(KENAR + 4 * mm, _y(y + 0.4), metin)
        y += 5.2
    return y


def _metadata(c, ctx, F, FB, y_ust: float):
    _hex(c, RENK.ZEMIN_SOLUK)
    kutu_h = 34
    c.roundRect(KENAR, _y(y_ust + kutu_h), IC_W, kutu_h * mm, 6,
                stroke=0, fill=1)
    _hex(c, RENK.IKINCIL)
    c.setFont(FB, TIPO.BOLUM)
    c.drawString(KENAR + 4 * mm, _y(y_ust + 6), "SANTRAL VE MODEL")

    sol = [
        ("Kurulu güç", f"{ctx.capacity_kwp:,.0f} kWp".replace(",", ".")),
        ("Konum", f"{ctx.latitude:.2f}, {ctx.longitude:.2f}"),
        ("Eğim / Azimut", f"{ctx.tilt_deg:.0f}° / {ctx.azimuth_deg:.0f}°"),
        ("Saat dilimi", ctx.plant_tz),
    ]
    sag = [
        ("Model", f"{ctx.model_name} ({ctx.model_version})"),
        ("Meteo kaynağı", ctx.meteo_source),
        ("η_BoS / BG",
         f"{ctx.eta_bos:.3f} / {ctx.bg:.3f}" if ctx.eta_bos is not None else "—"),
        ("Şema", f"v{ctx.schema_version}"),
    ]
    y = y_ust + 12
    for (e1, v1), (e2, v2) in zip(sol, sag):
        c.setFont(F, 7.5); _hex(c, RENK.IKINCIL)
        c.drawString(KENAR + 4 * mm, _y(y), e1)
        c.drawString(KENAR + IC_W / 2 + 2 * mm, _y(y), e2)
        c.setFont(FB, 8); _hex(c, RENK.METIN)
        c.drawString(KENAR + 32 * mm, _y(y), v1)
        c.drawString(KENAR + IC_W / 2 + 30 * mm, _y(y), v2)
        y += 5.4


def _footer(c, ctx, F):
    _hex(c, RENK.CIZGI)
    c.setLineWidth(0.7)
    c.line(KENAR, _y(283), SAYFA_W - KENAR, _y(283))
    _hex(c, RENK.IKINCIL)
    c.setFont(F, TIPO.KUCUK)
    c.drawString(KENAR, _y(287),
                 "IEC 61724-1 uyumlu adlandırma · P90: %90 olasılıkla aşılacak değer (IEA-PVPS T13)")
    c.drawRightString(SAYFA_W - KENAR, _y(287),
                      f"PVQuant · {ctx.run_at_utc:%Y-%m-%dT%H:%M}Z · Sayfa 1/1")
