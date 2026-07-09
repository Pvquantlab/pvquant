"""
PVQuant Sayfa Fonksiyonlari (Faz 2 Adim 1a - Placeholder'lar)
"""

import streamlit as st


def _placeholder(page_title: str, subtitle: str, adim: str) -> None:
    """Standart placeholder ekran."""
    # Sayfa basligi
    st.markdown(
        f'<div class="pvq-page-title">{page_title}</div>'
        f'<div class="pvq-page-subtitle">{subtitle}</div>',
        unsafe_allow_html=True,
    )

    # Placeholder kart
    st.markdown(
        f'<div class="pvq-placeholder">'
        f'  <div class="pvq-placeholder-title">{page_title}</div>'
        f'  <div>Bu ekran <strong>{adim}</strong>&apos;de gelecek.</div>'
        f'  <div style="margin-top:12px;font-size:12px;">'
        f'    Su an sadece kabuk test ediliyor: sol menu, renkler, fontlar, footer.'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_santralim() -> None:
    _placeholder(
        "Santralim",
        "Santralinizin bugununu ve onumuzdeki 7 gunu tek bakista gorun",
        "Adim 2",
    )


def render_veri_yukleme() -> None:
    _placeholder(
        "Veri Yukleme",
        "Tahmin yolunuzu secin; SCADA veriniz varsa kalibre tahmine gecin",
        "Adim 3-4",
    )


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
