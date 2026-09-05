"""Çoklu NWP harmanı (ECMWF + ICON + GFS) ve ensemble yayılımı.

Yöntem:
  1. Her modelin GHI'sı gök açıklığı endeksine (kt) çevrilir — harman kt üzerinde
     yapılır ki gündoğumu/batımı eğriliği bozulmasın.
  2. Ağırlıklar: son N gündeki kt hatasının ters karesiyle (inverse-MSE); geçmiş
     yoksa eşit. Ağırlıklar ufka göre değil, modele göredir (basit ve sağlam).
  3. Ensemble üyeleri varsa (ENS/GEFS) ampirik kantiller (P10/P50/P90) üye
     dağılımından; yoksa modeller-arası yayılım × kalibrasyon katsayısı.
Bu modül model çekirdeğine dokunmaz: yalnız meteoroloji girdisini üretir.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .ortak import KOLONLAR, MeteoCerceve, acik_gok_ghi, gok_acikligi


@dataclass
class HarmanSonucu:
    df: pd.DataFrame            # ghi (P50), dni, dhi, temp_air, wind_speed_10m, cloud_cover, ghi_p10, ghi_p90
    agirliklar: dict[str, float]
    uye_sayisi: int


def agirlik_hesapla(gecmis: dict[str, pd.Series], gerceklesen: pd.Series, taban: float = 1e-4) -> dict[str, float]:
    """Model → ağırlık. gecmis[model] = geçmiş kt tahmini (saatlik), gerceklesen = ölçülen kt.
    Ortak saatlerde MSE; w ∝ 1/(MSE+taban). Veri yoksa eşit."""
    w = {}
    for ad, s in gecmis.items():
        ortak = s.dropna().index.intersection(gerceklesen.dropna().index)
        if len(ortak) < 24:
            w[ad] = np.nan
            continue
        mse = float(((s.loc[ortak] - gerceklesen.loc[ortak]) ** 2).mean())
        w[ad] = 1.0 / (mse + taban)
    if all(np.isnan(v) for v in w.values()):
        return {ad: 1.0 / len(w) for ad in w}
    dolu = {ad: v for ad, v in w.items() if not np.isnan(v)}
    top = sum(dolu.values())
    return {ad: (dolu.get(ad, 0.0) / top) for ad in w}


def harmanla(modeller: dict[str, MeteoCerceve], agirliklar: dict[str, float] | None = None,
             yayilim_katsayisi: float = 1.28) -> HarmanSonucu:
    """modeller: {"ecmwf": cerceve, "icon": ..., "gfs": ...}. Ortak saat aralığında harman."""
    if not modeller:
        raise ValueError("harmanlanacak model yok")
    lat = next(iter(modeller.values())).latitude
    lon = next(iter(modeller.values())).longitude
    idx = None
    for c in modeller.values():
        idx = c.df.index if idx is None else idx.intersection(c.df.index)
    if idx is None or len(idx) == 0:
        raise ValueError("modellerin ortak zaman aralığı boş")
    cs = acik_gok_ghi(idx, lat, lon)
    adlar = list(modeller)
    if agirliklar is None:
        agirliklar = {a: 1.0 / len(adlar) for a in adlar}
    top = sum(agirliklar.get(a, 0.0) for a in adlar) or 1.0
    w = {a: agirliklar.get(a, 0.0) / top for a in adlar}

    kt_mat = pd.DataFrame({a: gok_acikligi(modeller[a].df.loc[idx, "ghi"], lat, lon) for a in adlar})
    kt_p50 = sum(kt_mat[a].fillna(0.0) * w[a] for a in adlar)
    out = pd.DataFrame(index=idx)
    out["ghi"] = (kt_p50 * cs).clip(lower=0.0)
    for kol in ("temp_air", "wind_speed_10m", "cloud_cover"):
        out[kol] = sum(modeller[a].df.loc[idx, kol].astype(float) * w[a] for a in adlar if kol in modeller[a].df)
    # DNI/DHI: ağırlıklı ortalama (kaynak verdiyse), yoksa ayrıştır
    if all("dni" in modeller[a].df and "dhi" in modeller[a].df for a in adlar):
        out["dni"] = sum(modeller[a].df.loc[idx, "dni"] * w[a] for a in adlar)
        out["dhi"] = sum(modeller[a].df.loc[idx, "dhi"] * w[a] for a in adlar)

    # Kantiller: üyeler varsa ampirik, yoksa modeller arası yayılım
    uyeler = []
    for a in adlar:
        for _, udf in modeller[a].uyeler.items():
            if "ghi" in udf:
                uyeler.append(udf["ghi"].reindex(idx))
    if len(uyeler) >= 10:
        U = pd.concat(uyeler, axis=1)
        out["ghi_p10"] = U.quantile(0.10, axis=1).clip(lower=0.0)
        out["ghi_p90"] = U.quantile(0.90, axis=1).clip(lower=0.0)
        n_uye = len(uyeler)
    else:
        sapma = kt_mat.std(axis=1).fillna(0.0) * yayilim_katsayisi
        out["ghi_p10"] = ((kt_p50 - sapma).clip(lower=0.0) * cs)
        out["ghi_p90"] = ((kt_p50 + sapma).clip(upper=1.3) * cs)
        n_uye = 0
    cerceve = MeteoCerceve(out, lat, lon, next(iter(modeller.values())).kaynak)
    return HarmanSonucu(cerceve.df, w, n_uye)
