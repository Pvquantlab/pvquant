"""v2.518 (P3a) — Piyasa ve mevzuat takvimi (SAF: veritabanı yok, pandas yok).

Kaynaklar (araştırma: ~/Desktop/PVQuant_GES_Sahibi_Ihtiyac_Arastirmasi, bulgular 02-01…02-16, 03-04, 03-10, 03-12, 03-17, 08-01, 08-11,
08-14, 08-15): DUY m.81(1), m.132, m.132/A–E, m.133 (sayaç, uzlaştırma, fatura, avans, teminat, itiraz); LÜY m.23(3), m.25(1)(e), m.26(7)
(lisanssızda GTŞ ödemesi); YEK Yön. m.5–7 (YEKDEM yıllık takvimi); EPDK Kurul Kararı 5905-27 (YEKDEM süreleri); 7189 sayılı CK Ek-1
(30.6.2021 sonrası: 10 yıl YEK fiyatı, 5 yıl yerli katkı); Lisans Yön. m.26(2) (sona erdirme için −6 ay), m.47 (sigorta); Lisans Yön.
m.43 ve 03-03 (YEK'te kabulden sonraki ilk 8 yıl lisans bedeli alınmaz); EPİAŞ «Teminat Usul ve Esasları Kapsamındaki Süreçler»
(10:30 / 11:00 / 16:30 / 17:00); TEİAŞ ESY (planlı devre dışı 30 Nisan; devreye alma tahmini iş günü 11:00).

Her olay bir «kaynak_turu» taşır: «mevzuat» (metinde yazılı gün/saat), «hesaplanan» (iş günü kaydırması ya da gün ekleme hesabı),
«duyuru» (EPİAŞ/EPDK'nın fiilî yayım kalıbı), «kunye» (müşterinin Santral tarihleri formuna girdiği tarih ya da ondan türeyen).
«kaydirma»: «is_gunu» (metin hafta sonu/tatilde izleyen iş gününe kaydırır), «yok» (takvim günü; yayım hafta sonu da yapılıyor — 02-02 —
ya da yükümlülük şebeke işletmecisinin/EPDK'nın), «belirsiz» (müşterinin son tarihi; metinde hafta sonu kuralı yok — m.132/B(1) 12'si ve
14'ü, m.132/C(1) 7 gün, m.133(1) 60 gün). Tarihler EPİAŞ duyurusuyla değişebilir; panel bunu yazar.

Görünür metin kuralı (01.11 incelemesi): «kaynak» ve «ad» alanları panelde okunur; araştırma bulgu numaraları (02-02, 03-10 …) yalnız bu
docstring'de ve kod yorumlarında kalır, kaynak metnine yazılmaz (tests/test_takvim.py bekçisi).
"""
from __future__ import annotations

from datetime import date, timedelta
import calendar
from pvquant.ext.turkiye import kunye as _kunye   # v2.535: dayanak künyesi sicili
# v2.535 dayanak künyeleri [DUY, LISANS, LUY, YEK_YON, 5346, 6446, SEBEKE, 2429, KARAR_14907, KARAR_14911, AYM, TPYS, GIP_KAPI, CK2949, CK7189, KARAR_5905] — bu dosyadaki madde atıflarının birincil yayımı (RG tarih-sayı, karar no); metin kunye.py sicilinden üretildi,
# tests/test_kunye_bekcisi.py sicille eş tutar (kaynak: 03.11.2026 doğrulama arşivi 03_Kaynak_Envanteri).
DAYANAK_KUNYELERI = (
    'DUY: Elektrik Piyasası Dengeleme ve Uzlaştırma Yönetmeliği, RG 14.04.2009-27200; değişiklikler RG 28.03.2015-29309, 30.10.2016-29873, 18.01.2018-30305, 09.08.2019-30857, 02.02.2020-31027, 19.11.2022-32018, 19.12.2023-32404, 17.12.2024-32755, 21.01.2025-32789, 29.12.2025-33122, 19.10.2026-33405, 21.10.2026-33407; '
    'Lisans Yön.: Elektrik Piyasası Lisans Yönetmeliği, RG 02.11.2013-28809; değişiklikler RG 24.02.2017-29989, 10.03.2022-31774, 17.12.2024-32755, 29.04.2026-33238, 19.10.2026-33405; '
    'LÜY: Elektrik Piyasasında Lisanssız Elektrik Üretim Yönetmeliği, RG 12.05.2019-30772; değişiklikler RG 09.05.2021-31479, 02.04.2026-33212, 19.10.2026-33405; '
    'YEK Yön.: Yenilenebilir Enerji Kaynaklarının Belgelendirilmesi ve Desteklenmesine İlişkin Yönetmelik, RG 01.10.2013-28782; değişiklikler RG 29.04.2016-29698 (m.16–17 mülga), 23.08.2019-30867, 19.08.2021-31573, 29.12.2025-33122, 19.10.2026-33405 (m.23(6)); '
    '5346: 5346 sayılı Yenilenebilir Enerji Kaynaklarının Elektrik Enerjisi Üretimi Amaçlı Kullanımına İlişkin Kanun, RG 18.05.2005-25819; '
    '6446: 6446 sayılı Elektrik Piyasası Kanunu, RG 30.03.2013-28603; m.16 idari para cezası tebliğleri RG 27.11.2025-33090, 25.12.2025-33118; '
    'Şebeke Yön.: Elektrik Şebeke Yönetmeliği, RG 28.05.2014-29013 (mükerrer); son değişiklik RG 29.12.2025-33122; '
    '2429: 2429 sayılı Ulusal Bayram ve Genel Tatiller Hakkında Kanun, RG 19.03.1981-17284; '
    'Karar 14907: EPDK Kurul Kararı 14907 (KÜPST, 1.11.2026 çıkarım), RG 19.10.2026-33405; '
    'Karar 14911: EPDK Kurul Kararı 14911 (DUY m.110 V = 100 TL/MWh), RG 19.10.2026-33405; '
    'AYM 2024/133: Anayasa Mahkemesi 26.11.2025, E.2024/133 K.2025/233 (5346 m.6(2) kısmi iptal; yürürlük 10.12.2026), RG 10.03.2026-33192; '
    'TPYS Bildirim Dokümanı: EPİAŞ TPYS Bildirim Dokümanı (EAK ve KGÜP), duyuru 19.02.2025 (ek 648549); KGUP.csv / EAK.csv şablonları 28.02.2018; dayanak DUY RG 17.12.2024-32755; '
    "GİP kapı kapanışı: DUY m.66/A(1)(f) yetkisiyle EPİAŞ duyurusu 28.08.2018 (01.10.2018'den teslimattan 60 dk önce); KGÜP revizyonu kapanış + 30 dk DUY m.69(1); "
    'CK 2949: 2949 sayılı Cumhurbaşkanı Kararı (1.1–30.6.2021 işletmeye girenler), RG 18.09.2020-31248; '
    '7189 sayılı CK: 7189 sayılı Cumhurbaşkanı Kararı (1.7.2021–31.12.2030 işletmeye girecek YEK belgeli tesisler), RG 01.05.2023-32177; düzeltme RG 04.05.2023-32180; '
    "Karar 5905-27: EPDK Kurul Kararı 5905-27 (02.12.2015; YEKDEM yararlanma yılları) — EPDK listesi, RG'de yayımlanmaz"
)

# ---- segment kapsamları (ext/turkiye/segment.Segment değerleri; burada metin olarak, bağımlılık yok) ----
LISANSLI = ("lisansli_serbest", "lisansli_yekdem", "yeka")
LISANSSIZ = ("lisanssiz_iletim", "lisanssiz_dagitim", "oz_tuketim_saatlik")
KGUP_BILDIREN = LISANSLI + ("lisanssiz_iletim",)          # 03 tablosu: iletime bağlı lisanssız da bildirir; dağıtımda GTŞ/toplayıcı
UZLASTIRMA_TARAFI = LISANSLI                              # EPİAŞ uzlaştırma bildirimi/faturası doğrudan katılımcıya (lisanslı)
# v2.535 Takvim doğrulama turu (DK-784, DK-540): iletime bağlı lisanssız da GTŞ/toplayıcı portföyündedir (DUY m.75(4), segment.KURALLAR
# «dengesizlik_sahibi: toplayıcı/GTŞ portföyü») — EPİAŞ itiraz/fatura son günleri ona gösterilmez; ödeme GTŞ'den.
GTS_ODEME = LISANSSIZ                                        # LÜY: ödeme GTŞ'den, izleyen ayın 5. iş günü
HEPSI = LISANSLI + LISANSSIZ

