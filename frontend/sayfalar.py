"""
PVQuant Sayfa Fonksiyonlari (Faz 2)
"""

import streamlit as st
from components import page_header
from santralim import render_santralim


def _placeholder(page_title: str, subtitle: str, adim: str) -> None:
    """Standart placeholder ekran."""
    page_header(page_title, subtitle)

    st.markdown(
        f'<div class="pvq-placeholder">'
        f'  <div class="pvq-placeholder-title">{page_title}</div>'
        f'  <div>Bu ekran <strong>{adim}</strong>&apos;de gelecek.</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_veri_yukleme() -> None:
    from veri_yukleme import render_veri_yukleme as _render
    _render()


def render_kalibrasyon() -> None:
    _placeholder(
        "Kalibrasyon",
        "Modeli santralinize uyarlama sihirbazi",
        "Adim 4",
    )


def render_tahminler() -> None:
    _placeholder(
        "Tahminler",
        "7 gunluk saatlik uretim tahmini ve model bulgular",
        "Adim 5",
    )


def render_raporlar() -> None:
    _placeholder(
        "Raporlar",
        "PDF yonetici ozeti, Excel tam veri, JSON API formati",
        "Adim 6",
    )


PAGE_RENDERERS = {
    "santralim":    render_santralim,
    "veri_yukleme": render_veri_yukleme,
    "kalibrasyon":  render_kalibrasyon,
    "tahminler":    render_tahminler,
    "raporlar":     render_raporlar,
}