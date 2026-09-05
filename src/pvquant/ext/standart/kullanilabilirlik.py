"""Kullanılabilirlik (availability) — IEC 61724-3 / SolarPower Europe O&M kılavuzu kalıbı.

Zaman tabanlı: A_t = (T_toplam − T_arıza − T_hariç) / (T_toplam − T_hariç); yalnız 'üretim mümkün' saatlerde
  (POA ≥ eşik) sayılır (gece kesintisi sayılmaz).
Enerji tabanlı: A_e = E_gerçek / (E_gerçek + E_kayıp_arıza); kayıp = beklenen − gerçek, arıza saatlerinde.
Hariç tutmalar: şebeke kesintisi, kısıntı, mücbir sebep, planlı bakım (sözleşmeye göre) — olay listesiyle.
Olay günlüğünden MTBF/MTTR; evirici bazında ve tesis bazında (kapasite-ağırlıklı) kullanılabilirlik.
Sözleşme: garanti eşiği (ör. %98) ve açık (shortfall) enerji/TL hesabı.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

HARIC_TIPLERI = {"sebeke", "kisinti", "mucbir", "planli_bakim"}


@dataclass
class Olay:
    baslangic: pd.Timestamp; bitis: pd.Timestamp; tip: str = "ariza"; birim: str | None = None; not_: str = ""


def olay_maskesi(index: pd.DatetimeIndex, olaylar: list[Olay], tipler: set[str] | None = None) -> pd.Series:
    m = pd.Series(False, index=index)
    for o in olaylar:
        if tipler is None or o.tip in tipler:
            m[(index >= o.baslangic) & (index < o.bitis)] = True
    return m


def zaman_tabanli(index: pd.DatetimeIndex, poa: pd.Series, olaylar: list[Olay], poa_esik: float = 50.0,
                  haric: set[str] = HARIC_TIPLERI) -> dict:
    uretim_mumkun = poa.reindex(index).fillna(0) >= poa_esik
    ariza = olay_maskesi(index, olaylar, {"ariza"}) & uretim_mumkun
    har = olay_maskesi(index, olaylar, haric) & uretim_mumkun
    payda = int((uretim_mumkun & ~har).sum())
    return {"saat_toplam": int(uretim_mumkun.sum()), "saat_haric": int(har.sum()), "saat_ariza": int((ariza & ~har).sum()),
            "A_t": float(1 - (ariza & ~har).sum() / payda) if payda else np.nan}


def enerji_tabanli(gercek_kwh: pd.Series, beklenen_kwh: pd.Series, olaylar: list[Olay], haric: set[str] = HARIC_TIPLERI) -> dict:
    idx = gercek_kwh.index.intersection(beklenen_kwh.index)
    g = gercek_kwh.loc[idx]; b = beklenen_kwh.loc[idx]
    ariza = olay_maskesi(idx, olaylar, {"ariza"}); har = olay_maskesi(idx, olaylar, haric)
    kayip = (b - g).clip(lower=0).where(ariza & ~har, 0.0)
    E = float(g[~har].sum()); K = float(kayip.sum())
    return {"E_gercek_kwh": E, "E_kayip_ariza_kwh": K, "A_e": E / (E + K) if (E + K) > 0 else np.nan}


def mtbf_mttr(olaylar: list[Olay], donem_baslangic: pd.Timestamp, donem_bitis: pd.Timestamp, birim: str | None = None) -> dict:
    ar = [o for o in olaylar if o.tip == "ariza" and (birim is None or o.birim == birim)]
    if not ar:
        return {"ariza_sayisi": 0, "MTTR_saat": np.nan, "MTBF_saat": np.nan}
    onarim = [(o.bitis - o.baslangic) / pd.Timedelta(hours=1) for o in ar]
    toplam = (donem_bitis - donem_baslangic) / pd.Timedelta(hours=1)
    calisma = toplam - sum(onarim)
    return {"ariza_sayisi": len(ar), "MTTR_saat": float(np.mean(onarim)), "MTBF_saat": float(calisma / len(ar))}


def birim_bazli(index: pd.DatetimeIndex, poa: pd.Series, olaylar: list[Olay], kapasiteler: dict[str, float], poa_esik: float = 50.0) -> pd.DataFrame:
    """Evirici/birim bazında A_t ve kapasite-ağırlıklı tesis A_t."""
    satir = []
    for b, kap in kapasiteler.items():
        ol = [o for o in olaylar if o.birim in (b, None)]
        z = zaman_tabanli(index, poa, ol, poa_esik); satir.append({"birim": b, "kapasite": kap, **z})
    df = pd.DataFrame(satir)
    tesis = float((df["A_t"] * df["kapasite"]).sum() / df["kapasite"].sum()) if df["kapasite"].sum() else np.nan
    df.attrs["tesis_A_t"] = tesis
    return df


def sozlesme(A_gercek: float, A_garanti: float, beklenen_kwh: float, birim_fiyat_tl_kwh: float) -> dict:
    """Garanti altı kalan kullanılabilirlik için enerji açığı ve TL karşılığı (LD/tazminat tabanı)."""
    acik = max(A_garanti - A_gercek, 0.0)
    e_acik = acik * beklenen_kwh
    return {"A_gercek": A_gercek, "A_garanti": A_garanti, "acik_puan": acik, "acik_kwh": e_acik, "acik_tl": e_acik * birim_fiyat_tl_kwh}
