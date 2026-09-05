"""Tarife / gelir yapılandırması — sabit, çok zamanlı, PTF-endeksli, YEKDEM (döviz endeksli), eskalasyonlu.

Tarife nesneleri saatlik fiyat (TL/MWh) üretir; `gelir()` üretimle çarpar. Çok zamanlı (ToU) dilimler İstanbul saatiyle
(varsayılan Türkiye: gündüz 06–17, puant 17–22, gece 22–06). PTF-endeksli: PTF × (1+prim) + sabit ek. YEKDEM:
USD-cent/kWh × kur (aylık TL; pvquant.ext.turkiye.segment ile uyumlu). Eskalasyon: yıllık % ya da TÜFE endeksi serisi.
Doğrulama: negatif fiyat, boşluklu dilim, tarih çakışması.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

IST = "Europe/Istanbul"


def _ist(idx: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return idx.tz_convert(IST) if idx.tz is not None else idx.tz_localize("UTC").tz_convert(IST)


@dataclass
class Sabit:
    tl_mwh: float
    def fiyat(self, idx: pd.DatetimeIndex, **_) -> pd.Series:
        if self.tl_mwh < 0: raise ValueError("negatif tarife")
        return pd.Series(self.tl_mwh, index=idx)


@dataclass
class CokZamanli:
    dilimler: dict[str, tuple[int, int]] = field(default_factory=lambda: {"gunduz": (6, 17), "puant": (17, 22), "gece": (22, 6)})
    fiyatlar: dict[str, float] = field(default_factory=dict)   # dilim → TL/MWh

    def dogrula(self) -> None:
        kapsam = [False] * 24
        for ad, (b, e) in self.dilimler.items():
            saatler = range(b, e) if b < e else list(range(b, 24)) + list(range(0, e))
            for h in saatler:
                if kapsam[h]: raise ValueError(f"dilim çakışması saat {h}")
                kapsam[h] = True
            if ad not in self.fiyatlar: raise ValueError(f"fiyat eksik: {ad}")
        if not all(kapsam): raise ValueError("24 saat kapsanmıyor")

    def dilim(self, saat: int) -> str:
        for ad, (b, e) in self.dilimler.items():
            if (b < e and b <= saat < e) or (b >= e and (saat >= b or saat < e)):
                return ad
        raise ValueError(saat)

    def fiyat(self, idx: pd.DatetimeIndex, **_) -> pd.Series:
        self.dogrula(); h = _ist(idx).hour
        return pd.Series([self.fiyatlar[self.dilim(int(s))] for s in h], index=idx)


@dataclass
class PtfEndeksli:
    prim_oran: float = 0.0; sabit_ek_tl_mwh: float = 0.0; taban: float | None = None; tavan: float | None = None
    def fiyat(self, idx: pd.DatetimeIndex, ptf: pd.Series | None = None, **_) -> pd.Series:
        if ptf is None: raise ValueError("PTF gerekli")
        f = ptf.reindex(idx) * (1 + self.prim_oran) + self.sabit_ek_tl_mwh
        return f.clip(lower=self.taban, upper=self.tavan)


@dataclass
class Yekdem:
    usd_cent_kwh: float; kur_tl_usd: pd.Series | float
    def fiyat(self, idx: pd.DatetimeIndex, **_) -> pd.Series:
        kur = self.kur_tl_usd if isinstance(self.kur_tl_usd, (int, float)) else self.kur_tl_usd.reindex(_ist(idx).to_period("M").to_timestamp().tz_localize(IST), method="ffill").values
        return pd.Series(self.usd_cent_kwh * 10.0 * np.asarray(kur, float), index=idx)   # cent/kWh → USD/MWh ×10 → TL


@dataclass
class Eskalasyon:
    yillik_oran: float = 0.0; baslangic_yil: int = 2025; endeks: pd.Series | None = None   # endeks: ay → çarpan (TÜFE/başlangıç)
    def carpan(self, idx: pd.DatetimeIndex) -> pd.Series:
        if self.endeks is not None:
            return pd.Series(self.endeks.reindex(_ist(idx).to_period("M").to_timestamp(), method="ffill").values, index=idx)
        yil = _ist(idx).year - self.baslangic_yil
        return pd.Series((1 + self.yillik_oran) ** np.maximum(yil, 0), index=idx)


@dataclass
class TarifeYapisi:
    ad: str; tarife: object; baslangic: pd.Timestamp; bitis: pd.Timestamp | None = None; eskalasyon: Eskalasyon | None = None

    def fiyat(self, idx: pd.DatetimeIndex, **ctx) -> pd.Series:
        f = self.tarife.fiyat(idx, **ctx)
        if self.eskalasyon: f = f * self.eskalasyon.carpan(idx)
        gecerli = (idx >= self.baslangic) if self.bitis is None else ((idx >= self.baslangic) & (idx < self.bitis))
        return f.where(gecerli)


def gelir(uretim_mwh: pd.Series, yapilar: list[TarifeYapisi], **ctx) -> pd.DataFrame:
    """Birden çok yapı (tarih dilimli) → saatlik fiyat ve gelir; çakışma hata, boşluk NaN."""
    idx = uretim_mwh.index
    fiyat = pd.Series(np.nan, index=idx); kaynak = pd.Series("", index=idx)
    for y in yapilar:
        f = y.fiyat(idx, **ctx); m = f.notna()
        if (fiyat[m].notna()).any(): raise ValueError(f"tarife çakışması: {y.ad}")
        fiyat[m] = f[m]; kaynak[m] = y.ad
    return pd.DataFrame({"uretim_mwh": uretim_mwh, "fiyat_tl_mwh": fiyat, "gelir_tl": uretim_mwh * fiyat, "tarife": kaynak})


def aylik(gelir_df: pd.DataFrame) -> pd.DataFrame:
    g = gelir_df.copy(); g.index = _ist(g.index)
    a = g.resample("ME").agg({"uretim_mwh": "sum", "gelir_tl": "sum"}); a["ort_fiyat_tl_mwh"] = a["gelir_tl"] / a["uretim_mwh"].replace(0, np.nan)
    return a
