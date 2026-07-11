"""
PVQuant Raporlar Ekrani (Faz 2 Adim 6)

Kalibre tahmin sonuclarini 3 farkli formatta (PDF/Excel/JSON) disa aktarir.

Adim 6a: Iskelet + KPI seridi + guard'lar
Adim 6b: 3 format karti (gorsel)
Adim 6c: Excel + JSON gercek isleyisi
Adim 6d: PDF yonetici ozeti (fpdf2)
Adim 6e: Rapor gecmisi (dekoratif)
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from components import page_header
from design_tokens import (
    PRIMARY, SUCCESS, WARNING,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY,
)


# ============================================================
# Guard - kalibrasyon yoksa
# ============================================================

def _uyari_kalibrasyon_yok() -> None:
    st.markdown(
        f"""
        <div class="pvq-card" style="border-left:3px solid {WARNING};
             text-align:center;padding:48px 24px">
          <div style="font-size:48px;margin-bottom:16px">📄</div>
          <div style="font-size:20px;font-weight:600;color:#0F1B28;
                      margin-bottom:12px">
            Once kalibrasyon yapin
          </div>
          <div style="font-size:14px;color:{TEXT_SECONDARY};max-width:480px;
                      margin:0 auto 24px auto">
            Rapor uretmek icin oncelikle SCADA verinizi yukleyip
            modeli santralinize kalibre etmelisiniz.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(
            "Kalibrasyon sayfasina git",
            key="raporlar_git_kalibrasyon",
            use_container_width=True,
            type="primary",
        ):
            st.session_state.active_page = "kalibrasyon"
            st.rerun()


# ============================================================
# Guard - forecast yoksa
# ============================================================

def _uyari_forecast_yok() -> None:
    st.markdown(
        f"""
        <div class="pvq-card" style="border-left:3px solid {WARNING};
             text-align:center;padding:48px 24px">
          <div style="font-size:48px;margin-bottom:16px">📊</div>
          <div style="font-size:20px;font-weight:600;color:#0F1B28;
                      margin-bottom:12px">
            Once tahmin olusturun
          </div>
          <div style="font-size:14px;color:{TEXT_SECONDARY};max-width:480px;
                      margin:0 auto 24px auto">
            Rapor icerigi 7 gunluk tahmine dayanir. Once Tahminler
            sayfasina gidip tahmini olusturun, sonra buraya donun.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(
            "Tahminler sayfasina git",
            key="raporlar_git_tahminler",
            use_container_width=True,
            type="primary",
        ):
            st.session_state.active_page = "tahminler"
            st.rerun()


# ============================================================
# 6a: KPI seridi
# ============================================================

def _kpi_seridi() -> None:
    from datetime import datetime

    result = st.session_state.forecast_result
    n_saat = len(result.hourly)

    # Boyut tahmini: kaba hesap (satir sayisi * kolon sayisi * ~10 byte)
    boyut_kb = int((n_saat * len(result.hourly.columns) * 10) / 1024)

    bugun = datetime.now().strftime("%d %b").replace(" 0", " ")

    kpi_cols = st.columns(4)
    with kpi_cols[0]:
        st.markdown(
            f'<div class="pvq-card">'
            f'<div class="pvq-microlabel">SON RAPOR</div>'
            f'<div class="pvq-kpi-value">'
            f'<span class="pvq-mono">{bugun}</span>'
            f'</div>'
            f'<div class="pvq-kpi-subtitle">bugun</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with kpi_cols[1]:
        st.markdown(
            f'<div class="pvq-card">'
            f'<div class="pvq-microlabel">FORMAT</div>'
            f'<div class="pvq-kpi-value">'
            f'<span class="pvq-mono">3</span>'
            f'<span class="pvq-kpi-unit">tip</span>'
            f'</div>'
            f'<div class="pvq-kpi-subtitle">PDF, Excel, JSON</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with kpi_cols[2]:
        st.markdown(
            f'<div class="pvq-card">'
            f'<div class="pvq-microlabel">VERI KAPSAMI</div>'
            f'<div class="pvq-kpi-value">'
            f'<span class="pvq-mono">{n_saat}</span>'
            f'<span class="pvq-kpi-unit">saat</span>'
            f'</div>'
            f'<div class="pvq-kpi-subtitle">7 gun tahmin</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with kpi_cols[3]:
        st.markdown(
            f'<div class="pvq-card">'
            f'<div class="pvq-microlabel">BOYUT</div>'
            f'<div class="pvq-kpi-value">'
            f'<span class="pvq-mono">~{boyut_kb}</span>'
            f'<span class="pvq-kpi-unit">KB</span>'
            f'</div>'
            f'<div class="pvq-kpi-subtitle">Excel tahmini</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ============================================================
# 6b placeholder - format kartlari (bir sonraki adimda gelecek)
# ============================================================

def _format_kartlari_placeholder() -> None:
    st.markdown(
        f'<div class="pvq-card" style="margin-top:24px;'
        f'text-align:center;padding:48px 24px">'
        f'<div style="font-size:15px;font-weight:600;color:{TEXT_PRIMARY};'
        f'margin-bottom:8px">3 format karti</div>'
        f'<div style="font-size:13px;color:{TEXT_SECONDARY}">'
        f'PDF Yonetici Ozeti / Excel Tam Veri / JSON API Formati'
        f'</div>'
        f'<div style="font-size:12px;color:{TEXT_TERTIARY};margin-top:12px;'
        f'font-style:italic">Adim 6b</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# ANA render
# ============================================================

def render_raporlar() -> None:
    page_header(   
        "Raporlar",
        "PDF yonetici ozeti, Excel tam veri, JSON API formati",
    )

    # Guard 1: kalibrasyon var mi?
    if "calibration_result" not in st.session_state:
        _uyari_kalibrasyon_yok()
        return

    # Guard 2: forecast var mi?
    if "forecast_result" not in st.session_state:
        _uyari_forecast_yok()
        return

    # 6a: KPI seridi
    _kpi_seridi()

    # 6b: Format kartlari (placeholder)
    _format_kartlari_placeholder()
    