# ---- resmî tatiller ----
# 2429 sayılı Ulusal Bayram ve Genel Tatiller Hakkında Kanun: sabit günler (28 Ekim öğleden sonra ve arifeler yarım gün → iş günü sayılır).
SABIT_TATIL = ((1, 1), (4, 23), (5, 1), (5, 19), (7, 15), (8, 30), (10, 29))
# Dinî bayramlar Diyanet takvimine göre; her yıl başında doğrulanır (yeni yıl eklenmezse o yılın bayramları iş günü sayılır — not panelde).
DINI_BAYRAM = {
    2026: (date(2026, 3, 20), date(2026, 3, 21), date(2026, 3, 22),                       # Ramazan Bayramı
           date(2026, 5, 27), date(2026, 5, 28), date(2026, 5, 29), date(2026, 5, 30)),   # Kurban Bayramı
    2027: (date(2027, 3, 9), date(2027, 3, 10), date(2027, 3, 11),
           date(2027, 5, 16), date(2027, 5, 17), date(2027, 5, 18), date(2027, 5, 19)),
    # v2.541: Diyanet «2028 Dinî Günler Listesi» (vakithesaplama.diyanet.gov.tr/icerik.php?icerik=185; 05.11.2026 okundu): Ramazan Bayramı 26–28 Şubat 2028
    # (arife 25 Şubat Cuma), Kurban Bayramı 5–8 Mayıs 2028 (arife 4 Mayıs Perşembe). 2027 aynı kaynakta (icerik=154) teyit edildi.
    2028: (date(2028, 2, 26), date(2028, 2, 27), date(2028, 2, 28),
           date(2028, 5, 5), date(2028, 5, 6), date(2028, 5, 7), date(2028, 5, 8)),
}
TATIL_KAYNAK = "Resmî tatiller: 2429 sayılı Kanun (sabit günler) ve Diyanet dinî günler listesi (vakithesaplama.diyanet.gov.tr); yarım günler iş günü sayıldı."


def resmi_tatil(d: date) -> bool:
    return (d.month, d.day) in SABIT_TATIL or d in DINI_BAYRAM.get(d.year, ())


def is_gunu(d: date) -> bool:
    return d.weekday() < 5 and not resmi_tatil(d)


def is_gununa_kaydir(d: date) -> date:
    """Hafta sonu ya da resmî tatilse izleyen ilk iş günü (DUY m.132/A(1) kalıbı)."""
    while not is_gunu(d):
        d += timedelta(days=1)
    return d


def is_gunu_ekle(d: date, n: int) -> date:
    """d'den sonraki n'inci iş günü (d sayılmaz): tebliğ + 6. iş günü (m.132/Ç(8)) gibi."""
    k = 0
    while k < n:
        d += timedelta(days=1)
        if is_gunu(d):
            k += 1
    return d


def ay_ekle(d: date, n: int) -> date:
    """Takvim ayı ekle/çıkar; gün ay sonunu aşarsa ay sonuna kırp (ortaklık değişikliği + 6 ay, izin iptali + 2 ay)."""
    y, m = divmod(d.month - 1 + n, 12)
    y += d.year; m += 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def yil_ekle(d: date, n: int) -> date:
    try:
        return d.replace(year=d.year + n)
    except ValueError:        # 29 Şubat
        return d.replace(year=d.year + n, day=28)


ISLEMLER = ("islem", "takip", "mevzuat", "dogrulama")   # işlem gerekli (santralin adımı) / takip edilmeli (başkasının adımı) / mevzuat değişikliği / doğrulama gerekli (koşullu)
ISLEM_ETIKET = {"islem": "işlem gerekli", "takip": "takip edilmeli", "mevzuat": "mevzuat değişikliği", "dogrulama": "doğrulama gerekli"}


def _olay(kod, ad, tarih, *, saat=None, kaynak, kaynak_turu, kaydirma="yok", kapsam=HEPSI, donem=None, not_=None, sonuc=None, sonuc_kisa=None,
          islem="takip", sorumlu=None) -> dict:
    """`sonuc` (v2.524, P3b): yükümlülük kaçırılınca ne olur — ilgili bent/madde ve ihtar süresi; eşleme Kurul takdirine bağlıysa «çıkarım» yazar. Tutar yok
    (yıllık tebliğ; 2027 tutarları yok). `islem`: santralin yapacağı iş mi (islem), başkasının adımı mı (takip), mevzuat değişikliği mi, koşulu
    doğrulanmamış mı (dogrulama). `sorumlu`: adımı yapan taraf (santral / EPİAŞ / EPDK / TEİAŞ / şebeke işletmecisi / GTŞ / Kurul)."""
    assert islem in ISLEMLER
    return {"kod": kod, "ad": ad, "tarih": tarih.isoformat(), "saat": saat, "kaynak": kaynak, "kaynak_turu": kaynak_turu,
            "dayanak": [d["kunye"] for d in _kunye.bul(kaynak)],   # v2.535: kaynak metnindeki anılışların birincil künyesi (RG tarih-sayı)
            "kaydirma": kaydirma, "kapsam": list(kapsam), "donem": donem, "not": not_, "sonuc": sonuc, "sonuc_kisa": sonuc_kisa,
            "islem": islem, "sorumlu": sorumlu, "hafta_sonu": tarih.weekday() >= 5, "tatil": resmi_tatil(tarih)}


