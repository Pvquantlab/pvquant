"""
PVQuant Kalibrasyon Ekrani (Faz 2 Adim 4b)

Adim 4b.1: PlantSpec formu + validation
Adim 4b.2: Open-Meteo get_historical + cache + hata yonetimi
Adim 4b.3: calibrate_from_scada + Bulduklarimiz karti

Ön koşul: session_state.scada_data varsa devam eder, yoksa uyarır.
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from components import page_header
from design_tokens import PRIMARY, SUCCESS, TEXT_SECONDARY, TEXT_TERTIARY, WARNING


# ============================================================
# Sihirbaz gostergesi
# ============================================================

def _adim_gostergesi() -> None:
    """3 · Kalibrasyon aktif adim."""
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:12px;
                    margin-bottom:32px;font-size:13px;
                    font-family:IBM Plex Mono,monospace">
          <span style="display:inline-flex;align-items:center;gap:6px;color:{SUCCESS};font-weight:500">
            <span style="display:inline-flex;align-items:center;justify-content:center;
                         width:20px;height:20px;border-radius:50%;
                         background:{SUCCESS};color:white;font-size:11px">✓</span>
            Santral bilgisi
          </span>
          <span style="color:#CBD5E1">·</span>
          <span style="display:inline-flex;align-items:center;gap:6px;color:{SUCCESS};font-weight:500">
            <span style="display:inline-flex;align-items:center;justify-content:center;
                         width:20px;height:20px;border-radius:50%;
                         background:{SUCCESS};color:white;font-size:11px">✓</span>
            Veri yolu
          </span>
          <span style="color:#CBD5E1">·</span>
          <span style="display:inline-flex;align-items:center;gap:6px;color:{PRIMARY};font-weight:600">
            <span style="display:inline-flex;align-items:center;justify-content:center;
                         width:20px;height:20px;border-radius:50%;
                         background:{PRIMARY};color:white;font-size:11px">3</span>
            Sonuc
          </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# SCADA yoksa uyari
# ============================================================

def _uyari_scada_yok() -> None:
    """SCADA yuklenmemisse gosterilen ekran."""
    st.markdown(
        f"""
        <div class="pvq-card" style="border-left:3px solid {WARNING};
             text-align:center;padding:48px 24px">
          <div style="font-size:48px;margin-bottom:16px">📁</div>
          <div style="font-size:20px;font-weight:600;color:#0F1B28;
                      margin-bottom:12px">
            Once SCADA verinizi yukleyin
          </div>
          <div style="font-size:14px;color:{TEXT_SECONDARY};max-width:480px;
                      margin:0 auto 24px auto">
            Kalibrasyon icin gecmis uretim veriniz gerekiyor.
            Veri Yukleme sayfasindan CSV dosyanizi yukleyerek baslayin.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(
            "Veri Yukleme sayfasina git",
            key="git_veri_yukleme",
            use_container_width=True,
            type="primary",
        ):
            st.session_state.active_page = "veri_yukleme"
            st.session_state.veri_yukleme_mod = "scada_upload"
            st.rerun()


# ============================================================
# 4b.1: Santral bilgi formu
# ============================================================

