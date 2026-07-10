"""
PVQuant Veri Yukleme Ekrani (Faz 2 Adim 3 + 4a)

Iki mod:
- Mod A (varsayilan): 'SCADA veriniz var mi?' - Hizli vs Kalibre yol ayrimi
- Mod B (scada_upload): CSV yukleme + load_csv cagrisi + ozet

Mod B'ye gecis: session_state.veri_yukleme_mod = 'scada_upload'
Adim 3'teki 'Kalibre tahmine gec' butonu bunu tetikler.
"""

import sys
from datetime import datetime
from pathlib import Path
import tempfile

import streamlit as st

from components import page_header
from design_tokens import PRIMARY, SUCCESS, TEXT_SECONDARY, TEXT_TERTIARY

# Backend import (Adim 4a)
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from pvquant.io.scada import load_csv


# ============================================================
# ORTAK: Sihirbaz adim gostergesi
# ============================================================

def _adim_gostergesi(aktif_adim: int = 2) -> None:
    """Sihirbaz - 1: Santral, 2: Veri yolu, 3: Sonuc."""
    def _dot(num, label, state):
        # state: 'done' | 'active' | 'pending'
        if state == "done":
            bg = SUCCESS
            fg = "white"
            metin_renk = SUCCESS
            weight = "500"
            icon = "✓"
        elif state == "active":
            bg = PRIMARY
            fg = "white"
            metin_renk = PRIMARY
            weight = "600"
            icon = str(num)
        else:
            bg = "#E2E6EA"
            fg = TEXT_TERTIARY
            metin_renk = TEXT_TERTIARY
            weight = "500"
            icon = str(num)
        return (
            f'<span style="display:inline-flex;align-items:center;gap:6px;'
            f'             color:{metin_renk};font-weight:{weight}">'
            f'  <span style="display:inline-flex;align-items:center;justify-content:center;'
            f'               width:20px;height:20px;border-radius:50%;'
            f'               background:{bg};color:{fg};font-size:11px">{icon}</span>'
            f'  {label}'
            f'</span>'
        )

    def _state(i):
        if i < aktif_adim:
            return "done"
        elif i == aktif_adim:
            return "active"
        else:
            return "pending"

    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:12px;
                    margin-bottom:32px;font-size:13px;
                    font-family:IBM Plex Mono,monospace">
          {_dot(1, "Santral bilgisi", _state(1))}
          <span style="color:#CBD5E1">·</span>
          {_dot(2, "Veri yolu", _state(2))}
          <span style="color:#CBD5E1">·</span>
          {_dot(3, "Sonuc", _state(3))}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# MOD A: Yol ayrimi kartlari
# ============================================================

