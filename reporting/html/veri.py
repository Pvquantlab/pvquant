# -*- coding: utf-8 -*-
"""veri.py — raporun TÜM sabit verisi tek kaynaktan (Dalga E.2, Adım 1).

Kural: bir sayı birden fazla sayfada görünüyorsa buradan türetilir.
JSON v2.0 adaptörü yazıldığında yalnız bu modül değişecek; build_sXX
dosyaları ve pvq.py veriye dokunmayacak. Alan eşlemesi: docs/veri_haritasi.md
"""

# ---------------------------------------------------------------- kimlik
SANTRAL = "Konya GES"                      # plant.name
MUSTERI = "Anadolu Enerji A.Ş."            # report.customer (şema v2.1)
KAPASITE_MWP = 12.4                        # plant.capacity_kwp/1000 (v2.103:
                                           # s11 özgül üretimdeki gömülü 12.4)
SEBEKE_AC_MWE = 10.0                       # plant.sebeke_ac_mwe (B3b-1 v2.169:
                                           # MWe ALANDIR — display-split öldü)
DONEM = "05–20 Ağustos 2026"               # forecast.horizon
GUN_SAYISI = 16                            # len(daily)
AY_YIL = "Ağustos 2026"                    # eksen/başlık ay etiketi
# C-3b/3 (v2.153): 120 gün KARNENİN değil METRİĞİN penceresidir (karne 30
# takvim günü, karar-a) — eski KARNE_PENCERE adı ve s01 "Karne penceresi"
# etiketi bu karışıklığı taşıyordu. Tek kaynak:
METRIK_PENCERE_GUN = 120
METRIK_PENCERE = "7 Nisan – 4 Ağustos 2026 (%d gün)" % METRIK_PENCERE_GUN  # prepared−119g → prepared
EGITIM_SERIT = "<i>7 Nisan 2026</i><i>11 Temmuz</i><i>4 Ağustos 2026</i>"  # %80/%20 şeridi

# c2b (v2.107): anlatı token'ları — kanonik metinler (statik yol);
# JSON yolunda narrative.* alanından gelir, yoksa nötr kalır.
NARR_EXEC_1 = "<b>Belirsizlik dar.</b> Bant genişliği dönem genelinde günlük ±%6–8 düzeyindedir;\n      yalnızca 11–13 Ağustos'ta beklenen cephe geçişi bandı genişletmektedir. 12 Ağustos'ta\n      beklenti 53,6 MWh'e gerilemekte, belirsizlik ±9,7 MWh'e çıkmaktadır. Cephe sonrasında\n      üretim mevsim normaline dönmektedir."
NARR_EXEC_2 = "<b>İyileşme bağımsız veride doğrulandı.</b> Model, santralin kendi üretim verisiyle\n      kalibre edildikten sonra hatayı %13,6'dan %8,9'a indirmiştir — %34,6 iyileşme. Bu ölçüm,\n      modelin eğitimde hiç görmediği son dönem verisi üzerinde yapılmıştır."
NARR_EXEC_3 = '<b>Doğrulama 87 gündür kesintisiz.</b> 120 günlük karne penceresinde yalnızca dört gün\n      (21 ve 29 Nisan, 7–8 Mayıs) ölçüm eksikliği nedeniyle karne dışında kalmıştır. Bu günler\n      hiçbir ortalamaya katılmamış, boş bırakılmıştır.'
NARR_EXEC_4 = '<b>Taahhüt için önerilen değer.</b> İşletme planlamasında bandın alt sınırı (P10)\n      güvenli taahhüt seviyesi olarak kullanılabilir: 16 günlük dönem için 1.005 MWh. Günler\n      kısmen bağımsız olduğundan dönem toplamındaki bant, günlük banttan dardır.'
NARR_IZLEME = "Kalite süzgecini geçen saat oranı tüm arşivde %71'dir; hedef en az %80. Düşüşün\n    tamamına yakını Mart–Mayıs döneminde kaynak dosyadaki bozuk bir yıl bloğundan\n    kaynaklanmaktadır. Bu blok düzeltilip yeniden yüklendiğinde kapsama hedefin üzerine çıkar;\n    Haziran'dan itibaren oran zaten %88–92 seviyesindedir. Ayrıntı ve aylık kırılım\n    Bağımsız test ve veri kalitesi bölümündedir (sayfa 10)."
NARR_S04_KUYRUK = " Dönemin ilk yarısı istikrarlıdır; 11–13 Ağustos'ta beklenen\n      cephe geçişi hem beklentiyi düşürmekte hem de belirsizliği genişletmektedir. Cephe\n      sonrasında üretim mevsim normaline dönmektedir."
NARR_S06 = 'Sütunlar arasındaki fark gün kalitesini, satırlar arasındaki fark gün içi seyri verir.\n      11–13 Ağustos sütunlarının öğle saatleri komşularından belirgin biçimde açık: cephe\n      geçişinin en çok vurduğu saatler 10:00–15:00 arasıdır. Sabah ve akşam saatleri ise\n      neredeyse hiç etkilenmemiştir.'
NARR_S07_BASLIK = "30 Temmuz'da ne oldu?"
NARR_S05_FIGCAP = "11 ve 12 Ağustos'ta eğri hem\n      alçalıyor hem yayvanlaşıyor: cephe geçişinin saatlik karşılığı budur."  # v2.144: sabit anlatı token'landı — kanonik
# varsayılan aynı metin (md5); canlıda ctx VERİDEN üretir, anlatı alanı
# gelirse o kazanır, ikisi de yoksa cümle düşer (kural 4).
NARR_S07_GOVDE = "O gün hata %12,7'ye çıktı, kazanç %20,1'e düştü — dönemin en zayıf günü. Nedeni ani\n      bulut açılmasıdır: model temkinli kalmış, öğleden sonraki gerçekleşen üretim beklentinin\n      üzerine çıkmıştır. Bu gün karneden çıkarılmadı; zayıf günler de ortalamaya girer."
NARR_S09_PROSE = "Kalibrasyonun bir modeli veriye uydurup uydurmadığı, bulunan katsayıların fiziksel\n      olarak anlamlı olup olmadığına bakılarak anlaşılır. Sistem verimi 0,942, tipik bir\n      kablolama–inverter–trafo zincirinin beklenen aralığındadır. %7,3'lük bifacial kazanç,\n      sahanın 0,16 olan zemin albedosuyla tutarlıdır."
NARR_S10_SEKIL = "Aylık geçerli saat payı. Mart–Mayıs\n      döneminde kapsama %49–58'e düşmüştür ve baskın neden tek bir kalemdir: kaynak dosyadaki\n      bozuk yıl bloğu. Haziran'dan itibaren oran %88–92 ile hedefin üzerindedir. Bu, ölçüm\n      sisteminden değil veri aktarımından kaynaklanan, düzeltilebilir bir sorundur."
ARSIV_ETIKET = '1 Şubat – 4 Ağustos 2026\n    (4.440 saat)'
# B3b-1 (v2.169): arşiv uçları GERÇEK ALANDIR (scada.arsiv_*) — D6/D15
# hükmü buradan verir, etiket yalnız sunumdur (s10 çizelge başlığı).
ARSIV_BAS = (2026, 2, 1)                   # scada.arsiv_baslangic (y, a, g)
ARSIV_BIT = (2026, 8, 4)                   # scada.arsiv_bitis
ARSIV_SAAT = 4440                          # scada.arsiv_saat
LEJANT_HATALI = 'Hatalı yıl bloğu'
NARR_S14_KAPSAMA = 'Kaynak dosyadaki bozuk yıl bloğu düzeltilene kadar kalibrasyon, olması gerekenden az saatle çalışmaktadır (sayfa 10).'
# B3b-2 (v2.170): katsayilar SAYIDIR (calibration.coefficients) — metin
# token'lari sayidan turetilir; asagidaki donmus metinler kanonik hikayenin
# birebir aynasidir (test: metin == turetim(sayi), mutasyon bekcili).
KAT_ETA_V, KAT_BIF_V = 0.942, 7.3          # coefficients.eta_bos / .bifacial_pct
KAT_ALBEDO = 0.16                          # coefficients.albedo
KAT_SAAT_V, KAT_TARIH_V = 1487, (2026, 7, 19)   # .saat / .tarih (y, a, g)
KAT_ETA = '0,942'
KAT_BIF = '%7,3'
KAT_SAAT = '1.487'
KAT_TARIH = '19 Temmuz 2026'
NARR_S07_SEKIL = 'Gün-öncesi hata dönem boyunca %6–13 bandında\n      kalmış, referansın belirgin altında seyretmiştir.'
NARR_S10_SEKIL1 = "Eğitim penceresinde hata %6,8, hiç\n    görülmemiş test döneminde %{{HOLDOUT}}'dur — aradaki fark makul, yani model ezberlememiştir."
KAL_PENCERE = ", 120 gün"                  # kanonik pencere iddiasi (v2.132)
MOD_ROZET = "MOD C · HİBRİT"               # run.mode
SAYFA_TOPLAM = 16

