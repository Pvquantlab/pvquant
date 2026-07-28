"""Kalibrasyon sayfası — Anayasa Adım 3 (Zeyilname v2.1 sözleşmesi).

Değişmez kurallar (bu dosyada uygulanmış halleri):
  KURAL 2  : Sayfa hesap yapmaz — yalnız servis okur, ui_kit çizer.
  K1       : Sayfa HER ZAMAN DB'den çizer; buton yalnız yazar + st.rerun().
             İki render yolu (taze sonuç / DB) YOKTUR.
  K4       : Tüm sayılar sayi_tr'den geçer.
  K5       : Ekranda aynı anda en fazla BİR birincil buton.
  K10      : Ham HTML/hex yok — her görsel öğe ui_kit'ten.
  v2.0     : Önce/Sonra Şeridi SAPMA çiftini gösterir (MAPE değil);
             sapma yoksa şerit çizilmez, MAPE'ye düşülmez.
  v2.1     : Emekli oturum anahtarları (Zeyilname v2.1 listesi)
             OKUNMAZ ve YAZILMAZ — kaynak her zaman DB.

UYARLAMA (D-1/2/3 raporu — Fable 5 v2.1 kuralı):
  Yerel Ana.py mekanizması PAGE_RENDERERS sözlüğü üzerinden çalışır ve
  sayfa modüllerinden render_<sayfa_adı> desenli fonksiyon bekler;
  render() genel adı yerine def render_kalibrasyon() kullanılır ve dosya
  sonundaki render() çağrısı silinir (K5+K10 mantığı değişmez).
"""
from __future__ import annotations

import json

import streamlit as st

import tema
import ui_kit
from oturum import giris_bekcisi
from pvquant.reporting.styles import sayi_tr
from pvquant.services import calib_service, plant_service
from pvquant.services.ingest_service import veri_ozeti

# ---------------------------------------------------------------- eylem
def _kalibre(auth: dict, santral: dict, hibrit: bool) -> None:
    """Tek yazma yolu: servis + rerun. Sonuç elde TUTULMAZ (K1)."""
    mesaj = ("Hibrit model eğitiliyor… 30-60 sn"
             if hibrit else "Kalibrasyon yürütülüyor… 10-30 sn")
    with st.spinner(mesaj):
        calib_service.kalibre_et(auth["tenant_id"], santral, hibrit=hibrit)
    st.rerun()


# ---------------------------------------------------------------- bölgeler
def _bulduklarimiz(cal, santral: dict, ozet: dict) -> None:
    p = cal.params_json if isinstance(cal.params_json, dict) else json.loads(cal.params_json or "{}")
    satirlar = [
        ("η_BoS", sayi_tr(p["eta_bos"], 3) if p.get("eta_bos") is not None else "—"),
    ]
    # v2.16 P2: BG yalniz bifacial santralda gosterilir (mono'da anlamsiz)
    if (santral.get("panel_tech") or "bifacial") == "bifacial":
        satirlar.append(("BG (bifacial kazanç)",
                         sayi_tr(p["bg"], 3) if p.get("bg") is not None else "—"))
    satirlar += [
        # v2.16 F6: None -> 0° yalan soylerdi; "model buldu" durust
        ("Eğim / Azimut",
         "— (model buldu)" if santral.get("tilt") is None
         else f"{sayi_tr(santral['tilt'], 0)}° / "
              f"{sayi_tr(santral.get('azimuth') or 0, 0)}°"),
        ("Geçerli saat", sayi_tr(cal.n_valid_hours or ozet["valid_saat"], 0)),
        ("Kalibrasyon tarihi", ui_kit.tarih_tr(cal.created_at)),
    ]

    ui_kit.mono_kart("BULDUKLARIMIZ", satirlar)


def _once_sonra(cal) -> None:
    """v2.0: SAPMA çifti. after yoksa şerit hiç çizilmez; before yoksa
    bileşen tek değere düşer (kendi içinde)."""
    q = cal.quality_json if isinstance(cal.quality_json, dict) else json.loads(cal.quality_json or "{}")
    sonra = q.get("deviation_pct")
    if sonra is None:
        return
    ui_kit.once_sonra_seridi(
        once=q.get("deviation_before_pct"),
        sonra=sonra,
        eyebrow="YILLIK ENERJİ SAPMASI",
        mikro_not=("kalibrasyonun düzelttiği sistematik sapmadır (kalibrasyon dönemi); "
                   "saatlik tahmin isabeti Doğruluk sayfasında ölçülür."),
    )


