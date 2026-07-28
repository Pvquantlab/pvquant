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

"Kalibrasyona gec" butonu ingestion sonucunu DB'ye kalicilastirir
(yukle_ve_kaydet) ve dogrudan Kalibrasyon sayfasina gecirir. Ara SCADAData
kopru katmani v2.30'da silindi -- Kalibrasyon sayfasi zaten DB'den okur.
"""

import os
import sys
import tempfile
from pathlib import Path

import streamlit as st
import ui_kit
from pvquant.services import forecast_service
from pvquant.services import ingest_service
from pvquant.services import plant_service

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
        width="stretch",
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
        # B-1 Adım 2: AC gücü opsiyonel (invertör toplamı) — boş=None
        _ac_saved = saved.get("ac_limit_kw")
        ac_limit_kw = st.number_input(
            "AC gücü (kW, invertör toplamı) — opsiyonel",
            min_value=None, max_value=None,
            value=float(_ac_saved) if _ac_saved is not None else None,
            step=100.0, key="ing_ac_limit",
            help="Bilmiyorsanız boş bırakın; kırpma modeli buna göre çalışır.",
        )
        latitude = st.number_input(
            "Enlem",
            min_value=-90.0, max_value=90.0,
            value=float(saved.get("latitude", 37.87)),
            step=0.01, format="%.4f", key="ing_lat",
        )
    with col2:
        # v2.42: TUM IANA saat dilimleri — sik kullanilanlar en ustte
        import zoneinfo
        _sik = ["Europe/Istanbul", "UTC",
                "Etc/GMT+5", "Etc/GMT+6", "Etc/GMT+7", "Etc/GMT+8",
                "America/New_York", "America/Chicago", "America/Denver",
                "America/Los_Angeles", "Asia/Kolkata", "Europe/Berlin",
                "Europe/London", "Asia/Tokyo", "Australia/Sydney"]
        _hepsi = sorted(zoneinfo.available_timezones() - set(_sik))
        timezone_options = _sik + _hepsi
        default_tz = saved.get("timezone", "Europe/Istanbul")
        tz_index = (timezone_options.index(default_tz)
                    if default_tz in timezone_options else 0)
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
        # v2.52: panel tipi kunyenin parcasidir — kWp neyse bu da o.
    panel_tipi = st.selectbox(
        "Panel tipi",
        ["Tek yüzlü (monofacial)", "Çift yüzlü (bifacial)"],
        index=(1 if saved.get("panel_tech") == "bifacial" else 0),
        help="Çift yüzlü panelde arka yüz katkısı (BG·BF·A) modele girer; "
             "BG değerini kalibrasyon sahanızın verisinden öğrenir.")
    _panel_tech = "bifacial" if "bifacial" in panel_tipi else "monofacial"

    # v2.39-C: yarimkure bekcisi — tz ile boylam isareti celisirse uyar
    _bati = timezone.startswith(("America", "Etc/GMT+"))
    if _bati and longitude > 0:
        st.warning("Batı yarımküre saat dilimi + pozitif boylam: ABD "
                   "sahaları için boylam EKSİ olmalı (ör. −73,25).")
    elif (not _bati) and timezone != "UTC" and longitude < 0:
        st.warning("Doğu yarımküre saat dilimi + negatif boylam — kontrol edin.")
    
    return {
        "name": _ad.strip(),
        "panel_tech": _panel_tech,
        "capacity_kwp": capacity,
        "ac_limit_kw": ac_limit_kw,
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
            # plant_ctx türetilmis görünüm (Fable 5 v1.4)
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
    if st.button("Devam", type="primary", width="stretch",
                 key="adim1_devam"):
        try:
            pid = plant_service.olustur(
                auth["tenant_id"],
name=(plant_ctx_form.get("name") or "Yeni santral"),
                panel_tech=plant_ctx_form.get("panel_tech") or "monofacial",                lat=plant_ctx_form["latitude"],
                lon=plant_ctx_form["longitude"],
                tz=plant_ctx_form["timezone"],
                capacity_kwp=plant_ctx_form["capacity_kwp"],
                ac_limit_kw=plant_ctx_form.get("ac_limit_kw"),
            )
            st.session_state.aktif_plant_id = pid
            st.session_state.pop("aktif_santral_ad", None)  # v2.39-B: seçici yeni listeyle kurulsun
            st.session_state.plant_context = plant_ctx_form
            st.rerun()
        except Exception as e:
            st.error(f"Santral oluşturulamadı: {e}")
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
            ✓ '{pv.matched_template}' ✓ Dosya yapısı tanındı — önceki yüklemeden öğrenilen kalıpla okundu
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
            st.dataframe(err.sample_rows, width="stretch", height=280)

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
            help="Anlık güç değerleri. Bu YOKSA enerji kolonu seçmelisiniz.",
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
    if st.button("Bu eşleme ile devam et", key="manuel_devam",
                 type="primary", width="stretch"):
        if timestamp_col == "(seçiniz)":
            st.error("Zaman kolonu zorunludur.")
            return
        if power_col == "(seçiniz)" and energy_col == "(seçiniz)":
            st.error("En az bir güç veya enerji kolonu seçmelisiniz.")
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

    if st.button("← Yol ayrımına dön", key="scada_geri", type="secondary"):
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
            SCADA verinizi yükleyin
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

    # --- v2.41 bekcileri: uyarir, ENGELLEMEZ ---
    import re as _re
    _ad = st.session_state.get("scada_filename", "") or ""
    if _ad.upper().startswith(("DA_", "HA4_")):
        st.warning(
            "Bu dosya adı bir tahmin dosyasına işaret ediyor (DA_/HA4_ öneki). "
            "Kalibrasyon, SCADA üretim verisi bekler — tahmin verisiyle sonuçlar "
            "anlamsız olur. Emin değilseniz Actual/SCADA dosyanızı seçin.")
    _m = _re.search(r"(\d+(?:\.\d+)?)MW", _ad, _re.IGNORECASE)
    if _m:
        _dosya_kw = float(_m.group(1)) * 1000.0
        _auth = st.session_state.get("auth")
        _pid = st.session_state.get("aktif_plant_id")
        if _auth and _pid:
            try:
                _p = plant_service.getir(_auth["tenant_id"], _pid)
                _kayit_kw = float((_p or {}).get("capacity_kwp") or 0)
                from pvquant.config import get_settings as _vgs
                _tol = _vgs().guard_capacity_tolerance
                if _kayit_kw > 0 and abs(_dosya_kw - _kayit_kw) / _kayit_kw > _tol:
                    st.warning(
                        f"Dosya adı ~{_m.group(1)} MW kapasiteye işaret ediyor; "
                        f"seçili santralın kaydı {_kayit_kw:.0f} kWp. "
                        "Yanlış santrala yüklüyor olabilirsiniz.")
            except Exception:
                pass

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
        st.dataframe(pv.sample_rows, width="stretch", height=280)
    
    # Santral bilgisi formu
    st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)
    plant_ctx = _adim1_santral()
    # v2.39-C: santral olusmadan Onayla cizilmez (NoneType kazasi)
    if plant_ctx is None:
        st.caption("Önce santral bilgisini doldurup Devam'a basın — "
                   "doğrulama, santral oluştuktan sonra açılır.")
        return
    
    
    # --- BOLUM 2: Onayla + Karne ---
    
    st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)
    
    if "scada_result" not in st.session_state:
        if st.button(
            "Onayla ve doğrula",
            key="ingest_onayla",
            width="stretch",
            type="primary",
        ):
            try:
                with st.spinner("Veri dönüştürülüyor ve doğrulanıyor…"):
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
                st.session_state.plant_context = plant_ctx
                st.rerun()
            except Exception as e:
                st.error(f"İşlem sırasında hata: {e}")
                return
        return
    
    # Sonuc var - kalite karnesi goster
    result = st.session_state.scada_result
    _kalite_karnesi_karti(result)
    
    # Alt butonlar
    st.markdown("<div style='margin-top:20px'></div>", unsafe_allow_html=True)
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Farklı dosya seç", key="farkli_dosya", width="stretch"):
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
            "Kalibrasyona geç →",
            key="kalibrasyona_gec",
            width="stretch",
            type="primary",
        ):
            # ---- FAZ 2 (Fable 5 v1.4): DB'ye kalicilastir ----
            auth = st.session_state.get("auth")
            aktif_pid = st.session_state.get("aktif_plant_id")
            plant_ctx = st.session_state.get("plant_context", {})
            # v2.30-Ek: iki ayrı teşhis (K10: sayfada tek banner, iki dal aynı anda tetiklenmez)
            if not (auth and aktif_pid):
                ui_kit.banner("hata", "Oturum süresi dolmuş görünüyor — "
                                      "yeniden giriş yapın.")
                st.stop()
            if not plant_ctx:
                ui_kit.banner("hata", "Santral bilgisi bulunamadı — "
                                      "Adım 1'e dönüp santral seçin.")
                st.stop()
            try:
                with st.spinner("Kalıcılaştırılıyor…"):
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
                except Exception as e:
                    print(f"[sablon][kaydedilemedi] {e}")  # v2.30-Ek: sessiz-kullaniciya/gorunur-loga
                st.toast(
                    f"Kalıcılaştırıldı ✓ · {out['n_satir']} satır kaydedildi"
                )
            except Exception as e:
                st.error(f"Kalıcılaştırma hatası: {e}")
                return
            # v2.30: onay dali pop (batch_id kalir - karne referansi)
            for k in ("scada_clean", "scada_preview", "scada_result"):
                st.session_state.pop(k, None)
            ui_kit.sayfaya_git("kalibrasyon")


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
            "SCADA verinizi yükleyin — format otomatik tespit + kalite kontrolü",
        )
        _render_mod_b_scada()
    elif mod == "hizli":
        _render_mod_hizli()
    else:
        _render_mod_a_wrapper()


def _render_mod_hizli():
    """Hızlı tahmin (Mod A — v2.32): kalibrasyon YOK, mevcut
    uret_ve_kaydet kalibrasyonsuz çağrılır; sonuç Tahminler'de."""
    auth = st.session_state.get("auth")
    aktif_pid = st.session_state.get("aktif_plant_id")
    if not (auth and aktif_pid):
        ui_kit.banner("hata", "Oturum süresi dolmuş görünüyor — "
                              "yeniden giriş yapın.")
        st.stop()
    santral = plant_service.getir(auth["tenant_id"], aktif_pid)
    if santral is None:
        ui_kit.banner("hata", "Santral bilgisi bulunamadı — "
                              "Adım 1'e dönüp santral seçin.")
        st.stop()
    with st.spinner("Hızlı tahmin üretiliyor… 10-20 sn"):
        forecast_service.uret_ve_kaydet(auth["tenant_id"], santral)
    st.toast("Tahmin hazır ✓")
    ui_kit.sayfaya_git("tahminler")


def _render_mod_a_wrapper():
    page_header(
        "Veri Yükleme",
        "Tahmin yolunuzu seçin — SCADA veriniz varsa kalibre tahmine geçin",
    )
    _render_mod_a()