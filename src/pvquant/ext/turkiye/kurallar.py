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
    m güneş 0,08, iletime bağlı lisanssız 0,20; n YEK: aylık arıza ≥30 ise 0,08 değilse 0,05; iletime bağlı lisanssız 0,02; topluluk 0,05 (künye Karar 14907 Md.2(1)(b); 14029 değeriyle aynı).
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
lisanssız m/n; GTŞ/toplayıcı UEVÇB'si 1.11.2026 öncesi; 2027 DSG oranı (karar en geç 1.12.2026); Karar 7524 0,015 penceresi; 2016 ve 2018–2019 AFL (2017: Karar 6851, v2.532).
"""
from __future__ import annotations

from pvquant.zaman import PIYASA_TZ

import re

from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd

from pvquant.ext.turkiye import kural_sicili as _sicil   # v2.600 (F4-F): değerler ve tarihler sicilden
# v2.535 dayanak künyeleri [DUY, LUY, KARAR_14907, KARAR_14968, KARAR_14029, KARAR_14030, KARAR_14911, KARAR_13869, KARAR_13025, AFL_UE] — bu dosyadaki madde atıflarının birincil yayımı (RG tarih-sayı, karar no); metin kunye.py sicilinden üretildi,
# tests/test_kunye_bekcisi.py sicille eş tutar (kaynak: 03.11.2026 doğrulama arşivi 03_Kaynak_Envanteri).
DAYANAK_KUNYELERI = (
    'DUY: Elektrik Piyasası Dengeleme ve Uzlaştırma Yönetmeliği, RG 14.04.2009-27200; değişiklikler RG 28.03.2015-29309, 30.10.2016-29873, 18.01.2018-30305, 09.08.2019-30857, 02.02.2020-31027, 19.11.2022-32018, 19.12.2023-32404, 17.12.2024-32755, 21.01.2025-32789, 29.12.2025-33122, 19.10.2026-33405, 21.10.2026-33407; '
    'LÜY: Elektrik Piyasasında Lisanssız Elektrik Üretim Yönetmeliği, RG 12.05.2019-30772; değişiklikler RG 09.05.2021-31479, 02.04.2026-33212, 19.10.2026-33405; '
    'Karar 14907: EPDK Kurul Kararı 14907 (KÜPST, 1.11.2026 çıkarım), RG 19.10.2026-33405; '
    "Karar 14968: EPDK Kurul Kararı 14968 (Şeffaflık Platformu veri listesi, 1.1.2027'den), RG 20.10.2026-33406; öncesi Karar 10711; "
    'Karar 14029: EPDK Kurul Kararı 14029 (KÜPST 2026), RG 29.12.2025-33122; '
    'Karar 14030: EPDK Kurul Kararı 14030 (yöne bağlı k/l, 1.1.2026), RG 29.12.2025-33122; '
    'Karar 14911: EPDK Kurul Kararı 14911 (DUY m.110 V = 100 TL/MWh), RG 19.10.2026-33405; '
    'Karar 13869: EPDK Kurul Kararı 13869 (DSG üye dengesizlik oranı %5), RG 18.10.2025-33051; '
    'Karar 13025: EPDK Kurul Kararı 13025 (KÜPST 2025), RG 17.12.2024-32755; '
    "AFL U&E: GÖP ve DGP'de Asgari ve Azami Fiyat Limitlerinin Belirlenmesine İlişkin Usul ve Esaslar, Karar 5629-16, RG 21.06.2015-29393; Karar 6851 RG 06.01.2017-29940; Karar 14459 RG 03.04.2026-33213"
)

IST = PIYASA_TZ   # v2.599: tek tanım pvquant.zaman
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
    dsg_esik: float | None        # None → üye eşiği yok (1.1.2025 öncesi: sapmalar DSG içinde tamamen netleşir)
    dsg_dayanak: str
    belirsiz_2027: bool

    @property
    def surum(self) -> str:
        """Sonuç kayıtlarında saklanan sürüm dizgisi (edt+kupst) — biçimi değişmez (geçmiş kayıtlarla karşılaştırılabilir)."""
        return f"{self.edt.surum}+{self.kupst.surum}"

    @property
    def surum_tam(self) -> str:
        """v2.600 (F4-F, bulgu M5): AFL ve DSG eşiğini de kapsayan tam sürüm — bu ikisi değişince ayırt edilir; sonuç meta'larına yazılır."""
        afl_ = f"afl{int(afl(self.tarih))}"   # o gün yürürlükteki AFL (EDT formülü kullanmasa da sicilde tarihli)
        dsg_ = f"dsg{int(round(self.dsg_esik * 100))}" if self.dsg_esik is not None else "dsg-yok"
        return f"{self.surum}+{afl_}+{dsg_}"

    @property
    def sicil_sha16(self) -> str:
        return _sicil.sicil_sha16()