# ---- aylık uzlaştırma / fatura / nakit takvimi (fatura dönemi = takvim ayı; olaylar izleyen ayda) ----
def donem_takvimi(yil: int, ay: int) -> list[dict]:
    """Fatura dönemi (yil, ay) için DUY m.132 zinciri. 02-01 doğrulaması: Ekim 2026 → 11.11, 12.11 17:30, 16.11 (15'i Pazar), 24.11, 25.11;
    Kasım 2026 → 11.12, 12.12 Cumartesi (belirsiz), 15.12, 23.12, 24.12."""
    donem = f"{yil:04d}-{ay:02d}"
    ny, nm = (yil + 1, 1) if ay == 12 else (yil, ay + 1)
    g = lambda d: date(ny, nm, d)   # noqa: E731
    nihai_metin = g(15); nihai = is_gununa_kaydir(nihai_metin)
    on = g(11); itiraz = g(12)
    olaylar = [
        _olay("sayac_veri", "Sayaç değerlerinin PYS'ye aktarımı (şebeke işletmecisi; üretici kontrol eder)", g(10),
              kaynak="DUY m.81(1): dönem sonunu izleyen ilk 10 gün", kaynak_turu="mevzuat", kapsam=HEPSI, donem=donem, islem="takip", sorumlu="şebeke işletmecisi"),
        _olay("on_bildirim", "Ön uzlaştırma bildirimi (itiraz penceresi açılır)", on,
              kaynak="DUY m.132/A(1): en geç ayın 11'i; EPİAŞ hafta sonu da yayımlıyor (Eylül 2026 dönemi: 11.10.2026 Pazar)", kaynak_turu="mevzuat", kaydirma="yok",   # 02-02
              kapsam=UZLASTIRMA_TARAFI, donem=donem, islem="takip", sorumlu="EPİAŞ"),
        _olay("itiraz_son", "Ön bildirime itiraz ve sayaç verisi düzeltme son anı", itiraz, saat="17:30",
              kaynak="DUY m.132/B(1); m.82(4): ayın 12'si 17:30; itiraz sayaç okuyan kurum / yardim.epias.com.tr üzerinden",
              kaynak_turu="mevzuat", kaydirma="belirsiz", kapsam=UZLASTIRMA_TARAFI, donem=donem, islem="islem", sorumlu="santral",
              sonuc="Bu andan sonra gelen sayaç düzeltmesi ve itiraz o ayın uzlaştırmasına girmez (DUY m.82(4), m.132/B(1)); sonrası 60 günlük fatura itirazı (m.133)",
              sonuc_kisa="Düzeltme o aya girmez (m.82(4))",
              not_=("Hafta sonuna denk geliyor; metinde kaydırma kuralı yok. EPİAŞ geçmiş dönemlerde 12'si 17:30'u kaydırmadan uyguladı "
                    "(12.07.2025 Cumartesi, 12.04.2026 Pazar); o ayın duyurusuna bakın.") if itiraz.weekday() >= 5 else None),
        _olay("itiraz_sonuc", "EPİAŞ itirazları sonuçlandırır", g(14), saat="16:00",
              kaynak="DUY m.132/B(1): ayın 14'ü 16:00", kaynak_turu="mevzuat", kaydirma="belirsiz", kapsam=UZLASTIRMA_TARAFI, donem=donem, islem="takip", sorumlu="EPİAŞ"),
        _olay("nihai_bildirim", "Nihai uzlaştırma bildirimi = fatura tebliği", nihai,
              kaynak="DUY m.132/A(1), m.132/C(1): ayın 15'i; hafta sonu/tatilde izleyen iş günü",
              kaynak_turu="hesaplanan" if nihai != nihai_metin else "mevzuat", kaydirma="is_gunu", kapsam=UZLASTIRMA_TARAFI, donem=donem, islem="takip", sorumlu="EPİAŞ",
              not_=f"15'i {['Pazartesi','Salı','Çarşamba','Perşembe','Cuma','Cumartesi','Pazar'][nihai_metin.weekday()]}; izleyen iş gününe kaydırıldı." if nihai != nihai_metin else None),
        _olay("fatura_duzenleme", "Fatura düzenleme son günü (alacaklıysa EPİAŞ'a kesilecek fatura)", nihai + timedelta(days=7),
              kaynak="DUY m.132/C(1), (5): nihai bildirimden itibaren 7 gün; hafta sonu kuralı yazılı değil", kaynak_turu="hesaplanan", kaydirma="belirsiz",
              kapsam=UZLASTIRMA_TARAFI, donem=donem, islem="islem", sorumlu="santral", not_="Yalnız dönem sonucu alacaklıysa.",
              sonuc="Sonuç metinde yazılı değil; fatura gecikirse EPİAŞ ödemesi gecikebilir (çıkarım, m.132/Ç(14))", sonuc_kisa="Ödeme gecikebilir (çıkarım)"),
        _olay("borc_odeme", "Borçlu katılımcının fatura ödemesi (6. iş günü; sonrası temerrüt, teminat mahsubu)", is_gunu_ekle(nihai, 6),
              kaynak="DUY m.132/Ç(8), m.132/E(1): tebliği izleyen 6. iş günü", kaynak_turu="hesaplanan", kapsam=UZLASTIRMA_TARAFI, donem=donem, islem="islem", sorumlu="santral",
              not_="Yalnız dönem sonucu borçluysa.", sonuc="DUY m.132/E: temerrüt faizi (6183 m.51 oranı) ve teminattan mahsup (m.132/D)", sonuc_kisa="Temerrüt + teminat mahsubu (m.132/E)"),
        _olay("alacak_tahsil", "EPİAŞ'ın alacaklıya ödemesi (en geç 7. iş günü; tahsilat oranında)", is_gunu_ekle(nihai, 7),
              kaynak="DUY m.132/Ç(9): tebliği izleyen 7. iş günü içinde; tahsil edilen tutarların net alacaklara oranına göre",
              kaynak_turu="hesaplanan", kapsam=UZLASTIRMA_TARAFI, donem=donem, islem="takip", sorumlu="EPİAŞ"),
        _olay("itiraz_60", "Faturaya yazılı itiraz süresi sonu (60 gün; ödemeyi durdurmaz)", nihai + timedelta(days=60),
              kaynak="DUY m.133(1)–(2): tebliğden itibaren 60 gün, yazılı; ölçüm itirazı TEİAŞ/dağıtıma, lisanssız üreticiye ödenecek toplam bedel (LÜYTOB) itirazı GTŞ'ye, diğerleri EPİAŞ'a; hafta sonu kuralı yazılı değil",
              kaynak_turu="hesaplanan", kaydirma="belirsiz", kapsam=UZLASTIRMA_TARAFI, donem=donem, islem="takip", sorumlu="santral",
              not_="İsteğe bağlı hak: yalnız faturaya itiraz edilecekse; zorunlu adım değildir. Geriye dönük düzeltme talebi m.133(5) ile 12 ayla sınırlıdır.",
              sonuc="60 günlük itiraz süresi biter (m.133(1)); m.133(5) 12 aylık geriye dönük düzeltme kuralı ayrıca", sonuc_kisa="60 günlük süre biter (m.133(1))"),
        # lisanssız (dağıtım): şebeke işletmecisi → GTŞ bildirimi ve GTŞ ödemesi
        _olay("gts_bildirim", "Şebeke işletmecisi ihtiyaç fazlasını GTŞ'ye bildirir", g(6),
              kaynak="LÜY m.23(3): her ayın 6'sına kadar (12.05.2019 öncesi tesisler); sonrası için m.26(2) düzenlenmiş takvime bağlı", kaynak_turu="mevzuat",
              kapsam=GTS_ODEME, donem=donem, islem="dogrulama", sorumlu="şebeke işletmecisi",
              not_="Ayın 6'sı kuralı 12.05.2019 öncesi tesisler içindir; sonraki tesislerde bildirim çağrı mektubu/sözleşme takvimine bağlıdır ve PVQuant'ta kayıtlı değildir."),
    ]
    # GTŞ ödemesi: EPİAŞ'ın GTŞ'ye ödediği ayı (nihai + 7 iş günü, izleyen ay) izleyen ayın 5. iş günü — 02-16: Ekim 2026 → 7.12.2026
    epias_gts = is_gunu_ekle(nihai, 7)
    oy, om = (epias_gts.year + 1, 1) if epias_gts.month == 12 else (epias_gts.year, epias_gts.month + 1)
    gts_odeme = is_gunu_ekle(date(oy, om, 1) - timedelta(days=1), 5)
    olaylar.append(_olay("gts_odeme", "GTŞ'nin üreticiye ödemesi (izleyen ayın 5. iş günü); itiraz 3 iş günü", gts_odeme,
                         kaynak="LÜY m.25(1)(e), m.26(7): EPİAŞ'ın GTŞ'ye ödeme yaptığı ayı izleyen ayın en geç 5. iş günü",
                         kaynak_turu="hesaplanan", kapsam=GTS_ODEME, donem=donem, islem="takip", sorumlu="GTŞ"))
    return olaylar


def donemler(bugun: date, once: int = 1, sonra: int = 1) -> list[dict]:
    """bugun'ün ayından `once` ay geriye ve `sonra` ay ileriye fatura dönemleri (olaylar izleyen ayda)."""
    out = []
    for k in range(-once, sonra + 1):
        d = ay_ekle(date(bugun.year, bugun.month, 1), k)
        out.append({"donem": f"{d.year:04d}-{d.month:02d}", "olaylar": donem_takvimi(d.year, d.month)})
    return out


# ---- günlük piyasa saatleri ----
def gunluk_saatler() -> list[dict]:
    """Günlük piyasa saatleri: saat, ad, kaynak, kapsam, gunler («her gün»: KGÜP/EAK/GİP — DUY m.69(1) «her gün»; «iş günü»: avans,
    teminat, ESY bildirimi — m.132(1) «her işgünü», m.132/Ç(1)–(6) hafta sonu kuralları). Sıralı. Kaynaklar: 01-01, 02-05, 02-06, 02-07, 03-10."""
    s = lambda saat, ad, kaynak, kapsam=HEPSI, not_=None, gunler="iş günü": {"saat": saat, "ad": ad, "kaynak": kaynak, "kapsam": list(kapsam), "not": not_, "gunler": gunler}   # noqa: E731
    HER_GUN = "her gün"
    TEMINAT = "Teminat Usul ve Esasları m.7(3), m.7(10)(a) (Karar 6282-3, RG 28.05.2016-29725); EPİAŞ süreç sayfası"   # v2.535 (DK-131): saatlerin maddesi
    return [
        s("09:00", "EAK bildirimi açılır (TPYS, 09:00–15:30)", "TPYS Bildirim Dokümanı; DUY m.69(1)", KGUP_BILDIREN, gunler=HER_GUN),
        s("10:30", "Teminat mektubunun EPİAŞ'a sunulma son anı (11:00 kontrolü için)", TEMINAT, LISANSLI),
        s("11:00", "Teminat kontrolü (GÖP + GİP); eksikse işlem yasağı riski", TEMINAT, LISANSLI,   # v2.535 (DK-131): m.132/E(4) temerrüt sonrası tamamlama hükmüdür, günlük kontrolün dayanağı değil
          "Üç iş günü üst üste eksik kalan katılımcıya Teminat Usul ve Esasları'ndaki tedbirler uygulanır."),
        s("11:00", "Devre dışı ünitelerin devreye alma tahmini (Millî Yük Tevzi Merkezi'ne yazılı; izleyen 2.–14. gün)",
          "Elektrik Şebeke Yönetmeliği m.53(1)(a); kapsam m.51(1): iletime doğrudan bağlı üretim tesisi", LISANSLI + ("lisanssiz_iletim",),
          "yalnız iletime doğrudan bağlı tesis; dağıtıma bağlıysa uygulanmaz"),   # v2.535 (DK-752)
        s("14:00", "Program (KGÜP) bildirim penceresi açılır (GÖP sonuçları kesinleşince)", "DUY m.68(1); TPYS Bildirim Dokümanı", KGUP_BILDIREN,
          "1.1.2027'den DUY m.50(2): frekans kontrol rezervi tedariki gecikirse GÖP süreçleri ötelenebilir, pencere daralabilir; EPİAŞ duyurusuna bakın", gunler=HER_GUN),   # v2.535 (DK-854)
        s("14:30", "Günlük avans bildirimi (bir önceki günün GÖP/GİP işlemleri)", "DUY m.132(1): her iş günü; hafta sonu ve tatil için izleyen ilk iş günü", LISANSLI),
        s("14:30", "PYS erişimi olmayan katılımcının program ve EAK'yi Bölgesel Yük Tevzi Merkezi'ne (BYTM) bildirme son saati", "DUY m.69(1)", KGUP_BILDIREN, gunler=HER_GUN),
        s("15:00", "Avans borcu ödeme son anı; sonrası temerrüt (6183 m.51 oranının %50'si)", "DUY m.132/Ç(1), (3), (5); m.132/D(1), (3)", LISANSLI),
        s("15:30", "Program (KGÜP) ve EAK bildirimi kapanır", "DUY m.69(1): her gün 15:30; TPYS", KGUP_BILDIREN, gunler=HER_GUN),
        s("16:30", "Teminat mektubunun sunulma son anı (17:00 GİP kontrolü için)", TEMINAT, LISANSLI),
        s("17:00", "Sistem işletmecisinin program (KGÜP) teyidi", "DUY m.69(4)", KGUP_BILDIREN, gunler=HER_GUN),
        s("17:00", "EPİAŞ'ın alacaklıya avans ödemesi; GİP teminat kontrolü; 17:00 sonrası ödemede temerrüt faizi tam oran",
          "DUY m.132/Ç(2), (4), (6); m.132/D(3); " + TEMINAT, LISANSLI),
        s("gün içi", "GİP kapı kapanışı teslimattan 1 saat önce; program (KGÜP) revizyonu kapanış + 30 dk", "DUY m.69(1) (+30 dk); GİP kapanışı 60 dk: DUY m.66/A(1)(f) yetkisi, EPİAŞ duyurusu 28.08.2018 (01.10.2018'den)", KGUP_BILDIREN, gunler=HER_GUN),
    ]