# ---------------------------------------------------------------- iklim arşivi (aylık üretim, MWh)
AY_TR = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
IKLIM = {
    2007: [971, 1178, 1514, 1913, 2310, 2370, 2142, 2231, 1847, 1497, 1029, 895],
    2008: [1010, 1139, 1693, 1805, 2280, 2487, 2362, 2268, 1854, 1487, 1039, 917],
    2009: [1068, 1031, 1580, 1781, 2082, 2472, 2381, 2022, 1743, 1437, 1033, 889],
    2010: [962, 1114, 1567, 1650, 2097, 2114, 2224, 1954, 1626, 1332, 1051, 877],
    2011: [941, 1081, 1572, 1604, 2114, 2246, 2452, 2236, 1718, 1378, 1036, 931],
    2012: [942, 1059, 1482, 1694, 2050, 2037, 2202, 2026, 1769, 1387, 1002, 854],
    2013: [1027, 1227, 1583, 1906, 2105, 2385, 2194, 2023, 1788, 1394, 1098, 999],
    2014: [1085, 1227, 1763, 2082, 2433, 2544, 2739, 2479, 1892, 1605, 1191, 945],
    2015: [1027, 1085, 1611, 1814, 2191, 2209, 2311, 1970, 1663, 1442, 948, 909],
    2016: [907, 1150, 1440, 1827, 2150, 2056, 2419, 2288, 1720, 1367, 1028, 811],
    2017: [1128, 1163, 1617, 1820, 2229, 2248, 2609, 2281, 1948, 1496, 1078, 905],
    2018: [1038, 1194, 1591, 1867, 2145, 2305, 2657, 2223, 1762, 1519, 1195, 853],
    2019: [1048, 1147, 1466, 1947, 2278, 2388, 2341, 2327, 1794, 1470, 1046, 857],
    2020: [1022, 1043, 1473, 1694, 2016, 2096, 2266, 2030, 1652, 1338, 1059, 853],
    2021: [1029, 1096, 1421, 1876, 2281, 2251, 2380, 2257, 1830, 1477, 1030, 937],
    2022: [1001, 1246, 1662, 1977, 2520, 2581, 2308, 2103, 1936, 1417, 1115, 960],
    2023: [893, 974, 1489, 1723, 2064, 2183, 2130, 1938, 1673, 1291, 932, 856],
    2024: [1006, 1150, 1454, 1730, 2066, 2167, 2337, 2088, 1786, 1434, 1159, 808],
    2025: [933, 995, 1377, 1490, 1895, 2105, 2082, 1916, 1553, 1345, 938, 702],
    2026: [922, 965, 1238, 1420, 2205, 2173, 2105, None, None, None, None, None],
}
TAM_YILLAR = list(range(2007, 2026))          # 19 tam yıl
LTA_AY = [round(sum(IKLIM[y][m] for y in TAM_YILLAR) / len(TAM_YILLAR)) for m in range(12)]
LTA_YIL = sum(LTA_AY)