# ---------------------------------------------------------------- tarihli parametreler --------------------------------
# AFL zinciri — her halka RG karar PDF'inden okundu (31.10.2026 araştırması, bulgular/08.md §8.2). Tarih = EPİAŞ'ın uyguladığı teslim günü;
# RG yürürlüğü yayım günü olan kararlarda (9598, 10489, 10978) EPİAŞ ertesi teslim gününden uyguladı. Formüllü dönem (7.10.2020–31.3.2022)
# EPİAŞ aylık duyurularından (Wayback; PTF serisinden yeniden hesaplanmadı). 1.7.2015–31.12.2019: 2.000 (geçici 1(2)); 7.1.2017–28.2.2017 teslim
# günleri 500 (Karar 6851; 03.11.2026 doğrulama arşivi DK-016 / 10_Uzlastirma_Dengesizlik Ç-1 — RG lafzı 6.1.2017 ve 1.3.2017 günleri açık, EPİAŞ
# uygulama günü esas alındı); 2016 ve 2018–2019 ara kararı doğrulanmadı.
_AFL_ZINCIRI: tuple[tuple[date, float, str], ...] = _sicil.afl_zinciri()   # v2.600 (F4-F): zincir kural sicilinden (kural_sicili._AFL_HAM); biçim geriye uyumlu


KGUP_KESIM_DEGISIM = date(2025, 1, 1)


def kgup_kesim(tarih: date) -> tuple[tuple[int, int], str]:
    """Teslim günü D için D-1 son KGÜP bildirim saati (İstanbul) ve dayanağı. 03.11.2026 doğrulama arşivi DK-154 / 11_KGUP_TPYS §3 (kanıt A):
    1.1.2025'ten 15:30 (RG 17.12.2024-32755 Md.17, 18, 20; DUY m.69(1)); öncesinde 16:00 (RG 14.04.2009-27200 m.69(1) asıl metin; EPDK 19.12.2023
    sürümü). Geri test ve yeniden hesaplarda 2024 ve öncesi teslim günleri için program kesimi 16:00 alınır."""
    k = _sicil.ara("kgup.kesim", tarih)
    if k is None:   # kapsam başından önce: eski dal
        k = _sicil.kayitlar("kgup.kesim")[0]
    return tuple(k.deger), k.gerekce


def kgup_kesim_sql(gun_ifadesi: str) -> str:
    """SQL parçası (v2.597, F4-B): teslim günü ifadesi (DATE) için D-1 kesim saati INTERVAL'i — `kgup_kesim` ile AYNI kural tablosundan
    üretilir (program_df'nin elle yazılmış CASE'i buraya bağlandı; üçlü denklik testi program_df = kaynak_kosu_df = karne_kurali.program_kovasi)."""
    (h0, m0), _ = kgup_kesim(KGUP_KESIM_DEGISIM - timedelta(days=1))
    (h1, m1), _ = kgup_kesim(KGUP_KESIM_DEGISIM)
    return (f"(CASE WHEN {gun_ifadesi} < DATE '{KGUP_KESIM_DEGISIM.isoformat()}' THEN INTERVAL '{h0} hours {m0} minutes'"
            f" ELSE INTERVAL '{h1} hours {m1} minutes' END)")


def afl(tarih: date) -> float:
    """Azami fiyat limiti (TL/MWh), teslim günü bazında. Zincir `_AFL_ZINCIRI`; 1.7.2015 öncesi 2.000 (kapsam dışı, doğrulanmadı)."""
    k = _sicil.ara("afl", tarih)
    return float(k.deger) if k is not None else _sicil.AFL_KAPSAM_DISI_DEGER


def afl_dayanak(tarih: date) -> str:
    k = _sicil.ara("afl", tarih)
    return k.gerekce if k is not None else _sicil.AFL_KAPSAM_DISI_DAYANAK


def v_degeri(tarih: date) -> float | None:
    k = _sicil.ara("edt.V", tarih)
    return float(k.deger) if k is not None else None     # 2026 öncesi V yok; Karar 14911 ile 1.11.2026'dan 100


