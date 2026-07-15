"""
PVQuant Raporlar Ekrani (Faz 2 Adim 6)

Kalibre tahmin sonuclarini 3 farkli formatta (PDF/Excel/JSON) disa aktarir.

Adim 6a: Iskelet + KPI seridi + guard'lar          [OK]
Adim 6b: 3 format karti (gorsel)                    [OK - 14 Temmuz]
Adim 6c: PDF + Excel + JSON gercek isleyisi         [OK - 14 Temmuz aksam]
Adim 6d: PDF yonetici ozeti fine-tuning
Adim 6e: Rapor gecmisi (dekoratif)
"""

import sys
from datetime import datetime
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
    result = st.session_state.forecast_result
    n_saat = len(result.hourly)

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
# 6c: Rapor uretim motoru
# ============================================================

def _rapor_dosya_adi(uzanti: str) -> str:
    """Rapor dosya adi: PVQuant_<santral>_<yyyymmdd>_hhmm.<uzanti>"""
    santral = st.session_state.get("plant_context", {}).get("plant_name", "santral")
    santral = "".join(c if c.isalnum() or c in "-_" else "_" for c in santral)
    zaman = datetime.now().strftime("%Y%m%d_%H%M")
    return f"PVQuant_{santral}_{zaman}.{uzanti}"


def _raporlari_uret():
    """3 formati bir kerede uretir, session_state'e cacheler."""
    forecast = st.session_state.forecast_result
    calibration = st.session_state.calibration_result

    cache_key = (id(forecast), id(calibration))
    if st.session_state.get("_rapor_cache_key") == cache_key:
        return st.session_state._rapor_cache

    with st.spinner("Raporlar hazirlaniyor..."):
        from pvquant.reporting import from_results, build_pdf, build_excel, build_json

        plant_ctx = st.session_state.get("plant_context", {})
        from pvquant.reporting.contracts import normalize_plant_name
        _ham = (
            st.session_state.get("plant_display_name")
            or plant_ctx.get("plant_name")
            or "Santral"
        )
        plant_name = normalize_plant_name(_ham)
        plant_tz = plant_ctx.get("timezone", "Europe/Istanbul")

        ctx = from_results(
            forecast, calibration,
            plant_name=plant_name,
            plant_tz=plant_tz,
            mode="B",
        )
        from pvquant.reporting import apply_hybrid_session
        ctx = apply_hybrid_session(ctx, st.session_state)

        sonuc = {"pdf": None, "xlsx": None, "json": None, "hatalar": {}}

        try:
            sonuc["pdf"] = build_pdf(ctx)
        except Exception as e:
            sonuc["hatalar"]["pdf"] = str(e)

        try:
            sonuc["xlsx"] = build_excel(ctx)
        except Exception as e:
            sonuc["hatalar"]["xlsx"] = str(e)

        try:
            sonuc["json"] = build_json(ctx)
        except Exception as e:
            sonuc["hatalar"]["json"] = str(e)

    st.session_state._rapor_cache_key = cache_key
    st.session_state._rapor_cache = sonuc
    return sonuc


# ============================================================
# 6c: 3 format karti + indir butonlari
# ============================================================

def _format_karti(
    ikon, baslik, aciklama, hedef, boyut_bilgisi,
    indir_bytes, indir_dosya_adi, indir_mime, buton_key,
    hata_mesaji=None,
) -> None:
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
                          font-weight:500" class="pvq-mono">{boyut_bilgisi}</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if hata_mesaji is not None:
        st.error(f"Uretim hatasi: {hata_mesaji[:150]}")
        st.button(
            f"↓  {baslik} indir",
            key=buton_key,
            use_container_width=True,
            disabled=True,
        )
        return

    if indir_bytes is None:
        st.button(
            f"↓  {baslik} indir",
            key=buton_key,
            use_container_width=True,
            disabled=True,
        )
        return

    if isinstance(indir_bytes, str):
        indir_bytes = indir_bytes.encode("utf-8")

    st.download_button(
        f"↓  {baslik} indir",
        data=indir_bytes,
        file_name=indir_dosya_adi,
        mime=indir_mime,
        key=buton_key,
        use_container_width=True,
        type="primary",
    )


