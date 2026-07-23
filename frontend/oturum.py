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
    # Anayasa Adım 7 (v2.10): login görünümü tek dosyaya çıkarıldı
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
    YENI = "＋ Yeni santral ekle"                     # v2.39-B
    secenekler = list(adlar) + [YENI]
    varsayilan = 0
    aktif = str(st.session_state.get("aktif_plant_id") or "")
    if aktif in adlar.values():
        varsayilan = list(adlar.values()).index(aktif)
    sec = st.sidebar.selectbox(
        "Santral", secenekler, index=varsayilan, key="aktif_santral_ad"
    )
    if sec == YENI:
        # yeni-santral modu: aktif kaydi birak, Veri Yukleme Adim 1'e
        st.session_state.aktif_plant_id = None
        st.session_state.active_page = "veri_yukleme"
        return None
    st.session_state.aktif_plant_id = adlar[sec]
    # v2.42: santral yonetimi — silme, ad-onayli (kalici islem)
    secili = next(p for p in ps if str(p["id"]) == adlar[sec])
    with st.sidebar.expander("Santral yönetimi"):
        st.caption(f"'{secili['name']}' ve TÜM verisi kalıcı silinir "
                   "(SCADA, kalibrasyon, tahminler, raporlar).")
        onay = st.text_input("Silmek için santral adını yazın",
                             key=f"sil_onay_{secili['id']}")
        if st.button("Santralı kalıcı sil", type="secondary",
                     use_container_width=True,
                     disabled=(onay.strip() != secili["name"]),
                     key=f"sil_btn_{secili['id']}"):
            rapor = plant_service.sil(auth["tenant_id"], secili["id"])
            st.session_state.aktif_plant_id = None
            st.session_state.pop("aktif_santral_ad", None)
            st.toast(f"Silindi — {sum(rapor.values())} kayıt.")
            st.rerun()
    st.session_state.aktif_plant_id = adlar[sec]
    return secili
    return next(p for p in ps if str(p["id"]) == adlar[sec])