def _hibrit_karti(auth: dict, santral: dict, cal) -> None:
    """Üç durum, kaynağı DB (gate_json + mode) — session değil (v2.1)."""
    gate = cal.gate_json if isinstance(cal.gate_json, dict) else json.loads(cal.gate_json or "{}")

    if cal.mode == "C":                                   # ---- AÇIK
        ui_kit.mono_kart("HİBRİT DEVREDE ✓", [
            ("Holdout MAPE", f"%{sayi_tr(gate.get('holdout_mape', 0), 1)}"),
            ("Fizik (aynı sınav)", f"%{sayi_tr(gate.get('fizik_mape', 0), 1)}"),
            ("İyileşme", f"%{sayi_tr(gate.get('iyilesme_pct', 0), 0)}"),
        ])
        st.caption("kronolojik son %20 sınavı")
        return

    if gate.get("denendi") and not gate.get("gecti"):     # ---- KAPI-GEÇEMEDİ
        sebep = gate.get("sebep", "iyileşme kapı eşiği %3'ün altında")
        ui_kit.banner("bilgi",
            f"Hibrit kapıyı geçemedi ({sebep}) — fizik modeliyle devam "
            "ediliyor. Bu bir hata değil, dürüstlük kuralıdır.")
        if st.button("Hibriti yeniden dene", type="secondary",
                     key="btn_hibrit_tekrar"):
            _kalibre(auth, santral, hibrit=True)
        return

    # ---- KAPALI (hiç denenmedi) — sayfanın TEK birincil butonu (K5)
    if st.button("🚀 Hibritle iyileştir", type="primary",
                 key="btn_hibrit", use_container_width=True):
        _kalibre(auth, santral, hibrit=True)
    st.caption("Fizik + AI rezidüel. Sistematik sapmaları öğrenir; "
               "eğitim 30-60 sn sürer.")


# ---------------------------------------------------------------- sayfa
def render_kalibrasyon() -> None:
    tema.kur("Kalibrasyon")
    auth = giris_bekcisi()
    if auth is None:
        st.stop()
    aktif_id = st.session_state.get("aktif_plant_id")
    if aktif_id is None:
        ui_kit.bos_durum("🏭", "Santral seçilmedi",
            "Kenar çubuğundan bir santral seçin ya da ilk "
            "santralinizi ekleyin.",
            "Veri Yükleme'ye git", "pages/veri_yukleme.py")
        st.stop()
    santral = plant_service.getir(auth["tenant_id"], aktif_id)
    if santral is None:
        # bayat-id: session'da eski id kalmıs — temizle ve boş duruma düş
        st.session_state.pop("aktif_plant_id", None)
        ui_kit.bos_durum("🏭", "Santral seçilmedi",
            "Kenar çubuğundan bir santral seçin ya da ilk "
            "santralinizi ekleyin.",
            "Veri Yükleme'ye git", "pages/veri_yukleme.py")
        st.stop()

    st.markdown('<div class="pv-sayfa-baslik">Kalibrasyon</div>',
                unsafe_allow_html=True)
    st.markdown('<div class="pv-sayfa-alt">Model, santralinizin kendi '
                'verisiyle uyarlanır — kanıtı bu sayfada görürsünüz.</div>',
                unsafe_allow_html=True)
    ui_kit.adimlar(aktif=3)

    tid, pid = auth["tenant_id"], santral["id"]
    ozet = veri_ozeti(tid, pid)

    # -------- boş durum 1: SCADA yok (D3 kalıbı — nötr, tek CTA)
    if ozet["valid_saat"] == 0:
        ui_kit.bos_durum("📁", "Önce SCADA verinizi yükleyin",
            "Kalibrasyon için geçmiş üretim veriniz gerekiyor. "
            "Veri Yükleme sayfasından CSV/xlsx dosyanızı yükleyerek başlayın.",
            "Veri Yükleme'ye git", "pages/veri_yukleme.py")
        st.stop()

    cal = calib_service.aktif_kalibrasyon(tid, pid)

    # -------- boş durum 2: SCADA var, kalibrasyon yok
    if cal is None:
        ui_kit.bos_durum_eylemli("⚙️",
            "Bu santral için kalibrasyon henüz yapılmadı",
            f"{sayi_tr(ozet['valid_saat'], 0)} geçerli saat hazır. "
            "Model kendini bu veriyle santralinize uyarlayacak.")
        if st.button("Kalibre et (Mod B)", type="primary",
                     key="btn_kalibre", use_container_width=True):
            _kalibre(auth, santral, hibrit=False)
        st.stop()

    # -------- dolu durum
    _bulduklarimiz(cal, santral, ozet)
    _once_sonra(cal)
    _hibrit_karti(auth, santral, cal)

    st.divider()
    # sessiz bakım eylemi — mevcut kademeyi korur (C ise hibritle yeniler)
    if st.button("Yeniden kalibre et", type="secondary",
                 key="btn_yeniden"):
        _kalibre(auth, santral, hibrit=(cal.mode == "C"))
    st.caption("Yeni veri yüklediyseniz yeniden kalibrasyon önerilir.")