def ay_pct(m, p):
    """Bir ayın 19 yıllık dağılımından yüzdelik (doğrusal ara değer)."""
    v = sorted(IKLIM[y][m] for y in TAM_YILLAR)
    k = (len(v) - 1) * p / 100
    i = int(k)
    return v[i] + (v[min(i + 1, len(v) - 1)] - v[i]) * (k - i)


# ---------------------------------------------------------------- günlük tahmin (16 gün)
# daily[].p50_kw / p10_kw / p90_kw — sayfa 1, 4, 5, 6
P50_GUN = [65.8, 65.0, 66.4, 68.3, 69.4, 67.1, 59.3, 53.6, 58.9,
           65.6, 68.8, 69.6, 67.9, 66.2, 63.5, 61.0]
HW_GUN = [4.3, 4.2, 4.3, 4.4, 4.5, 4.4, 7.6, 9.7, 7.4,
          4.3, 4.5, 4.5, 4.4, 4.3, 4.2, 4.0]
GUN_ETIKET = ["%02d" % d for d in range(5, 21)]
# C-5/1 + D21 (v2.155): ham tarih yüzeyleri — DONEM forecast.start/end'den,
# eksen daily[].date'ten türer; iki AYRI girdi bloğu birbirini tutmalı.
GUN_TARIH = ["2026-08-%02d" % d for d in range(5, 21)]
FORECAST_BASLANGIC, FORECAST_BITIS = GUN_TARIH[0], GUN_TARIH[-1]
CEPHE = (6, 8)                                # cephe geçişi: vurgulu gün aralığı (11–13 Ağu)

# ---------------------------------------------------------------- saatlik taban eğrisi
# hourly[].p50_kw (tipik gün) — sayfa 5, 6; toplamı 65,8 MWh
BASE_KW = [489, 1048, 2004, 3412, 5175, 6991, 8413, 9017, 8610, 7322, 5547, 3743,
           2250, 1205, 574]                   # 05–06 … 19–20 saat dilimleri
PEAK = 9600.0                                 # renk ölçeği üst sınırı [kW]

# ---------------------------------------------------------------- doğruluk karnesi (son 30 gün)
# accuracy.report_card[] — sayfa 7
KARNE_WM = [10.4, 9.1, 11.2, 7.8, 6.2, 6.4, 12.9, 9.3, 8.6, 10.2, 7.1, 8.4, 11.0,
            8.2, 8.9, 9.5, 10.6, 8.0, 9.9, 11.1, 7.6, 8.3, 9.2,
            8.1, 9.0, 12.7, 8.5, 7.4, 8.8, 9.6]
KARNE_SK = [.36, .40, .31, .44, .47, .45, .28, .39, .41, .35, .46, .38, .33,
            .42, .37, .36, .34, .43, .35, .32, .44, .40, .38,
            .445, .404, .201, .422, .464, .409, .377]
KARNE_NAIF = [16.2, 15.2, 16.2, 13.9, 11.7, 11.6, 17.9, 15.2, 14.6, 15.7, 13.1, 13.5, 16.4, 14.1, 14.1,
              14.8, 16.1, 14, 15.2, 16.3, 13.6, 13.8, 14.8, 14.6, 15.1, 15.9, 14.7, 13.8, 14.9, 15.4]   # naif WMAPE (v2.137: ÖLÇÜMdür, türetilmez)
KARNE_NAIF_KAYNAK = "alan"
KARNE_OLCULDU = [True] * 30                # v2.140: statik kanonikte hepsi ölçülü
# C-3b (v2.151): s08 "bütünlük kuralları" kopyasının makine karşılığı —
# eşikler TEK kaynaktan (kullanıcı kararı 17 Ağu: mekanizma eklendi, metin
# kaldı; şartname bu sayıları tanımlamıyordu, bu sözlük kayıt makamıdır).
KARNE_ESIK = {"kapsama_pct": 60,           # gün içi geçerli saat oranı tabanı
              "kucuk_orneklem_gun": 14}    # pencerede en az geçerli gün
KARNE_KAPSAMA = [100] * 30                 # kanonikte hepsi tam kapsamalı
                                           # (olculdu=true ile tutarlı dondurma)
KARNE_H72 = [14.1, 12.4, 15.2, 10.6, 8.4, 8.7, 17.5, 12.6, 11.7, 13.9, 9.7, 11.4, 15, 11.2, 12.1,
             12.9, 14.4, 10.9, 13.5, 15.1, 10.3, 11.3, 12.5, 11.9, 12.4, 16.2, 12, 10.8, 12.1, 13]   # 24–72 sa hatası, 30 gün (v2.143: ÖLÇÜMdür —
# w×1,36 uydurma çarpanı söküldü; kanonik hikâyenin ilk 23 değeri eski
# türetilmişle birebir donduruldu, kuyruk zaten ölçümdü)
KARNE_TARIH = ["%02d Tem" % d for d in range(5, 32)] + ["%02d Ağu" % d for d in (1, 2, 3)]

# ---------------------------------------------------------------- hata dağılımı — sayfa 8
PROF = [0.5, 1.0, 2.0, 3.4, 5.2, 7.0, 8.4, 9.0, 8.6, 7.3, 5.5, 3.7, 2.3, 1.2, 0.6]
MAE24 = [.07, .12, .19, .30, .42, .52, .58, .56, .49, .37, .25, .16, .10, .06]
MAE72 = [.11, .19, .31, .49, .69, .84, .90, .87, .74, .57, .38, .24, .14, .08]
MU, SD, NDAYS = -0.2, 2.0, 116                # günlük sapma: ortalama · st. sapma · geçerli gün

