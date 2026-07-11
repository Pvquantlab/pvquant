"""
PVQuant Tahminler Ekrani (Faz 2 Adim 5)

Prototipteki en zengin ekran.

Adim 5a: Iskelet + KPI seridi
Adim 5b: Once/Sonra + Bulduklarimiz + Veri Kaliteniz + Uyarilar
Adim 5c: Grafik + 7 gunluk tablo
Adim 5d: Export butonlari (sonra)
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from components import page_header
from design_tokens import (
    PRIMARY, SUCCESS, WARNING,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY,
    FONT_MONO,
    CHART_ACTUAL, CHART_FORECAST, CHART_GRID,
)


# ============================================================
# Uyari - kalibrasyon yoksa
# ============================================================

def _uyari_kalibrasyon_yok() -> None:
    st.markdown(
        f"""
        <div class="pvq-card" style="border-left:3px solid {WARNING};
             text-align:center;padding:48px 24px">
          <div style="font-size:48px;margin-bottom:16px">📊</div>
          <div style="font-size:20px;font-weight:600;color:#0F1B28;
                      margin-bottom:12px">
            Once kalibrasyon yapin
          </div>
          <div style="font-size:14px;color:{TEXT_SECONDARY};max-width:480px;
                      margin:0 auto 24px auto">
            Tahmin sonuclari icin oncelikle SCADA verinizi yukleyip
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
            key="git_kalibrasyon",
            use_container_width=True,
            type="primary",
        ):
            st.session_state.active_page = "kalibrasyon"
            st.rerun()


# ============================================================
# KPI seridi
# ============================================================

def _kpi_seridi() -> None:
    result = st.session_state.calibration_result
    v_after = result.validation_after
    duration_sec = st.session_state.get("calibration_duration_sec", 0.0)

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


# ============================================================
# 5b: Once/Sonra ibresi
# ============================================================

