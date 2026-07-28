"""Anayasa Bölüm 5 — bileşen kütüphanesi.
Sayfa dosyaları YALNIZ bu fonksiyonları çağırır (K10).
Ham hex/style YASAK; her değer styles.css :root'tan gelir."""
from __future__ import annotations
import streamlit as st
import plotly.graph_objects as go


# --- 5.2 Mod sözlüğü (PDF ile aynı) ---
MOD_METIN = {"A": "Mod A — saf fizik", "B": "Mod B — kalibre fizik",
             "C": "Mod C — hibrit"}
AYLAR_KISA_TR = ["Oca", "Şub", "Mar", "Nis", "May", "Haz",
                 "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]  # v2.16 F3
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
    ek = (f" · yıllık enerji sapması %{abs(sapma_pct):.2f}".replace(".", ",")
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
        sayfaya_git(cta_sayfa)


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
    koyu = bool(st.session_state.get("koyu_tema"))          # v2.50
    izgara = "#1E2A36" if koyu else "#EDF0F3"
    yazi = "#A7B8C2" if koyu else "#6B7280"
    fig.update_layout(
        height=yukseklik, margin=dict(l=8, r=8, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", size=12, color=yazi),
        showlegend=False, hovermode="x unified",
        xaxis=dict(gridcolor="rgba(0,0,0,0)",
                   tickfont=dict(family="JetBrains Mono", size=11)),
        yaxis=dict(gridcolor=izgara, zeroline=False,
                   tickfont=dict(family="JetBrains Mono", size=11)))
    return fig


def gun_isigi_egrisi(saat, gercek_kw, tahmin_kw, simdi_idx,
                     p10_kw=None, p90_kw=None,
                     ac_limit_kw=None) -> go.Figure:
    """IMZA 1. gercek: amber dolgulu; tahmin: yesil dolgulu kesikli;
    simdi: dikey cizgi. v2.34 K-3: lejant + kW ekseni.
    v2.37: tahmin egrisine gun-isigi dolgusu (canlilik, durust yolla)."""
    fig = go.Figure()
    # v2.43: P10-P90 bandi — sektor dili ana sayfada
    if p10_kw and p90_kw and any(v is not None for v in p10_kw):
        fig.add_scatter(x=saat, y=p90_kw, mode="lines",
            line=dict(width=0), hoverinfo="skip", showlegend=False)
        fig.add_scatter(x=saat, y=p10_kw, mode="lines",
            line=dict(width=0), fill="tonexty",
            fillcolor="rgba(15,110,86,.10)", name="P10-P90",
            hoverinfo="skip")
    fig.add_scatter(x=saat[:simdi_idx+1], y=gercek_kw[:simdi_idx+1],
        mode="lines", line=dict(color="#D97706", width=2.2),
        fill="tozeroy", fillcolor="rgba(245,158,11,.12)",
        name="Gerçekleşen")
    # v2.43: tam-gun P50 plani her zaman cizilir — gerceklesen yoksa da
    # sayfa "plan"i gosterir; gelince "plana karsi gercek" okumasi dogar.
    fig.add_scatter(x=saat, y=tahmin_kw,
        mode="lines", line=dict(color="#0E6B54", width=1.6, dash="dot"),
        name="Tahmin (P50)")
    fig.add_scatter(x=saat[simdi_idx:], y=tahmin_kw[simdi_idx:],
        mode="lines", line=dict(color="#0E6B54", width=0.1),
        fill="tozeroy", fillcolor="rgba(14,107,84,.10)",
        showlegend=False, hoverinfo="skip")
    # v2.21: kategori ekseninde add_vline string x kabul etmez —
    # add_shape + add_annotation, x = kategori KONUMU (indeks)
    fig.add_shape(type="line",
        x0=simdi_idx, x1=simdi_idx, y0=0, y1=1,
        xref="x", yref="paper",
        line=dict(width=1, dash="dash", color="#9CA3AF"))
    fig.add_annotation(x=simdi_idx, y=1.04, xref="x", yref="paper",
        text=f"şimdi · {saat[simdi_idx]}", showarrow=False,
        font=dict(family="JetBrains Mono", size=10, color="#6B7280"))
    if ac_limit_kw:                                     # v2.48
        _ac = f"{ac_limit_kw:,.0f}".replace(",", ".")
        fig.add_hline(y=ac_limit_kw, line_dash="dot", line_width=1,
                      line_color="#9CA3AF",
                      annotation_text=f"AC tavanı {_ac} kW",
                      annotation_position="top left",
                      annotation_font=dict(family="JetBrains Mono",
                                           size=10, color="#6B7280"))
    fig = tema_uygula(fig)
    fig.update_layout(showlegend=True, legend=dict(
        orientation="h", x=0, y=1.12, yanchor="bottom",
        font=dict(family="JetBrains Mono", size=11)))
    fig.update_yaxes(title_text="kW",
        title_font=dict(family="JetBrains Mono", size=11))
    fig.update_xaxes(tickvals=list(saat)[::2])       # v2.47: saat etiketi seyrelt
    fig.update_yaxes(tickformat="~s", nticks=5)      # v2.47: 20k bicimi, az izgara
    return fig


def yedi_gun_bar(gunler, mwh, bugun_idx) -> go.Figure:
    """koyu = bugun, acik = digerleri, amber = en dusuk gun (K7)."""
    renk = ["#8FB8CB"] * len(mwh)
    renk[bugun_idx] = "#1E5A78"
    renk[mwh.index(min(mwh))] = "#F59E0B"
    fig = go.Figure(go.Bar(x=gunler, y=mwh, marker_color=renk,
        text=[f"{v:.1f}".replace(".", ",") for v in mwh],
        textposition="outside",
        textfont=dict(family="JetBrains Mono", size=12)))
    fig.update_yaxes(nticks=5)                       # v2.47
    return tema_uygula(fig, 260)


# --- 5.7 Hero (Santralim üst bandı) ---
def hero(santral: dict, mod, sapma, icgoru, hava: list):
    """hava: [{"gun":"BUGÜN","derece":31,"kwhm2":7.1}, ...] en cok 3.
    icgoru None ise satir CIZILMEZ (K1 — veri yoksa cumle yok)."""
    hava_html = "".join(
        f'<div class="pv-hava"><div class="pv-hava-gun">{h["gun"]}</div>'
        f'<div class="pv-hava-derece">{str(h["derece"]).replace(".", ",")}°</div>'
        f'<div class="pv-hava-kwh">{str(h["kwhm2"]).replace(".", ",")} '
        f'kWh/m²</div></div>' for h in hava)
    icgoru_html = (f'<div class="pv-hero-icgoru">{icgoru}</div>'
                   if icgoru else "")
    # v2.34 K-2: rozetteki yuzde YILLIK enerji sapmasidir
    rozet = (f'<span class="pv-rozet pv-rozet-hero">{MOD_KISA[mod]}{" model" if mod else ""}'
             + (f' — yıllık enerji sapması %{abs(sapma):.2f}'.replace(".", ",")
                if sapma is not None else "") + "</span>")
    konum = santral.get("konum_metni", "")
    mw_tr = f"{santral['capacity_kwp']/1000:.1f}".replace(".", ",")  # O-1
    html = ('<div class="pv-hero"><div class="pv-hero-sol">'
        f'<div class="pv-hero-ad">{santral["name"]}</div>'
        f'<div class="pv-hero-kunye">{mw_tr}'
        f' MW · {konum}</div>'
        f'<div class="pv-hero-rozetler">{rozet}</div>' + icgoru_html +
        f'</div><div class="pv-hero-hava">{hava_html}</div></div>')
    st.markdown(html, unsafe_allow_html=True)


# --- v2.37: Santral Künye Kartı ---
_KUNYE_SVG = ('<svg viewBox="0 0 240 150" width="240" height="150" '
  'aria-hidden="true"><defs>'
  '<linearGradient id="kCam" x1="0" y1="0" x2="1" y2="1">'
  '<stop offset="0" stop-color="#1B3A55"/>'
  '<stop offset=".5" stop-color="#12293D"/>'
  '<stop offset="1" stop-color="#0C1E2E"/></linearGradient>'
  '<linearGradient id="kHucre" x1="0" y1="0" x2="0" y2="1">'
  '<stop offset="0" stop-color="#1E4668"/>'
  '<stop offset="1" stop-color="#132C42"/></linearGradient>'
  '<linearGradient id="kParilti" x1="0" y1="0" x2="1" y2="1">'
  '<stop offset="0" stop-color="#FFFFFF" stop-opacity=".22"/>'
  '<stop offset=".45" stop-color="#FFFFFF" stop-opacity=".05"/>'
  '<stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/></linearGradient>'
  '<linearGradient id="kCerceve" x1="0" y1="0" x2="0" y2="1">'
  '<stop offset="0" stop-color="#B8C4CC"/>'
  '<stop offset="1" stop-color="#5E6B74"/></linearGradient></defs>'
  '<ellipse cx="120" cy="132" rx="88" ry="8" fill="#000" opacity=".28"/>'
  '<g transform="translate(20,8) skewX(-14)">'
  '<rect x="46" y="10" width="160" height="98" rx="4" '
  'fill="url(#kCerceve)"/>'
  '<rect x="50" y="14" width="152" height="90" rx="2" fill="url(#kCam)"/>'
  + "".join(
    f'<rect x="{54+s*37.5}" y="{18+r*28}" width="33" height="24" rx="1.5" '
    f'fill="url(#kHucre)" stroke="#0A1B26" stroke-width="1.2"/>'
    for r in range(3) for s in range(4)) +
  '<rect x="50" y="14" width="152" height="90" rx="2" '
  'fill="url(#kParilti)"/>'
  '<rect x="46" y="104" width="160" height="5" rx="2" fill="#47535C"/></g>'
  '<path d="M70 116 L64 136 L70 136 L75 118 Z" fill="#5E6B74"/>'
  '<path d="M182 116 L188 136 L182 136 L177 118 Z" fill="#4A565F"/>'
  '<line x1="76" y1="141" x2="204" y2="141" stroke="#F59E0B" '
  'stroke-width="2" opacity="0.85"/>'
  '<line x1="204" y1="141" x2="226" y2="141" stroke="#7FD1B9" '
  'stroke-width="2" opacity="0.5"/></svg>')


def kunye_karti(santral: dict, mod, foto_yolu: str | None = None):
    """v2.37: santral kimligi tek kartta — buyuk DC gucu + kunye cipleri +
    santral gorseli. foto_yolu varsa gercek fotograf, yoksa sematik SVG.
    K1: bilinmeyen alan '—' gosterir, sahte deger yok."""
    dc = f"{santral['capacity_kwp']:,.0f}".replace(",", ".")
    ac = santral.get("ac_limit_kw")
    ac_txt = (f"{ac:,.0f}".replace(",", ".") + " kW") if ac else "—"
    egim = "model buldu" if mod == "C" else "—"
    gorsel = _KUNYE_SVG
    if foto_yolu:
        try:
            import base64
            from pathlib import Path
            b64 = base64.b64encode(Path(foto_yolu).read_bytes()).decode()
            gorsel = (f'<img src="data:image/jpeg;base64,{b64}" '
                      f'class="pv-kunye-foto" alt="Santral fotoğrafı">')
        except OSError:
            pass                       # foto okunamazsa sematik kalir
    st.markdown(f'''
    <div class="pv-kunye">
      <div>
        <div class="pv-eyebrow" style="color:#96A9B4">SANTRAL KÜNYESİ</div>
        <div class="pv-kunye-buyuk">{dc}<span class="pv-kunye-birim">kWp DC</span></div>
        <div class="pv-kunye-cipler">
          <div><div class="pv-kunye-cip-ad">AC tavanı</div>
               <div class="pv-kunye-cip-deger">{ac_txt}</div></div>
          <div><div class="pv-kunye-cip-ad">Eğim / Azimut</div>
               <div class="pv-kunye-cip-deger" style="color:var(--mint)">{egim}</div></div>
          <div><div class="pv-kunye-cip-ad">Saat dilimi</div>
               <div class="pv-kunye-cip-deger">{santral.get("tz") or "—"}</div></div>
        </div>
      </div>
      <div>{gorsel}</div>
    </div>''', unsafe_allow_html=True)


# --- 5.8 Veri sağlığı kartı ---
def saglik_karti(son_yukleme, islenen_saat: int, anomali: int):
    import datetime as _dt
    saat_tr = f"{islenen_saat:,}".replace(",", ".")   # sayi_tr dili
    anomali_tr = f"{anomali:,}".replace(",", ".")   # v2.44 binlik
    # v2.34 O-2: bayatlik esikleri — <=7 notr, 8-30 vurgu, 31+ negatif.
    tarih_stil, yas_html = "", ""
    if son_yukleme is not None:
        g = son_yukleme.date() if hasattr(son_yukleme, "date") else son_yukleme
        yas = (_dt.date.today() - g).days
        if yas > 30:
            tarih_stil = ' style="color:var(--negatif)"'
            yas_html = (f'<div class="pv-mikro" style="color:var(--negatif)">'
                        f'Veri akışı {yas} gündür kesik — karne son veri tarihine kadar hesaplanır.</div>')
        elif yas > 7:
            tarih_stil = ' style="color:var(--vurgu)"'
            yas_html = (f'<div class="pv-mikro" style="color:var(--vurgu)">'
                        f'Son veri {yas} gün önce</div>')
    html = ('<div class="pv-kart">'
      '<div class="pv-eyebrow">VERİ SAĞLIĞI</div>'
      '<div class="pv-saglik-izgara">'
      '<div><div class="pv-mikro">Son SCADA yüklemesi</div>'
      f'<div class="pv-olcum-kucuk"{tarih_stil}>{tarih_tr(son_yukleme)}</div>'
      f'{yas_html}</div>'
      '<div><div class="pv-mikro">İşlenen veri</div>'
      f'<div class="pv-olcum-kucuk">{saat_tr} saat</div></div>'
      '<div><div class="pv-mikro">Anomali tespiti</div>'
      f'<div class="pv-olcum-kucuk">{anomali_tr}</div>'
      '<div class="pv-mikro">satır işaretlendi · ham veri değiştirilmedi</div></div></div>'
      '<div class="pv-mikro">Model, en '
      'güncel veriniz kadar isabetlidir.</div></div>')
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

# =====================================================================
# Anayasa Adim 4 ekleri
# =====================================================================

def sayfaya_git(sayfa_adi: str) -> None:
    """Tek yonlendirme kapisi (D-1). bos_durum CTA'si ve sessiz eylemler
    hepsi buradan gecer — iki ayri yol yasatilmaz.

    v2.31: govde repo'nun gercek yonlendirme mimarisine (active_page +
    PAGE_RENDERERS) baglandi; st.switch_page pages/ konvansiyonu ister,
    bu repo onu kullanmaz."""
    st.session_state.active_page = sayfa_adi
    st.rerun()


def tahmin_grafigi(df_yerel, mode: str, ac_limit_kw=None):
    """Ana tahmin grafigi: p50 cizgi (marka); Mod C'de P10-P90 dolgu
    bandi (marka %14 opak). Bant verisi yoksa (eski kosu) bant cizilmez
    — K1: sayfa caption'i sebebini soyler."""
    import plotly.graph_objects as go
    fig = go.Figure()
    bant_var = (mode == "C" and "p10_kw" in df_yerel.columns
                and df_yerel["p10_kw"].notna().any())
    if bant_var:
        fig.add_scatter(x=df_yerel.index, y=df_yerel["p90_kw"],
                        mode="lines", line=dict(width=0),
                        hoverinfo="skip", showlegend=False)
        fig.add_scatter(x=df_yerel.index, y=df_yerel["p10_kw"],
                        mode="lines", line=dict(width=0),
                        fill="tonexty", fillcolor="rgba(15,110,86,.14)",
                        name="P10-P90", hoverinfo="skip")
    fig.add_scatter(x=df_yerel.index, y=df_yerel["p50_kw"],
                    mode="lines", name="P50",
                    line=dict(color="#0F6E56", width=2.2))
    # v2.48: AC tavani referansi — plato, kirpmanin kanitidir
    if ac_limit_kw:
        _ac = f"{ac_limit_kw:,.0f}".replace(",", ".")
        fig.add_hline(y=ac_limit_kw, line_dash="dot", line_width=1,
                      line_color="#9CA3AF",
                      annotation_text=f"AC tavanı {_ac} kW",
                      annotation_position="top left",
                      annotation_font=dict(family="JetBrains Mono",
                                           size=10, color="#6B7280"))
    fig = tema_uygula(fig, yukseklik=320)
    fig.update_yaxes(tickformat="~s", nticks=5)      # v2.47-B: 20k bicimi
    # v2.16 F3: eksen Türkçe — 3+ günde günlük etiket, kısa ufukta saat
    gunler = sorted({ts.date() for ts in df_yerel.index})
    if len(gunler) <= 2:
        fig.update_xaxes(tickformat="%H:%M")     # dil-nötr saat ekseni
    else:
        import datetime as _dt
        tzinfo = df_yerel.index.tz
        tv = [_dt.datetime.combine(d, _dt.time(12), tzinfo=tzinfo)
              for d in gunler]
        tt = [f"{d.day} {AYLAR_KISA_TR[d.month - 1]}" for d in gunler]
        fig.update_xaxes(tickvals=tv, ticktext=tt)
    return fig


# Anayasa Adim 5 — kovali skill grafigi
_KOVA_STIL = {                       # Anayasa §6.5 renk duzeni
    "0-24":  dict(color="#0F6E56", width=2.4),               # marka — duz
    "24-72": dict(color="#6B7280", width=1.8, dash="dash"),  # v2.34 O-3
    "72+":   dict(color="#C4CBD4", width=1.6, dash="dot"),   # v2.34 O-3
}


def skill_grafigi(piv):
    """Gunluk MAPE cizgileri, ufuk kovalarina gore. piv: pivot_table
    (index=date, columns=horizon_bucket, values=mape).
    v2.16 F4: gun-eksenli kategori + lines+markers (az nokta okunur)."""
    fig = go.Figure()
    for kova, stil in _KOVA_STIL.items():
        if kova in piv.columns:
            fig.add_scatter(x=list(piv.index), y=piv[kova],
                            mode="lines+markers", name=f"{kova} saat",
                            line=stil, marker=dict(size=6),
                            connectgaps=False)
    fig = tema_uygula(fig, 300)
    fig.update_layout(showlegend=True, legend=dict(
        orientation="h", x=0, y=1.08, yanchor="bottom",
        font=dict(family="JetBrains Mono", size=11)))
    tt = [f"{d.day} {AYLAR_KISA_TR[d.month - 1]}" for d in piv.index]
    fig.update_xaxes(tickvals=list(piv.index), ticktext=tt,
                     type="category")
    return fig