"""Kural ve parametre sürüm tablosu (F-01) — uzlaştırma kuralı TESLİM GÜNÜNE ve SEGMENTE göre seçilir.

Neden: DUY m.110 formülü ve katsayıları 2025–2027 arasında birkaç kez değişti; tarihsiz sabit (k = l = 0,03) geçmiş ayı
o ayın kuralıyla hesaplayamaz, 1.11.2026'dan sonra her ay yanlış olur. Bu modül «hangi tarihte hangi kural» sorusunun tek
kaynağıdır; hesap motoru (dengesizlik.py) buradan okur, ekran «kural: …» etiketini buradan basar.

Birincil kaynaklar (29.10.2026'da RG/mevzuat.gov.tr'den okundu; 31.10.2026 mevzuat araştırması — ~/Desktop/PVQuant_Acik_Konular_Arastirma,
bulgular/08–14 — her kararı RG PDF'inden ikinci kez doğruladı, çelişkiler Ç1–Ç5 bu sürümde (v2.510) işlendi):
  - DUY m.110(1)-(2) (RG 29.12.2025-33122 Md.17, yürürlük 1.1.2026; toplama RG 19.10.2026-33405): EDT(−) = EDM(−)·max(V,NPTF,SMF_N)·(1+k_u);
    max = AFL ise EDM(−)·AFL·1,05·(1+k_u). EDT(+) = EDM(+)·min(NPTF,SMF_P)·(1−l_u); min < V ise EDM(+)·(−1)·B·(1+l_u).
    V başlangıç 150, B başlangıç 100 TL/MWh. EDTA = ΣΣ max(EDT(+);0), EDTB = ΣΣ EDT(−) − ΣΣ min(EDT(+);0) (19.10.2026'dan).
  - Eski formül (RG 2.2.2020-31027 Md.32; 31.12.2025'e kadar): EDT(−) = EDM(−)·max(NPTF,SMF)·(1+k); EDT(+) = EDM(+)·min(NPTF,SMF)·(1−l).
  - Karar 14030 (RG 29.12.2025): 1.1.2026 teslim gününden: sistem açık → l 0,03 / k 0,06; fazla → l 0,06 / k 0,03; dengede → 0,03 / 0,03.
  - Karar 14911 (RG 19.10.2026): V = 100 TL/MWh, yayımı takip eden fatura döneminden (Kasım 2026 → 1.11.2026).
  - DUY m.110(3) (RG 17.12.2024-32755): KÜPST = Σ KÜPSM·max(750; NPTF; SMF)·n.
  - Karar 14029 (RG 29.12.2025; 1.1.2026): UDÜPS = |UEVM − BUDÜP|; KÜPSM = UDÜPS − m·BUDÜP (UDÜPS > m·BUDÜP ise, değilse 0);
    m güneş 0,08, iletime bağlı lisanssız 0,20; n YEK: aylık arıza ≥30 ise 0,08 değilse 0,05; iletime bağlı lisanssız 0,02; topluluk 0,05.
  - Karar 14907 (RG 19.10.2026; yayımı takip eden fatura dönemi → 1.11.2026): UDÜPS = |(UEVM − UEÇM) − BUDÜP| (net); m/n güneşte aynı;
    dağıtıma bağlı lisanssız («piyasa katılımcısı bazlı»; UEVÇB DUY m.110(6)(b)(3)) m 0,25 / n 0,01; iletime bağlı lisanssız 0,20 / 0,02
    (14029'dan sürer); Md.1(3): lisanssızlarda yalnız üretim miktarı (net sapma yok → Ç2); Md.5: LÜY m.5(1)(ç),(d),(e) kapsamındaki iletime
    bağlı tesislere karar uygulanmaz (santral ayarı `luy_istisna` → Ç3); Md.6: 14029 kalkar; Geçici 1: tüketim UEÇB bentleri 1.1.2027'den.
  - Karar 13025 (RG 17.12.2024-32755 s.1–3; 1.1.2025): güneş m 0,10 (Md.3(1)); YEK n: «Arıza =>40 ise 0,05, değil ise 0,03» (Md.2(1)(c)). Zincir
    7524 (RG 18.1.2018) → 9422 (1.8.2020) → 11589-2 (1.2.2023) → 13025 → 14029 (1.1.2026) → 14907 (1.11.2026); 1.8.2020 öncesi etiket 7524 (Ç5).
  - Karar 13869 (RG 18.10.2025-33051): DSG üyesi dengesizlik oranı ≤ %5 → bireysel miktar grup içinde (1.1.2026'dan; bitiş yok); 2025: %10
    (DUY m.111(5), RG 17.12.2024 Md.24). m.111(5): oran «her yılın 1 Aralık tarihine kadar» Kurul kararıyla düşürülür (son tarih, karar günü değil).
  - AFL zinciri `_AFL_ZINCIRI`: 1.7.2015'ten 4.4.2026'ya her halka RG karar PDF'iyle (Ç1: 1.9.2022 öncesi 600–4.000, formüllü aylar 563–1.745).
  - RG 21.1.2025-32789 Md.13 + Md.20(b): m.110(1)-(4) 1.1.2027'de değişir (tek EDT_f; V/B/AFL ve EDTA/EDTB yok; tek k/l; KÜPST 15 dk «ç»);
    30.10.2026'ya kadar ertelenmedi/değiştirilmedi, ama 33122/33405 aynı fıkraları sonradan yeniden yazdı ve tek k/l ile «ç» bazlı KÜPSM
    kararları yok → hukuken BELİRSİZ (`BELIRSIZ_2027_GEREKCE`). Varsayılan: 2026 rejimi sürer, her 2027 sonucu «belirsiz» bayrağı taşır.
  - DUY son değişiklik RG 21.10.2026-33407 (m.132/E, teminat; uzlaştırmaya etkisiz).
Doğrulanamayanlar: 2025 k = l = 0,03'ü koyan kararın numarası (değer EPDK 4-16180 taslağı «Mevcut Metin» ile teyitli); 2025 iletime bağlı
lisanssız m/n; GTŞ/toplayıcı UEVÇB'si 1.11.2026 öncesi; 2027 DSG oranı (karar en geç 1.12.2026); Karar 7524 0,015 penceresi; 2016–2019 AFL.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

IST = "Europe/Istanbul"
YONLER = ("acik", "fazla", "dengede")

# ---------------------------------------------------------------- segment → KÜPST hesap birimi ------------------------
# «santral»: KÜPST santralin kendi UEVÇB'sinde · «portfoy_uevcb»: GTŞ/toplayıcı UEVÇB'sinde (santral sahibinde 0) · «yok»: uygulanmaz
KUPST_BIRIMI = {
    "lisansli_serbest": "santral", "lisansli_yekdem": "santral", "yeka": "santral",
    "lisanssiz_iletim": "santral", "lisanssiz_dagitim": "portfoy_uevcb", "oz_tuketim_saatlik": "yok",
}


@dataclass(frozen=True)
class EdtKurali:
    rejim: str                  # "2025" | "2026"
    k: dict[str, float]         # yön → k (negatif dengesizlik)
    l: dict[str, float]         # yön → l (pozitif dengesizlik)
    V: float | None             # 2026: 150 → 100 (1.11.2026)
    B: float | None             # 2026: 100
    AFL: float | None           # azami fiyat limiti (AFL dalı yalnız 2026)
    toplama: str                # "net" (2025, tek EDT) | "edta_net" (1.1–18.10.2026) | "edta_ayrik" (19.10.2026'dan)
    dayanak: str
    surum: str


@dataclass(frozen=True)
class KupstKurali:
    m: float | None             # tolerans katsayısı (BUDÜP'ün oranı); None → doğrulanamadı
    n: float | None             # fiyat katsayısı; None → doğrulanamadı
    n_ariza: float | None       # aylık arıza eşiği aşılınca n
    ariza_esigi: int | None
    taban: float                # fiyat tabanı (750 TL/MWh, 1.1.2025'ten)
    net_sapma: bool             # 14907: UEÇM düşülür
    birim: str                  # KUPST_BIRIMI değeri
    dayanak: str
    surum: str

    def n_etkin(self, ariza_sayisi: int = 0) -> float | None:
        if self.n is None:
            return None
        if self.n_ariza is not None and self.ariza_esigi is not None and ariza_sayisi >= self.ariza_esigi:
            return self.n_ariza
        return self.n


@dataclass(frozen=True)
class Kural:
    tarih: date
    segment: str | None
    edt: EdtKurali
    kupst: KupstKurali
    dsg_esik: float
    dsg_dayanak: str
    belirsiz_2027: bool

    @property
    def surum(self) -> str:
        return f"{self.edt.surum}+{self.kupst.surum}"


# ---------------------------------------------------------------- tarihli parametreler --------------------------------
# AFL zinciri — her halka RG karar PDF'inden okundu (31.10.2026 araştırması, bulgular/08.md §8.2). Tarih = EPİAŞ'ın uyguladığı teslim günü;
# RG yürürlüğü yayım günü olan kararlarda (9598, 10489, 10978) EPİAŞ ertesi teslim gününden uyguladı. Formüllü dönem (7.10.2020–31.3.2022)
# EPİAŞ aylık duyurularından (Wayback; PTF serisinden yeniden hesaplanmadı). 1.7.2015–31.12.2019: 2.000 (geçici 1(2); 2016–2019 doğrulanmadı).
_AFL_ZINCIRI: tuple[tuple[date, float, str], ...] = (
    (date(2026, 4, 4), 4500.0, "Karar 14459 (RG 3.4.2026-33213 s.47)"),
    (date(2025, 4, 5), 3400.0, "Karar 13423 (RG 5.4.2025-32861)"),
    (date(2024, 7, 1), 3000.0, "Karar 12716 (RG 29.6.2024-32587 s.26)"),
    (date(2023, 7, 4), 2700.0, "Karar 11933 (RG 4.7.2023-32238; yürürlük maddesi yok, EPİAŞ 4.7.2023 teslim gününden)"),
    (date(2023, 4, 1), 2600.0, "Karar 11772 (RG 31.3.2023-32149 s.5)"),
    (date(2023, 3, 1), 3050.0, "Karar 11682 (RG 1.3.2023-32119; karar tarihi 28.2.2023, EPİAŞ 1.3.2023 teslim gününden)"),
    (date(2023, 2, 1), 3650.0, "Karar 11588 (RG 27.1.2023-32086)"),
    (date(2023, 1, 1), 4200.0, "Karar 11499 (RG 30.12.2022-32059 s.2)"),
    (date(2022, 9, 1), 4800.0, "Karar 11156 (RG 1.9.2022-31940)"),
    (date(2022, 8, 1), 4000.0, "Karar 11083 (RG 29.7.2022-31907)"),
    (date(2022, 7, 1), 3750.0, "Karar 11043 (RG 30.6.2022-31882)"),
    (date(2022, 6, 1), 3200.0, "Karar 10984 (RG 28.5.2022-31849)"),
    (date(2022, 5, 20), 2750.0, "Karar 10978 (RG 19.5.2022-31840; EPİAŞ 20.5.2022'den)"),
    (date(2022, 4, 1), 2500.0, "Karar 10890 (RG 30.3.2022-31794 s.7)"),
    (date(2022, 3, 1), 1745.0, "Karar 10489 formülü (3× 12 aylık PTF, ≤2.000); EPİAŞ Mart 2022 duyurusu"),
    (date(2022, 2, 1), 1524.0, "Karar 10489 formülü; EPİAŞ Şubat 2022 duyurusu"),
    (date(2022, 1, 1), 1345.0, "Karar 10489 formülü; EPİAŞ Ocak 2022 duyurusu"),
    (date(2021, 12, 1), 1217.0, "Karar 10489 formülü; EPİAŞ Aralık 2021 duyurusu"),
    (date(2021, 11, 1), 1131.0, "Karar 10489 formülü; EPİAŞ Kasım 2021 duyurusu"),
    (date(2021, 10, 16), 1078.0, "Karar 10489 (RG 15.10.2021-31629); EPİAŞ 16–31.10.2021 duyurusu"),
    (date(2021, 10, 1), 718.0, "Karar 9598 formülü (2× 12 aylık PTF); EPİAŞ 1–15.10.2021"),
    (date(2021, 9, 1), 674.0, "Karar 9598 formülü; EPİAŞ Eylül 2021 duyurusu"),
    (date(2021, 8, 1), 636.0, "Karar 9598 formülü; EPİAŞ Ağustos 2021 duyurusu"),
    (date(2021, 7, 1), 617.0, "Karar 9598 formülü; EPİAŞ Temmuz 2021 duyurusu"),
    (date(2021, 6, 1), 595.0, "Karar 9598 formülü; EPİAŞ Haziran 2021 duyurusu"),
    (date(2021, 5, 1), 578.0, "Karar 9598 formülü; EPİAŞ Mayıs 2021 duyurusu"),
    (date(2021, 4, 1), 567.0, "Karar 9598 formülü; EPİAŞ Nisan 2021 duyurusu"),
    (date(2021, 3, 1), 569.0, "Karar 9598 formülü; EPİAŞ Mart 2021 duyurusu"),
    (date(2021, 1, 1), 572.0, "Karar 9598 formülü; EPİAŞ Ocak–Şubat 2021 duyuruları"),
    (date(2020, 12, 1), 572.0, "Karar 9598 formülü; EPİAŞ Aralık 2020 duyurusu"),
    (date(2020, 11, 1), 566.0, "Karar 9598 formülü; EPİAŞ Kasım 2020 duyurusu"),
    (date(2020, 10, 7), 563.0, "Karar 9598 (RG 6.10.2020-31266); EPİAŞ 7–31.10.2020 duyurusu"),
    (date(2020, 4, 1), 2000.0, "Karar 9021 süresi doldu → geçici 1(2) 2.000 (EPİAŞ 25.3.2020 duyurusu)"),
    (date(2020, 1, 1), 600.0, "Karar 9021 (RG 28.12.2019-30992; 1.1–31.3.2020, GÖP ve DGP)"),
    (date(2015, 7, 1), 2000.0, "Karar 5629-16 geçici 1(2) (RG 21.6.2015-29393); 2016–2019 ara kararı doğrulanmadı"),
)


def afl(tarih: date) -> float:
    """Azami fiyat limiti (TL/MWh), teslim günü bazında. Zincir `_AFL_ZINCIRI`; 1.7.2015 öncesi 2.000 (kapsam dışı, doğrulanmadı)."""
    for bas, deger, _ in _AFL_ZINCIRI:
        if tarih >= bas:
            return deger
    return 2000.0


def afl_dayanak(tarih: date) -> str:
    for bas, _, day in _AFL_ZINCIRI:
        if tarih >= bas:
            return day
    return "1.7.2015 öncesi: kapsam dışı (doğrulanmadı)"


def v_degeri(tarih: date) -> float | None:
    if tarih < date(2026, 1, 1):
        return None
    return 100.0 if tarih >= date(2026, 11, 1) else 150.0     # Karar 14911


def edt_kurali(tarih: date) -> EdtKurali:
    if tarih < date(2026, 1, 1):
        return EdtKurali("2025", {y: 0.03 for y in YONLER}, {y: 0.03 for y in YONLER}, None, None, None, "net",
                         "DUY m.110 (RG 2.2.2020-31027 Md.32); k = l = 0,03 — EPDK 4-16180 (22.09.2025) k/l karar taslağı «Mevcut Metin»: "
                         "01/05/2015'ten 0,03 (asıl karar no bulunamadı); 2.2.2020 öncesi formül farklı, 1.12.2011–30.4.2015 k = l = 0 (geçici m.21) — kapsam dışı", "edt-2025")
    toplama = "edta_ayrik" if tarih >= date(2026, 10, 19) else "edta_net"
    v = v_degeri(tarih)
    return EdtKurali("2026", {"acik": 0.06, "fazla": 0.03, "dengede": 0.03}, {"acik": 0.03, "fazla": 0.06, "dengede": 0.03},
                     v, 100.0, afl(tarih), toplama,
                     "DUY m.110(1)-(2) (RG 29.12.2025-33122 Md.17); Karar 14030 (k/l); " + ("Karar 14911 (V = 100)" if v == 100.0 else "V = 150 başlangıç")
                     + ("; EDTA/EDTB dönem bazlı max/min (RG 19.10.2026-33405 Md.22)" if toplama == "edta_ayrik"
                        else "; EDTA = max(ΣΣEDT(+);0), EDTB = ΣΣEDT(−) − min(ΣΣEDT(+);0) (RG 33122 Md.17)")
                     + f"; AFL {afl(tarih):.0f}: {afl_dayanak(tarih)}",
                     f"edt-2026-V{int(v)}-{toplama}")


def kupst_kurali(tarih: date, segment: str | None, portfoy: bool = False, luy_istisna: bool = False) -> KupstKurali:
    """Segment: ext.turkiye.segment.Segment değeri (str). portfoy=True → dağıtıma bağlı lisanssız için GTŞ/toplayıcı UEVÇB katsayısı.
    luy_istisna=True → tesis LÜY m.5(1)(ç),(d),(e) kapsamında (öz tüketim YEK / verimli kojenerasyon / mikrokojenerasyon):
    Karar 14907 Md.5 gereği iletime bağlı lisanssıza 1.11.2026'dan karar uygulanmaz (KÜPST 0). Santral ayarı; LÜY bent harfleri
    2019 ilk metninden, güncel harflendirme doğrulanmadı (31.10.2026)."""
    birim = KUPST_BIRIMI.get(segment or "", "yok")
    taban = 750.0 if tarih >= date(2025, 1, 1) else 0.0
    # 14907 Md.1(1) net sapma (UEÇM düşülür) yalnız lisanslıda; Md.1(3): lisanssızlarda «sadece üretim miktarı» (31.10.2026 araştırması Ç2)
    lisanssiz = segment in ("lisanssiz_iletim", "lisanssiz_dagitim")
    net = tarih >= date(2026, 11, 1) and not lisanssiz
    if birim == "yok" or segment is None:
        return KupstKurali(None, None, None, None, taban, net, birim if segment else "yok", "KÜPST bu segmentte uygulanmaz / segment seçilmedi", "kupst-yok")
    if segment == "lisanssiz_dagitim":
        if portfoy and tarih >= date(2026, 11, 1):
            return KupstKurali(0.25, 0.01, None, None, taban, net, birim,
                               "Karar 14907 Md.2(1)(ç) piyasa katılımcısı bazlı, Md.3(1)(e); UEVÇB: DUY m.110(6)(b)(3) (RG 19.10.2026-33405 Md.22); Md.1(3) brüt",
                               "kupst-14907-dagitim")
        if portfoy:
            return KupstKurali(None, None, None, None, taban, net, birim,
                               "Karar 13025/14029'da dağıtıma bağlı lisanssız / GTŞ-toplayıcı UEVÇB'sine özel satır yok; genel satırın uygulanıp uygulanmadığı "
                               "belirsiz (EPİAŞ uygulaması bulunamadı); KGÜP yükümlülüğü 11.03.2025'ten (TPYS); özel katsayı Karar 14907 ile 1.11.2026'dan",
                               "kupst-dagitim-portfoy-belirsiz")
        return KupstKurali(0.0, 0.0, None, None, taban, net, birim,
                           "Dağıtıma bağlı lisanssız: KÜPST santral sahibinde değil, GTŞ/toplayıcı UEVÇB'sinde hesaplanır (DUY m.69(11), m.110(6)(b)(3), "
                           "RG 19.10.2026-33405 ile 19.10.2026'dan; öncesinde toplayıcı için eski m.110(6) (1.1.2025), GTŞ için m.69(2) + TPYS 11.03.2025)",
                           "kupst-dagitim-santral-0")
    if segment == "lisanssiz_iletim":
        if tarih >= date(2026, 11, 1) and luy_istisna:
            return KupstKurali(0.0, 0.0, None, None, taban, net, birim,
                               "Karar 14907 Md.5: LÜY m.5(1)(ç),(d),(e) kapsamındaki iletime bağlı tesislere karar uygulanmaz (santral ayarı)", "kupst-14907-luy-istisna")
        if tarih >= date(2026, 11, 1):
            return KupstKurali(0.20, 0.02, None, None, taban, net, birim,
                               "Karar 14907 Md.2(1)(c), Md.3(1)(d); Md.1(3) brüt; LÜY 5(1)(ç),(d),(e) tesislerine uygulanmaz (Md.5 — santral ayarı «LÜY istisnası»)",
                               "kupst-14907-iletim")
        if tarih >= date(2026, 1, 1):
            return KupstKurali(0.20, 0.02, None, None, taban, net, birim, "Karar 14029 Md.2(1)(c), Md.3(1) (RG 29.12.2025-33122; 14907 Md.6 ile 1.11.2026'da kalktı)", "kupst-14029-iletim")
        return KupstKurali(None, None, None, None, taban, net, birim,
                           "2025 katsayısı DOĞRULANAMADI: Karar 13025'te bu gruba özel satır yok, DUY m.110(6)/13025 Md.4 karşı okumaya açık; "
                           "yükümlülük hukuken RG 21.1.2025-32789 m.69(10), fiilen TPYS 11.03.2025", "kupst-2025-iletim-belirsiz")
    # lisanslı güneş (serbest / YEKDEM / YEKA)
    if tarih >= date(2026, 11, 1):
        return KupstKurali(0.08, 0.05, 0.08, 30, taban, True, birim, "Karar 14907 Md.1(1) net sapma, Md.2(1)(f), Md.3(1)(b) (RG 19.10.2026-33405)", "kupst-14907")
    if tarih >= date(2026, 1, 1):
        return KupstKurali(0.08, 0.05, 0.08, 30, taban, False, birim, "Karar 14029 Md.2(1)(ç), Md.3(1) (RG 29.12.2025-33122)", "kupst-14029")
    if tarih >= date(2025, 1, 1):
        return KupstKurali(0.10, 0.03, 0.05, 40, taban, False, birim, "Karar 13025 Md.2(1)(c) YEK satırı, Md.3(1) (RG 17.12.2024-32755 s.3); taban DUY m.110(3)", "kupst-13025")
    if tarih >= date(2023, 2, 1):
        return KupstKurali(0.12, 0.03, None, None, 0.0, False, birim, "Karar 11589-2 (RG 27.1.2023-32086)", "kupst-11589")
    if tarih >= date(2020, 8, 1):
        return KupstKurali(0.10, 0.03, None, None, 0.0, False, birim, "Karar 9422 (RG 3.7.2020-31174; 1.8.2020'den)", "kupst-9422")
    return KupstKurali(0.10, 0.03, None, None, 0.0, False, birim,
                       "Karar 7524 (RG 18.1.2018-30305); ilk 3 ay n 0,015 penceresinin tarihi bulunamadı — 0,03 kullanıldı", "kupst-7524")


def dsg_esigi(tarih: date) -> tuple[float, str]:
    if tarih < date(2026, 1, 1):
        return 0.10, "DUY m.111(5), RG 17.12.2024-32755 Md.24 (%10; yürürlük 1.1.2025)"
    if tarih < date(2027, 1, 1):
        return 0.05, "Karar 13869 (RG 18.10.2025-33051), 1.1.2026'dan %5"
    return 0.05, ("Karar 13869 yürürlükte (süre sınırı yok, %5); DUY m.111(5) uyarınca yıllık düşürme kararı en geç 1.12.2026'da alınır, "
                  "RG yayımı Aralık sonuna sarkabilir; yön riski aşağı — %5 VARSAYILDI")


# 1.1.2027 belirsizlik bayrağının gerekçesi (31.10.2026 araştırması, bulgular/09.md): ekran/rapor notu için tek kaynak.
BELIRSIZ_2027_GEREKCE = (
    "(i) m.110(1)-(2): RG 21.1.2025-32789 Md.13 1.1.2027'de yürürlüğe girer, ama 33122/33405 aynı fıkraları sonradan yeniden yazdı; "
    "tek k/l kararı yok (üç aylık duyuru süresi 1.10.2026'da doldu). (ii) m.110(3)-(4): Md.13 KÜPST'yi 15 dakikalık «ç» bazına alır; "
    "«ç» bazlı KÜPSM yöntem kararı yok (14907 «u» bazlı). (iii) m.91(2) + Geçici 40: 15 dakikalık DGP 1.1.2027'den önce başlamaz, "
    "fiilî başlangıç ilan edilmedi. (iv) SMF_N/SMF_P çeyrek SMF ister; Karar 14968 Şeffaflık'ta SMF'yi yalnız saatlik listeler. "
    "Varsayılan: 2026 rejimi sürer, sonuçlar «belirsiz» etiketi taşır; Kasım–Aralık 2026 RG'leri izlenir."
)


def kural(tarih: date | str | pd.Timestamp, segment: str | None = None, portfoy: bool = False, luy_istisna: bool = False) -> Kural:
    """Teslim günü (İstanbul takvim günü) için yürürlükteki kural. Saatlik damga verilirse İstanbul gününe çevrilir."""
    t = _gun(tarih)
    e, k = edt_kurali(t), kupst_kurali(t, segment, portfoy, luy_istisna)
    esik, dayanak = dsg_esigi(t)
    return Kural(t, segment, e, k, esik, dayanak, belirsiz_2027=t >= date(2027, 1, 1))


def _gun(tarih) -> date:
    if isinstance(tarih, date) and not isinstance(tarih, pd.Timestamp):
        return tarih
    ts = pd.Timestamp(tarih)
    if ts.tz is not None:
        ts = ts.tz_convert(IST)
    return ts.date()


def parametre_cercevesi(index: pd.DatetimeIndex, segment: str | None = None, ariza_sayisi: int = 0, portfoy: bool = False, *,
                        karsi_olgu: str | None = None, luy_istisna: bool = False) -> pd.DataFrame:
    """Saatlik index (UTC ya da saat dilimli) → her saat için yürürlükteki parametreler (vektörel hesap için).
    karsi_olgu (F-07 geri test sütunları, C iş kolu tanımı): '2026' → bütün saatlere 2026 kuralı — EDT formülü (yöne bağlı k/l, V 150 /
    1.11.2026'dan 100, B, o saatin AFL'si) VE KÜPST katsayıları Karar 14029/14907 (tarihe göre; 2025 saatlerinde 14029 brüt);
    '2026_V100' → ayrıca V = 100 bütün dönemde. DSG eşiği tarihli kalır."""
    idx = pd.DatetimeIndex(index)
    yerel = idx.tz_convert(IST) if idx.tz is not None else idx.tz_localize("UTC").tz_convert(IST)
    gunler = pd.Series(yerel.date, index=idx)
    satirlar = {}
    for g in gunler.unique():
        r = kural(g, segment, portfoy, luy_istisna)
        if karsi_olgu in ("2026", "2026_V100"):
            g26 = max(g, date(2026, 1, 1))
            e = edt_kurali(g26); kp = kupst_kurali(g26, segment, portfoy, luy_istisna)
            v = 100.0 if karsi_olgu == "2026_V100" else e.V
            e = EdtKurali(e.rejim, e.k, e.l, v, e.B, afl(g), e.toplama,            # AFL o saatin gerçek tavanı (3.000/3.400/4.500)
                          e.dayanak + ("; karşı-olgu: 2026 kuralı tüm döneme, V = 100" if karsi_olgu == "2026_V100" else "; karşı-olgu: 2026 kuralı tüm döneme"),
                          (e.surum.replace("V150", "V100") if karsi_olgu == "2026_V100" else e.surum) + "-karsi-olgu")
            r = Kural(r.tarih, r.segment, e, kp, r.dsg_esik, r.dsg_dayanak, r.belirsiz_2027)
        satirlar[g] = {"rejim": r.edt.rejim, "surum": r.surum,
                       "k_acik": r.edt.k["acik"], "k_fazla": r.edt.k["fazla"], "k_dengede": r.edt.k["dengede"],
                       "l_acik": r.edt.l["acik"], "l_fazla": r.edt.l["fazla"], "l_dengede": r.edt.l["dengede"],
                       "V": r.edt.V, "B": r.edt.B, "AFL": r.edt.AFL, "toplama": r.edt.toplama,
                       "m": r.kupst.m, "n": r.kupst.n_etkin(ariza_sayisi), "taban": r.kupst.taban, "net_sapma": r.kupst.net_sapma,
                       "kupst_birim": r.kupst.birim, "dsg_esik": r.dsg_esik, "belirsiz_2027": r.belirsiz_2027}
    out = pd.DataFrame([satirlar[g] for g in gunler], index=idx)
    for kol in ("V", "B", "AFL", "m", "n"):
        out[kol] = pd.to_numeric(out[kol], errors="coerce")
    return out


def tablo(segment: str | None = "lisansli_serbest") -> list[dict]:
    """Yönetici ekranı / API için salt okunur satırlar: parametre, geçerlilik, değer, dayanak."""
    sinirlar = [date(2023, 1, 1), date(2024, 7, 1), date(2025, 1, 1), date(2025, 4, 5), date(2026, 1, 1), date(2026, 4, 4),
                date(2026, 10, 19), date(2026, 11, 1), date(2027, 1, 1)]
    out = []
    for i, bas in enumerate(sinirlar):
        bitis = (sinirlar[i + 1] - pd.Timedelta(days=1)).isoformat() if i + 1 < len(sinirlar) else None
        r = kural(bas, segment)
        out.append({"gecerlilik_bas": bas.isoformat(), "gecerlilik_bitis": bitis, "rejim": r.edt.rejim, "kural_surumu": r.surum,
                    "k": r.edt.k, "l": r.edt.l, "V": r.edt.V, "B": r.edt.B, "AFL": r.edt.AFL, "aylik_toplama": r.edt.toplama,
                    "kupst": {"m": r.kupst.m, "n": r.kupst.n, "n_ariza": r.kupst.n_ariza, "ariza_esigi": r.kupst.ariza_esigi,
                              "taban": r.kupst.taban, "net_sapma": r.kupst.net_sapma, "birim": r.kupst.birim, "dayanak": r.kupst.dayanak},
                    "dsg_esik": r.dsg_esik, "dsg_dayanak": r.dsg_dayanak, "edt_dayanak": r.edt.dayanak,
                    "belirsiz_2027": r.belirsiz_2027})
    return out


def yon_normalize(deger) -> str | None:
    """EPİAŞ sistem yönü metni/kodu → 'acik' | 'fazla' | 'dengede' | None. Bilinmeyen değer None (yön SMF>PTF'den ÇIKARILMAZ)."""
    if deger is None:
        return None
    if isinstance(deger, float) and pd.isna(deger):
        return None
    s = str(deger).strip().lower()
    if s in ("acik", "fazla", "dengede"):
        return s
    if not s or s == "nan":
        return None
    s = (s.replace("ı", "i").replace("ğ", "g").replace("ş", "s").replace("ç", "c").replace("ö", "o").replace("ü", "u"))
    if "acig" in s or "acik" in s or "deficit" in s or "negatif" in s or "negative" in s:
        return "acik"
    if "fazla" in s or "surplus" in s or "pozitif" in s or "positive" in s:
        return "fazla"
    if "denge" in s or "balance" in s or s in ("0", "0.0"):
        return "dengede"
    return None
