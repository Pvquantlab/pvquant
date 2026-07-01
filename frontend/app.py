"""PVQuant - Hassas Gunes Enerjisi Tahmini."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd
import numpy as np

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from pvquant.models_v2.contracts import (
    PlantProfile, Location, PanelSpec, MountingSpec, InverterSpec,
    ForecastInput,HistoricalData, OperationConfig,
)
from pvquant.models_v2.barhdadi_bennis import BarhdadiBennisModel
from pvquant.io.meteo import OpenMeteoClient
from pvquant.io.scada import load_csv
from pvquant.storage import save_plant, load_plant, list_plants, delete_plant


st.set_page_config(
    page_title="PVQuant",
    page_icon=":sun_with_face:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    font-feature-settings: 'cv02', 'cv03', 'cv04', 'cv11', 'tnum';
}

#MainMenu, footer, header[data-testid="stHeader"] {
    visibility: hidden !important;
    height: 0 !important;
}

/* HIDE STREAMLIT ANCHOR LINKS (zincir ikonlari) */
[data-testid="stHeaderActionElements"],
.stMarkdown a[href^="#"] {
    display: none !important;
}
h1 > div > a, h2 > div > a, h3 > div > a,
h1 a, h2 a, h3 a {
    display: none !important;
}

:root {
    --bg: #0A0E1A;
    --surface: #131825;
    --surface-2: #1A2030;
    --border: #232938;
    --border-strong: #2D3548;
    --text: #E6E9EF;
    --text-2: #8B92A7;
    --text-3: #555E72;
    --text-4: #3A4256;
    --accent: #F59E0B;
    --accent-hover: #FBBF24;
    --success: #10B981;
    --neutral: #6B7280;
    --danger: #EF4444;
    --info: #3B82F6;
}

.stApp { background: var(--bg) !important; }

.block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 4rem !important;
    max-width: 1280px !important;
}

/* === TOPBAR (border-bottom eklendi, daha disiplinli) === */
.pv-topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 0 1.25rem 0;
    margin-bottom: 3rem;
    border-bottom: 1px solid var(--border);
}
.pv-topbar-left { display: flex; align-items: center; gap: 0.75rem; }

/* LOGO: daha kompakt, padding'li */
.pv-logo-wrap {
    width: 30px; height: 30px;
    display: flex; align-items: center; justify-content: center;
    background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%);
    border-radius: 7px;
    box-shadow: 0 2px 8px rgba(245, 158, 11, 0.2);
}
.pv-logo-mark {
    color: #0A0E1A;
    font-weight: 800;
    font-size: 11px;
    letter-spacing: -0.02em;
    font-family: 'Inter', sans-serif;
}
.pv-brand-block { display: flex; flex-direction: column; gap: 1px; }
.pv-wordmark {
    font-size: 15px;
    font-weight: 700;
    color: var(--text);
    letter-spacing: -0.01em;
    line-height: 1.15;
}
.pv-tagline {
    font-size: 11px;
    color: var(--text-3);
    font-weight: 500;
    letter-spacing: 0.01em;
}
.pv-topbar-right { display: flex; align-items: center; gap: 0.75rem; }

/* MODE PILL: gri nokta default, renk anlamlari netlestirildi */
.pv-mode-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.4rem 0.85rem;
    background: var(--surface);
    border: 1px solid var(--border-strong);
    border-radius: 6px;
    font-size: 12px;
    font-weight: 500;
    color: var(--text-2);
}
.pv-mode-dot {
    width: 6px; height: 6px; border-radius: 50%;
}

/* === SIDEBAR === */
[data-testid="stSidebar"] {
    background: var(--bg) !important;
    border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] > div:first-child {
    padding-top: 1.5rem;
}
[data-testid="stSidebar"] .stRadio > label { display: none; }
[data-testid="stSidebar"] .stRadio > div { gap: 0.125rem; }
[data-testid="stSidebar"] [role="radiogroup"] label {
    background: transparent;
    border-radius: 6px;
    padding: 0.55rem 0.75rem !important;
    transition: background 0.15s;
    cursor: pointer;
}
[data-testid="stSidebar"] [role="radiogroup"] label:hover {
    background: var(--surface);
}
[data-testid="stSidebar"] [role="radiogroup"] label p {
    color: var(--text-2) !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    margin: 0 !important;
}
[data-testid="stSidebar"] [role="radiogroup"] label[data-baseweb="radio"]:has(input:checked) {
    background: var(--surface);
}
[data-testid="stSidebar"] [role="radiogroup"] label[data-baseweb="radio"]:has(input:checked) p {
    color: var(--text) !important;
    font-weight: 600 !important;
}

.pv-sidebar-section {
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-3);
    margin: 1.5rem 0 0.5rem 0;
    padding-left: 0.75rem;
}

.pv-sidebar-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.875rem;
    margin: 0.5rem 0;
}
.pv-sidebar-card-label {
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-3);
    margin-bottom: 0.35rem;
}
.pv-sidebar-card-value {
    font-size: 13px;
    font-weight: 600;
    color: var(--text);
}
.pv-sidebar-card-meta {
    font-size: 11px;
    color: var(--text-3);
    margin-top: 0.25rem;
}

/* === TYPOGRAPHY: hiyerarşi netlestirildi === */
h1 {
    font-size: 26px !important;
    font-weight: 700 !important;
    color: var(--text) !important;
    letter-spacing: -0.02em !important;
    margin: 0 0 0.25rem 0 !important;
    line-height: 1.2 !important;
}

/* SECTION HEADERS (HAFTALIK OZET, ICGORULER vb): belirgin ama hiyerarsi icinde */
h2 {
    font-size: 12px !important;
    font-weight: 700 !important;
    color: var(--text-2) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    margin: 3rem 0 1rem 0 !important;
    line-height: 1.3 !important;
}

/* FORM SECTIONS (GENEL, KONUM, PANEL): h2'den daha vurgulu */
h3 {
    font-size: 13px !important;
    font-weight: 700 !important;
    color: var(--text) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    margin: 2rem 0 1rem 0 !important;
    padding-bottom: 0.5rem !important;
    border-bottom: 1px solid var(--border) !important;
}

p, .stMarkdown, [data-testid="stCaptionContainer"] {
    color: var(--text-2) !important;
    font-size: 14px !important;
    line-height: 1.5 !important;
}

.pv-subtitle {
    color: var(--text-3);
    font-size: 13px;
    margin-bottom: 2.5rem;
}

/* === METRICS: daha kompakt, daha az padding === */
[data-testid="stMetric"] {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1rem 1.25rem;
    transition: border-color 0.15s;
}
[data-testid="stMetric"]:hover {
    border-color: var(--border-strong);
}
[data-testid="stMetricLabel"] {
    color: var(--text-3) !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    margin-bottom: 0.4rem !important;
}
[data-testid="stMetricValue"] {
    color: var(--text) !important;
    font-size: 24px !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
    font-variant-numeric: tabular-nums !important;
}
/* DELTA: yesil pill yerine sade gri metin */
[data-testid="stMetricDelta"] {
    color: var(--text-3) !important;
    font-size: 11px !important;
    font-weight: 500 !important;
    background: transparent !important;
    padding: 0 !important;
    margin-top: 0.25rem !important;
}
[data-testid="stMetricDelta"] svg { display: none !important; }
[data-testid="stMetricDelta"] > div {
    background: transparent !important;
    padding: 0 !important;
    color: var(--text-3) !important;
}

/* Metric columns arasi bosluk azaltildi */
[data-testid="column"] {
    gap: 0.75rem !important;
}

/* === BUTTONS: primary button text rengi netlestirildi === */
.stButton > button {
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
    font-size: 13px !important;
    border-radius: 8px !important;
    transition: all 0.15s !important;
    border: 1px solid var(--border-strong) !important;
    background: var(--surface) !important;
    color: var(--text) !important;
    padding: 0.5rem 1rem !important;
}
.stButton > button:hover {
    background: var(--surface-2) !important;
    border-color: var(--text-3) !important;
}
.stButton > button[kind="primary"],
.stButton > button[kind="primary"] p,
.stButton > button[kind="primary"] span,
.stButton > button[kind="primary"] div {
    background: var(--accent) !important;
    border-color: var(--accent) !important;
    color: #1A0F00 !important;
    font-weight: 700 !important;
}
.stButton > button[kind="primary"]:hover,
.stButton > button[kind="primary"]:hover p,
.stButton > button[kind="primary"]:hover span {
    background: var(--accent-hover) !important;
    border-color: var(--accent-hover) !important;
    color: #1A0F00 !important;
}
.stForm .stButton > button[kind="primary"] {
    color: #1A0F00 !important;
}

/* === FORMS: alan spacing artirildi, daha kompakt input === */
[data-testid="stForm"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    padding: 2rem !important;
}

/* Input alanlari: daha kompakt yukseklik */
.stTextInput input, .stNumberInput input {
    background: var(--bg) !important;
    border: 1px solid var(--border-strong) !important;
    border-radius: 6px !important;
    color: var(--text) !important;
    font-size: 14px !important;
    font-family: 'Inter', sans-serif !important;
    padding: 0.5rem 0.75rem !important;
}
.stSelectbox > div > div {
    background: var(--bg) !important;
    border: 1px solid var(--border-strong) !important;
    border-radius: 6px !important;
    color: var(--text) !important;
    font-size: 14px !important;
    min-height: 38px !important;
}
.stTextInput input:focus, .stNumberInput input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.1) !important;
}

/* NumberInput +/- butonlari daha kompakt */
.stNumberInput button {
    background: var(--surface) !important;
    border: 1px solid var(--border-strong) !important;
    height: 38px !important;
    width: 32px !important;
}
.stNumberInput button:hover {
    background: var(--surface-2) !important;
}

[data-testid="stForm"] label {
    color: var(--text-2) !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    margin-bottom: 0.25rem !important;
}

/* Form icindeki h3'lere ekstra ust bosluk */
[data-testid="stForm"] h3:first-child {
    margin-top: 0 !important;
}

/* === ALERTS === */
[data-testid="stAlert"] {
    border-radius: 8px !important;
    border-left-width: 3px !important;
    background: var(--surface) !important;
    color: var(--text) !important;
    font-size: 13px !important;
}

/* === DATAFRAME: header'lar uppercase, satir alternating === */
[data-testid="stDataFrame"] {
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    overflow: hidden !important;
}
[data-testid="stDataFrame"] thead th,
[data-testid="stDataFrame"] [data-testid="dataframe-header-cell"] {
    background: var(--surface) !important;
    color: var(--text-3) !important;
    font-size: 11px !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}
[data-testid="stDataFrame"] tbody tr:nth-child(even) {
    background: rgba(255,255,255,0.02) !important;
}

/* === DIVIDER === */
hr {
    border: none !important;
    border-top: 1px solid var(--border) !important;
    margin: 3rem 0 !important;
}

/* === SEGMENTED CONTROL (Saatlik/Gunluk/Haftalik) === */
.pv-view-toggle {
    display: inline-flex;
    background: var(--surface);
    padding: 4px;
    border-radius: 8px;
    border: 1px solid var(--border);
    margin-bottom: 1rem;
}

/* Radio'lari segmented control gibi yap */
div[data-testid="stHorizontalBlock"] > div > [data-testid="stRadio"] > div {
    flex-direction: row !important;
    gap: 0 !important;
    background: var(--surface);
    padding: 4px;
    border-radius: 8px;
    border: 1px solid var(--border);
}
div[data-testid="stHorizontalBlock"] > div > [data-testid="stRadio"] label {
    padding: 0.4rem 1rem !important;
    border-radius: 6px;
    margin: 0 !important;
}
div[data-testid="stHorizontalBlock"] > div > [data-testid="stRadio"] label:has(input:checked) {
    background: var(--surface-2);
}

/* === INSIGHT CARDS === */
.pv-insight-row {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin: 0.5rem 0 1rem 0;
}
.pv-insight-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1rem 1.25rem;
}
.pv-insight-label {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-3);
    margin-bottom: 0.5rem;
}
.pv-insight-value {
    font-size: 16px;
    font-weight: 700;
    color: var(--text);
    letter-spacing: -0.01em;
    font-variant-numeric: tabular-nums;
    text-transform: uppercase;
    letter-spacing: 0.02em;
}
.pv-insight-meta {
    font-size: 11px;
    color: var(--text-3);
    margin-top: 0.35rem;
    font-variant-numeric: tabular-nums;
}
</style>""", unsafe_allow_html=True)