def _format_kartlari() -> None:
    """Uc format kartini yan yana gosterir - butonlar aktif."""
    sonuc = _raporlari_uret()

    def _boyut_str(icerik):
        if icerik is None:
            return "—"
        if isinstance(icerik, str):
            icerik = icerik.encode("utf-8")
        kb = len(icerik) / 1024
        return f"~{kb:.0f} KB"

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
        _format_karti(
            ikon="📄",
            baslik="PDF Yonetici Ozeti",
            aciklama=(
                "Tek sayfada 7 gunluk tahmin ozeti: toplam uretim, "
                "gunluk grafik, kritik notlar. E-posta ekine, sunuma uygun."
            ),
            hedef="Yonetim, e-posta paylasimi",
            boyut_bilgisi=_boyut_str(sonuc["pdf"]),
            indir_bytes=sonuc["pdf"],
            indir_dosya_adi=_rapor_dosya_adi("pdf"),
            indir_mime="application/pdf",
            buton_key="rapor_pdf_indir",
            hata_mesaji=sonuc["hatalar"].get("pdf"),
        )

    with col_excel:
        n_saat = len(st.session_state.forecast_result.hourly)
        _format_karti(
            ikon="📊",
            baslik="Excel Tam Veri",
            aciklama=(
                f"{n_saat} satirlik saatlik detay: guc (kW), enerji (kWh), "
                "hucre sicakligi, POA isinim. Analiz ve raporlama icin."
            ),
            hedef="Analiz, muhasebe, arsiv",
            boyut_bilgisi=_boyut_str(sonuc["xlsx"]),
            indir_bytes=sonuc["xlsx"],
            indir_dosya_adi=_rapor_dosya_adi("xlsx"),
            indir_mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            buton_key="rapor_excel_indir",
            hata_mesaji=sonuc["hatalar"].get("xlsx"),
        )

    with col_json:
        _format_karti(
            ikon="🔧",
            baslik="JSON API Formati",
            aciklama=(
                "Yapisal veri: metadata, saatlik seriler, ozet metrikleri. "
                "Baska bir sisteme (SCADA, ERP, BI) beslemek icin."
            ),
            hedef="Sistem entegrasyonu, otomasyon",
            boyut_bilgisi=_boyut_str(sonuc["json"]),
            indir_bytes=sonuc["json"],
            indir_dosya_adi=_rapor_dosya_adi("json"),
            indir_mime="application/json",
            buton_key="rapor_json_indir",
            hata_mesaji=sonuc["hatalar"].get("json"),
        )

    basarili = sum(1 for k in ("pdf", "xlsx", "json") if sonuc[k] is not None)
    if basarili == 3:
        st.markdown(
            f'<div style="margin-top:16px;padding:12px 16px;'
            f'background:#F0FDF4;border-radius:6px;border-left:3px solid {SUCCESS}">'
            f'<div style="font-size:12px;color:{TEXT_SECONDARY};line-height:1.5">'
            f'<b style="color:{TEXT_PRIMARY}">3 format hazir.</b> '
            f'Butona basarak indirebilirsiniz. Raporlar mevcut kalibrasyon + '
            f'tahmine gore uretildi.'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div style="margin-top:16px;padding:12px 16px;'
            f'background:#FEF2F2;border-radius:6px;border-left:3px solid {WARNING}">'
            f'<div style="font-size:12px;color:{TEXT_SECONDARY};line-height:1.5">'
            f'<b style="color:{TEXT_PRIMARY}">{basarili}/3 format hazirlandi.</b> '
            f'Basarisiz formatlarda hata mesaji gosteriliyor.'
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

    if "calibration_result" not in st.session_state:
        _uyari_kalibrasyon_yok()
        return

    if "forecast_result" not in st.session_state:
        _uyari_forecast_yok()
        return

    _kpi_seridi()
    _format_kartlari()