# ---------------------------------------------------------------- kalibrasyon şelalesi — sayfa 9
# calibration.steps[] · physics_mape · holdout_mape
SELALE_ADIM = [
    ("Ham fizik", None, "bas"),
    ("Sistem verimi", -1.8, "iyi"),
    ("Bifacial kazanç", -1.2, "iyi"),
    ("Bulut geçişi", +0.3, "kotu"),
    ("ML artık öğrenme", -2.0, "iyi"),
    ("Hibrit model", None, "bas"),
]
SELALE_BAS, SELALE_BIT = 13.6, 8.9

# ---------------------------------------------------------------- veri kalitesi — sayfa 10
# scada.quality_flags — aylık kırılım + bayrak tablosu
KALITE_AYLAR = ["Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz"]
KALITE_GECERLI = [84, 58, 49, 55, 88, 92]
KALITE_HATALI = [10, 36, 45, 39, 6, 3]        # kaynak dosyadaki bozuk yıl bloğu
KALITE_DIGER = [6, 6, 6, 6, 6, 5]
BAYRAK = [
    ("Hatalı yıl bloğu", "1.052", "%23,7",
     "Kaynak dosyadaki bozuk yıl etiketi düzeltilip veri yeniden yüklenmeli."),
    ("Gece üretimi", "62", "%1,4",
     "Sayaç ofseti kontrol edilmeli; gece sıfırdan büyük üretim fiziksel değildir."),
    ("Donmuş veri", "76", "%1,7",
     "Telemetri kesintisi; aynı değerin tekrarlandığı bloklar düşürüldü."),
    ("Kapasite üstü kayıt", "22", "%0,5",
     "Ölçek hatası olasılığı; kurulu güç künyesiyle çapraz doğrulanmalı."),
    ("Okunamayan satır", "66", "%1,5",
     "Ayrıştırılamayan kayıtlar; örnekleri veri ekinde listelenir."),
]

# ---------------------------------------------------------------- santral künyesi — sayfa 13
# plant.* / sources.*
SAHA = [
    ("Koordinat", "37,9000°K · 32,5000°D"),
    ("Yükseklik", "1.016 m"),
    ("Kurulu güç", "12,4 MWp / 10,0 MWe"),
    ("DC/AC oranı", "1,24"),
    ("Panel eğimi / azimut", "25° / 180° (güney)"),
    ("İzleyici", "sabit eğim"),
    ("Panel / inverter", "MonoPERC-540B · INV-3125K"),
    ("Saat dilimi", "Europe/Istanbul (UTC+3)"),
]
KUNYE = [
    ("Hava tahmini", "Saatlik ışınım, bulut, sıcaklık, rüzgâr", "saatlik · ~11 km",
     "her tahmin için 16 gün", "UTC"),
    ("Santral verisi (SCADA)", "Gerçekleşen üretim ve kalite bayrakları", "15 dakika → saatlik",
     "1 Şubat – 4 Ağustos 2026", "UTC"),
    ("İklim arşivi", "Aylık üretim geçmişi", "aylık", "2007–2025 (19 tam yıl) + 2026",
     "yerel ay"),
    ("Zemin albedosu", "Bifacial kazanç hesabının girdisi (0,16)", "sabit", "kurulumda girilir",
     "—"),
    ("Santral künyesi", "Kurulu güç, koordinat, eğim/azimut, panel ve inverter", "—",
     "kurulumda bir kez", "Europe/Istanbul"),
]

# ---------------------------------------------------------------- tahmin evrimi — sayfa 14
# run arşivi: (tarih, P50, ± yarı bant) — hedef gün 05 Ağu
EVRIM = [("29 Tem", 63.2, 7.4), ("30 Tem", 63.9, 6.6), ("31 Tem", 64.6, 5.9),
         ("01 Ağu", 66.1, 5.1), ("02 Ağu", 67.3, 4.3), ("03 Ağu", 64.5, 3.4),
         ("04 Ağu", 65.8, 2.8)]

# ---------------------------------------------------------------- dönem özeti (totals.* / accuracy.*)
TOPLAM_P50_MWH = 1036.4        # totals.p50_mwh
TOPLAM_P10_MWH = 1005          # totals.p10_mwh — taahhüt alt sınırı
TOPLAM_P90_MWH = 1068          # totals.p90_mwh
KF_PCT = 27.0                  # totals.capacity_factor
WMAPE120_PCT = 9.4             # accuracy.wmape_0_24 (120 gün)
SKILL120_PCT = 38              # accuracy.skill (120 gün, tam sayı gösterim)
KAPSAMA_PCT = 71               # scada.coverage_pct
KESINTISIZ_GUN = 87            # accuracy.uninterrupted_days
RAPOR_ID = "PVQ-2026-08-04-C-0417"       # report.id (yer tutucu)
HAZIRLANMA = "4 Ağustos 2026 · 08:00"    # run.run_at (görsel)
EPOSTA = "rapor@pvquant.example"         # report.contact (yer tutucu)

# ================================================================ JSON adaptörü (E.2 Adım 2)
# PVQ_VERI_JSON ortam değişkeni bir JSON v2.0/v2.1 dosyası gösteriyorsa
# yukarıdaki varsayılanlar oradan gelen değerlerle değiştirilir.
# Alan eşlemesi: docs/veri_haritasi.md · Örnek girdi: ornek_girdi_v21.json
AY_UZUN = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
           "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]


def _tr(x, d=1):
    # B3b-2: yukleyici token turetiminde kullanir — tanim cagridan once olmali
    return ("%.*f" % (d, x)).replace(".", ",")


def _tarih(s):
    y, m, d = (int(x) for x in s.split("-"))
    return y, m, d