# ---- sabit (tek seferlik ve yıllık) tarihler ----
def sabit_tarihler(bugun: date) -> list[dict]:
    """Bugünden itibaren bilinen sabit tarihler; yıllık olanlar bugünün yılı ve sonrası için üretilir."""
    out = []
    for yil in (bugun.year, bugun.year + 1):
        out += [
            _olay("yekdem_basvuru", f"YEKDEM {yil + 1} başvurusu ve vazgeçme son günü (yıl içinde çıkılamaz)", is_gununa_kaydir(date(yil, 11, 30)),
                  kaynak="YEK Yön. m.5(1)–(2), m.4(2); 5346 m.6; EPDK yıllık YEKDEM duyurusu (hafta sonu/tatilde izleyen iş günü, EPDK uygulaması)",   # v2.535 (DK-302/279)
                  kaynak_turu="hesaplanan" if not is_gunu(date(yil, 11, 30)) else "mevzuat", kaydirma="is_gunu",
                  not_="30 Kasım hafta sonu/tatile denk geliyor; EPDK uygulamasına göre izleyen iş günü." if not is_gunu(date(yil, 11, 30)) else None,
                  kapsam=LISANSLI, islem="islem", sorumlu="santral", sonuc_kisa=f"{yil + 1}'de YEKDEM yok",
                  sonuc=f"Süresinde başvurulmazsa {yil + 1} yılında YEKDEM'den yararlanılamaz (YEK Yön. m.5); yıl içinde giriş yok"),
            _olay("yek_on_liste", f"Ön YEK listesi ({yil + 1}): Aralık'ın ilk 10 günü içinde ilan; düzeltme için 5 gün içinde yazılı itiraz", date(yil, 12, 10),
                  kaynak="YEK Yön. m.6", kaynak_turu="hesaplanan", kapsam=LISANSLI, islem="takip", sorumlu="EPDK", sonuc_kisa="Yazılı itiraz 5 gün (m.6)",
                  sonuc="Lisans sahibi ilana konu bilgilerin düzeltilmesi için 5 gün içinde yazılı itiraz edebilir (YEK Yön. m.6); nihai liste 31 Aralık'a kadar Kurul kararıyla (m.7)"),
            _olay("yek_nihai_liste", f"Nihai YEK listesi ({yil + 1}) 31 Aralık'a kadar", date(yil, 12, 31),
                  kaynak="YEK Yön. m.7(1)", kaynak_turu="mevzuat", kapsam=LISANSLI, islem="takip", sorumlu="EPDK"),
            _olay("planli_devre_disi", f"{yil + 1} yılı planlı devre dışı taleplerinin TEİAŞ'a bildirimi", date(yil, 4, 30),
                  kaynak="Elektrik Şebeke Yönetmeliği m.52: içinde bulunulan yılın 30 Nisan'ına kadar; iletime bağlı üretim tesisi",   # 03-10
                  kaynak_turu="mevzuat", kaydirma="belirsiz", kapsam=LISANSLI + ("lisanssiz_iletim",), sonuc=M30_B, sonuc_kisa=M16_KISA,
                  islem="islem", sorumlu="santral",
                  not_="Bildirilmeyen bakım yıllık plana girmez; 48 saati aşan devre dışılar plana bağlıdır (çıkarım: m.54 48 saate kadarını düzenler). "
                       "Yalnız iletime doğrudan bağlı tesis (m.51(1)); dağıtıma bağlıysa bakım takvimi dağıtım şirketine (Lisans Yön. m.30(2)(b))." + HAFTA_SONU_NOT),
            _olay("luy_isletim_bedeli_tem", "Lisanssız yıllık işletim bedeli, 1. taksit (Temmuz son iş günü)", _son_is_gunu(yil, 7),
                  kaynak="LÜY m.36(2): Temmuz son iş günü mesai bitimi", kaynak_turu="hesaplanan", kapsam=LISANSSIZ, islem="islem", sorumlu="santral",   # 03-17
                  sonuc="Sonuç LÜY m.36(2)'de yazılı değil; sistem kullanım bedeli ödenmezse bildirimsiz ayırma (LÜY m.36(3))", sonuc_kisa="m.36(3) ayırma riski"),
            _olay("luy_isletim_bedeli_ara", "Lisanssız yıllık işletim bedeli, 2. taksit (Aralık son iş günü)", _son_is_gunu(yil, 12),
                  kaynak="LÜY m.36(2): Aralık son iş günü mesai bitimi", kaynak_turu="hesaplanan", kapsam=LISANSSIZ, islem="islem", sorumlu="santral",
                  sonuc="Sonuç LÜY m.36(2)'de yazılı değil; sistem kullanım bedeli ödenmezse bildirimsiz ayırma (LÜY m.36(3))", sonuc_kisa="m.36(3) ayırma riski"),
        ]
    out += [
        _olay("dsg_2027_orani", "DSG 2027 üye eşiği için Kurul karar son günü", date(2026, 12, 1),
              kaynak="DUY m.111(5): yıllık karar en geç 1 Aralık", kaynak_turu="mevzuat", kapsam=LISANSLI, islem="takip", sorumlu="Kurul",   # 08-01
              not_="Kurul'un yasal son günüdür, kararın çıkıp çıkmadığı PVQuant'ta izlenmez; karar yayımlanınca Doğruluk ve Portföy'deki DSG eşiği kural motorunda güncellenir."),
        _olay("aym_luy_10yil", "AYM iptali yürürlükte: 5346 m.6(2) 1.–2. cümle (10 yılı dolan lisanssızın lisanslıya geçiş yolu) kalkıyor; fiyat hükmü (3. cümle, CK 11415) yürürlükte", date(2026, 12, 10),
              kaynak="AYM kararı 26.11.2025, E.2024/133 K.2025/233 (RG 10.3.2026); 5346 m.6(2); CK 11415 (13.06.2026'dan fiyat rejimi)", kaynak_turu="mevzuat", kapsam=LISANSSIZ, islem="mevzuat",
              sorumlu="Cumhurbaşkanlığı / EPDK", not_="İptal yalnız lisanslıya geçiş yolunu kapsar; 10 yıl sonrası satış fiyatı CK 11415 formülüyle sürer."),   # v2.535 (DK-663/571)
        _olay("luy_gecici14", "LÜY Geçici 14: bağlantı anlaşması revizyonu başvuru süresi sonu (19.10.2026 + 60 gün)", date(2026, 12, 18),
              kaynak="LÜY Geçici m.14 (RG 19.10.2026-33405): yayımdan itibaren 60 gün; metinde tarih yazmıyor", kaynak_turu="hesaplanan",   # 08-11
              kapsam=("lisanssiz_dagitim",), islem="dogrulama", sorumlu="santral",
              not_="Yükümlülük DUY m.75(4) kapsamındaki (GTŞ/toplayıcı portföyündeki) lisanssız üreticiler içindir; hangi anlaşmalar için zorunlu olduğu doğrulanmadı; "
                   "yayım günü sayılırsa temkinli son gün 17.12.2026. Dağıtım şirketinizin duyurusuna bakın."),
        _olay("m110_2027", "DUY m.110 yeni rejim (15 dk DGP, tek k/l, «ç» bazlı KÜPSM) — uygulama belirsiz", date(2027, 1, 1),
              kaynak="RG 21.1.2025-32789 Md.13, Md.20(b); 31.10.2026'ya kadar yeni Kurul kararı yok", kaynak_turu="mevzuat",   # 08-01
              kapsam=HEPSI, islem="mevzuat", sorumlu="Kurul", not_="Yürürlük tarihi yazılı; uygulama ayrıntıları (DGP 15 dk, tek k/l, «ç» bazlı KÜPSM) Kurul kararı çıkana kadar belirsiz. Hesap yürürlükteki kuralla. "
                                                                 "Aynı değişikliğin Md.5'i ile 1.1.2027'den DUY m.50(2): frekans kontrol rezervi tedariki gecikirse GÖP süreçleri ötelenebilir; KGÜP penceresi daralabilir."),
        _olay("gecici_m39_bitis", "DUY Geçici m.39 sona erer: dağıtım ve GTŞ DSG'lerinde %100 üye eşiği biter, genel eşik uygulanır", date(2027, 1, 1),
              kaynak="DUY Geçici m.39", kaynak_turu="mevzuat", kapsam=LISANSLI, islem="dogrulama", sorumlu="DSG yöneticisi",
              not_="Yalnız dağıtım şirketi ile bölgesindeki görevli tedarik şirketinin birlikte kurduğu DSG'lerin üyelerini etkiler; DSG'nizin türü PVQuant'ta kayıtlı değil."),
        _olay("sktt_2027", "SKTT 2027 tüketim limitleri yürürlükte (Karar 15005)", date(2027, 1, 1),
              kaynak="RG 31.10.2026-33416, Karar 15005", kaynak_turu="mevzuat", kapsam=("oz_tuketim_saatlik",), islem="mevzuat", sorumlu="EPDK"),
        _olay("luy_cezai_sart", "Karar 14909 lisanssız SCADA/uzaktan kontrol cezai şart askısının sonu", date(2027, 4, 30),
              kaynak="LÜY Geçici m.14(2) (RG 19.10.2026-33405): bağlantı anlaşması 16/1-f, g cezai şartları 30.4.2027'ye kadar uygulanmaz",   # v2.535 (DK-570): birincil metin
              kaynak_turu="mevzuat", kapsam=("lisanssiz_dagitim", "oz_tuketim_saatlik"), islem="mevzuat", sorumlu="dağıtım şirketi",
              not_="Askı bitince bağlantı anlaşmasının 16/1-f, g bedel maddeleri uygulanır (Geçici m.14(2))."),
    ]
    return out


