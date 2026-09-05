"""Segmentasyon — santral tipine göre dengesizlik sorumluluğu, KGÜP yükümlülüğü ve gelir formülü.

Segmentler (kaynak: DUY md. 69/110–111, LÜY RG 02.04.2026, YEK Kanunu/YEKDEM Yön.):
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

import numpy as np
import pandas as pd


class Segment(str, Enum):
    LISANSLI_SERBEST = "lisansli_serbest"
    LISANSLI_YEKDEM = "lisansli_yekdem"
    YEKA = "yeka"
    LISANSSIZ_ILETIM = "lisanssiz_iletim"
    LISANSSIZ_DAGITIM = "lisanssiz_dagitim"
    OZ_TUKETIM_SAATLIK = "oz_tuketim_saatlik"


KURALLAR = pd.DataFrame([
    {"segment": Segment.LISANSLI_SERBEST, "kgup_yukumlu": True, "dengesizlik_sahibi": "santral/DSG", "kupst": True, "fiyat": "PTF / ikili anlaşma", "uzlastirma": "saatlik"},
    {"segment": Segment.LISANSLI_YEKDEM, "kgup_yukumlu": True, "dengesizlik_sahibi": "santral/DSG (YEKDEM içi dağılım: parametre)", "kupst": True, "fiyat": "YEKDEM sabit", "uzlastirma": "aylık (gelir) + saatlik (dengesizlik)"},
    {"segment": Segment.YEKA, "kgup_yukumlu": True, "dengesizlik_sahibi": "sözleşmeye göre", "kupst": True, "fiyat": "YEKA sözleşme", "uzlastirma": "sözleşme"},
    {"segment": Segment.LISANSSIZ_ILETIM, "kgup_yukumlu": True, "dengesizlik_sahibi": "toplayıcı/GTŞ portföyü", "kupst": True, "fiyat": "YEKDEM (10 yıl) / PTF", "uzlastirma": "saatlik"},
    {"segment": Segment.LISANSSIZ_DAGITIM, "kgup_yukumlu": False, "dengesizlik_sahibi": "GTŞ/toplayıcı (santral taşımaz)", "kupst": False, "fiyat": "YEKDEM (10 yıl) / toplayıcı sözleşmesi", "uzlastirma": "saatlik mahsup"},
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
    """Saatlik brüt gelir (dengesizlik hariç — o `dengesizlik.saatlik` ile ayrı eklenir)."""
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
