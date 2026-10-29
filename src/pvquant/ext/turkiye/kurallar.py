"""Kural ve parametre sürüm tablosu (F-01) — uzlaştırma kuralı TESLİM GÜNÜNE ve SEGMENTE göre seçilir.

Neden: DUY m.110 formülü ve katsayıları 2025–2027 arasında birkaç kez değişti; tarihsiz sabit (k = l = 0,03) geçmiş ayı
o ayın kuralıyla hesaplayamaz, 1.11.2026'dan sonra her ay yanlış olur. Bu modül «hangi tarihte hangi kural» sorusunun tek
kaynağıdır; hesap motoru (dengesizlik.py) buradan okur, ekran «kural: …» etiketini buradan basar.

Birincil kaynaklar (29.10.2026'da Resmî Gazete/mevzuat.gov.tr PDF'lerinden okundu; EPİAŞ sayfaları erişilemedi):
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
    dağıtıma bağlı lisanssız (piyasa katılımcısı UEVÇB'si) m 0,25 / n 0,01; iletime bağlı lisanssız 0,20 / 0,02; Md.1(3): lisanssızlarda
    yalnız üretim miktarı; Md.5: LÜY 5/1 (ç),(d),(e) iletime bağlı tesislere uygulanmaz (koşullu).
  - Karar 13025 (RG 17.12.2024; 2025): güneş m 0,10, YEK n 0,03 (ayda ≥40 arızada 0,05) — Faz 2 A raporu A-128/F1#9 (PDF bu oturumda okunmadı).
  - Karar 13869 (RG 18.10.2025): DSG üyesi dengesizlik oranı ≤ %5 → bireysel miktar grup içinde (1.1.2026'dan); 2025: %10 (RG 17.12.2024).
  - AFL zinciri (EPİAŞ duyuruları + RG; Faz 2 A §5): 2.700 (4.7.2023) → 3.000 (1.7.2024) → 3.400 (5.4.2025) → 4.500 (4.4.2026).
  - RG 21.1.2025-32789 Md.13: m.110 metni 1.1.2027'de değişir (askıda; V/B/AFL dalları ve yöne bağlı k/l metinden düşer) — hukuken
    BELİRSİZ (Faz 2 A §2.3). Varsayılan: 2026 rejimi sürer, her 2027 sonucu «belirsiz» bayrağı taşır. Md.13 rejimi bu sürümde
    yalnız bayrak olarak tutulur, formül olarak uygulanmaz.
Doğrulanamayanlar: 2025 k = l = 0,03 kararı (bülten ampirik); 2025 iletime bağlı lisanssız m/n; 1.12.2026 DSG 2027 oranı.
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
def afl(tarih: date) -> float:
    """Azami fiyat limiti (TL/MWh) — EPİAŞ/RG zinciri (Faz 2 A §5; 4.4.2026 Karar 14459 RG 3.4.2026-33213)."""
    if tarih >= date(2026, 4, 4): return 4500.0
    if tarih >= date(2025, 4, 5): return 3400.0
    if tarih >= date(2024, 7, 1): return 3000.0
    if tarih >= date(2023, 7, 4): return 2700.0
    if tarih >= date(2023, 4, 1): return 2600.0
    if tarih >= date(2023, 3, 1): return 3050.0
    if tarih >= date(2023, 2, 1): return 3650.0
    if tarih >= date(2023, 1, 1): return 4200.0
    return 4800.0


def v_degeri(tarih: date) -> float | None:
    if tarih < date(2026, 1, 1):
        return None
    return 100.0 if tarih >= date(2026, 11, 1) else 150.0     # Karar 14911


def edt_kurali(tarih: date) -> EdtKurali:
    if tarih < date(2026, 1, 1):
        return EdtKurali("2025", {y: 0.03 for y in YONLER}, {y: 0.03 for y in YONLER}, None, None, None, "net",
                         "DUY m.110 (RG 2.2.2020-31027 Md.32); k = l = 0,03 (karar bulunamadı; bülten ampirik)", "edt-2025")
    toplama = "edta_ayrik" if tarih >= date(2026, 10, 19) else "edta_net"
    v = v_degeri(tarih)
    return EdtKurali("2026", {"acik": 0.06, "fazla": 0.03, "dengede": 0.03}, {"acik": 0.03, "fazla": 0.06, "dengede": 0.03},
                     v, 100.0, afl(tarih), toplama,
                     "DUY m.110(1)-(2) (RG 29.12.2025-33122); Karar 14030 (k/l); " + ("Karar 14911 (V = 100)" if v == 100.0 else "V = 150 başlangıç")
                     + ("; toplama RG 19.10.2026-33405" if toplama == "edta_ayrik" else ""),
                     f"edt-2026-V{int(v)}-{toplama}")


def kupst_kurali(tarih: date, segment: str | None, portfoy: bool = False) -> KupstKurali:
    """Segment: ext.turkiye.segment.Segment değeri (str). portfoy=True → dağıtıma bağlı lisanssız için GTŞ/toplayıcı UEVÇB katsayısı."""
    birim = KUPST_BIRIMI.get(segment or "", "yok")
    taban = 750.0 if tarih >= date(2025, 1, 1) else 0.0
    net = tarih >= date(2026, 11, 1)
    if birim == "yok" or segment is None:
        return KupstKurali(None, None, None, None, taban, net, birim if segment else "yok", "KÜPST bu segmentte uygulanmaz / segment seçilmedi", "kupst-yok")
    if segment == "lisanssiz_dagitim":
        if portfoy and tarih >= date(2026, 11, 1):
            return KupstKurali(0.25, 0.01, None, None, taban, net, birim, "Karar 14907 Md.2(1)(ç), Md.3(1)(e) — piyasa katılımcısı UEVÇB'si", "kupst-14907-dagitim")
        if portfoy:
            return KupstKurali(None, None, None, None, taban, net, birim, "GTŞ/toplayıcı UEVÇB'si için 1.11.2026 öncesi katsayı DOĞRULANAMADI", "kupst-dagitim-portfoy-belirsiz")
        return KupstKurali(0.0, 0.0, None, None, taban, net, birim,
                           "Dağıtıma bağlı lisanssız: KÜPST santral sahibinde değil, GTŞ/toplayıcı UEVÇB'sinde hesaplanır (DUY m.110(6), m.69(11))",
                           "kupst-dagitim-santral-0")
    if segment == "lisanssiz_iletim":
        if tarih >= date(2026, 11, 1):
            return KupstKurali(0.20, 0.02, None, None, taban, net, birim, "Karar 14907 Md.2(1)(c), Md.3(1)(d); LÜY 5/1 (ç),(d),(e) tesislerine uygulanmaz (Md.5, koşullu)", "kupst-14907-iletim")
        if tarih >= date(2026, 1, 1):
            return KupstKurali(0.20, 0.02, None, None, taban, net, birim, "Karar 14029 Md.2(1)(c), Md.3(1)", "kupst-14029-iletim")
        return KupstKurali(None, None, None, None, taban, net, birim, "2025 katsayısı DOĞRULANAMADI (yükümlülük RG 21.1.2025 m.69(10))", "kupst-2025-iletim-belirsiz")
    # lisanslı güneş (serbest / YEKDEM / YEKA)
    if tarih >= date(2026, 11, 1):
        return KupstKurali(0.08, 0.05, 0.08, 30, taban, True, birim, "Karar 14907 Md.1(1) net sapma, Md.2(1)(f), Md.3(1)(b)", "kupst-14907")
    if tarih >= date(2026, 1, 1):
        return KupstKurali(0.08, 0.05, 0.08, 30, taban, False, birim, "Karar 14029 Md.2(1)(ç), Md.3(1)", "kupst-14029")
    if tarih >= date(2025, 1, 1):
        return KupstKurali(0.10, 0.03, 0.05, 40, taban, False, birim, "Karar 13025 (RG 17.12.2024); taban DUY m.110(3)", "kupst-13025")
    if tarih >= date(2023, 2, 1):
        return KupstKurali(0.12, 0.03, None, None, 0.0, False, birim, "Karar 11589-2 (RG 27.1.2023)", "kupst-11589")
    return KupstKurali(0.10, 0.03, None, None, 0.0, False, birim, "Karar 9422 (RG 3.7.2020)", "kupst-9422")


def dsg_esigi(tarih: date) -> tuple[float, str]:
    if tarih < date(2026, 1, 1):
        return 0.10, "DUY m.111(5), RG 17.12.2024-32755 (%10)"
    if tarih < date(2027, 1, 1):
        return 0.05, "Karar 13869 (RG 18.10.2025), 1.1.2026'dan %5"
    return 0.05, "2027 oranı açıklanmadı (1.12.2026 kararı bekleniyor) — %5 VARSAYILDI"


def kural(tarih: date | str | pd.Timestamp, segment: str | None = None, portfoy: bool = False) -> Kural:
    """Teslim günü (İstanbul takvim günü) için yürürlükteki kural. Saatlik damga verilirse İstanbul gününe çevrilir."""
    t = _gun(tarih)
    e, k = edt_kurali(t), kupst_kurali(t, segment, portfoy)
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
                        karsi_olgu: str | None = None) -> pd.DataFrame:
    """Saatlik index (UTC ya da saat dilimli) → her saat için yürürlükteki parametreler (vektörel hesap için).
    karsi_olgu (F-07 geri test sütunları, C iş kolu tanımı): '2026' → bütün saatlere 2026 kuralı — EDT formülü (yöne bağlı k/l, V 150 /
    1.11.2026'dan 100, B, o saatin AFL'si) VE KÜPST katsayıları Karar 14029/14907 (tarihe göre; 2025 saatlerinde 14029 brüt);
    '2026_V100' → ayrıca V = 100 bütün dönemde. DSG eşiği tarihli kalır."""
    idx = pd.DatetimeIndex(index)
    yerel = idx.tz_convert(IST) if idx.tz is not None else idx.tz_localize("UTC").tz_convert(IST)
    gunler = pd.Series(yerel.date, index=idx)
    satirlar = {}
    for g in gunler.unique():
        r = kural(g, segment, portfoy)
        if karsi_olgu in ("2026", "2026_V100"):
            g26 = max(g, date(2026, 1, 1))
            e = edt_kurali(g26); kp = kupst_kurali(g26, segment, portfoy)
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
