"""Anayasa 8.4 — Santralim referans uygulama.
Cerceve (tema.kur + giris_bekcisi + santral_secici + top bar) Ana.py'de.
Bu dosya SALT ICERIK: hero + kunye + KPI + grafikler + veri sagligi.

K10: ham hex/style YASAK — hepsi ui_kit + styles.css'ten.
K1: ozet_service mode=None dondurursa 'Kalibre değil' + bos KPI (sahte deger YOK).
"""
from __future__ import annotations
import streamlit as st

import ui_kit
from pvquant.services.ozet_service import gunun_ozeti
from pvquant.reporting.styles import sayi_tr


def render_santralim() -> None:
    """PAGE_RENDERERS['santralim'] cagrisi. Ana.py bunu cerceve icinde cagirir."""
    # Ana.py session'da bunlari kurdu
    auth = st.session_state.get("auth")
    aktif_id = st.session_state.get("aktif_plant_id")
    if not auth or not aktif_id:
        ui_kit.bos_durum(
            "🏭", "Santral seçilmedi",
            "Sol sidebar'dan bir santral seçin.",
            "Santral ekle", "veri_yukleme",
        )
        return

    # santral_secici sidebar'da secilen dict'i doner ama session'a
    # yalniz id yazar; adi ve kapasiteyi burada tek sorgu ile aliriz
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(auth["tenant_id"]) as s:
        row = s.execute(text(
            "SELECT id, name, capacity_kwp, ac_limit_kw, lat, lon, tz "
            "FROM plants WHERE id=:p"
        ), {"p": aktif_id}).first()
    if row is None:
        ui_kit.bos_durum(
            "🏭", "Santral bulunamadı",
            "Seçili santralın kaydı silinmiş olabilir.",
            "Santral ekle", "veri_yukleme",
        )
        return
    santral = {
        "id": str(row.id),
        "name": row.name,
        "capacity_kwp": float(row.capacity_kwp),
        # v2.37: kunye karti icin AC tavani (B-1) — yoksa None, kart '—' basar
        "ac_limit_kw": float(row.ac_limit_kw) if row.ac_limit_kw is not None else None,
        "lat": row.lat, "lon": row.lon, "tz": row.tz,
        # konum_metni: 'Konya' gibi il/koordinat kisa — simdilik koordinat
        "konum_metni": f"{row.lat:.2f}, {row.lon:.2f}",
    }

    # ----- Ana veri: tek servis cagrisi (Anayasa 8.4) -----
    o = gunun_ozeti(auth["tenant_id"], santral)

    # ----- HERO (Anayasa 5.7) -----
    ui_kit.hero(
        santral=santral,
        mod=o.mode,
        sapma=o.sapma_pct,
        icgoru=o.icgoru_cumlesi,
        hava=o.hava_3gun,
    )

    st.markdown('<div style="margin-top:24px"></div>', unsafe_allow_html=True)

    # ----- KPI ŞERİDİ (4 kart) -----
    # K1: mode=None => tum tahmin KPI'lari '—' gosterir (sahte deger yok)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        deger = sayi_tr(o.bugun_kwh, 0) if o.bugun_kwh is not None else "—"
        ui_kit.kpi("BUGÜNKÜ TAHMİNİ ÜRETİM", deger, "kWh",
                   "kalibrasyon bekleniyor" if o.mode is None
                   else "gün sonuna kadar")
    with c2:
        deger = sayi_tr(o.yarin_kwh, 0) if o.yarin_kwh is not None else "—"
        ui_kit.kpi("YARIN BEKLENEN", deger, "kWh", o.yarin_hava)
    with c3:
        deger = sayi_tr(o.hafta_mwh, 1) if o.hafta_mwh is not None else "—"
        ui_kit.kpi("BU HAFTAKİ TOPLAM", deger, "MWh",
                   "7 günlük tahmin" if o.hafta_mwh is not None else "")
    with c4:
        ui_kit.kpi(
            "MODEL DURUMU",
            ui_kit.MOD_KISA[o.mode],
            "",
            _model_alt_zengin(o) if o.model_alt else "Kalibrasyon sayfasından başlayın",
            durum="pozitif" if o.mode is not None and o.mode != "A" else "notr",
        )

    # ----- v2.37: SANTRAL KÜNYE KARTI -----
    # foto varsa gercek fotograf (assets/santral/{id}.jpg), yoksa sematik SVG
    from pathlib import Path
    _foto = Path("assets/santral") / f"{santral['id']}.jpg"
    ui_kit.kunye_karti(santral, o.mode,
                       foto_yolu=str(_foto) if _foto.exists() else None)

    st.markdown('<div style="margin-top:24px"></div>', unsafe_allow_html=True)

    # ----- GRAFİKLER (2 sütun: 2/3 + 1/3) -----
    g1, g2 = st.columns([2, 1])
    with g1:
        st.markdown(
            '<div class="pv-eyebrow">BUGÜN — SAATLİK ÜRETİM</div>',
            unsafe_allow_html=True,
        )
        # v2.16 F1: egri TAHMIN varsa cizilir; gerceklesen yoklugu
        # yalniz dolgu katmanini dusurur (imza grafigi kapali duramaz)
        if o.saatler and o.tahmin_kw:
            gercek = (o.gercek_kw if o.gercek_kw
                      else [None] * len(o.saatler))
            st.plotly_chart(
                ui_kit.gun_isigi_egrisi(
                    o.saatler, gercek, o.tahmin_kw, o.simdi_idx
                ),
                use_container_width=True,
                config={"displayModeBar": False},
            )
            if not o.gercek_kw or all(v is None for v in o.gercek_kw):
                st.caption("bugünün gerçekleşeni için güncel SCADA gerekli")
        else:
            ui_kit.bos_durum(
                "📊", "Gün Işığı Eğrisi henüz hazır değil",
                "İlk tahmin üretildiğinde saatlik üretim eğrisi burada görünür.",
                "Tahminler'e geç", "tahminler",
            )
    with g2:
        st.markdown(
            '<div class="pv-eyebrow">7 GÜNLÜK GÖRÜNÜM</div>',
            unsafe_allow_html=True,
        )
        if o.gunler and o.gunluk_mwh:
            st.plotly_chart(
                ui_kit.yedi_gun_bar(o.gunler, o.gunluk_mwh, o.bugun_idx),
                use_container_width=True,
                config={"displayModeBar": False},
            )
        else:
            st.markdown(
                '<div class="pv-mikro" style="color:var(--ikincil);'
                'margin-top:12px">Kalibrasyon sonrası 7 günlük tahmin '
                'burada görünecek.</div>',
                unsafe_allow_html=True,
            )

    st.markdown('<div style="margin-top:24px"></div>', unsafe_allow_html=True)

    # ----- VERİ SAĞLIĞI (Anayasa 5.8) -----
    ui_kit.saglik_karti(
        son_yukleme=o.son_scada_tarihi,
        islenen_saat=o.islenen_saat,
        anomali=o.anomali_sayisi,
    )


def _model_alt_zengin(o):
    """v2.13: Model Durumu KPI alt satiri bilgi tasisin.
    'Hibrit' yerine 'sapma %3,23 · son kalibrasyon 17 Tem'."""
    from pvquant.reporting.styles import sayi_tr
    import ui_kit
    parcalar = []
    if o.sapma_pct is not None:
        parcalar.append(f"yıllık sapma %{sayi_tr(abs(o.sapma_pct), 2)}")
    if o.kalibrasyon_tarihi is not None:
        parcalar.append(f"son kalibrasyon {ui_kit.tarih_tr(o.kalibrasyon_tarihi)}")
    return " · ".join(parcalar) if parcalar else o.model_alt