def _json_yukle(path):
    import json
    J = json.load(open(path, encoding="utf-8"))
    g = {}

    # kimlik
    g["SANTRAL"] = J["plant"]["name"]
    g["SEBEKE_AC_MWE"] = J["plant"].get("sebeke_ac_mwe")   # yoksa None → "—"
    g["MUSTERI"] = J["report"]["customer"]
    g["KAPASITE_MWP"] = float(J["plant"].get("capacity_kwp", 12400)) / 1000  # v2.103
    g["MOD_ROZET"] = J["run"]["mode"]
    g["SAYFA_TOPLAM"] = J["run"]["pages"]
    (y1, m1, d1), (y2, m2, d2) = _tarih(J["forecast"]["start"]), _tarih(J["forecast"]["end"])
    g["FORECAST_BASLANGIC"] = J["forecast"]["start"]   # D21 (v2.155): ham uçlar
    g["FORECAST_BITIS"] = J["forecast"]["end"]
    g["DONEM"] = ("%02d–%02d %s %d" % (d1, d2, AY_UZUN[m1 - 1], y1) if (y1, m1) == (y2, m2)
                  else "%02d %s – %02d %s %d" % (d1, AY_UZUN[m1 - 1], d2, AY_UZUN[m2 - 1], y2))

    # iklim arşivi + türetilenler
    g["IKLIM"] = {int(y): v for y, v in J["climate"]["monthly_history"].items()}
    g["TAM_YILLAR"] = [y for y in sorted(g["IKLIM"]) if None not in g["IKLIM"][y]]
    g["LTA_AY"] = [round(sum(g["IKLIM"][y][m] for y in g["TAM_YILLAR"]) / len(g["TAM_YILLAR"]))
                   for m in range(12)]
    g["LTA_YIL"] = sum(g["LTA_AY"])

    # günlük tahmin
    D = J["daily"]
    g["P50_GUN"] = [x["p50_mwh"] for x in D]
    g["HW_GUN"] = [x["half_mwh"] for x in D]
    g["GUN_ETIKET"] = ["%02d" % _tarih(x["date"])[2] for x in D]
    g["GUN_TARIH"] = [x["date"] for x in D]            # D21 (v2.155)
    cf = [i for i, x in enumerate(D) if x.get("flag") == "cephe"]
    g["CEPHE"] = (min(cf), max(cf)) if cf else None

    # saatlik taban
    g["BASE_KW"] = J["hourly_typical"]["base_kw"]
    g["PEAK"] = J["hourly_typical"]["peak_kw"]

    # doğruluk karnesi
    K = J["accuracy"]["report_card"]
    g["KARNE_WM"] = [x["wmape_0_24"] for x in K]
    g["KARNE_SK"] = [x["skill"] for x in K]
    # v2.137 (Faz B1): naif alandan okunur (spec #4). Eski girdilerde alan
    # yoksa GECICI turetme korunur ama kaynak isaretlenir — D4 turetilmis
    # naifi totolojik sayar ve uyari verir (kok is: kontrat alani).
    _nf = [x.get("naif_wmape") for x in K]
    _olc = [bool(x.get("olculdu", True)) for x in K]
    # v2.140: kaynak "alan"dır — anahtar girdide var VE her ÖLÇÜLÜ satırda
    # dolu ise (ölçülmemiş satırın None'ı alan eksikliği sayılmaz).
    if any("naif_wmape" in x for x in K) and \
            all(n is not None for n, o in zip(_nf, _olc) if o):
        g["KARNE_NAIF"], g["KARNE_NAIF_KAYNAK"] = _nf, "alan"
    else:
        g["KARNE_NAIF"] = [round(w / (1 - s), 1)
                           if (w is not None and s is not None) else None
                           for w, s in zip(g["KARNE_WM"], g["KARNE_SK"])]
        g["KARNE_NAIF_KAYNAK"] = "turetilmis"
    # v2.143: 24-72 hatası HER satır için ölçümdür (None geçirgen);
    # 'yalnız son 7' sözleşmesi ve w×1,36 uydurması bitti.
    g["KARNE_H72"] = [x.get("wmape_24_72") for x in K]
    g["KARNE_OLCULDU"] = [bool(x.get("olculdu", True)) for x in K]
    # C-3b (v2.151): gün içi kapsama yüzdesi — alan yoksa None (D19
    # "denetlenemedi" der; v2.152 worker'ı doldurur).
    g["KARNE_KAPSAMA"] = [x.get("kapsama_pct") for x in K]
    g["KARNE_TARIH"] = ["%02d %s" % (_tarih(x["date"])[2], AY_TR[_tarih(x["date"])[1] - 1])
                        for x in K]

    # hata dağılımı
    E = J["error_dist"]
    g["PROF"], g["MAE24"], g["MAE72"] = E["prof_mw"], E["mae24"], E["mae72"]
    g["MU"], g["SD"], g["NDAYS"] = E["mu"], E["sd"], E["ndays"]

    # kalibrasyon şelalesi
    C = J["calibration"]
    if "steps" in C:
        g["SELALE_ADIM"] = [(s["label"], s["delta"], s["kind"]) for s in C["steps"]]
    else:
        # v2.132: B4 karari TERSINE cevrildi — 10 Agu vakasinin koku, gercek
        # uclarla (fizik/holdout) SABIT motor adimlarini ayni selalede
        # karistirmakti. Adim kirilimi girdide yoksa selale HIC basilmaz;
        # s09 yerine tek satir "veri eksik" basar (gorev recetesi: yanlis
        # selale, selalesizlikten kotudur). None bu isarettir.
        g["SELALE_ADIM"] = None
    g["SELALE_BAS"], g["SELALE_BIT"] = C["physics_mape"], C["holdout_mape"]
    _wd = C.get("window_days")
    g["KAL_PENCERE"] = (", %d gün" % int(_wd)) if _wd else ""

    # veri kalitesi
    Q = J["scada"]["quality_monthly"]
    g["KALITE_AYLAR"], g["KALITE_GECERLI"] = Q["aylar"], Q["gecerli"]
    g["KALITE_HATALI"], g["KALITE_DIGER"] = Q["hatali"], Q["diger"]
    g["BAYRAK"] = [(b["ad"], b["saat"], b["pay"], b["aksiyon"])
                   for b in J["scada"]["quality_flags"]]

    # dönem özeti (E.2 Adım 2b)
    T = J["totals"]
    g["TOPLAM_P50_MWH"], g["TOPLAM_P10_MWH"] = T["p50_mwh"], T["p10_mwh"]
    g["TOPLAM_P90_MWH"], g["KF_PCT"] = T["p90_mwh"], T["capacity_factor"]
    g["WMAPE120_PCT"] = J["accuracy"]["wmape_0_24"]
    g["SKILL120_PCT"] = J["accuracy"]["skill"]
    g["KESINTISIZ_GUN"] = J["accuracy"]["uninterrupted_days"]
    g["KAPSAMA_PCT"] = J["scada"]["coverage_pct"]
    # B3b-1: arşiv uçları alandan; alan yoksa None — D6/D15 etiket yedeğine düşer
    _ab = J["scada"].get("arsiv_baslangic"); _abt = J["scada"].get("arsiv_bitis")
    g["ARSIV_BAS"] = _tarih(_ab) if _ab else None
    g["ARSIV_BIT"] = _tarih(_abt) if _abt else None
    g["ARSIV_SAAT"] = J["scada"].get("arsiv_saat")
    g["RAPOR_ID"] = J["report"]["id"]
    g["EPOSTA"] = J["report"]["contact"]
    py, pm, pd_, ps = J["run"]["prepared"][:4], J["run"]["prepared"][5:7], J["run"]["prepared"][8:10], J["run"]["prepared"][11:16]
    g["HAZIRLANMA"] = "%d %s %s · %s" % (int(pd_), AY_UZUN[int(pm) - 1], py, ps)
    # c2a (v2.106): tarih token'ları girdiden — kanonikte birebir aynı metinler
    g["GUN_SAYISI"] = len(D)
    _ilk_y, _ilk_m, _ilk_d = _tarih(D[0]["date"])
    g["AY_YIL"] = "%s %d" % (AY_UZUN[_ilk_m - 1], _ilk_y)
    import datetime as _dtm
    _p = _dtm.date(int(py), int(pm), int(pd_))
    _b = _p - _dtm.timedelta(days=METRIK_PENCERE_GUN - 1)
    _m = _b + _dtm.timedelta(days=95)
    g["METRIK_PENCERE"] = "%d %s – %d %s %d (%d gün)" % (
        _b.day, AY_UZUN[_b.month - 1], _p.day, AY_UZUN[_p.month - 1], _p.year,
        METRIK_PENCERE_GUN)
    # c2b (v2.107): anlatılar GİRDİNİN parçası — motor hikâye taşımaz
    _N = J.get("narrative") or {}
    g["NARR_EXEC_1"] = _N.get("exec_1", "")
    g["NARR_EXEC_2"] = _N.get("exec_2", "")
    g["NARR_EXEC_3"] = _N.get("exec_3", "")
    g["NARR_EXEC_4"] = _N.get("exec_4", "")
    g["NARR_IZLEME"] = _N.get("izleme", "")
    g["NARR_S05_FIGCAP"] = _N.get("s05_figcap", "")
    g["NARR_S04_KUYRUK"] = _N.get("s04_kuyruk", "")
    g["NARR_S06"] = _N.get("s06", "")
    g["NARR_S07_BASLIK"] = _N.get("s07_baslik", "")
    g["NARR_S07_GOVDE"] = _N.get("s07_govde", "")
    g["NARR_S09_PROSE"] = _N.get("s09_prose", "")
    g["NARR_S10_SEKIL"] = _N.get("s10_sekil", "")
    g["ARSIV_ETIKET"] = _N.get("arsiv_etiket", "—")
    g["LEJANT_HATALI"] = _N.get("lejant_hatali", "hatalı")
    g["NARR_S14_KAPSAMA"] = _N.get("s14_kapsama", "")
    # B3b-2 (v2.170): katsayilar calibration.coefficients ALANINDAN; alan
    # yoksa narrative.kat_* yedegi (eski JSON), o da yoksa durust "—".
    _CF = C.get("coefficients") or {}
    g["KAT_ETA_V"] = _CF.get("eta_bos")
    g["KAT_BIF_V"] = _CF.get("bifacial_pct")
    g["KAT_ALBEDO"] = _CF.get("albedo")
    g["KAT_SAAT_V"] = _CF.get("saat")
    _kt = _CF.get("tarih")
    g["KAT_TARIH_V"] = _tarih(_kt) if _kt else None
    g["KAT_ETA"] = (_tr(g["KAT_ETA_V"], 3) if g["KAT_ETA_V"] is not None
                    else _N.get("kat_eta", "—"))
    g["KAT_BIF"] = ("%" + _tr(g["KAT_BIF_V"], 1) if g["KAT_BIF_V"] is not None
                    else _N.get("kat_bif", "—"))
    g["KAT_SAAT"] = ("{:,}".format(int(g["KAT_SAAT_V"])).replace(",", ".")
                     if g["KAT_SAAT_V"] is not None else _N.get("kat_saat", "—"))
    g["KAT_TARIH"] = ("%d %s %d" % (g["KAT_TARIH_V"][2],
                                    AY_UZUN[g["KAT_TARIH_V"][1] - 1],
                                    g["KAT_TARIH_V"][0])
                      if g["KAT_TARIH_V"] else _N.get("kat_tarih", "—"))
    g["NARR_S07_SEKIL"] = _N.get("s07_sekil", "")
    g["NARR_S10_SEKIL1"] = _N.get("s10_sekil1", "")
    g["EGITIM_SERIT"] = "<i>%d %s %d</i><i>%d %s</i><i>%d %s %d</i>" % (
        _b.day, AY_UZUN[_b.month - 1], _b.year,
        _m.day, AY_UZUN[_m.month - 1],
        _p.day, AY_UZUN[_p.month - 1], _p.year)

    # künye ve evrim
    g["SAHA"] = [tuple(p) for p in J["plant"]["display"]]
    g["KUNYE"] = [tuple(k) for k in J["sources"]["display"]]
    g["EVRIM"] = [(e["date"], e["p50"], e["half"]) for e in J["history"]["evolution"]]

    globals().update(g)


