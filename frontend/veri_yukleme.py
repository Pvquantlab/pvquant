"""
PVQuant Veri Yukleme Ekrani (Faz 2 Adim 3 + 4a + Ingestion)

Iki mod:
- Mod A (varsayilan): 'SCADA veriniz var mi?' - Hizli vs Kalibre yol ayrimi
- Mod B (scada_upload): CSV yukleme + ingestion (preview -> onayla -> karne)

Ingestion akisi (2 bolum, tek sayfa):
  1. Yukle + Onizleme: preview_file -> format karti + kolon eslemesi
                       + santral bilgisi formu + ornek satirlar
  2. Onayla + Karne: ingest_file -> kalite karnesi + to_clean_frame() saklanir
                     -> "Kalibrasyona gec" butonu aktif
"""

import os
import sys
import tempfile
from pathlib import Path

import streamlit as st

from components import page_header
from design_tokens import PRIMARY, SUCCESS, TEXT_SECONDARY, TEXT_TERTIARY, WARNING

# Backend import - yeni ingestion katmani
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from pvquant.io.ingestion import (
    ColumnMapping,
    FileFormat,
    TemplateStore,
    ingest_file,
    preview_file,
)

# Sablon deposu - kullanicinin ikinci yuklemesinde otomatik esleme
_TEMPLATE_STORE = TemplateStore(
    Path(__file__).parent.parent / "ingestion_templates"
)


# ============================================================
# ORTAK: Sihirbaz adim gostergesi
# ============================================================

def _adim_gostergesi(aktif_adim: int = 2) -> None:
    """Sihirbaz - 1: Santral, 2: Veri yolu, 3: Sonuc."""
    def _dot(num, label, state):
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
# MOD A: Yol ayrimi kartlari (degismedi)
# ============================================================

def _yol_karti(baslik, ikon, sapma_txt, maddeler, buton_metni, onerilen, on_click_action):
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
    st.button(
        buton_metni,
        key=f"yol_{on_click_action}",
        use_container_width=True,
        type="primary" if onerilen else "secondary",
        on_click=lambda: st.session_state.update({"veri_yukleme_mod": on_click_action}),
    )


def _render_mod_a() -> None:
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
# MOD B: SCADA yukleme (Ingestion akisi)
# ============================================================

# --- Santral bilgisi formu (ingestion parametreleri icin) ---