def edt_kurali(tarih: date) -> EdtKurali:
    """v2.600 (F4-F): rejim, k/l, V, B, toplama ve dayanak parçaları kural sicilinden; çıktı (değer ve dayanak metni) v2.535 ile birebir."""
    r = _sicil.ara("edt.rejim", tarih) or _sicil.kayitlar("edt.rejim")[0]
    t = _sicil.ara("edt.toplama", tarih) or _sicil.kayitlar("edt.toplama")[-1]
    if r.rejim == "2025":
        return EdtKurali("2025", dict(r.deger["k"]), dict(r.deger["l"]), None, None, None, t.deger, r.gerekce, r.surum)
    v = v_degeri(tarih)
    vk = _sicil.ara("edt.V", tarih)
    return EdtKurali("2026", dict(r.deger["k"]), dict(r.deger["l"]), v, float(r.deger["B"]), afl(tarih), t.deger,
                     r.gerekce + (vk.gerekce if vk is not None else "") + t.gerekce + f"; AFL {afl(tarih):.0f}: {afl_dayanak(tarih)}",
                     f"edt-2026-V{int(v)}-{t.deger}")

def kupst_kurali(tarih: date, segment: str | None, portfoy: bool = False, luy_istisna: bool = False) -> KupstKurali:
    """Segment: ext.turkiye.segment.Segment değeri (str). portfoy=True → dağıtıma bağlı lisanssız için GTŞ/toplayıcı UEVÇB katsayısı.
    luy_istisna=True → tesis LÜY m.5(1)(ç),(d),(e) kapsamında (öz tüketim YEK / verimli kojenerasyon / mikrokojenerasyon):
    Karar 14907 Md.5 gereği iletime bağlı lisanssıza 1.11.2026'dan karar uygulanmaz (KÜPST 0 — yorum). Santral ayarı: yalnız (ç) aynı ölçüm
    noktası / (d) kojenerasyon / (e) mikrokojenerasyon; (h) türü öz tüketim istisna dışı. Harflendirme güncel konsolide metinle teyitli (03.11.2026).
    v2.600 (F4-F): katsayılar, tarihler ve dayanak metinleri kural sicilinden (segment grubu + koşul); çıktılar v2.535 ile birebir."""
    birim = KUPST_BIRIMI.get(segment or "", "yok")
    tk = _sicil.ara("kupst.taban", tarih) or _sicil.kayitlar("kupst.taban")[0]
    taban = float(tk.deger)
    # 14907 Md.1(1) net sapma (UEÇM düşülür) yalnız lisanslıda; Md.1(3): lisanssızlarda «sadece üretim miktarı» (31.10.2026 araştırması Ç2)
    lisanssiz = segment in ("lisanssiz_iletim", "lisanssiz_dagitim")
    net = _sicil.ara("kupst.net_sapma", tarih) is not None and not lisanssiz
    if birim == "yok" or segment is None:
        return KupstKurali(None, None, None, None, taban, net, birim if segment else "yok", _sicil.KUPST_YOK_DAYANAK, "kupst-yok")
    kosul = None
    if segment == "lisanssiz_dagitim":
        if not portfoy:
            k = _sicil.ara("kupst", tarih, segment, None)
        else:
            k = _sicil.ara("kupst", tarih, segment, "portfoy")
    elif segment == "lisanssiz_iletim":
        kosul = "luy_istisna" if (luy_istisna and _sicil.ara("kupst", tarih, segment, "luy_istisna") is not None) else None
        k = _sicil.ara("kupst", tarih, segment, kosul)
    else:
        k = _sicil.ara("kupst", tarih, segment, None) or _sicil.ara("kupst", tarih, "lisansli_serbest", None)
    if k is None:   # kapsam başından önce: en eski lisanslı dal (eski davranış: Karar 7524 etiketi)
        k = [x for x in _sicil.kayitlar("kupst") if x.segmentler and segment in x.segmentler and x.kosul is None][0]
    d = k.deger
    return KupstKurali(d["m"], d["n"], d["n_ariza"], d["ariza_esigi"], taban, net, birim, k.gerekce, k.surum)   # taban tarihli (kupst.taban); 2025 öncesi 0

def dsg_esigi(tarih: date) -> tuple[float | None, str]:
    """DSG üye dengesizlik oranı eşiği. 03.11.2026 doğrulama arşivi DK-249 (kanıt A): m.111(3)-(5) RG 17.12.2024-32755 Md.24 ile
    eklendi, Md.30 ile 1.1.2025'te yürürlüğe girdi; 2023 sürümünde m.111 yalnız (1)-(2) → 1.1.2025 öncesinde üye eşiği YOK (eşiksiz netleşme).
    02.02.2020 öncesi m.111 sürümleri okunmadı (kapsam dışı). v2.600: değer ve dayanak kural sicilinden."""
    k = _sicil.ara("dsg.esik", tarih) or _sicil.kayitlar("dsg.esik")[0]
    return (float(k.deger) if k.deger is not None else None), k.gerekce


