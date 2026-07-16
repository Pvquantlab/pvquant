"""
PVQuant ana giris noktasi + kalici cerceve (sidebar + top bar).
Anayasa 3.2 (cerceve) + El Kitabi P2 5b (dönüsüm kalibi) uyumlu.

Calistirmak:
    cd ~/Desktop/pvquant
    source .venv/bin/activate
    streamlit run frontend/Ana.py
"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import streamlit as st

# --- Anayasa: tema + auth (Bolum 8.1 + 3.3) ---
import tema
from oturum import giris_bekcisi, santral_secici

# --- Eski cerceve bilesenleri (styles.py Adim 2'de yenilenir) ---
from design_tokens import MENU_ITEMS, PRIVACY_TEXT, APP_VERSION, COPYRIGHT
from styles import inject_global_css
from sayfalar import PAGE_RENDERERS

# ============================================================
# 1) TEMA (set_page_config + styles.css enjeksiyonu)
# ============================================================
tema.kur("Santralim")   # Ana giris varsayilan sayfasi
inject_global_css()     # eski top bar/sidebar CSS'i (styles.py) hala aktif

# ============================================================
# 2) SESSION STATE
# ============================================================
if "active_page" not in st.session_state:
    st.session_state.active_page = "santralim"


def _set_page(key: str) -> None:
    st.session_state.active_page = key


# ============================================================
# 3) GIRIS BEKCISI (Anayasa 3.3)
# ============================================================
auth = giris_bekcisi()
if auth is None:
    st.stop()


# ============================================================
# 4) SIDEBAR (Anayasa 3.2)
# ============================================================
santral = santral_secici(auth)

with st.sidebar:
    st.markdown(
        '<div class="pvq-sidebar-brand">'
        '<span>⚡</span>'
        '<span>PVQuant</span>'
        '</div>',
        unsafe_allow_html=True,
    )
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
    st.markdown(
        f'<div class="pvq-sidebar-privacy">{PRIVACY_TEXT}</div>',
        unsafe_allow_html=True,
    )
    # Kurulus blogu: tenant adı — sistem_baglami ile tek okuma
    from sqlalchemy import text
    from pvquant.db import sistem_baglami
    if "tenant_name" not in st.session_state:
        with sistem_baglami() as s:
            row = s.execute(text("SELECT name FROM tenants WHERE id=:t"),
                            {"t": auth["tenant_id"]}).first()
        st.session_state.tenant_name = row.name if row else "—"
    org_initial = st.session_state.tenant_name[0].upper() if st.session_state.tenant_name else "—"
    st.markdown(
        f'<div class="pvq-sidebar-org">'
        f'  <div class="pvq-sidebar-org-initial">{org_initial}</div>'
        f'  <div>'
        f'    <div class="pvq-sidebar-org-name">{st.session_state.tenant_name}</div>'
        f'    <div class="pvq-sidebar-org-plan">{auth["role"].capitalize()}</div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )

# ============================================================
# 5) UST BAR (Anayasa 3.2 — kanit seridi)
# ============================================================
_gunler = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
_aylar = ["Oca", "Şub", "Mar", "Nis", "May", "Haz",
          "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
_now = datetime.now()
_tarih_str = f"{_now.day} {_aylar[_now.month - 1]} {_now.year} · {_gunler[_now.weekday()]}"
_santral_ad = santral["name"] if santral else "—"

# K1: gercek kalibrasyon yoksa "Kalibre değil" (mock 'Veri akisi aktif' KALDIRILDI)
# Mod bilgisi P3'te ozet_service'ten gelecek; simdilik notr rozet
st.markdown(
    f'<div class="pvq-topbar">'
    f'  <div class="pvq-topbar-search">'
    f'    <span>🔍</span>'
    f'    <span class="pvq-topbar-search-text">Ara veya komut yaz…</span>'
    f'    <span class="pvq-topbar-search-kbd">⌘K</span>'
    f'  </div>'
    f'  <div class="pvq-topbar-right">'
    f'    <div class="pvq-topbar-plant">'
    f'      <span class="pvq-topbar-plant-label">Santral</span>'
    f'      <span class="pvq-topbar-plant-name">{_santral_ad}</span>'
    f'    </div>'
    f'    <div class="pvq-topbar-date">{_tarih_str}</div>'
    f'    <div class="pvq-topbar-avatar">'
    f'      <div class="pvq-topbar-avatar-circle">{org_initial}</div>'
    f'      <div class="pvq-topbar-avatar-info">'
    f'        <div class="pvq-topbar-avatar-name">{auth.get("role","").capitalize()}</div>'
    f'        <div class="pvq-topbar-avatar-org">{st.session_state.tenant_name}</div>'
    f'      </div>'
    f'    </div>'
    f'  </div>'
    f'</div>',
    unsafe_allow_html=True,
)

# ============================================================
# 6) ANA ICERIK (mevcut PAGE_RENDERERS mantigi korundu)
# ============================================================
active = st.session_state.active_page
if active in PAGE_RENDERERS:
    PAGE_RENDERERS[active]()
else:
    st.error(f"Bilinmeyen sayfa: {active}")

# ============================================================
# 7) FOOTER
# ============================================================
_STATUS = "Sistem sağlıklı"
st.markdown(
    f'<div class="pvq-footer">'
    f'  <div>{APP_VERSION}</div>'
    f'  <div class="pvq-footer-status">'
    f'    <span class="pvq-footer-dot"></span>'
    f'    <span>{_STATUS}</span>'
    f'  </div>'
    f'  <div>{COPYRIGHT}</div>'
    f'</div>',
    unsafe_allow_html=True,
)
