"""
PVQuant Ana Giris Noktasi (Faz 2 Adim 1a + 1b)

Streamlit'in native sidebar'ini kullanir, CSS ile PVQuant tasarim
sistemine uydurulur.

Calistirmak:
    cd ~/Desktop/pvquant
    source .venv/bin/activate
    streamlit run frontend/Ana.py
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st

from design_tokens import (
    MENU_ITEMS, PRIVACY_TEXT,
    ORG_NAME, ORG_PLAN, ORG_INITIAL,
    APP_VERSION, COPYRIGHT, STATUS_TEXT,
)
from styles import inject_global_css
from sayfalar import PAGE_RENDERERS


# ============================================================
# SAYFA AYARLARI
# ============================================================
st.set_page_config(
    page_title="PVQuant - Santralinizi tanıyan tahmin",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# SESSION STATE
# ============================================================
if "active_page" not in st.session_state:
    st.session_state.active_page = "santralim"


def _set_page(key: str) -> None:
    st.session_state.active_page = key


# ============================================================
# GLOBAL CSS
# ============================================================
inject_global_css()


# ============================================================
# SOL MENU (Streamlit sidebar)
# ============================================================
with st.sidebar:
    # Marka
    st.markdown(
        '<div class="pvq-sidebar-brand">'
        '<span>⚡</span>'
        '<span>PVQuant</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Nav butonlari - aktif olan primary, digerleri secondary
    for key, label in MENU_ITEMS:
        is_active = (key == st.session_state.active_page)
        st.button(
            label,
            key=f"nav_{key}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
            on_click=_set_page,
            args=(key,),
        )

    # Gizlilik cumlesi
    st.markdown(
        f'<div class="pvq-sidebar-privacy">{PRIVACY_TEXT}</div>',
        unsafe_allow_html=True,
    )

    # Kurulus blogu
    st.markdown(
        f'<div class="pvq-sidebar-org">'
        f'  <div class="pvq-sidebar-org-initial">{ORG_INITIAL}</div>'
        f'  <div>'
        f'    <div class="pvq-sidebar-org-name">{ORG_NAME}</div>'
        f'    <div class="pvq-sidebar-org-plan">{ORG_PLAN}</div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# UST BAR (Adim 1b)
# ============================================================
_gunler = ["Pzt", "Sal", "Car", "Per", "Cum", "Cmt", "Paz"]
_aylar = ["Oca", "Sub", "Mar", "Nis", "May", "Haz",
          "Tem", "Agu", "Eyl", "Eki", "Kas", "Ara"]
_now = datetime.now()
_tarih_str = f"{_now.day} {_aylar[_now.month - 1]} {_now.year} · {_gunler[_now.weekday()]}"

st.markdown(
    f'<div class="pvq-topbar">'
    f'  <div class="pvq-topbar-search">'
    f'    <span>🔍</span>'
    f'    <span class="pvq-topbar-search-text">Ara veya komut yaz...</span>'
    f'    <span class="pvq-topbar-search-kbd">⌘K</span>'
    f'  </div>'
    f'  <div class="pvq-topbar-right">'
    f'    <div class="pvq-topbar-plant">'
    f'      <span class="pvq-topbar-plant-label">Santral</span>'
    f'      <span class="pvq-topbar-plant-name">Konya GES</span>'
    f'    </div>'
    f'    <div class="pvq-topbar-live">'
    f'      <span class="pvq-topbar-live-dot"></span>'
    f'      <span>Veri akisi aktif</span>'
    f'    </div>'
    f'    <div class="pvq-topbar-date">{_tarih_str}</div>'
    f'    <div class="pvq-topbar-avatar">'
    f'      <div class="pvq-topbar-avatar-circle">D</div>'
    f'      <div class="pvq-topbar-avatar-info">'
    f'        <div class="pvq-topbar-avatar-name">Deniz Yilmaz</div>'
    f'        <div class="pvq-topbar-avatar-org">Anadolu Enerji A.S.</div>'
    f'      </div>'
    f'    </div>'
    f'  </div>'
    f'</div>',
    unsafe_allow_html=True,
)


# ============================================================
# ANA ICERIK
# ============================================================
active = st.session_state.active_page
if active in PAGE_RENDERERS:
    PAGE_RENDERERS[active]()
else:
    st.error(f"Bilinmeyen sayfa: {active}")


# ============================================================
# FOOTER
# ============================================================
st.markdown(
    f'<div class="pvq-footer">'
    f'  <div>{APP_VERSION}</div>'
    f'  <div class="pvq-footer-status">'
    f'    <span class="pvq-footer-dot"></span>'
    f'    <span>{STATUS_TEXT}</span>'
    f'  </div>'
    f'  <div>{COPYRIGHT}</div>'
    f'</div>',
    unsafe_allow_html=True,
)