# DUY Geçici m.39 (RG 17.12.2024-32755 Md.29; bulgular/10.md (e)): dağıtım lisansı sahipleri ile bölgelerindeki görevli tedarik şirketlerinin
# kurduğu DSG'lerde m.111(5) oranı «1/1/2027 tarihine kadar yüzde yüz olarak uygulanır» — bu gruplarda üye eşiği %100 (bireysel kısım yok).
# PVQuant müşterisinin DSG'si hangi türde bilinmiyor; motor genel oranı uygular, ekran notu olarak söylenir. 1.1.2027'de hüküm biter.
GECICI_M39_NOT = ("DUY Geçici m.39: dağıtım şirketi ile bölgesindeki görevli tedarik şirketinin birlikte kurduğu DSG'lerde üye eşiği 1.1.2027'ye kadar %100 "
                  "(RG 17.12.2024-32755 Md.29); DSG'niz bu türdeyse burada gösterilen genel oran yerine %100 uygulanır")
GECICI_M39_BITIS = date(2027, 1, 1)
GECICI_M39_DIPNOT = ("Dağıtım şirketi ile bölgesindeki görevli tedarik şirketinin birlikte kurduğu DSG'lerde üye eşiği 1.1.2027'ye kadar %100 (DUY Geçici m.39); "
                     "DSG'niz bu türdeyse netleşme farkı burada gösterilenden büyüktür.")


def gecici_m39_notu(tarih: date) -> str | None:
    """Geçici m.39 yürürlükteyken (1.1.2027 öncesi) ekran notu; sonrası None."""
    return GECICI_M39_NOT if tarih < GECICI_M39_BITIS else None


# 1.1.2027 belirsizlik bayrağının gerekçesi (31.10.2026 araştırması, bulgular/09.md): ekran/rapor notu için tek kaynak.
BELIRSIZ_2027_GEREKCE = _sicil.BELIRSIZ_2027_GEREKCE   # v2.600: tek metin kural sicilinde


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
        satirlar[g] = {"rejim": r.edt.rejim, "surum": r.surum, "surum_tam": r.surum_tam,
                       "k_acik": r.edt.k["acik"], "k_fazla": r.edt.k["fazla"], "k_dengede": r.edt.k["dengede"],
                       "l_acik": r.edt.l["acik"], "l_fazla": r.edt.l["fazla"], "l_dengede": r.edt.l["dengede"],
                       "V": r.edt.V, "B": r.edt.B, "AFL": r.edt.AFL, "toplama": r.edt.toplama,
                       "m": r.kupst.m, "n": r.kupst.n_etkin(ariza_sayisi), "taban": r.kupst.taban, "net_sapma": r.kupst.net_sapma,
                       "kupst_birim": r.kupst.birim, "dsg_esik": r.dsg_esik, "belirsiz_2027": r.belirsiz_2027}
    out = pd.DataFrame([satirlar[g] for g in gunler], index=idx)
    for kol in ("V", "B", "AFL", "m", "n"):
        out[kol] = pd.to_numeric(out[kol], errors="coerce")
    return out


TABLO_BAS = date(2023, 1, 1)
TABLO_UFUK = date(2027, 1, 1)


def _imza(r: "Kural") -> tuple:
    """Tablo satırını belirleyen alanlar (AFL hariç — fiyat tavanı ayrı zincir, satırda başlangıç/son değeriyle verilir)."""
    return (r.surum, r.edt.rejim, tuple(sorted(r.edt.k.items())), tuple(sorted(r.edt.l.items())), r.edt.V, r.edt.toplama,
            r.kupst.m, r.kupst.n, r.kupst.n_ariza, r.kupst.ariza_esigi, r.kupst.taban, r.kupst.net_sapma, r.dsg_esik, r.belirsiz_2027)


def donem_sinirlari(segment: str | None = "lisansli_serbest", bas: date = TABLO_BAS, ufuk: date = TABLO_UFUK) -> list[date]:
    """03.11 (v2.528 inceleme): dönem sınırları elle yazılmaz, kural motoru GÜN GÜN taranır ve imza değiştiği gün yeni dönem
    açılır. Böylece Hakkında tablosu motorun bir tarihe uyguladığı kuralla çelişemez (eski liste 1.2.2023 Karar 11589-2
    geçişini atlıyor, 2023 satırı 17 ay boyunca m = 0,10 gösteriyordu; motor 0,12 uyguluyordu)."""
    out = [bas]; son = _imza(kural(bas, segment)); g = bas
    while g < ufuk:
        g = g + timedelta(days=1)
        imza = _imza(kural(g, segment))
        if imza != son:
            out.append(g); son = imza
    if ufuk not in out:
        out.append(ufuk)   # 2027: «belirsiz» satırı imzayla zaten açılır; güvence
    return out


