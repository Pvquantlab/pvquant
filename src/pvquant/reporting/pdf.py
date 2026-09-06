"""Şartname v2.0 PDF — 8 sayfa (S1 kapak + S2-S8 içerik), A4, ReportLab.

Sayfa planı (Rapor Spesifikasyonu v2.0 §3):
    S1 Kapak · S2 Yönetici Özeti · S3 Tahmin Detayı · S4 Doğruluk Karnesi
    S5 Kalibrasyon Hikayesi · S6 İklim Bağlamı · S7 Metodoloji & Künye
    S8 Koşu Arşivi (koşullu — <2 koşuda dürüst işaret)

İlkeler: her sayfa altbilgisinde koşu kimliği + "Sayfa X/8"; veri yoksa
"—" ya da "veri eksik (gereken: …)" — asla uydurma 0, asla boş iskelet.
Sayılar sayi_tr ile (v2.96 duruşma dersi: %27.8 nokta / 481,6 virgül
karışıklığı). Gömme: matplotlib → PNG 300dpi → drawImage.
"""
from __future__ import annotations

from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as rl_canvas

from .charts import (fig_flags, fig_gunluk_barlar, fig_iklim_zarf,
                     fig_kalib, fig_karne, fig_kosu_evrim, fig_son12,
                     fig_tipik_gun, fig_to_png, gun_tr)
from .styles import (RENK, TIPO, karne_donem_metni, pdf_fontlarini_kaydet,
                     sayi_tr, wmape_baslik)

SAYFA_W, SAYFA_H = A4          # pt
KENAR = 12 * mm
IC_W = SAYFA_W - 2 * KENAR
TOPLAM = 8                     # sartname: 1 kapak + 7 icerik


def _y(mm_ustten: float) -> float:
    return SAYFA_H - mm_ustten * mm


def _kunye_satiri() -> str:
    """v2.270 — rapor künyesindeki kaynak/lisans satırı; DB yoksa (test) sabit açık kaynak listesi."""
    try:
        from pvquant.services.kaynak_service import rapor_kunye_satiri
        return rapor_kunye_satiri()
    except Exception:   # noqa: BLE001
        return ("Hava verisi: ECMWF Open Data (CC BY 4.0) · ICON-EU, DWD (CC BY 4.0) · PVGIS-SARAH3, JRC (CC BY 4.0) · "
                "Gerçekleşme: santral SCADA'sı · Fizik modeli: pvlib. Veriler PVQuant tarafından işlenmiştir; kaynaklar bu ürünü desteklemez.")


def _hex(c, hexrenk: str):
    c.setFillColor(hexrenk)
    c.setStrokeColor(hexrenk)


def build_pdf(ctx) -> bytes:
    F, FB = pdf_fontlarini_kaydet()
    buf = BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    n_gun = len(ctx.daily_kwh)
    c.setTitle(f"PVQuant — {ctx.plant_name} {n_gun} Günlük Tahmin + Karne")

    sayfalar = (_kapak, _yonetici_ozeti, _tahmin_detayi, _karne_sayfasi,
                _kalibrasyon, _iklim, _metodoloji, _arsiv)
    for i, sayfa in enumerate(sayfalar, start=1):
        sayfa(c, ctx, F, FB)
        _footer(c, ctx, F, sayfa=i)
        c.showPage()
    c.save()
    return buf.getvalue()


# ---------------------------------------------------------------- ortak
def _logo(c, x_pt: float, ust_mm: float, boyut_mm: float = 8.0):
    """PVQuant simgesi — assets/pvquant_logo.svg ile birebir ayni geometri."""
    s = boyut_mm * mm / 48.0
    y_alt = _y(ust_mm + boyut_mm)
    _hex(c, RENK.MARKA)
    c.roundRect(x_pt, y_alt, 48 * s, 48 * s, 11 * s, stroke=0, fill=1)
    _hex(c, RENK.VURGU)
    c.circle(x_pt + 36.5 * s, y_alt + (48 - 10.5) * s, 4 * s, stroke=0, fill=1)
    _hex(c, "#FFFFFF")
    for bx, by, bh in ((10, 28, 9), (20.5, 22, 15), (31, 16, 21)):
        c.roundRect(x_pt + bx * s, y_alt + (48 - by - bh) * s,
                    6.5 * s, bh * s, 1.5 * s, stroke=0, fill=1)


def _rozet(c, FB, sag_pt: float, ust_mm: float, mode: str):
    metin = {"A": "Mod A — saf fizik", "B": "Mod B — kalibre fizik",
             "C": "Mod C — hibrit"}.get(mode, mode)
    rw = c.stringWidth(metin, FB, 8) + 8
    _hex(c, RENK.MARKA)
    c.roundRect(sag_pt - rw, _y(ust_mm + 3.3), rw, 4.6 * mm, 3,
                stroke=1, fill=0)
    c.setFont(FB, 8)
    c.drawRightString(sag_pt - 4, _y(ust_mm + 1.7), metin)


