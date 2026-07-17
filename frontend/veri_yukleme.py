"""
PVQuant Veri Yukleme Ekrani (Faz 2 Adim 3 + 4a + Ingestion)

Iki mod:
- Mod A (varsayilan): 'SCADA veriniz var mı?' - Hizli vs Kalibre yol ayrimi
- Mod B (scada_upload): CSV yukleme + ingestion (preview -> onayla -> karne)

Ingestion akisi (2 bolum, tek sayfa):
  1. Yukle + Onizleme: preview_file -> format karti + kolon eslemesi
                       + santral bilgisi formu + ornek satirlar
  2. Onayla + Karne: ingest_file -> kalite karnesi + to_clean_frame() saklanir
                     -> "Kalibrasyona gec" butonu aktif

MappingFailedError: otomatik esleme basarisiz olursa manuel esleme
mini-ekrani devreye girer (dropdown'lar + ornek satirlar).

Kopru (Cephe 1): "Kalibrasyona gec" butonu, ingestion cikti
(scada_clean DataFrame) -> SCADAData donusumunu yapar ve
session_state.scada_data'ya koyar (kalibrasyon sayfasi eski API
bekliyor).
"""

import os
import sys
import tempfile
import pandas as pd
from pathlib import Path

import streamlit as st
import ui_kit
from pvquant.services import plant_service
from pvquant.services import ingest_service

from components import page_header
from design_tokens import PRIMARY, SUCCESS, TEXT_SECONDARY, TEXT_TERTIARY, WARNING

