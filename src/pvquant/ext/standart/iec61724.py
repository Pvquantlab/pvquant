"""IEC 61724-1:2021 performans göstergeleri.

Tanımlar (τ raporlama dönemi, saatlik veriden):
  H_i  : POA ışınım toplamı (kWh/m²)            Y_r = H_i / G_STC        (referans verim, h)
  E_dc : dizi DC enerjisi (kWh)                 Y_a = E_dc / P_0         (dizi verimi, h)
  E_ac : sisteme AC enerji (kWh)                Y_f = E_ac / P_0         (son verim, h)
  PR = Y_f / Y_r ;  L_c = Y_r − Y_a (yakalama kaybı) ;  L_s = Y_a − Y_f (sistem kaybı)
  Sıcaklık düzeltmeli PR′ (IEC Ek: yıllık ağırlıklı hücre sıcaklığı):
    PR′ = Y_f / Σ_k [ (G_k/G_STC) · (1 + γ(T_c,k − T_ref)) ]  ; T_ref = yıllık ışınım-ağırlıklı ortalama T_c
    (T_ref = 25 °C alınırsa 'STC-düzeltmeli PR' olur — ikisi de sunulur.)
  Kapasite faktörü CF = E_ac / (P_0 · saat).
Veri kalitesi: dönem içinde kullanılabilir veri oranı < %95 ise bayrak (IEC 61724-1 §8).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

G_STC = 1000.0


@dataclass
class KPI:
    donem: str; H_i: float; Y_r: float; Y_a: float | None; Y_f: float; PR: float
    PR_stc: float | None; PR_yillik_agirlikli: float | None; L_c: float | None; L_s: float | None
    CF: float; veri_orani: float; bayrak: str

    def tablo(self) -> pd.Series:
        return pd.Series(self.__dict__)


def hucre_sicakligi_faiman(poa: pd.Series, temp_air: pd.Series, wind: pd.Series, u0: float = 25.0, u1: float = 6.84) -> pd.Series:
    """Faiman (IEC 61853-2): T_c = T_a + G / (u0 + u1·v)."""
    return temp_air + poa / (u0 + u1 * wind)


def t_ref_yillik(poa: pd.Series, t_cell: pd.Series) -> float:
    """Yıllık ışınım-ağırlıklı ortalama hücre sıcaklığı (IEC 61724-1 sıcaklık düzeltmesi referansı)."""
    w = poa.clip(lower=0)
    return float((w * t_cell).sum() / max(w.sum(), 1e-9))


def kpi(e_ac_kwh: pd.Series, poa_wm2: pd.Series, p0_kwp: float, e_dc_kwh: pd.Series | None = None,
        t_cell: pd.Series | None = None, gamma: float = -0.0035, t_ref: float | None = None, donem: str = "ME",
        min_veri_orani: float = 0.95) -> pd.DataFrame:
    """Saatlik girdi → dönem (ay/yıl) bazlı KPI tablosu. gamma: 1/°C (ör. −0,0035)."""
    idx = e_ac_kwh.index.intersection(poa_wm2.index)
    e = e_ac_kwh.loc[idx].astype(float); g = poa_wm2.loc[idx].astype(float).clip(lower=0)
    beklenen = pd.Series(1.0, index=idx).resample(donem).size()
    gecerli = (e.notna() & g.notna())
    if t_cell is not None:
        tc = t_cell.loc[idx]
        if t_ref is None:
            t_ref = t_ref_yillik(g[gecerli], tc[gecerli])
    satirlar = []
    for d, ii in gecerli.groupby(gecerli.resample(donem).transform(lambda x: 0)).groups.items() if False else []:
        pass
    grup = pd.Series(idx, index=idx).resample(donem)
    for d, blok in grup:
        ii = blok.index
        ok = gecerli.loc[ii]
        n_ok = int(ok.sum()); n_top = len(ii)
        veri_orani = n_ok / max(n_top, 1)
        ee = e.loc[ii][ok]; gg = g.loc[ii][ok]
        H_i = float(gg.sum() / 1000.0)
        Y_r = H_i  # kWh/m² / (1 kW/m²) = h
        Y_f = float(ee.sum() / p0_kwp)
        PR = Y_f / Y_r if Y_r > 0 else np.nan
        Y_a = L_c = L_s = None
        if e_dc_kwh is not None:
            Y_a = float(e_dc_kwh.loc[ii][ok].sum() / p0_kwp); L_c = Y_r - Y_a; L_s = Y_a - Y_f
        PR_stc = PR_w = None
        if t_cell is not None:
            tc = t_cell.loc[ii][ok]
            payda_stc = float(((gg / G_STC) * (1 + gamma * (tc - 25.0))).sum())
            payda_w = float(((gg / G_STC) * (1 + gamma * (tc - t_ref))).sum())
            PR_stc = Y_f / payda_stc if payda_stc > 0 else np.nan
            PR_w = Y_f / payda_w if payda_w > 0 else np.nan
        CF = float(ee.sum() / (p0_kwp * max(n_ok, 1)))
        bayrak = "" if veri_orani >= min_veri_orani else f"veri %{veri_orani*100:.0f} < %{min_veri_orani*100:.0f}"
        satirlar.append(KPI(str(d.date()), H_i, Y_r, Y_a, Y_f, PR, PR_stc, PR_w, L_c, L_s, CF, veri_orani, bayrak).tablo())
    out = pd.DataFrame(satirlar).set_index("donem")
    out.attrs["t_ref"] = t_ref
    return out


def yillik_ozet(kpi_aylik: pd.DataFrame) -> pd.Series:
    """Aylık KPI'lardan yıllık toplam/ağırlıklı PR (aylık PR'lerin ortalaması DEĞİL)."""
    Y_f = kpi_aylik["Y_f"].sum(); Y_r = kpi_aylik["Y_r"].sum()
    out = {"Y_r": Y_r, "Y_f": Y_f, "PR": Y_f / Y_r if Y_r else np.nan, "CF": kpi_aylik["CF"].mean(),
           "veri_orani": kpi_aylik["veri_orani"].mean()}
    if "Y_a" in kpi_aylik and kpi_aylik["Y_a"].notna().any():
        Y_a = kpi_aylik["Y_a"].sum(); out.update({"Y_a": Y_a, "L_c": Y_r - Y_a, "L_s": Y_a - Y_f})
    return pd.Series(out)
