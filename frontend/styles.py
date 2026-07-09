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
    /* Sidebar'in animasyon wrapper'i */
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

    /* NOT: Streamlit 1.58'in sidebar collapse butonunu gizleme kurallari
       tum sidebar'i kirdigi icin cikarildi. Buton gorunur kaliyor. */

    /* Sidebar butonlari - nav */
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

    /* Marka blogu */
    .pvq-sidebar-brand {{
        font-size: {SIZE_H3};
        font-weight: {WEIGHT_BOLD};
        display: flex;
        align-items: center;
        gap: {SPACE_SM};
        padding: 0 0 {SPACE_MD} 0;
        letter-spacing: {LETTER_SPACING_TIGHT};
    }}

    /* Gizlilik cumlesi */
    .pvq-sidebar-privacy {{
        color: #94A3B8 !important;
        font-size: {SIZE_CAPTION};
        line-height: 1.5;
        padding: {SPACE_MD} 0;
    }}

    /* Kurulus blogu */
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

    /* Tipografi */
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

    /* Placeholder kart */
    .pvq-placeholder {{
        background: {CARD_BG};
        border: 1px dashed {BORDER};
        border-radius: {RADIUS_CARD};
        padding: {SPACE_XL};
        text-align: center;
        color: {TEXT_TERTIARY};
        margin-top: {SPACE_MD};
    }}
    .pvq-placeholder-title {{
        font-size: {SIZE_H2};
        font-weight: {WEIGHT_SEMI};
        color: {TEXT_SECONDARY};
        margin-bottom: {SPACE_SM};
    }}

    /* Footer */
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
    """


def inject_global_css() -> None:
    st.markdown(f"<style>{_build_css()}</style>", unsafe_allow_html=True)
