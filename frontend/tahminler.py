"""Tahminler sayfasi — Anayasa Adim 4 (Zeyilname v2.3 sozlesmesi).

Uygulanan kurallar: sayfa DB'den cizer, buton yazar+rerun (K1);
santral cerceveden gelir — aktif_plant_id + plant_service.getir (v2.2);
sunum ozetlemesi serbest, is mantigi yasak (v1.9 genellemesi);
bant yalniz Mod C'de, yoklugu caption'la durustce soylenir (K4/K1);
sayilar sayi_tr (K4); ham HTML yok (K10); ekran basina tek birincil (K5).
"""
from __future__ import annotations

import streamlit as st

import tema
import ui_kit
from oturum import giris_bekcisi
from pvquant.reporting.styles import sayi_tr
from pvquant.services import calib_service, forecast_service, plant_service

UFUKLAR = {"24s": 24, "72s": 72, "7g": 168}


# ---------------------------------------------------------------- eylem
def _tahmin_uret(auth: dict, santral: dict) -> None:
    with st.spinner("Tahmin üretiliyor… 10-20 sn"):
        forecast_service.uret_ve_kaydet(auth["tenant_id"], santral)
    st.rerun()


# ---------------------------------------------------------------- sayfa
def render_tahminler() -> None:
    tema.kur("Tahminler")
    auth = giris_bekcisi()
    if auth is None:
        st.stop()

    aktif_id = st.session_state.get("aktif_plant_id")          # v2.2 kalibi
    if aktif_id is None:
        ui_kit.bos_durum("🏭", "Santral seçilmedi",
            "Kenar çubuğundan bir santral seçin ya da ilk santralinizi "
            "ekleyin.", "Veri Yükleme'ye git", "veri_yukleme")
        st.stop()
    santral = plant_service.getir(auth["tenant_id"], aktif_id)
    if santral is None:                                        # bayat id
        st.session_state.pop("aktif_plant_id", None)
        st.rerun()

    st.markdown('<div class="pv-sayfa-baslik">Tahminler</div>',
                unsafe_allow_html=True)
    st.markdown('<div class="pv-sayfa-alt">168 saatlik kalibre üretim '
                'tahmini — arşivden, son koşu.</div>',
                unsafe_allow_html=True)

    tid, pid = auth["tenant_id"], santral["id"]

    # -------- bos durum 1: kalibrasyon yok
    cal = calib_service.aktif_kalibrasyon(tid, pid)
    if cal is None:
        ui_kit.bos_durum("📊", "Önce kalibrasyon yapın",
            "Tahmin, modelin santralinizi tanımasıyla başlar. SCADA "
            "verinizi yükleyip modeli kalibre edin.",
            "Kalibrasyon'a git", "kalibrasyon")
        st.stop()

    # -------- boş durum 2: kalibrasyon var, henüz koşu yok
    df = forecast_service.son_kosu(tid, pid)
    if df is None or df.empty:
        ui_kit.bos_durum_eylemli("↗",
            "İlk tahmin henüz üretilmedi",
            f"Model kalibre (Mod {cal.mode}). İlk 7 günlük tahmini şimdi "
            "üretebilirsiniz; sonrakiler her sabah otomatik koşar.")
        if st.button("Tahmin üret", type="primary",
                     key="btn_tahmin", use_container_width=True):
            _tahmin_uret(auth, santral)
        st.stop()

    # -------- dolu durum
    yerel = df.tz_convert(santral["tz"])                       # sunum

    ust1, ust2 = st.columns([3, 1])
    with ust1:
        try:
            ufuk = st.segmented_control(
                "Ufuk", options=list(UFUKLAR), default="7g",
                key="ufuk_sec", label_visibility="collapsed")
        except AttributeError:                                 # D-3 fallback
            ufuk = st.radio("Ufuk", list(UFUKLAR), index=2,
                            horizontal=True, key="ufuk_sec",
                            label_visibility="collapsed")
    with ust2:
        if st.button("Rapor sayfasında indir →", type="tertiary",
                     key="btn_rapora"):
            ui_kit.sayfaya_git("raporlar")

    g = yerel.head(UFUKLAR[ufuk or "7g"])                      # (9) onayli

    # ana grafik — bant kurali bilesenin icinde (Mod C + veri varsa)
    st.plotly_chart(ui_kit.tahmin_grafigi(g, cal.mode),
                    use_container_width=True,
                    config={"displayModeBar": False})
    if cal.mode != "C":
        st.caption("Belirsizlik bandı (P10–P90) Mod C ile gelir.")

    # gunluk ozet tablosu (sunum ozetlemesi — v1.9 genellemesi)
    gunluk = g["p50_kw"].groupby(g.index.date).sum()
    gunluk = gunluk[gunluk > 0]  # v2.12: sifir-kuyruk gunleri dus
    satirlar = {"Tarih": [ui_kit.tarih_tr(t) for t in gunluk.index],
                "P50 (kWh)": [sayi_tr(v, 0) for v in gunluk.values]}
    if cal.mode == "C" and g["p10_kw"].notna().any():
        alt = g["p10_kw"].groupby(g.index.date).sum()
        alt = alt[gunluk.index]  # v2.12: aynı maske
        ust = g["p90_kw"].groupby(g.index.date).sum()
        ust = ust[gunluk.index]  # v2.12: aynı maske
        satirlar["P90-P10 (kWh)"] = [
            f"{sayi_tr(a, 0)} - {sayi_tr(u, 0)}"
            for a, u in zip(alt.values, ust.values)]
    import pandas as pd                                        # sunum
    ui_kit.mono_tablo(pd.DataFrame(satirlar), {})

    st.caption(f"Son koşu Mod {cal.mode} · kaynak: tahmin arşivi "
               "— koşular güncellenmez, yenisi eklenir.")