def _son_is_gunu(yil: int, ay: int) -> date:
    d = date(yil, ay, calendar.monthrange(yil, ay)[1])
    while not is_gunu(d):
        d -= timedelta(days=1)
    return d


def _n_inci_is_gunu(yil: int, ay: int, n: int) -> date:
    """Ayın n. iş günü (Lisans Yön. m.43(7): «ilk beş iş günü içinde» → 5. iş günü son gün)."""
    d = date(yil, ay, 1); k = 0
    while True:
        if is_gunu(d):
            k += 1
            if k == n:
                return d
        d += timedelta(days=1)


# ---- v2.524 (P3b): lisans, bildirim ve uyum takvimi ----
M16_B = "6446 m.16(1)(b) idari yaptırımı (eşleme çıkarım), ihtar 30 gün; önce EPDK uyarısı ve 7 gün süre (Bildirim Yükümlülük Tablosu)"
M16_B_SADE = "6446 m.16(1)(b) idari yaptırımı (eşleme çıkarım), ihtar 30 gün"   # v2.535 (DK-593): 7 günlük uyarı yalnız bildirim tablosundaki yükümlülüklerde
M30_B = "Lisans Yön. m.30(2)(b) bakım takvimi yükümlülüğü → 6446 m.16(1)(b) (eşleme çıkarım), ihtar 30 gün"
M16_KISA = "6446 m.16(1)(b) · ihtar 30 gün (çıkarım)"
HAFTA_SONU_NOT = " Son gün hafta sonuna denk gelirse kaydırma kuralı metinde yok; önceki iş gününde tamamlayın."
UYUM_KODLAR = ("ilerleme_raporu", "lisans_bedeli_taksit", "bdb02", "planli_devre_disi", "planli_devre_disi_nihai", "planli_devre_disi_itiraz", "planli_devre_disi_alternatif", "isg_periyodik_kontrol",
               "ortaklik_bildirim", "izin_iptali_bildirim", "luy_alim_suresi", "lisans_bedeli_muafiyet", "lisans_bitis", "police_bitis", "yekdem_son_yil",
               "luy_isletim_bedeli_tem", "luy_isletim_bedeli_ara", "luy_cezai_sart", "yekdem_basvuru", "yek_on_liste", "yek_nihai_liste")
BDB02_ESIK_KW = 100_000.0   # EPDK Bildirim Yükümlülük Tablosu: herhangi bir tesisinin kurulu gücü 100 MW (mekanik) üzeri; kWp ile yaklaşıldı


