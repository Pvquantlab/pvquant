"""Login görünümü — Anayasa Adım 7 (§6.7 revize, Zeyilname v2.10).

TASARIM TEZİ: "Kontrol odasının kapısı" — sol panelde odanın camından
görünen manzara (koyu zemin + imza Gün Işığı Eğrisi illüstrasyonu +
GERÇEK referans kanıtı), sağda milimetrik form kartı. Süs yok, karakter
var. Animasyon/parallax/video YASAK (K8); marka rengi aksan (buton +
eğri), zemin boğulmaz.

MANTIK SÖZLEŞMESİ: giris_bekcisi'nin auth mantığı BİREBİR korunmuştur
(auth_service.giris -> session_state.auth -> rerun). Bu dosya yalnız
GÖRSEL katmanı değiştirir + "Yeni firma kaydı"nı mevcut
auth_service.tenant_ve_admin_olustur servisine bağlar (yeni backend yok).

KULLANIM: frontend/oturum.py'deki giris_bekcisi içinde, auth yoksa
çizilen eski form bloğunu `login_ekrani()` çağrısıyla değiştir;
fonksiyon giriş başarılıysa session'ı kurup st.rerun() eder (eskisiyle
aynı akış). K1 notu: kanıt satırındaki sayılar GERÇEKTİR (referans
santral holdout sonucu) — güncellenirse tek yer burası.
"""
from __future__ import annotations

import time

import streamlit as st

from pvquant.services import auth_service

# İmza eğri — dekoratif illüstrasyon (eksen/sayı yok: veri iddiası
# taşımaz, K1 ile çelişmez). Prototip estetiğiyle birebir.
_EGRI_SVG = """
<svg viewBox="0 0 420 150" xmlns="http://www.w3.org/2000/svg" role="img"
     aria-label="Günlük üretim eğrisi illüstrasyonu">
  <path d="M 10 130 C 80 128, 110 40, 195 34 C 240 31, 250 45, 268 60"
        fill="none" stroke="#F59E0B" stroke-width="2.6"/>
  <path d="M 10 130 C 80 128, 110 40, 195 34 C 240 31, 250 45, 268 60
           L 268 138 L 10 138 Z" fill="rgba(245,158,11,.14)"/>
  <path d="M 268 60 C 300 88, 350 122, 410 132" fill="none"
        stroke="#6FA8DC" stroke-width="2" stroke-dasharray="3 6"/>
  <line x1="268" y1="18" x2="268" y2="138" stroke="#7E93A0"
        stroke-width="1" stroke-dasharray="4 4"/>
  <text x="268" y="12" text-anchor="middle" fill="#9FB3BE"
        font-family="ui-monospace,monospace" font-size="9">şimdi</text>
</svg>"""


def login_ekrani() -> None:
    """Tam login ekranı. Başarılı girişte session kurar + rerun."""
    sol, sag = st.columns([11, 9], gap="large")

    # ---------------- SOL: kontrol odasının camı ----------------
    with sol:
        st.markdown(f"""
        <div class="pv-login-panel">
          <div class="pv-login-marka">⚡ PVQuant</div>
          <div class="pv-login-slogan">Santralinizin kanıtlı
          üretim tahmini</div>
          <div class="pv-login-egri">{_EGRI_SVG}</div>
          <div class="pv-login-kanit">
            <div class="pv-eyebrow" style="color:#7E93A0">REFERANS
            SANTRAL · HOLDOUT SINAVI</div>
            <div class="pv-login-kanit-sayi">MAPE %38,7 → %14,8</div>
            <div class="pv-login-kanit-not">saf fizik → hibrit ·
            kronolojik son %20 üzerinde ölçüldü</div>
          </div>
          <div class="pv-login-ilkeler">
            <span>● Kendi verinizle kalibre</span>
            <span>● Her sabah 7 günlük tahmin</span>
            <span>● Doğruluk karnesi her gece</span>
          </div>
        </div>""", unsafe_allow_html=True)

    # ---------------- SAĞ: form kartı ----------------
    with sag:
        st.markdown('<div class="pv-login-baslik">Hesabınıza giriş '
                    'yapın</div>', unsafe_allow_html=True)
        with st.form("login", clear_on_submit=False):
            e = st.text_input("E-posta", key="login_email",
                              placeholder="ornek@firma.com")
            p = st.text_input("Şifre", type="password",
                              key="login_sifre")
            gonder = st.form_submit_button("Gir", type="primary",
                                           use_container_width=True)
        if gonder:
            r = auth_service.giris(e, p)              # MANTIK: birebir
            if r is None:
                n = st.session_state.get("giris_deneme", 0) + 1
                st.session_state["giris_deneme"] = n
                time.sleep(min(2 ** min(n, 4), 12))   # 2-4-8-12sn artan fren
                st.markdown('<div class="pv-login-hata">E-posta veya '
                            'şifre hatalı.</div>', unsafe_allow_html=True)
            else:
                st.session_state.pop("giris_deneme", None)
                st.session_state.auth = r
                st.rerun()

        st.markdown('<div class="pv-login-yardim">'
                    '<span class="pv-login-pasif" title="Yakında — '
                    'şimdilik yöneticinizle iletişime geçin">Şifremi '
                    'unuttum</span></div>', unsafe_allow_html=True)

        with st.expander("Yeni firma kaydı"):
            with st.form("kayit"):
                f = st.text_input("Firma adı")
                ke = st.text_input("Yönetici e-postası")
                ks = st.text_input("Şifre", type="password",
                                   key="kayit_sifre")
                kg = st.form_submit_button("Firmayı oluştur",
                                           use_container_width=True)
            if kg:
                if not (f and ke and len(ks) >= 8):
                    st.markdown('<div class="pv-login-hata">Tüm alanlar '
                        'gerekli; şifre en az 8 karakter.</div>',
                        unsafe_allow_html=True)
                else:
                    auth_service.tenant_ve_admin_olustur(f, ke, ks)
                    r = auth_service.giris(ke, ks)    # otomatik giriş
                    if r:
                        st.session_state.auth = r
                        st.rerun()

        with st.expander("Kişisel verilerin korunması (KVKK)"):
            from pathlib import Path
            st.markdown(Path("assets/kvkk_aydinlatma.md")
                        .read_text(encoding="utf-8"))
        st.markdown('<div class="pv-login-footer">PVQuant · '
                    '<span class="pv-login-durum">● Tüm sistemler çalışır durumda'
                    '</span> · © 2026</div>', unsafe_allow_html=True)
