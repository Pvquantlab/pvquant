"""Dogruluk sayfasi — Anayasa Adim 5 (§6.5) · Zeyilname v2.5+v2.8.

Urunun vaadi bu ekrandir: dogrulugunu KANITLAR. Veri mantigi P4 §2'den;
gorsel kabuk Anayasa §6.5; cerceve kalibi v2.2; okumalar servis uzerinden
(KURAL 2 — sayfada SQL yok)."""
from __future__ import annotations

import json

import streamlit as st

import tema
import ui_kit
from oturum import giris_bekcisi
from pvquant.reporting.styles import sayi_tr
from pvquant.services import calib_service, forecast_service, plant_service


def render_dogruluk() -> None:
    tema.kur("Doğruluk")
    auth = giris_bekcisi()
    if auth is None:
        st.stop()

    aktif_id = st.session_state.get("aktif_plant_id")          # v2.2
    if aktif_id is None:
        ui_kit.bos_durum("🏭", "Santral seçilmedi",
            "Kenar çubuğundan bir santral seçin.",
            "Veri Yükleme'ye git", "veri_yukleme")
        st.stop()
    santral = plant_service.getir(auth["tenant_id"], aktif_id)
    if santral is None:
        st.session_state.pop("aktif_plant_id", None)
        st.rerun()

    st.markdown('<div class="pv-sayfa-baslik">Doğruluk Karnesi</div>',
                unsafe_allow_html=True)
    st.markdown('<div class="pv-sayfa-alt">Tahminlerimiz gerçekleşenle '
                'her gece karşılaştırılır — kanıt burada birikir.</div>',
                unsafe_allow_html=True)

    tid, pid = auth["tenant_id"], santral["id"]

    # -------- bos durum 1: kalibrasyon yok
    if calib_service.aktif_kalibrasyon(tid, pid) is None:
        ui_kit.bos_durum("📊", "Önce kalibrasyon yapın",
            "Karne, kalibre modelin tahminleriyle başlar.",
            "Kalibrasyon'a git", "kalibrasyon")
        st.stop()

    sk = forecast_service.skill_gecmisi(tid, pid, gun=120)  # v2.14: demo icin genis pencere

    # -------- bos durum 2: karne henuz birikiyor
    if sk.empty:
        ui_kit.bos_durum_eylemli("⏳", "Karne birikiyor",
            "İlk skor için gereken: güncel SCADA verisi + 2 gece. "
            "Worker her gece tahmini gerçekleşenle karşılaştırır. "
            "Bu sayfa doldukça satış konuşmanız da dolar.")
        st.stop()

    # -------- dolu durum: 3 KPI
    kova0 = sk[sk["horizon_bucket"] == "0-24"]
    c1, c2, c3 = st.columns(3)
    with c1:
        if len(kova0):
            ui_kit.kpi("MAPE (0-24s, 30 GÜN ORT.)",
                       f"%{sayi_tr(kova0['mape'].mean(), 1)}", "",
                       "gündüz saatleri, valid veriyle")
        else:
            ui_kit.kpi("MAPE (0-24s, 30 GÜN ORT.)", "—", "",
                       "0-24s kovası henüz boş")
    with c2:
        sv = kova0["skill_vs_naive"].dropna() if len(kova0) else []
        if len(sv):
            ort = sv.mean()
            ui_kit.kpi("NAİFE GÖRE ÜSTÜNLÜK",
                       f"%{sayi_tr(ort, 0)}", "",
                       "referans: dünün aynı saati",
                       durum="pozitif" if ort > 0 else "dikkat")
        else:
            ui_kit.kpi("NAİFE GÖRE ÜSTÜNLÜK", "—", "",
                       "referans birikiyor")
    with c3:
        ui_kit.kpi("KARNE GÜNÜ",
                   sayi_tr(sk["date"].nunique(), 0), "gün",
                   "kesintisiz kanıt geçmişi")

    # -------- gunluk MAPE — ufuk kovalarina gore
    st.markdown('<div class="pv-eyebrow">GUNLUK MAPE — UFUK '
                'KOVALARINA GORE</div>', unsafe_allow_html=True)
    piv = sk.pivot_table(index="date", columns="horizon_bucket",
                         values="mape")
    st.plotly_chart(ui_kit.skill_grafigi(piv),
                    use_container_width=True,
                    config={"displayModeBar": False})
    st.caption("0-24s marka · 24-72s gri · 72s+ soluk — uzak ufuk "
               "dogal olarak daha belirsizdir.")

    # -------- mod gecmisi (kapi kayitlariyla)
    st.markdown('<div class="pv-eyebrow">MOD GEÇMİŞİ</div>',
                unsafe_allow_html=True)
    satirlar = []
    for r in calib_service.kalibrasyon_gecmisi(tid, pid):
        g_raw = r.gate_json
        g = g_raw if isinstance(g_raw, dict) else json.loads(g_raw or "{}")
        ek = (f"kapı: +%{sayi_tr(g['iyilesme_pct'], 0)}"
              if g.get("gecti") else
              ("kapı: geçemedi" if g.get("denendi") else "—"))
        satirlar.append((ui_kit.tarih_tr(r.created_at),
                         f"Mod {r.mode} · {ek}"))
    ui_kit.mono_kart("KALİBRASYON KAYITLARI", satirlar)