def uyum_olaylari(pj: dict | None, bugun: date, segment: str | None, capacity_kwp: float | None = None) -> list[dict]:
    """Yıllık ve olay anından sayan uyum son tarihleri (bugünün yılı ve sonraki yıl): ilerleme raporu (Ocak/Temmuz sonu; tam kabule kadar), lisans bedeli
    taksitleri (Şubat/Haziran/Ekim 5. iş günü; muafiyet bitince), BDB-02 (15 Mayıs; 100 MW üzeri), TEİAŞ nihai bakım planı (31 Ekim), İSG periyodik kontrol
    (son kontrol + 1 yıl), ortaklık değişikliği (+6 ay), izin/ruhsat iptali (+2 ay), lisanssız 10 yıllık alım süresi (ilk enerji + 10 yıl)."""
    pj = pj or {}
    kabul = _tarih(pj.get("kabul_tarihi")); tam_kabul = _tarih(pj.get("tam_kabul_tarihi")); giris = _tarih(pj.get("isletmeye_giris"))
    isg = _tarih(pj.get("isg_son_kontrol")); ortaklik = _tarih(pj.get("ortaklik_degisikligi")); izin = _tarih(pj.get("izin_iptali"))
    muafiyet_bitis = yil_ekle(kabul, 8) if kabul else None
    out = []
    for yil in (bugun.year, bugun.year + 1):
        if tam_kabul is None:   # m.30(2)(ç): toplam kurulu gücün tamamının kabulüne kadar
            for ay, ad in ((1, "Ocak"), (7, "Temmuz")):
                out.append(_olay("ilerleme_raporu", f"İlerleme raporu ({ad} sonu; kurulu gücün tamamı kabul edilene kadar)", date(yil, ay, calendar.monthrange(yil, ay)[1]),
                                 kaynak="Lisans Yön. m.30(2)(ç): her yılın Ocak ve Temmuz ayları içinde; EPDK bildirim tablosu «ay sonuna kadar», muhatap Elektrik Piyasası Dairesi",
                                 kaynak_turu="mevzuat", kaydirma="belirsiz", kapsam=LISANSLI, sonuc=M16_B, sonuc_kisa=M16_KISA, islem=("islem" if kabul else "dogrulama"), sorumlu="santral",   # v2.535: kabul tarihi yoksa yükümlülük doğrulanmamış
                                 not_=("Tam kabul tarihini Santral tarihleri formuna girince bu satır kalkar." if kabul else
                                       "Kabul tarihleri girilmedi; kurulu gücün tamamı kabul edildiyse tam kabul tarihini girin, satır kalkar.") + HAFTA_SONU_NOT))
        for ay in (2, 6, 10):
            t = _n_inci_is_gunu(yil, ay, 5)
            if muafiyet_bitis is None or muafiyet_bitis <= t:
                out.append(_olay("lisans_bedeli_taksit", "Yıllık lisans bedeli taksiti (ayın ilk 5 iş günü içinde; önceki yılın üretimi üzerinden)", t,
                                 kaynak="Lisans Yön. m.43(5)(a), (7)(a): Şubat, Haziran ve Ekim'in ilk beş iş günü, üç eşit taksit; m.43(8): gecikmede 6183 m.51 zammı",
                                 kaynak_turu="hesaplanan", kaydirma="yok", kapsam=LISANSLI, sonuc="6183 sayılı Kanun m.51 gecikme zammı (Lisans Yön. m.43(8))", sonuc_kisa="Gecikme zammı (6183 m.51)",
                                 islem=("islem" if muafiyet_bitis else "dogrulama"), sorumlu="santral",
                                 not_=("Birim bedel yılın Kurul kararıyla belirlenir; tutar burada hesaplanmaz." if muafiyet_bitis else
                                       "İlk kabul tarihi girilmedi; yenilenebilir tesiste ilk kabulden sonraki 8 yıl bedel alınmaz (m.43(4)).")))
        if capacity_kwp is not None and float(capacity_kwp) > BDB02_ESIK_KW:   # v2.535 (DK-580): «üzeri» → >
            out.append(_olay("bdb02", "BDB-02 bağımsız denetim raporu bildirimi (100 MW mekanik üzeri tesis)", date(yil, 5, 15),
                             kaynak="EPDK Elektrik Piyasası Bildirim Yükümlülük Tablosu (v15, Karar 13721): BDB-02, yıllık, Mayıs'ın 15. gününe kadar; muhatap Denetim Dairesi",
                             kaynak_turu="mevzuat", kaydirma="belirsiz", kapsam=LISANSLI, sonuc="6446 m.16(1)(a) idari yaptırımı (eşleme çıkarım), ihtar 15 gün", sonuc_kisa="6446 m.16(1)(a) · ihtar 15 gün (çıkarım)",
                             islem="dogrulama", sorumlu="santral",
                             not_="Mekanik güç kurulu güce (kWp) göre yaklaşıldı; yükümlülük şirket düzeyindedir (aynı şirketin başka bir tesisi eşiği aşıyorsa da geçerli); "
                                  "tesisin mekanik gücü 100 MW ve altındaysa bu tesisten doğmaz." + HAFTA_SONU_NOT))
        ILETIM = LISANSLI + ("lisanssiz_iletim",)
        DAG_NOT = ("Elektrik Şebeke Yönetmeliği m.51(1) uyarınca iletime doğrudan bağlı üretim tesislerine uygulanır; dağıtıma bağlı lisanslı tesiste yıllık bakım takvimi "
                   "dağıtım şirketine bildirilir (Lisans Yön. m.30(2)(b), tarih yazılı değil); bağlantı türü PVQuant'ta kayıtlı değil.")   # v2.535 (DK-567/736/752)
        out.append(_olay("planli_devre_disi_itiraz", f"TEİAŞ'ın {yil + 1} planlı devre dışı taslağına itiraz son günü (31 Temmuz)", date(yil, 7, 31),
                         kaynak="Elektrik Şebeke Yönetmeliği m.52: TEİAŞ ilk taslağı 30 Haziran'a kadar hazırlar; taraf 31 Temmuz'a kadar itiraz eder; iletime bağlı üretim tesisi",
                         kaynak_turu="mevzuat", kaydirma="belirsiz", kapsam=ILETIM, sonuc="İtiraz edilmezse taslak plan bu haliyle nihaileşir; nihai plana uyma zorunluluğu (m.52(6))",
                         sonuc_kisa="Taslak nihaileşir", islem=("islem" if segment == "lisanssiz_iletim" else "dogrulama"), sorumlu="santral", not_=DAG_NOT + HAFTA_SONU_NOT))
        out.append(_olay("planli_devre_disi_alternatif", f"{yil + 1} planlı devre dışı için alternatif önerinin TEİAŞ'a bildirimi (31 Ağustos)", date(yil, 8, 31),
                         kaynak="Elektrik Şebeke Yönetmeliği m.52: itiraz eden taraf alternatifini 31 Ağustos'a kadar bildirir; iletime bağlı üretim tesisi",
                         kaynak_turu="mevzuat", kaydirma="belirsiz", kapsam=ILETIM, sonuc="Alternatif bildirilmezse TEİAŞ taslağı esas alır; nihai plana uyma zorunluluğu (m.52(6))",
                         sonuc_kisa="TEİAŞ taslağı esas alınır", islem=("islem" if segment == "lisanssiz_iletim" else "dogrulama"), sorumlu="santral", not_=DAG_NOT + HAFTA_SONU_NOT))
        out.append(_olay("planli_devre_disi_nihai", f"TEİAŞ {yil + 1} nihai planlı devre dışı programını yayımlar (31 Ekim'e kadar); yayımdan sonra nihai plana uyulur", date(yil, 10, 31),
                         kaynak="Elektrik Şebeke Yönetmeliği m.52: ilk taslak 30 Eylül, nihai plan 31 Ekim (TEİAŞ'ın adımı); m.52(6): kullanıcı nihai plana uymak zorunda; iletime bağlı üretim tesisi",
                         kaynak_turu="mevzuat", kaydirma="yok", kapsam=ILETIM, sonuc="Nihai plana uyulmaması: " + M30_B, sonuc_kisa="Plana uyulmazsa " + M16_KISA,
                         islem="takip", sorumlu="TEİAŞ", not_="TEİAŞ'ın yayım adımıdır, santralin bildirim son günü değildir. " + DAG_NOT))
    if isg:
        out.append(_olay("isg_periyodik_kontrol", "İSG periyodik kontrol (elektrik, topraklama, yıldırımdan korunma, trafo, akü tesisatı; yılda bir)", yil_ekle(isg, 1),
                         kaynak="İş Ekipmanlarının Kullanımında Sağlık ve Güvenlik Şartları Yön. Ek-III 2.3.1–2.3.2, Tablo-3: standartta süre yoksa 1 yıl; son kontrol tarihi Santral tarihleri formundan",
                         kaynak_turu="kunye", kapsam=HEPSI, sonuc="6331 sayılı Kanun idari yaptırımı (tutar doğrulanmadı)", sonuc_kisa="6331 yaptırımı", islem="islem", sorumlu="santral"))
    if ortaklik:
        out.append(_olay("ortaklik_bildirim", "Ortaklık yapısı değişikliğinin EPDK'ya bildirimi (değişiklikten itibaren 6 ay)", ay_ekle(ortaklik, 6),
                         kaynak="Lisans Yön. m.57(2): tarifesi düzenlemeye tabi olmayan lisans sahibi her değişikliği altı ay içinde bildirir; değişiklik tarihi Santral tarihleri formundan",
                         kaynak_turu="kunye", kapsam=LISANSLI, sonuc="6446 m.16(1)(ç) idari yaptırımı (eşleme çıkarım), ihtar 30 gün", sonuc_kisa="6446 m.16(1)(ç) · ihtar 30 gün (çıkarım)", islem="islem", sorumlu="santral"))
    if izin:
        out.append(_olay("izin_iptali_bildirim", "Lisansa esas izin/ruhsat iptalinin EPDK'ya bildirimi (iptalden itibaren en geç 2 ay)", ay_ekle(izin, 2),
                         kaynak="Lisans Yön. m.30(2)(ı): lisansa esas izin ya da ruhsatın iptali en geç iki ay içinde bildirilir (sürenin iptal tarihinden mi tebliğden mi işlediği metinde açık değil); iptal tarihi Santral tarihleri formundan",
                         kaynak_turu="kunye", kapsam=LISANSLI, sonuc=M16_B_SADE, sonuc_kisa=M16_KISA, islem="islem", sorumlu="santral"))
    if giris and (segment in LISANSSIZ or segment is None):
        bitis = yil_ekle(giris, 10)
        out.append(_olay("luy_alim_suresi", "Lisanssız 10 yıllık alım süresinin sonu (ilk enerji + 10 yıl); şebeke işletmecisi 2 ay kala EPİAŞ'a bildirir", bitis,
                         kaynak="LÜY m.26(4): ihtiyaç fazlası on yıl süreyle satın alınır (m.19(2) ilk enerji tarihinden); m.33(7): bitime iki ay kala bildirim; ilk enerji tarihi Santral tarihleri formundan",
                         kaynak_turu="kunye", kapsam=LISANSSIZ, islem="takip", sorumlu="şebeke işletmecisi",
                         not_="10 yıl sonrası satış fiyatı 13.06.2026'dan CK 11415 formülüyle (5346 m.6(2) 3. cümle); AYM iptali (10.12.2026) yalnız m.6(2) 1.–2. cümleleri (lisanslıya geçiş yolu) kapsar."))
    return out


BAKIM_BILDIRIM_KAYNAK = ("Elektrik Şebeke Yönetmeliği m.54: 8 saatten kısa planlı devre dışı en az 24 saat önce, 8–48 saat arası en az 7 takvim günü önce bildirilir; "
                         "48 saati aşanlar m.54 kapsamı dışındadır: yıllık plan (m.52, 30 Nisan) ya da nihai plan değişikliği (m.52(5)) — çıkarım; "
                         "yalnız iletime doğrudan bağlı üretim tesisi (m.51(1))")   # v2.535 (DK-568)


