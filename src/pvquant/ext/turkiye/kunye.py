"""04.11.2026 v2.535 — Dayanak künyesi sicili: koddaki mevzuat atıflarının birincil künyesi (Resmî Gazete tarih-sayı, karar numarası) TEK yerde.

Kaynak: 03.11.2026 doğrulama arşivi (~/Desktop/PVQuant_Kapsamli_Dogrulama_Arastirmasi, 03_Kaynak_Envanteri.md; 04.11.2026 kapanışı) ve
04.11.2026 kaynak teyidi (~/Desktop/PVQuant_Kaynak_Teyit_2026-11-04). Her RG sayısı tests/data/kunye_envanteri.json ile (arşiv envanterinin
sayı → tarih kopyası) bekçi testinde sınanır; sicile arşivde tarihi doğrulanmamış künye girilmez. Kodun madde atıfları (m.110, m.69/A …) kendi
yerinde kalır; bu modül yalnız atfın hangi metne, hangi yayıma dayandığını söyler. Katsayı/değer burada YAZILMAZ.
"""
from __future__ import annotations

KUNYE: dict[str, tuple[str, str]] = {
    # kısa ad → (koddaki anılış, birincil künye)
    "DUY": ("DUY", "Elektrik Piyasası Dengeleme ve Uzlaştırma Yönetmeliği, RG 14.04.2009-27200; değişiklikler RG 28.03.2015-29309, 30.10.2016-29873, "
                   "18.01.2018-30305, 09.08.2019-30857, 02.02.2020-31027, 19.11.2022-32018, 19.12.2023-32404, 17.12.2024-32755, 21.01.2025-32789, "
                   "29.12.2025-33122, 19.10.2026-33405, 21.10.2026-33407"),
    "LUY": ("LÜY", "Elektrik Piyasasında Lisanssız Elektrik Üretim Yönetmeliği, RG 12.05.2019-30772; değişiklikler RG 09.05.2021-31479, 02.04.2026-33212, 19.10.2026-33405"),
    "LISANS": ("Lisans Yön.", "Elektrik Piyasası Lisans Yönetmeliği, RG 02.11.2013-28809; değişiklikler RG 24.02.2017-29989, 10.03.2022-31774, 17.12.2024-32755, "
                              "29.04.2026-33238, 19.10.2026-33405"),
    "DEPOLAMA_YON": ("Depolama Yön.", "Elektrik Piyasasında Depolama Faaliyetleri Yönetmeliği, RG 09.05.2021-31479; değişiklikler RG 29.12.2025-33122 (m.4(4) emre amade tanımı, "
                                     "m.5(7), EK-1a/1b/1c/1ç ve EK-2; 1.1.2026), 19.10.2026-33405 (m.6(1))"),   # v2.543 (P9)
    "YEK_YON": ("YEK Yön.", "Yenilenebilir Enerji Kaynaklarının Belgelendirilmesi ve Desteklenmesine İlişkin Yönetmelik, RG 01.10.2013-28782; değişiklikler "
                            "RG 29.04.2016-29698 (m.16–17 mülga), 23.08.2019-30867, 19.08.2021-31573, 29.12.2025-33122, 19.10.2026-33405 (m.23(6))"),
    "5346": ("5346", "5346 sayılı Yenilenebilir Enerji Kaynaklarının Elektrik Enerjisi Üretimi Amaçlı Kullanımına İlişkin Kanun, RG 18.05.2005-25819"),
    "6446": ("6446", "6446 sayılı Elektrik Piyasası Kanunu, RG 30.03.2013-28603; m.16 idari para cezası tebliğleri RG 27.11.2025-33090, 25.12.2025-33118"),
    "CK7189": ("7189 sayılı CK", "7189 sayılı Cumhurbaşkanı Kararı (1.7.2021–31.12.2030 işletmeye girecek YEK belgeli tesisler), RG 01.05.2023-32177; düzeltme RG 04.05.2023-32180"),
    "CK2949": ("CK 2949", "2949 sayılı Cumhurbaşkanı Kararı (1.1–30.6.2021 işletmeye girenler), RG 18.09.2020-31248"),
    "CK3453": ("CK 3453", "3453 sayılı Cumhurbaşkanı Kararı, RG 30.01.2021-31380 (7189 ile yürürlükten kalktı)"),
    "CK11415": ("CK 11415", "11415 sayılı Cumhurbaşkanı Kararı (on yılı dolan lisanssız tesiste fiyat), RG 13.06.2026-33279"),
    "OLCUM": ("Ölçüm Sist. Yön.", "Elektrik Piyasası Ölçüm Sistemleri Yönetmeliği, RG 28.12.2023-32413; değişiklikler RG 07.06.2024-32569, 25.09.2024-32673, "
                                  "21.12.2024-32759, 21.01.2026-33144"),
    "AFL_UE": ("AFL U&E", "GÖP ve DGP'de Asgari ve Azami Fiyat Limitlerinin Belirlenmesine İlişkin Usul ve Esaslar, Karar 5629-16, RG 21.06.2015-29393; "
                          "Karar 6851 RG 06.01.2017-29940; Karar 14459 RG 03.04.2026-33213"),
    "TUE": ("Teminat U&E", "Teminat Usul ve Esasları, Karar 6282-3, RG 28.05.2016-29725; son değişiklik Karar 14954, RG 21.10.2026-33407"),
    "SEBEKE": ("Şebeke Yön.", "Elektrik Şebeke Yönetmeliği, RG 28.05.2014-29013 (mükerrer); son değişiklik RG 29.12.2025-33122"),
    "TOPLAYICI": ("Toplayıcılık Yön.", "Elektrik Piyasasında Toplayıcılık Faaliyeti Yönetmeliği, RG 17.12.2024-32755; değişiklik RG 29.12.2025-33122"),
    "SEFFAFLIK": ("Şeffaflık Yön.", "Enerji Piyasalarında Şeffaflığa ve Piyasa Bozucu Davranışlara İlişkin Yönetmelik, RG 14.02.2026-33168; değişiklik RG 23.05.2026-33262"),
    "KARAR_14968": ("Karar 14968", "EPDK Kurul Kararı 14968 (Şeffaflık Platformu veri listesi, 1.1.2027'den), RG 20.10.2026-33406; öncesi Karar 10711"),
    "KARAR_14967": ("Karar 14967", "EPDK Kurul Kararı 14967 (dâhilî bilgi bildirimi), RG 20.10.2026-33406"),
    "KARAR_14907": ("Karar 14907", "EPDK Kurul Kararı 14907 (KÜPST, 1.11.2026 çıkarım), RG 19.10.2026-33405"),
    "KARAR_14911": ("Karar 14911", "EPDK Kurul Kararı 14911 (DUY m.110 V = 100 TL/MWh), RG 19.10.2026-33405"),
    "KARAR_14029": ("Karar 14029", "EPDK Kurul Kararı 14029 (KÜPST 2026), RG 29.12.2025-33122"),
    "KARAR_14030": ("Karar 14030", "EPDK Kurul Kararı 14030 (yöne bağlı k/l, 1.1.2026), RG 29.12.2025-33122"),
    "KARAR_13025": ("Karar 13025", "EPDK Kurul Kararı 13025 (KÜPST 2025), RG 17.12.2024-32755"),
    "KARAR_13869": ("Karar 13869", "EPDK Kurul Kararı 13869 (DSG üye dengesizlik oranı %5), RG 18.10.2025-33051"),
    "KARAR_5905": ("Karar 5905-27", "EPDK Kurul Kararı 5905-27 (02.12.2015; YEKDEM yararlanma yılları) — EPDK listesi, RG'de yayımlanmaz"),
    "KARAR_13995": ("Karar 13995", "Akıllı Sayaç Sistemlerinin Yaygınlaştırılmasına ve Kullanımına İlişkin Usul ve Esaslar, Karar 13995, RG 05.12.2025-33098"),
    "KARAR_14982": ("Karar 14982", "EPDK Kurul Kararı 14982 (dağıtım şirketi mobil uygulaması), RG 24.10.2026-33410"),
    "OSOS_UE": ("OSOS U&E", "OSOS Kapsamına Giren Tesislere İlişkin Usul ve Esaslar, RG 08.08.2015-29439"),
    "2429": ("2429", "2429 sayılı Ulusal Bayram ve Genel Tatiller Hakkında Kanun, RG 19.03.1981-17284"),
    "YAZ_SAATI": ("BKK 2016/9154", "Bütün Yurtta Yaz Saati Uygulanması Hakkında Karar (2016/9154), RG 08.09.2016-29825 — yıl boyu UTC+3; 697 sayılı Kanun RG 02.01.1926-260"),
    "AYM": ("AYM 2024/133", "Anayasa Mahkemesi 26.11.2025, E.2024/133 K.2025/233 (5346 m.6(2) kısmi iptal; yürürlük 10.12.2026), RG 10.03.2026-33192"),
    "TPYS": ("TPYS Bildirim Dokümanı", "EPİAŞ TPYS Bildirim Dokümanı (EAK ve KGÜP), duyuru 19.02.2025 (ek 648549); KGUP.csv / EAK.csv şablonları 28.02.2018; dayanak DUY RG 17.12.2024-32755"),
    "GIP_KAPI": ("GİP kapı kapanışı", "DUY m.66/A(1)(f) yetkisiyle EPİAŞ duyurusu 28.08.2018 (01.10.2018'den teslimattan 60 dk önce); KGÜP revizyonu kapanış + 30 dk DUY m.69(1)"),
}


