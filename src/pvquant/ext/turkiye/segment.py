"""Segmentasyon — santral tipine göre dengesizlik sorumluluğu, KGÜP yükümlülüğü ve gelir formülü.

Segmentler (kaynak: DUY m.69, m.110–111 (RG 14.04.2009-27200; son değişiklik RG 19.10.2026-33405); LÜY (RG 12.05.2019-30772; değişiklik RG 02.04.2026-33212);
5346 sayılı Kanun (RG 18.05.2005-25819) ve YEK Yön. (RG 01.10.2013-28782); CK 7189 (RG 01.05.2023-32177) / CK 2949 (RG 18.09.2020-31248) / CK 11415
(RG 13.06.2026-33279) — tam künyeler kunye.py; v2.535):
  LISANSLI_SERBEST      : gelir = üretim·PTF (ikili anlaşma varsa sözleşme fiyatı); dengesizlik + KÜPST santralde (ya da DSG'de)
  LISANSLI_YEKDEM       : gelir = üretim·YEKDEM fiyatı (TL/MWh, aylık uzlaştırma); dengesizlik AYRI hesaplanır (santral/DSG); YEKDEM portföy
                          dengesizliği 01.05.2016'dan mülga (RG 29.04.2016-29698), pay 1,0; m.23(6) dışı üretim 19.10.2026'dan (yekdem_service)
  YEKA                  : yarışma fiyatı; şartname süresince YEKDEM kapsamında (5346 m.4(2)); dengesizlik ve KÜPST santralde (YEK Yön. m.23(1)),
                          şartname özel hükmü varsa parametre (sözleşme hükmü doğrulanmadı)
  LISANSSIZ_ILETIM      : KGÜP bildirir (DUY m.69(10)); dengesizlik toplayıcı/GTŞ portföyünde — v2.538 (EK-3 DK-653/DK-785, kanıt A): EDT'nin tesis
                          sahibine yansıtılmasına dair açık hüküm DUY'da bulunamadı, yansıyan kalemler talimat tutarlarıdır (m.75(3)); bu yüzden
                          dengesizlik_tasir_mi False (eski «santral taşır, pay 1,0» varsayımı kaynaksızdı), yansıtma sözleşme konusudur;
                          KÜPST santral bazında hesaplanır (Karar 14907 m.2(1)(c): 0,02; m.3(1)(d) tolerans 0,20; 1.11.2026)
  LISANSSIZ_DAGITIM     : santral sahibi KGÜP bildirmez, KGÜP GTŞ/toplayıcı UEVÇB'sinden (DUY m.69(11)); KÜPST portföy UEVÇB'sinde 1.11.2026'dan
                          (Karar 14907); ihtiyaç fazlasını GTŞ/toplayıcı alır (10 yıl, sonrası CK 11415); EDT/KÜPST santralde değil — talimat tutarları
                          (DUY m.75(3)) ve LÜY Ek m.4 tahsilatı yansıtılabilir
  OZ_TUKETIM_SAATLIK    : 1 Mayıs 2026 saatlik mahsuplaşma (LÜY m.4(1)(ö), RG 02.04.2026-33212; mesken aylık m.26(20)): saatlik net = üretim − tüketim;
                          model fazlayı GTŞ fiyatıyla, eksiği tarifeyle değerler — (ç)/(d) bendi tesislerinde fazlaya ödeme yok (m.26(5)), modellenmedi; fiilî uygulama teyitsiz.
                          v2.538 KAPSAM SINIRI (EK-3 DK-662/DK-668/DK-696, kanıt A): LÜY m.26(17) iki kat sınırı (12.5.2019 ve sonrası çağrı mektuplu
                          tesiste yıllık üretimin ilişkili tüketimin iki katını aşan kısmına ödeme yok) ve m.26(20) mesken aylık mahsup istisnası
                          modellenmedi; öz tüketim/saatlik mahsup hesabı ürün yüzeyine bağlı DEĞİL (gelir() çağrılmaz, tüketim verisi girişi yok)
Çıktı: kurallar tablosu + saatlik gelir hesabı; dengesizlik simülatörüne 'kimin cebinden' bilgisi. GTŞ/toplayıcı portföy netleşmesi modellenmez
(tek santral, üst sınır). KÜPST santral bazında hesaplanır (DUY m.110(6)(b)(2)); tahakkuk GTŞ/toplayıcıya, yansıtma m.132/Ç(18). Toplayıcı portföyü DSG değildir (DUY m.20(4)).
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
    {"segment": Segment.LISANSLI_YEKDEM, "kgup_yukumlu": True, "dengesizlik_sahibi": "santral/DSG (YEKDEM portföy dengesizliği 01.05.2016'dan mülga)", "kupst": True, "fiyat": "YEK fiyatı: Cetvel I (USD cent × günlük TCMB kuru) ya da 7189 CK aylık ilan (yekdem_service)", "uzlastirma": "aylık (gelir) + saatlik (dengesizlik)"},
    {"segment": Segment.YEKA, "kgup_yukumlu": True, "dengesizlik_sahibi": "sözleşmeye göre", "kupst": True, "fiyat": "YEKA sözleşme", "uzlastirma": "sözleşme"},
    {"segment": Segment.LISANSSIZ_ILETIM, "kgup_yukumlu": True, "dengesizlik_sahibi": "toplayıcı/GTŞ portföyü (EDT'nin tesis sahibine yansıtılmasına dair açık hüküm bulunamadı; talimat tutarları DUY m.75(3) ile yansıtılır)", "kupst": True, "fiyat": "LÜY fiyatı (GTŞ alımı, 10 yıl) / sonrası CK 11415 formülü", "uzlastirma": "saatlik"},
    {"segment": Segment.LISANSSIZ_DAGITIM, "kgup_yukumlu": False, "dengesizlik_sahibi": "GTŞ/toplayıcı (santral EDT/KÜPST taşımaz; talimat tutarları ve LÜY Ek m.4 tahsilatı yansıtılabilir)", "kupst": False, "fiyat": "LÜY fiyatı (GTŞ alımı, 10 yıl) / toplayıcı sözleşmesi", "uzlastirma": "saatlik mahsup"},
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
    yekdem_dengesizlik_payi: float = 1.0   # YEKDEM içi pay: YEKDEM portföy dengesizliği 01.05.2016'dan mülga → 1,0 (parametre geriye uyum için kaldı)

    def kural(self) -> pd.Series:
        return KURALLAR.loc[self.segment]

    def dengesizlik_tasir_mi(self) -> bool:
        """Santralin cebinden çıkan dengesizlik var mı. v2.538 (DK-653/DK-785): iletime bağlı lisanssız çıkarıldı — EDT GTŞ/toplayıcı
        portföyünde (KURALLAR tablosuyla tutarlı); sahibe yansıtma sözleşmeye bağlı, mevzuatta açık hüküm bulunamadı."""
        return self.segment in (Segment.LISANSLI_SERBEST, Segment.LISANSLI_YEKDEM, Segment.YEKA)

    def kgup_gerekli_mi(self) -> bool:
        return bool(self.kural()["kgup_yukumlu"])


def gelir(santral: Santral, uretim_mwh: pd.Series, ptf: pd.Series | None = None, tuketim_mwh: pd.Series | None = None,
          gts_fiyat_tl_mwh: float | None = None, tarife_tl_mwh: float | None = None) -> pd.DataFrame:
    """Saatlik brüt gelir (dengesizlik hariç — o `dengesizlik.saatlik` ile ayrı eklenir).
    03.11.2026 doğrulama arşivi DK-292 / DK-652 (kanıt A): bu fonksiyon hiçbir servisçe çağrılmaz (gelir tarife_service → ext.turkiye.tarife.gelir);
    YEKDEM dalı tek sabit fiyat varsayar (gerçekte Cetvel I günlük kur ya da 7189 aylık ilan — yekdem_service), iletime bağlı lisanssız dalı
    PTF'ye düşer (gerçekte LÜY fiyatıyla GTŞ alımı 10 yıl, sonrası CK 11415). Yeni kullanıma bağlanmadan önce bu iki dal düzeltilmelidir.
    v2.538 (EK-3 DK-662/DK-668/DK-696, kanıt A): öz tüketim dalı LÜY m.26(17) iki kat sınırını (sınır aşıldıktan sonra fazlaya gelir 0) ve m.26(20)
    mesken aylık mahsup istisnasını (saatlik formül mesken grubuna uygulanmaz) içermez; bağlanırken bu iki kural eklenmelidir."""
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