def bakim_bildirim(baslangic, bitis) -> dict:
    """Olay kaydındaki planlı bakım için TEİAŞ'a bildirim son anı (saf; tz-aware datetime). Süre bilinmiyorsa (bitiş yok) kural seçilemez."""
    if bitis is None:
        return {"sure_saat": None, "kural": "süre girilmedi", "son_an": None, "kaynak": BAKIM_BILDIRIM_KAYNAK}
    sure = (bitis - baslangic).total_seconds() / 3600
    if sure < 8:
        return {"sure_saat": round(sure, 1), "kural": "8 saatten kısa: en az 24 saat önce", "son_an": (baslangic - timedelta(hours=24)).isoformat(), "kaynak": BAKIM_BILDIRIM_KAYNAK}
    if sure <= 48:
        return {"sure_saat": round(sure, 1), "kural": "8–48 saat: en az 7 takvim günü önce", "son_an": (baslangic - timedelta(days=7)).isoformat(), "kaynak": BAKIM_BILDIRIM_KAYNAK}
    return {"sure_saat": round(sure, 1), "kural": "48 saatten uzun: m.54 dışı; yıllık plan (30 Nisan) ya da plan değişikliği (m.52(5), çıkarım)", "son_an": None, "kaynak": BAKIM_BILDIRIM_KAYNAK}


# ---- künye tarihleri ve türeyenler ----
KUNYE_TARIH_ALANLARI = ("lisans_yururluk", "lisans_bitis", "kabul_tarihi", "tam_kabul_tarihi", "isletmeye_giris", "police_bitis", "ced_karar_tarihi",
                        "baglanti_anlasmasi", "toplayici_giris", "toplayici_cikis", "isg_son_kontrol", "ortaklik_degisikligi", "izin_iptali",
                        "cagri_mektubu_tarihi")   # v2.524 (P3b): +4; v2.541 (EK-2 DK-659): çağrı mektubuna hak kazanma tarihi (lisanssız rejim ölçütü)
KUNYE_ETIKET = {"lisans_yururluk": "Lisans yürürlük tarihi", "lisans_bitis": "Lisans bitiş tarihi", "kabul_tarihi": "İlk kabul tarihi (kısmi ya da tam)",
                "cagri_mektubu_tarihi": "Çağrı mektubuna hak kazanma tarihi (lisanssız)",   # v2.541 (DK-659)
                "isletmeye_giris": "İşletmeye giriş (ilk enerji) tarihi", "police_bitis": "Sigorta poliçesi bitişi", "ced_karar_tarihi": "ÇED kararı tarihi",
                "baglanti_anlasmasi": "Bağlantı anlaşması tarihi", "toplayici_giris": "Toplayıcı portföyüne giriş", "toplayici_cikis": "Toplayıcı portföyünden çıkış",
                "yekdem_baslangic_yili": "YEKDEM başlangıç yılı",
                "tam_kabul_tarihi": "Tam kabul tarihi (kurulu gücün tamamı)", "isg_son_kontrol": "Son İSG periyodik kontrol tarihi",   # v2.524 (P3b)
                "ortaklik_degisikligi": "Son ortaklık yapısı değişikliği", "izin_iptali": "Lisansa esas izin/ruhsat iptali tarihi"}


def _tarih(v) -> date | None:
    if not v:
        return None
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


LUY_REJIM_ESIGI = date(2019, 5, 12)   # LÜY (RG 12.05.2019-30772): 12.05.2019 öncesi çağrı mektuplu tesisler m.25, sonrası m.26 (EK-2 DK-659: ölçüt çağrı mektubuna hak kazanma tarihi)


def luy_rejimi(pj: dict | None) -> dict:
    """v2.541 (EK-2 DK-659): lisanssız tesisin LÜY rejimi — ölçüt çağrı mektubuna hak kazanma tarihi (12.05.2019 öncesi: m.25 eski rejim, ayın 6'sı
    GTŞ bildirimi m.23(3); 12.05.2019 ve sonrası: m.26, 1.5.2026'dan saatlik mahsup). Çağrı mektubu tarihi girilmemişse işletmeye giriş tarihi
    yorumla kullanılır ve «yorum» etiketlenir; ikisi de yoksa belirsiz."""
    pj = pj or {}
    cm = _tarih(pj.get("cagri_mektubu_tarihi")); giris = _tarih(pj.get("isletmeye_giris"))
    if cm is not None:
        t, olcut, kesinlik = cm, "çağrı mektubuna hak kazanma tarihi", "teyit"
    elif giris is not None:
        t, olcut, kesinlik = giris, "işletmeye giriş tarihi (çağrı mektubu tarihi girilmedi; yorum)", "yorum"
    else:
        return {"rejim": None, "etiket": "belirsiz", "olcut": None, "tarih": None, "kesinlik": "belirsiz",
                "not": "Çağrı mektubuna hak kazanma tarihi girilmedi; LÜY m.25 / m.26 ayrımı yapılamadı (Santral tarihleri formu)."}
    eski = t < LUY_REJIM_ESIGI
    return {"rejim": "m25" if eski else "m26", "etiket": ("12.05.2019 öncesi (LÜY m.25)" if eski else "12.05.2019 ve sonrası (LÜY m.26)"), "olcut": olcut,
            "tarih": t.isoformat(), "kesinlik": kesinlik,
            "not": ("Ölçüt çağrı mektubuna hak kazanma tarihidir, işletmeye giriş değil (LÜY m.25(1)/m.26(1)). " +
                    ("Ayın 6'sı GTŞ bildirimi (m.23(3)) bu tesise uygulanır." if eski else "GTŞ bildirimi m.26(2) düzenlenmiş takvime bağlı; 1.5.2026'dan saatlik mahsup (m.26)."))}


def yekdem_suresi(isletmeye_giris: date | None, baslangic_yili: int | None = None) -> dict | None:
    """EPDK Kurul Kararı 5905-27: işletmeye giriş 1 Kasım–31 Ekim gruplarının izleyen yıldan başlayarak 10 yıl (01.11.2015–31.10.2016 → 2017–2026).
    1.1.2021–30.6.2021 arasında işletmeye girenlerde CK 2949 m.1(1) (RG 18.9.2020-31248): I sayılı Cetvel fiyatları 31.12.2030'a kadar
    (ilk yıl 2022, son yıl 2030; EPDK SSS «2022'den başlayarak 9 takvim yılı») — v2.532, 03.11.2026 doğrulama arşivi DK-306/DK-304 (kanıt A).
    30.6.2021 sonrası tesislerde 7189 sayılı CK Ek-1: 10 yıl YEK fiyatı + 5 yıl yerli katkı, işletmeye giriş tarihinden (hesaplanan).
    `baslangic_yili` verilmişse (kullanıcı girdisi) son yıl = başlangıç + 9."""
    if baslangic_yili:
        return {"rejim": "kullanici", "ilk_yil": int(baslangic_yili), "son_yil": int(baslangic_yili) + 9,
                "kaynak": "YEKDEM başlangıç yılı kullanıcı girdisi; 10 takvim yılı (5346 m.6)", "kaynak_turu": "hesaplanan"}
    if isletmeye_giris is None:
        return None
    if isletmeye_giris > date(2021, 6, 30):
        return {"rejim": "7189", "yek_bitis": yil_ekle(isletmeye_giris, 10).isoformat(), "yerli_katki_bitis": yil_ekle(isletmeye_giris, 5).isoformat(),
                "ilk_yil": isletmeye_giris.year, "son_yil": yil_ekle(isletmeye_giris, 10).year,
                "kaynak": "7189 sayılı CK Ek-1: 10 yıl YEK fiyatı, 5 yıl yerli katkı; işletmeye giriş tarihinden (hesaplanan)", "kaynak_turu": "hesaplanan"}   # 08-04
    if isletmeye_giris >= date(2021, 1, 1):   # v2.532: CK 2949 grubu — Cetvel I 31.12.2030'a kadar
        return {"rejim": "2949", "ilk_yil": 2022, "son_yil": 2030,
                "kaynak": "CK 2949 m.1(1) (RG 18.9.2020-31248): 1.1–30.6.2021 arasında işletmeye girenlerde I sayılı Cetvel fiyatları 31.12.2030'a kadar", "kaynak_turu": "mevzuat"}
    grup_bitis = isletmeye_giris.year if isletmeye_giris.month <= 10 else isletmeye_giris.year + 1
    return {"rejim": "5905-27", "ilk_yil": grup_bitis + 1, "son_yil": grup_bitis + 10,
            "kaynak": "EPDK Kurul Kararı 5905-27 (02.12.2015): 1 Kasım–31 Ekim grubu, izleyen yıldan 10 yıl", "kaynak_turu": "mevzuat"}


