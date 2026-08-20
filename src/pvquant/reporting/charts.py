"""Rapor grafikleri — saf fonksiyonlar: ReportContext → matplotlib Figure.

PDF'e gömme: fig → BytesIO(PNG, 300 dpi) → reportlab drawImage.
300 dpi: 90 mm genişlikte ~1063 px; lazer baskıda pikselsiz, dosya ~150-300 KB.
"""
from __future__ import annotations

from io import BytesIO

import matplotlib.pyplot as plt
import numpy as np

from .styles import AYLAR_TR, RENK, sayi_tr, tema_uygula


def gun_tr(t) -> str:
    """Eksen etiketi: '23 Tem' — strftime %b DEGIL (locale Ingilizce'ye
    dusuyordu: '23 Jul'). Defter borcu 'PDF eksen etiketleri' burada
    kapandi; yeni grafikler de bunu kullanir."""
    return f"{t.day} {AYLAR_TR[t.month - 1][:3]}"


def fig_to_png(fig, dpi: int = 300) -> BytesIO:
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight",
                pad_inches=0.02, facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf


def fig_karne(ctx) -> plt.Figure:
    """S4 grafigi (sartname §6 paleti): gunluk WMAPE 0-24s (amber) ve
    24-72s (koyu amber), naif referans gri KESIKLI. Olculmeyen gun tam
    tarih araligina reindex ile NaN kalir -> cizgi KIRILIR (sifir yok)."""
    import pandas as pd
    tema_uygula()
    k = ctx.karne.copy()
    k["date"] = pd.to_datetime(k["date"])
    tam = pd.date_range(k["date"].min(), k["date"].max(), freq="D")

    def seri(kova: str, kolon: str):
        s = k[k["horizon_bucket"] == kova]
        if len(s) == 0 or kolon not in s.columns:
            return None
        return s.set_index("date")[kolon].reindex(tam)

    w0, w1 = seri("0-24", "mape"), seri("24-72", "mape")
    nf = seri("0-24", "naive_wmape")
    fig, ax = plt.subplots(figsize=(7.3, 2.75))
    if nf is not None and nf.notna().any():
        ax.plot(tam, nf, color=RENK.IKINCIL, lw=1.2, ls="--",
                dashes=(4, 2.5), label="naif referans (0–24 s)", zorder=3)
    if w0 is not None and w0.notna().any():
        ax.plot(tam, w0, color=RENK.VURGU, lw=1.9, marker="o", ms=3.4,
                label="0–24 s", zorder=5)
    if w1 is not None and w1.notna().any():
        ax.plot(tam, w1, color="#B45309", lw=1.4, marker="s", ms=2.8,
                label="24–72 s", zorder=4)
    ax.set_title("Günlük WMAPE — tahmin vs gerçekleşen üretim")
    ax.set_ylabel("WMAPE %")
    ust = max(x.max() for x in (w0, w1, nf) if x is not None and x.notna().any())
    ax.set_ylim(0, float(ust) * 1.28)   # lejant tepe payi
    adim = max(1, len(tam) // 8)
    ax.set_xticks(tam[::adim])
    ax.set_xticklabels([gun_tr(t) for t in tam[::adim]])
    ax.margins(x=0.015)
    ax.legend(frameon=False, fontsize=7.2, ncol=3, loc="upper left")
    fig.tight_layout()
    return fig


def fig_gunluk_barlar(ctx) -> plt.Figure:
    """Günlük enerji barları — N güne ölçeklenir (v2.96 duruşma dersi:
    7 gün için çizilmiş düzen 16 barda etiketleri çarpıştırıyordu).
    >8 günde: etiketler seyreltilir, değer yalnız min/maks bara yazılır.
    En düşük gün amber (bakım sinyali); Mod C'de P10–P90 bant çizgileri."""
    tema_uygula()
    d = ctx.daily_kwh / 1000.0  # MWh
    n = len(d)
    fig, ax = plt.subplots(figsize=(7.3, 2.55) if n > 8 else (3.55, 2.35))
    renkler = [RENK.MARKA] * n
    i_min = int(np.argmin(d.values))
    renkler[i_min] = RENK.VURGU
    ax.bar(range(n), d.values, color=renkler, width=0.62, zorder=3)
    i_max = int(np.argmax(d.values))
    etiketli = range(n) if n <= 8 else {i_min, i_max}
    for i in etiketli:
        ax.text(i, d.values[i], sayi_tr(d.values[i], 1), ha="center",
                va="bottom", fontsize=7, color=RENK.METIN)
    if ctx.has_band:
        p10 = ctx.daily_p10.values / 1000.0
        p90 = ctx.daily_p90.values / 1000.0
        ax.vlines(np.arange(n), p10, p90, color=RENK.METIN,
                  linewidth=1.0, alpha=0.55, zorder=4)
        ax.hlines(p90, np.arange(n) - 0.24, np.arange(n) + 0.24,
                  color=RENK.METIN, linewidth=1.0, zorder=4)
        ax.hlines(p10, np.arange(n) - 0.24, np.arange(n) + 0.24,
                  color=RENK.METIN, linewidth=1.0, zorder=4)
    adim = 1 if n <= 8 else 2
    ax.set_xticks(range(0, n, adim))
    ax.set_xticklabels([gun_tr(t) for t in d.index[::adim]], rotation=0,
                       fontsize=7 if n > 8 else 8.5)
    ax.set_title(f"Günlük üretim — {n} gün"
                 + (" (çizgiler: P10–P90)" if ctx.has_band else ""))
    ax.set_ylabel("MWh")
    ax.set_ylim(0, d.max() * 1.2)
    ax.margins(x=0.02)
    fig.tight_layout()
    return fig


def fig_tipik_gun(ctx) -> plt.Figure:
    """Sağ grafik: 7 günün saat-bazlı ortalama profili + gün-içi min/maks bandı."""
    tema_uygula()
    h = ctx.hourly.tz_convert(ctx.plant_tz)
    grp = h["p50_kw"].groupby(h.index.hour)
    ort = grp.mean()
    if "p10_kw" in h.columns and h["p10_kw"].notna().any():
        # Mod C: bant = saatlik P10/P90 ortalama profili (v2.96 — gercek bant)
        alt = h["p10_kw"].groupby(h.index.hour).mean()
        ust = h["p90_kw"].groupby(h.index.hour).mean()
    else:
        alt, ust = grp.min(), grp.max()   # bant yok: gun-ici min/maks
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


# ---------------------------------------------- v2.96 tam sartname grafikleri
def fig_kalib(ctx) -> plt.Figure:
    """S5: fizik -> hibrit iyilesme — before/after MAPE barlari."""
    tema_uygula()
    fig, ax = plt.subplots(figsize=(3.4, 2.3))
    once, sonra = ctx.holdout_physics_mape_pct, ctx.holdout_mape_pct
    ax.bar([0, 1], [once, sonra], color=[RENK.IKINCIL, RENK.MARKA],
           width=0.5, zorder=3)
    for i, v in enumerate((once, sonra)):
        ax.text(i, v, f"%{sayi_tr(v, 1)}", ha="center", va="bottom",
                fontsize=8, color=RENK.METIN, fontweight="bold")
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["saf fizik", "hibrit"])
    ax.set_title("Holdout MAPE — fizik vs hibrit")
    ax.set_ylabel("MAPE %")
    ax.set_ylim(0, max(once, sonra) * 1.25)
    fig.tight_layout()
    return fig


