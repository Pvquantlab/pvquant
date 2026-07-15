"""Rapor grafikleri — saf fonksiyonlar: ReportContext → matplotlib Figure.

PDF'e gömme: fig → BytesIO(PNG, 300 dpi) → reportlab drawImage.
300 dpi: 90 mm genişlikte ~1063 px; lazer baskıda pikselsiz, dosya ~150-300 KB.
"""
from __future__ import annotations

from io import BytesIO

import matplotlib.pyplot as plt
import numpy as np

from .styles import RENK, sayi_tr, tema_uygula


def fig_to_png(fig, dpi: int = 300) -> BytesIO:
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight",
                pad_inches=0.02, facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf


def fig_gunluk_barlar(ctx) -> plt.Figure:
    """Sol grafik: 7 günlük enerji barları; en düşük gün amber (bakım sinyali)."""
    tema_uygula()
    d = ctx.daily_kwh / 1000.0  # MWh
    fig, ax = plt.subplots(figsize=(3.55, 2.35))
    renkler = [RENK.MARKA] * len(d)
    renkler[int(np.argmin(d.values))] = RENK.VURGU
    ax.bar(range(len(d)), d.values, color=renkler, width=0.62, zorder=3)
    for i, v in enumerate(d.values):
        ax.text(i, v, sayi_tr(v, 1), ha="center", va="bottom",
                fontsize=7, color=RENK.METIN)
    if ctx.has_band:
        p90 = ctx.daily_p90.values / 1000.0
        ax.hlines(p90, np.arange(len(d)) - 0.31, np.arange(len(d)) + 0.31,
                  color=RENK.METIN, linewidth=1.0, zorder=4)
    ax.set_xticks(range(len(d)))
    ax.set_xticklabels([f"{t:%d %b}" for t in d.index], rotation=0)
    ax.set_title("Günlük üretim")
    ax.set_ylabel("MWh")
    ax.set_ylim(0, d.max() * 1.18)
    ax.margins(x=0.02)
    fig.tight_layout()
    return fig


def fig_tipik_gun(ctx) -> plt.Figure:
    """Sağ grafik: 7 günün saat-bazlı ortalama profili + gün-içi min/maks bandı."""
    tema_uygula()
    h = ctx.hourly.tz_convert(ctx.plant_tz)
    grp = h["p50_kw"].groupby(h.index.hour)
    ort, alt, ust = grp.mean(), grp.min(), grp.max()
    fig, ax = plt.subplots(figsize=(3.55, 2.35))
    ax.fill_between(ort.index, alt, ust, color=RENK.MARKA, alpha=0.22,
                    linewidth=0)
    ax.plot(ort.index, ort.values, color=RENK.MARKA, linewidth=1.9)
    tepe_s = int(ort.idxmax())
    ax.plot([tepe_s], [ort.max()], "o", ms=3.5, color=RENK.MARKA, zorder=5)
    ax.annotate(f"tepe {sayi_tr(ort.max(), 0)} kW",
                xy=(tepe_s, ort.max()), xytext=(7, -3),
                textcoords="offset points", ha="left", va="top",
                fontsize=7, color=RENK.METIN, fontweight="bold")
    ax.set_title("Tipik gün profili")
    ax.set_ylabel("kW")
    ax.set_xlabel("saat (yerel)")
    ax.set_xticks([0, 6, 12, 18, 23])
    ax.set_xlim(0, 23)
    ax.set_ylim(bottom=0)
    fig.tight_layout()
    return fig