def _sayfa_ustu(c, ctx, F, FB, baslik: str, alt: str = "",
                donem: str = ""):
    """S2-S8 ortak başlık bandı."""
    _logo(c, KENAR, ust_mm=11.5, boyut_mm=8.0)
    _hex(c, RENK.MARKA)
    c.setFont(FB, 14)
    c.drawString(KENAR + 10.5 * mm, _y(17.6), "PVQuant")
    _hex(c, RENK.METIN)
    c.setFont(FB, TIPO.BASLIK)
    c.drawString(KENAR, _y(25.5), baslik)
    if alt:
        c.setFont(F, TIPO.ALT_BASLIK)
        _hex(c, RENK.IKINCIL)
        c.drawString(KENAR, _y(31), alt)
    sag = SAYFA_W - KENAR
    if donem:
        _hex(c, RENK.IKINCIL)
        c.setFont(F, 8)
        c.drawRightString(sag, _y(16), donem)
    _rozet(c, FB, sag, 25.5, ctx.mode)
    _hex(c, RENK.MARKA)
    c.setLineWidth(1.1)
    c.line(KENAR, _y(34), SAYFA_W - KENAR, _y(34))


def _kart(c, F, FB, x, kutu_w, y_et, y_num, y_alt, etiket, deger,
          birim="", alt=None, renk=None, ayrac=False):
    if ayrac:
        _hex(c, RENK.CIZGI)
        c.setLineWidth(0.7)
        c.line(x - 4 * mm, y_et + 2 * mm, x - 4 * mm, y_alt - 1.5 * mm)
    _hex(c, RENK.IKINCIL)
    c.setFont(FB, TIPO.KPI_ETIKET)
    c.drawString(x, y_et, etiket)
    _hex(c, renk or RENK.METIN)
    c.setFont(FB, 19)
    c.drawString(x, y_num, deger)
    if birim:
        c.setFont(F, TIPO.KPI_BIRIM)
        _hex(c, RENK.IKINCIL)
        c.drawString(x + c.stringWidth(deger, FB, 19) + 3, y_num, birim)
    if alt:
        c.setFont(F, 6.9)
        _hex(c, RENK.IKINCIL)
        c.drawString(x, y_alt, alt)


def _bilgi_yok(c, F, FB, y_mm: float, baslik: str, aciklama: str):
    """Dürüst 'veri eksik' bloğu — iskelet/boş şablon yerine."""
    _hex(c, RENK.METIN)
    c.setFont(FB, 11)
    c.drawString(KENAR, _y(y_mm), baslik)
    _hex(c, RENK.IKINCIL)
    c.setFont(F, TIPO.GOVDE)
    c.drawString(KENAR, _y(y_mm + 7), aciklama)


def _footer(c, ctx, F, sayfa: int):
    _hex(c, RENK.CIZGI)
    c.setLineWidth(0.7)
    c.line(KENAR, _y(283), SAYFA_W - KENAR, _y(283))
    _hex(c, RENK.IKINCIL)
    c.setFont(F, TIPO.KUCUK)
    c.drawString(KENAR, _y(287),
                 "IEC 61724-1 · P90: %90 olasılıkla aşılacak değer (IEA-PVPS T13)")
    sag_metin = f"PVQuant {ctx.model_version}"
    if ctx.calibrated_at is not None:
        sag_metin += f" · kal. {ctx.calibrated_at:%d.%m.%Y}"
    sag_metin += (f" · {ctx.mode} · {ctx.run_at_utc:%Y-%m-%dT%H:%M}Z"
                  f" · {sayfa}/{TOPLAM}")
    c.drawRightString(SAYFA_W - KENAR, _y(287), sag_metin)


# ------------------------------------------------------------ S1: Kapak
def _kapak(c, ctx, F, FB):
    n_gun = len(ctx.daily_kwh)
    _logo(c, SAYFA_W / 2 - 11 * mm, ust_mm=64, boyut_mm=22)
    _hex(c, RENK.MARKA)
    c.setFont(FB, 30)
    c.drawCentredString(SAYFA_W / 2, _y(102), "PVQuant")
    _hex(c, RENK.IKINCIL)
    c.setFont(F, 10)
    c.drawCentredString(SAYFA_W / 2, _y(109),
                        "Santralinizin kanıtlı üretim tahmini")
    _hex(c, RENK.METIN)
    c.setFont(FB, 21)
    c.drawCentredString(SAYFA_W / 2, _y(132), ctx.plant_name)
    c.setFont(FB, 13.5)
    c.drawCentredString(SAYFA_W / 2, _y(141),
                        f"{n_gun} Günlük Üretim Tahmini + Doğruluk Karnesi")
    _hex(c, RENK.IKINCIL)
    c.setFont(F, 10)
    c.drawCentredString(SAYFA_W / 2, _y(149), f"Dönem: {ctx.period_str}")

    # kimlik kutusu — rapor kimligi HER ZAMAN kosudan (v2.94 dersi)
    kw, kh = 118 * mm, 30 * mm
    x = (SAYFA_W - kw) / 2
    _hex(c, RENK.ZEMIN_SOLUK)
    c.roundRect(x, _y(196), kw, kh, 6, stroke=0, fill=1)
    satirlar = [
        ("Koşu", f"{ctx.run_at_utc:%d.%m.%Y %H:%M} UTC"),
        ("Mod", {"A": "A — saf fizik", "B": "B — kalibre fizik",
                 "C": "C — hibrit"}.get(ctx.mode, ctx.mode)),
        ("Model", f"{ctx.model_name} ({ctx.model_version})"),
        ("Konum", f"{ctx.latitude:.2f}, {ctx.longitude:.2f}"
                  f" · {sayi_tr(ctx.capacity_kwp, 0)} kWp"),
    ]
    yy = 173.5
    for e, v in satirlar:
        _hex(c, RENK.IKINCIL)
        c.setFont(F, 8.5)
        c.drawString(x + 8 * mm, _y(yy), e)
        _hex(c, RENK.METIN)
        c.setFont(FB, 9.5)
        c.drawString(x + 30 * mm, _y(yy), v)
        yy += 5.9
    _hex(c, RENK.IKINCIL)
    c.setFont(F, 8)
    c.drawCentredString(SAYFA_W / 2, _y(212),
                        "Rapor Spesifikasyonu v2.0 · her sayı koşu "
                        "verisinden — veri yoksa \u201c—\u201d, asla uydurma 0")


# --------------------------------------------------- S2: Yönetici Özeti
def _yonetici_ozeti(c, ctx, F, FB):
    _sayfa_ustu(c, ctx, F, FB, "Yönetici Özeti", ctx.plant_name,
                donem=f"Dönem: {ctx.period_str}")
    kutu_w = IC_W / 4.0
    o0 = ctx.karne_ozet("0-24")

    def sira(y0, kartlar):
        y_et, y_num, y_alt = _y(y0), _y(y0 + 9.5), _y(y0 + 15)
        for i, k in enumerate(kartlar):
            _kart(c, F, FB, KENAR + i * kutu_w, kutu_w, y_et, y_num,
                  y_alt, *k[:-1], ayrac=(i > 0), renk=k[-1])

    # ust sira: uretim
    if ctx.has_band:
        p90, p10 = ctx.band_mwh
        alt_b, ust_b = sorted((p90, p10))   # kantil yonu farketmez
        guven = (f"{sayi_tr(alt_b, 0)}–{sayi_tr(ust_b, 0)}", "MWh",
                 "P10/P90 bandı (IEA-PVPS)")
    else:
        guven = ("—", "", "yalnız Mod C'de üretilir")
    sira(41.5, [
        ("TOPLAM BEKLENEN ÜRETİM", sayi_tr(ctx.total_mwh, 1), "MWh",
         f"P50 · {len(ctx.daily_kwh)} gün", None),
        ("GÜVEN ARALIĞI",) + guven + (None,),
        ("KAPASİTE FAKTÖRÜ", f"%{sayi_tr(ctx.capacity_factor_pct, 1)}", "",
         "E / (P_nom × saat)", None),
        ("ÖZGÜL VERİM", sayi_tr(ctx.specific_yield, 1), "kWh/kWp",
         "IEC 61724-1", None),
    ])
    # alt sira: dogruluk/veri
    kal = (f"%{sayi_tr(ctx.mape_pct, 1)}" if ctx.mape_pct is not None
           else "—")
    hold = (f"%{sayi_tr(ctx.holdout_mape_pct, 1)}"
            if ctx.holdout_mape_pct is not None else "—")
    karne_v = (f"%{sayi_tr(o0['wmape_ort'], 1)}" if o0 else "—")
    kaps = (f"%{sayi_tr(ctx.coverage_pct, 1)}"
            if ctx.coverage_pct is not None else "—")
    sira(63, [
        ("KALİBRASYON MAPE", kal, "", "eğitim dönemi isabeti", None),
        ("HOLDOUT MAPE", hold, "", "kronolojik son %20 sınavı", None),
        ("KARNE WMAPE (0-24s)", karne_v, "",
         f"{o0['gun']} gün ort." if o0 else "gece doğrulama birikiyor",
         RENK.MARKA if o0 else None),
        ("SCADA KAPSAMA", kaps, "", "geçerli saat / toplam", None),
    ])
    _hex(c, RENK.CIZGI)
    c.setLineWidth(0.8)
    c.line(KENAR, _y(84), SAYFA_W - KENAR, _y(84))

    # üç cümlelik anlatı
    _hex(c, RENK.IKINCIL)
    c.setFont(FB, TIPO.BOLUM)
    c.drawString(KENAR, _y(92), "ÖZET")
    _hex(c, RENK.METIN)
    c.setFont(F, 9)
    mod_c = {"A": "saf fizik modeliyle", "B": "SCADA ile kalibre edilmiş "
             "fizik modeliyle", "C": "kalibre fizik + ML hibrit modeliyle"
             }.get(ctx.mode, "")
    anlati = [
        f"{ctx.plant_name} için {len(ctx.daily_kwh)} günlük dönemde "
        f"{sayi_tr(ctx.total_mwh, 1)} MWh üretim bekleniyor (P50, {mod_c}).",
    ]
    if ctx.has_band:
        p90, p10 = ctx.band_mwh
        alt_b, ust_b = sorted((p90, p10))
        anlati.append(
            f"Olasılıksal bant {sayi_tr(alt_b, 0)}–{sayi_tr(ust_b, 0)} MWh "
            f"(P10/P90); gerçekleşme %80 olasılıkla bu aralıkta beklenir.")
    else:
        anlati.append("Bu koşuda olasılıksal bant üretilmedi; bant yalnız "
                      "hibrit (Mod C) koşularda hesaplanır.")
    if o0:
        anlati.append(
            f"Doğruluk karnesi son {o0['gun']} ölçülen günde ortalama "
            f"%{sayi_tr(o0['wmape_ort'], 1)} WMAPE gösteriyor — ayrıntı S4.")
    else:
        anlati.append("Doğruluk karnesi henüz birikmedi: taze SCADA "
                      "yüklendikçe her gece otomatik doğrulanır (S4).")
    yy = 98
    for cume in anlati:
        c.drawString(KENAR, _y(yy), cume)
        yy += 5.4

    # nasıl okunur kutusu
    _hex(c, RENK.ZEMIN_SOLUK)
    c.roundRect(KENAR, _y(158), IC_W, 38 * mm, 6, stroke=0, fill=1)
    _hex(c, RENK.IKINCIL)
    c.setFont(FB, TIPO.BOLUM)
    c.drawString(KENAR + 4 * mm, _y(124), "BU RAPOR NASIL OKUNUR")
    maddeler = [
        "P50: medyan tahmin — gerçekleşmenin %50 olasılıkla üstünde kalacağı değer. P90 daha temkinli (%90).",
        "WMAPE: Σ|tahmin−gerçek| / Σgerçek — üretimle ağırlıklı hata; karne her gece gerçekle karşılaştırılır.",
        "Skill: naif referansa (akıllı persistans) üstünlük — pozitifse model dünü kopyalamaktan iyidir.",
        "\u201c—\u201d: o metrik için veri yok demektir; PVQuant veri yoksa sıfır uydurmaz, boş bırakır.",
        "Mod rozeti her sayfanın sağ üstünde: A saf fizik · B kalibre fizik · C hibrit (bantlı).",
    ]
    yy = 130.5
    c.setFont(F, 8.2)
    for m in maddeler:
        _hex(c, RENK.MARKA)
        c.rect(KENAR + 4 * mm, _y(yy), 2, 2, stroke=0, fill=1)
        _hex(c, RENK.METIN)
        c.drawString(KENAR + 7.5 * mm, _y(yy + 0.4), m)
        yy += 5.6


# --------------------------------------------------- S3: Tahmin Detayı
def _tahmin_detayi(c, ctx, F, FB):
    _sayfa_ustu(c, ctx, F, FB, "Tahmin Detayı", ctx.plant_name,
                donem=f"Dönem: {ctx.period_str}")
    # tam genişlik günlük barlar (N gün ölçekli)
    img = fig_to_png(fig_gunluk_barlar(ctx))
    c.drawImage(ImageReader(img), KENAR, _y(116), width=IC_W,
                height=74 * mm, preserveAspectRatio=True, anchor="sw")
    # alt sol: tipik gün · alt sağ: bant açıklaması / dürüst blok
    img2 = fig_to_png(fig_tipik_gun(ctx))
    c.drawImage(ImageReader(img2), KENAR, _y(188), width=90 * mm,
                height=62 * mm, preserveAspectRatio=True, anchor="sw")
    x = KENAR + 96 * mm
    _hex(c, RENK.IKINCIL)
    c.setFont(FB, TIPO.BOLUM)
    c.drawString(x, _y(132), "OLASILIK BANDI")
    c.setFont(F, 8.4)
    if ctx.has_band:
        _hex(c, RENK.METIN)
        satirlar = [
            "Bu koşu hibrit (Mod C): P10–P90 bandı üretildi.",
            "Barlardaki dikey çizgiler günlük P10–P90 aralığı;",
            "profildeki gölge saatlik ortalama bandıdır.",
        ]
        if ctx.kapsama_p10_p90 is not None:
            satirlar.append(f"Holdout kapsaması: gerçekleşmelerin")
            satirlar.append(f"%{sayi_tr(ctx.kapsama_p10_p90, 1)}'i bant "
                            f"içinde (hedef ~%80).")
        if ctx.bant_pct is not None:
            satirlar.append(f"Ort. bant genişliği: P50'nin "
                            f"%{sayi_tr(ctx.bant_pct, 1)}'i.")
    else:
        _hex(c, RENK.METIN)
        satirlar = [
            f"Bu koşu {'kalibre fizik (Mod B)' if ctx.mode == 'B' else 'saf fizik (Mod A)'} modundadır;",
            "olasılıksal bant (P10–P90) yalnızca hibrit (Mod C)",
            "modda üretilir. Neden: ML bileşeni bu koşuda",
            "devrede değil — bant uydurulmaz, dürüstçe boş",
            "bırakılır (\u201c—\u201d).",
        ]
    yy = 138
    for sat in satirlar:
        c.drawString(x, _y(yy), sat)
        yy += 4.8


# ------------------------------------------------- S4: Doğruluk Karnesi
def _karne_sayfasi(c, ctx, F, FB):
    donem = ""
    kd = ctx.karne_donem
    if kd:
        donem = f"Dönem: {karne_donem_metni(kd[0], kd[1])}"
    _sayfa_ustu(c, ctx, F, FB, "Doğruluk Karnesi",
                f"{ctx.plant_name} — her tahmin ertesi gece gerçekle "
                f"karşılaştırılır", donem=donem)
    if not ctx.karne_var:
        _bilgi_yok(c, F, FB, 48,
                   "Veri eksik — gereken: gece doğrulama (skill_daily) kaydı.",
                   "SCADA gerçekleşmeleri yüklendikçe karne her gece birikir; "
                   "boş şablon basılmaz (Rapor Spesifikasyonu v2.0 kuralı).")
        return
    o0 = ctx.karne_ozet("0-24")
    o1 = ctx.karne_ozet("24-72")
    kutu_w = IC_W / 4.0
    y_et, y_num, y_alt = _y(41.5), _y(51), _y(56.5)
    kartlar = []
    if o0:
        kartlar.append((wmape_baslik(o0["gun"]),
                        f"%{sayi_tr(o0['wmape_ort'], 1)}", "",
                        "Σ|P50−gerçek| / Σgerçek", None))
    else:
        kartlar.append(("WMAPE (0-24s)", "—", "", "bu kovada kayıt yok",
                        None))
    if o1:
        kartlar.append(("WMAPE (24-72s)", f"%{sayi_tr(o1['wmape_ort'], 1)}",
                        "", f"uzak ufuk · {o1['gun']} gün", None))
    else:
        kartlar.append(("WMAPE (24-72s)", "—", "", "bu kovada kayıt yok",
                        None))
    if o0 and o0["skill_ort"] is not None:
        kartlar.append(("NAİFE ÜSTÜNLÜK", f"%{sayi_tr(o0['skill_ort'], 0)}",
                        "", "skill = 100×(1−WMAPE/naif)", RENK.MARKA))
    else:
        kartlar.append(("NAİFE ÜSTÜNLÜK", "—", "",
                        "naif referans birikimde", None))
    kg = ctx.karne_kesintisiz_gun
    kartlar.append(("KESİNTİSİZ KARNE", f"{kg}", "gün",
                    "son günden geriye ardışık", None))
    for i, k in enumerate(kartlar):
        _kart(c, F, FB, KENAR + i * kutu_w, kutu_w, y_et, y_num, y_alt,
              *k[:-1], ayrac=(i > 0), renk=k[-1])

    img = fig_to_png(fig_karne(ctx))
    c.drawImage(ImageReader(img), KENAR, _y(140), width=IC_W,
                height=76 * mm, preserveAspectRatio=True, anchor="sw")

    # ADIL ufuk kıyası — yalnız ortak günler (v2.96 duruşma dersi)
    y = 148
    ki = ctx.karne_ufuk_kiyasi()
    c.setFont(F, TIPO.GOVDE)
    if ki:
        if ki["fark"] >= 0:
            _hex(c, RENK.POZITIF)
            c.drawString(KENAR, _y(y),
                         f"Ortak ölçülen {ki['gun']} günde 0–24 s ufku, "
                         f"24–72 s'den {sayi_tr(ki['fark'], 1)} puan daha "
                         f"isabetli — ufuk uzadıkça hata büyür (beklenen).")
        else:
            _hex(c, RENK.VURGU)
            c.drawString(KENAR, _y(y),
                         f"Dikkat: ortak ölçülen {ki['gun']} günde 24–72 s "
                         f"ufku {sayi_tr(-ki['fark'], 1)} puan daha iyi — "
                         f"beklenmedik; veri/model incelemesi önerilir.")
        y += 6
    else:
        _hex(c, RENK.IKINCIL)
        c.drawString(KENAR, _y(y),
                     "Ufuk kıyası yapılmadı: iki kovanın da ölçüldüğü ortak "
                     "gün yok — farklı gün kümeleri kıyaslanmaz.")
        y += 6
    _hex(c, RENK.IKINCIL)
    c.setFont(F, TIPO.KUCUK)
    c.drawString(KENAR, _y(y),
                 "Naif referans: akıllı persistans — dün aynı saat × "
                 "berrak-gök oranı (Haurwitz). Ölçülmeyen günler karneye "
                 "katılmaz; çizgide boşluk bırakılır (—), sıfır yazılmaz.")


# ---------------------------------------------- S5: Kalibrasyon Hikayesi
def _kalibrasyon(c, ctx, F, FB):
    _sayfa_ustu(c, ctx, F, FB, "Kalibrasyon Hikayesi", ctx.plant_name,
                donem=(f"Kalibrasyon: {ctx.calibrated_at:%d.%m.%Y}"
                       if ctx.calibrated_at else ""))
    if ctx.eta_bos is None and ctx.flag_dagilimi is None:
        _bilgi_yok(c, F, FB, 48,
                   "Veri eksik — gereken: SCADA ile kalibrasyon.",
                   "Santral SCADA verisi yüklenip kalibre edildiğinde bu "
                   "sayfa katsayıları, holdout sınavını ve veri kalitesi "
                   "karnesini gösterir.")
        return
    # sol: fizik→hibrit (varsa) · sağ: flag dağılımı (varsa)
    if ctx.holdout_physics_mape_pct is not None and \
            ctx.holdout_mape_pct is not None:
        img = fig_to_png(fig_kalib(ctx))
        c.drawImage(ImageReader(img), KENAR, _y(106), width=88 * mm,
                    height=62 * mm, preserveAspectRatio=True, anchor="sw")
    else:
        _hex(c, RENK.IKINCIL)
        c.setFont(F, 8.4)
        c.drawString(KENAR, _y(52), "Fizik→hibrit kıyası: — (holdout "
                                    "sınavı bu kalibrasyonda yok)")
    if ctx.flag_dagilimi:
        img2 = fig_to_png(fig_flags(ctx))
        c.drawImage(ImageReader(img2), KENAR + 96 * mm, _y(106),
                    width=88 * mm, height=62 * mm,
                    preserveAspectRatio=True, anchor="sw")
    # holdout metodolojisi tek cümle
    _hex(c, RENK.IKINCIL)
    c.setFont(F, 8.2)
    c.drawString(KENAR, _y(113),
                 "Holdout metodu: veri kronolojik bölünür — ilk %80 eğitim, "
                 "son %20 sınav; model sınav dönemini hiç görmeden notlanır.")
    # katsayılar tablosu
    _hex(c, RENK.ZEMIN_SOLUK)
    c.roundRect(KENAR, _y(168), IC_W, 46 * mm, 6, stroke=0, fill=1)
    _hex(c, RENK.IKINCIL)
    c.setFont(FB, TIPO.BOLUM)
    c.drawString(KENAR + 4 * mm, _y(128), "BULUNAN KATSAYILAR VE SINAV")
    sol = [
        ("η_BoS (sistem verimi)",
         f"{ctx.eta_bos:.3f}" if ctx.eta_bos is not None else "—"),
        ("Bifacial kazanç (BG)",
         f"{ctx.bg:.3f}" if ctx.bg is not None else "—"),
        ("Geçerli saat", sayi_tr(ctx.n_valid_hours, 0)
         if ctx.n_valid_hours else "—"),
        ("SCADA kapsama", f"%{sayi_tr(ctx.coverage_pct, 1)}"
         if ctx.coverage_pct is not None else "—"),
    ]
    sag = [
        ("Fizik MAPE (holdout)", f"%{sayi_tr(ctx.holdout_physics_mape_pct, 1)}"
         if ctx.holdout_physics_mape_pct is not None else "—"),
        ("Hibrit MAPE (holdout)", f"%{sayi_tr(ctx.holdout_mape_pct, 1)}"
         if ctx.holdout_mape_pct is not None else "—"),
        ("İyileşme", f"%{sayi_tr(ctx.holdout_improvement_pct, 1)}"
         if ctx.holdout_improvement_pct is not None else "—"),
        ("P10–P90 kapsaması", f"%{sayi_tr(ctx.kapsama_p10_p90, 1)}"
         if ctx.kapsama_p10_p90 is not None else "—"),
    ]
    yy = 135
    for (e1, v1), (e2, v2) in zip(sol, sag):
        c.setFont(F, 8)
        _hex(c, RENK.IKINCIL)
        c.drawString(KENAR + 4 * mm, _y(yy), e1)
        c.drawString(KENAR + IC_W / 2 + 2 * mm, _y(yy), e2)
        c.setFont(FB, 8.5)
        _hex(c, RENK.METIN)
        c.drawString(KENAR + 44 * mm, _y(yy), v1)
        c.drawString(KENAR + IC_W / 2 + 44 * mm, _y(yy), v2)
        yy += 6.2
    # uyarılar
    uyarilar = (ctx.warnings or [])[:4]
    yy = 176
    _hex(c, RENK.IKINCIL)
    c.setFont(FB, TIPO.BOLUM)
    c.drawString(KENAR, _y(yy), "KALİBRASYON NOTLARI")
    yy += 6
    c.setFont(F, TIPO.GOVDE)
    if not uyarilar:
        _hex(c, RENK.POZITIF)
        n = ctx.n_valid_hours
        c.drawString(KENAR, _y(yy),
                     f"\u2713 Veri kalitesi başarılı — {sayi_tr(n, 0)} "
                     f"geçerli saat işlendi." if n else
                     "\u2713 Kalibrasyon temiz — uyarı yok.")
    else:
        for u in uyarilar:
            _hex(c, RENK.VURGU)
            c.rect(KENAR, _y(yy), 2.2, 2.2, stroke=0, fill=1)
            _hex(c, RENK.METIN)
            c.drawString(KENAR + 4 * mm, _y(yy + 0.4),
                         u if len(u) <= 118 else u[:115] + "…")
            yy += 5.2


# ------------------------------------------------- S6: İklim Bağlamı
def _iklim(c, ctx, F, FB):
    _sayfa_ustu(c, ctx, F, FB, "İklim Bağlamı", ctx.plant_name)
    if ctx.iklim is None and ctx.son12 is None:
        _bilgi_yok(c, F, FB, 48,
                   "Veri eksik — gereken: iklim beklentisi hesabı.",
                   "Worker'ın aylık iklim işi koştuğunda 20 yıllık GHI "
                   "zarfı ve gerçekleşen üretim karşılaştırması burada "
                   "görünür.")
        return
    if ctx.iklim is not None:
        img = fig_to_png(fig_iklim_zarf(ctx))
        c.drawImage(ImageReader(img), KENAR, _y(112), width=90 * mm,
                    height=68 * mm, preserveAspectRatio=True, anchor="sw")
    else:
        _hex(c, RENK.IKINCIL)
        c.setFont(F, 8.4)
        c.drawString(KENAR, _y(52), "GHI zarfı: — (iklim hesabı yok)")
    if ctx.son12 is not None:
        img2 = fig_to_png(fig_son12(ctx))
        c.drawImage(ImageReader(img2), KENAR + 96 * mm, _y(112),
                    width=90 * mm, height=68 * mm,
                    preserveAspectRatio=True, anchor="sw")
    else:
        _hex(c, RENK.IKINCIL)
        c.setFont(F, 8.4)
        c.drawString(KENAR + 96 * mm, _y(52),
                     "Son 12 ay üretim: — (geçerli SCADA yok)")
    _hex(c, RENK.IKINCIL)
    c.setFont(F, 8.2)
    notlar = [
        "Zarf, santral konumu için son 20 yılın aylık GHI dağılımıdır "
        "(uydu türevli ışınım arşivi): P50 tipik yıl, bant yıllar-arası değişkenlik.",
        "Bu ayın aktüel GHI konumu: — (aylık aktüel ışınım arşivi "
        "tutulmuyor; üretim karşılaştırması sağdaki grafiktedir).",
        "Sağdaki barlar yalnız \u2018geçerli\u2019 bayraklı SCADA "
        "saatlerinden toplanır; ölçülmeyen aylar dürüstçe boş kalır.",
    ]
    yy = 122
    for n in notlar:
        c.drawString(KENAR, _y(yy), n)
        yy += 5
    if ctx.son_scada_ts is not None:
        c.drawString(KENAR, _y(yy),
                     f"Son SCADA kaydı: {ctx.son_scada_ts:%d.%m.%Y %H:%M} "
                     f"UTC — bu tarihten sonrası ölçülmemiştir.")