def _yol_karti(baslik, ikon, sapma_txt, maddeler, buton_metni, onerilen, on_click_action):
    """Iki yol karti icin ortak render."""
    onerilen_rozet = ""
    kart_style = "border:1px solid #E2E6EA;background:white"
    if onerilen:
        onerilen_rozet = f"""
        <div style="position:absolute;top:-11px;right:24px">
          <span style="background:white;border:1px solid {SUCCESS};color:{SUCCESS};
                       padding:4px 12px;border-radius:999px;font-size:11px;
                       font-weight:600;letter-spacing:0.05em">ONERILEN</span>
        </div>
        """
        kart_style = f"border:2px solid {SUCCESS};background:white"

    sapma_renk = SUCCESS if onerilen else TEXT_SECONDARY

    maddeler_html = ""
    for m in maddeler:
        maddeler_html += (
            f'<li style="display:flex;align-items:flex-start;gap:10px;'
            f'           margin-bottom:12px;font-size:14px;color:#0F1B28">'
            f'  <span style="color:{TEXT_TERTIARY};margin-top:4px">•</span>'
            f'  <span>{m}</span>'
            f'</li>'
        )

    st.markdown(
        f"""
        <div style="position:relative;{kart_style};border-radius:8px;
                    padding:32px 28px 20px 28px;height:100%">
          {onerilen_rozet}
          <div style="font-size:22px;margin-bottom:16px">
            <span style="font-size:20px;margin-right:8px">{ikon}</span>
            <span style="font-weight:600">{baslik}</span>
          </div>
          <div style="font-size:14px;color:#3D4854;margin-bottom:20px">
            {sapma_txt.split('|')[0]}
          </div>
          <div style="margin-bottom:24px">
            <span style="font-size:36px;font-weight:700;color:{sapma_renk};
                         font-family:IBM Plex Mono,monospace">
              {sapma_txt.split('|')[1]}
            </span>
            <span style="font-size:14px;color:{TEXT_SECONDARY};margin-left:8px">
              beklenen sapma
            </span>
          </div>
          <ul style="list-style:none;padding:0;margin:0 0 20px 0">
            {maddeler_html}
          </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )
    # Butonu Streamlit ile - callback'i tetiklemek icin
    st.button(
        buton_metni,
        key=f"yol_{on_click_action}",
        use_container_width=True,
        type="primary" if onerilen else "secondary",
        on_click=lambda: st.session_state.update({"veri_yukleme_mod": on_click_action}),
    )


def _render_mod_a() -> None:
    """Mod A: SCADA veriniz var mi? - iki kart."""
    _adim_gostergesi(aktif_adim=2)

    st.markdown(
        f"""
        <div style="text-align:center;margin-bottom:40px">
          <div style="font-size:32px;font-weight:700;color:#0F1B28;
                      letter-spacing:-0.02em;margin-bottom:12px">
            SCADA veriniz var mi?
          </div>
          <div style="font-size:15px;color:{TEXT_SECONDARY}">
            Fark, modelin santralinizi ne kadar tanidiginda.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(2, gap="large")

    with cols[0]:
        _yol_karti(
            baslik="Hizli tahmin",
            ikon="⚡",
            sapma_txt="Veri yuklemeden — hemen simdi.|%5-10",
            maddeler=[
                "Veri yuklemeden, saniyeler icinde sonuc",
                "Profesyonel meteoroloji verisiyle 7 gunluk tahmin",
                "Diledigimiz an kalibre tahmine yukseltin",
            ],
            buton_metni="Hizli tahminle devam et",
            onerilen=False,
            on_click_action="hizli",
        )

    with cols[1]:
        _yol_karti(
            baslik="Kalibre tahmin",
            ikon="🛡",
            sapma_txt="SCADA verinizle — model kendini santralinize kalibre eder.|%1-3",
            maddeler=[
                "Model kendini gecmis uretiminize gore ayarlar",
                "Panel yonu ve egimi bilinmiyorsa model bulur",
                "En az 3 ay SCADA verisi gerekir — onerilen 12 ay",
            ],
            buton_metni="Kalibre tahmine gec",
            onerilen=True,
            on_click_action="scada_upload",
        )

    st.markdown(
        f"""
        <div style="text-align:center;margin-top:32px;font-size:13px;
                    color:{TEXT_SECONDARY};max-width:720px;
                    margin-left:auto;margin-right:auto">
          Veriniz azsa endiselenmeyin: 3 aydan kisa veri bulursak sizi engellemeyiz,
          hizli tahminle baslatip sonra yukseltmenizi oneririz.
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# MOD B: SCADA CSV yukleme + load_csv cagrisi
# ============================================================

def _render_mod_b_scada() -> None:
    """Mod B: CSV yukleme + load_csv + ozet."""
    _adim_gostergesi(aktif_adim=2)

    # Geri donme
    if st.button("← Yol ayrimina don", key="scada_geri", type="secondary"):
        st.session_state.veri_yukleme_mod = "yol_ayrimi"
        st.session_state.pop("scada_data", None)
        st.rerun()

    st.markdown(
        f"""
        <div style="margin:24px 0 8px 0">
          <div style="font-size:22px;font-weight:700;color:#0F1B28;
                      letter-spacing:-0.02em;margin-bottom:8px">
            SCADA verinizi yukleyin
          </div>
          <div style="font-size:14px;color:{TEXT_SECONDARY}">
            En az 3 ay veri onerilir. Turkce ve Ingilizce sutun adlari otomatik tanindir.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # File uploader
    uploaded = st.file_uploader(
        "CSV dosyasi",
        type=["csv"],
        key="scada_uploader",
        label_visibility="collapsed",
    )

    if uploaded is None:
        st.markdown(
            f"""
            <div style="margin-top:16px;padding:16px;background:#F7F8F9;
                        border:1px solid #E2E6EA;border-radius:8px;
                        font-size:13px;color:{TEXT_SECONDARY}">
              <strong>Ipucu:</strong> SCADA dosyanizin en az 'zaman' ve 'guc' sutunlarini
              icermesi yeterli. Isinim (POA), sicaklik, ruzgar gibi ek sutunlar varsa
              kalibrasyon daha isabetli olur.
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    # Yuklendi - load_csv cagir
    # Streamlit file_uploader BytesIO doner, load_csv Path bekliyor
    # Gecici dosyaya yazip yolu ver
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        tmp.write(uploaded.getvalue())
        tmp_path = tmp.name

    try:
        with st.spinner("Dosya okunuyor ve sutunlar tanindir..."):
            # Once virgul ile dene, olmazsa noktali virgul
            try:
                scada = load_csv(tmp_path, delimiter=",")
            except (ValueError, Exception):
                try:
                    scada = load_csv(tmp_path, delimiter=";", decimal=",")
                except Exception as e2:
                    st.error(f"Dosya okunamadi: {e2}")
                    return

        st.session_state.scada_data = scada
        st.session_state.scada_filename = uploaded.name

    except Exception as e:
        st.error(f"Dosya okunurken hata: {e}")
        return

    # Basari - ozet karti
    _scada_ozet_karti(scada, uploaded.name)


def _scada_ozet_karti(scada, filename: str) -> None:
    """Yuklenen SCADA'nin ozet karti."""
    n_kayit = len(scada.power_kw)
    baslangic = scada.power_kw.index.min()
    bitis = scada.power_kw.index.max()
    sure_gun = (bitis - baslangic).days

    # Tespit edilen ek sutunlar
    ek_sutunlar = []
    for isim, sutun in [
        ("POA (isinim)", scada.poa_irradiance),
        ("Enerji (kWh)", scada.energy_kwh),
    ]:
        if sutun is not None:
            ek_sutunlar.append(isim)
    # Diger optional sutunlari da kontrol et
    for attr, label in [
        ("temperature_ambient", "Ortam sicakligi"),
        ("temperature_module", "Modul sicakligi"),
        ("wind_speed", "Ruzgar hizi"),
    ]:
        val = getattr(scada, attr, None)
        if val is not None:
            ek_sutunlar.append(label)

    ek_sutunlar_html = ""
    if ek_sutunlar:
        rozet_html = "".join(
            f'<span style="display:inline-block;padding:4px 10px;'
            f'background:rgba(30,158,106,0.08);color:{SUCCESS};'
            f'border:1px solid rgba(30,158,106,0.2);'
            f'border-radius:999px;font-size:12px;margin-right:6px;'
            f'margin-bottom:6px;font-weight:500">{s}</span>'
            for s in ek_sutunlar
        )
        ek_sutunlar_html = f"""
        <div style="margin-top:16px">
          <div style="font-size:12px;color:{TEXT_TERTIARY};margin-bottom:8px;
                      text-transform:uppercase;letter-spacing:0.05em;font-weight:600">
            Ek sutunlar tespit edildi
          </div>
          <div>{rozet_html}</div>
        </div>
        """

    # Yeterlilik uyarisi
    yeterlilik = ""
    if sure_gun < 90:
        yeterlilik = f"""
        <div style="margin-top:16px;padding:12px 16px;
                    background:rgba(201,80,46,0.08);
                    border-left:3px solid #C9502E;
                    border-radius:4px;font-size:13px;color:#0F1B28">
          <strong>Dikkat:</strong> {sure_gun} gunluk veriniz var, 90 gunden az.
          Kalibre tahmin yerine Hizli tahmini onerdik.
        </div>
        """
    elif sure_gun < 365:
        yeterlilik = f"""
        <div style="margin-top:16px;padding:12px 16px;
                    background:rgba(31,82,136,0.06);
                    border-left:3px solid {PRIMARY};
                    border-radius:4px;font-size:13px;color:#0F1B28">
          <strong>Iyi:</strong> {sure_gun} gunluk veri kalibre tahmin icin yeterli.
          12 ay ({sure_gun}/365) veriye ulasirsaniz mevsimsel dogruluk artar.
        </div>
        """
    else:
        yeterlilik = f"""
        <div style="margin-top:16px;padding:12px 16px;
                    background:rgba(30,158,106,0.08);
                    border-left:3px solid {SUCCESS};
                    border-radius:4px;font-size:13px;color:#0F1B28">
          <strong>Mukemmel:</strong> {sure_gun} gunluk veri kalibrasyon icin ideal.
        </div>
        """

    baslangic_str = baslangic.strftime("%d %b %Y").replace(baslangic.strftime("%b"),
        {"Jan":"Oca","Feb":"Sub","Mar":"Mar","Apr":"Nis","May":"May","Jun":"Haz",
         "Jul":"Tem","Aug":"Agu","Sep":"Eyl","Oct":"Eki","Nov":"Kas","Dec":"Ara"}
        [baslangic.strftime("%b")])
    bitis_str = bitis.strftime("%d %b %Y").replace(bitis.strftime("%b"),
        {"Jan":"Oca","Feb":"Sub","Mar":"Mar","Apr":"Nis","May":"May","Jun":"Haz",
         "Jul":"Tem","Aug":"Agu","Sep":"Eyl","Oct":"Eki","Nov":"Kas","Dec":"Ara"}
        [bitis.strftime("%b")])

    st.markdown(
        f"""
        <div class="pvq-card" style="margin-top:24px;
             border-left:3px solid {SUCCESS}">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:16px">
            <span style="color:{SUCCESS};font-size:18px">✓</span>
            <span style="font-size:15px;font-weight:600">
              {filename} - Basariyla okundu
            </span>
          </div>
          <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:24px">
            <div>
              <div style="font-size:11px;color:{TEXT_TERTIARY};
                          text-transform:uppercase;letter-spacing:0.05em;
                          font-weight:600;margin-bottom:6px">Kayit sayisi</div>
              <div style="font-family:IBM Plex Mono,monospace;font-size:20px;
                          font-weight:700;color:#0F1B28">
                {n_kayit:,}</div>
            </div>
            <div>
              <div style="font-size:11px;color:{TEXT_TERTIARY};
                          text-transform:uppercase;letter-spacing:0.05em;
                          font-weight:600;margin-bottom:6px">Tarih araligi</div>
              <div style="font-family:IBM Plex Mono,monospace;font-size:14px;
                          font-weight:600;color:#0F1B28">
                {baslangic_str}<br>{bitis_str}</div>
            </div>
            <div>
              <div style="font-size:11px;color:{TEXT_TERTIARY};
                          text-transform:uppercase;letter-spacing:0.05em;
                          font-weight:600;margin-bottom:6px">Sure</div>
              <div style="font-family:IBM Plex Mono,monospace;font-size:20px;
                          font-weight:700;color:#0F1B28">
                {sure_gun} gun</div>
            </div>
          </div>
          {ek_sutunlar_html}
          {yeterlilik}
        </div>
        """.replace(",", "."),
        unsafe_allow_html=True,
    )

    st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Farkli dosya sec", key="farkli_dosya", use_container_width=True):
            st.session_state.pop("scada_data", None)
            st.session_state.pop("scada_filename", None)
            st.rerun()
    with col2:
        st.button(
            "Kalibrasyona gec →",
            key="kalibrasyona_gec",
            use_container_width=True,
            type="primary",
            disabled=True,
            help="Kalibrasyon sayfasi Adim 4b'de gelecek",
        )


# ============================================================
# ANA render
# ============================================================

def render_veri_yukleme() -> None:
    """Veri Yukleme sayfasi - iki modlu."""
    # Session state init
    if "veri_yukleme_mod" not in st.session_state:
        st.session_state.veri_yukleme_mod = "yol_ayrimi"

    mod = st.session_state.veri_yukleme_mod

    if mod == "scada_upload":
        page_header(
            "Veri Yukleme",
            "SCADA verinizi yukleyin, model sutunlarinizi otomatik tanisin",
        )
        _render_mod_b_scada()
    elif mod == "hizli":
        # Hizli tahmin secildi - Adim 5'e yonlendir (henuz yok)
        st.session_state.veri_yukleme_mod = "yol_ayrimi"
        st.info("Hizli tahmin akisi Adim 5'te gelecek. Simdilik yol ayrimina donduruldunuz.")
        _render_mod_a_wrapper()
    else:
        _render_mod_a_wrapper()


def _render_mod_a_wrapper():
    """Mod A icin sayfa basligi + gorsel."""
    page_header(
        "Veri Yukleme",
        "Tahmin yolunuzu secin — SCADA veriniz varsa kalibre tahmine gecin",
    )
    _render_mod_a()