"""Raporlar sayfasi — Anayasa Adim 6 (§6.6) · Zeyilname v2.9 sozlesmesi.

ANAYASA §6.6: Uc format karti yan yana (PDF yonetici ozeti / Excel tam veri /
JSON API) — her kartta SESSIZ indirme akisi; sayfanin birincil butonu YOKTUR
(K5: indirme birincil sayilmaz). Kart altbilgisi: son uretim zamani mono.
Altta "Gecmis kosular" tablosu. Bos durum D3.

v2.9 kararlari:
  - Rapor dosyalari ARSIVLENMEZ (MVP): talep aninda uretilir.
  - "Hazirla -> indir" iki dokunus: bytes SESSION'da tutulur (gecici UI eseri).
  - Uretim tek kapidan: report_service.uret(tid, plant, format).
"""
from __future__ import annotations

import streamlit as st

import tema
import ui_kit
from oturum import giris_bekcisi
from pvquant.services import (calib_service, forecast_service,
                              plant_service, report_service)

_FORMATLAR = [
    ("pdf",  "📄 PDF",   "Yönetici özeti — logo, KPI'lar, HOLDOUT kutusu"),
    ("xlsx", "📊 Excel", "Tam veri — saatlik tablo, Özet ve Metadata sayfaları"),
    ("json", "🔌 JSON",  "API formatı — şema 1.1.0, entegrasyona hazır"),
]

MODEL_AD = {"hybrid_residual": "Hibrit", "barhdadi_bennis": "Fizik",
            "backtest": "Geriye dönük"}   # v2.16 P3 sunum sözlüğü


def render_raporlar() -> None:
    tema.kur("Raporlar")
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

    st.markdown('<div class="pv-sayfa-baslik">Raporlar</div>',
                unsafe_allow_html=True)
    st.markdown('<div class="pv-sayfa-alt">PDF yönetici özeti · Excel '
                'tam veri · JSON API formatı — hepsi tahmin arşivinden.'
                '</div>', unsafe_allow_html=True)

    tid, pid = auth["tenant_id"], santral["id"]

    # -------- bos durum 1: kalibrasyon yok
    if calib_service.aktif_kalibrasyon(tid, pid) is None:
        ui_kit.bos_durum("📄", "Önce kalibrasyon yapın",
            "Rapor üretmek için önce SCADA verinizi yükleyip modeli "
            "santralinize kalibre etmelisiniz.",
            "Kalibrasyon'a git", "kalibrasyon")
        st.stop()

    # -------- boş durum 2: kalibre ama koşu yok
    if forecast_service.son_kosu(tid, pid) is None:
        ui_kit.bos_durum("↗", "Önce tahmin üretin",
            "Rapor, arşivdeki son tahmin koşusundan kurulur. "
            "Tahminler sayfasından ilk koşuyu üretin.",
            "Tahminler'e git", "tahminler")
        st.stop()

    # -------- dolu durum: uc format karti (K5: birincil YOK)
    kolonlar = st.columns(3)
    for (fmt, baslik, tanim), kol in zip(_FORMATLAR, kolonlar):
        with kol:
            ui_kit.mono_kart(baslik, [("", tanim)])
            anahtar = f"rapor_{fmt}_{pid}"
            hazir = st.session_state.get(anahtar)
            if hazir is None:
                if st.button("Hazırla", key=f"btn_{fmt}",
                             type="secondary", width="stretch"):
                    with st.spinner("Üretiliyor…"):
                        st.session_state[anahtar] = report_service.uret(
                            tid, santral, fmt)
                    st.rerun()
            else:
                veri, dosya_adi, uretim_ts = hazir
                st.download_button("İndir", data=veri,
                    file_name=dosya_adi, key=f"dl_{fmt}",
                    width="stretch")
                st.caption(f"hazır · {uretim_ts:%H:%M}")

    # -------- gecmis kosular (v2.9: dosya kolonu yok)
    st.markdown('<div class="pv-eyebrow">GEÇMİŞ KOŞULAR</div>',
                unsafe_allow_html=True)
    gecmis = forecast_service.kosu_gecmisi(tid, pid, n=10)
    if gecmis:
        import pandas as pd                                    # sunum
        ui_kit.mono_tablo(pd.DataFrame(
            {"Tarih": [f"{r.run_at:%d.%m.%Y %H:%M}" for r in gecmis],
             "Mod": [r.mode for r in gecmis],
             "Model": [MODEL_AD.get(r.model, r.model) for r in gecmis]}), {})
        st.caption("Koşular güncellenmez, yenisi eklenir — rapor her "
                   "koşudan yeniden üretilebilir.")
