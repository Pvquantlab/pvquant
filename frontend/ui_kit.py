"""Anayasa Bölüm 5 — bileşen kütüphanesi.
Sayfa dosyaları YALNIZ bu fonksiyonları çağırır (K10).
Ham hex/style YASAK; her değer styles.css :root'tan gelir."""
from __future__ import annotations
import streamlit as st
import plotly.graph_objects as go


# --- 5.2 Mod sözlüğü (PDF ile aynı) ---
MOD_METIN = {"A": "Mod A — saf fizik", "B": "Mod B — kalibre fizik",
             "C": "Mod C — hibrit"}
MOD_KISA = {"A": "Saf fizik", "B": "Kalibre", "C": "Hibrit", None: "—"}


# --- 5.1 KPI karti ---
def kpi(etiket: str, deger: str, birim: str = "", alt: str = "",
        durum: str = "notr"):
    """durum: notr|pozitif|dikkat — yalnız ALT satırın rengini etkiler.
    deger sayi_tr ile bicimlenmis gelir (K4); burada bicimleme YAPILMAZ."""
    renk = {"notr": "var(--ikincil)", "pozitif": "var(--pozitif)",
            "dikkat": "var(--vurgu)"}[durum]
    st.markdown(f'''
    <div class="pv-kart pv-kpi">
      <div class="pv-eyebrow">{etiket}</div>
      <div class="pv-olcum">{deger}<span class="pv-birim">{birim}</span></div>
      <div class="pv-mikro" style="color:{renk}">{alt}</div>
    </div>''', unsafe_allow_html=True)


# --- 5.2 Mod / durum rozeti ---
def mod_rozet(mode: str | None, sapma_pct: float | None = None):
    """Kanit seridinin cekirdegi. mode None => 'Kalibre degil' (gri) — K1."""
    if mode is None:
        st.markdown(
            '<span class="pv-rozet pv-rozet-notr">Kalibre değil</span>',
            unsafe_allow_html=True)
        return
    ek = (f" · sapma %{abs(sapma_pct):.2f}".replace(".", ",")
          if sapma_pct is not None else "")
    st.markdown(f'<span class="pv-rozet pv-rozet-marka">'
                f'{MOD_METIN[mode]}{ek}</span>', unsafe_allow_html=True)


# --- 5.3 Boş durum (K6) ---
def bos_durum(ikon: str, baslik: str, aciklama: str,
              cta_metin: str, cta_sayfa: str):
    """NOTR cerceve. Kirmizi/sol cubuk YASAK. Tek CTA."""
    st.markdown(f'''
    <div class="pv-bos">
      <div class="pv-bos-ikon">{ikon}</div>
      <div class="pv-bos-baslik">{baslik}</div>
      <div class="pv-bos-metin">{aciklama}</div>
    </div>''', unsafe_allow_html=True)
    if st.button(cta_metin, type="primary", use_container_width=True):
        st.switch_page(cta_sayfa)


# --- 5.4 Sihirbaz adım göstergesi (yalnız Veri Yükleme — K9) ---
def adimlar(aktif: int,
            adlar: tuple = ("Santral bilgisi", "Veri yolu", "Sonuç")):
    parca = []
    for i, ad in enumerate(adlar, 1):
        sinif = ("tamam" if i < aktif else
                 "aktif" if i == aktif else "bekliyor")
        isaret = "✓" if i < aktif else str(i)
        parca.append(f'<span class="pv-adim pv-adim-{sinif}">'
                     f'<b>{isaret}</b> {ad}</span>')
    st.markdown('<div class="pv-adimlar">' + " · ".join(parca) + "</div>",
                unsafe_allow_html=True)