# Backend import - yeni ingestion katmani
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from pvquant.io.ingestion import (
    ColumnMapping,
    FileFormat,
    MappingFailedError,
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
    ui_kit.adimlar(aktif=2)

    st.markdown(
        f"""
        <div style="text-align:center;margin-bottom:40px">
          <div style="font-size:32px;font-weight:700;color:#0F1B28;
                      letter-spacing:-0.02em;margin-bottom:12px">
            SCADA veriniz var mı?
          </div>
          <div style="font-size:15px;color:{TEXT_SECONDARY}">
            Fark, modelin santralinizi ne kadar tanıdığında.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(2, gap="large")

    with cols[0]:
        _yol_karti(
            baslik="Hızlı tahmin",
            ikon="⚡",
            sapma_txt="Veri yüklemeden — hemen şimdi.|%5-10",
            maddeler=[
                "Veri yüklemeden, saniyeler içinde sonuç",
                "Profesyonel meteoroloji verisiyle 7 günlük tahmin",
                "Dilediğiniz an kalibre tahmine yükseltin",
            ],
            buton_metni="Hızlı tahminle devam et",
            onerilen=False,
            on_click_action="hizli",
        )

    with cols[1]:
        _yol_karti(
            baslik="Kalibre tahmin",
            ikon="🛡",
            sapma_txt="SCADA verinizle — model kendini santralinize kalibre eder.|%1-3",
            maddeler=[
                "Model kendini geçmiş üretiminize göre ayarlar",
                "Panel yönü ve eğimi bilinmiyorsa model bulur",
                "En az 3 ay SCADA verisi gerekir — önerilen 12 ay",
            ],
            buton_metni="Kalibre tahmine geç",
            onerilen=True,
            on_click_action="scada_upload",
        )

    st.markdown(
        f"""
        <div style="text-align:center;margin-top:32px;font-size:13px;
                    color:{TEXT_SECONDARY};max-width:720px;
                    margin-left:auto;margin-right:auto">
          Veriniz azsa endişelenmeyin: 3 aydan kısa veri bulursak sizi engellemeyiz,
          hızlı tahminle başlatıp sonra yükseltmenizi öneririz.
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
        _ad = st.text_input(
            "Santral adı (opsiyonel)",
            value=saved.get("plant_name", saved.get("name", "")),
            key="ing_plant_name",
            help="Raporlarda görünecek ad. Boşsa dosya adı kullanılır.",
        )
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
                 "Emin değilseniz 'UTC' seçin.",
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



def _adim1_santral() -> dict | None:
    """Anayasa 6.2 Adim 1 - IKI MODLU (Fable 5 v1.4):
    - Sidebar'da santral SECILIYSE: salt-okunur ozet karti + Devam tusu
    - SECILI DEGILSE: mevcut form + Devam -> plant_service.olustur
    Donen dict = plant_ctx (capacity_kwp, latitude, longitude, timezone).
    None dondururse akis durur (form eksik ya da Devam basilmadi)."""
    auth = st.session_state.get("auth")
    aktif_pid = st.session_state.get("aktif_plant_id")

    # --- MOD 1: sidebar'da santral secili ---
    if aktif_pid and auth:
        try:
            p = plant_service.getir(auth["tenant_id"], aktif_pid)
        except Exception:
            p = None
        if p:
            # Salt-okunur ozet karti
            st.markdown(
                f'<div class="pv-kart" style="margin:12px 0">'
                f'  <div class="pv-eyebrow">BU SANTRAL ICIN YUKLUYORSUNUZ</div>'
                f'  <div style="font-family:var(--f-mono);font-size:15px;'
                f'              margin-top:6px">'
                f'    {p["name"]} · {p["capacity_kwp"]:.0f} kWp · '
                f'    {p["lat"]:.2f}, {p["lon"]:.2f} · {p["tz"]}'
                f'  </div>'
                f'  <div class="pv-mikro" style="margin-top:6px">'
                f'    Farklı santral mı? Kenar çubuğundan seçin.'
                f'  </div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            # plant_ctx turetilmis gorunum (Fable 5 v1.4)
            plant_ctx = {
                "capacity_kwp": p["capacity_kwp"],
                "latitude": p["lat"],
                "longitude": p["lon"],
                "timezone": p["tz"],
                "name": p["name"],
            }
            return plant_ctx

    # --- MOD 2: yeni kullanici (santral yok) ---
    plant_ctx_form = _santral_bilgi_formu()
    if plant_ctx_form is None:
        return None
    # Kullanici formu doldurdu; Devam anında santral olustur
    if st.button("Devam", type="primary", use_container_width=True,
                 key="adim1_devam"):
        try:
            pid = plant_service.olustur(
                auth["tenant_id"],
                name=plant_ctx_form.get("name", "Yeni santral"),
                lat=plant_ctx_form["latitude"],
                lon=plant_ctx_form["longitude"],
                tz=plant_ctx_form["timezone"],
                capacity_kwp=plant_ctx_form["capacity_kwp"],
            )
            st.session_state.aktif_plant_id = pid
            st.session_state.plant_context = plant_ctx_form
            st.rerun()
        except Exception as e:
            st.error(f"Santral olusturulamadi: {e}")
            return None
    return None

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


# --- Manuel esleme mini ekrani (MappingFailedError yakalayinca) ---

def _manuel_esleme_ekrani(err: MappingFailedError, tmp_path: str) -> None:
    """Otomatik esleme basarisiz olunca kullaniciya dropdown'larla soruyoruz.

    En az timestamp + (power VEYA energy) secmesi gerek. Onaylayinca
    session_state.scada_preview'a IngestionPreview yerlestirilir ve
    normal akis devam eder.
    """
    st.markdown(
        f"""
        <div class="pvq-card" style="margin-top:16px;
             border-left:3px solid {WARNING};background:rgba(201,80,46,0.06)">
          <div style="font-size:15px;font-weight:600;color:#0F1B28;
                      margin-bottom:8px">
            Otomatik esleme basarisiz — manuel secim gerekli
          </div>
          <div style="font-size:13px;color:{TEXT_SECONDARY};line-height:1.6">
            Sistem dosyanizin kolonlarini otomatik taniyamadi. Asagidan 
            hangi kolonun zamani ve hangisinin guc/enerjiyi tasidigini 
            secin. Diger alanlar opsiyoneldir.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Ornek satirlar (varsa) goster
    if len(err.sample_rows) > 0:
        with st.expander("Dosyadan ornek satirlar (ilk 10)", expanded=True):
            st.dataframe(err.sample_rows, use_container_width=True, height=280)

    # Dropdown'lar
    kolonlar = ["(seçiniz)"] + list(err.columns)

    col1, col2 = st.columns(2)
    with col1:
        timestamp_col = st.selectbox(
            "Zaman kolonu *", options=kolonlar, key="manuel_ts",
            help="Tarih/saat bilgisini tasiyan kolon",
        )
        power_col = st.selectbox(
            "Guc kolonu (kW/MW)", options=kolonlar, key="manuel_pow",
            help="Anlik guc degerleri. Bu YOKSA enerji kolonu secmelisiniz.",
        )
        poa_col = st.selectbox(
            "Işınım (POA) — opsiyonel", options=kolonlar, key="manuel_poa",
        )
        temp_ambient_col = st.selectbox(
            "Ortam sıcaklığı — opsiyonel", options=kolonlar, key="manuel_temp",
        )
    with col2:
        energy_col = st.selectbox(
            "Enerji kolonu (kWh) — guc yoksa zorunlu",
            options=kolonlar, key="manuel_ene",
            help="Aralik enerjisi veya kumulatif sayac.",
        )
        temp_module_col = st.selectbox(
            "Modül sıcaklığı — opsiyonel", options=kolonlar, key="manuel_tmod",
        )
        wind_col = st.selectbox(
            "Rüzgar hızı — opsiyonel", options=kolonlar, key="manuel_wind",
        )
        ghi_col = st.selectbox(
            "GHI (yatay ışınım) — opsiyonel", options=kolonlar, key="manuel_ghi",
        )

    st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)

    # Dogrulama ve devam
    if st.button("Bu esleme ile devam et", key="manuel_devam",
                 type="primary", use_container_width=True):
        if timestamp_col == "(seçiniz)":
            st.error("Zaman kolonu zorunludur.")
            return
        if power_col == "(seçiniz)" and energy_col == "(seçiniz)":
            st.error("En az bir guc veya enerji kolonu secmelisiniz.")
            return

        def _or_none(col):
            return None if col == "(seçiniz)" else col

        manual_mapping = ColumnMapping(
            timestamp=timestamp_col,
            power=_or_none(power_col),
            energy=_or_none(energy_col),
            poa_irradiance=_or_none(poa_col),
            temp_ambient=_or_none(temp_ambient_col),
            temp_module=_or_none(temp_module_col),
            wind_speed=_or_none(wind_col),
            ghi=_or_none(ghi_col),
            confidence={},  # manuel secim - guven skorlamasi yok
        )

        # IngestionPreview'i taklit et
        from pvquant.io.ingestion import IngestionPreview
        secilen = {v for v in [
            manual_mapping.timestamp,
            manual_mapping.power,
            manual_mapping.energy,
            manual_mapping.poa_irradiance,
            manual_mapping.temp_ambient,
            manual_mapping.temp_module,
            manual_mapping.wind_speed,
            manual_mapping.ghi,
        ] if v is not None}
        st.session_state.scada_preview = IngestionPreview(
            file_format=err.file_format,
            mapping=manual_mapping,
            unmapped_columns=[c for c in err.columns if c not in secilen],
            sample_rows=err.sample_rows,
            matched_template=None,
            notes=["Manuel esleme kullanildi."],
        )
        # Manuel esleme bayrakini kaldir ki normal akis devam etsin
        st.session_state.pop("scada_mapping_failed", None)
        st.rerun()


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
    ui_kit.adimlar(aktif=2)

    if st.button("← Yol ayrimina don", key="scada_geri", type="secondary"):
        st.session_state.veri_yukleme_mod = "yol_ayrimi"
        for k in ("scada_preview", "scada_result", "scada_clean", "scada_batch_id",
                  "scada_filename", "scada_tmp_path",
                  "scada_mapping_failed"):
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
        for k in ("scada_preview", "scada_result", "scada_clean", "scada_batch_id",
                  "scada_mapping_failed"):
            st.session_state.pop(k, None)
        
        # Yeni gecici dosya
        suffix = "." + uploaded.name.rsplit(".", 1)[-1]
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(uploaded.getvalue())
            st.session_state.scada_tmp_path = tmp.name
        st.session_state.scada_filename = uploaded.name

    tmp_path = st.session_state.scada_tmp_path
    
    # Preview cagirma (cache session'da)
    if "scada_preview" not in st.session_state and \
       "scada_mapping_failed" not in st.session_state:
        try:
            with st.spinner("Dosya analiz ediliyor..."):
                pv = preview_file(tmp_path, template_store=_TEMPLATE_STORE)
            st.session_state.scada_preview = pv
        except MappingFailedError as e:
            # Yapilandirilmis istisna: manuel esleme ekrani kur
            st.session_state.scada_mapping_failed = e
        except Exception as e:
            st.error(f"Dosya okunurken hata: {e}")
            st.info(
                "Ipucu: Dosyanizda en azindan bir 'zaman' ve bir 'guc/enerji' "
                "kolonu olmali. Baslik satiri dosyanin ilk 10 satirinda olmali."
            )
            return
    
    # Manuel esleme gerekiyor mu?
    if "scada_mapping_failed" in st.session_state:
        _manuel_esleme_ekrani(
            st.session_state.scada_mapping_failed, tmp_path,
        )
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
    plant_ctx = _adim1_santral()
    
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
            for k in ("scada_preview", "scada_result", "scada_clean", "scada_batch_id",
                      "scada_filename", "scada_tmp_path",
                      "scada_mapping_failed"):
                st.session_state.pop(k, None)
            st.rerun()
    with col2:
        # Kalibrasyona gec - clean frame -> SCADAData kopru
        if st.button(
            "Kalibrasyona gec →",
            key="kalibrasyona_gec",
            use_container_width=True,
            type="primary",
        ):
            # ---- FAZ 2 (Fable 5 v1.4): DB'ye kalicilastir ----
            auth = st.session_state.get("auth")
            aktif_pid = st.session_state.get("aktif_plant_id")
            plant_ctx = st.session_state.get("plant_context", {})
            if auth and aktif_pid and plant_ctx:
                try:
                    with st.spinner("Kalicilastiriliyor..."):
                        out = ingest_service.yukle_ve_kaydet(
                            auth["tenant_id"],
                            aktif_pid,
                            tmp_path,
                            capacity_kwp=plant_ctx["capacity_kwp"],
                            latitude=plant_ctx["latitude"],
                            longitude=plant_ctx["longitude"],
                            source_timezone=plant_ctx["timezone"],
                            file_format=result.file_format,
                            mapping=result.mapping,
                            hazir_sonuc=result,
                        )
                    st.session_state.scada_batch_id = out["batch_id"]
                    # Sablonu ONAY DALINDA kaydet (Fable 5 v1.4)
                    try:
                        _TEMPLATE_STORE.save(
                            f"user_{uploaded.name.rsplit('.', 1)[0]}",
                            result.to_template(),
                        )
                    except Exception:
                        pass  # sablon kaydi kritik degil
                    st.toast(
                        f"Kalicilastirildi ✓ · {out['n_satir']} satir kaydedildi"
                    )
                except Exception as e:
                    st.error(f"Kalicilastirma hatasi: {e}")
                    return
            _kopru_scadadata_ve_gec()
            st.rerun()


# ============================================================
# KOPRU: Ingestion -> Kalibrasyon (scada_clean -> SCADAData)
# ============================================================

def _kopru_scadadata_ve_gec() -> None:
    """Ingestion cikti (scada_clean DataFrame) -> SCADAData kopru.

    Kalibrasyon sayfasi eski SCADAData nesnesi bekliyor; ingestion
    ise DataFrame + plant_context dondu. Burada kolon adlarini
    ceviriyor ve dataclass'i insa ediyoruz.

    Kolon esleme (ingestion adi -> SCADAData adi):
      power_kw       -> power_kw          (ayni)
      energy_kwh     -> energy_kwh        (ayni)
      poa_global     -> poa_irradiance    (ad degisir!)
      t_air          -> temp_ambient      (ad degisir!)
      t_module       -> temp_module       (ad degisir!)
      wind_speed     -> wind_speed        (ayni)
    """
    from pvquant.io.scada import SCADAData

    clean = st.session_state.scada_clean  # DataFrame
    filename = st.session_state.get("scada_filename", "SCADA verisi")

    # timestamp kolonunu index yap (SCADAData'nin tum serileri paylasan index)
    df = clean.set_index("timestamp") if "timestamp" in clean.columns else clean

    # KOPRU FIX: kalibrasyon backend'i tam saatlik izgara bekliyor
    # (_detect_timestep_hours %90+ tutarlilik istiyor). Ingestion sadece
    # VALID satirlari veriyor -> gece saatleri dusuyor -> diff'ler bozuluyor.
    # Cozum: full saatlik range'e reindex, eksik saatler NaN kalir.
    # power_kw NaN olan gece saatleri kalibrasyona zaten girmez (backend
    # asagi akista dropna yapar) ama index tutarli olur.
    if isinstance(df.index, pd.DatetimeIndex) and len(df) > 1:
        full_range = pd.date_range(
            start=df.index.min(),
            end=df.index.max(),
            freq="1h",
            tz=df.index.tz,
        )
        df = df.reindex(full_range)
        df.index.name = "timestamp"
        
        # Gece saatlerinde NaN power_kw -> 0 doldur (gerçekte uretim yok)
        # Gunduz NaN'lari NaN kalir (backend duser). Boylece index tam kalir
        # ama gunduzun tam satirlari kesintisiz olur -> %90+ tutarlilik.
        try:
            import pvlib
            solpos = pvlib.solarposition.get_solarposition(
                df.index,
                st.session_state.plant_context["latitude"],
                st.session_state.plant_context["longitude"],
            )
            is_night = solpos["apparent_elevation"] < -3.0
            night_nan_mask = is_night.values & df["power_kw"].isna().values
            df.loc[night_nan_mask, "power_kw"] = 0.0
        except Exception:
            # pvlib yoksa fallback: tum NaN'lari 0 yap (daha az temiz ama calisir)
            df["power_kw"] = df["power_kw"].fillna(0.0)

    def _opt(col_name: str):
        """Kolon varsa Series don, yoksa None."""
        return df[col_name] if col_name in df.columns else None

    scada = SCADAData(
        power_kw=df["power_kw"],
        energy_kwh=_opt("energy_kwh"),
        poa_irradiance=_opt("poa_global"),   # ingestion "poa_global" -> SCADAData "poa_irradiance"
        temp_ambient=_opt("t_air"),          # ingestion "t_air" -> SCADAData "temp_ambient"
        temp_module=_opt("t_module"),        # ingestion "t_module" -> SCADAData "temp_module"
        wind_speed=_opt("wind_speed"),
        plant_name=filename.rsplit(".", 1)[0],
        timestep_minutes=60,  # ingestion her zaman saatlige indiriyor
    )

    st.session_state.scada_data = scada
    st.session_state.scada_filename = filename  # kalibrasyon.py bunu kullaniyor
    st.session_state.active_page = "kalibrasyon"


# ============================================================
# ANA render
# ============================================================

def render_veri_yukleme() -> None:
    if "veri_yukleme_mod" not in st.session_state:
        st.session_state.veri_yukleme_mod = "yol_ayrimi"

    mod = st.session_state.veri_yukleme_mod

    if mod == "scada_upload":
        page_header(
            "Veri Yükleme",
            "SCADA verinizi yukleyin — format otomatik tespit + kalite kontrolu",
        )
        _render_mod_b_scada()
    elif mod == "hizli":
        st.session_state.veri_yukleme_mod = "yol_ayrimi"
        st.info("Hızlı tahmin akışı Adım 5'te gelecek. Şimdilik yol ayrımına döndürüldünüz.")
        _render_mod_a_wrapper()
    else:
        _render_mod_a_wrapper()


def _render_mod_a_wrapper():
    page_header(
        "Veri Yükleme",
        "Tahmin yolunuzu seçin — SCADA veriniz varsa kalibre tahmine geçin",
    )
    _render_mod_a()