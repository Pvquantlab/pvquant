"""
PVQuant Raporlar Ekrani (Faz 2 Adim 6)

Kalibre tahmin sonuclarini 3 farkli formatta (PDF/Excel/JSON) disa aktarir.

Adim 6a: Iskelet + KPI seridi + guard'lar          [OK]
Adim 6b: 3 format karti (gorsel)                    [OK - 14 Temmuz]
Adim 6c: Excel + JSON gercek isleyisi
Adim 6d: PDF yonetici ozeti (fpdf2)
Adim 6e: Rapor gecmisi (dekoratif)
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from components import page_header
from design_tokens import (
    PRIMARY, SUCCESS, WARNING,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY,
)


# ============================================================
# Guard - kalibrasyon yoksa
# ============================================================

def _uyari_kalibrasyon_yok() -> None:
    st.markdown(
        f"""
        <div class="pvq-card" style="border-left:3px solid {WARNING};
             text-align:center;padding:48px 24px">
          <div style="font-size:48px;margin-bottom:16px">📄</div>
          <div style="font-size:20px;font-weight:600;color:#0F1B28;
                      margin-bottom:12px">
            Once kalibrasyon yapin
          </div>
          <div style="font-size:14px;color:{TEXT_SECONDARY};max-width:480px;
                      margin:0 auto 24px auto">
            Rapor uretmek icin oncelikle SCADA verinizi yukleyip
            modeli santralinize kalibre etmelisiniz.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(
            "Kalibrasyon sayfasina git",
            key="raporlar_git_kalibrasyon",
            use_container_width=True,
            type="primary",
        ):
            st.session_state.active_page = "kalibrasyon"
            st.rerun()


# ============================================================
# Guard - forecast yoksa
# ============================================================