# --- 5.5 Grafik teması ---
def tema_uygula(fig: go.Figure, yukseklik: int = 300) -> go.Figure:
    fig.update_layout(
        height=yukseklik, margin=dict(l=8, r=8, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", size=12, color="#6B7280"),
        showlegend=False, hovermode="x unified",
        xaxis=dict(gridcolor="rgba(0,0,0,0)",
                   tickfont=dict(family="JetBrains Mono", size=11)),
        yaxis=dict(gridcolor="#E5E7EB", zeroline=False,
                   tickfont=dict(family="JetBrains Mono", size=11)))
    return fig


def gun_isigi_egrisi(saat, gercek_kw, tahmin_kw, simdi_idx) -> go.Figure:
    """IMZA 1. gercek: dolgulu; kalan: kesikli; simdi: dikey cizgi."""
    fig = go.Figure()
    fig.add_scatter(x=saat[:simdi_idx+1], y=gercek_kw[:simdi_idx+1],
        mode="lines", line=dict(color="#D97706", width=2.2),
        fill="tozeroy", fillcolor="rgba(245,158,11,.12)",
        name="Gerçekleşen")
    fig.add_scatter(x=saat[simdi_idx:], y=tahmin_kw[simdi_idx:],
        mode="lines", line=dict(color="#1D4ED8", width=1.8, dash="dot"),
        name="Kalan saatler")
    fig.add_vline(x=saat[simdi_idx], line_width=1, line_dash="dash",
        line_color="#9CA3AF",
        annotation_text=f"şimdi · {saat[simdi_idx]}",
        annotation_font=dict(family="JetBrains Mono", size=10))
    return tema_uygula(fig)


def yedi_gun_bar(gunler, mwh, bugun_idx) -> go.Figure:
    """koyu = bugun, acik = digerleri, amber = en dusuk gun (K7)."""
    renk = ["#8FB8CB"] * len(mwh)
    renk[bugun_idx] = "#1E5A78"
    renk[mwh.index(min(mwh))] = "#F59E0B"
    fig = go.Figure(go.Bar(x=gunler, y=mwh, marker_color=renk,
        text=[f"{v:.1f}".replace(".", ",") for v in mwh],
        textposition="outside",
        textfont=dict(family="JetBrains Mono", size=10)))
    return tema_uygula(fig, 260)


# --- 5.7 Hero (Santralim üst bandı) ---
def hero(santral: dict, mod, sapma, icgoru, hava: list):
    """hava: [{"gun":"BUGÜN","derece":31,"kwhm2":7.1}, ...] en cok 3.
    icgoru None ise satir CIZILMEZ (K1 — veri yoksa cumle yok)."""
    hava_html = "".join(
        f'<div class="pv-hava"><div class="pv-hava-gun">{h["gun"]}</div>'
        f'<div class="pv-hava-derece">{h["derece"]}°</div>'
        f'<div class="pv-hava-kwh">{str(h["kwhm2"]).replace(".", ",")} '
        f'kWh/m²</div></div>' for h in hava)
    icgoru_html = (f'<div class="pv-hero-icgoru">{icgoru}</div>'
                   if icgoru else "")
    rozet = (f'<span class="pv-rozet pv-rozet-hero">{MOD_KISA[mod]}'
             + (f' — sapma %{abs(sapma):.2f}'.replace(".", ",")
                if sapma is not None else "") + "</span>")
    konum = santral.get("konum_metni", "")
    html = ('<div class="pv-hero"><div class="pv-hero-sol">'
        f'<div class="pv-hero-ad">{santral["name"]}</div>'
        f'<div class="pv-hero-kunye">{santral["capacity_kwp"]/1000:.1f}'
        f' MW · {konum}</div>'
        f'<div class="pv-hero-rozetler">{rozet}</div>' + icgoru_html +
        f'</div><div class="pv-hero-hava">{hava_html}</div></div>')
    st.markdown(html, unsafe_allow_html=True)


# --- 5.8 Veri sağlığı kartı ---
def saglik_karti(son_yukleme, islenen_saat: int, anomali: int):
    saat_tr = f"{islenen_saat:,}".replace(",", ".")   # sayi_tr dili
    html = ('<div class="pv-kart">'
      '<div class="pv-eyebrow">VERİ SAĞLIĞI</div>'
      '<div class="pv-saglik-izgara">'
      '<div><div class="pv-mikro">Son SCADA yüklemesi</div>'
      f'<div class="pv-olcum-kucuk">{tarih_tr(son_yukleme)}</div></div>'
      '<div><div class="pv-mikro">İşlenen veri</div>'
      f'<div class="pv-olcum-kucuk">{saat_tr} saat</div></div>'
      '<div><div class="pv-mikro">Bayraklanan anomali</div>'
      f'<div class="pv-olcum-kucuk">{anomali}</div>'
      '<div class="pv-mikro">bayraklandı, silinmedi</div></div></div>'
      '<div class="pv-mikro">Daha güncel veri, daha isabetli '
      'kalibrasyon demektir.</div></div>')
    st.markdown(html, unsafe_allow_html=True)


def tarih_tr(t) -> str:
    """'6 Tem 2026' — locale'e GUVENME; AYLAR_TR'den kisalt."""
    if t is None:
        return "—"
    from pvquant.reporting.styles import AYLAR_TR
    return f"{t.day} {AYLAR_TR[t.month-1][:3]} {t.year}"


# --- 5.9 Banner ve tablo ---
def banner(tur: str, metin: str):
    """tur: hata|bilgi. Sayfa ustunde ayni anda TEK banner."""
    sinif = "pv-banner-hata" if tur == "hata" else "pv-banner-bilgi"
    st.markdown(f'<div class="pv-banner {sinif}">{metin}</div>',
                unsafe_allow_html=True)


def mono_tablo(df, kolon_adlari: dict):
    """Tum tablolar bu yoldan: mono hucre, sayilar sayi_tr'den gecmis
    METIN olarak gelir (dataframe'e ham float verme)."""
    st.dataframe(df.rename(columns=kolon_adlari),
        use_container_width=True, hide_index=True)


def once_sonra_seridi(once, sonra, eyebrow: str, mikro_not: str,
                      birim: str = "%"):
    """İMZA bileşen (Zeyilname v2.0): iki büyük mono sayı arasında ok.
    once None => TEK değer + 'ilk kayıt' notu (v2.0). Değerler MUTLAK
    gösterilir (yön bilgisi gerekiyorsa mikro nota yazılır)."""
    from pvquant.reporting.styles import sayi_tr
    if once is None:
        orta = (f'<span class="pv-serit-sayi">{birim}'
                f'{sayi_tr(abs(sonra), 2)}</span>')
        mikro_not = "ilk kayıt — karşılaştırma sonraki kalibrasyonda"
    else:
        orta = (f'<span class="pv-serit-sayi pv-soluk">{birim}'
                f'{sayi_tr(abs(once), 2)}</span>'
                f'<span class="pv-serit-ok">→</span>'
                f'<span class="pv-serit-sayi">{birim}'
                f'{sayi_tr(abs(sonra), 2)}</span>')
    st.markdown(
        f'<div class="pv-kart pv-serit">'
        f'<div class="pv-eyebrow">{eyebrow}</div>'
        f'<div class="pv-serit-govde">{orta}</div>'
        f'<div class="pv-mikro">{mikro_not}</div></div>',
        unsafe_allow_html=True)


def mono_kart(baslik: str, satirlar):
    """Genel anahtar-değer kartı (Bulduklarımız, künyeler, hibrit özeti).
    satirlar: [(etiket, deger_metni), ...] — değerler çağıran tarafta
    sayi_tr'den geçmiş METİN olarak gelir (K4 sorumluluğu çağırandadır)."""
    govde = "".join(
        f'<div class="pv-mono-satir"><span>{e}</span><b>{d}</b></div>'
        for e, d in satirlar)
    st.markdown(
        f'<div class="pv-kart"><div class="pv-eyebrow">{baslik}</div>'
        f'<div class="pv-mono-govde">{govde}</div></div>',
        unsafe_allow_html=True)


def bos_durum_eylemli(ikon: str, baslik: str, aciklama: str):
    """K6 boş-durum kutusunun CTA'sız hali: sayfa kendi birincil butonunu
    ALTINA koyar (eylem sayfa-değiştirme değilse bu kullanılır)."""
    st.markdown(
        f'<div class="pv-bos">'
        f'<div class="pv-bos-ikon">{ikon}</div>'
        f'<div class="pv-bos-baslik">{baslik}</div>'
        f'<div class="pv-bos-metin">{aciklama}</div></div>',
        unsafe_allow_html=True)
