"""ESKİ dengesizlik maliyeti formülü (DUY m.110 2025 rejimi, k = l = 0,03) — yalnız 31.12.2025'e kadarki teslim günleri; 2026+ için ValueError.

v2.604 (F4-J): bu modüldeki ikinci Şeffaflık istemcisi (`SeffaflikIstemci`) ölüydü (hiçbir üretim yolu çağırmıyordu) ve kaldırıldı; canlı istemci
pvquant.ext.turkiye.epias.Istemci. Güncel uzlaştırma hesabı ext.turkiye.dengesizlik.saatlik() + ext.turkiye.kurallar (tarihe göre katsayı).
"""
from __future__ import annotations

import pandas as pd

from pvquant.zaman import PIYASA_TZ

# v2.535 dayanak künyeleri [DUY, KARAR_14968] — bu dosyadaki madde atıflarının birincil yayımı (RG tarih-sayı, karar no); metin kunye.py sicilinden üretildi,
# tests/test_kunye_bekcisi.py sicille eş tutar (kaynak: 03.11.2026 doğrulama arşivi 03_Kaynak_Envanteri).
DAYANAK_KUNYELERI = (
    'DUY: Elektrik Piyasası Dengeleme ve Uzlaştırma Yönetmeliği, RG 14.04.2009-27200; değişiklikler RG 28.03.2015-29309, 30.10.2016-29873, 18.01.2018-30305, 09.08.2019-30857, 02.02.2020-31027, 19.11.2022-32018, 19.12.2023-32404, 17.12.2024-32755, 21.01.2025-32789, 29.12.2025-33122, 19.10.2026-33405, 21.10.2026-33407; '
    "Karar 14968: EPDK Kurul Kararı 14968 (Şeffaflık Platformu veri listesi, 1.1.2027'den), RG 20.10.2026-33406; öncesi Karar 10711"
)

# v2.604 (F4-J): ikinci (ölü) Şeffaflık istemcisi `SeffaflikIstemci` kaldırıldı — tek istemci pvquant.ext.turkiye.epias.Istemci (TGT önbellekli,
# MockTransport'lu, UTC hizalı). Bu modülde yalnız ESKİ dengesizlik formülü (≤31.12.2025) kalır; üretim yolunda çağrılmaz.

ESKI_FORMUL_SON = "2025-12-31"   # v2.538 (DK-023): sabit k = l = 0,03'ün son teslim günü (RG 02.02.2020-31027 Md.32; 1.1.2026'dan Karar 14030)


def dengesizlik_maliyeti(kgup_mwh: pd.Series, gerceklesen_mwh: pd.Series, ptf: pd.Series, smf: pd.Series,
                         k: float = 0.03, l: float = 0.03) -> pd.DataFrame:
    """DUY md. 110–111 ESKİ formülü (RG 02.02.2020-31027 Md.32; yalnız 31.12.2025'e kadarki teslim günleri): sapma = gerçekleşen − KGÜP (saatlik MWh).
    Pozitif dengesizlik geliri = min(PTF,SMF)·(1−l)·sapma; negatif dengesizlik gideri = max(PTF,SMF)·(1+k)·|sapma|; sabit k = l = 0,03.
    'maliyet' = PTF ile satılsaydı elde edilecek gelire göre kayıp (TL). KÜPST ayrı hesaplanır (Kurul katsayıları).
    v2.538 (EK-3 DK-023): 1.1.2026'dan k ve l sistem yönüne bağlıdır (Karar 14030, RG 29.12.2025-33122) ve KÜPST netleşmesi vardır; bu fonksiyon
    üretim yolunda çağrılmaz, 2026 ve sonrası saat içeren seri için ValueError verir — güncel hesap ext.turkiye.dengesizlik.saatlik() ve
    ext.turkiye.kurallar (tarihe göre katsayı)."""
    idx = kgup_mwh.index.intersection(gerceklesen_mwh.index).intersection(ptf.index).intersection(smf.index)
    if len(idx) and isinstance(idx, pd.DatetimeIndex):
        son = idx.max(); son = son.tz_convert(PIYASA_TZ) if son.tzinfo is not None else son.tz_localize(PIYASA_TZ)
        if son >= pd.Timestamp(ESKI_FORMUL_SON, tz=PIYASA_TZ) + pd.Timedelta(days=1):
            raise ValueError("dengesizlik_maliyeti eski formüldür (k = l = 0,03; 31.12.2025'e kadar): 2026 ve sonrası için ext.turkiye.dengesizlik.saatlik() kullanın")
    sap = (gerceklesen_mwh - kgup_mwh).loc[idx]
    poz = sap.clip(lower=0.0); neg = (-sap).clip(lower=0.0)
    gelir_poz = poz * pd.concat([ptf.loc[idx], smf.loc[idx]], axis=1).min(axis=1) * (1 - l)
    gider_neg = neg * pd.concat([ptf.loc[idx], smf.loc[idx]], axis=1).max(axis=1) * (1 + k)
    referans = sap.abs() * ptf.loc[idx]
    out = pd.DataFrame({"sapma_mwh": sap, "pozitif_gelir_tl": gelir_poz, "negatif_gider_tl": gider_neg})
    out["maliyet_tl"] = (referans - gelir_poz).where(sap > 0, gider_neg - referans)
    return out
