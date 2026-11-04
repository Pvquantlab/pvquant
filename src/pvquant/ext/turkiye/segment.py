"""Segmentasyon — santral tipine göre dengesizlik sorumluluğu, KGÜP yükümlülüğü ve gelir formülü.

Segmentler (kaynak: DUY m.69, m.110–111 (RG 14.04.2009-27200; son değişiklik RG 19.10.2026-33405); LÜY (RG 12.05.2019-30772; değişiklik RG 02.04.2026-33212);
5346 sayılı Kanun (RG 18.05.2005-25819) ve YEK Yön. (RG 01.10.2013-28782); CK 7189 (RG 01.05.2023-32177) / CK 2949 (RG 18.09.2020-31248) / CK 11415
(RG 13.06.2026-33279) — tam künyeler kunye.py; v2.535):
  LISANSLI_SERBEST      : gelir = üretim·PTF (ikili anlaşma varsa sözleşme fiyatı); dengesizlik + KÜPST santralde (ya da DSG'de)
  LISANSLI_YEKDEM       : gelir = üretim·YEKDEM fiyatı (TL/MWh, aylık uzlaştırma); dengesizlik AYRI hesaplanır (santral/DSG) — YEKDEM içi
                          dağılım ayrıntısı teyit edilemedi → parametre
  YEKA                  : sözleşme fiyatı; dengesizlik sözleşmeye göre (parametre)
  LISANSSIZ_ILETIM      : KGÜP bildirir (md. 69(10)); dengesizlik toplayıcı/GTŞ portföyünde, KÜPST toplayıcı portföyünde
  LISANSSIZ_DAGITIM     : KGÜP yok; ihtiyaç fazlası GTŞ/toplayıcı alır (10 yıl YEKDEM); doğrudan dengesizlik YOK — toplayıcı taşır
  OZ_TUKETIM_SAATLIK    : 1 Mayıs 2026 saatlik mahsuplaşma: saatlik net = üretim − tüketim; fazla GTŞ fiyatıyla, eksik tarifeyle
Çıktı: kurallar tablosu + saatlik gelir hesabı; dengesizlik simülatörüne 'kimin cebinden' bilgisi.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import pandas as pd
# v2.535 dayanak künyeleri [DUY, LUY, YEK_YON, 5346, CK7189, CK2949, CK11415, KARAR_14907] — bu dosyadaki madde atıflarının birincil yayımı (RG tarih-sayı, karar no); metin kunye.py sicilinden üretildi,
# tests/test_kunye_bekcisi.py sicille eş tutar (kaynak: 03.11.2026 doğrulama arşivi 03_Kaynak_Envanteri).
DAYANAK_KUNYELERI = (
    'DUY: Elektrik Piyasası Dengeleme ve Uzlaştırma Yönetmeliği, RG 14.04.2009-27200; değişiklikler RG 28.03.2015-29309, 30.10.2016-29873, 18.01.2018-30305, 09.08.2019-30857, 02.02.2020-31027, 19.11.2022-32018, 19.12.2023-32404, 17.12.2024-32755, 21.01.2025-32789, 29.12.2025-33122, 19.10.2026-33405, 21.10.2026-33407; '
    'LÜY: Elektrik Piyasasında Lisanssız Elektrik Üretim Yönetmeliği, RG 12.05.2019-30772; değişiklikler RG 09.05.2021-31479, 02.04.2026-33212, 19.10.2026-33405; '
    'YEK Yön.: Yenilenebilir Enerji Kaynaklarının Belgelendirilmesi ve Desteklenmesine İlişkin Yönetmelik, RG 01.10.2013-28782; değişiklikler RG 29.04.2016-29698 (m.16–17 mülga), 23.08.2019-30867, 19.08.2021-31573, 29.12.2025-33122, 19.10.2026-33405 (m.23(6)); '
    '5346: 5346 sayılı Yenilenebilir Enerji Kaynaklarının Elektrik Enerjisi Üretimi Amaçlı Kullanımına İlişkin Kanun, RG 18.05.2005-25819; '
    '7189 sayılı CK: 7189 sayılı Cumhurbaşkanı Kararı (1.7.2021–31.12.2030 işletmeye girecek YEK belgeli tesisler), RG 01.05.2023-32177; düzeltme RG 04.05.2023-32180; '
    'CK 2949: 2949 sayılı Cumhurbaşkanı Kararı (1.1–30.6.2021 işletmeye girenler), RG 18.09.2020-31248; '
    'CK 11415: 11415 sayılı Cumhurbaşkanı Kararı (on yılı dolan lisanssız tesiste fiyat), RG 13.06.2026-33279; '
    'Karar 14907: EPDK Kurul Kararı 14907 (KÜPST, 1.11.2026 çıkarım), RG 19.10.2026-33405'
)


class Segment(str, Enum):
    LISANSLI_SERBEST = "lisansli_serbest"
    LISANSLI_YEKDEM = "lisansli_yekdem"
    YEKA = "yeka"
    LISANSSIZ_ILETIM = "lisanssiz_iletim"
    LISANSSIZ_DAGITIM = "lisanssiz_dagitim"
    OZ_TUKETIM_SAATLIK = "oz_tuketim_saatlik"


KURALLAR = pd.DataFrame([
    {"segment": Segment.LISANSLI_SERBEST, "kgup_yukumlu": True, "dengesizlik_sahibi": "santral/DSG", "kupst": True, "fiyat": "PTF / ikili anlaşma", "uzlastirma": "saatlik"},
    {"segment": Segment.LISANSLI_YEKDEM, "kgup_yukumlu": True, "dengesizlik_sahibi": "santral/DSG (YEKDEM içi dağılım: parametre)", "kupst": True, "fiyat": "YEK fiyatı: Cetvel I (USD cent × günlük TCMB kuru) ya da 7189 CK aylık ilan (yekdem_service)", "uzlastirma": "aylık (gelir) + saatlik (dengesizlik)"},
    {"segment": Segment.YEKA, "kgup_yukumlu": True, "dengesizlik_sahibi": "sözleşmeye göre", "kupst": True, "fiyat": "YEKA sözleşme", "uzlastirma": "sözleşme"},
    {"segment": Segment.LISANSSIZ_ILETIM, "kgup_yukumlu": True, "dengesizlik_sahibi": "toplayıcı/GTŞ portföyü", "kupst": True, "fiyat": "LÜY fiyatı (GTŞ alımı, 10 yıl) / sonrası CK 11415 formülü", "uzlastirma": "saatlik"},
    {"segment": Segment.LISANSSIZ_DAGITIM, "kgup_yukumlu": False, "dengesizlik_sahibi": "GTŞ/toplayıcı (santral taşımaz)", "kupst": False, "fiyat": "LÜY fiyatı (GTŞ alımı, 10 yıl) / toplayıcı sözleşmesi", "uzlastirma": "saatlik mahsup"},
    {"segment": Segment.OZ_TUKETIM_SAATLIK, "kgup_yukumlu": False, "dengesizlik_sahibi": "yok (mahsuplaşma)", "kupst": False, "fiyat": "saatlik net: fazla GTŞ fiyatı, eksik tarife", "uzlastirma": "saatlik mahsup"},
]).set_index("segment")


@dataclass
class Santral:
    ad: str
    segment: Segment
    kurulu_guc_mw: float
    yekdem_fiyat_tl_mwh: float | None = None
    sozlesme_fiyat_tl_mwh: float | None = None
    dsg: str | None = None            # DSG/toplayıcı adı
    yekdem_dengesizlik_payi: float = 1.0   # YEKDEM içi: santralin taşıdığı dengesizlik payı (teyit edilemedi → parametre)

    def kural(self) -> pd.Series:
        return KURALLAR.loc[self.segment]

    def dengesizlik_tasir_mi(self) -> bool:
        return self.segment in (Segment.LISANSLI_SERBEST, Segment.LISANSLI_YEKDEM, Segment.YEKA, Segment.LISANSSIZ_ILETIM)

    def kgup_gerekli_mi(self) -> bool:
        return bool(self.kural()["kgup_yukumlu"])


def gelir(santral: Santral, uretim_mwh: pd.Series, ptf: pd.Series | None = None, tuketim_mwh: pd.Series | None = None,
          gts_fiyat_tl_mwh: float | None = None, tarife_tl_mwh: float | None = None) -> pd.DataFrame:
    """Saatlik brüt gelir (dengesizlik hariç — o `dengesizlik.saatlik` ile ayrı eklenir).
    03.11.2026 doğrulama arşivi DK-292 / DK-652 (kanıt A): bu fonksiyon hiçbir servisçe çağrılmaz (gelir tarife_service → ext.turkiye.tarife.gelir);
    YEKDEM dalı tek sabit fiyat varsayar (gerçekte Cetvel I günlük kur ya da 7189 aylık ilan — yekdem_service), iletime bağlı lisanssız dalı
    PTF'ye düşer (gerçekte LÜY fiyatıyla GTŞ alımı 10 yıl, sonrası CK 11415). Yeni kullanıma bağlanmadan önce bu iki dal düzeltilmelidir."""
    s = santral.segment
    idx = uretim_mwh.index
    if s in (Segment.LISANSLI_SERBEST, Segment.LISANSSIZ_ILETIM) and santral.sozlesme_fiyat_tl_mwh is None:
        if ptf is None:
            raise ValueError("PTF gerekli")
        g = uretim_mwh * ptf.reindex(idx); kaynak = "PTF"
    elif s in (Segment.LISANSLI_YEKDEM, Segment.LISANSSIZ_DAGITIM):
        f = santral.yekdem_fiyat_tl_mwh
        if f is None:
            raise ValueError("YEKDEM fiyatı gerekli")
        g = uretim_mwh * f; kaynak = "YEKDEM"
    elif s == Segment.OZ_TUKETIM_SAATLIK:
        if tuketim_mwh is None or gts_fiyat_tl_mwh is None or tarife_tl_mwh is None:
            raise ValueError("tüketim, GTŞ fiyatı ve tarife gerekli")
        net = uretim_mwh - tuketim_mwh.reindex(idx).fillna(0)
        g = net.clip(lower=0) * gts_fiyat_tl_mwh - (-net).clip(lower=0) * tarife_tl_mwh
        # 'kaçınılan alım' değeri: tüketimin üretimle karşılanan kısmı × tarife
        # santralin değeri = kaçınılan alım (öz tüketilen × tarife) + fazlanın satışı; alım_tl tüketicinin kalan faturasıdır (bilgi)
        kacinilan = pd.concat([uretim_mwh, tuketim_mwh.reindex(idx).fillna(0)], axis=1).min(axis=1) * tarife_tl_mwh
        satis = net.clip(lower=0) * gts_fiyat_tl_mwh
        return pd.DataFrame({"net_mwh": net, "satis_tl": satis, "alim_tl": (-net).clip(lower=0) * tarife_tl_mwh,
                             "kacinilan_alim_tl": kacinilan, "gelir_tl": satis + kacinilan, "kaynak": "mahsup"})
    else:  # YEKA / sözleşme
        f = santral.sozlesme_fiyat_tl_mwh
        if f is None:
            raise ValueError("sözleşme fiyatı gerekli")
        g = uretim_mwh * f; kaynak = "sözleşme"
    return pd.DataFrame({"gelir_tl": g, "kaynak": kaynak})


def dengesizlik_paylastir(santral: Santral, toplam_maliyet_tl: pd.Series) -> pd.Series:
    """Segment kuralına göre santralin cebinden çıkan kısım (YEKDEM içi pay parametreyle)."""
    if not santral.dengesizlik_tasir_mi():
        return toplam_maliyet_tl * 0.0
    pay = santral.yekdem_dengesizlik_payi if santral.segment == Segment.LISANSLI_YEKDEM else 1.0
    return toplam_maliyet_tl * pay
