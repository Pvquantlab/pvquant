"""
PVQuant Kalibrasyon Ekrani (Faz 2 Adim 4b)

Adim 4b.1: PlantSpec formu + validation
Adim 4b.2: Open-Meteo get_historical
Adim 4b.3: calibrate_from_scada + sonuç gösterimi (sonra)

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

    # SCADA ozeti (kucuk)
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

    # Form basligi
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

    # === Konum ===
    st.markdown(
        f'<div class="pvq-microlabel" style="margin-top:24px;margin-bottom:8px">'
        f'KONUM'
        f'</div>',
        unsafe_allow_html=True,
    )
    lat_col, lon_col = st.columns(2)
    with lat_col:
        latitude = st.number_input(
            "Enlem",
            min_value=-90.0,
            max_value=90.0,
            value=st.session_state.get("form_latitude", 37.87),
            step=0.01,
            format="%.4f",
            key="form_latitude",
            help="Konya icin ornek: 37.87",
        )
    with lon_col:
        longitude = st.number_input(
            "Boylam",
            min_value=-180.0,
            max_value=180.0,
            value=st.session_state.get("form_longitude", 32.49),
            step=0.01,
            format="%.4f",
            key="form_longitude",
            help="Konya icin ornek: 32.49",
        )

    # === Kurulu guc ===
    st.markdown(
        f'<div class="pvq-microlabel" style="margin-top:24px;margin-bottom:8px">'
        f'KURULU GUC'
        f'</div>',
        unsafe_allow_html=True,
    )
    p_nom_kwp = st.number_input(
        "Nominal DC guc (kWp)",
        min_value=1.0,
        max_value=1_000_000.0,
        value=st.session_state.get("form_p_nom_kwp", 2500.0),
        step=100.0,
        format="%.1f",
        key="form_p_nom_kwp",
        help="Panel etiketlerindeki nominal gucun toplami. Ornek: 2500 kWp = 2.5 MW",
    )

    # === Panel yerleşimi ===
    st.markdown(
        f'<div class="pvq-microlabel" style="margin-top:24px;margin-bottom:8px">'
        f'PANEL YERLESIMI'
        f'</div>',
        unsafe_allow_html=True,
    )

    tilt_col, azimuth_col = st.columns(2)
    with tilt_col:
        tilt_bilmiyorum = st.checkbox(
            "Egimi bilmiyorum, model bulsun",
            key="form_tilt_fit",
        )
        tilt = st.number_input(
            "Egim (derece)",
            min_value=0.0,
            max_value=90.0,
            value=st.session_state.get("form_tilt", 30.0),
            step=1.0,
            format="%.1f",
            key="form_tilt",
            disabled=tilt_bilmiyorum,
            help="0 = yatay, 90 = dikey. Turkiye icin tipik 25-35 derece",
        )

    with azimuth_col:
        azimuth_bilmiyorum = st.checkbox(
            "Yonu bilmiyorum, model bulsun",
            key="form_azimuth_fit",
        )
        azimuth = st.number_input(
            "Yon (azimuth, derece)",
            min_value=0.0,
            max_value=360.0,
            value=st.session_state.get("form_azimuth", 180.0),
            step=1.0,
            format="%.1f",
            key="form_azimuth",
            disabled=azimuth_bilmiyorum,
            help="180 = guney (kuzey yarikure icin ideal), 90 = dogu, 270 = bati",
        )

    # XOR uyari
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

    # === Panel teknolojisi ===
    st.markdown(
        f'<div class="pvq-microlabel" style="margin-top:24px;margin-bottom:8px">'
        f'PANEL TEKNOLOJISI'
        f'</div>',
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

    # === Alt satir: aksiyon butonlari ===
    st.markdown("<div style='margin-top:32px'></div>", unsafe_allow_html=True)
    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button(
            "← Veri Yukleme'ye don",
            key="kal_geri",
            use_container_width=True,
        ):
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
    """Cache'lenmis Open-Meteo cagrisi.

    MeteoData nesnesi cache'lenemez (pd.Series icerir), bu yuzden
    dict'e cevirip cache'liyoruz. Daha sonra tekrar MeteoData'ya donuyoruz.
    """
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
        st.session_state.calibration_stage = "meteo_done"
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
        if st.button(
            "Tekrar dene",
            key="err_retry",
            use_container_width=True,
            type="primary",
        ):
            st.session_state.calibration_stage = "meteo_fetch"
            st.rerun()


def _stage_meteo_done() -> None:
    """Meteo cekildi, sirada calibrate_from_scada var (4b.3)."""
    meteo = st.session_state.historical_meteo
    n_saat = len(meteo.ghi)

    st.markdown(
        f"""
        <div class="pvq-card" style="border-left:3px solid {SUCCESS}">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
            <span style="color:{SUCCESS};font-size:18px">✓</span>
            <span style="font-size:15px;font-weight:600">
              Meteoroloji verisi basariyla cekildi
            </span>
          </div>
          <div style="font-size:13px;color:{TEXT_SECONDARY}">
            {n_saat:,} saatlik veri ({meteo.timezone}) hazir.
          </div>
        </div>
        """.replace(",", "."),
        unsafe_allow_html=True,
    )

    st.info(
        "Adim 4b.2 (Open-Meteo) tamam! "
        "Adim 4b.3 (calibrate_from_scada) henuz uygulanmadi."
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("← Forma don", key="done_geri", use_container_width=True):
            st.session_state.calibration_stage = "form"
            st.rerun()


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

    # SCADA yuklu mu?
    if "scada_data" not in st.session_state:
        _uyari_scada_yok()
        return

    # Stage yonetimi
    stage = st.session_state.get("calibration_stage", "form")
    if stage == "form":
        _santral_formu()
    elif stage == "meteo_fetch":
        _stage_meteo_fetch()
    elif stage == "meteo_error":
        _stage_meteo_error()
    elif stage == "meteo_done":
        _stage_meteo_done()
    else:
        _santral_formu()