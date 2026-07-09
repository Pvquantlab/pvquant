"""
PVQuant Veri Yukleme Ekrani (Faz 2 Adim 3)

'SCADA veriniz var mi?' - kullanicinin Hizli tahmin vs Kalibre tahmin
arasinda sectigi yol ayrimi.
"""

import streamlit as st

from components import page_header
from design_tokens import PRIMARY, SUCCESS, TEXT_SECONDARY, TEXT_TERTIARY


def _adim_gostergesi() -> None:
    """Sihirbaz adim gostergesi - sayfa basliginin altinda."""
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:12px;
                    margin-bottom:32px;font-size:13px;
                    font-family:IBM Plex Mono,monospace">
          <span style="display:inline-flex;align-items:center;gap:6px;color:{SUCCESS}">
            <span style="display:inline-flex;align-items:center;justify-content:center;
                         width:20px;height:20px;border-radius:50%;
                         background:{SUCCESS};color:white;font-size:11px">✓</span>
            1 · Santral bilgisi
          </span>
          <span style="color:#CBD5E1">·</span>
          <span style="display:inline-flex;align-items:center;gap:6px;
                       color:{PRIMARY};font-weight:600">
            <span style="display:inline-flex;align-items:center;justify-content:center;
                         width:20px;height:20px;border-radius:50%;
                         background:{PRIMARY};color:white;font-size:11px">2</span>
            Veri yolu
          </span>
          <span style="color:#CBD5E1">·</span>
          <span style="display:inline-flex;align-items:center;gap:6px;color:{TEXT_TERTIARY}">
            <span style="display:inline-flex;align-items:center;justify-content:center;
                         width:20px;height:20px;border-radius:50%;
                         background:#E2E6EA;color:{TEXT_TERTIARY};font-size:11px">3</span>
            Sonuc
          </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _yol_karti(
    baslik: str,
    ikon: str,
    sapma_txt: str,
    maddeler: list,
    buton_metni: str,
    onerilen: bool,
    hedef_sayfa: str,
) -> None:
    """Iki yol karti icin ortak render."""
    onerilen_rozet = ""
    kart_style = f"border:1px solid #E2E6EA;background:white"
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
    buton_bg = PRIMARY if onerilen else "white"
    buton_color = "white" if onerilen else PRIMARY
    buton_border = PRIMARY

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
                    padding:32px 28px 28px 28px;height:100%">
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
          <ul style="list-style:none;padding:0;margin:0 0 28px 0">
            {maddeler_html}
          </ul>
          <a href="?p={hedef_sayfa}" target="_self"
             style="display:block;text-align:center;padding:12px;
                    background:{buton_bg};color:{buton_color};
                    border:1px solid {buton_border};border-radius:6px;
                    text-decoration:none;font-weight:600;font-size:14px">
            {buton_metni}
          </a>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_veri_yukleme() -> None:
    """Veri Yukleme ekraninin tam render'i."""
    page_header(
        "Veri Yukleme",
        "Tahmin yolunuzu secin — SCADA veriniz varsa kalibre tahmine gecin",
    )

    _adim_gostergesi()

    # Ortada buyuk soru
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

    # Iki kart yan yana
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
            hedef_sayfa="tahminler",
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
            hedef_sayfa="kalibrasyon",
        )

    # Alt not
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