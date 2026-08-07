# -*- coding: utf-8 -*-
"""veri.py — raporun TÜM sabit verisi tek kaynaktan (Dalga E.2, Adım 1).

Kural: bir sayı birden fazla sayfada görünüyorsa buradan türetilir.
JSON v2.0 adaptörü yazıldığında yalnız bu modül değişecek; build_sXX
dosyaları ve pvq.py veriye dokunmayacak. Alan eşlemesi: docs/veri_haritasi.md
"""

# ---------------------------------------------------------------- kimlik
SANTRAL = "Konya GES"                      # plant.name
MUSTERI = "Anadolu Enerji A.Ş."            # report.customer (şema v2.1)
DONEM = "05–20 Ağustos 2026"               # forecast.horizon
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
KARNE_H72_KUYRUK = [11.9, 12.4, 16.2, 12.0, 10.8, 12.1, 13.0]   # son 7 günün 24–72 sa hatası
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