def kunye(ad: str) -> str:
    """Kısa addan tam künye; yoksa ad aynen döner (sicil dışı atıf bekçi testinde görünür)."""
    return KUNYE[ad][1] if ad in KUNYE else ad


def blok(*adlar: str) -> str:
    """Modül başına dayanak bloğu: 'DUY: …; LÜY: …'. Kod atıf yerinde yalnız madde yazar; künye buradan bulunur."""
    return "; ".join(f"{KUNYE[a][0]}: {KUNYE[a][1]}" for a in adlar)


def bul(metin: str) -> list[dict]:
    """Serbest metindeki anılışlara göre künye listesi (Takvim/Hakkında ipucu): 'DUY m.132/A' → DUY künyesi."""
    if not metin:
        return []
    out = []
    for ad, (kisa, tam) in KUNYE.items():
        if kisa in metin or (ad == "LUY" and "LÜY" in metin) or (ad == "6446" and "6446" in metin) or (ad == "5346" and "5346" in metin):
            out.append({"ad": ad, "kisa": kisa, "kunye": tam})
    return out


def rg_sayilari() -> set[str]:
    import re
    return set(re.findall(r"RG\s+\d{1,2}\.\d{1,2}\.\d{4}-(\d{5})\b", " ".join(t for _, t in KUNYE.values())))
