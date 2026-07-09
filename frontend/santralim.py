"""
PVQuant Santralim Ekrani (Faz 2 Adim 2)

Prototipteki 'kalp oge' - kullanicinin ilk gordugu ekran.
Adim 2'de statik veri; Adim 4-5'te backend'e baglanacak.
"""

import streamlit as st
import plotly.graph_objects as go

from components import page_header, brand_band, pill, kpi_card
from design_tokens import (
    CHART_ACTUAL, CHART_FORECAST, CHART_GRID,
    PRIMARY, TEXT_TERTIARY, TEXT_SECONDARY,
)
from santralim_data import (
    SANTRAL, KALIBRASYON, BUGUN, HAVA,
    SAATLIK_GERCEK, SAATLIK_TAHMIN, SIMDI_SAAT,
    GUNLUK_TAHMIN, VERI_SAGLIGI,
)


def _weather_column_html(gun: str, sicaklik: int, ghi: float, aktif: bool = False) -> str:
    """Tek bir hava sutunu HTML'i."""
    aktif_class = " pvq-weather-col--active" if aktif else ""
    return (
        f'<div class="pvq-weather-col{aktif_class}">'
        f'  <div class="pvq-weather-day">{gun}</div>'
        f'  <div class="pvq-weather-temp">{sicaklik}°</div>'
        f'  <div class="pvq-weather-ghi">{ghi:.1f} kWh/m²</div>'
        f'</div>'
    )