def _once_sonra_karti() -> None:
    result = st.session_state.calibration_result
    v_before = result.validation_before
    v_after = result.validation_after

    once_pct = v_before.total_deviation_pct
    sonra_pct = v_after.total_deviation_pct

    once_color = "#C9502E" if abs(once_pct) > 5 else SUCCESS
    sonra_color = SUCCESS if abs(sonra_pct) < 5 else "#C9502E"
    mono = "IBM Plex Mono, monospace"

    html = (
        f'<div class="pvq-card" style="margin-top:24px">'
        f'<div style="font-size:15px;font-weight:600;margin-bottom:24px">Once / Sonra</div>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;'
        f'gap:32px;align-items:center;text-align:center">'
        f'<div>'
        f'<div class="pvq-microlabel" style="margin-bottom:8px">KALIBRASYON ONCESI</div>'
        f'<div style="font-family:{mono};font-size:36px;font-weight:700;'
        f'color:{once_color};line-height:1">%{once_pct:+.0f}</div>'
        f'<div style="font-size:12px;color:{TEXT_SECONDARY};margin-top:8px">baslangic ayarlari</div>'
        f'</div>'
        f'<div style="padding:16px 0">'
        f'<div style="font-family:{mono};font-size:32px;font-weight:700;'
        f'color:{sonra_color};line-height:1">%{sonra_pct:+.2f}</div>'
        f'<div style="font-size:11px;color:{TEXT_TERTIARY};margin-top:8px;'
        f'text-transform:uppercase;letter-spacing:0.05em">olculen sapma</div>'
        f'</div>'
        f'<div>'
        f'<div class="pvq-microlabel" style="margin-bottom:8px">KALIBRASYON SONRASI</div>'
        f'<div style="font-family:{mono};font-size:36px;font-weight:700;'
        f'color:{sonra_color};line-height:1">%{sonra_pct:+.2f}</div>'
        f'<div style="font-size:12px;color:{TEXT_SECONDARY};margin-top:8px">santralinize kalibre</div>'
        f'</div>'
        f'</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# ============================================================
# 5b: Bulduklarimiz karti
# ============================================================

def _bulduklarimiz_karti() -> None:
    result = st.session_state.calibration_result
    original_plant = result.original_plant
    calibrated_plant = result.plant

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

    mono = "IBM Plex Mono, monospace"
    bulgular_html = ""
    for i, b in enumerate(bulgular):
        border = "" if i == len(bulgular) - 1 else "border-bottom:1px solid #E2E6EA;"
        if b["eski"] is None:
            deger_html = (
                f'<span style="font-family:{mono};'
                f'font-size:14px;font-weight:600;color:{TEXT_PRIMARY}">'
                f'{b["yeni"]}</span>'
            )
        else:
            deger_html = (
                f'<span style="font-family:{mono};font-size:14px">'
                f'<span style="color:{TEXT_TERTIARY};text-decoration:line-through">'
                f'{b["eski"]}</span>'
                f'<span style="color:{TEXT_SECONDARY};margin:0 8px">→</span>'
                f'<span style="font-weight:600;color:{TEXT_PRIMARY}">{b["yeni"]}</span>'
                f'</span>'
            )
        bulgular_html += (
            f'<div style="display:flex;justify-content:space-between;'
            f'align-items:center;padding:10px 0;{border}">'
            f'<div style="display:flex;align-items:center;gap:8px">'
            f'<span style="color:{PRIMARY};font-size:14px">🛡</span>'
            f'<span style="font-size:13px">{b["isim"]}</span>'
            f'</div>'
            f'{deger_html}'
            f'</div>'
        )

    st.markdown(
        f'<div class="pvq-card">'
        f'<div style="font-size:15px;font-weight:600;color:{TEXT_PRIMARY};'
        f'margin-bottom:4px">Bulduklarimiz</div>'
        f'<div style="font-size:12px;color:{TEXT_SECONDARY};margin-bottom:8px">'
        f'Model, santraliniz hakkinda size yeni bir sey ogretti.'
        f'</div>'
        f'{bulgular_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# 5b: Veri Kaliteniz karti
# ============================================================

def _veri_kaliteniz_karti() -> None:
    result = st.session_state.calibration_result
    n_valid = result.n_valid_hours

    outlier_report = result.outlier_report or {}
    n_outliers = outlier_report.get("n_outliers_removed", 0)
    longest_gap_hours = outlier_report.get("longest_gap_hours", 0)

    n_valid_str = f"{n_valid:,}".replace(",", ".")
    n_outliers_str = f"{n_outliers:,}".replace(",", ".")

    if longest_gap_hours >= 24:
        gap_str = f"{longest_gap_hours // 24} gun {longest_gap_hours % 24} sa"
    elif longest_gap_hours >= 1:
        gap_str = f"{longest_gap_hours} saat"
    else:
        gap_str = "yok"

    mono = "IBM Plex Mono, monospace"
    rows_html = ""
    for label, value in [
        ("Bulunan ve temizlenen anomali", n_outliers_str),
        ("En uzun kesinti", gap_str),
        ("Islenen veri", f"{n_valid_str} saat"),
    ]:
        rows_html += (
            f'<div style="display:flex;justify-content:space-between;'
            f'align-items:center;padding:10px 0;'
            f'border-bottom:1px solid #E2E6EA">'
            f'<span style="font-size:13px">{label}</span>'
            f'<span style="font-family:{mono};font-size:14px;'
            f'font-weight:600;color:{TEXT_PRIMARY}">{value}</span>'
            f'</div>'
        )

    st.markdown(
        f'<div class="pvq-card">'
        f'<div style="font-size:15px;font-weight:600;color:{TEXT_PRIMARY};'
        f'margin-bottom:4px">Veri Kaliteniz</div>'
        f'<div style="font-size:12px;color:{TEXT_SECONDARY};margin-bottom:8px">'
        f'Ariza ve sensor hatalari tespit edilip kalibrasyon disi birakildi.'
        f'</div>'
        f'{rows_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# 5b: Uyarilar karti
# ============================================================

def _uyarilar_karti() -> None:
    result = st.session_state.calibration_result
    if not result.warnings:
        return

    uyari_html = "<br>".join(f"• {w}" for w in result.warnings)
    st.markdown(
        f'<div class="pvq-card" style="margin-top:16px;'
        f'border-left:3px solid {WARNING};background:rgba(201,80,46,0.04)">'
        f'<div style="font-size:13px;font-weight:600;color:{TEXT_PRIMARY};'
        f'margin-bottom:8px">Dikkat edilmesi gerekenler</div>'
        f'<div style="font-size:12px;color:{TEXT_SECONDARY};line-height:1.7">'
        f'{uyari_html}'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# 5c: Forecast cagrisi
# ============================================================

@st.cache_data(show_spinner=False, ttl=1800)
def _fetch_forecast_meteo_cached(latitude: float, longitude: float) -> dict:
    from pvquant.io.meteo import OpenMeteoClient
    client = OpenMeteoClient()
    meteo = client.get_forecast(latitude=latitude, longitude=longitude, days=7)
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


def _dict_to_meteodata_forecast(d: dict):
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


def _forecast_bolumu() -> None:
    plant = st.session_state.plant_spec

    if "forecast_result" not in st.session_state:
        try:
            with st.spinner("7 gunluk hava tahmini cekiliyor..."):
                meteo_dict = _fetch_forecast_meteo_cached(
                    latitude=plant.latitude,
                    longitude=plant.longitude,
                )
            meteo = _dict_to_meteodata_forecast(meteo_dict)

            with st.spinner("Uretim tahmini hesaplaniyor..."):
                from pvquant.pipeline.forecast import forecast_7day
                result = forecast_7day(meteo=meteo, plant=plant)

            st.session_state.forecast_meteo = meteo
            st.session_state.forecast_result = result
        except Exception as e:
            st.error(f"Tahmin hesaplanamadi: {e}")
            return

    result = st.session_state.forecast_result

    _grafik_gercek_vs_tahmin(result)
    _tablo_7_gun(result)


def _grafik_gercek_vs_tahmin(result) -> None:
    import plotly.graph_objects as go

    hourly = result.hourly

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hourly.index,
        y=hourly["p_ac_kw"],
        mode="lines",
        line=dict(color=CHART_FORECAST, width=2, dash="dash"),
        name="Tahmin",
        hovertemplate="%{x|%d %b %H:%M}<br>%{y:.2f} kW<extra></extra>",
    ))

    fig.update_layout(
        height=320,
        margin=dict(l=0, r=0, t=8, b=0),
        plot_bgcolor="white",
        paper_bgcolor="white",
        showlegend=False,
        xaxis=dict(
            showgrid=False, zeroline=False,
            tickfont=dict(family="IBM Plex Mono", size=10, color="#6B7684"),
        ),
        yaxis=dict(
            showgrid=True, gridcolor=CHART_GRID, zeroline=False,
            tickfont=dict(family="IBM Plex Mono", size=10, color="#6B7684"),
            title=dict(text="kW", font=dict(size=10, color="#6B7684")),
        ),
        hoverlabel=dict(
            bgcolor="#0E1D30", bordercolor="#0E1D30",
            font=dict(color="white", family="IBM Plex Mono", size=12),
        ),
    )

    st.markdown(
        f'<div class="pvq-card" style="margin-top:24px;padding-bottom:8px">'
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:center;margin-bottom:12px">'
        f'<div style="font-size:15px;font-weight:600">Uretim tahmini - saatlik guc</div>'
        f'<div style="display:flex;gap:16px;font-size:12px">'
        f'<span style="display:inline-flex;align-items:center;gap:6px">'
        f'<span style="width:12px;height:0;border-top:2px dashed {CHART_FORECAST};'
        f'display:inline-block"></span>Model tahmini'
        f'</span>'
        f'</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _tablo_7_gun(result) -> None:
    import pandas as pd

    hourly = result.hourly
    daily_energy = result.daily_energy_kwh

    gunler_tr = ["Pazartesi", "Sali", "Carsamba", "Persembe", "Cuma", "Cumartesi", "Pazar"]
    mono = "IBM Plex Mono, monospace"

    rows = []
    daily_energy_list = list(daily_energy.items())

    for i, (date, energy_kwh) in enumerate(daily_energy_list):
        try:
            day_date = pd.Timestamp(date).date()
        except Exception:
            continue

        day_mask = [pd.Timestamp(t).date() == day_date for t in hourly.index]
        day_hourly = hourly.loc[day_mask]

        if len(day_hourly) == 0:
            continue

        peak_idx = day_hourly["p_ac_kw"].idxmax()
        peak_saat = f"{pd.Timestamp(peak_idx).hour:02d}:00"
        peak_guc = day_hourly.loc[peak_idx, "p_ac_kw"]

        if i == 0:
            fark_str = "—"
            fark_renk = TEXT_TERTIARY
        else:
            base = daily_energy_list[0][1]
            fark_pct = ((energy_kwh - base) / base * 100) if base > 0 else 0
            if fark_pct > 0:
                fark_str = f"+%{fark_pct:.0f}"
                fark_renk = SUCCESS
            elif fark_pct < 0:
                fark_str = f"-%{abs(fark_pct):.0f}"
                fark_renk = "#C9502E"
            else:
                fark_str = "0%"
                fark_renk = TEXT_TERTIARY

        gun_ismi = gunler_tr[pd.Timestamp(date).weekday()]
        bugun_flag = "<span style='color:#6B7684;font-size:11px;margin-left:6px'>bugun</span>" if i == 0 else ""

        energy_str = f"{energy_kwh:,.0f}".replace(",", ".")
        peak_str = f"{peak_guc:,.0f}".replace(",", ".")

        rows.append({
            "gun": f"{gun_ismi}{bugun_flag}",
            "energy": energy_str,
            "peak_saat": peak_saat,
            "peak_guc": peak_str,
            "fark": fark_str,
            "fark_renk": fark_renk,
        })

    header = (
        '<tr style="border-bottom:1px solid #E2E6EA">'
        '<th style="text-align:left;padding:12px 8px;font-size:11px;'
        'text-transform:uppercase;letter-spacing:0.05em;color:#6B7684;'
        'font-weight:600">Gun</th>'
        '<th style="text-align:right;padding:12px 8px;font-size:11px;'
        'text-transform:uppercase;letter-spacing:0.05em;color:#6B7684;'
        'font-weight:600">Beklenen Uretim (kWh)</th>'
        '<th style="text-align:right;padding:12px 8px;font-size:11px;'
        'text-transform:uppercase;letter-spacing:0.05em;color:#6B7684;'
        'font-weight:600">Pik Saat</th>'
        '<th style="text-align:right;padding:12px 8px;font-size:11px;'
        'text-transform:uppercase;letter-spacing:0.05em;color:#6B7684;'
        'font-weight:600">Pik Guc (kW)</th>'
        '<th style="text-align:right;padding:12px 8px;font-size:11px;'
        'text-transform:uppercase;letter-spacing:0.05em;color:#6B7684;'
        'font-weight:600">Bugune Gore</th>'
        '</tr>'
    )

    body = ""
    for r in rows:
        body += (
            '<tr style="border-bottom:1px solid #F0F2F4">'
            f'<td style="padding:12px 8px;font-size:13px;font-weight:500">{r["gun"]}</td>'
            f'<td style="padding:12px 8px;font-size:13px;text-align:right;'
            f'font-family:{mono}">{r["energy"]}</td>'
            f'<td style="padding:12px 8px;font-size:13px;text-align:right;'
            f'font-family:{mono}">{r["peak_saat"]}</td>'
            f'<td style="padding:12px 8px;font-size:13px;text-align:right;'
            f'font-family:{mono}">{r["peak_guc"]}</td>'
            f'<td style="padding:12px 8px;font-size:13px;text-align:right;'
            f'font-family:{mono};font-weight:600;'
            f'color:{r["fark_renk"]}">{r["fark"]}</td>'
            '</tr>'
        )

    st.markdown(
        '<div class="pvq-card" style="margin-top:16px">'
        '<div style="font-size:15px;font-weight:600;margin-bottom:12px">'
        '7 gunluk uretim tahmini'
        '</div>'
        f'<table style="width:100%;border-collapse:collapse">'
        f'{header}{body}'
        f'</table>'
        '</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# ANA render
# ============================================================
# ============================================================
# 5d: Export butonlari + API URL
# ============================================================

def _export_ve_api_bolumu() -> None:
    """CSV, Excel, JSON download + API URL kopyala kutusu."""
    import io
    import pandas as pd

    result = st.session_state.forecast_result
    plant = st.session_state.plant_spec

    hourly = result.hourly.copy()
    # Kolon adlarini kullanici dostu yap
    hourly_export = hourly.reset_index().rename(columns={"index": "timestamp"})

    # CSV
    csv_bytes = hourly_export.to_csv(index=False).encode("utf-8")

    # Excel - openpyxl timezone-aware datetime kabul etmiyor,
    # timestamp'i tz-unaware'e cevir (sadece Excel icin)
    hourly_excel = hourly_export.copy()
    if pd.api.types.is_datetime64_any_dtype(hourly_excel["timestamp"]):
        if hourly_excel["timestamp"].dt.tz is not None:
            hourly_excel["timestamp"] = hourly_excel["timestamp"].dt.tz_localize(None)

    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        hourly_excel.to_excel(writer, index=False, sheet_name="Saatlik Tahmin")
        # Ozet sayfasi
        ozet_df = pd.DataFrame({
            "Metrik": [
                "Toplam uretim (7 gun)",
                "Ortalama gunluk",
                "Pik guc",
                "Kapasite faktoru",
                "Latitude",
                "Longitude",
                "Kurulu guc (kWp)",
            ],
            "Deger": [
                f"{result.total_kwh:.1f} kWh",
                f"{result.average_daily_kwh:.1f} kWh",
                f"{result.peak_power_kw:.2f} kW",
                f"{result.capacity_factor:.3f}",
                plant.latitude,
                plant.longitude,
                plant.p_nom_kwp,
            ],
        })
        ozet_df.to_excel(writer, index=False, sheet_name="Ozet")
    excel_bytes = excel_buffer.getvalue()

    # JSON
    json_bytes = hourly_export.to_json(orient="records", date_format="iso").encode("utf-8")

    # Ust satir: 3 buton + API URL kutusu
    st.markdown(
        '<div class="pvq-card" style="margin-top:16px">'
        '<div style="display:flex;justify-content:space-between;'
        'align-items:center;margin-bottom:12px">'
        '<div style="font-size:15px;font-weight:600">Disa aktar</div>'
        '<div style="font-size:11px;color:#6B7684;'
        'text-transform:uppercase;letter-spacing:0.05em;font-weight:600">'
        '168 saatlik veri'
        '</div>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    cols = st.columns([1, 1, 1, 3])
    with cols[0]:
        st.download_button(
            label="⬇ CSV",
            data=csv_bytes,
            file_name="pvquant_tahmin_7gun.csv",
            mime="text/csv",
            use_container_width=True,
            key="dl_csv",
        )
    with cols[1]:
        st.download_button(
            label="⬇ Excel",
            data=excel_bytes,
            file_name="pvquant_tahmin_7gun.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key="dl_xlsx",
        )
    with cols[2]:
        st.download_button(
            label="⬇ JSON",
            data=json_bytes,
            file_name="pvquant_tahmin_7gun.json",
            mime="application/json",
            use_container_width=True,
            key="dl_json",
        )
    with cols[3]:
        # API URL - dekoratif, kopyalanabilir
        api_url = "https://api.pvquant.io/v1/santral/konya-ges/tahmin"
        st.text_input(
            "API adresi (yakinda)",
            value=api_url,
            key="api_url",
            label_visibility="collapsed",
            disabled=True,
            help="REST API entegrasyonu yakinda gelecek",
        )

def render_tahminler() -> None:
    page_header(
        "Tahminler",
        "168 saatlik kalibre uretim tahmini",
    )

    if "calibration_result" not in st.session_state:
        _uyari_kalibrasyon_yok()
        return

    _kpi_seridi()
    _once_sonra_karti()

    col1, col2 = st.columns(2, gap="medium")
    with col1:
        _bulduklarimiz_karti()
    with col2:
        _veri_kaliteniz_karti()

    _uyarilar_karti()

  # 5c: Forecast + grafik + tablo
    _forecast_bolumu()

    # 5d: Export butonlari
    if "forecast_result" in st.session_state:
        _export_ve_api_bolumu()
        