_FLAG_TR = {"valid": "geçerli", "night_production": "gece üretimi",
            "frozen_value": "donmuş değer", "over_capacity": "kapasite üstü",
            "negative_power": "negatif güç", "unparseable": "okunamayan",
            "duplicate_time": "çift zaman", "dst_ambiguous": "DST belirsiz"}


def fig_flags(ctx) -> plt.Figure:
    """S5: veri kalitesi karnesi — bayrak dagilimi (gecerli haric,
    log yatay bar; supheli satir SILINMEZ, bayraklanir ilkesinin resmi)."""
    tema_uygula()
    d = {k: v for k, v in (ctx.flag_dagilimi or {}).items() if k != "valid"}
    d = dict(sorted(d.items(), key=lambda kv: kv[1]))
    fig, ax = plt.subplots(figsize=(3.4, 2.3))
    adlar = [_FLAG_TR.get(k, k) for k in d]
    ax.barh(range(len(d)), list(d.values()), color=RENK.VURGU,
            height=0.55, zorder=3)
    for i, v in enumerate(d.values()):
        ax.text(v, i, f" {v:,}".replace(",", "."), va="center",
                fontsize=7, color=RENK.METIN)
    ax.set_yticks(range(len(d)))
    ax.set_yticklabels(adlar, fontsize=7.5)
    ax.set_title("Bayraklı saatler (geçerli hariç)")
    ax.set_xlabel("saat")
    ax.margins(x=0.14)
    ax.grid(axis="x")
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    return fig


