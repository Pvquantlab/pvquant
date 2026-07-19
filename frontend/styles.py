"""
PVQuant Global Styles (Faz 2 - Yaklasim B+)

Streamlit'in native sidebar ve content alanini CSS ile PVQuant tasarim
sistemine uydurur. Kabuk mimarisi Streamlit'in kendi mimarisidir; biz
sadece renkleri, fontlari ve boslugu ayarliyoruz.
"""

import streamlit as st
from design_tokens import (
    PRIMARY, PRIMARY_HOVER, DARK_NAVY,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY, MICROLABEL,
    BORDER, PAGE_BG, CARD_BG,
    SUCCESS,
    FONT_UI, FONT_MONO,
    SIZE_MICRO, SIZE_CAPTION, SIZE_BODY, SIZE_LABEL,
    SIZE_H1, SIZE_H2, SIZE_H3,
    WEIGHT_MEDIUM, WEIGHT_SEMI, WEIGHT_BOLD,
    LETTER_SPACING_MICRO, LETTER_SPACING_TIGHT,
    SPACE_XS, SPACE_SM, SPACE_MD, SPACE_LG, SPACE_XL,
    RADIUS_CARD, RADIUS_BUTTON,
    SIDEBAR_WIDTH, CONTENT_MAX,
)


def _build_css() -> str:
    return f"""
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

    /* Streamlit default'unu ez */
    #MainMenu {{ visibility: hidden; }}
    div[data-testid="stToolbar"] {{ visibility: hidden; height: 0; }}
    div[data-testid="stDecoration"] {{ display: none; }}
    header[data-testid="stHeader"] {{ background: transparent; height: 0; }}

    html, body, [class*="css"] {{
        font-family: {FONT_UI} !important;
    }}
    body {{ color: {TEXT_PRIMARY}; background: {PAGE_BG}; }}

    /* ============================================================ */
    /* SOL MENU                                                     */
    /* ============================================================ */

    section[data-testid="stSidebar"],
    section[data-testid="stSidebar"] > div,
    section[data-testid="stSidebar"] > div > div,
    div[data-testid="stSidebarContent"],
    div[data-testid="stSidebarUserContent"] {{
        background: {DARK_NAVY} !important;
    }}
    section[data-testid="stSidebar"] {{
        width: {SIDEBAR_WIDTH} !important;
        min-width: {SIDEBAR_WIDTH} !important;
        display: flex !important;
        visibility: visible !important;
        transform: none !important;
        left: 0 !important;
        margin-left: 0 !important;
    }}
    section[data-testid="stSidebar"] > div {{
        transform: none !important;
    }}
    section[data-testid="stSidebar"] * {{
        color: #CBD5E1;
    }}
    section[data-testid="stSidebar"] .pvq-sidebar-brand,
    section[data-testid="stSidebar"] .pvq-sidebar-org-initial,
    section[data-testid="stSidebar"] .pvq-sidebar-org-name {{
        color: #FFFFFF !important;
    }}

    section[data-testid="stSidebar"] button {{
        width: 100%;
        text-align: left;
        justify-content: flex-start;
        background: transparent;
        border: 1px solid transparent;
        color: #CBD5E1;
        padding: {SPACE_SM} {SPACE_MD};
        margin: 2px 0;
        border-radius: {RADIUS_BUTTON};
        font-weight: {WEIGHT_MEDIUM};
        font-size: {SIZE_BODY};
    }}
    section[data-testid="stSidebar"] button:hover {{
        background: rgba(255,255,255,0.06);
        color: #FFFFFF;
        border: 1px solid transparent;
    }}
    section[data-testid="stSidebar"] button[kind="primary"] {{
        background: {PRIMARY} !important;
        color: #FFFFFF !important;
        border: 1px solid {PRIMARY} !important;
    }}
    section[data-testid="stSidebar"] button[kind="primary"]:hover {{
        background: {PRIMARY_HOVER} !important;
        border-color: {PRIMARY_HOVER} !important;
    }}

    .pvq-sidebar-brand {{
        font-size: {SIZE_H3};
        font-weight: {WEIGHT_BOLD};
        display: flex;
        align-items: center;
        gap: {SPACE_SM};
        padding: 0 0 {SPACE_MD} 0;
        letter-spacing: {LETTER_SPACING_TIGHT};
    }}

    .pvq-sidebar-privacy {{
        color: #94A3B8 !important;
        font-size: {SIZE_CAPTION};
        line-height: 1.5;
        padding: {SPACE_MD} 0;
    }}

    .pvq-sidebar-org {{
        display: flex;
        align-items: center;
        gap: {SPACE_SM};
        padding: {SPACE_MD} 0;
        border-top: 1px solid rgba(255,255,255,0.08);
        margin-top: {SPACE_SM};
    }}
    .pvq-sidebar-org-initial {{
        width: 32px;
        height: 32px;
        border-radius: {RADIUS_BUTTON};
        background: rgba(255,255,255,0.1);
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: {WEIGHT_SEMI};
        font-size: {SIZE_LABEL};
        flex-shrink: 0;
    }}
    .pvq-sidebar-org-name {{
        font-size: {SIZE_LABEL};
        font-weight: {WEIGHT_SEMI};
        line-height: 1.3;
    }}
    .pvq-sidebar-org-plan {{
        font-size: {SIZE_CAPTION};
        color: #94A3B8 !important;
        line-height: 1.3;
    }}

    /* ============================================================ */
    /* ANA ICERIK                                                   */
    /* ============================================================ */

    .main .block-container,
    section.main > div.block-container,
    div[data-testid="stMain"] .block-container {{
        padding-top: {SPACE_LG} !important;
        padding-bottom: {SPACE_LG} !important;
        padding-left: {SPACE_XL} !important;
        padding-right: {SPACE_XL} !important;
        max-width: {CONTENT_MAX} !important;
    }}

    .pvq-mono {{
        font-family: {FONT_MONO};
        font-feature-settings: 'tnum' 1, 'zero' 1;
    }}
    .pvq-microlabel {{
        font-size: {SIZE_MICRO};
        font-weight: {WEIGHT_SEMI};
        text-transform: uppercase;
        letter-spacing: {LETTER_SPACING_MICRO};
        color: {MICROLABEL};
    }}
    .pvq-page-title {{
        font-size: {SIZE_H1};
        font-weight: {WEIGHT_BOLD};
        letter-spacing: {LETTER_SPACING_TIGHT};
        color: {TEXT_PRIMARY};
        margin: 0 0 {SPACE_XS} 0;
    }}
    .pvq-page-subtitle {{
        font-size: {SIZE_BODY};
        color: {TEXT_SECONDARY};
        margin: 0 0 {SPACE_LG} 0;
    }}
    .pvq-page-stamp {{
        font-family: {FONT_MONO};
        font-size: {SIZE_CAPTION};
        color: {TEXT_TERTIARY};
    }}


    .pvq-footer {{
        border-top: 1px solid {BORDER};
        padding: {SPACE_MD} 0;
        margin-top: {SPACE_XL};
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: {SPACE_MD};
        font-family: {FONT_MONO};
        font-size: {SIZE_CAPTION};
        color: {TEXT_TERTIARY};
    }}
    .pvq-footer-status {{
        display: flex;
        align-items: center;
        gap: {SPACE_XS};
        color: {SUCCESS};
    }}
    .pvq-footer-dot {{
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: {SUCCESS};
    }}

    /* ============================================================ */
    /* UST BAR (Adim 1b)                                            */
    /* ============================================================ */

    .pvq-topbar {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: {SPACE_MD};
        padding: {SPACE_SM} 0 {SPACE_MD} 0;
        margin-bottom: {SPACE_LG};
        border-bottom: 1px solid {BORDER};
    }}
    .pvq-topbar-right {{
        display: flex;
        align-items: center;
        gap: {SPACE_MD};
        margin-left: auto;
    }}
    .pvq-topbar-plant {{
        display: flex;
        align-items: center;
        gap: {SPACE_XS};
        font-size: {SIZE_LABEL};
        padding: {SPACE_XS} {SPACE_SM};
    }}
    .pvq-topbar-plant-label {{
        color: {TEXT_TERTIARY};
        font-weight: {WEIGHT_MEDIUM};
    }}
    .pvq-topbar-plant-name {{
        color: {TEXT_PRIMARY};
        font-weight: {WEIGHT_SEMI};
    }}
    .pvq-topbar-live {{
        display: flex;
        align-items: center;
        gap: {SPACE_XS};
        font-size: {SIZE_CAPTION};
        color: {SUCCESS};
    }}
    .pvq-topbar-live-dot {{
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: {SUCCESS};
    }}
    .pvq-topbar-date {{
        font-family: {FONT_MONO};
        font-size: {SIZE_CAPTION};
        color: {TEXT_SECONDARY};
    }}
    .pvq-topbar-avatar {{
        display: flex;
        align-items: center;
        gap: {SPACE_SM};
    }}
    .pvq-topbar-avatar-circle {{
        width: 32px;
        height: 32px;
        border-radius: 50%;
        background: {PRIMARY};
        color: #FFFFFF;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: {WEIGHT_SEMI};
        font-size: {SIZE_LABEL};
    }}
    .pvq-topbar-avatar-info {{
        display: flex;
        flex-direction: column;
        gap: 1px;
        line-height: 1.2;
    }}
    .pvq-topbar-avatar-name {{
        font-size: {SIZE_LABEL};
        font-weight: {WEIGHT_SEMI};
        color: {TEXT_PRIMARY};
    }}
    .pvq-topbar-avatar-org {{
        font-size: {SIZE_CAPTION};
        color: {TEXT_TERTIARY};
    }}

    /* ============================================================ */
    /* PAYLASILAN BILESENLER (Adim 1c)                              */
    /* ============================================================ */

    .pvq-page-header-row {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: {SPACE_MD};
        margin-bottom: {SPACE_LG};
    }}
    .pvq-page-header-row .pvq-page-title,
    .pvq-page-header-row .pvq-page-subtitle {{
        margin-bottom: 0;
    }}
    .pvq-page-header-row .pvq-page-subtitle {{
        margin-top: {SPACE_XS};
    }}

    .pvq-card {{
        background: {CARD_BG};
        border: 1px solid {BORDER};
        border-radius: {RADIUS_CARD};
        padding: {SPACE_LG};
    }}

    .pvq-kpi {{
        display: flex;
        flex-direction: column;
        gap: {SPACE_SM};
    }}
    .pvq-kpi-value {{
        font-size: 32px;
        font-weight: {WEIGHT_BOLD};
        color: {TEXT_PRIMARY};
        line-height: 1.1;
        display: flex;
        align-items: baseline;
        gap: {SPACE_XS};
    }}
    .pvq-kpi-value--success {{
        color: {SUCCESS};
    }}
    .pvq-kpi-value--primary {{
        color: {PRIMARY};
    }}
    .pvq-kpi-unit {{
        font-size: {SIZE_BODY};
        font-weight: {WEIGHT_MEDIUM};
        color: {TEXT_SECONDARY};
        font-family: {FONT_UI};
    }}
    .pvq-kpi-subtitle {{
        font-size: {SIZE_CAPTION};
        color: {TEXT_TERTIARY};
    }}
    .pvq-kpi-info {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 14px;
        height: 14px;
        border-radius: 50%;
        border: 1px solid {TEXT_TERTIARY};
        color: {TEXT_TERTIARY};
        font-size: 10px;
        font-style: italic;
        margin-left: 4px;
        cursor: help;
    }}

    .pvq-pill {{
        display: inline-flex;
        align-items: center;
        gap: {SPACE_XS};
        padding: 4px 10px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: {WEIGHT_SEMI};
        border: 1px solid transparent;
        white-space: nowrap;
    }}
    .pvq-pill--success {{
        color: {SUCCESS};
        border-color: {SUCCESS};
        background: rgba(30, 158, 106, 0.08);
    }}
    .pvq-pill--primary {{
        color: {PRIMARY};
        border-color: {PRIMARY};
        background: rgba(31, 82, 136, 0.08);
    }}
    .pvq-pill--neutral {{
        color: {TEXT_SECONDARY};
        border-color: {BORDER};
        background: {PAGE_BG};
    }}
    .pvq-pill-dot {{
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: currentColor;
    }}

    /* Marka bandi (Santralim ekraninin ust bolumu) */
    .pvq-brand-band {{
        background: linear-gradient(135deg, {DARK_NAVY} 0%, #1a2f4a 100%);
        color: #FFFFFF;
        border-radius: {RADIUS_CARD};
        padding: {SPACE_LG} {SPACE_XL};
        margin-bottom: {SPACE_LG};
    }}
    .pvq-brand-band-content {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: {SPACE_LG};
    }}
    .pvq-brand-band-name {{
        font-size: 28px;
        font-weight: {WEIGHT_BOLD};
        letter-spacing: {LETTER_SPACING_TIGHT};
        margin-bottom: {SPACE_XS};
    }}
    .pvq-brand-band-meta {{
        font-size: {SIZE_BODY};
        color: rgba(255, 255, 255, 0.7);
        margin-bottom: {SPACE_MD};
    }}
    .pvq-brand-band-pills {{
        display: flex;
        gap: {SPACE_SM};
    }}
    .pvq-brand-band-pills .pvq-pill {{
        background: rgba(255, 255, 255, 0.1);
        border-color: rgba(255, 255, 255, 0.2);
    }}
    .pvq-brand-band-pills .pvq-pill--success {{
        color: #6EE7B7;
        border-color: rgba(110, 231, 183, 0.4);
        background: rgba(30, 158, 106, 0.15);
    }}
    .pvq-brand-band-weather {{
        display: flex;
        gap: {SPACE_LG};
    }}

    /* Hava sutunlari - marka bandi sag tarafta */
    .pvq-weather-col {{
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 4px;
        padding: {SPACE_SM} {SPACE_MD};
        border-radius: {RADIUS_BUTTON};
        min-width: 76px;
    }}
    .pvq-weather-col--active {{
        background: rgba(255, 255, 255, 0.08);
    }}
    .pvq-weather-day {{
        font-size: 11px;
        font-weight: {WEIGHT_SEMI};
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: rgba(255, 255, 255, 0.7);
    }}
    .pvq-weather-temp {{
        font-size: 20px;
        font-weight: {WEIGHT_BOLD};
        color: #FFFFFF;
        font-family: {FONT_MONO};
    }}
    .pvq-weather-ghi {{
        font-size: {SIZE_CAPTION};
        color: rgba(255, 255, 255, 0.6);
        font-family: {FONT_MONO};
    }}

    .pvq-brand-band-footer {{
        margin-top: {SPACE_MD};
        padding-top: {SPACE_MD};
        border-top: 1px solid rgba(255, 255, 255, 0.1);
        font-size: {SIZE_BODY};
        color: rgba(255, 255, 255, 0.8);
    }}
    """


def inject_global_css() -> None:
    st.markdown(f"<style>{_build_css()}</style>", unsafe_allow_html=True)