import os as _os2
_J = _os2.environ.get("PVQ_VERI_JSON")
if _J:
    _json_yukle(_J)

# c1 (v2.105): günlük fan ekseni veri-güdümlü — kanonik girdide 40/80'i
# birebir üretir (min P10=43,9→40; max P90=74,1→80).
import math as _math
IKLIM_ARALIK = "%d–%d" % (min(IKLIM), max(IKLIM))   # c2a: matris yıl aralığı
# v2.181: BANT gözlenebilir DURUMDUR — half listesi tam ve toplam uçları
# doluysa bant var; tek None bile bantsız sayılır (yarım bant çizilmez,
# uydurulmaz — v2.178 'yanlış bant, bantsızlıktan kötüdür' ailesi).
# Kanonik girdide True → md5 birebir.
BANT_VAR = (all(h is not None for h in HW_GUN)
            and TOPLAM_P10_MWH is not None and TOPLAM_P90_MWH is not None)
GUN_YMIN = int(_math.floor(min(v - (h or 0) for v, h in zip(P50_GUN, HW_GUN)) / 10.0)) * 10
GUN_YMAX = int(_math.ceil(max(v + (h or 0) for v, h in zip(P50_GUN, HW_GUN)) / 10.0)) * 10

# v2.131: s06 matris ölçekleyicisi tipik gün TOPLAMINDAN türetilir — gömülü
# 65,8 sabiti kanonik girdide birebir aynı değeri üretir (md5 korunur);
# canlı santralde matris sütunları günlük P50'yi tanım gereği tutar (D3).
MATRIS_OLCEK_MWH = sum(BASE_KW) / 1000.0