def fig_iklim_zarf(ctx) -> plt.Figure:
    """S6: 20-yillik aylik GHI zarfi (P10-P90 bant + P50 cizgi)."""
    tema_uygula()
    ik = ctx.iklim
    gerekli = ("ay", "ghi_p10_kwh_m2", "ghi_p50_kwh_m2", "ghi_p90_kwh_m2")
    if ik is None or len(ik) == 0 or any(k not in ik for k in gerekli):
        # v2.161: bos iklimde KeyError yerine durust isaret (pdf.py ilkesi:
        # "veri yoksa 'veri eksik (gereken: ...)' - asla bos iskelet").
        fig, ax = plt.subplots(figsize=(3.55, 2.4))
        ax.axis("off")
        ax.text(0.5, 0.5,
                "veri eksik (gereken: iklim zarfi -\nay, ghi_p10/p50/p90_kwh_m2)",
                ha="center", va="center", fontsize=7)
        ax.set_title("Aylik GHI zarfi")
        fig.tight_layout()
        return fig
    fig, ax = plt.subplots(figsize=(3.55, 2.4))
    ax.fill_between(ik["ay"], ik["ghi_p10_kwh_m2"], ik["ghi_p90_kwh_m2"],
                    color=RENK.MARKA, alpha=0.20, linewidth=0,
                    label="P10–P90")
    ax.plot(ik["ay"], ik["ghi_p50_kwh_m2"], color=RENK.MARKA, lw=1.9,
            label="P50")
    yil_n = int(ik["yil_sayisi"].iloc[0]) if "yil_sayisi" in ik else 20
    ax.set_title(f"Aylık GHI zarfı — {yil_n} yıl")
    ax.set_ylabel("kWh/m²")
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels([AYLAR_TR[a - 1][:3] for a in range(1, 13)],
                       fontsize=6, rotation=45, ha="right")
    ax.legend(frameon=False, fontsize=7, loc="upper right")
    ax.set_ylim(bottom=0)
    fig.tight_layout()
    return fig


def fig_son12(ctx) -> plt.Figure:
    """S6: son 12 ayin gerceklesen uretimi (SCADA, yalniz gecerli saatler).
    Olculmeyen ay bar YOK — bosluk durust birakilir."""
    tema_uygula()
    d = ctx.son12
    fig, ax = plt.subplots(figsize=(3.55, 2.4))
    ax.bar(range(len(d)), d["actual_mwh"], color=RENK.MARKA, width=0.6,
           zorder=3)
    for i, v in enumerate(d["actual_mwh"]):
        ax.text(i, v, sayi_tr(float(v), 0), ha="center", va="bottom",
                fontsize=6.5, color=RENK.METIN)
    ax.set_xticks(range(len(d)))
    ax.set_xticklabels([f"{AYLAR_TR[t.month - 1][:3]} {t:%y}"
                        for t in d["ay"]], rotation=45, ha="right",
                       fontsize=6.5)
    ax.set_title("Gerçekleşen üretim — son 12 ay")
    ax.set_ylabel("MWh")
    ax.set_ylim(bottom=0)
    fig.tight_layout()
    return fig


def fig_kosu_evrim(ctx) -> plt.Figure:
    """S8: hedef gun icin son kosularda P50 evrimi — kosular guncellenmez,
    eklenir; tahminin zamanla nasil oturdugunun resmi."""
    tema_uygula()
    ev = ctx.kosu_evrim
    fig, ax = plt.subplots(figsize=(7.3, 2.4))
    ax.plot(range(len(ev)), ev["p50_mwh"], color=RENK.MARKA, lw=1.9,
            marker="o", ms=4)
    for i, v in enumerate(ev["p50_mwh"]):
        ax.annotate(sayi_tr(float(v), 1), (i, v), textcoords="offset points",
                    xytext=(0, 6), ha="center", fontsize=7,
                    color=RENK.METIN)
    ax.set_xticks(range(len(ev)))
    ax.set_xticklabels([f"{gun_tr(t)} {t:%H:%M}" for t in ev["run_at"]],
                       fontsize=7)
    ax.set_title(f"{gun_tr(ctx.evrim_gunu)} günü için P50 evrimi "
                 f"— koşudan koşuya")
    ax.set_ylabel("MWh")
    y0, y1 = float(ev["p50_mwh"].min()), float(ev["p50_mwh"].max())
    pay = max((y1 - y0) * 0.35, y1 * 0.06, 0.5)
    ax.set_ylim(max(0, y0 - pay), y1 + pay)
    fig.tight_layout()
    return fig
