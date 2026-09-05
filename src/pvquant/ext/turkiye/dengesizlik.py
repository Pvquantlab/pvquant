"""Dengesizlik maliyeti simülatörü — DUY md. 110–111 ve KÜPST.

Saatlik: sapma = gerçekleşen − KGÜP (MWh).
  Pozitif dengesizlik geliri = sapma⁺ · min(PTF, SMF) · (1 − l)
  Negatif dengesizlik gideri = sapma⁻ · max(PTF, SMF) · (1 + k)         (k = l = 0,03; 1 Mayıs 2015'ten beri)
  Referans (kusursuz program) geliri = gerçekleşen · PTF
  Dengesizlik maliyeti = referans gelir − (KGÜP·PTF + pozitif gelir − negatif gider)
KÜPST (md. 110(3)-(6)): |sapma| toleransı aşan kısım · max(PTF,SMF) · n  — n ve tolerans Kurul kararı (parametre, varsayılan 0).
DSG: portföy sapmaları saatlik toplanır (netleşme), sonra formül uygulanır.
Teminat: son 3 ayın en yüksek aylık negatif dengesizlik tutarı × risk katsayısı (EPİAŞ esaslarının sadeleşmiş hali).
Kıyas: iki tahmin (ör. naif vs PVQuant) → "PVQuant X TL kurtardı".
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class Katsayilar:
    k: float = 0.03            # negatif dengesizlik
    l: float = 0.03            # pozitif dengesizlik
    kupst_n: float = 0.0       # KÜPST katsayısı (Kurul kararı; 0 = uygulanmıyor)
    kupst_tolerans: float = 0.0  # KGÜP'ün oranı olarak tolerans (ör. 0,10)
    kupst_kgup_yukumlu: bool = True


def _hizala(*seriler: pd.Series) -> pd.DatetimeIndex:
    idx = seriler[0].dropna().index
    for s in seriler[1:]:
        idx = idx.intersection(s.dropna().index)
    return idx


def saatlik(kgup_mwh: pd.Series, gerceklesen_mwh: pd.Series, ptf: pd.Series, smf: pd.Series, kat: Katsayilar = Katsayilar()) -> pd.DataFrame:
    idx = _hizala(kgup_mwh, gerceklesen_mwh, ptf, smf)
    K, G, P, S = (x.loc[idx].astype(float) for x in (kgup_mwh, gerceklesen_mwh, ptf, smf))
    sap = G - K
    poz, neg = sap.clip(lower=0), (-sap).clip(lower=0)
    fmin = pd.concat([P, S], axis=1).min(axis=1); fmax = pd.concat([P, S], axis=1).max(axis=1)
    poz_gelir = poz * fmin * (1 - kat.l)
    neg_gider = neg * fmax * (1 + kat.k)
    program_gelir = K * P
    gerceklesen_gelir = program_gelir + poz_gelir - neg_gider
    referans_gelir = G * P
    maliyet = referans_gelir - gerceklesen_gelir
    kupst = pd.Series(0.0, index=idx)
    if kat.kupst_n > 0 and kat.kupst_kgup_yukumlu:
        asim = (sap.abs() - kat.kupst_tolerans * K.abs()).clip(lower=0)
        kupst = asim * fmax * kat.kupst_n
    return pd.DataFrame({"kgup": K, "gerceklesen": G, "sapma": sap, "ptf": P, "smf": S, "pozitif_gelir": poz_gelir,
                         "negatif_gider": neg_gider, "referans_gelir": referans_gelir, "gerceklesen_gelir": gerceklesen_gelir,
                         "dengesizlik_maliyeti": maliyet, "kupst": kupst, "toplam_maliyet": maliyet + kupst})


def aylik_karne(saatlik_df: pd.DataFrame, tz: str = "Europe/Istanbul") -> pd.DataFrame:
    """Piyasa ayı İstanbul saatiyle: UTC index önce yerel saate çevrilir (1 Temmuz 00:00 IST = 30 Haziran 21:00 UTC)."""
    df = saatlik_df.copy(); df.index = df.index.tz_convert(tz)
    a = df.resample("ME").agg({"gerceklesen": "sum", "sapma": lambda x: x.abs().sum(), "referans_gelir": "sum",
                                       "dengesizlik_maliyeti": "sum", "kupst": "sum", "toplam_maliyet": "sum"})
    a["sapma_orani"] = a["sapma"] / a["gerceklesen"].replace(0, np.nan)
    a["maliyet_gelir_orani"] = a["toplam_maliyet"] / a["referans_gelir"].replace(0, np.nan)
    a["tl_per_mwh"] = a["toplam_maliyet"] / a["gerceklesen"].replace(0, np.nan)
    return a


def kiyas(kgup_a: pd.Series, kgup_b: pd.Series, gerceklesen: pd.Series, ptf: pd.Series, smf: pd.Series,
          kat: Katsayilar = Katsayilar(), ad_a: str = "naif", ad_b: str = "pvquant") -> pd.DataFrame:
    """İki program (ör. dünkü-üretim naifi vs PVQuant P50) → aylık maliyet ve fark ('kurtarılan')."""
    A = aylik_karne(saatlik(kgup_a, gerceklesen, ptf, smf, kat)); B = aylik_karne(saatlik(kgup_b, gerceklesen, ptf, smf, kat))
    out = pd.DataFrame({f"{ad_a}_tl": A["toplam_maliyet"], f"{ad_b}_tl": B["toplam_maliyet"]})
    out["kurtarilan_tl"] = out[f"{ad_a}_tl"] - out[f"{ad_b}_tl"]
    out["kurtarilan_oran"] = out["kurtarilan_tl"] / out[f"{ad_a}_tl"].replace(0, np.nan)
    return out


def dsg_netlestir(programlar: dict[str, pd.Series], gerceklesenler: dict[str, pd.Series]) -> tuple[pd.Series, pd.Series]:
    """DSG portföyü: saatlik KGÜP ve gerçekleşen toplamları (netleşme etkisi burada doğar)."""
    K = pd.concat(programlar.values(), axis=1).sum(axis=1); G = pd.concat(gerceklesenler.values(), axis=1).sum(axis=1)
    return K, G


def teminat(saatlik_df: pd.DataFrame, risk_katsayisi: float = 1.0, ay: int = 3) -> float:
    """Son `ay` ayın en yüksek aylık negatif dengesizlik gideri × risk katsayısı (sadeleştirilmiş EPİAŞ esası)."""
    a = saatlik_df["negatif_gider"].resample("ME").sum().tail(ay)
    return float(a.max() * risk_katsayisi) if len(a) else 0.0


def senaryo_spread(ptf: pd.Series, spread_oran: float = 0.2, yon_olasilik: float = 0.5, seed: int = 0) -> pd.Series:
    """SMF senaryosu: PTF·(1 ± spread) — sistem yönü rastgele (enerji açığı ↑, fazlası ↓). Gerçek SMF yoksa."""
    rng = np.random.default_rng(seed)
    yon = np.where(rng.uniform(size=len(ptf)) < yon_olasilik, 1.0, -1.0)
    return (ptf * (1 + yon * spread_oran)).clip(lower=0)


def optimal_teklif_kantili(ptf: float, smf_beklenen_acik: float, smf_beklenen_fazla: float, kat: Katsayilar = Katsayilar()) -> float:
    """Gazeteci-çocuk (newsvendor) kuralı: KGÜP için en iyi kantil τ* = c_eksik / (c_eksik + c_fazla).
    c_eksik = negatif dengesizlik birim cezası (max(PTF,SMF_açık)(1+k) − PTF), c_fazla = pozitif kayıp (PTF − min(PTF,SMF_fazla)(1−l))."""
    c_eksik = max(ptf, smf_beklenen_acik) * (1 + kat.k) - ptf
    c_fazla = ptf - min(ptf, smf_beklenen_fazla) * (1 - kat.l)
    if c_eksik + c_fazla <= 0:
        return 0.5
    return float(np.clip(c_fazla / (c_eksik + c_fazla), 0.05, 0.95))