def render_santralim() -> None:
    """Santralim ekraninin tam render'i."""
    page_header(
        "Santralim",
        "Santralinizin bugununu ve onumuzdeki 7 gunu tek bakista gorun",
    )

    # ============================================================
    # BLOK 1: Marka bandi
    # ============================================================
    meta_line = (
        f"{SANTRAL['kapasite_mw']} MW &middot; {SANTRAL['konum']} "
        f"&middot; Devreye alma {SANTRAL['devreye_alma']}"
    )

    kalibre_pill = pill(
        f"Kalibre — sapma %{KALIBRASYON['sapma_pct']:.2f}",
        variant="success",
        dot=True,
    )
    tahmin_pill = pill("Bugunun tahmini hazir →", variant="primary")
    pills_html = kalibre_pill + tahmin_pill

    weather_cols = []
    for i, h in enumerate(HAVA):
        weather_cols.append(_weather_column_html(
            gun=h["gun"],
            sicaklik=h["sicaklik"],
            ghi=h["ghi_kwh_m2"],
            aktif=(i == 0),
        ))
    weather_html = "".join(weather_cols)

    footer_note = (
        f"Yarin {BUGUN['yarin_hava']} — beklenen uretim bugunden "
        f"<strong>%{BUGUN['yarin_dusus_pct']}</strong>, cuma "
        f"<strong>%{BUGUN['cuma_dusus_pct']}</strong> dusuk."
    )

    brand_band(
        name=SANTRAL["adi"],
        meta_line=meta_line,
        pills_html=pills_html,
        weather_html=weather_html,
        footer_note=footer_note,
    )

    # ============================================================
    # BLOK 2: 4 KPI karti
    # ============================================================
    kpi_cols = st.columns(4, gap="medium")
    with kpi_cols[0]:
        bugunku_str = f"{BUGUN['tahmini_uretim_kwh']:,}".replace(",", ".")
        kpi_card(
            label="BUGUNKU TAHMINI URETIM",
            value=bugunku_str,
            unit="kWh",
            subtitle="gun sonuna kadar",
            info_tooltip=True,
        )
    with kpi_cols[1]:
        yarin_str = f"{BUGUN['yarin_beklenen_kwh']:,}".replace(",", ".")
        kpi_card(
            label="YARIN BEKLENEN",
            value=yarin_str,
            unit="kWh",
            subtitle=BUGUN["yarin_hava"],
            value_color="primary",
            info_tooltip=True,
        )
    with kpi_cols[2]:
        hafta_str = f"{BUGUN['bu_hafta_toplam_mwh']:.1f}".replace(".", ",")
        kpi_card(
            label="BU HAFTAKI TOPLAM",
            value=hafta_str,
            unit="MWh",
            subtitle="7 gunluk tahmin",
            info_tooltip=True,
        )
    with kpi_cols[3]:
        sapma_str = f"{KALIBRASYON['sapma_pct']:.2f}"
        son_kal = KALIBRASYON["son_kalibrasyon"]
        st.markdown(
            f'<div class="pvq-card pvq-kpi">'
            f'  <div class="pvq-microlabel">MODEL DURUMU</div>'
            f'  <div class="pvq-kpi-value pvq-kpi-value--success" style="font-size:24px">'
            f'    <span>🛡 Kalibre</span>'
            f'  </div>'
            f'  <div class="pvq-kpi-subtitle">'
            f'    sapma %{sapma_str} · son kalibrasyon {son_kal}'
            f'  </div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ============================================================
    # BLOK 3-4: Grafikler (yan yana)
    # ============================================================
    st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)
    chart_cols = st.columns([3, 2], gap="medium")

    # ---- BLOK 3: Bugun saatlik uretim (sol, genis) ----
    with chart_cols[0]:
        st.markdown(
            f'<div class="pvq-card" style="padding-bottom:8px">'
            f'  <div style="display:flex;justify-content:space-between;'
            f'              align-items:center;margin-bottom:12px">'
            f'    <div style="font-size:15px;font-weight:600">Bugun — saatlik uretim</div>'
            f'    <div style="display:flex;gap:16px;font-size:12px">'
            f'      <span style="display:inline-flex;align-items:center;gap:6px">'
            f'        <span style="width:12px;height:2px;background:{CHART_ACTUAL};'
            f'                     display:inline-block"></span>Gerceklesen'
            f'      </span>'
            f'      <span style="display:inline-flex;align-items:center;gap:6px">'
            f'        <span style="width:12px;height:0;border-top:2px dashed {CHART_FORECAST};'
            f'                     display:inline-block"></span>Kalan saatler'
            f'      </span>'
            f'    </div>'
            f'  </div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        gercek_x = [t for t, _ in SAATLIK_GERCEK]
        gercek_y = [v for _, v in SAATLIK_GERCEK]
        tahmin_x = [t for t, _ in SAATLIK_TAHMIN]
        tahmin_y = [v for _, v in SAATLIK_TAHMIN]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=gercek_x, y=gercek_y,
            mode="lines",
            line=dict(color=CHART_ACTUAL, width=2.5, shape="spline"),
            fill="tozeroy",
            fillcolor="rgba(232, 148, 10, 0.15)",
            hovertemplate="%{x}:00 · %{y} kW<extra></extra>",
            name="",
        ))
        fig.add_trace(go.Scatter(
            x=tahmin_x, y=tahmin_y,
            mode="lines",
            line=dict(color=CHART_FORECAST, width=2, dash="dash", shape="spline"),
            hovertemplate="%{x}:00 · %{y} kW<extra></extra>",
            name="",
        ))
        fig.add_vline(
            x=SIMDI_SAAT,
            line=dict(color=TEXT_SECONDARY, width=1, dash="dot"),
            annotation_text=f"simdi · {SIMDI_SAAT}:00",
            annotation_position="top",
            annotation_font=dict(size=11, color=TEXT_SECONDARY, family="IBM Plex Mono"),
        )
        fig.update_layout(
            height=280,
            margin=dict(l=0, r=0, t=20, b=0),
            plot_bgcolor="white",
            paper_bgcolor="white",
            showlegend=False,
            xaxis=dict(
                showgrid=False, zeroline=False,
                tickmode="array",
                tickvals=[0, 6, 12, 18, 23],
                ticktext=["00", "06", "12", "18", "23"],
                tickfont=dict(family="IBM Plex Mono", size=10, color=TEXT_TERTIARY),
            ),
            yaxis=dict(
                showgrid=True, gridcolor=CHART_GRID, zeroline=False,
                tickfont=dict(family="IBM Plex Mono", size=10, color=TEXT_TERTIARY),
            ),
            hoverlabel=dict(
                bgcolor="#0E1D30", bordercolor="#0E1D30",
                font=dict(color="white", family="IBM Plex Mono", size=12),
            ),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        st.markdown(
            '<div style="font-size:11px;color:#6B7684;'
            'font-family:IBM Plex Mono,monospace;margin-top:-8px;padding-bottom:12px">'
            'saatlik guc (kW) · MW olcegi solda'
            '</div>',
            unsafe_allow_html=True,
        )

    # ---- BLOK 4: 7 gunluk mini bar (sag, dar) ----
    with chart_cols[1]:
        st.markdown(
            f'<div class="pvq-card" style="padding-bottom:8px">'
            f'  <div style="display:flex;justify-content:space-between;'
            f'              align-items:center;margin-bottom:12px">'
            f'    <div style="font-size:15px;font-weight:600">7 gunluk gorunum</div>'
            f'    <a href="?p=tahminler" target="_self" '
            f'       style="color:{PRIMARY};font-size:13px;text-decoration:none;'
            f'              font-weight:500">Tahminler →</a>'
            f'  </div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        bar_x = [g["gun"] for g in GUNLUK_TAHMIN]
        bar_y = [g["mwh"] for g in GUNLUK_TAHMIN]
        bar_colors = [PRIMARY if g["bugun"] else "#93B4D1" for g in GUNLUK_TAHMIN]

        fig_bar = go.Figure(go.Bar(
            x=bar_x, y=bar_y,
            marker=dict(color=bar_colors),
            hovertemplate="%{x} · %{y:.2f} MWh<extra></extra>",
        ))
        fig_bar.update_layout(
            height=280,
            margin=dict(l=0, r=0, t=20, b=0),
            plot_bgcolor="white",
            paper_bgcolor="white",
            showlegend=False,
            xaxis=dict(
                showgrid=False, zeroline=False,
                tickfont=dict(family="IBM Plex Mono", size=11, color=TEXT_TERTIARY),
            ),
            yaxis=dict(
                showgrid=True, gridcolor=CHART_GRID, zeroline=False,
                tickfont=dict(family="IBM Plex Mono", size=10, color=TEXT_TERTIARY),
            ),
            hoverlabel=dict(
                bgcolor="#0E1D30", bordercolor="#0E1D30",
                font=dict(color="white", family="IBM Plex Mono", size=12),
            ),
        )
        st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})

        st.markdown(
            '<div style="font-size:11px;color:#6B7684;'
            'font-family:IBM Plex Mono,monospace;margin-top:-8px;padding-bottom:12px">'
            'gunluk beklenen enerji (MWh) — koyu: bugun'
            '</div>',
            unsafe_allow_html=True,
        )

    # ============================================================
    # BLOK 5: Veri sagligi
    # ============================================================
    islenen_str = f"{VERI_SAGLIGI['islenen_saat']:,}".replace(",", ".")
    scada_str = VERI_SAGLIGI["son_scada_yukleme"]
    anomali_str = str(VERI_SAGLIGI["temizlenen_anomali"])

    st.markdown(
        f"""
        <div class="pvq-card" style="margin-top:16px">
          <div style="display:flex;justify-content:space-between;
                      align-items:center;margin-bottom:12px">
            <div style="font-size:15px;font-weight:600">Veri sagligi</div>
            <a href="?p=veri_yukleme" target="_self"
               style="color:{PRIMARY};font-size:13px;text-decoration:none;
                      font-weight:500">Veri Yukleme →</a>
          </div>
          <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:24px">
            <div>
              <div style="font-size:13px;color:#3D4854;margin-bottom:4px">Son SCADA yuklemesi</div>
              <div style="font-family:IBM Plex Mono,monospace;font-size:18px;
                          font-weight:600;color:#0F1B28">{scada_str}</div>
            </div>
            <div>
              <div style="font-size:13px;color:#3D4854;margin-bottom:4px">Islenen veri</div>
              <div style="font-family:IBM Plex Mono,monospace;font-size:18px;
                          font-weight:600;color:#0F1B28">{islenen_str} saat</div>
            </div>
            <div>
              <div style="font-size:13px;color:#3D4854;margin-bottom:4px">Temizlenen anomali</div>
              <div style="font-family:IBM Plex Mono,monospace;font-size:18px;
                          font-weight:600;color:#0F1B28">{anomali_str}</div>
            </div>
          </div>
          <div style="margin-top:16px;font-size:13px;color:#3D4854">
            Daha guncel veri, daha isabetli kalibrasyon demektir.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )