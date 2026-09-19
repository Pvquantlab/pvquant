"""PVQuant rapor stil katmanı — renk ve Türkçe biçim yardımcıları.

Tasarım dili: beyaz zemin, tek marka rengi (petrol yeşili), disiplinli
nötr griler, amber yalnız vurguda.

v2.344 (E.4): reportlab/matplotlib katmanı (TIPO, dejavu_yollari,
pdf_fontlarini_kaydet, tema_uygula) EMEKLİ — eski yönetici-özeti PDF'i
(pdf.py + charts.py) 16 sayfalık HTML motorunun seçkisiyle değiştirildi;
tarih git'te. Kalanlar Excel/JSON ve panel metinlerinin ortak kaynağıdır.
"""
from __future__ import annotations


class RENK:
    METIN = "#111827"
    IKINCIL = "#6B7280"
    CIZGI = "#E5E7EB"
    ZEMIN_SOLUK = "#F8FAFC"
    MARKA = "#0F6E56"
    VURGU = "#F59E0B"
    POZITIF = "#15803D"
    NEGATIF = "#B91C1C"
    GECE = "#F3F4F6"


# ---------------------------------------------------------------- Türkçe format
AYLAR_TR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
            "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]


def sayi_tr(x: float, ondalik: int = 1) -> str:
    """Türkçe sayı biçimi: binlik ayracı nokta, ondalık virgül.
    4514 -> '4.514' · 218.9 -> '218,9' · 1234.5 -> '1.234,5'
    (Önceki tek-replace yaklaşımı binlikli ondalıklarda '1.234.5'
    üretiyordu — bu yardımcı o hata sınıfını kapatır.)"""
    metin = f"{x:,.{ondalik}f}"
    return metin.replace(",", "\u00a7").replace(".", ",").replace("\u00a7", ".")


BANT_BASLIK = "P10-P90 (kWh)"       # v2.71-B: baslik ile hucre tek kaynakta


def bant_araligi(alt: float, ust: float) -> str:
    """P10-P90 bandinin hucre metni - sira BANT_BASLIK ile ayni.

    v2.71-B: onceki halinde baslik tahminler.py'de 'P90-P10' yaziyor,
    hucre ise P10 -> P90 sirasiyla basiliyordu (ekranda P50=30.356 iken
    '29.076 - 33.287'). Iki yer ayri tanimliydi; ikisi de buradan gelir.
    """
    return f"{sayi_tr(alt, 0)} - {sayi_tr(ust, 0)}"


def egim_azimut_metni(tilt, azimuth=None) -> str:
    """Egim/azimut ciftinin ekran metni - gercekte kullanilani soyler.

    v2.46 bunu Kalibrasyon sayfasinda duzeltmisti; Santralim kunyesi
    atlanmisti ve orada "model buldu" yaziyordu. Model egimi FIT ETMIYOR
    (fit_tilt/fit_azimuth kapali) - bos kayitta varsayilan kullanilir.
    v2.71-C: iki sayfa da bu tek metinden okur.

    Not: azimuth=0 (kuzey) gecerli bir degerdir; 'or 180' tuzagina
    dusmemek icin acikca None kontrolu yapilir.
    """
    if tilt is None:
        return "20° / 180° (varsayılan)"
    az = 180 if azimuth is None else azimuth
    return (f"{sayi_tr(tilt, 0)}° / {sayi_tr(az, 0)}°"
            " (santral kaydı)")


def ufuk_alt_yazisi(saat: int) -> str:
    """Tahminler sayfasinin alt yazisi - secili ufku soyler.

    v2.71-D: cumle '168 saatlik ...' diye sabit yazilmisti; v2.69 ufku
    384 saate cikarinca 16g sekmesinde de 168 diyordu. Sabit metin
    yalniz 7g sekmesinde dogruydu.
    """
    return f"{saat} saatlik kalibre üretim tahmini — arşivden, son koşu."


def donem_tr(t1, t2) -> str:
    """Dönem metni, Türkçe ay adlarıyla:
    aynı ay  -> '14 – 21 Temmuz 2026'
    ay geçişi-> '14 Temmuz – 3 Ağustos 2026'
    yıl geçişi-> '28 Aralık 2026 – 3 Ocak 2027'"""
    a1, a2 = AYLAR_TR[t1.month - 1], AYLAR_TR[t2.month - 1]
    if t1.year == t2.year and t1.month == t2.month:
        return f"{t1.day} – {t2.day} {a1} {t1.year}"
    if t1.year == t2.year:
        return f"{t1.day} {a1} – {t2.day} {a2} {t1.year}"
    return f"{t1.day} {a1} {t1.year} – {t2.day} {a2} {t2.year}"


def wmape_baslik(gun_sayisi: int) -> str:
    """Karne WMAPE kartinin basligi - kac gun ortalandigini soyler.

    v2.71-E: baslik '30 GUN ORT.' diye sabitti. Sorgu penceresi ise
    v2.14'te 120 gune cikarilmisti ve gercekte kac gun ortalandigi
    hicbir yerde yazmiyordu (Konya'da 4 gun vardi, kart 30 diyordu).
    """
    if gun_sayisi <= 0:
        return "WMAPE (0-24s)"
    return f"WMAPE (0-24s, {gun_sayisi} GÜN ORT.)"


def karne_donem_metni(ilk, son) -> str:
    """Karnenin kapsadigi donem - tek gunse tek tarih yazar.

    v2.71-E: sayfa "her gece karsilastirilir" diyordu ama hangi tarihleri
    kapsadigini soylemiyordu. Konya SCADA'si 30 Nis'te bittigi icin
    Temmuz'da bakan biri Nisan verisini guncel saniyordu.
    """
    if ilk == son:
        return f"{ilk.day} {AYLAR_TR[ilk.month - 1]} {ilk.year}"
    return donem_tr(ilk, son)


def model_gorunur_adi(ham: str) -> str:
    """v2.292 — müşteri yüzünde ham model adı geçmez (tasarım anayasası): PDF/Excel
    künyesi operatör diliyle yazar; JSON dışa aktarımı makine adını korur."""
    return {"barhdadi_bennis": "PVQuant fizik boru hattı"}.get(ham, ham)
