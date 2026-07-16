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
    # Anayasa 3.3 — orta kolonda tek kart (mock detay P2 Adim 4'te temizlendi)
    _l, orta, _r = st.columns([1, 2, 1])
    with orta:
        st.markdown(
            '<div class="pv-kart" style="max-width:380px;margin:0 auto">'
            '<div style="text-align:center;font-size:28px;'
            'font-weight:650;margin-bottom:4px">⚡ PVQuant</div>'
            '<div style="text-align:center;color:var(--ikincil);'
            'font-size:13px;margin-bottom:20px">'
            'Santralinizin kanıtlı üretim tahmini</div>',
            unsafe_allow_html=True,
        )
        with st.form("login", clear_on_submit=False):
            e = st.text_input("E-posta", key="login_email")
            p = st.text_input("Şifre", type="password", key="login_sifre")
            submitted = st.form_submit_button("Gir", type="primary",
                                              use_container_width=True)
            if submitted:
                r = auth_service.giris(e, p)
                if r is None:
                    st.markdown(
                        '<div style="color:var(--negatif);font-size:12px;'
                        'margin-top:8px">E-posta veya şifre hatalı.</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.session_state.auth = r
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
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