def _santral_formu() -> None:
    """PlantSpec icin kullanici formu."""
    scada = st.session_state.scada_data
    filename = st.session_state.get("scada_filename", "SCADA verisi")
    n_kayit = len(scada.power_kw)

    st.markdown(
        f"""
        <div class="pvq-card" style="border-left:3px solid {SUCCESS};
             margin-bottom:24px;padding:16px 20px">
          <div style="display:flex;align-items:center;gap:8px;font-size:13px">
            <span style="color:{SUCCESS}">✓</span>
            <span style="color:{TEXT_SECONDARY}">Yuklenen veri:</span>
            <span style="font-weight:600;color:#0F1B28">{filename}</span>
            <span style="color:{TEXT_TERTIARY};font-family:IBM Plex Mono,monospace">
              · {n_kayit:,} kayit
            </span>
          </div>
        </div>
        """.replace(",", "."),
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div style="margin-bottom:16px">
          <div style="font-size:18px;font-weight:600;color:#0F1B28;
                      margin-bottom:6px">
            Santral bilgileri
          </div>
          <div style="font-size:13px;color:{TEXT_SECONDARY}">
            Model kendini santralinize uyarlarken bu bilgileri kullanacak.
            Bilmedikleriniz icin isaretleyin, model kendisi bulacak.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Konum
    st.markdown(
        '<div class="pvq-microlabel" style="margin-top:24px;margin-bottom:8px">KONUM</div>',
        unsafe_allow_html=True,
    )
    lat_col, lon_col = st.columns(2)
    with lat_col:
        latitude = st.number_input(
            "Enlem",
            min_value=-90.0, max_value=90.0,
            value=st.session_state.get("form_latitude", 37.87),
            step=0.01, format="%.4f",
            key="form_latitude",
            help="Konya icin ornek: 37.87",
        )
    with lon_col:
        longitude = st.number_input(
            "Boylam",
            min_value=-180.0, max_value=180.0,
            value=st.session_state.get("form_longitude", 32.49),
            step=0.01, format="%.4f",
            key="form_longitude",
            help="Konya icin ornek: 32.49",
        )

    # Kurulu guc
    st.markdown(
        '<div class="pvq-microlabel" style="margin-top:24px;margin-bottom:8px">KURULU GUC</div>',
        unsafe_allow_html=True,
    )
    p_nom_kwp = st.number_input(
        "Nominal DC guc (kWp)",
        min_value=1.0, max_value=1_000_000.0,
        value=st.session_state.get("form_p_nom_kwp", 2500.0),
        step=100.0, format="%.1f",
        key="form_p_nom_kwp",
        help="Panel etiketlerindeki nominal gucun toplami. Ornek: 2500 kWp = 2.5 MW",
    )

    # Panel yerlesimi
    st.markdown(
        '<div class="pvq-microlabel" style="margin-top:24px;margin-bottom:8px">PANEL YERLESIMI</div>',
        unsafe_allow_html=True,
    )
    tilt_col, azimuth_col = st.columns(2)
    with tilt_col:
        tilt_bilmiyorum = st.checkbox("Egimi bilmiyorum, model bulsun", key="form_tilt_fit")
        tilt = st.number_input(
            "Egim (derece)",
            min_value=0.0, max_value=90.0,
            value=st.session_state.get("form_tilt", 30.0),
            step=1.0, format="%.1f",
            key="form_tilt",
            disabled=tilt_bilmiyorum,
            help="0 = yatay, 90 = dikey. Turkiye icin tipik 25-35 derece",
        )
    with azimuth_col:
        azimuth_bilmiyorum = st.checkbox("Yonu bilmiyorum, model bulsun", key="form_azimuth_fit")
        azimuth = st.number_input(
            "Yon (azimuth, derece)",
            min_value=0.0, max_value=360.0,
            value=st.session_state.get("form_azimuth", 180.0),
            step=1.0, format="%.1f",
            key="form_azimuth",
            disabled=azimuth_bilmiyorum,
            help="180 = guney (kuzey yarikure icin ideal), 90 = dogu, 270 = bati",
        )

    if tilt_bilmiyorum and azimuth_bilmiyorum:
        st.markdown(
            f"""
            <div style="margin-top:12px;padding:10px 14px;
                        background:rgba(31,82,136,0.06);
                        border-left:3px solid {PRIMARY};
                        border-radius:4px;font-size:12px;color:#0F1B28">
              Ikisi birden bilinmiyorsa model once egimi tahmin eder, sonra
              yonu belirler. En az bir tanesini biliyorsaniz daha isabetli olur.
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Panel teknolojisi
    st.markdown(
        '<div class="pvq-microlabel" style="margin-top:24px;margin-bottom:8px">PANEL TEKNOLOJISI</div>',
        unsafe_allow_html=True,
    )
    tech_col, bifacial_col = st.columns(2)
    with tech_col:
        module_tech = st.selectbox(
            "Modul teknolojisi",
            options=["mono_si", "topcon", "hjt"],
            format_func=lambda x: {
                "mono_si": "Mono kristal (mono-Si)",
                "topcon": "TOPCon",
                "hjt": "Heterojunction (HJT)",
            }[x],
            index=0,
            key="form_module_tech",
        )
    with bifacial_col:
        bifacial = st.checkbox(
            "Cift yuzlu (bifacial) modul",
            key="form_bifacial",
            help="Modulun arka yuzu de uretim yapiyorsa isaretleyin",
        )

    # Aksiyon butonlari
    st.markdown("<div style='margin-top:32px'></div>", unsafe_allow_html=True)
    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("← Veri Yukleme'ye don", key="kal_geri", use_container_width=True):
            st.session_state.active_page = "veri_yukleme"
            st.session_state.veri_yukleme_mod = "scada_upload"
            st.rerun()

    with col2:
        if st.button(
            "Kalibrasyonu baslat →",
            key="kalibrasyonu_baslat",
            use_container_width=True,
            type="primary",
        ):
            from pvquant.pipeline.forecast import PlantSpec

            plant = PlantSpec(
                p_nom_kwp=p_nom_kwp,
                latitude=latitude,
                longitude=longitude,
                tilt=tilt,
                azimuth=azimuth,
                module_tech=module_tech,
                bifacial_factor=0.7 if bifacial else 0.0,
            )
            _pctx = st.session_state.get("plant_context", {})
            st.session_state.plant_display_name = (
                _pctx.get("plant_name")
                or st.session_state.get("scada_filename", "").rsplit(".", 1)[0]
                or "Santral"
            )
            st.session_state.plant_spec = plant
            st.session_state.calibration_fit_tilt = tilt_bilmiyorum
            st.session_state.calibration_fit_azimuth = azimuth_bilmiyorum
            st.session_state.calibration_stage = "meteo_fetch"
            st.rerun()


# ============================================================
# 4b.2: Open-Meteo tarihsel meteo cagrisi
# ============================================================

@st.cache_data(show_spinner=False, ttl=3600)
def _fetch_historical_meteo_cached(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
) -> dict:
    """Cache'lenmis Open-Meteo cagrisi."""
    from pvquant.io.meteo import OpenMeteoClient

    client = OpenMeteoClient()
    meteo = client.get_historical(
        latitude=latitude,
        longitude=longitude,
        start_date=start_date,
        end_date=end_date,
    )
    return {
        "ghi": meteo.ghi,
        "temp_air": meteo.temp_air,
        "wind_speed_10m": meteo.wind_speed_10m,
        "relative_humidity": meteo.relative_humidity,
        "cloud_cover": meteo.cloud_cover,
        "latitude": meteo.latitude,
        "longitude": meteo.longitude,
        "timezone": meteo.timezone,
    }


def _dict_to_meteodata(d: dict):
    """Cache'lenmis dict'i MeteoData nesnesine cevir."""
    from pvquant.io.meteo import MeteoData
    return MeteoData(
        ghi=d["ghi"],
        temp_air=d["temp_air"],
        wind_speed_10m=d["wind_speed_10m"],
        relative_humidity=d["relative_humidity"],
        cloud_cover=d["cloud_cover"],
        latitude=d["latitude"],
        longitude=d["longitude"],
        timezone=d["timezone"],
    )


def _stage_meteo_fetch() -> None:
    """Meteo cekilirken gosterilen ekran."""
    scada = st.session_state.scada_data
    plant = st.session_state.plant_spec

    start_date = scada.power_kw.index.min().strftime("%Y-%m-%d")
    end_date = scada.power_kw.index.max().strftime("%Y-%m-%d")

    st.markdown(
        f"""
        <div class="pvq-card" style="text-align:center;padding:48px 24px">
          <div style="font-size:48px;margin-bottom:16px">🌤</div>
          <div style="font-size:20px;font-weight:600;color:#0F1B28;
                      margin-bottom:12px">
            Meteoroloji verisi cekiliyor
          </div>
          <div style="font-size:14px;color:{TEXT_SECONDARY};max-width:520px;
                      margin:0 auto 24px auto">
            Santralinizin bulundugu konum icin
            <strong>{start_date}</strong> - <strong>{end_date}</strong>
            tarihleri arasindaki profesyonel meteoroloji verisi cekiliyor.
            Bu birkac saniye surer.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        with st.spinner("Tarihsel meteoroloji verisi cekiliyor..."):
            meteo_dict = _fetch_historical_meteo_cached(
                latitude=plant.latitude,
                longitude=plant.longitude,
                start_date=start_date,
                end_date=end_date,
            )
        meteo = _dict_to_meteodata(meteo_dict)
        st.session_state.historical_meteo = meteo
        st.session_state.calibration_stage = "calibrating"
        st.rerun()

    except Exception as e:
        st.session_state.calibration_stage = "meteo_error"
        st.session_state.calibration_error = str(e)
        st.rerun()


def _stage_meteo_error() -> None:
    """Meteo cekimi basarisiz oldu."""
    err = st.session_state.get("calibration_error", "Bilinmeyen hata")

    st.markdown(
        f"""
        <div class="pvq-card" style="border-left:3px solid {WARNING};
             text-align:center;padding:48px 24px">
          <div style="font-size:48px;margin-bottom:16px">⚠</div>
          <div style="font-size:20px;font-weight:600;color:#0F1B28;
                      margin-bottom:12px">
            Meteoroloji verisi cekilemedi
          </div>
          <div style="font-size:14px;color:{TEXT_SECONDARY};max-width:520px;
                      margin:0 auto 8px auto">
            Baglanti sorunu ya da servis gecici olarak kullanilmiyor olabilir.
          </div>
          <div style="font-size:12px;color:{TEXT_TERTIARY};
                      font-family:IBM Plex Mono,monospace;
                      margin-top:16px;padding:8px;
                      background:#F7F8F9;border-radius:4px;
                      max-width:600px;margin-left:auto;margin-right:auto">
            {err}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("← Forma don", key="err_geri", use_container_width=True):
            st.session_state.calibration_stage = "form"
            st.rerun()
    with col2:
        if st.button("Tekrar dene", key="err_retry", use_container_width=True, type="primary"):
            st.session_state.calibration_stage = "meteo_fetch"
            st.rerun()


# ============================================================
# 4b.3: calibrate_from_scada cagrisi
# ============================================================

def _stage_calibrating() -> None:
    """calibrate_from_scada calisiyor."""
    scada = st.session_state.scada_data
    meteo = st.session_state.historical_meteo
    plant = st.session_state.plant_spec
    fit_tilt = st.session_state.get("calibration_fit_tilt", False)
    fit_azimuth = st.session_state.get("calibration_fit_azimuth", False)

    fit_bilgi = ""
    if fit_tilt or fit_azimuth:
        fit_bilgi = " ve panel yerlesimini bulmaya"

    st.markdown(
        f"""
        <div class="pvq-card" style="text-align:center;padding:48px 24px">
          <div style="font-size:48px;margin-bottom:16px">🛡</div>
          <div style="font-size:20px;font-weight:600;color:#0F1B28;
                      margin-bottom:12px">
            Model santralinize uyarliyor
          </div>
          <div style="font-size:14px;color:{TEXT_SECONDARY};max-width:520px;
                      margin:0 auto 24px auto">
            Gecmis uretim veriniz ile meteoroloji verilerini karsilastirarak
            sistem verimlilik katsayilarini{fit_bilgi} calisiyor.
            Bu 30 saniyeye kadar surebilir.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        import time
        with st.spinner("Model kalibre ediliyor..."):
            from pvquant.pipeline.calibration import calibrate_from_scada

            t_start = time.time()
            result = calibrate_from_scada(
                scada=scada,
                historical_meteo=meteo,
                plant=plant,
                fit_bg=(plant.bifacial_factor > 0),
                fit_eta_bos=True,
                fit_tilt=fit_tilt,
                fit_azimuth=fit_azimuth,
                clean_outliers=True,
            )
            duration_sec = time.time() - t_start

        st.session_state.calibration_result = result
        st.session_state.calibration_duration_sec = duration_sec
        st.session_state.calibration_stage = "done"
        st.rerun()

    except Exception as e:
        import traceback
        st.session_state.calibration_stage = "calibrate_error"
        st.session_state.calibration_error = f"{type(e).__name__}: {e}"
        st.session_state.calibration_traceback = traceback.format_exc()
        st.rerun()


def _stage_calibrate_error() -> None:
    """calibrate_from_scada basarisiz."""
    err = st.session_state.get("calibration_error", "Bilinmeyen hata")
    tb = st.session_state.get("calibration_traceback", "")

    st.markdown(
        f"""
        <div class="pvq-card" style="border-left:3px solid {WARNING};
             text-align:center;padding:48px 24px">
          <div style="font-size:48px;margin-bottom:16px">⚠</div>
          <div style="font-size:20px;font-weight:600;color:#0F1B28;
                      margin-bottom:12px">
            Kalibrasyon tamamlanamadi
          </div>
          <div style="font-size:14px;color:{TEXT_SECONDARY};max-width:520px;
                      margin:0 auto 8px auto">
            Model verilerinizi analiz ederken bir sorunla karsilasti.
          </div>
          <div style="font-size:12px;color:{TEXT_TERTIARY};
                      font-family:IBM Plex Mono,monospace;
                      margin-top:16px;padding:12px;
                      background:#F7F8F9;border-radius:4px;
                      max-width:720px;margin-left:auto;margin-right:auto;
                      text-align:left;white-space:pre-wrap;overflow-x:auto">
            {err}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Teknik detay (traceback)"):
        st.code(tb, language="python")

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("← Forma don", key="cerr_geri", use_container_width=True):
            st.session_state.calibration_stage = "form"
            st.rerun()
    with col2:
        if st.button("Tekrar dene", key="cerr_retry", use_container_width=True, type="primary"):
            st.session_state.calibration_stage = "calibrating"
            st.rerun()


def _stage_done() -> None:
    """Kalibrasyon basarili - Bulduklarimiz karti + sonuc."""
    result = st.session_state.calibration_result
    original_plant = result.original_plant
    calibrated_plant = result.plant
    v_after = result.validation_after
    duration_sec = st.session_state.get("calibration_duration_sec", 0.0)

    # Basari basligi
    st.markdown(
        f"""
        <div style="text-align:center;margin-bottom:32px">
          <div style="font-size:56px;margin-bottom:12px">✓</div>
          <div style="font-size:24px;font-weight:700;color:{SUCCESS};
                      letter-spacing:-0.02em;margin-bottom:8px">
            Kalibrasyon tamamlandi
          </div>
          <div style="font-size:14px;color:{TEXT_SECONDARY}">
            Model artik santralinizin karakterine gore ayarli.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # KPI seridi
    sapma_pct = v_after.total_deviation_pct
    mape_pct = v_after.mape_pct
    n_saat = result.n_valid_hours
    n_str = f"{n_saat:,}".replace(",", ".")

    kpi_cols = st.columns(4)
    with kpi_cols[0]:
        st.markdown(
            f'<div class="pvq-card">'
            f'<div class="pvq-microlabel">SAPMA</div>'
            f'<div class="pvq-kpi-value pvq-kpi-value--success">'
            f'<span class="pvq-mono">%{sapma_pct:+.2f}</span>'
            f'</div>'
            f'<div class="pvq-kpi-subtitle">kalibrasyon sonrasi</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with kpi_cols[1]:
        st.markdown(
            f'<div class="pvq-card">'
            f'<div class="pvq-microlabel">ORTALAMA TAHMIN HATASI</div>'
            f'<div class="pvq-kpi-value pvq-kpi-value--primary">'
            f'<span class="pvq-mono">%{mape_pct:.1f}</span>'
            f'</div>'
            f'<div class="pvq-kpi-subtitle">saatlik MAPE</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with kpi_cols[2]:
        st.markdown(
            f'<div class="pvq-card">'
            f'<div class="pvq-microlabel">SURE</div>'
            f'<div class="pvq-kpi-value">'
            f'<span class="pvq-mono">{duration_sec:.0f}</span>'
            f'<span class="pvq-kpi-unit">sn</span>'
            f'</div>'
            f'<div class="pvq-kpi-subtitle">kalibrasyon</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with kpi_cols[3]:
        st.markdown(
            f'<div class="pvq-card">'
            f'<div class="pvq-microlabel">VERI</div>'
            f'<div class="pvq-kpi-value">'
            f'<span class="pvq-mono">{n_str}</span>'
            f'</div>'
            f'<div class="pvq-kpi-subtitle">saat islendi</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Bulduklarimiz karti
    st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)

    bulgular = []
    bulgular.append({
        "isim": "Sistem verimlilik katsayisi",
        "eski": None,
        "yeni": f"{result.eta_bos:.3f}",
    })

    if calibrated_plant.bifacial_factor > 0:
        bulgular.append({
            "isim": "Bifacial kazanci (BG)",
            "eski": None,
            "yeni": f"{result.bg:.3f}",
        })

    fit_tilt = st.session_state.get("calibration_fit_tilt", False)
    if fit_tilt:
        bulgular.append({
            "isim": "Panel egimi (tilt)",
            "eski": f"{original_plant.tilt:.0f}°",
            "yeni": f"{calibrated_plant.tilt:.1f}°",
        })

    fit_azimuth = st.session_state.get("calibration_fit_azimuth", False)
    if fit_azimuth:
        bulgular.append({
            "isim": "Panel yonu (azimuth)",
            "eski": f"{original_plant.azimuth:.0f}°",
            "yeni": f"{calibrated_plant.azimuth:.1f}°",
        })

    bulgular_html = ""
    for i, b in enumerate(bulgular):
        border = "" if i == len(bulgular) - 1 else "border-bottom:1px solid #E2E6EA;"
        if b["eski"] is None:
            deger_html = (
                f'<span style="font-family:IBM Plex Mono,monospace;'
                f'font-size:14px;font-weight:600;color:#0F1B28">'
                f'{b["yeni"]}</span>'
            )
        else:
            deger_html = (
                f'<span style="font-family:IBM Plex Mono,monospace;font-size:14px">'
                f'<span style="color:{TEXT_TERTIARY};text-decoration:line-through">'
                f'{b["eski"]}</span>'
                f'<span style="color:{TEXT_SECONDARY};margin:0 8px">→</span>'
                f'<span style="font-weight:600;color:#0F1B28">{b["yeni"]}</span>'
                f'</span>'
            )
        bulgular_html += (
            f'<div style="display:flex;justify-content:space-between;'
            f'align-items:center;padding:12px 0;{border}">'
            f'<div style="display:flex;align-items:center;gap:8px">'
            f'<span style="color:{PRIMARY};font-size:14px">🛡</span>'
            f'<span style="font-size:14px">{b["isim"]}</span>'
            f'</div>'
            f'{deger_html}'
            f'</div>'
        )

    st.markdown(
        f'<div class="pvq-card">'
        f'<div style="font-size:15px;font-weight:600;color:#0F1B28;'
        f'margin-bottom:4px">Bulduklarimiz</div>'
        f'<div style="font-size:12px;color:{TEXT_SECONDARY};margin-bottom:8px">'
        f'Model, santraliniz hakkinda size yeni bir sey ogretti.'
        f'</div>'
        f'{bulgular_html}'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Uyarilar
    if result.warnings:
        uyari_html = "<br>".join(f"• {w}" for w in result.warnings)
        st.markdown(
            f'<div class="pvq-card" style="margin-top:16px;'
            f'border-left:3px solid {WARNING};background:rgba(201,80,46,0.04)">'
            f'<div style="font-size:13px;font-weight:600;color:#0F1B28;'
            f'margin-bottom:8px">Dikkat edilmesi gerekenler</div>'
            f'<div style="font-size:12px;color:{TEXT_SECONDARY};line-height:1.7">'
            f'{uyari_html}'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Aksiyon butonlari
    st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("← Forma don", key="done_geri", use_container_width=True):
            st.session_state.calibration_stage = "form"
            st.rerun()
    with col2:
        st.button(
            "Tahminlere gec →",
            key="tahminlere_gec",
            use_container_width=True,
            type="primary",
            disabled=True,
            help="Tahminler ekrani Adim 5'te gelecek",
        )


# ============================================================
# ANA render
# ============================================================

def render_kalibrasyon() -> None:
    """Kalibrasyon sayfasi ana render."""
    page_header(
        "Kalibrasyon",
        "Modeli santralinize uyarliyoruz. Santral bilgilerinizi girin.",
    )

    _adim_gostergesi()

    if "scada_data" not in st.session_state:
        _uyari_scada_yok()
        return

    stage = st.session_state.get("calibration_stage", "form")
    if stage == "form":
        _santral_formu()
    elif stage == "meteo_fetch":
        _stage_meteo_fetch()
    elif stage == "meteo_error":
        _stage_meteo_error()
    elif stage == "calibrating":
        _stage_calibrating()
    elif stage == "calibrate_error":
        _stage_calibrate_error()
    elif stage == "done":
        _stage_done()
    else:
        _santral_formu()