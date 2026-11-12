"""v2.600 (Faz 4 F4-F, Stage 9) — MEVZUAT KURAL SİCİLİ: sürümlü, kod içi, saf.

Her kural/parametre bir `KuralKaydi`: kimlik, sürüm etiketi, yürürlük aralığı, değer, künye (madde, RG), doğrulama durumu,
gerekçe, hangi sürümü değiştirdiği. Kural motoru (`kurallar.py`: `afl`, `v_degeri`, `edt_kurali`, `kupst_kurali`, `dsg_esigi`,
`kgup_kesim`) değerleri ve tarihleri BURADAN okur; imzalar ve çıktılar v2.510–v2.535 ile birebir (54 vektör + gün gün tablo bekçisi).
DB'de düzenlenebilir kural tablosu YOK (geri test ve CI deterministik); gece işi sicilin anlık görüntüsünü (`kural_sicili_anlik`,
sha16) saklar, sonuç meta'ları `kural_sicili_sha` taşır. Belge: docs/KURAL-SICILI.md.

Doğrulama durumları: dogrulandi (birincil kaynak künyeli) · cikarim (yürürlük tarihi «yayımı takip eden fatura dönemi»nden çıkarım) ·
yorum (metnin uygulanışı yorum) · varsayim (karar henüz yok, değer varsayıldı) · belirsiz (hukuken belirsiz) · dogrulanamadi (karar
numarası/dönem bulunamadı). Durum YAPISALDIR; metinden türetilmez (eski `dogrulama_durumu` tablo satırı için metin okumayı sürdürür).
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import date
from functools import lru_cache

SURUM = "2026-11-12"
DOGRULAMA = ("dogrulandi", "cikarim", "yorum", "varsayim", "belirsiz", "dogrulanamadi")
YONLER = ("acik", "fazla", "dengede")
BASLANGIC = date(2000, 1, 1)   # «kapsam başı» — daha eski tarihler motorun son dalına düşer (eski davranış)


@dataclass(frozen=True)
class KuralKaydi:
    kural_id: str                      # "afl" | "edt.rejim" | "edt.V" | "edt.B" | "edt.toplama" | "kupst" | "kupst.taban" | "dsg.esik" | "kgup.kesim" | "kgup.takvim" | "piyasa.senaryo" | "2027"
    surum: str                         # sürüm etiketi (kural_surumu parçaları bunlardan kurulur)
    parametre: str                     # insan dili ad
    yururluk_bas: date
    yururluk_bit: date | None          # hariç; None = süresiz
    deger: object                      # sayı / sözlük / None (belirsiz)
    kunye_ad: str                      # kunye.py anahtarı (DUY, KARAR_14907 …) ya da serbest ad
    madde: str                         # madde / karar atfı
    yayim_rg: str | None               # RG tarih-sayı
    dogrulama: str                     # DOGRULAMA
    gerekce: str                       # dayanak metni (motorun bastığı dayanak bu metinden kurulur)
    segmentler: tuple[str, ...] | None = None   # kupst: uygulandığı segment grubu
    rejim: str | None = None
    degisiklik: str | None = None      # değiştirdiği sürüm
    kosul: str | None = None           # kupst: "portfoy" | "luy_istisna" | None

    def kapsar(self, tarih: date) -> bool:
        return self.yururluk_bas <= tarih and (self.yururluk_bit is None or tarih < self.yururluk_bit)


def _afl(bas: date, deger: float, dayanak: str, dogrulama: str, bit: date | None = None, degisiklik: str | None = None) -> KuralKaydi:
    m = re.search(r"RG\s+([\d.]+-\d{5})", dayanak)
    rg = m.group(1) if m else None
    return KuralKaydi("afl", f"afl-{bas.isoformat()}", "Azami fiyat limiti (TL/MWh)", bas, bit, deger, "AFL_UE", dayanak, rg, dogrulama, dayanak, degisiklik=degisiklik)


# ---- AFL zinciri (en yeni önce; her halka RG karar PDF'inden — 31.10.2026 araştırması bulgular/08.md §8.2; v2.532 DK-016) ------------------
_AFL_HAM: tuple[tuple[date, float, str, str], ...] = (
    (date(2026, 4, 4), 4500.0, "Karar 14459 (RG 3.4.2026-33213 s.47)", "dogrulandi"),
    (date(2025, 4, 5), 3400.0, "Karar 13423 (RG 5.4.2025-32861)", "dogrulandi"),
    (date(2024, 7, 1), 3000.0, "Karar 12716 (RG 29.6.2024-32587 s.26)", "dogrulandi"),
    (date(2023, 7, 4), 2700.0, "Karar 11933 (RG 4.7.2023-32238; yürürlük maddesi yok — Usul ve Esaslar Md.4(5) lafzen 1.8.2023, EPİAŞ 4.7.2023 teslim gününden uyguladı; uygulama tarihi esas alındı)", "yorum"),
    (date(2023, 4, 1), 2600.0, "Karar 11772 (RG 31.3.2023-32149 s.5)", "dogrulandi"),
    (date(2023, 3, 1), 3050.0, "Karar 11682 (RG 1.3.2023-32119; karar tarihi 28.2.2023, EPİAŞ 1.3.2023 teslim gününden)", "dogrulandi"),
    (date(2023, 2, 1), 3650.0, "Karar 11588 (RG 27.1.2023-32086)", "dogrulandi"),
    (date(2023, 1, 1), 4200.0, "Karar 11499 (RG 30.12.2022-32059 s.2)", "dogrulandi"),
    (date(2022, 9, 1), 4800.0, "Karar 11156 (RG 1.9.2022-31940)", "dogrulandi"),
    (date(2022, 8, 1), 4000.0, "Karar 11083 (RG 29.7.2022-31907)", "dogrulandi"),
    (date(2022, 7, 1), 3750.0, "Karar 11043 (RG 30.6.2022-31882)", "dogrulandi"),
    (date(2022, 6, 1), 3200.0, "Karar 10984 (RG 28.5.2022-31849)", "dogrulandi"),
    (date(2022, 5, 20), 2750.0, "Karar 10978 (RG 19.5.2022-31840; EPİAŞ 20.5.2022'den)", "dogrulandi"),
    (date(2022, 4, 1), 2500.0, "Karar 10890 (RG 30.3.2022-31794 s.7)", "dogrulandi"),
    (date(2022, 3, 1), 1745.0, "Karar 10489 formülü (3× 12 aylık PTF, ≤2.000); EPİAŞ Mart 2022 duyurusu", "cikarim"),
    (date(2022, 2, 1), 1524.0, "Karar 10489 formülü; EPİAŞ Şubat 2022 duyurusu", "cikarim"),
    (date(2022, 1, 1), 1345.0, "Karar 10489 formülü; EPİAŞ Ocak 2022 duyurusu", "cikarim"),
    (date(2021, 12, 1), 1217.0, "Karar 10489 formülü; EPİAŞ Aralık 2021 duyurusu", "cikarim"),
    (date(2021, 11, 1), 1131.0, "Karar 10489 formülü; EPİAŞ Kasım 2021 duyurusu", "cikarim"),
    (date(2021, 10, 16), 1078.0, "Karar 10489 (RG 15.10.2021-31629); EPİAŞ 16–31.10.2021 duyurusu", "dogrulandi"),
    (date(2021, 10, 1), 718.0, "Karar 9598 formülü (2× 12 aylık PTF); EPİAŞ 1–15.10.2021", "cikarim"),
    (date(2021, 9, 1), 674.0, "Karar 9598 formülü; EPİAŞ Eylül 2021 duyurusu", "cikarim"),
    (date(2021, 8, 1), 636.0, "Karar 9598 formülü; EPİAŞ Ağustos 2021 duyurusu", "cikarim"),
    (date(2021, 7, 1), 617.0, "Karar 9598 formülü; EPİAŞ Temmuz 2021 duyurusu", "cikarim"),
    (date(2021, 6, 1), 595.0, "Karar 9598 formülü; EPİAŞ Haziran 2021 duyurusu", "cikarim"),
    (date(2021, 5, 1), 578.0, "Karar 9598 formülü; EPİAŞ Mayıs 2021 duyurusu", "cikarim"),
    (date(2021, 4, 1), 567.0, "Karar 9598 formülü; EPİAŞ Nisan 2021 duyurusu", "cikarim"),
    (date(2021, 3, 1), 569.0, "Karar 9598 formülü; EPİAŞ Mart 2021 duyurusu", "cikarim"),
    (date(2021, 1, 1), 572.0, "Karar 9598 formülü; EPİAŞ Ocak–Şubat 2021 duyuruları", "cikarim"),
    (date(2020, 12, 1), 572.0, "Karar 9598 formülü; EPİAŞ Aralık 2020 duyurusu", "cikarim"),
    (date(2020, 11, 1), 566.0, "Karar 9598 formülü; EPİAŞ Kasım 2020 duyurusu", "cikarim"),
    (date(2020, 10, 7), 563.0, "Karar 9598 (RG 6.10.2020-31266); EPİAŞ 7–31.10.2020 duyurusu", "dogrulandi"),
    (date(2020, 4, 1), 2000.0, "Karar 9021 süresi doldu → geçici 1(2) 2.000 (EPİAŞ 25.3.2020 duyurusu)", "dogrulandi"),
    (date(2020, 1, 1), 600.0, "Karar 9021 (RG 28.12.2019-30992; 1.1–31.3.2020, GÖP ve DGP)", "dogrulandi"),
    (date(2017, 3, 1), 2000.0, "Karar 6851 süreli hükmü bitti → geçici 1(2) 2.000 (EPİAŞ 24.2.2017 duyurusu: 1.3.2017 teslim gününden); 2018–2019 ara kararı doğrulanmadı", "dogrulanamadi"),
    (date(2017, 1, 7), 500.0, "Karar 6851 Geçici 1(3) (RG 6.1.2017-29940; lafzen 06.01–01.03.2017, EPİAŞ 5.1.2017 duyurusu: 7.1.2017 teslim gününden)", "dogrulandi"),
    (date(2015, 7, 1), 2000.0, "Karar 5629-16 geçici 1(2) (RG 21.6.2015-29393); 2016 ve 2018–2019 ara kararı doğrulanmadı", "dogrulanamadi"),
)
AFL_KAPSAM_DISI_DEGER = 2000.0
AFL_KAPSAM_DISI_DAYANAK = "1.7.2015 öncesi: kapsam dışı (doğrulanmadı)"


def _afl_kayitlari() -> tuple[KuralKaydi, ...]:
    out = []
    for i, (bas, deger, day, dog) in enumerate(_AFL_HAM):
        bit = _AFL_HAM[i - 1][0] if i > 0 else None
        degis = f"afl-{_AFL_HAM[i + 1][0].isoformat()}" if i + 1 < len(_AFL_HAM) else None
        out.append(_afl(bas, deger, day, dog, bit, degis))
    return tuple(out)


# ---- EDT (DUY m.110) --------------------------------------------------------------------------------------------------
EDT_2025_DAYANAK = ("DUY m.110 (RG 2.2.2020-31027 Md.32); k = l = 0,03 — EPDK 4-16180 (22.09.2025) k/l karar taslağı «Mevcut Metin»: "
                    "01/05/2015'ten 0,03 (asıl karar no bulunamadı); 2.2.2020 öncesi formül farklı, 1.12.2011–30.4.2015 k = l = 0 (geçici m.21) — kapsam dışı")
EDT_2026_DAYANAK = "DUY m.110(1)-(2) (RG 29.12.2025-33122 Md.17); Karar 14030 (k/l); "
V150_DAYANAK = "V = 150 başlangıç"
V100_DAYANAK = "Karar 14911 (V = 100; «yayımı takip eden fatura dönemi» → 1.11.2026 çıkarım, EPİAŞ uygulama duyurusu bulunamadı)"
TOPLAMA_NET_DAYANAK = "; EDTA = max(ΣΣEDT(+);0), EDTB = ΣΣEDT(−) − min(ΣΣEDT(+);0) (RG 33122 Md.17)"
TOPLAMA_AYRIK_DAYANAK = "; EDTA/EDTB dönem bazlı max/min (RG 19.10.2026-33405 Md.22)"

_EDT_KAYITLARI: tuple[KuralKaydi, ...] = (
    KuralKaydi("edt.rejim", "edt-2025", "EDT formülü ve k/l (2025 rejimi)", BASLANGIC, date(2026, 1, 1),
               {"k": {y: 0.03 for y in YONLER}, "l": {y: 0.03 for y in YONLER}, "V": None, "B": None, "AFL_dali": False},
               "DUY", "DUY m.110 (RG 2.2.2020-31027 Md.32)", "2.2.2020-31027", "dogrulanamadi", EDT_2025_DAYANAK, rejim="2025"),
    KuralKaydi("edt.rejim", "edt-2026", "EDT formülü ve yöne bağlı k/l (2026 rejimi)", date(2026, 1, 1), None,
               {"k": {"acik": 0.06, "fazla": 0.03, "dengede": 0.03}, "l": {"acik": 0.03, "fazla": 0.06, "dengede": 0.03}, "B": 100.0, "AFL_dali": True},
               "DUY", "DUY m.110(1)-(2) (RG 29.12.2025-33122 Md.17); Karar 14030", "29.12.2025-33122", "dogrulandi", EDT_2026_DAYANAK, rejim="2026", degisiklik="edt-2025"),
    KuralKaydi("edt.V", "V150", "V başlangıç değeri (TL/MWh)", date(2026, 1, 1), date(2026, 11, 1), 150.0, "DUY", "DUY m.110(1) (RG 29.12.2025-33122 Md.17)", "29.12.2025-33122", "dogrulandi", V150_DAYANAK, rejim="2026"),
    KuralKaydi("edt.V", "V100", "V = 100 TL/MWh", date(2026, 11, 1), None, 100.0, "KARAR_14911", "Karar 14911 (RG 19.10.2026-33405)", "19.10.2026-33405", "cikarim", V100_DAYANAK, rejim="2026", degisiklik="V150"),
    KuralKaydi("edt.B", "B100", "B (fazla üretimde borç parametresi, TL/MWh)", date(2026, 1, 1), None, 100.0, "DUY", "DUY m.110(2) (RG 29.12.2025-33122 Md.17)", "29.12.2025-33122", "dogrulandi", "B başlangıç 100 TL/MWh", rejim="2026"),
    KuralKaydi("edt.toplama", "edta_net", "Aylık toplama: EDTA net, EDTB netlenmiş", date(2026, 1, 1), date(2026, 10, 19), "edta_net", "DUY", "DUY m.110 (RG 29.12.2025-33122 Md.17)", "29.12.2025-33122", "dogrulandi", TOPLAMA_NET_DAYANAK, rejim="2026"),
    KuralKaydi("edt.toplama", "edta_ayrik", "Aylık toplama: EDTA/EDTB dönem bazlı max/min (B borcu alacakla netleşmez)", date(2026, 10, 19), None, "edta_ayrik", "DUY", "DUY m.110 (RG 19.10.2026-33405 Md.22)", "19.10.2026-33405", "dogrulandi", TOPLAMA_AYRIK_DAYANAK, rejim="2026", degisiklik="edta_net"),
    KuralKaydi("edt.toplama", "net", "Aylık toplama: tek net EDT (2025)", BASLANGIC, date(2026, 1, 1), "net", "DUY", "DUY m.110(1) (2025 metni)", "2.2.2020-31027", "dogrulandi", "2025 tek net EDT", rejim="2025"),
)

# ---- KÜPST (DUY m.110(3); kurul kararları) — segment grupları ---------------------------------------------------------
LISANSLI = ("lisansli_serbest", "lisansli_yekdem", "yeka")
_K = lambda m, n, n_ariza=None, esik=None: {"m": m, "n": n, "n_ariza": n_ariza, "ariza_esigi": esik}   # noqa: E731
_KUPST_KAYITLARI: tuple[KuralKaydi, ...] = (
    # lisanslı güneş
    KuralKaydi("kupst", "kupst-7524", "KÜPST m/n (Karar 7524)", BASLANGIC, date(2020, 8, 1), _K(0.10, 0.03), "KARAR_7524", "Karar 7524 (RG 18.1.2018-30305)", "18.1.2018-30305", "dogrulanamadi",
               "Karar 7524 (RG 18.1.2018-30305); ilk 3 ay n 0,015 penceresinin tarihi bulunamadı — 0,03 kullanıldı", LISANSLI),
    KuralKaydi("kupst", "kupst-9422", "KÜPST m/n (Karar 9422)", date(2020, 8, 1), date(2023, 2, 1), _K(0.10, 0.03), "KARAR_9422", "Karar 9422 (RG 3.7.2020-31174)", "3.7.2020-31174", "dogrulandi",
               "Karar 9422 (RG 3.7.2020-31174; 1.8.2020'den)", LISANSLI, degisiklik="kupst-7524"),
    KuralKaydi("kupst", "kupst-11589", "KÜPST m/n (Karar 11589-2)", date(2023, 2, 1), date(2025, 1, 1), _K(0.12, 0.03), "KARAR_11589", "Karar 11589-2 (RG 27.1.2023-32086)", "27.1.2023-32086", "dogrulandi",
               "Karar 11589-2 (RG 27.1.2023-32086)", LISANSLI, degisiklik="kupst-9422"),
    KuralKaydi("kupst", "kupst-13025", "KÜPST m/n (Karar 13025; YEK arıza ≥40 → n 0,05)", date(2025, 1, 1), date(2026, 1, 1), _K(0.10, 0.03, 0.05, 40), "KARAR_13025", "Karar 13025 Md.2(1)(c), Md.3(1)", "17.12.2024-32755", "dogrulandi",
               "Karar 13025 Md.2(1)(c) YEK satırı, Md.3(1) (RG 17.12.2024-32755 s.3); taban DUY m.110(3)", LISANSLI, degisiklik="kupst-11589"),
    KuralKaydi("kupst", "kupst-14029", "KÜPST m/n (Karar 14029; arıza ≥30 → n 0,08)", date(2026, 1, 1), date(2026, 11, 1), _K(0.08, 0.05, 0.08, 30), "KARAR_14029", "Karar 14029 Md.2(1)(ç), Md.3(1)", "29.12.2025-33122", "dogrulandi",
               "Karar 14029 Md.2(1)(ç), Md.3(1) (RG 29.12.2025-33122)", LISANSLI, degisiklik="kupst-13025"),
    KuralKaydi("kupst", "kupst-14907", "KÜPST m/n (Karar 14907; net sapma)", date(2026, 11, 1), None, _K(0.08, 0.05, 0.08, 30), "KARAR_14907", "Karar 14907 Md.1(1), Md.2(1)(f), Md.3(1)(b)", "19.10.2026-33405", "cikarim",
               "Karar 14907 Md.1(1) net sapma, Md.2(1)(f), Md.3(1)(b) (RG 19.10.2026-33405); Md.7 «takip eden fatura dönemi» → 1.11.2026 çıkarım", LISANSLI, degisiklik="kupst-14029"),
    # iletime bağlı lisanssız
    KuralKaydi("kupst", "kupst-2025-iletim-belirsiz", "KÜPST m/n (iletime bağlı lisanssız, 2025 ve öncesi)", BASLANGIC, date(2026, 1, 1), _K(None, None), "KARAR_13025", "Karar 13025 Md.4 / DUY m.110(6)", "17.12.2024-32755", "dogrulanamadi",
               "2025 katsayısı DOĞRULANAMADI: Karar 13025'te bu gruba özel satır yok, DUY m.110(6)/13025 Md.4 karşı okumaya açık; "
               "yükümlülük hukuken RG 21.1.2025-32789 m.69(10), fiilen TPYS 11.03.2025", ("lisanssiz_iletim",)),
    KuralKaydi("kupst", "kupst-14029-iletim", "KÜPST m/n (iletime bağlı lisanssız, Karar 14029)", date(2026, 1, 1), date(2026, 11, 1), _K(0.20, 0.02), "KARAR_14029", "Karar 14029 Md.2(1)(c), Md.3(1)", "29.12.2025-33122", "dogrulandi",
               "Karar 14029 Md.2(1)(c), Md.3(1) (RG 29.12.2025-33122; 14907 Md.6 ile 1.11.2026'da kalktı)", ("lisanssiz_iletim",), degisiklik="kupst-2025-iletim-belirsiz"),
    KuralKaydi("kupst", "kupst-14907-iletim", "KÜPST m/n (iletime bağlı lisanssız, Karar 14907)", date(2026, 11, 1), None, _K(0.20, 0.02), "KARAR_14907", "Karar 14907 Md.2(1)(c), Md.3(1)(d)", "19.10.2026-33405", "cikarim",
               "Karar 14907 Md.2(1)(c), Md.3(1)(d); Md.1(3) brüt; LÜY 5(1)(ç),(d),(e) tesislerine uygulanmaz (Md.5 — santral ayarı «LÜY istisnası»)", ("lisanssiz_iletim",), degisiklik="kupst-14029-iletim"),
    KuralKaydi("kupst", "kupst-14907-luy-istisna", "KÜPST uygulanmaz (LÜY m.5(1)(ç),(d),(e) istisnası)", date(2026, 11, 1), None, _K(0.0, 0.0), "KARAR_14907", "Karar 14907 Md.5", "19.10.2026-33405", "yorum",
               "Karar 14907 Md.5: LÜY m.5(1)(ç),(d),(e) kapsamındaki iletime bağlı tesislere karar uygulanmaz (santral ayarı)", ("lisanssiz_iletim",), kosul="luy_istisna"),
    # dağıtıma bağlı lisanssız
    KuralKaydi("kupst", "kupst-dagitim-santral-0", "KÜPST santral sahibinde 0 (GTŞ/toplayıcı UEVÇB'sinde)", BASLANGIC, None, _K(0.0, 0.0), "DUY", "DUY m.69(11), m.110(3), m.110(6)(b)(3)", "19.10.2026-33405", "yorum",
               "Dağıtıma bağlı lisanssız: KÜPST santral sahibinde değil, GTŞ/toplayıcı UEVÇB'sinde hesaplanır (GTŞ: DUY m.69(11) + m.110(3); toplayıcı: m.110(6)(b)(3); "
               "RG 19.10.2026-33405 ile 19.10.2026'dan; üreticiye yansıtma m.132/Ç(18) olası — GTŞ'de yansıtma hükmü yok, toplayıcıda hizmet anlaşmasına bağlı; "
               "öncesinde toplayıcı için eski m.110(6) tesis bazında münferit (1.1.2025), GTŞ için m.69(2) + TPYS 11.03.2025)", ("lisanssiz_dagitim",)),
    KuralKaydi("kupst", "kupst-dagitim-portfoy-belirsiz", "KÜPST m/n (GTŞ/toplayıcı UEVÇB'si, 1.11.2026 öncesi)", BASLANGIC, date(2026, 11, 1), _K(None, None), "KARAR_14029", "Karar 13025/14029", "29.12.2025-33122", "belirsiz",
               "Karar 13025/14029'da dağıtıma bağlı lisanssız / GTŞ-toplayıcı UEVÇB'sine özel satır yok; genel satırın uygulanıp uygulanmadığı "
               "belirsiz (EPİAŞ uygulaması bulunamadı); KGÜP yükümlülüğü 11.03.2025'ten (TPYS); özel katsayı Karar 14907 ile 1.11.2026'dan", ("lisanssiz_dagitim",), kosul="portfoy"),
    KuralKaydi("kupst", "kupst-14907-dagitim", "KÜPST m/n (GTŞ/toplayıcı UEVÇB'si, Karar 14907)", date(2026, 11, 1), None, _K(0.25, 0.01), "KARAR_14907", "Karar 14907 Md.2(1)(ç), Md.3(1)(e); DUY m.110(6)(b)(3)", "19.10.2026-33405", "dogrulandi",
               "Karar 14907 Md.2(1)(ç) piyasa katılımcısı bazlı, Md.3(1)(e); UEVÇB: DUY m.110(6)(b)(3) (RG 19.10.2026-33405 Md.22); Md.1(3) brüt", ("lisanssiz_dagitim",), kosul="portfoy", degisiklik="kupst-dagitim-portfoy-belirsiz"),
    # taban ve net sapma
    KuralKaydi("kupst.taban", "taban-0", "KÜPST fiyat tabanı yok", BASLANGIC, date(2025, 1, 1), 0.0, "DUY", "DUY m.110(3) (eski metin)", None, "dogrulandi", "1.1.2025 öncesi fiyat tabanı yok"),
    KuralKaydi("kupst.taban", "taban-750", "KÜPST fiyat tabanı 750 TL/MWh", date(2025, 1, 1), None, 750.0, "DUY", "DUY m.110(3) (RG 17.12.2024-32755)", "17.12.2024-32755", "dogrulandi", "DUY m.110(3): KÜPST = Σ KÜPSM·max(750; NPTF; SMF)·n", degisiklik="taban-0"),
    KuralKaydi("kupst.net_sapma", "net-sapma-14907", "KÜPSM net sapma (UEÇM düşülür) — yalnız lisanslı", date(2026, 11, 1), None, True, "KARAR_14907", "Karar 14907 Md.1(1), Md.1(3)", "19.10.2026-33405", "cikarim",
               "14907 Md.1(1) net sapma (UEÇM düşülür) yalnız lisanslıda; Md.1(3): lisanssızlarda «sadece üretim miktarı» (31.10.2026 araştırması Ç2)"),
)
KUPST_YOK_DAYANAK = "KÜPST bu segmentte uygulanmaz / segment seçilmedi"

# ---- DSG üye eşiği (DUY m.111(5)) ---------------------------------------------------------------------------------------
_DSG_KAYITLARI: tuple[KuralKaydi, ...] = (
    KuralKaydi("dsg.esik", "dsg-esik-yok", "DSG üye eşiği yok (tam netleşme)", BASLANGIC, date(2025, 1, 1), None, "DUY", "DUY m.111(1)-(2) (2023 sürümü)", "17.12.2024-32755", "dogrulandi",
               "DUY m.111(3)-(5) 1.1.2025'ten (RG 17.12.2024-32755 Md.24, Md.30); öncesinde üye eşiği yok — sapmalar DSG içinde tamamen netleşir"),
    KuralKaydi("dsg.esik", "dsg-10", "DSG üye dengesizlik oranı eşiği %10", date(2025, 1, 1), date(2026, 1, 1), 0.10, "DUY", "DUY m.111(5), RG 17.12.2024-32755 Md.24", "17.12.2024-32755", "dogrulandi",
               "DUY m.111(5), RG 17.12.2024-32755 Md.24 (%10; yürürlük 1.1.2025)", degisiklik="dsg-esik-yok"),
    KuralKaydi("dsg.esik", "dsg-5", "DSG üye dengesizlik oranı eşiği %5", date(2026, 1, 1), date(2027, 1, 1), 0.05, "KARAR_13869", "Karar 13869 (RG 18.10.2025-33051)", "18.10.2025-33051", "yorum",
               "Karar 13869 (RG 18.10.2025-33051), 1.1.2026'dan %5 (grupta sayılan payın %5 alınması yorum)", degisiklik="dsg-10"),
    KuralKaydi("dsg.esik", "dsg-5-2027-varsayim", "DSG üye eşiği 2027 (karar bekleniyor; %5 varsayıldı)", date(2027, 1, 1), None, 0.05, "KARAR_13869", "Karar 13869; DUY m.111(5) yıllık düşürme", "18.10.2025-33051", "varsayim",
               "Karar 13869 yürürlükte (süre sınırı yok, %5); DUY m.111(5) uyarınca yıllık düşürme kararı en geç 1.12.2026'da alınır, "
               "RG yayımı Aralık sonuna sarkabilir; yön riski aşağı — %5 VARSAYILDI", degisiklik="dsg-5"),
)

# ---- KGÜP kesimi ve TPYS takvimi (DUY m.69) -----------------------------------------------------------------------------
_KGUP_KAYITLARI: tuple[KuralKaydi, ...] = (
    KuralKaydi("kgup.kesim", "kesim-1600", "D-1 son KGÜP bildirim saati 16:00", BASLANGIC, date(2025, 1, 1), (16, 0), "DUY", "DUY m.69(1) (RG 14.04.2009-27200 asıl metin; EPDK 19.12.2023 sürümü)", "14.04.2009-27200", "dogrulandi",
               "DUY m.69(1) (RG 14.04.2009-27200): 31.12.2024'e kadar D-1 16:00"),
    KuralKaydi("kgup.kesim", "kesim-1530", "D-1 son KGÜP bildirim saati 15:30", date(2025, 1, 1), None, (15, 30), "DUY", "DUY m.69(1) (RG 17.12.2024-32755 Md.17, 18, 20)", "17.12.2024-32755", "dogrulandi",
               "DUY m.69(1) (RG 17.12.2024-32755 Md.17): 1.1.2025'ten D-1 15:30", degisiklik="kesim-1600"),
    KuralKaydi("kgup.takvim", "takvim-2025", "TPYS gün öncesi takvimi (İstanbul)", date(2025, 1, 1), None,
               {"pencere_acilis": "14:00", "bytm_son": "14:30", "son": "15:30", "teyit": "17:00", "eak_acilis": "09:00"}, "DUY", "DUY m.69(1), (4); TPYS Bildirim Dokümanı (EPİAŞ, 19.02.2025)", "17.12.2024-32755", "dogrulandi",
               "KGÜP penceresi 14:00–15:30, BYTM son 14:30, TEİAŞ teyidi 17:00, EAK açılışı 09:00 (TPYS Bildirim Dokümanı)"),
)

# ---- piyasa senaryo fiyatı (EPDK 2025 yıllık ortalaması) ----------------------------------------------------------------
_PIYASA_KAYITLARI: tuple[KuralKaydi, ...] = (
    KuralKaydi("piyasa.senaryo", "senaryo-epdk-2025", "Senaryo fiyatı: EPDK 2025 yıllık ortalama PTF/SMF (TL/MWh)", date(2026, 1, 1), None,
               {"ptf": 2651.81, "smf": 2524.09, "ad": "senaryo (EPDK 2025 ortalaması)"}, "EPDK_SEKTOR_RAPORU", "EPDK Elektrik Piyasası Sektör Raporu Aralık 2025 (ağırlıklı ortalama PTF; aritmetik ortalama SMF)", None, "dogrulandi",
               "EPİAŞ fiyatı bağlı olmadığında senaryo; sistem yönü dengede varsayılır (k = l = 0,03)"),
)

# ---- 2027 belirsizliği --------------------------------------------------------------------------------------------------
BELIRSIZ_2027_GEREKCE = (
    "(i) m.110(1)-(2): RG 21.1.2025-32789 Md.13 (tek EDT_f; V/B/AFL ve EDTA/EDTB kalkar) yürürlük tarihi RG'de 1.1.2027 yazılı, ama 33122/33405 aynı "
    "fıkraları sonradan yeniden yazdı — ilişkisi hukuken belirsiz; tek k/l kararı yok (üç aylık duyuru süresinin 1.10.2026'da dolması çıkarım). (ii) m.110(3)-(4): Md.13 KÜPST'yi 15 dakikalık «ç» bazına alır; "
    "«ç» bazlı KÜPSM yöntem kararı yok (14907 «u» bazlı). (iii) m.91(2) + Geçici 40: 15 dakikalık DGP 1.1.2027'den önce başlamaz, "
    "fiilî başlangıç ilan edilmedi. (iv) SMF_N/SMF_P çeyrek SMF ister; Karar 14968 Şeffaflık'ta SMF'yi yalnız saatlik listeler. "
    "Varsayılan: 2026 rejimi sürer, sonuçlar «belirsiz» etiketi taşır; Kasım–Aralık 2026 RG'leri izlenir (kanıt kesimi 03.11.2026)."
)
_GELECEK_KAYITLARI: tuple[KuralKaydi, ...] = (
    KuralKaydi("2027", "2027-belirsiz", "1.1.2027 DUY m.110 değişikliği (RG 21.1.2025-32789 Md.13)", date(2027, 1, 1), None, None, "DUY", "RG 21.1.2025-32789 Md.13, Md.20(b)", "21.1.2025-32789", "belirsiz",
               BELIRSIZ_2027_GEREKCE),
    KuralKaydi("dgp.15dk", "dgp-15dk-belirsiz", "15 dakikalık DGP / uzlaştırma çözünürlüğü", date(2027, 1, 1), None, None, "DUY", "DUY m.91(2) + Geçici 40", "21.1.2025-32789", "belirsiz",
               "15 dakikalık DGP 1.1.2027'den önce başlamaz; fiilî başlangıç ilan edilmedi — arşiv saatlik, 15 dk tahmin iddia edilmez (docs/ZAMAN-SOZLESMESI.md)"),
)


def _sicil() -> tuple[KuralKaydi, ...]:
    return _afl_kayitlari() + _EDT_KAYITLARI + _KUPST_KAYITLARI + _DSG_KAYITLARI + _KGUP_KAYITLARI + _PIYASA_KAYITLARI + _GELECEK_KAYITLARI


SICIL: tuple[KuralKaydi, ...] = _sicil()
for _k in SICIL:
    assert _k.dogrulama in DOGRULAMA, _k.surum
    assert _k.yururluk_bit is None or _k.yururluk_bit > _k.yururluk_bas, _k.surum


def kayitlar(kural_id: str | None = None) -> list[KuralKaydi]:
    return [k for k in SICIL if kural_id is None or k.kural_id == kural_id]


def ara(kural_id: str, tarih: date, segment: str | None = None, kosul: str | None = None) -> KuralKaydi | None:
    """Tarihte yürürlükteki kayıt; kupst için segment grubu + koşul (portfoy / luy_istisna) eşleşmeli. Birden çok eşleşirse en yeni başlangıç."""
    adaylar = [k for k in SICIL if k.kural_id == kural_id and k.kapsar(tarih)
               and (k.segmentler is None or segment in k.segmentler) and (k.kosul == kosul)]
    if not adaylar:
        return None
    return max(adaylar, key=lambda k: k.yururluk_bas)


def guncel(kural_id: str) -> KuralKaydi:
    """Kural için en son yürürlüğe giren kayıt (tarihten bağımsız sabitler: senaryo fiyatı, TPYS takvimi) — ekleme sırasına bağlı değil."""
    return max(kayitlar(kural_id), key=lambda k: k.yururluk_bas)


def afl_zinciri() -> tuple[tuple[date, float, str], ...]:
    """Geriye uyum: `kurallar._AFL_ZINCIRI` biçimi (en yeni önce)."""
    return tuple((b, d, day) for b, d, day, _ in _AFL_HAM)


def _json(k: KuralKaydi) -> dict:
    d = asdict(k)
    for a in ("yururluk_bas", "yururluk_bit"):
        d[a] = d[a].isoformat() if d[a] else None
    if isinstance(d["deger"], tuple):
        d["deger"] = list(d["deger"])
    if isinstance(d["segmentler"], tuple):
        d["segmentler"] = list(d["segmentler"])
    return d


def tablo() -> list[dict]:
    """Sicilin tamamı (API / anlık görüntü), yürürlük başına göre sıralı."""
    return [_json(k) for k in sorted(SICIL, key=lambda k: (k.kural_id, k.yururluk_bas, k.surum))]


@lru_cache(maxsize=1)
def sicil_sha16() -> str:
    """Sicil içeriğinin SHA-256 ilk 16 hex'i — sonuç meta'larında «hangi kural kümesiyle hesaplandı» damgası. SICIL değişmez → tek hesap."""
    metin = json.dumps(tablo(), ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(metin.encode("utf-8")).hexdigest()[:16]


def yururlukte(tarih: date) -> list[dict]:
    return [_json(k) for k in SICIL if k.kapsar(tarih)]


def gelecek(tarih: date) -> list[dict]:
    """Tarihten sonra yürürlüğe girecek kayıtlar (geçiş hükümleri, belirsizler)."""
    return [_json(k) for k in sorted(SICIL, key=lambda k: k.yururluk_bas) if k.yururluk_bas > tarih]


def ozet(tarih: date) -> dict:
    """API özeti: sicil sürümü, sha, sayılar, doğrulama dağılımı, tarihteki ve gelecekteki kayıtlar."""
    yur = yururlukte(tarih); gel = gelecek(tarih)
    dag: dict[str, int] = {}
    for k in SICIL:
        dag[k.dogrulama] = dag.get(k.dogrulama, 0) + 1
    return {"surum": SURUM, "sha16": sicil_sha16(), "kayit": len(SICIL), "dogrulama_dagilimi": dag, "tarih": tarih.isoformat(),
            "yururlukte": yur, "gelecek": gel,
            "belirsiz": [k.surum for k in SICIL if k.dogrulama in ("belirsiz", "varsayim", "dogrulanamadi")]}