if "plant" not in st.session_state:
    st.session_state.plant = None
if "forecast_result" not in st.session_state:
    st.session_state.forecast_result = None
if "meteo" not in st.session_state:
    st.session_state.meteo = None
if "calibrated" not in st.session_state:
    st.session_state.calibrated = False
if "calibration_result" not in st.session_state:
    st.session_state.calibration_result = None    
if "scada_df" not in st.session_state:
    st.session_state.scada_df = None
if "scada_filename" not in st.session_state:
    st.session_state.scada_filename = None
if "backtest_result" not in st.session_state:
    st.session_state.backtest_result = None

# === TOPBAR ===
# Pure Forecast = nötr durum = gri (uyari degil!)
calibrated = st.session_state.get("calibrated", False)
if calibrated:
    mode_label = "Calibrated"
    mode_color = "#10B981"  # yesil = aktif/saglikli
else:
    mode_label = "Pure Forecast"
    mode_color = "#6B7280"  # gri = notr/info

st.markdown(f"""
<div class='pv-topbar'>
    <div class='pv-topbar-left'>
        <div class="pv-logo-wrap"><span class="pv-logo-mark">PQ</span></div>
        <div class='pv-brand-block'>
            <span class='pv-wordmark'>PVQuant</span>
            <span class='pv-tagline'>Hassas Gunes Enerjisi Tahmini</span>
        </div>
    </div>
    <div class='pv-topbar-right'>
        <div class='pv-mode-pill'>
            <span class='pv-mode-dot' style='background: {mode_color};'></span>
            {mode_label}
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# === SIDEBAR ===
with st.sidebar:
    st.markdown("<div class='pv-sidebar-section'>CALISMA ALANI</div>", unsafe_allow_html=True)
    page = st.radio(
        "Navigasyon",
        ["Santral Kayit", "7 Gunluk Tahmin"],
        label_visibility="collapsed",
    )

    # KAYITLI SANTRALLER - diske kaydedilmis tum santraller
    saved_plants = list_plants()
    if saved_plants:
        st.markdown("<div class='pv-sidebar-section'>KAYITLI SANTRALLER</div>", unsafe_allow_html=True)
        # Saved-plant kart stilleri (sidebar icin ozel)
        st.markdown("""
        <style>
        .pv-saved-card {
            background: rgba(255,255,255,0.02);
            border: 1px solid rgba(255,255,255,0.06);
            border-left: 3px solid transparent;
            border-radius: 8px;
            padding: 10px 12px;
            margin-bottom: 8px;
            transition: all 0.15s ease;
        }
        .pv-saved-card.active {
            border-left-color: #F59E0B;
            background: rgba(245, 158, 11, 0.04);
        }
        .pv-saved-name {
            font-size: 12px;
            font-weight: 600;
            color: #F3F4F6;
            letter-spacing: -0.01em;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            margin-bottom: 2px;
        }
        .pv-saved-meta {
            font-size: 10.5px;
            color: #9CA3AF;
            font-weight: 500;
            margin-bottom: 6px;
            letter-spacing: 0.01em;
        }
        .pv-saved-sapma {
            font-size: 11px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 5px;
            letter-spacing: -0.01em;
        }
        .pv-saved-sapma .dot {
            display: inline-block;
            width: 6px;
            height: 6px;
            border-radius: 50%;
        }
        /* Sidebar buttonlarini sadelestir */
        [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] button {
            background: transparent !important;
            border: 1px solid rgba(255,255,255,0.08) !important;
            color: #E5E7EB !important;
            font-size: 11px !important;
            font-weight: 500 !important;
            padding: 4px 8px !important;
            min-height: 28px !important;
            height: 28px !important;
            border-radius: 6px !important;
            box-shadow: none !important;
        }
        [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] button:hover {
            background: rgba(255,255,255,0.05) !important;
            border-color: rgba(255,255,255,0.12) !important;
        }
        /* Sil butonu hover'da kirmizi tonuna gecsin */
        [data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"]:has(span:contains("delete")):hover,
        [data-testid="stSidebar"] button[kind="secondary"][title*="kaydini sil"]:hover {
            background: rgba(239, 68, 68, 0.08) !important;
            border-color: rgba(239, 68, 68, 0.25) !important;
            color: #EF4444 !important;
        }
        /* Material ikonlarini hizala */
        [data-testid="stSidebar"] button span[data-testid="stIconMaterial"] {
            font-size: 16px !important;
        }
        </style>
        """, unsafe_allow_html=True)

        current_plant_id = st.session_state.plant.plant_id if st.session_state.plant else None
        tech_label_map = {"mono": "Monofacial", "bifacial": "Bifacial", "thin_film": "Ince Film"}

        for sp in saved_plants:
            sp_id = sp["plant_id"]
            is_active = (sp_id == current_plant_id)
            sapma = sp.get("yillik_sapma_pct")
            cap = sp.get("capacity_kwp") or 0
            tech = sp.get("panel_tech") or ""
            tech_tr = tech_label_map.get(tech, tech.title() if tech else "—")

            # Sapma rengi ve metni
            if sapma is None:
                sapma_color = "#6B7280"
                sapma_text = "Kalibre edilmedi"
            elif abs(sapma) <= 5:
                sapma_color = "#10B981"
                sapma_text = f"{sapma:+.2f}% sapma"
            elif abs(sapma) <= 10:
                sapma_color = "#F59E0B"
                sapma_text = f"{sapma:+.2f}% sapma"
            else:
                sapma_color = "#EF4444"
                sapma_text = f"{sapma:+.2f}% sapma"

            # Kart goruntusu
            active_class = "active" if is_active else ""
            st.markdown(f"""
            <div class='pv-saved-card {active_class}'>
                <div class='pv-saved-name' title='{sp_id}'>{sp_id}</div>
                <div class='pv-saved-meta'>{cap:,.0f} kWp - {tech_tr}</div>
                <div class='pv-saved-sapma' style='color:{sapma_color};'>
                    <span class='dot' style='background:{sapma_color};'></span>
                    {sapma_text}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Aksiyon butonlari (Yukle / Sil) - tek satir
            col_load, col_del = st.columns([4, 1])
            with col_load:
                if st.button(
                    "Aktif Santral" if is_active else "Bu Santrali Yukle",
                    key=f"load_{sp_id}",
                    use_container_width=True,
                    disabled=is_active,
                ):
                    loaded = load_plant(sp_id)
                    if loaded:
                        try:
                            st.session_state.plant = PlantProfile.model_validate(loaded["profile"])
                            st.session_state.forecast_result = None
                            st.session_state.calibrated = False
                            st.session_state.calibration_result = None
                            st.session_state.backtest_result = None
                            st.session_state.scada_df = None
                            st.session_state.scada_filename = None
                            st.rerun()
                        except Exception as load_err:
                            st.error(f"Yukleme hatasi: {load_err}")
            with col_del:
                if st.button(":material/delete:", key=f"del_{sp_id}", use_container_width=True, help=f"{sp_id} kaydini sil"):
                    if delete_plant(sp_id):
                        if current_plant_id == sp_id:
                            st.session_state.plant = None
                        st.rerun()

    if st.session_state.plant:
        plant = st.session_state.plant
        tech_tr = {"mono": "Monokristal", "bifacial": "Bifacial", "thin_film": "Ince Film"}
        st.markdown("<div class='pv-sidebar-section'>AKTIF SANTRAL</div>", unsafe_allow_html=True)
        st.markdown(f"""
        <div class='pv-sidebar-card'>
            <div class='pv-sidebar-card-value'>{plant.name}</div>
            <div class='pv-sidebar-card-meta'>{plant.dc_capacity_kwp:,.0f} kWp - {tech_tr.get(plant.panel.technology, plant.panel.technology)}</div>
        </div>
        <div class='pv-sidebar-card'>
            <div class='pv-sidebar-card-label'>Konum</div>
            <div class='pv-sidebar-card-value' style='font-size:12px; font-weight:500;'>{plant.location.latitude:.2f}N, {plant.location.longitude:.2f}E</div>
            <div class='pv-sidebar-card-meta'>{plant.location.elevation_m:.0f} m rakim</div>
        </div>
        """, unsafe_allow_html=True)


# === SAYFA: SANTRAL KAYIT ===
if "Santral" in page:
    col_title, col_action = st.columns([3, 1])
    with col_title:
        # HTML kullanarak baslik (Streamlit anchor link'i bypass)
        st.markdown("<h1 style='margin:0;'>Santral Kayit</h1>", unsafe_allow_html=True)
        st.markdown("<div class='pv-subtitle'>Santralinizin teknik ozelliklerini tanimlayin</div>", unsafe_allow_html=True)
    with col_action:
        if st.button("Ornek Veri", use_container_width=True):
            st.session_state._defaults = {
                "name": "MERKAS GES",
                "lat": 37.87, "lon": 32.49, "elev": 1000.0,
                "kwp": 4514, "panel_count": 8280,
                "tech": "bifacial", "power_w": 545,
                "gamma": -0.34, "bifaciality": 0.7,
                "tilt": 20.0, "azimuth": 180.0, "height": 2.0,
                "inv_kw": 215.0, "inv_count": 18,
            }
            st.rerun()

    d = st.session_state.get("_defaults", {})

    with st.form("plant_form"):
        # H3 olarak section headers
        st.markdown("<h3>Genel</h3>", unsafe_allow_html=True)
        name = st.text_input("Santral adi", value=d.get("name", ""), placeholder="Ornek: Konya GES 1")

        st.markdown("<h3>Konum</h3>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            lat = st.number_input("Enlem", value=d.get("lat", 39.0), format="%.4f")
        with c2:
            lon = st.number_input("Boylam", value=d.get("lon", 35.0), format="%.4f")
        with c3:
            elev = st.number_input("Rakim (m)", value=d.get("elev", 1000.0))

        st.markdown("<h3>Kapasite</h3>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            kwp = st.number_input("DC kapasite (kWp)", value=d.get("kwp", 1000), min_value=1)
        with c2:
            panel_count = st.number_input("Panel sayisi", value=d.get("panel_count", 2000), min_value=1)

        st.markdown("<h3>Panel</h3>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            tech_options = ["mono", "bifacial", "thin_film"]
            tech_labels = {"mono": "Monokristal", "bifacial": "Bifacial", "thin_film": "Ince Film"}
            tech = st.selectbox(
                "Teknoloji", options=tech_options,
                format_func=lambda x: tech_labels[x],
                index=tech_options.index(d.get("tech", "bifacial")),
            )
            power_w = st.number_input("Panel gucu (W)", value=d.get("power_w", 545), min_value=1)
        with c2:
            gamma = st.number_input("Sicaklik katsayisi gamma (%/C)", value=d.get("gamma", -0.34), format="%.3f")
            bifaciality = st.number_input("Bifaciality faktoru", value=d.get("bifaciality", 0.7), min_value=0.0, max_value=1.0, format="%.2f")

        st.markdown("<h3>Montaj</h3>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            tilt = st.number_input("Egim acisi (derece)", value=d.get("tilt", 20.0), min_value=0.0, max_value=90.0)
        with c2:
            azimuth = st.number_input("Azimut (derece, 180=Guney)", value=d.get("azimuth", 180.0), min_value=0.0, max_value=359.9)
        with c3:
            height = st.number_input("Yerden yukseklik (m)", value=d.get("height", 2.0), min_value=0.0)

        st.markdown("<h3>Inverter</h3>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            inv_kw = st.number_input("AC kapasite (kW)", value=d.get("inv_kw", 200.0))
        with c2:
            inv_count = st.number_input("Inverter sayisi", value=d.get("inv_count", 5), min_value=1)

        submitted = st.form_submit_button("Santrali Kaydet", use_container_width=True, type="primary")

        if submitted:
            if not name:
                st.error("Santral adi zorunludur")
            else:
                try:
                    plant = PlantProfile(
                        plant_id=name.lower().replace(" ", "_"), name=name,
                        location=Location(latitude=lat, longitude=lon, timezone="Europe/Istanbul", elevation_m=elev),
                        dc_capacity_kwp=kwp, panel_count=panel_count,
                        panel=PanelSpec(
                            technology=tech, nominal_power_w=power_w,
                            temperature_coefficient_gamma=gamma, noct_celsius=45,
                            bifaciality_factor=bifaciality if tech == "bifacial" else None,
                        ),
                        mounting=MountingSpec(
                            mount_type="ground_fixed", tilt_degrees=tilt,
                            azimuth_degrees=azimuth, height_above_ground_m=height,
                        ),
                        inverter=InverterSpec(ac_capacity_kw=inv_kw, count=inv_count, efficiency=0.98),
                    )
                    st.session_state.plant = plant
                    st.session_state.forecast_result = None
                    # Diske kalici yaz
                    try:
                        save_path = save_plant(plant.plant_id, plant)
                        st.success(
                            f"{name} kaydedildi (disk: {save_path.name}). "
                            f"Sol panelden 7 Gunluk Tahmin sayfasina gecebilirsiniz."
                        )
                    except Exception as save_err:
                        # Disk hatasi - session'da yine de duruyor, devam edilebilir
                        st.warning(
                            f"{name} session'a kaydedildi ama diske yazilamadi: {save_err}. "
                            "Streamlit yeniden baslarsa kaybolur."
                        )
                except Exception as e:
                    st.error(f"Hata: {e}")

# === MOD B: KALIBRASYON SECTION (form disinda, sayfa icinde) ===
    st.markdown("<h2>SCADA Verinizle Daha Hassas Tahmin</h2>", unsafe_allow_html=True)
    st.markdown(
        "<div class='pv-subtitle' style='margin-top: -0.5rem; margin-bottom: 2rem;'>"
        "Gecmis uretim verinizi yukleyerek modelimizin sizin santralinizde "
        "ne kadar isabetli tahmin ettigini gorun. "
        "Bu adim opsiyoneldir."
        "</div>",
        unsafe_allow_html=True,
    )

    plant_exists = st.session_state.plant is not None

    if not plant_exists:
        st.markdown("""
        <div class='pv-insight-card' style='border-style: dashed; opacity: 0.6;'>
            <div class='pv-insight-label'>On Kosul</div>
            <div class='pv-insight-value' style='text-transform: none; letter-spacing: -0.01em; font-size: 14px; font-weight: 500;'>
                Once yukaridaki formdan santralinizi kaydedin.
            </div>
            <div class='pv-insight-meta'>
                SCADA kalibrasyonu icin santral bilgileri gereklidir.
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        with st.expander("CSV format ve gereksinimler"):
            st.markdown("""
            **Beklenen sutunlar:**
            - `timestamp` — UTC zaman damgasi (saatlik)
            - `power_kw` — Gercek uretim gucu (kW)
            - `poa_global` — POA isinim olcumu (W/m2) — opsiyonel
            - `t_air` — Hava sicakligi (C) — opsiyonel

            **Veri sureleri:**
            - Minimum: 3 ay (90 gun)
            - Onerilen: 12 ay (mevsimsellik icin)

            **Format:** UTF-8 CSV, ilk satir basliklar
            """)

        col_upload, col_sample = st.columns([3, 1])
        with col_upload:
            uploaded_file = st.file_uploader(
                "SCADA verisi (CSV)",
                type=["csv"],
                label_visibility="collapsed",
                key="scada_uploader",
            )
        with col_sample:
            sample_clicked = st.button(
                "MERKAS Ornek Veri",
                use_container_width=True,
                key="scada_sample_btn",
            )

        # --- CSV okuma mantigi ---
        scada_df_local = None
        scada_source_name = None

        if sample_clicked:
            try:
                merkas_path = ROOT / "data" / "MERKAS_SCADA_FULL.csv"
                scada_df_local = load_csv(merkas_path).to_dataframe()
                scada_source_name = "MERKAS_SCADA_FULL.csv (ornek)"
            except Exception as e:
                st.error(f"MERKAS ornek dosyasi yuklenemedi: {e}")
        elif uploaded_file is not None:
            try:
                # Streamlit UploadedFile'i gecici dosyaya yaz (load_csv Path bekliyor)
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name
                scada_df_local = load_csv(tmp_path).to_dataframe()
                scada_source_name = uploaded_file.name
            except Exception as e:
                st.error(f"CSV okunamadi: {e}")

        # Yeni dosya yuklendiyse session state'i guncelle
        if scada_df_local is not None:
            # Kolon dogrulama
            required_cols = {"timestamp", "power_kw"}
            missing = required_cols - set(scada_df_local.columns)
            if missing:
                st.error(f"Eksik kolon(lar): {', '.join(missing)}. CSV'de timestamp ve power_kw zorunlu.")
            elif len(scada_df_local) < 100:
                st.error(f"Yetersiz veri: {len(scada_df_local)} satir. Minimum 100 saat gereklidir.")
            else:
                st.session_state.scada_df = scada_df_local
                st.session_state.scada_filename = scada_source_name
                # Yeni dosya yuklenince eski kalibrasyon sonucunu temizle
                st.session_state.calibration_result = None
                st.session_state.backtest_result = None
                st.session_state.calibrated = False

        # --- Yuklenen dosya ozeti ---
        scada_df = st.session_state.scada_df
        if scada_df is not None:
            n_rows = len(scada_df)
            start_dt = scada_df["timestamp"].min()
            end_dt = scada_df["timestamp"].max()
            days = (end_dt - start_dt).days
            has_poa = "poa_global" in scada_df.columns
            has_temp = "t_air" in scada_df.columns

            optional_cols = []
            if has_poa: optional_cols.append("POA")
            if has_temp: optional_cols.append("Sicaklik")
            optional_str = " · ".join(optional_cols) if optional_cols else "Yok"

            st.markdown(f"""
            <div class='pv-insight-row' style='grid-template-columns: repeat(3, 1fr);'>
                <div class='pv-insight-card'>
                    <div class='pv-insight-label'>Dosya</div>
                    <div class='pv-insight-value' style='text-transform: none; letter-spacing: -0.01em; font-size: 13px; font-weight: 600;'>{st.session_state.scada_filename}</div>
                    <div class='pv-insight-meta'>{n_rows:,} satir</div>
                </div>
                <div class='pv-insight-card'>
                    <div class='pv-insight-label'>Tarih Araligi</div>
                    <div class='pv-insight-value' style='text-transform: none; letter-spacing: -0.01em; font-size: 13px; font-weight: 600;'>{start_dt.strftime('%d %b %Y')} -> {end_dt.strftime('%d %b %Y')}</div>
                    <div class='pv-insight-meta'>{days} gun ({days/30:.1f} ay)</div>
                </div>
                <div class='pv-insight-card'>
                    <div class='pv-insight-label'>Opsiyonel Kolonlar</div>
                    <div class='pv-insight-value' style='text-transform: none; letter-spacing: -0.01em; font-size: 13px; font-weight: 600;'>{optional_str}</div>
                    <div class='pv-insight-meta'>poa_global, t_air</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # --- Kalibrasyonu Baslat butonu ---
        st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
        calibrate_disabled = scada_df is None
        calibrate_clicked = st.button(
            "Kalibrasyonu Baslat",
            type="primary",
            use_container_width=False,
            disabled=calibrate_disabled,
            key="calibrate_btn",
            help="Once SCADA dosyasi yukleyin veya ornek veriyi secin" if calibrate_disabled else "Kalibrasyon birkac dakika surebilir",
        )

    # --- KALIBRASYON CALISTIRMA ---
        if calibrate_clicked:
            try:
                with st.status("Kalibrasyon calistiriliyor...", expanded=True) as status:
                    st.write("Adim 1/3 — SCADA verisi hazirlaniyor...")
                    historical = HistoricalData(
                        plant_id=st.session_state.plant.plant_id,
                        data=st.session_state.scada_df,
                    )

                    st.write("Adim 2/3 — Open-Meteo arsiv verisi cekiliyor ve POA bias ogreniliyor...")
                    model = BarhdadiBennisModel(st.session_state.plant)

                    st.write("Adim 3/3 — BG ve eta_BoS fit ediliyor (1-3 dakika)...")
                    cal_result = model.calibrate(historical)

                    # Sonuclari session state'e kaydet
                    st.session_state.calibration_result = cal_result
                    st.session_state.calibrated_model = model
                    st.session_state.calibrated = True

                    status.update(label="Kalibrasyon tamamlandi", state="complete", expanded=False)

                # Yeni tahmin yapilmasi gerektigi icin eski forecast'i temizle
                st.session_state.forecast_result = None
                # --- BACKTEST: kalibre model ile gecmis donemi yeniden tahmin et ---
                with st.status("Backtest hesaplaniyor...", expanded=True) as bt_status:
                    st.write("Adim 1/3 — Tarihsel meteoroloji verisi cekiliyor...")
                    scada_df = st.session_state.scada_df
                    start_date = scada_df["timestamp"].min().strftime("%Y-%m-%d")
                    end_date = scada_df["timestamp"].max().strftime("%Y-%m-%d")

                    client = OpenMeteoClient()
                    historical_meteo = client.get_historical(
                        latitude=st.session_state.plant.location.latitude,
                        longitude=st.session_state.plant.location.longitude,
                        start_date=start_date,
                        end_date=end_date,
                        timezone=st.session_state.plant.location.timezone,
                    )

                    st.write("Adim 2/3 — Kalibre model ile gecmis donem tahmin ediliyor...")
                    backtest_forecast_df = pd.DataFrame({
                        "timestamp": historical_meteo.ghi.index,
                        "ghi": historical_meteo.ghi.values,
                        "t_air": historical_meteo.temp_air.values,
                        "wind_speed": historical_meteo.wind_speed_10m.values,
                    })
                    backtest_input = ForecastInput(
                        source="open_meteo",
                        resolution_minutes=60,
                        data=backtest_forecast_df,
                    )
                    backtest_config = OperationConfig(operation_mode="calibrated")
                    backtest_result = model.predict(backtest_input, backtest_config)

                    st.write("Adim 3/3 — SCADA gercek ile karsilastiriliyor...")
                    # Hizalama
                    pred_ts = backtest_result.timeseries.set_index("timestamp_utc")
                    if pred_ts.index.tz is None:
                        pred_ts.index = pd.to_datetime(pred_ts.index).tz_localize("UTC")

                    scada_ts = scada_df.set_index("timestamp")
                    if scada_ts.index.tz is None:
                        scada_ts.index = scada_ts.index.tz_localize(
                            st.session_state.plant.location.timezone,
                            ambiguous="infer",
                            nonexistent="shift_forward",
                        ).tz_convert("UTC")

                    comp = pd.DataFrame({
                        "scada_kw": scada_ts["power_kw"],
                        "pred_kw": pred_ts["ac_power_kw"],
                    }).dropna()

                    # Metrikler
                    scada_total_kwh = float(comp["scada_kw"].sum())
                    pred_total_kwh = float(comp["pred_kw"].sum())
                    dev_pct = 100.0 * (pred_total_kwh - scada_total_kwh) / scada_total_kwh

                    errors = comp["pred_kw"] - comp["scada_kw"]
                    rmse_kw = float(np.sqrt((errors ** 2).mean()))
                    mae_kw = float(errors.abs().mean())

                    # Gunduz MAPE (50 kW esik, gece saatlerini ele)
                    day_mask = comp["scada_kw"] > 50
                    if day_mask.sum() > 0:
                        mape_day_pct = float(
                            100 * (errors[day_mask].abs() / comp.loc[day_mask, "scada_kw"]).mean()
                        )
                    else:
                        mape_day_pct = float("nan")

                    scada_peak_kw = float(comp["scada_kw"].max())
                    pred_peak_kw = float(comp["pred_kw"].max())
                    peak_dev_pct = 100.0 * (pred_peak_kw - scada_peak_kw) / scada_peak_kw

                    n_hours_compared = int(len(comp))
                    n_days = (comp.index.max() - comp.index.min()).days

                    st.session_state.backtest_result = {
                        "scada_total_mwh": scada_total_kwh / 1000,
                        "pred_total_mwh": pred_total_kwh / 1000,
                        "dev_pct": dev_pct,
                        "rmse_kw": rmse_kw,
                        "mae_kw": mae_kw,
                        "mape_day_pct": mape_day_pct,
                        "scada_peak_kw": scada_peak_kw,
                        "pred_peak_kw": pred_peak_kw,
                        "peak_dev_pct": peak_dev_pct,
                        "n_hours_compared": n_hours_compared,
                        "n_days": n_days,
                        "comp_df": comp,  # Adim 2D'de grafik icin
                    }
                    bt_status.update(label="Backtest tamamlandi", state="complete", expanded=False)

                # Diske kalibrasyon sonucunu kaydet (mevcut profil uzerine guncellenir)
                try:
                    calibration_payload = {
                        "params": {
                            "bifacial_gain_geometric": float(cal_result.parameters["bifacial_gain_geometric"]),
                            "eta_bos": float(cal_result.parameters["eta_bos"]),
                        },
                        "metrics": {
                            "yillik_sapma_pct": float(st.session_state.backtest_result["dev_pct"]),
                            "pik_sapma_pct": float(st.session_state.backtest_result["peak_dev_pct"]),
                            "rmse_kw": float(st.session_state.backtest_result["rmse_kw"]),
                            "mae_kw": float(st.session_state.backtest_result["mae_kw"]),
                            "mape_day_pct": float(st.session_state.backtest_result["mape_day_pct"]),
                            "scada_total_mwh": float(st.session_state.backtest_result["scada_total_mwh"]),
                            "pred_total_mwh": float(st.session_state.backtest_result["pred_total_mwh"]),
                            "n_hours_compared": int(st.session_state.backtest_result["n_hours_compared"]),
                            "n_days": int(st.session_state.backtest_result["n_days"]),
                        },
                        "calibrated_at": pd.Timestamp.now().isoformat(timespec="seconds"),
                    }
                    save_plant(
                        st.session_state.plant.plant_id,
                        st.session_state.plant,
                        calibration=calibration_payload,
                    )
                except Exception as save_err:
                    st.warning(f"Kalibrasyon diske yazilamadi (session'da duruyor): {save_err}")
                

                # Ozet basari mesaji (gecici - Adim 2C/2D'de detayli sonuc gelecek)
                bg = cal_result.parameters["bifacial_gain_geometric"]
                eta = cal_result.parameters["eta_bos"]
                dev_after = cal_result.quality_metrics["total_deviation_pct_after"]
                mape_after = cal_result.quality_metrics["mape_pct_after"]
                hours = cal_result.valid_hours_used
              
              # Sonuc gosterimi — Adim 2D'de tasinacak ayri bloka
                # Su an success mesaji yerine st.session_state'e koy, asagida render edilecek
                st.session_state.show_calibration_result = True

            except ValueError as e:
                st.error(f"Kalibrasyon basarisiz: {e}")
            except ConnectionError as e:
                st.error(f"Open-Meteo'ya baglanilamadi: {e}. Internet baglantinizi kontrol edin.")
            except Exception as e:
                st.error(f"Beklenmeyen hata: {type(e).__name__}: {e}")
                # === KALIBRASYON SONUC EKRANI ===
        # Hem buton tiklamasinda hem rerun'da gosterilir (session_state'den okunur)
        if st.session_state.get("backtest_result") is not None:
            bt = st.session_state.backtest_result
            cal = st.session_state.calibration_result

            st.markdown("<h2 style='margin-top: 3rem;'>Kalibrasyon Sonuclari</h2>", unsafe_allow_html=True)
            st.markdown(
                f"<div class='pv-subtitle' style='margin-top: -0.5rem; margin-bottom: 1.5rem;'>"
                f"Gecmis {bt['n_days']} gunluk donemde modelimizin sizin santralinizdeki performansi."
                f"</div>",
                unsafe_allow_html=True,
            )

            # --- 3 HERO METRIK ---
            dev = bt["dev_pct"]
            dev_color = "var(--success)" if abs(dev) <= 1.0 else ("var(--accent)" if abs(dev) <= 5.0 else "var(--danger)")
            dev_quality = "Mukemmel" if abs(dev) <= 1.0 else ("Iyi" if abs(dev) <= 5.0 else "Iyilestirme gerekli")

            st.markdown(f"""
            <div class='pv-insight-row' style='grid-template-columns: repeat(3, 1fr); gap: 16px;'>
                <div class='pv-insight-card' style='border-left: 3px solid {dev_color}; padding: 1.25rem 1.5rem;'>
                    <div class='pv-insight-label'>Yillik Sapma</div>
                    <div class='pv-insight-value' style='font-size: 28px; font-weight: 800; color: {dev_color}; text-transform: none; letter-spacing: -0.02em; margin-top: 0.5rem;'>
                        {dev:+.2f}%
                    </div>
                    <div class='pv-insight-meta' style='margin-top: 0.5rem;'>{dev_quality} · Hedef ±1%</div>
                </div>
                <div class='pv-insight-card' style='padding: 1.25rem 1.5rem;'>
                    <div class='pv-insight-label'>Gercek Uretim</div>
                    <div class='pv-insight-value' style='font-size: 28px; font-weight: 800; text-transform: none; letter-spacing: -0.02em; margin-top: 0.5rem;'>
                        {bt['scada_total_mwh']:.1f} <span style='font-size: 16px; font-weight: 600; color: var(--text-3);'>MWh</span>
                    </div>
                    <div class='pv-insight-meta' style='margin-top: 0.5rem;'>SCADA olculen toplam</div>
                </div>
                <div class='pv-insight-card' style='padding: 1.25rem 1.5rem;'>
                    <div class='pv-insight-label'>Modelimizin Tahmini</div>
                    <div class='pv-insight-value' style='font-size: 28px; font-weight: 800; text-transform: none; letter-spacing: -0.02em; margin-top: 0.5rem;'>
                        {bt['pred_total_mwh']:.1f} <span style='font-size: 16px; font-weight: 600; color: var(--text-3);'>MWh</span>
                    </div>
                    <div class='pv-insight-meta' style='margin-top: 0.5rem;'>Kalibre edilmis model</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # --- PIK KARSILAŞTIRMA ---
            peak_dev = bt["peak_dev_pct"]
            peak_color = "var(--success)" if abs(peak_dev) <= 5.0 else "var(--accent)"
            st.markdown(f"""
            <div class='pv-insight-row' style='grid-template-columns: 1fr; gap: 16px; margin-top: 1rem;'>
                <div class='pv-insight-card' style='padding: 1.25rem 1.5rem;'>
                    <div class='pv-insight-label'>Pik Guc Karsilastirmasi</div>
                    <div style='display: flex; gap: 2rem; align-items: baseline; margin-top: 0.5rem; flex-wrap: wrap;'>
                        <div>
                            <span style='font-size: 11px; font-weight: 600; color: var(--text-3); text-transform: uppercase; letter-spacing: 0.06em;'>Gercek</span>
                            <span style='font-size: 20px; font-weight: 700; color: var(--text); margin-left: 0.5rem; letter-spacing: -0.01em;'>{bt['scada_peak_kw']:,.0f} kW</span>
                        </div>
                        <div>
                            <span style='font-size: 11px; font-weight: 600; color: var(--text-3); text-transform: uppercase; letter-spacing: 0.06em;'>Tahmin</span>
                            <span style='font-size: 20px; font-weight: 700; color: var(--text); margin-left: 0.5rem; letter-spacing: -0.01em;'>{bt['pred_peak_kw']:,.0f} kW</span>
                        </div>
                        <div>
                            <span style='font-size: 11px; font-weight: 600; color: var(--text-3); text-transform: uppercase; letter-spacing: 0.06em;'>Fark</span>
                            <span style='font-size: 20px; font-weight: 700; color: {peak_color}; margin-left: 0.5rem; letter-spacing: -0.01em;'>{peak_dev:+.2f}%</span>
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # --- ZAMAN SERISI GRAFIGI ---
            st.markdown("<h2 style='margin-top: 2.5rem;'>Gercek vs Tahmin — 12 Ay</h2>", unsafe_allow_html=True)
            st.markdown(
                "<div class='pv-subtitle' style='margin-top: -0.5rem; margin-bottom: 1rem;'>"
                "Haftalik ortalama uretim gucu (kW). SCADA ile tahminin uyumunu gosterir."
                "</div>",
                unsafe_allow_html=True,
            )

            comp_df = bt["comp_df"].copy()
            weekly = comp_df.resample("W").mean()

            fig_bt = go.Figure()
            fig_bt.add_trace(go.Scatter(
                x=weekly.index, y=weekly["scada_kw"],
                mode="lines", name="SCADA (Gercek)",
                line=dict(color="#10B981", width=2.5),
                hovertemplate="<b>%{x|%d %b %Y}</b><br>Gercek: %{y:,.0f} kW<extra></extra>",
            ))
            fig_bt.add_trace(go.Scatter(
                x=weekly.index, y=weekly["pred_kw"],
                mode="lines", name="Tahmin",
                line=dict(color="#F59E0B", width=2.5, dash="dot"),
                hovertemplate="<b>%{x|%d %b %Y}</b><br>Tahmin: %{y:,.0f} kW<extra></extra>",
            ))
            fig_bt.update_layout(
                height=380,
                xaxis_title=None, yaxis_title=None,
                margin=dict(l=0, r=0, t=12, b=0),
                hovermode="x unified",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#8B92A7", family="Inter", size=11),
                xaxis=dict(gridcolor="rgba(35,41,56,0.5)", showline=False, zeroline=False, tickfont=dict(color="#555E72", size=10)),
                yaxis=dict(gridcolor="rgba(35,41,56,0.5)", showline=False, zeroline=False, tickfont=dict(color="#555E72", size=10), ticksuffix=" kW"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                           bgcolor="rgba(0,0,0,0)", font=dict(size=11, color="#8B92A7")),
            )
            st.plotly_chart(
                fig_bt,
                use_container_width=True,
                config={
                    "displayModeBar": False,
                    "responsive": True,
                    "toImageButtonOptions": {"format": "png", "scale": 3},
                },
            )

            # --- GELISMIS DETAYLAR EXPANDER ---
            with st.expander("Gelismis detaylar — Ogrenilen katsayilar ve hata metrikleri"):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("**Ogrenilen Katsayilar**")
                    is_bifacial = st.session_state.plant.panel.technology == "bifacial"
                    if is_bifacial:
                        bg_value = cal.parameters['bifacial_gain_geometric']
                        st.markdown(f"- **Bifacial Gain (BG):** `{bg_value:.4f}`")
                        if bg_value <= 0.06:
                            st.warning("Bifacial gain dusuk. Sistemde gercek bifacial uretim aliyor musunuz?")
                    st.markdown(f"- **η_BoS (BoS verimi):** `{cal.parameters['eta_bos']:.4f}`")
                    st.markdown(f"- **Albedo:** `{cal.parameters['albedo']:.2f}`")
                    st.markdown(f"- **Gamma (sicaklik katsayisi):** `{cal.parameters['gamma_pdc']:.4f}`")
                with col_b:
                    st.markdown("**Hata Metrikleri**")
                    st.markdown(f"- **RMSE:** `{bt['rmse_kw']:,.1f} kW`")
                    st.markdown(f"- **MAE:** `{bt['mae_kw']:,.1f} kW`")
                    st.markdown(f"- **MAPE (gunduz):** `{bt['mape_day_pct']:.2f}%`")
                    st.markdown(f"- **Karsilastirilan saat:** `{bt['n_hours_compared']:,}`")
                st.markdown(
                    "<div style='margin-top: 1rem; padding: 0.75rem; background: var(--surface-2); border-radius: 6px; font-size: 12px; color: var(--text-3);'>"
                    "MAPE saatlik bazda olculur ve gece saatlerinde (gercek uretim &lt; 50 kW) anlamsizdir; "
                    "bu yuzden sadece gunduz saatleri raporlanir. Yillik toplam sapma asil performans metrigidir."
                    "</div>",
                    unsafe_allow_html=True,
                )
# === SAYFA: TAHMIN ===
elif "Tahmin" in page:
    plant = st.session_state.plant
    if not plant:
        st.warning("Once Santral Kayit sayfasindan santral olusturun.")
        st.stop()

    col_title, col_action = st.columns([3, 1])
    with col_title:
        st.markdown("<h1 style='margin:0;'>7 Gunluk Uretim Tahmini</h1>", unsafe_allow_html=True)
        tech_tr = {"mono": "Monokristal", "bifacial": "Bifacial", "thin_film": "Ince Film"}
        st.markdown(f"<div class='pv-subtitle'>{plant.name} - {plant.dc_capacity_kwp:,.0f} kWp - {tech_tr.get(plant.panel.technology, plant.panel.technology)} - {plant.location.latitude:.2f}N {plant.location.longitude:.2f}E</div>", unsafe_allow_html=True)
    with col_action:
        run_forecast = st.button("Tahmini Yenile", type="primary", use_container_width=True)

    # --- MOD BANNER ---
    is_calibrated = st.session_state.get("calibrated", False)
    if is_calibrated:
        bt = st.session_state.get("backtest_result")
        if bt is not None:
            dev_str = f"{bt['dev_pct']:+.2f}%"
            st.markdown(f"""
            <div class='pv-insight-card' style='border-left: 3px solid var(--success); padding: 1rem 1.25rem; margin-bottom: 1.5rem;'>
                <div style='display: flex; align-items: center; gap: 0.75rem;'>
                    <span style='color: var(--success); font-size: 16px;'>●</span>
                    <span style='font-size: 13px; font-weight: 600; color: var(--text); text-transform: uppercase; letter-spacing: 0.04em;'>Calibrated Mod Aktif</span>
                </div>
                <div style='font-size: 12px; color: var(--text-3); margin-top: 0.4rem; margin-left: 1.6rem;'>
                    SCADA verinizle kalibre edilmis model kullanilacak. Gecmis backtest sapmasi: {dev_str}.
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class='pv-insight-card' style='border-left: 3px solid var(--neutral); padding: 1rem 1.25rem; margin-bottom: 1.5rem;'>
            <div style='display: flex; align-items: center; gap: 0.75rem;'>
                <span style='color: var(--neutral); font-size: 16px;'>●</span>
                <span style='font-size: 13px; font-weight: 600; color: var(--text); text-transform: uppercase; letter-spacing: 0.04em;'>Pure Forecast Modu</span>
            </div>
            <div style='font-size: 12px; color: var(--text-3); margin-top: 0.4rem; margin-left: 1.6rem;'>
                Sadece meteoroloji + santral profili kullanilacak (sapma %5-10). Daha hassas tahmin icin Santral Kayit sayfasinda SCADA verinizi yukleyin.
            </div>
        </div>
        """, unsafe_allow_html=True)

    if run_forecast:
        with st.spinner("Meteoroloji verisi cekiliyor..."):
            try:
                client = OpenMeteoClient()
                meteo = client.get_forecast(
                    latitude=plant.location.latitude,
                    longitude=plant.location.longitude,
                )
                forecast_df = pd.DataFrame({
                    "timestamp": meteo.ghi.index,
                    "ghi": meteo.ghi.values,
                    "t_air": meteo.temp_air.values,
                    "wind_speed": meteo.wind_speed_10m.values,
                })
                forecast_input = ForecastInput(source="open_meteo", resolution_minutes=60, data=forecast_df)

                # Mod B aktifse kalibre modeli kullan, yoksa yeni model yarat
                if is_calibrated and st.session_state.get("calibrated_model") is not None:
                    model = st.session_state.calibrated_model
                    config = OperationConfig(operation_mode="calibrated")
                else:
                    model = BarhdadiBennisModel(plant)
                    config = OperationConfig(operation_mode="pure_forecast")

                result = model.predict(forecast_input, config)
                st.session_state.forecast_result = result
                st.session_state.meteo = meteo
            except Exception as e:
                st.error(f"Tahmin basarisiz: {e}")
                st.stop()
    result = st.session_state.forecast_result
    if not result:
        st.info("Yukaridaki butona basarak 7 gunluk tahmini baslatın.")
        st.stop()

    ts = result.timeseries.copy()
    ts["timestamp"] = pd.to_datetime(ts["timestamp_utc"])
    ts["day"] = ts["timestamp"].dt.date

    total_mwh = ts["ac_power_kw"].sum() / 1000
    peak_kw = ts["ac_power_kw"].max()
    peak_time = ts.loc[ts["ac_power_kw"].idxmax(), "timestamp"]
    avg_daily = total_mwh / 7
    cf = (total_mwh * 1000) / (plant.dc_capacity_kwp * 168) * 100

    # === HAFTALIK OZET ===
    st.markdown("<h2>Haftalik Ozet</h2>", unsafe_allow_html=True)
    day_map = {"Mon": "Pzt", "Tue": "Sal", "Wed": "Car", "Thu": "Per", "Fri": "Cum", "Sat": "Cmt", "Sun": "Paz"}
    peak_str = peak_time.strftime("%a %H:%M")
    for en, tr in day_map.items():
        peak_str = peak_str.replace(en, tr)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Toplam Uretim", f"{total_mwh:.1f} MWh")
    with c2:
        # Delta'da pill yok artik, sade gri metin
        st.metric("Pik Guc", f"{peak_kw/1000:.2f} MW", peak_str)
    with c3:
        st.metric("Gunluk Ort.", f"{avg_daily:.1f} MWh")
    with c4:
        st.metric("Kapasite Faktoru", f"%{cf:.1f}")

    # === ICGORULER ===
    daily_totals = ts.groupby("day")["ac_power_kw"].sum() / 1000
    best_day = daily_totals.idxmax()
    worst_day = daily_totals.idxmin()
    avg_temp = st.session_state.meteo.temp_air.mean() if st.session_state.meteo is not None else 0
    avg_wind = st.session_state.meteo.wind_speed_10m.mean() if st.session_state.meteo is not None else 0
    avg_ghi = st.session_state.meteo.ghi.mean() if st.session_state.meteo is not None else 0

    day_tr = {0: "PZT", 1: "SAL", 2: "CAR", 3: "PER", 4: "CUM", 5: "CMT", 6: "PAZ"}
    month_tr = {1: "OCA", 2: "SUB", 3: "MAR", 4: "NIS", 5: "MAY", 6: "HAZ", 7: "TEM", 8: "AGU", 9: "EYL", 10: "EKI", 11: "KAS", 12: "ARA"}

    def fmt_day(d):
        return f"{day_tr[d.weekday()]} - {d.day:02d} {month_tr[d.month]}"

    st.markdown("<h2>Icgoruler</h2>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class='pv-insight-row'>
        <div class='pv-insight-card'>
            <div class='pv-insight-label'>En Uretken Gun</div>
            <div class='pv-insight-value'>{fmt_day(best_day)}</div>
            <div class='pv-insight-meta'>{daily_totals[best_day]:.1f} MWh</div>
        </div>
        <div class='pv-insight-card'>
            <div class='pv-insight-label'>En Dusuk Gun</div>
            <div class='pv-insight-value'>{fmt_day(worst_day)}</div>
            <div class='pv-insight-meta'>{daily_totals[worst_day]:.1f} MWh</div>
        </div>
        <div class='pv-insight-card'>
            <div class='pv-insight-label'>Hava Durumu Ortalamasi</div>
            <div class='pv-insight-value'>{avg_temp:.1f} C</div>
            <div class='pv-insight-meta'>{avg_ghi:.0f} W/m2 GHI · {avg_wind:.1f} m/s ruzgar</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # === URETIM EGRISI + GORUNUM SECICI ===
    st.markdown("<h2>Uretim Egrisi</h2>", unsafe_allow_html=True)

    view_mode = st.radio(
        "Gorunum",
        ["Saatlik", "Gunluk", "Haftalik"],
        horizontal=True,
        label_visibility="collapsed",
        key="view_radio",
    )

    if view_mode == "Saatlik":
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=ts["timestamp"], y=ts["ac_power_kw"],
            fill="tozeroy", mode="lines",
            line=dict(color="#F59E0B", width=2),
            fillcolor="rgba(245, 158, 11, 0.12)",
            hovertemplate="<b>%{x|%d %b %H:%M}</b><br>%{y:.0f} kW<extra></extra>",
        ))
        y_label = "kW"
    elif view_mode == "Gunluk":
        daily_kwh = ts.groupby("day")["ac_power_kw"].sum().reset_index()
        daily_kwh.columns = ["day", "kwh"]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=daily_kwh["day"], y=daily_kwh["kwh"],
            marker=dict(color="#F59E0B", line=dict(width=0)),
            hovertemplate="<b>%{x|%d %b}</b><br>%{y:,.0f} kWh<extra></extra>",
        ))
        y_label = "kWh"
    else:
        weekly_total = ts["ac_power_kw"].sum()
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=["Bu Hafta"], y=[weekly_total],
            marker=dict(color="#F59E0B"),
            text=[f"{weekly_total/1000:.1f} MWh"],
            textposition="outside",
            textfont=dict(color="#E6E9EF", size=14),
            hovertemplate="<b>Haftalik Toplam</b><br>%{y:,.0f} kWh<extra></extra>",
        ))
        y_label = "kWh"

    # GRAFIK: y-axis daha soluk, x-axis daha soluk
    fig.update_layout(
        height=360,
        xaxis_title=None, yaxis_title=None,
        margin=dict(l=0, r=0, t=12, b=0),
        hovermode="x unified",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#555E72", family="Inter", size=10),
        xaxis=dict(gridcolor="rgba(35,41,56,0.5)", showline=False, zeroline=False, tickfont=dict(color="#555E72", size=10)),
        yaxis=dict(gridcolor="rgba(35,41,56,0.5)", showline=False, zeroline=False, tickfont=dict(color="#555E72", size=10), ticksuffix=f" {y_label}"),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # === METEOROLOJI ===
    if st.session_state.meteo is not None:
        st.markdown("<h2>Meteoroloji</h2>", unsafe_allow_html=True)
        meteo = st.session_state.meteo
        weather_df = pd.DataFrame({
            "timestamp": meteo.ghi.index,
            "ghi": meteo.ghi.values,
            "t_air": meteo.temp_air.values,
            "wind_speed": meteo.wind_speed_10m.values,
        })

        fig_w = make_subplots(
            rows=1, cols=2,
            subplot_titles=("ISINIM VE SICAKLIK", "RUZGAR HIZI"),
            specs=[[{"secondary_y": True}, {"secondary_y": False}]],
            horizontal_spacing=0.1,
        )
        fig_w.add_trace(
            go.Scatter(x=weather_df["timestamp"], y=weather_df["ghi"],
                      name="GHI", line=dict(color="#F59E0B", width=1.5),
                      hovertemplate="GHI: %{y:.0f} W/m2<extra></extra>"),
            row=1, col=1, secondary_y=False,
        )
        fig_w.add_trace(
            go.Scatter(x=weather_df["timestamp"], y=weather_df["t_air"],
                      name="Sicaklik", line=dict(color="#3B82F6", width=1.5),
                      hovertemplate="T: %{y:.1f} C<extra></extra>"),
            row=1, col=1, secondary_y=True,
        )
        fig_w.add_trace(
            go.Scatter(x=weather_df["timestamp"], y=weather_df["wind_speed"],
                      name="Ruzgar", line=dict(color="#10B981", width=1.5),
                      hovertemplate="Ruzgar: %{y:.1f} m/s<extra></extra>"),
            row=1, col=2,
        )
        # Meteoroloji grafikleri: kucuk caps baslik
        fig_w.update_layout(
            height=260,
            margin=dict(l=0, r=0, t=40, b=0),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#555E72", family="Inter", size=10),
            showlegend=False,
            hovermode="x unified",
        )
        fig_w.update_xaxes(gridcolor="rgba(35,41,56,0.5)", showline=False, zeroline=False, tickfont=dict(color="#555E72", size=9))
        fig_w.update_yaxes(gridcolor="rgba(35,41,56,0.5)", showline=False, zeroline=False, tickfont=dict(color="#555E72", size=9))
        fig_w.update_yaxes(ticksuffix=" W/m2", row=1, col=1, secondary_y=False)
        fig_w.update_yaxes(ticksuffix=" C", row=1, col=1, secondary_y=True)
        fig_w.update_yaxes(ticksuffix=" m/s", row=1, col=2)
        # Subplot baslik styling
        for ann in fig_w["layout"]["annotations"]:
            ann["font"] = dict(color="#8B92A7", size=10, family="Inter")
            ann["text"] = f"<b>{ann['text']}</b>"
        st.plotly_chart(fig_w, use_container_width=True, config={"displayModeBar": False})

    # === GUNLUK TABLO ===
    st.markdown("<h2>Gunluk Dagilim</h2>", unsafe_allow_html=True)
    daily = ts.groupby("day").agg(
        toplam=("ac_power_kw", "sum"),
        pik=("ac_power_kw", "max"),
    ).reset_index()
    daily.columns = ["TARIH", "TOPLAM (KWH)", "PIK GUC (KW)"]
    daily["TOPLAM (KWH)"] = daily["TOPLAM (KWH)"].round(1)
    daily["PIK GUC (KW)"] = daily["PIK GUC (KW)"].round(1)
    st.dataframe(daily, use_container_width=True, hide_index=True)