# v2.535 (Hakkında doğrulama turu, 04.11.2026): satırın kaynak durumu dayanak metnindeki işaretlerden TÜRETİLİR; elle etiket yok.
# Metinde «bulunamadı» / «doğrulanmadı» / «taslağı» geçen bir dayanak → doğrulama gerekli; yalnız «çıkarım» → çıkarım; aksi → doğrulandı.
_DOGRULAMA_ISARETLERI = ("bulunamadı", "doğrulanmadı", "taslağı")
DOGRULAMA_DURUMLARI = ("dogrulandi", "cikarim", "dogrulama_gerekli", "belirsiz")


def dogrulama_durumu(edt_dayanak: str | None, kupst_dayanak: str | None, belirsiz_2027: bool = False) -> tuple[str, str]:
    """(durum, not). durum ∈ DOGRULAMA_DURUMLARI. Not, hangi dayanak parçasının eksik olduğunu söyler (ekranda açılır metin)."""
    notlar: list[str] = []
    for ad, metin in (("EDT", edt_dayanak or ""), ("KÜPST", kupst_dayanak or "")):
        for parca in re.split(r"[;—]", metin):
            if any(i in parca for i in _DOGRULAMA_ISARETLERI):
                notlar.append(f"{ad}: {parca.strip().strip('()«» ')}")
    if belirsiz_2027:
        return "belirsiz", "1.1.2027 sonrası uygulama ayrıntıları henüz belirsiz (DUY m.110); varsayılan: 2026 rejimi sürer" + ("; " + "; ".join(notlar) if notlar else "")
    if notlar:
        return "dogrulama_gerekli", "; ".join(notlar)
    if "çıkarım" in (edt_dayanak or "") + (kupst_dayanak or ""):
        return "cikarim", "yürürlük tarihi «yayımı takip eden fatura dönemi» ifadesinden çıkarım; sayısal değerler birincil kaynaktan"
    return "dogrulandi", "birincil kaynak (Resmî Gazete yayımı / Kurul kararı) künyeli"


def tablo(segment: str | None = "lisansli_serbest") -> list[dict]:
    """Yönetici ekranı / API için salt okunur satırlar: parametre, geçerlilik, değer, dayanak.
    AFL: dönem başı ve dönem sonu değeri (fiyat tavanı dönem içinde değişebilir; saatlik hesap kendi gününün tavanını alır)."""
    sinirlar = donem_sinirlari(segment)
    out = []
    for i, bas in enumerate(sinirlar):
        bitis_d = (sinirlar[i + 1] - timedelta(days=1)) if i + 1 < len(sinirlar) else None
        bitis = bitis_d.isoformat() if bitis_d else None
        r = kural(bas, segment)
        afl_son = afl(bitis_d) if bitis_d else afl(max(bas, pd.Timestamp.now(tz=IST).date()))
        out.append({"gecerlilik_bas": bas.isoformat(), "gecerlilik_bitis": bitis, "rejim": r.edt.rejim, "kural_surumu": r.surum,
                    "k": r.edt.k, "l": r.edt.l, "V": r.edt.V, "B": r.edt.B, "AFL": r.edt.AFL, "AFL_son": afl_son,
                    "AFL_degisken": afl_son != r.edt.AFL, "aylik_toplama": r.edt.toplama,
                    "kupst": {"m": r.kupst.m, "n": r.kupst.n, "n_ariza": r.kupst.n_ariza, "ariza_esigi": r.kupst.ariza_esigi,
                              "taban": r.kupst.taban, "net_sapma": r.kupst.net_sapma, "birim": r.kupst.birim, "dayanak": r.kupst.dayanak},
                    "dsg_esik": r.dsg_esik, "dsg_dayanak": r.dsg_dayanak, "edt_dayanak": r.edt.dayanak,
                    "belirsiz_2027": r.belirsiz_2027})
        out[-1]["dogrulama"], out[-1]["dogrulama_notu"] = dogrulama_durumu(r.edt.dayanak, r.kupst.dayanak, r.belirsiz_2027)   # v2.535
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
