"""Clear-sky (McClear / Ineichen), IAM ve spektral düzeltme — model zincirinin eksik terimleri.

Bu modül POA'dan "etkin ışınım"a giden terimleri sağlar; mevcut fizik zinciri bunları
çarpan olarak alabilir (çekirdeğe dokunmadan girdi düzeyinde). pvlib üzerinden:
- Açık gök: Ineichen (Linke bulanıklığı pvlib'in aylık tablosundan) ya da CAMS McClear (ağ, e-posta).
- IAM: physical (n=1,526, K=4, L=0,002) / ashrae (b=0,05) / martin_ruiz (a_r=0,16); difüz için Marion.
- Spektral: First Solar modeli (hava kütlesi + yağışa suya göre M), modül teknolojisine göre katsayılar;
  yağışa su yoksa Gueymard 1994 yaklaşımıyla T/RH'den kestirilir.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pvlib


def acik_gok(index: pd.DatetimeIndex, lat: float, lon: float, yukseklik: float = 0.0, model: str = "ineichen") -> pd.DataFrame:
    konum = pvlib.location.Location(lat, lon, altitude=yukseklik, tz="UTC")
    orta = index + pd.Timedelta(minutes=30)
    cs = konum.get_clearsky(orta, model=model)
    cs.index = index
    return cs


def mcclear(lat: float, lon: float, baslangic: str, bitis: str, email: str) -> pd.DataFrame:
    """CAMS McClear açık gök (saatlik). Ağ gerekir; lisans CC BY 4.0."""
    df, _ = pvlib.iotools.get_cams(lat, lon, pd.Timestamp(baslangic), pd.Timestamp(bitis), email,
                                   identifier="mcclear", time_step="1h", map_variables=True)
    return df[["ghi_clear", "dni_clear", "dhi_clear"]] if "ghi_clear" in df else df


def iam_katsayilari(aoi: pd.Series, model: str = "physical", **p) -> pd.Series:
    """Işın (beam) IAM. model: physical|ashrae|martin_ruiz|sapm(param ister)."""
    if model == "physical":
        return pd.Series(pvlib.iam.physical(aoi.values, **p), index=aoi.index)
    if model == "ashrae":
        return pd.Series(pvlib.iam.ashrae(aoi.values, **p), index=aoi.index)
    if model == "martin_ruiz":
        return pd.Series(pvlib.iam.martin_ruiz(aoi.values, **p), index=aoi.index)
    raise ValueError(model)


def iam_difuz(surface_tilt: float, model: str = "physical") -> tuple[float, float]:
    """Gök difüz ve zemin yansıması için Marion integrasyonu → (iam_sky, iam_ground)."""
    iam_fn = {"physical": pvlib.iam.physical, "ashrae": pvlib.iam.ashrae, "martin_ruiz": pvlib.iam.martin_ruiz}[model]
    return float(pvlib.iam.marion_diffuse(model, surface_tilt=surface_tilt)["sky"]), float(pvlib.iam.marion_diffuse(model, surface_tilt=surface_tilt)["ground"])


def spektral_duzeltme(index: pd.DatetimeIndex, lat: float, lon: float, temp_air: pd.Series, rh: pd.Series | None,
                      pw_cm: pd.Series | None = None, modul: str = "multisi", basinc_pa: float = 101325.0) -> pd.Series:
    """First Solar spektral uyumsuzluk M (≈1 ± 0,05). modul: monosi|multisi|cdte|cigs|asi|polysi."""
    orta = index + pd.Timedelta(minutes=30)
    sp = pvlib.solarposition.get_solarposition(orta, lat, lon)
    am_rel = pvlib.atmosphere.get_relative_airmass(sp["apparent_zenith"].values)
    am_abs = pvlib.atmosphere.get_absolute_airmass(am_rel, basinc_pa)
    if pw_cm is None:
        if rh is None:
            raise ValueError("pw_cm ya da rh gerekir")
        pw_cm = pd.Series(pvlib.atmosphere.gueymard94_pw(temp_air.values, rh.values), index=index)
    M = pvlib.spectrum.spectral_factor_firstsolar(pw_cm.values, am_abs, module_type=modul)
    return pd.Series(np.nan_to_num(np.asarray(M, float), nan=1.0), index=index).clip(0.8, 1.2)


def etkin_isinim(poa_beam: pd.Series, poa_sky: pd.Series, poa_ground: pd.Series, aoi: pd.Series, surface_tilt: float,
                 spektral_M: pd.Series | None = None, iam_model: str = "physical") -> pd.Series:
    """G_eff = M · (IAM_b·B + IAM_sky·D_sky + IAM_gnd·D_gnd) — çekirdek POA'sına uygulanacak çarpanlı form."""
    ib = iam_katsayilari(aoi, iam_model); isky, ignd = iam_difuz(surface_tilt, iam_model)
    g = ib * poa_beam + isky * poa_sky + ignd * poa_ground
    return (g * (spektral_M.reindex(g.index) if spektral_M is not None else 1.0)).clip(lower=0.0)
