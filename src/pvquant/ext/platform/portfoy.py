"""Portföy görünümü — çok santral toplama ve özet.

Girdi: santral kayıtları + santral bazlı saatlik tahmin/gerçekleşen serileri (UTC) + karne satırları.
Çıktı: portföy toplamı (MW), kapasite-ağırlıklı PR/WMAPE, günlük toplamlar, sıralamalar, alarm özeti.
Hiyerarşik uzlaştırma (MinT) pvquant.ext.tahmin.portfoy'da; burada yalnız toplama ve görüntüleme verisi.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class SantralKaydi:
    id: str; ad: str; kurulu_guc_mw: float; bolge: str = ""; segment: str = ""; etiketler: list[str] = field(default_factory=list)


@dataclass
class Portfoy:
    santraller: dict[str, SantralKaydi]

    def kapasite(self, ids: list[str] | None = None) -> float:
        return float(sum(s.kurulu_guc_mw for k, s in self.santraller.items() if ids is None or k in ids))

    def gruplar(self, anahtar: str = "bolge") -> dict[str, list[str]]:
        g: dict[str, list[str]] = {}
        for k, s in self.santraller.items():
            g.setdefault(getattr(s, anahtar) or "—", []).append(k)
        return g


def topla(seriler: dict[str, pd.Series], ids: list[str] | None = None) -> pd.Series:
    """Saatlik seriler (MW ya da MWh) → toplam; eksik santral saati NaN ise toplam da 'eksik' bayrağıyla."""
    secili = {k: v for k, v in seriler.items() if ids is None or k in ids}
    if not secili:
        return pd.Series(dtype=float)
    df = pd.concat(secili.values(), axis=1, keys=list(secili))
    return df.sum(axis=1, min_count=len(secili))


def eksik_haritasi(seriler: dict[str, pd.Series]) -> pd.DataFrame:
    df = pd.concat(seriler.values(), axis=1, keys=list(seriler))
    return df.isna().resample("D").mean()   # gün × santral eksik oranı


def agirlikli_kpi(karneler: dict[str, dict], portfoy: Portfoy, alanlar=("wmape", "pr", "skill")) -> pd.Series:
    """Santral karnelerinden kapasite-ağırlıklı portföy KPI'ları. karneler[id] = {"wmape":.., "pr":.., ...}."""
    out = {}
    for a in alanlar:
        pay = payda = 0.0
        for k, kr in karneler.items():
            v = kr.get(a)
            if v is None or (isinstance(v, float) and np.isnan(v)):
                continue
            w = portfoy.santraller[k].kurulu_guc_mw; pay += v * w; payda += w
        out[a] = pay / payda if payda else np.nan
    out["kapsanan_kapasite_mw"] = sum(portfoy.santraller[k].kurulu_guc_mw for k in karneler)
    return pd.Series(out)


def siralama(karneler: dict[str, dict], portfoy: Portfoy, alan: str = "wmape", n: int = 5, kucuk_iyi: bool = True) -> pd.DataFrame:
    df = pd.DataFrame([{"id": k, "ad": portfoy.santraller[k].ad, "mw": portfoy.santraller[k].kurulu_guc_mw, alan: v.get(alan)} for k, v in karneler.items()]).dropna(subset=[alan])
    df = df.sort_values(alan, ascending=kucuk_iyi)
    return pd.concat([df.head(n).assign(grup="en_iyi"), df.tail(n).assign(grup="en_kotu")])


def gunluk_ozet(tahmin_mw: dict[str, pd.Series], gercek_mw: dict[str, pd.Series], portfoy: Portfoy, tz: str = "Europe/Istanbul") -> pd.DataFrame:
    T = topla(tahmin_mw).tz_convert(tz); G = topla(gercek_mw).tz_convert(tz)
    df = pd.DataFrame({"tahmin_mwh": T.resample("D").sum(min_count=1), "gercek_mwh": G.resample("D").sum(min_count=1)})
    df["sapma_mwh"] = df["gercek_mwh"] - df["tahmin_mwh"]
    df["sapma_pct"] = df["sapma_mwh"] / df["gercek_mwh"].replace(0, np.nan) * 100
    df["kapasite_faktoru"] = df["gercek_mwh"] / (portfoy.kapasite() * 24)
    return df


def alarm_ozeti(alarmlar: pd.DataFrame, portfoy: Portfoy) -> pd.DataFrame:
    """alarmlar: kolonlar plant_id, severity, rule, acknowledged (bool). Santral × şiddet sayımı + açık alarm oranı."""
    if alarmlar.empty:
        return pd.DataFrame(columns=["id", "ad", "kritik", "uyari", "bilgi", "acik"])
    acik = alarmlar[~alarmlar["acknowledged"].astype(bool)]
    piv = acik.pivot_table(index="plant_id", columns="severity", values="rule", aggfunc="count", fill_value=0)
    out = pd.DataFrame({"id": list(portfoy.santraller)}).set_index("id")
    for sev in ("kritik", "uyari", "bilgi"):
        out[sev] = piv[sev].reindex(out.index).fillna(0).astype(int) if sev in piv else 0
    out["acik"] = out[["kritik", "uyari", "bilgi"]].sum(axis=1)
    out.insert(0, "ad", [portfoy.santraller[i].ad for i in out.index])
    return out.reset_index()