def _santral_bilgi_formu() -> dict | None:
    """4 alanli santral bilgisi formu.
    
    Returns:
        dict: {capacity_kwp, latitude, longitude, timezone} veya None
    """
    # Onceki oturumdan varsa varsayilan olarak koy
    saved = st.session_state.get("plant_context", {})
    
    st.markdown(
        f"""
        <div style="margin-top:8px;margin-bottom:12px">
          <div style="font-size:15px;font-weight:600;color:#0F1B28;
                      margin-bottom:4px">Santral bilgisi</div>
          <div style="font-size:12px;color:{TEXT_SECONDARY}">
            Bu bilgiler dosyanin dogru okunmasi icin gerekli 
            (birim tespiti, saat dilimi, gece uretimi kontrolu).
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    col1, col2 = st.columns(2)
    with col1:
        capacity = st.number_input(
            "Kurulu guc (kWp)",
            min_value=1.0, max_value=1_000_000.0,
            value=float(saved.get("capacity_kwp", 4514.0)),
            step=100.0, key="ing_capacity",
        )
        latitude = st.number_input(
            "Enlem",
            min_value=-90.0, max_value=90.0,
            value=float(saved.get("latitude", 37.87)),
            step=0.01, format="%.4f", key="ing_lat",
        )
    with col2:
        timezone_options = [
            "Europe/Istanbul", "UTC", "Europe/London", "Europe/Berlin",
            "America/New_York", "America/Los_Angeles",
            "Asia/Tokyo", "Australia/Sydney", "Australia/Darwin",
        ]
        default_tz = saved.get("timezone", "Europe/Istanbul")
        tz_index = timezone_options.index(default_tz) if default_tz in timezone_options else 0
        timezone = st.selectbox(
            "Saat dilimi (dosyadaki zamanlar)",
            options=timezone_options,
            index=tz_index,
            key="ing_tz",
            help="Dosyanizdaki zaman damgalari hangi dilimde? "
                 "Emin degilseniz 'UTC' secin.",
        )
        longitude = st.number_input(
            "Boylam",
            min_value=-180.0, max_value=180.0,
            value=float(saved.get("longitude", 32.49)),
            step=0.01, format="%.4f", key="ing_lon",
        )
    
    return {
        "capacity_kwp": capacity,
        "latitude": latitude,
        "longitude": longitude,
        "timezone": timezone,
    }


# --- Onizleme kartlari ---

def _format_karti(pv) -> None:
    """Preview file_format bilgisini gosteren kart."""
    ff = pv.file_format
    conf_renk = SUCCESS if ff.confidence >= 0.7 else WARNING
    
    matched_rozet = ""
    if pv.matched_template:
        matched_rozet = f"""
        <div style="margin-bottom:12px">
          <span style="background:rgba(30,158,106,0.12);color:{SUCCESS};
                       padding:4px 10px;border-radius:999px;font-size:11px;
                       font-weight:600;letter-spacing:0.05em">
            ✓ '{pv.matched_template}' SABLONU ILE ESLESTI
          </span>
        </div>
        """
    
    rows_html = ""
    for label, value in [
        ("Kodlama", ff.encoding),
        ("Ayrac", repr(ff.delimiter)),
        ("Ondalik", repr(ff.decimal)),
        ("Baslik satiri", str(ff.header_row + 1)),
    ]:
        rows_html += (
            f'<div style="display:flex;justify-content:space-between;'
            f'padding:6px 0;font-size:13px">'
            f'<span style="color:{TEXT_SECONDARY}">{label}</span>'
            f'<span style="font-family:IBM Plex Mono,monospace;'
            f'color:#0F1B28;font-weight:500">{value}</span>'
            f'</div>'
        )
    
    st.markdown(
        f"""
        <div class="pvq-card" style="height:100%">
          {matched_rozet}
          <div style="display:flex;justify-content:space-between;
                      align-items:center;margin-bottom:12px">
            <div style="font-size:15px;font-weight:600">Dosya formati</div>
            <span style="font-family:IBM Plex Mono,monospace;font-size:11px;
                         color:{conf_renk};font-weight:600">
              guven %{ff.confidence * 100:.0f}
            </span>
          </div>
          {rows_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _kolon_eslemesi_karti(pv) -> None:
    """Preview kolon eslemesini gosteren kart."""
    m = pv.mapping
    alan_isimleri = {
        "timestamp": "Zaman",
        "power": "Guc",
        "energy": "Enerji",
        "poa_irradiance": "Isinim (POA)",
        "temp_ambient": "Ortam sicakligi",
        "temp_module": "Modul sicakligi",
        "wind_speed": "Ruzgar hizi",
        "ghi": "Yatay isinim (GHI)",
    }
    
    rows_html = ""
    for alan, tr_isim in alan_isimleri.items():
        col_adi = getattr(m, alan, None)
        if col_adi is None:
            continue
        conf = m.confidence.get(alan, 1.0)
        conf_renk = SUCCESS if conf >= 0.6 else WARNING
        rows_html += (
            f'<div style="display:flex;justify-content:space-between;'
            f'align-items:center;padding:6px 0;font-size:13px">'
            f'<span style="color:{TEXT_SECONDARY}">{tr_isim}</span>'
            f'<span style="display:flex;align-items:center;gap:8px">'
            f'<span style="font-family:IBM Plex Mono,monospace;'
            f'color:#0F1B28;font-weight:500;font-size:12px">{col_adi}</span>'
            f'<span style="font-family:IBM Plex Mono,monospace;font-size:10px;'
            f'color:{conf_renk};font-weight:600">%{conf * 100:.0f}</span>'
            f'</span>'
            f'</div>'
        )
    
    unmapped_html = ""
    if pv.unmapped_columns:
        unmapped_txt = ", ".join(pv.unmapped_columns[:3])
        if len(pv.unmapped_columns) > 3:
            unmapped_txt += f" +{len(pv.unmapped_columns) - 3} daha"
        unmapped_html = f"""
        <div style="margin-top:12px;padding-top:12px;
                    border-top:1px solid #E2E6EA;
                    font-size:11px;color:{TEXT_TERTIARY}">
          Yoksayilan: {unmapped_txt}
        </div>
        """
    
    st.markdown(
        f"""
        <div class="pvq-card" style="height:100%">
          <div style="font-size:15px;font-weight:600;margin-bottom:12px">
            Kolon eslemesi
          </div>
          {rows_html}
          {unmapped_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _notlar_karti(pv) -> None:
    """Preview notes'lari uyari olarak gosterir."""
    if not pv.notes:
        return
    
    notlar_html = "".join(f"<li style='margin-bottom:6px'>{n}</li>" for n in pv.notes)
    st.markdown(
        f"""
        <div class="pvq-card" style="margin-top:16px;
             border-left:3px solid {WARNING};background:rgba(201,80,46,0.04)">
          <div style="font-size:13px;font-weight:600;margin-bottom:8px">
            Kontrol edilmesi gerekenler
          </div>
          <ul style="margin:0;padding-left:20px;font-size:13px;
                     color:{TEXT_SECONDARY};line-height:1.6">
            {notlar_html}
          </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


# --- Kalite karnesi ---

def _kalite_karnesi_karti(result) -> None:
    """ingest_file sonucundaki QualityReport'u gosterir."""
    r = result.report
    valid_renk = SUCCESS if r.valid_fraction >= 0.9 else WARNING
    
    # KPI seridi
    st.markdown(
        f"""
        <div class="pvq-card" style="margin-top:16px">
          <div style="font-size:15px;font-weight:600;margin-bottom:16px">
            Veri kaliteniz
          </div>
          <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:24px">
            <div>
              <div class="pvq-microlabel">OKUNAN SATIR</div>
              <div style="font-family:IBM Plex Mono,monospace;
                          font-size:22px;font-weight:700">
                {r.n_rows_read:,}</div>
            </div>
            <div>
              <div class="pvq-microlabel">GECERLI SATIR</div>
              <div style="font-family:IBM Plex Mono,monospace;
                          font-size:22px;font-weight:700;color:{valid_renk}">
                {r.n_rows_valid:,}</div>
              <div style="font-size:11px;color:{TEXT_SECONDARY};margin-top:2px">
                %{r.valid_fraction * 100:.1f}</div>
            </div>
            <div>
              <div class="pvq-microlabel">BOSLUK</div>
              <div style="font-family:IBM Plex Mono,monospace;
                          font-size:22px;font-weight:700">
                {r.gap_hours}</div>
              <div style="font-size:11px;color:{TEXT_SECONDARY};margin-top:2px">
                saat</div>
            </div>
            <div>
              <div class="pvq-microlabel">TARIH ARALIGI</div>
              <div style="font-family:IBM Plex Mono,monospace;
                          font-size:12px;font-weight:600;line-height:1.4">
                {r.coverage_start[:10] if r.coverage_start else '-'}<br>
                {r.coverage_end[:10] if r.coverage_end else '-'}</div>
            </div>
          </div>
        </div>
        """.replace(",", "."),
        unsafe_allow_html=True,
    )
    
    # Bayrak dagilimi
    flag_labels = {
        "negative_power": "Negatif guc",
        "night_production": "Gece uretimi",
        "over_capacity": "Kapasite ustu",
        "frozen_value": "Donmus deger",
        "duplicate_time": "Tekrar eden zaman",
        "dst_ambiguous": "Yaz saati belirsizligi",
        "unparseable": "Okunamayan",
    }
    
    rows_html = ""
    for flag, count in sorted(r.flag_counts.items(), key=lambda kv: -kv[1]):
        if flag == "valid" or count == 0:
            continue
        label = flag_labels.get(flag, flag)
        renk = WARNING if flag == "night_production" else TEXT_SECONDARY
        rows_html += (
            f'<div style="display:flex;justify-content:space-between;'
            f'padding:8px 0;border-bottom:1px solid #F0F2F4;font-size:13px">'
            f'<span style="color:{renk}">{label}</span>'
            f'<span style="font-family:IBM Plex Mono,monospace;'
            f'font-weight:600">{count:,}</span>'
            f'</div>'
        )
    
    if rows_html:
        st.markdown(
            f"""
            <div class="pvq-card" style="margin-top:12px">
              <div style="font-size:13px;font-weight:600;margin-bottom:8px">
                Bayrakli satirlar (kalibrasyona girmez)
              </div>
              {rows_html}
            </div>
            """.replace(",", "."),
            unsafe_allow_html=True,
        )
    
    # Uyarilar (ozellikle gece uretimi = tz hatasi)
    for uyari in r.warnings:
        tz_hatasi = "saat dilimi" in uyari.lower()
        renk = "#C9502E" if tz_hatasi else WARNING
        bg = "rgba(201,80,46,0.08)" if tz_hatasi else "rgba(201,80,46,0.04)"
        st.markdown(
            f"""
            <div class="pvq-card" style="margin-top:12px;
                 border-left:3px solid {renk};background:{bg}">
              <div style="font-size:13px;color:#0F1B28;line-height:1.6">
                {uyari}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# --- Mod B ana render ---

def _render_mod_b_scada() -> None:
    """Mod B: CSV yukleme + ingestion pipeline."""
    _adim_gostergesi(aktif_adim=2)

    if st.button("← Yol ayrimina don", key="scada_geri", type="secondary"):
        st.session_state.veri_yukleme_mod = "yol_ayrimi"
        for k in ("scada_preview", "scada_result", "scada_clean",
                  "scada_filename", "scada_tmp_path"):
            st.session_state.pop(k, None)
        st.rerun()

    st.markdown(
        f"""
        <div style="margin:24px 0 8px 0">
          <div style="font-size:22px;font-weight:700;color:#0F1B28;
                      letter-spacing:-0.02em;margin-bottom:8px">
            SCADA verinizi yukleyin
          </div>
          <div style="font-size:14px;color:{TEXT_SECONDARY}">
            Herhangi bir format kabul edilir — Turkce/Ingilizce sutunlar, 
            cp1254/utf-8, virgul/noktali virgul, kW/MW hepsi otomatik tespit.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    uploaded = st.file_uploader(
        "CSV / Excel dosyasi",
        type=["csv", "xlsx", "xls"],
        key="scada_uploader",
        label_visibility="collapsed",
    )

    if uploaded is None:
        st.markdown(
            f"""
            <div style="margin-top:16px;padding:16px;background:#F7F8F9;
                        border:1px solid #E2E6EA;border-radius:8px;
                        font-size:13px;color:{TEXT_SECONDARY}">
              <strong>Ne kabul edilir:</strong> Zaman kolonu + Guc (kW/MW) 
              veya Enerji (kWh) kolonu zorunlu. Isinim, sicaklik, ruzgar 
              gibi ek sutunlar varsa kalibrasyon daha isabetli olur.
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    # --- BOLUM 1: Yukle + Onizleme ---
    
    # Gecici dosya (yalniz preview icin - ingest sonrasi silinir)
    if "scada_tmp_path" not in st.session_state or \
       st.session_state.get("scada_filename") != uploaded.name:
        # Yeni dosya - eskiyi temizle
        old_tmp = st.session_state.get("scada_tmp_path")
        if old_tmp and os.path.exists(old_tmp):
            try:
                os.unlink(old_tmp)
            except OSError:
                pass
        # Sonuclari sifirla
        for k in ("scada_preview", "scada_result", "scada_clean"):
            st.session_state.pop(k, None)
        
        # Yeni gecici dosya
        suffix = "." + uploaded.name.rsplit(".", 1)[-1]
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(uploaded.getvalue())
            st.session_state.scada_tmp_path = tmp.name
        st.session_state.scada_filename = uploaded.name

    tmp_path = st.session_state.scada_tmp_path
    
    # Preview cagirma (cache session'da)
    if "scada_preview" not in st.session_state:
        try:
            with st.spinner("Dosya analiz ediliyor..."):
                pv = preview_file(tmp_path, template_store=_TEMPLATE_STORE)
            st.session_state.scada_preview = pv
        except ValueError as e:
            st.error(f"Dosya cozumlenemedi: {e}")
            st.info(
                "Ipucu: Dosyanizda en azindan bir 'zaman' ve bir 'guc/enerji' "
                "kolonu olmali. Baslik satiri dosyanin ilk 10 satirinda olmali."
            )
            return
        except Exception as e:
            st.error(f"Dosya okunurken hata: {e}")
            return
    
    pv = st.session_state.scada_preview
    
    # Onizleme: 2 sutun (format + kolon) yan yana, sonra santral formu
    st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        _format_karti(pv)
    with c2:
        _kolon_eslemesi_karti(pv)
    
    _notlar_karti(pv)
    
    # Ornek satirlar
    with st.expander("Dosyadan ornek satirlar (ilk 10)"):
        st.dataframe(pv.sample_rows, use_container_width=True, height=280)
    
    # Santral bilgisi formu
    st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)
    plant_ctx = _santral_bilgi_formu()
    
    # --- BOLUM 2: Onayla + Karne ---
    
    st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)
    
    if "scada_result" not in st.session_state:
        if st.button(
            "Onayla ve dogrula",
            key="ingest_onayla",
            use_container_width=True,
            type="primary",
        ):
            try:
                with st.spinner("Veri donusturuluyor ve dogrulaniyor..."):
                    result = ingest_file(
                        tmp_path,
                        capacity_kwp=plant_ctx["capacity_kwp"],
                        latitude=plant_ctx["latitude"],
                        longitude=plant_ctx["longitude"],
                        source_timezone=plant_ctx["timezone"],
                        file_format=pv.file_format,
                        mapping=pv.mapping,
                    )
                st.session_state.scada_result = result
                st.session_state.scada_clean = result.to_clean_frame()
                st.session_state.plant_context = plant_ctx
                # Sablonu kaydet (ikinci yuklemede otomatik esleme)
                try:
                    _TEMPLATE_STORE.save(
                        f"user_{uploaded.name.rsplit('.', 1)[0]}",
                        result.to_template(),
                    )
                except Exception:
                    pass  # sablon kaydi kritik degil
                st.rerun()
            except Exception as e:
                st.error(f"Islem sirasinda hata: {e}")
                return
        return
    
    # Sonuc var - kalite karnesi goster
    result = st.session_state.scada_result
    _kalite_karnesi_karti(result)
    
    # Alt butonlar
    st.markdown("<div style='margin-top:20px'></div>", unsafe_allow_html=True)
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Farkli dosya sec", key="farkli_dosya", use_container_width=True):
            # Gecici dosyayi temizle
            if os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
            for k in ("scada_preview", "scada_result", "scada_clean",
                      "scada_filename", "scada_tmp_path"):
                st.session_state.pop(k, None)
            st.rerun()
    with col2:
        # Kalibrasyona gec - clean frame session'da hazir
        if st.button(
            "Kalibrasyona gec →",
            key="kalibrasyona_gec",
            use_container_width=True,
            type="primary",
        ):
            st.session_state.active_page = "kalibrasyon"
            st.rerun()


# ============================================================
# ANA render
# ============================================================

def render_veri_yukleme() -> None:
    if "veri_yukleme_mod" not in st.session_state:
        st.session_state.veri_yukleme_mod = "yol_ayrimi"

    mod = st.session_state.veri_yukleme_mod

    if mod == "scada_upload":
        page_header(
            "Veri Yukleme",
            "SCADA verinizi yukleyin — format otomatik tespit + kalite kontrolu",
        )
        _render_mod_b_scada()
    elif mod == "hizli":
        st.session_state.veri_yukleme_mod = "yol_ayrimi"
        st.info("Hizli tahmin akisi Adim 5'te gelecek. Simdilik yol ayrimina donduruldunuz.")
        _render_mod_a_wrapper()
    else:
        _render_mod_a_wrapper()


def _render_mod_a_wrapper():
    page_header(
        "Veri Yukleme",
        "Tahmin yolunuzu secin — SCADA veriniz varsa kalibre tahmine gecin",
    )
    _render_mod_a()