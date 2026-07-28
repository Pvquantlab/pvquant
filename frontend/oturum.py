"""Anayasa 3.3 + El Kitabi P2 §5 — login bekcisi + sidebar santral secici.
Her sayfanin en basinda (tema.kur'dan sonra) cagrilir."""
from __future__ import annotations
import streamlit as st
from pvquant.services import auth_service, plant_service

# v2.50 Faz-1: koyu tema gecersiz kilma seti — yalniz anahtar acikken
# basilir. Isik mimarisi korunur: gece yuzeyleri (hero/kunye/sidebar)
# sabit kalir, kanvas/kartlar token takasiyla doner.
_KOYU_CSS = """<style>
:root{ --zemin:#0E1822; --kart:#14202E; --cizgi:#22303C;
  --metin:#E8EDF1; --ikincil:#A7B8C2; --soluk:#7C8798;
  --marka-acik:#0F3A30; --vurgu-acik:#3A2E14;
  --pozitif-acik:#0F3A30; --negatif-acik:#3A1720;
  --golge:none; --golge-hover:none; }
.stApp{ background:var(--zemin); }
.stApp p, .stApp label, .stApp span, .stApp li,
.stApp h1,.stApp h2,.stApp h3 { color:var(--metin); }
.pv-banner-bilgi{ background:#12263A; color:#9EC5FF; border-color:#1E3A5C; }
.pv-banner-hata{ background:#3A1720; color:#FF9EA8; border-color:#5C1E2A; }
.pv-uyari-kart{ background:#2E2410; border-color:#4A3A14; }
.pv-uyari-kart .pv-uyari-metin{ color:var(--metin); }
.pv-bos{ background:#121D28; border-color:#22303C; }
.pv-kart, .pv-kart div { color: var(--metin); }
.pv-adimlar { color: var(--soluk); }
</style>"""


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
    # v2.50: tema anahtari — her kimlikli durumda calisir (yeni-santral
    # modu ve santralsiz kiraci dahil), o yuzden fonksiyonun BASINDA.
    if st.sidebar.toggle("Koyu tema", key="koyu_tema"):
        st.markdown(_KOYU_CSS, unsafe_allow_html=True)

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
    secili = next(p for p in ps if str(p["id"]) == adlar[sec])
    # v2.54 (eski v2.42): santral yonetimi — ARSIVLEME, ad-onayli
    with st.sidebar.expander("Santral yönetimi"):
        st.caption(f"'{secili['name']}' arşivlenir: listelerden kalkar, "
                   "verisi (SCADA, kalibrasyon, tahminler) denetim için saklanır.")
        onay = st.text_input("Arşivlemek için santral adını yazın",
                             key=f"sil_onay_{secili['id']}")
        if st.button("Santralı arşivle", type="secondary",
                     width="stretch",
                     disabled=(onay.strip() != secili["name"]),
                     key=f"sil_btn_{secili['id']}"):
            plant_service.sil(auth["tenant_id"], secili["id"])
            st.session_state.aktif_plant_id = None
            st.session_state.pop("aktif_santral_ad", None)
            st.toast("Arşivlendi — verisi saklanıyor.")
            st.rerun()
    return secili