def _uyari_forecast_yok() -> None:
    st.markdown(
        f"""
        <div class="pvq-card" style="border-left:3px solid {WARNING};
             text-align:center;padding:48px 24px">
          <div style="font-size:48px;margin-bottom:16px">📊</div>
          <div style="font-size:20px;font-weight:600;color:#0F1B28;
                      margin-bottom:12px">
            Once tahmin olusturun
          </div>
          <div style="font-size:14px;color:{TEXT_SECONDARY};max-width:480px;
                      margin:0 auto 24px auto">
            Rapor icerigi 7 gunluk tahmine dayanir. Once Tahminler
            sayfasina gidip tahmini olusturun, sonra buraya donun.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(
            "Tahminler sayfasina git",
            key="raporlar_git_tahminler",
            use_container_width=True,
            type="primary",
        ):
            st.session_state.active_page = "tahminler"
            st.rerun()


# ============================================================
# 6a: KPI seridi
# ============================================================

def _kpi_seridi() -> None:
    from datetime import datetime

    result = st.session_state.forecast_result
    n_saat = len(result.hourly)

    # Boyut tahmini: kaba hesap (satir sayisi * kolon sayisi * ~10 byte)
    boyut_kb = int((n_saat * len(result.hourly.columns) * 10) / 1024)

    bugun = datetime.now().strftime("%d %b").replace(" 0", " ")

    kpi_cols = st.columns(4)
    with kpi_cols[0]:
        st.markdown(
            f'<div class="pvq-card">'
            f'<div class="pvq-microlabel">SON RAPOR</div>'
            f'<div class="pvq-kpi-value">'
            f'<span class="pvq-mono">{bugun}</span>'
            f'</div>'
            f'<div class="pvq-kpi-subtitle">bugun</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with kpi_cols[1]:
        st.markdown(
            f'<div class="pvq-card">'
            f'<div class="pvq-microlabel">FORMAT</div>'
            f'<div class="pvq-kpi-value">'
            f'<span class="pvq-mono">3</span>'
            f'<span class="pvq-kpi-unit">tip</span>'
            f'</div>'
            f'<div class="pvq-kpi-subtitle">PDF, Excel, JSON</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with kpi_cols[2]:
        st.markdown(
            f'<div class="pvq-card">'
            f'<div class="pvq-microlabel">VERI KAPSAMI</div>'
            f'<div class="pvq-kpi-value">'
            f'<span class="pvq-mono">{n_saat}</span>'
            f'<span class="pvq-kpi-unit">saat</span>'
            f'</div>'
            f'<div class="pvq-kpi-subtitle">7 gun tahmin</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with kpi_cols[3]:
        st.markdown(
            f'<div class="pvq-card">'
            f'<div class="pvq-microlabel">BOYUT</div>'
            f'<div class="pvq-kpi-value">'
            f'<span class="pvq-mono">~{boyut_kb}</span>'
            f'<span class="pvq-kpi-unit">KB</span>'
            f'</div>'
            f'<div class="pvq-kpi-subtitle">Excel tahmini</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ============================================================
# 6b: 3 format karti
# ============================================================

def _format_karti(
    ikon: str,
    baslik: str,
    aciklama: str,
    hedef: str,
    boyut_kb: int,
    buton_key: str,
    aktif: bool = False,
    aksiyon_notu: str = "",
) -> bool:
    """Tek bir format kartini render eder.
    
    Args:
        ikon: Emoji ikonu (48px gosterilir).
        baslik: Format adi.
        aciklama: 1-2 satirlik aciklama.
        hedef: Hedef kitle etiketi (kucuk yazi).
        boyut_kb: Yaklasik dosya boyutu (KB).
        buton_key: Streamlit button key.
        aktif: False ise buton disabled, hazir degil notu goserilir.
        aksiyon_notu: Aktif degilse gosterilecek not.
    
    Returns:
        Butona tiklanip tiklanmadigi.
    """
    st.markdown(
        f"""
        <div class="pvq-card" style="min-height:280px;
             display:flex;flex-direction:column;padding:24px">
          <div style="font-size:40px;margin-bottom:12px">{ikon}</div>
          <div style="font-size:17px;font-weight:600;color:{TEXT_PRIMARY};
                      margin-bottom:8px">{baslik}</div>
          <div style="font-size:13px;color:{TEXT_SECONDARY};
                      line-height:1.5;margin-bottom:16px;flex-grow:1">
            {aciklama}
          </div>
          <div style="display:flex;justify-content:space-between;
                      align-items:center;margin-bottom:12px;
                      padding-top:12px;border-top:1px solid #E5E7EB">
            <div>
              <div class="pvq-microlabel" style="margin-bottom:2px">HEDEF</div>
              <div style="font-size:12px;color:{TEXT_PRIMARY};
                          font-weight:500">{hedef}</div>
            </div>
            <div style="text-align:right">
              <div class="pvq-microlabel" style="margin-bottom:2px">BOYUT</div>
              <div style="font-size:12px;color:{TEXT_PRIMARY};
                          font-weight:500" class="pvq-mono">~{boyut_kb} KB</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    if aktif:
        return st.button(
            f"↓  {baslik} indir",
            key=buton_key,
            use_container_width=True,
            type="primary",
        )
    else:
        st.button(
            f"↓  {baslik} indir",
            key=buton_key,
            use_container_width=True,
            disabled=True,
            help=aksiyon_notu or "Bu format sonraki adimda gelecek",
        )
        return False


def _format_kartlari() -> None:
    """Uc format kartini yan yana gosterir."""
    result = st.session_state.forecast_result
    n_saat = len(result.hourly)
    n_kolon = len(result.hourly.columns)
    
    # Boyut tahminleri (kaba hesap - 6c/6d'de gercek boyut alinacak)
    excel_kb = int((n_saat * n_kolon * 12) / 1024) + 15  # header/formatting overhead
    json_kb = int((n_saat * n_kolon * 25) / 1024) + 2    # JSON verbose
    pdf_kb = 45  # tek sayfa yonetici ozeti ~40-50 KB
    
    st.markdown(
        f'<div style="margin-top:24px;margin-bottom:12px">'
        f'<div style="font-size:15px;font-weight:600;color:{TEXT_PRIMARY};'
        f'margin-bottom:4px">Format secin</div>'
        f'<div style="font-size:12px;color:{TEXT_SECONDARY}">'
        f'Her format farkli bir kullanim icin optimize edildi.'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    
    col_pdf, col_excel, col_json = st.columns(3)
    
    with col_pdf:
        pdf_tiklandi = _format_karti(
            ikon="📄",
            baslik="PDF Yonetici Ozeti",
            aciklama=(
                "Tek sayfada 7 gunluk tahmin ozeti: toplam uretim, "
                "gunluk grafik, kritik notlar. E-posta ekine, sunuma uygun."
            ),
            hedef="Yonetim, e-posta paylasimi",
            boyut_kb=pdf_kb,
            buton_key="rapor_pdf_indir",
            aktif=False,
            aksiyon_notu="PDF uretimi Adim 6d'de gelecek",
        )
    
    with col_excel:
        excel_tiklandi = _format_karti(
            ikon="📊",
            baslik="Excel Tam Veri",
            aciklama=(
                f"{n_saat} satirlik saatlik detay: guc (kW), enerji (kWh), "
                "hucre sicakligi, POA isinim. Analiz ve raporlama icin."
            ),
            hedef="Analiz, muhasebe, arsiv",
            boyut_kb=excel_kb,
            buton_key="rapor_excel_indir",
            aktif=False,
            aksiyon_notu="Excel disa aktarim Adim 6c'de gelecek",
        )
    
    with col_json:
        json_tiklandi = _format_karti(
            ikon="🔧",
            baslik="JSON API Formati",
            aciklama=(
                "Yapisal veri: metadata, saatlik seriler, ozet metrikleri. "
                "Baska bir sisteme (SCADA, ERP, BI) beslemek icin."
            ),
            hedef="Sistem entegrasyonu, otomasyon",
            boyut_kb=json_kb,
            buton_key="rapor_json_indir",
            aktif=False,
            aksiyon_notu="JSON disa aktarim Adim 6c'de gelecek",
        )
    
    # 6b bilgi notu (6c-6d bittiginde bu blok kaldirilir)
    st.markdown(
        f'<div style="margin-top:16px;padding:12px 16px;'
        f'background:#F7F8F9;border-radius:6px;border-left:3px solid {PRIMARY}">'
        f'<div style="font-size:12px;color:{TEXT_SECONDARY};line-height:1.5">'
        f'<b style="color:{TEXT_PRIMARY}">Adim 6b tamam.</b> Format kartlari '
        f'gorsel olarak hazir. Gercek dosya uretimi Adim 6c (Excel + JSON) '
        f've Adim 6d (PDF) ile devreye girecek.'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# ANA render
# ============================================================

def render_raporlar() -> None:
    page_header(   
        "Raporlar",
        "PDF yonetici ozeti, Excel tam veri, JSON API formati",
    )

    # Guard 1: kalibrasyon var mi?
    if "calibration_result" not in st.session_state:
        _uyari_kalibrasyon_yok()
        return

    # Guard 2: forecast var mi?
    if "forecast_result" not in st.session_state:
        _uyari_forecast_yok()
        return

    # 6a: KPI seridi
    _kpi_seridi()

    # 6b: Format kartlari
    _format_kartlari()