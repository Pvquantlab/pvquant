"""
PVQuant Paylasilan Bilesenler (Faz 2 Adim 1c)

Sayfalar arasi tekrar kullanilan UI parcaciklari.
Hepsi CSS class'larini styles.py'den kullanir.
"""

from datetime import datetime
import streamlit as st


def page_header(title: str, subtitle: str, show_stamp: bool = True) -> None:
    """Sayfa basligi disiplini: baslik + gri aciklama + sagda 'Son guncelleme HH:MM'."""
    now = datetime.now()
    stamp_html = ""
    if show_stamp:
        stamp_html = f'<div class="pvq-page-stamp">Son guncelleme {now.strftime("%H:%M")}</div>'

    st.markdown(
        f'<div class="pvq-page-header-row">'
        f'  <div>'
        f'    <div class="pvq-page-title">{title}</div>'
        f'    <div class="pvq-page-subtitle">{subtitle}</div>'
        f'  </div>'
        f'  {stamp_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def microlabel(text: str) -> str:
    """Mikro-etiket HTML'i (BUYUK HARF, kucuk font, harflerarasi bosluklu)."""
    return f'<div class="pvq-microlabel">{text}</div>'


def kpi_card(
    label: str,
    value: str,
    unit: str = "",
    subtitle: str = "",
    value_color: str = "",
    info_tooltip: bool = False,
) -> None:
    """KPI karti: mikro-etiket + buyuk sayi (+ birim) + alt not.

    value_color: 'success', 'primary' veya bos - sayilar icin ozel renk.
    """
    color_class = f"pvq-kpi-value--{value_color}" if value_color else ""
    info_html = ' <span class="pvq-kpi-info">i</span>' if info_tooltip else ''

    st.markdown(
        f'<div class="pvq-card pvq-kpi">'
        f'  <div class="pvq-microlabel">{label}{info_html}</div>'
        f'  <div class="pvq-kpi-value {color_class}">'
        f'    <span class="pvq-mono">{value}</span>'
        f'    {f"<span class=\"pvq-kpi-unit\">{unit}</span>" if unit else ""}'
        f'  </div>'
        f'  {f"<div class=\"pvq-kpi-subtitle\">{subtitle}</div>" if subtitle else ""}'
        f'</div>',
        unsafe_allow_html=True,
    )


def pill(text: str, variant: str = "neutral", dot: bool = False) -> str:
    """Rozet/pill HTML'i.

    variant: 'success' (yesil), 'primary' (mavi), 'neutral' (gri), 'warning' (bakir).
    dot: basa yesil/kirmizi vs. nokta koy.
    """
    dot_html = f'<span class="pvq-pill-dot"></span>' if dot else ''
    return f'<span class="pvq-pill pvq-pill--{variant}">{dot_html}{text}</span>'


def brand_band(
    name: str,
    meta_line: str,
    pills_html: str = "",
    weather_html: str = "",
    footer_note: str = "",
) -> None:
    """Koyu marka bandi - Santralim ekraninin en ustunde.

    name: 'Konya GES'
    meta_line: '2.5 MW * Konya, Turkiye * Devreye alma 2023'
    pills_html: iki pill (Kalibre, Bugunun tahmini hazir)
    weather_html: sagda hava sutunlari
    footer_note: alt seritte uretim etkisi cumlesi
    """
    st.markdown(
        f'<div class="pvq-brand-band">'
        f'  <div class="pvq-brand-band-content">'
        f'    <div class="pvq-brand-band-left">'
        f'      <div class="pvq-brand-band-name">{name}</div>'
        f'      <div class="pvq-brand-band-meta">{meta_line}</div>'
        f'      <div class="pvq-brand-band-pills">{pills_html}</div>'
        f'    </div>'
        f'    <div class="pvq-brand-band-weather">{weather_html}</div>'
        f'  </div>'
        f'  {f"<div class=\"pvq-brand-band-footer\">{footer_note}</div>" if footer_note else ""}'
        f'</div>',
        unsafe_allow_html=True,
    )