# v2.135: şelaledeki iyileşme yüzdesi TEK yerde türetilir (spec #7 — baş/sondan
# yeniden hesaplanabilir; denetim D12 bayat/elle değere karşı bekçiler).
IYILESME_PCT = (round((SELALE_BAS - SELALE_BIT) / SELALE_BAS * 100, 1)
                if SELALE_BAS else None)

# v2.139 (Faz B2): yillik istatistikler TEK yerde turetilir (spec #5 —
# yillik Pxx, aciklanan sigma ve z ile yeniden uretilebilir olmali).
# s11 bunlari tuketir; denetim D17, IKLIM'den yeniden hesaplayip yuzeydeki
# degerleri bekciler (bayat/elle deger + formul kaymasi: SD ORNEKLEM
# sapmasidir, n-1 boleni sozlesmedir). Normal varsayimi YALNIZ yillik
# egride kullanilir (gunluk/saatlik bantlar kantil yontemiyle gelir).
Z_YIL = {50: 0.0, 75: 0.6745, 90: 1.2816}
if len(TAM_YILLAR) >= 2:
    YIL_TOPLAM = [sum(IKLIM[y]) for y in TAM_YILLAR]
    YIL_ORT = sum(YIL_TOPLAM) / len(YIL_TOPLAM)
    YIL_SD = _math.sqrt(sum((v - YIL_ORT) ** 2 for v in YIL_TOPLAM)
                        / (len(YIL_TOPLAM) - 1))
    YIL_CV_PCT = YIL_SD / YIL_ORT * 100
    PXX_YIL = {p: YIL_ORT - z * YIL_SD for p, z in Z_YIL.items()}
else:
    YIL_TOPLAM, YIL_ORT, YIL_SD, YIL_CV_PCT, PXX_YIL = [], None, None, None, None

# v2.135: KPI durumları elle değil eşikten türetilir (spec #18 — eşik ile
# değer arasındaki yön tutarlılığı; kopyadaki "hedef %10 altı / %80 üstü"
# iddialarının makine karşılığı). Kanonikte ok/ok/watch üretir (md5 korunur).
KPI_ESIK = {"WMAPE120": (10.0, "alt"), "HOLDOUT": (10.0, "alt"),
            "KAPSAMA": (80.0, "ust")}
DURUM_WMAPE120 = "ok" if WMAPE120_PCT < KPI_ESIK["WMAPE120"][0] else "watch"
DURUM_HOLDOUT = "ok" if SELALE_BIT < KPI_ESIK["HOLDOUT"][0] else "watch"
DURUM_KAPSAMA = "ok" if KAPSAMA_PCT > KPI_ESIK["KAPSAMA"][0] else "watch"


def kpi_hedef(ad, esik=None):
    """C-3 (v2.150): s03 kopya metnindeki hedef iddiası KPI_ESIK'ten türer.

    "hedef %10 altı" / "hedef %80 üstü" — sayı ve yön tek kaynaktan gelir;
    eşik değişirse kopya kendiliğinden izler (D16 zaten değer↔durum yönünü
    denetler; bu, kopya↔eşik bacağını kapatır). Kanonikte birebir aynı
    metni üretir (md5 token tekniği).
    """
    e, yon = (esik or KPI_ESIK)[ad]
    return "hedef %%%s %s" % (("%g" % e).replace(".", ","),
                              "altı" if yon == "alt" else "üstü")


def karne_uyari(gecerli, esik=None):
    """C-3b (v2.151, s08 kuralı 4): "14 günden az geçerli gün → başlığa
    uyarı" iddiasının makinesi. Anlatı VERİDEN türer: uyarı elle konmaz,
    KARNE_OLCULDU sayımından çıkar (D20 tutarlılığı bekçiler). Kanonikte
    30 geçerli gün → boş dize → md5 birebir. Renk pvq.AMBER aynasıdır
    (#A87519; pvq→veri yönlü import döngü yaratır, değer dondurulmuştur)."""
    e = (esik or KARNE_ESIK)["kucuk_orneklem_gun"]
    if gecerli >= e:
        return ""
    return (' · <span style="color:#A87519">Uyarı: küçük örneklem — '
            "%d geçerli gün (eşik %d)</span>" % (gecerli, e))