# --------------------------------------------- S7: Metodoloji & Künye
def _metodoloji(c, ctx, F, FB):
    _sayfa_ustu(c, ctx, F, FB, "Metodoloji ve Künye", ctx.plant_name)
    # model zinciri diyagramı — 4 kutu + oklar
    kutular = ["profesyonel\nhava tahmini", "pvlib fizik\nPOA + güç",
               "SCADA\nkalibrasyon", "ML hibrit\nartık düzeltme"]
    kw, kh, bosluk = 38 * mm, 14 * mm, 8 * mm
    x0 = KENAR + (IC_W - (4 * kw + 3 * bosluk)) / 2
    for i, k in enumerate(kutular):
        x = x0 + i * (kw + bosluk)
        aktif = not (i == 3 and ctx.mode != "C") and \
            not (i == 2 and ctx.mode == "A")
        _hex(c, RENK.MARKA if aktif else RENK.CIZGI)
        c.setLineWidth(1.1)
        c.roundRect(x, _y(56), kw, kh, 4, stroke=1, fill=0)
        _hex(c, RENK.METIN if aktif else RENK.IKINCIL)
        for j, sat in enumerate(k.split("\n")):
            c.setFont(FB if j == 0 else "PVQ", 8.2 if j == 0 else 7.2)
            c.drawCentredString(x + kw / 2, _y(48.5 + j * 4.2), sat)
        if i < 3:
            _hex(c, RENK.IKINCIL)
            c.setFont("PVQ", 10)
            c.drawCentredString(x + kw + bosluk / 2, _y(50.5), "\u2192")
    if ctx.mode != "C":                     # yalniz soluk kutu VARSA
        _hex(c, RENK.IKINCIL)
        c.setFont(F, 7.6)
        c.drawCentredString(SAYFA_W / 2, _y(61.5),
                            "soluk kutular bu koşuda devrede değil")

    def bolum(y0, baslik, satirlar, fnt=8.2, adim=4.9):
        _hex(c, RENK.IKINCIL)
        c.setFont(FB, TIPO.BOLUM)
        c.drawString(KENAR, _y(y0), baslik)
        _hex(c, RENK.METIN)
        c.setFont(F, fnt)
        yy = y0 + 6
        for sat in satirlar:
            c.drawString(KENAR, _y(yy), sat)
            yy += adim
        return yy

    y = bolum(72, "STANDARTLAR VE KAYNAKLAR", [
        "IEC 61724-1 (PV sistem performansı: özgül verim, kapasite faktörü, veri erişilebilirliği) · IEA-PVPS T13 (P50/P90 aşılma olasılıkları).",
        _kunye_satiri(),   # v2.270: künye sayfası — kaynak adı + lisans (Anayasa v2.245 istisnası)
        "Naif referans: akıllı persistans — dün-aynı-saat üretimi, berrak-gök oranıyla (Haurwitz) ölçeklenir.",
    ])
    y = bolum(y + 3, "KISA SÖZLÜK", [
        "P50 / P90 — %50 / %90 olasılıkla aşılacak üretim.  ·  WMAPE — Σ|tahmin−gerçek| / Σgerçek (üretim ağırlıklı hata).",
        "Holdout — kronolojik son %20 sınav bölmesi; model görmeden notlanır.  ·  Skill — 100×(1−WMAPE/WMAPE_naif).",
        "η_BoS — panel sonrası sistem verimi (invertör, kablo, kirlilik).  ·  BG — bifacial (çift yüzey) kazancı.",
    ])
    # künye
    _hex(c, RENK.ZEMIN_SOLUK)
    kutu_h = 34
    c.roundRect(KENAR, _y(y + 8 + kutu_h), IC_W, kutu_h * mm, 6,
                stroke=0, fill=1)
    _hex(c, RENK.IKINCIL)
    c.setFont(FB, TIPO.BOLUM)
    c.drawString(KENAR + 4 * mm, _y(y + 14), "SANTRAL VE MODEL KÜNYESİ")
    sol = [
        ("Kurulu güç", f"{sayi_tr(ctx.capacity_kwp, 0)} kWp"),
        ("Konum", f"{ctx.latitude:.2f}, {ctx.longitude:.2f}"),
        ("Eğim / Azimut", f"{ctx.tilt_deg:.0f}° / {ctx.azimuth_deg:.0f}°"),
        ("Saat dilimi", ctx.plant_tz),
    ]
    sag = [
        ("Model", f"{ctx.model_name} ({ctx.model_version})"),
        ("Meteo kaynağı", ctx.meteo_source),
        ("η_BoS / BG",
         f"{ctx.eta_bos:.3f} / {ctx.bg:.3f}"
         if ctx.eta_bos is not None else "—"),
        ("Şema", f"v{ctx.schema_version}"),
    ]
    yy = y + 20
    for (e1, v1), (e2, v2) in zip(sol, sag):
        c.setFont(F, 7.5)
        _hex(c, RENK.IKINCIL)
        c.drawString(KENAR + 4 * mm, _y(yy), e1)
        c.drawString(KENAR + IC_W / 2 + 2 * mm, _y(yy), e2)
        c.setFont(FB, 8)
        _hex(c, RENK.METIN)
        c.drawString(KENAR + 32 * mm, _y(yy), v1)
        c.drawString(KENAR + IC_W / 2 + 30 * mm, _y(yy), v2)
        yy += 5.4
    _hex(c, RENK.IKINCIL)
    c.setFont(F, TIPO.KUCUK)
    c.drawString(KENAR, _y(yy + 8),
                 "Hukuki not: Bu rapor bir üretim tahminidir; garanti değildir. "
                 "Metrik tanımları ve olasılık dili yukarıdaki standartlara dayanır.")


# ---------------------------------------------------- S8: Koşu Arşivi
def _arsiv(c, ctx, F, FB):
    _sayfa_ustu(c, ctx, F, FB, "Koşu Arşivi",
                f"{ctx.plant_name} — koşular güncellenmez, eklenir")
    if ctx.kosu_evrim is None or len(ctx.kosu_evrim) < 2:
        _bilgi_yok(c, F, FB, 48,
                   "Veri eksik — gereken: aynı günü kapsayan en az 2 koşu.",
                   "Tahminler koşudan koşuya arşivlenir; hedef günü kapsayan "
                   "ikinci koşu doğduğunda evrim grafiği burada görünür — "
                   "boş şablon basılmaz.")
        return
    img = fig_to_png(fig_kosu_evrim(ctx))
    c.drawImage(ImageReader(img), KENAR, _y(118), width=IC_W,
                height=74 * mm, preserveAspectRatio=True, anchor="sw")
    ev = ctx.kosu_evrim["p50_mwh"]
    fark = float(ev.iloc[-1] - ev.iloc[0])
    _hex(c, RENK.METIN)
    c.setFont(F, TIPO.GOVDE)
    c.drawString(KENAR, _y(126),
                 f"{gun_tr(ctx.evrim_gunu)} günü için P50, ilk koşudan bu "
                 f"yana {sayi_tr(abs(fark), 1)} MWh "
                 f"{'yükseldi' if fark >= 0 else 'düştü'} — hedef gün "
                 f"yaklaştıkça hava tahmini netleşir, tahmin oturur.")
    _hex(c, RENK.IKINCIL)
    c.setFont(F, TIPO.KUCUK)
    c.drawString(KENAR, _y(132),
                 "Her nokta bağımsız bir koşunun o gün için toplam P50 "
                 "tahminidir; koşular üzerine yazılmaz (denetlenebilir arşiv).")
