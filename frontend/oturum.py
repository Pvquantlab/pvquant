"""Anayasa 3.3 + El Kitabi P2 §5 — login bekcisi + sidebar santral secici.
Her sayfanin en basinda (tema.kur'dan sonra) cagrilir."""
from __future__ import annotations
import streamlit as st
from pvquant.services import auth_service, plant_service


def giris_bekcisi() -> dict | None:
    """Her sayfanin EN BASINDA cagrilir. Girilmemisse login formu cizer
    ve None doner (sayfa icerigini cizme!). Girilmisse claims doner."""
    if "auth" in st.session_state:
        return st.session_state.auth
    # Anayasa Adim 7 (v2.10): login gorunumu tek dosyaya cikarildi
    from login_gorunum import login_ekrani
    login_ekrani()
    return None


def santral_secici(auth: dict) -> dict | None:
    """Sidebar'da santral listesi; secilen SANTRAL DICT'ini doner.
    Session'da yalniz plant_id tutulur — profil verisi DEGIL (Kural)."""
    ps = plant_service.listele(auth["tenant_id"])
    if not ps:
        st.sidebar.info(
            "Henüz santral yok — Santralim sayfasından ekleyin."
        )
        return None
    adlar = {p["name"]: str(p["id"]) for p in ps}
    sec = st.sidebar.selectbox(
        "Santral", list(adlar), key="aktif_santral_ad"
    )
    st.session_state.aktif_plant_id = adlar[sec]
    return next(p for p in ps if str(p["id"]) == adlar[sec])