KARNE_GECERLI_GUN = sum(1 for o in KARNE_OLCULDU if o)
KARNE_UYARI = karne_uyari(KARNE_GECERLI_GUN)


# ================================================================ görsel doldurma (E.2 Adım 2b)
def _bin(x):
    return "{:,}".format(int(round(x))).replace(",", ".")


def _bin1(x):
    return ("{:,.1f}".format(x).replace(",", "X").replace(".", ",").replace("X", "."))


def doldur(s):
    """HTML/CSS içindeki {{TOKEN}} yer tutucularını güncel veriyle doldurur.
    pvq.build() her sayfada çağırır; token yoksa metin aynen geçer."""
    d = dict(SAHA)
    i_min = P50_GUN.index(min(P50_GUN))
    D = {
        "SANTRAL": SANTRAL, "MUSTERI": MUSTERI, "DONEM": DONEM,
        "NARR_EXEC_1": NARR_EXEC_1, "NARR_EXEC_2": NARR_EXEC_2, "NARR_EXEC_3": NARR_EXEC_3, "NARR_EXEC_4": NARR_EXEC_4, "NARR_IZLEME": NARR_IZLEME, "NARR_S04_KUYRUK": NARR_S04_KUYRUK, "NARR_S06": NARR_S06, "NARR_S07_BASLIK": NARR_S07_BASLIK, "NARR_S07_GOVDE": NARR_S07_GOVDE, "NARR_S09_PROSE": NARR_S09_PROSE, "NARR_S10_SEKIL": NARR_S10_SEKIL, "ARSIV_ETIKET": ARSIV_ETIKET, "LEJANT_HATALI": LEJANT_HATALI, "NARR_S14_KAPSAMA": NARR_S14_KAPSAMA, "KAT_ETA": KAT_ETA, "KAT_BIF": KAT_BIF, "KAT_SAAT": KAT_SAAT, "KAT_TARIH": KAT_TARIH, "NARR_S07_SEKIL": NARR_S07_SEKIL, "NARR_S10_SEKIL1": NARR_S10_SEKIL1,
        "RAPOR_ID": RAPOR_ID, "HAZIRLANMA": HAZIRLANMA, "EPOSTA": EPOSTA,
        "DONEM": DONEM,
        "KURULU": d.get("Kurulu güç", ""),
        "KOORD_YUK": (d.get("Koordinat", "") + " · " + d.get("Yükseklik", "")),
        "TOPLAM_P50": _bin1(TOPLAM_P50_MWH),
        # v2.181: bantsız koşuda bant token'ları '—' (uydurma değer yok).
        # Cümle-içi yüzeylerin (taahhüt satırı, s04 prozu) kural-4 düşürmesi
        # bilinçli olarak mühür-2'nin (Mod B bloğu) işi — burada yalnız değer.
        "TOPLAM_BANT": (_bin(TOPLAM_P10_MWH) + "–" + _bin(TOPLAM_P90_MWH))
                       if BANT_VAR else "—",
        "TOPLAM_P10": _bin(TOPLAM_P10_MWH) if BANT_VAR else "—",
        "KF": _tr(KF_PCT), "WMAPE120": _tr(WMAPE120_PCT),
        "SKILL120": "%d" % SKILL120_PCT,
        "FIZIK": _tr(SELALE_BAS), "HOLDOUT": _tr(SELALE_BIT),
        "IYILESME": _tr(IYILESME_PCT) if IYILESME_PCT is not None else "—",
        "KESINTISIZ": (str(int(KESINTISIZ_GUN)) if KESINTISIZ_GUN is not None
                       else "—"),  # v2.135: s03'teki elle '87' baypası kapandı
        "DURUM_WMAPE120": DURUM_WMAPE120, "DURUM_HOLDOUT": DURUM_HOLDOUT,
        "DURUM_KAPSAMA": DURUM_KAPSAMA,
        "KAPSAMA": "%d" % KAPSAMA_PCT, "KESINTISIZ": "%d" % KESINTISIZ_GUN,
        "MIN_P50": _tr(P50_GUN[i_min]),
        "MIN_HW": _tr(HW_GUN[i_min]) if BANT_VAR else "—",  # v2.181
        "TEPE_TIPIK": _tr(max(BASE_KW) / 1000 * (sum(P50_GUN) / len(P50_GUN))
                          / (sum(BASE_KW) / 1000)),
        # B3b-1: alan makamdır; display-split geri-ayrıştırması söküldü
        "SEBEKE": ("%s MWe" % _tr(SEBEKE_AC_MWE))
                  if SEBEKE_AC_MWE is not None else "—",
        # v2.131: s14 hedef günü veri-güdümlü — kanonikte '05 Ağustos' birebir
        "HEDEF_GUN": GUN_ETIKET[0] + " " + AY_YIL.split()[0],
        "KAL_PENCERE": KAL_PENCERE,  # v2.132: pencere iddiasi veriden
        "KARNE_UYARI": KARNE_UYARI,  # C-3b (v2.151): kanonikte "" — md5 birebir
        "NARR_S05_FIGCAP": NARR_S05_FIGCAP,
        "TOPLAM_P90": _bin(TOPLAM_P90_MWH) if BANT_VAR else "—",  # v2.181
    }
    for k, v in D.items():
        # v2.154: None/yanlış tip sessiz TypeError yerine İSİM söyler —
        # "replace() argument 2 must be str" hangi token'ın boş olduğunu
        # gizliyordu; eksik alan ya girdide doldurulur ya '—' basılır.
        if not isinstance(v, str):
            raise ValueError(
                "doldur: {{%s}} token'ı %s — kaynak alan boş/yanlış tipte; "
                "girdi JSON'ında ilgili alanı doldurun ya da '—' basın"
                % (k, "None" if v is None else type(v).__name__))
        s = s.replace("{{%s}}" % k, v)
    return s
