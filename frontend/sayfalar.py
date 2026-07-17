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
    from kalibrasyon import render_kalibrasyon as _render
    _render()


def render_tahminler() -> None:
    from tahminler import render_tahminler as _render
    _render()


def render_dogruluk() -> None:
    from dogruluk import render_dogruluk as _render
    _render()
def render_raporlar() -> None:
    from raporlar import render_raporlar as _render
    _render()


PAGE_RENDERERS = {
    "santralim":    render_santralim,
    "veri_yukleme": render_veri_yukleme,
    "kalibrasyon":  render_kalibrasyon,
    "tahminler":    render_tahminler,
    "dogruluk":    render_dogruluk,
    "raporlar":     render_raporlar,
}