def kunye_turet(pj: dict | None, bugun: date) -> dict:
    """params_json'daki tarih alanlarından türeyenler. Boş alan → None; panel «Belirtilmedi» yazar."""
    pj = pj or {}
    alanlar = {k: (_tarih(pj.get(k)).isoformat() if _tarih(pj.get(k)) else None) for k in KUNYE_TARIH_ALANLARI}
    yb = pj.get("yekdem_baslangic_yili")
    alanlar["yekdem_baslangic_yili"] = int(yb) if yb else None
    lb = _tarih(pj.get("lisans_bitis")); kabul = _tarih(pj.get("kabul_tarihi")); giris = _tarih(pj.get("isletmeye_giris")); police = _tarih(pj.get("police_bitis"))
    # 01.11 incelemesi: «bitiş − 6 ay» türetmesi kaldırıldı — Lisans Yön. m.26(2) erken sona erdirme başvurusunun asgari süresidir (istenen
    # tarihten en az 6 ay önce); lisans süre bitiminde kendiliğinden sona erer (m.26(1)(a)), bitişe bağlı bir başvuru tarihi yoktur.
    turetilen = {
        "lisans_kalan_gun": (lb - bugun).days if lb else None,
        "lisans_bedeli_muafiyet_bitis": yil_ekle(kabul, 8).isoformat() if kabul else None,   # 03-03: m.43(4) ilk (kısmi/tam) kabulden sonraki 8 yıl
        "yekdem": yekdem_suresi(giris, alanlar["yekdem_baslangic_yili"]),
        "police_kalan_gun": (police - bugun).days if police else None,
        # v2.524 (P3b)
        "ilerleme_raporu_yukumlu": _tarih(pj.get("tam_kabul_tarihi")) is None,
        "isg_sonraki_kontrol": yil_ekle(_tarih(pj.get("isg_son_kontrol")), 1).isoformat() if _tarih(pj.get("isg_son_kontrol")) else None,
    }
    return {"alanlar": alanlar, "turetilen": turetilen, "etiketler": KUNYE_ETIKET}


SIGORTA_KAYNAK = ("Lisans Yön. m.47: tesis varlıkları doğal afet, yangın, kaza, hırsızlık, üçüncü şahıs mali sorumluluğu, terör ve sabotaja "
                  "karşı teminat altına alınır (sigorta); poliçe tarihi Santral tarihleri formundan")


def kunye_olaylari(pj: dict | None, bugun: date, segment: str | None) -> list[dict]:
    """Santral tarihleri formundan türeyen olaylar; kaynak_turu «kunye» (tarih müşterinin girdisi)."""
    k = kunye_turet(pj, bugun); t = k["turetilen"]; out = []
    if k["alanlar"]["lisans_bitis"]:
        out.append(_olay("lisans_bitis", "Lisans süresi biter (kendiliğinden sona erer)", date.fromisoformat(k["alanlar"]["lisans_bitis"]),
                         kaynak="Lisans Yön. m.26(1)(a); bitiş tarihi Santral tarihleri formundan", kaynak_turu="kunye", kapsam=LISANSLI, islem="takip", sorumlu="EPDK",
                         not_="Süre uzatımı ayrı başvuru gerektirir; erken sona erdirme için istenen tarihten en az 6 ay önce başvurulur (m.26(2))."))
    if k["alanlar"]["police_bitis"]:
        out.append(_olay("police_bitis", "Sigorta poliçesi bitişi (yenileme)", date.fromisoformat(k["alanlar"]["police_bitis"]),
                         kaynak=SIGORTA_KAYNAK, kaynak_turu="kunye", kapsam=HEPSI,
                         sonuc="Lisanslıda Lisans Yön. m.47 sigorta yükümlülüğüne aykırılık → 6446 m.16(1)(b) (eşleme çıkarım); her tesiste hasar teminatsız kalır",
                         sonuc_kisa="Hasar teminatsız; lisanslıda m.16(1)(b)", islem="islem", sorumlu="santral"))
    if t["lisans_bedeli_muafiyet_bitis"]:
        out.append(_olay("lisans_bedeli_muafiyet", "Lisans bedeli muafiyetinin sonu (ilk kabul + 8 yıl); sonra Şubat, Haziran ve Ekim'in ilk 5 iş gününde taksit",
                         date.fromisoformat(t["lisans_bedeli_muafiyet_bitis"]),
                         kaynak="Lisans Yön. m.43(4), (7): ilk kabulden sonraki 8 yıl alınmaz (yıl sayımı metinde açık değil); kabul tarihi Santral tarihleri formundan",
                         kaynak_turu="kunye", kapsam=LISANSLI, sonuc="Sonraki taksitler gecikirse 6183 sayılı Kanun m.51 gecikme zammı (m.43(8))", sonuc_kisa="Sonra taksitler başlar", islem="takip", sorumlu="EPDK"))
    y = t["yekdem"]
    if y and segment in ("lisansli_yekdem",):
        out.append(_olay("yekdem_son_yil", f"YEKDEM son yılı {y['son_yil']}; {y['son_yil'] + 1}'den itibaren serbest piyasa (dengesizlik ve KÜPST sorumluluğu)",
                         date(y["son_yil"], 12, 31), kaynak=y["kaynak"] + "; işletmeye giriş tarihi Santral tarihleri formundan", kaynak_turu="kunye",
                         kapsam=("lisansli_yekdem",), islem="takip", sorumlu="EPİAŞ", not_="Sonraki yıl için serbest piyasa hazırlığı (ikili anlaşma / GÖP, dengesizlik ve KÜPST sorumluluğu)."))
    return out


# ---- yaklaşan ----
def yaklasan(bugun: date, pj: dict | None, segment: str | None, gun: int = 90, capacity_kwp: float | None = None) -> list[dict]:
    """Bugünden `gun` gün ileriye kadar, segmente uyan olaylar; kalan_gun ile; tarih/saat sıralı. Segment yoksa hepsi (kapsam etiketi gösterilir)."""
    son = bugun + timedelta(days=gun)
    havuz = []
    for d in donemler(bugun, once=1, sonra=2):
        havuz += d["olaylar"]
    havuz += sabit_tarihler(bugun) + kunye_olaylari(pj, bugun, segment) + uyum_olaylari(pj, bugun, segment, capacity_kwp)   # v2.524 (P3b)
    pj = pj or {}
    yk = yekdem_suresi(_tarih(pj.get("isletmeye_giris")), pj.get("yekdem_baslangic_yili"))
    out = []
    for o in havuz:
        t = date.fromisoformat(o["tarih"])
        if not (bugun <= t <= son):
            continue
        if segment and segment not in o["kapsam"]:
            continue
        o = yekdem_uygunluk(o, segment, yk, t.year)
        if o is None:
            continue
        if o["kod"] == "planli_devre_disi" and segment in LISANSLI:   # bağlantı türü (iletim/dağıtım) PVQuant'ta kayıtlı değil → koşullu
            o = {**o, "islem": "dogrulama"}
        out.append({**o, "kalan_gun": (t - bugun).days})
    out.sort(key=lambda o: (o["tarih"], o["saat"] or "", o["kod"]))
    return out


YEKDEM_KODLAR = ("yekdem_basvuru", "yek_on_liste", "yek_nihai_liste")


def yekdem_uygunluk(o: dict, segment: str | None, yk: dict | None, yil: int) -> dict | None:
    """YEKDEM takvimi yalnız uygun tesise: YEKA sözleşmeli tesise uygulanmaz; destek süresi (10 yıl) hedef yıldan önce bitmişse satır düşer;
    işletmeye giriş ya da başlangıç yılı girilmemişse «doğrulama gerekli». Hedef yıl = takvim yılı + 1 (30 Kasım {yıl} → {yıl+1} YEKDEM listesi)."""
    if o["kod"] not in YEKDEM_KODLAR:
        return o
    if segment == "yeka":   # v2.535 (DK-337): silmek yerine doğrulama gerekli
        return {**o, "islem": "dogrulama", "not": "YEKA tesisleri YEKDEM'den sözleşme/şartname koşullarıyla yararlanır; yıllık başvuru takviminin bu tesise uygulanıp uygulanmadığı doğrulanmadı."}
    hedef = yil + 1
    if yk is None:
        return {**o, "islem": "dogrulama", "not": "İşletmeye giriş tarihi ya da YEKDEM başlangıç yılı girilmedi (Santral tarihleri); destek süresi bilinmediğinden "
                                                  "bu tesise uygulanıp uygulanmadığı doğrulanamadı."}
    if yk["son_yil"] < hedef:
        return None   # destek süresi bitmiş: başvuru/liste bu tesisi ilgilendirmez
    if segment == "lisansli_serbest" and o["kod"] == "yekdem_basvuru":
        return {**o, "not": f"İsteğe bağlı: destek süresi {yk['son_yil']} sonuna kadar; {hedef} için YEKDEM'e girmek isterseniz başvurun, kalacaksanız işlem yok."}
    return o
