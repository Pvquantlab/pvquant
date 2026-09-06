"""v2.253 — Dalga 2.8b: eğitim/servis kayması denetimi (rezidüel özellikleri hangi meteodan geliyor?).

Gerçek: kalibrasyon/ML eğitimi ARŞİV meteosuyla (OpenMeteoClient.get_historical — analiz), tahmin servisi
TAHMİN meteosuyla (get_forecast) çalışır. Aynı saatlerde ikisinin dağılımı farklıysa (PSI/KS) ya da sistematik
sapma varsa (GHI nMBE), rezidüel model eğitimde görmediği bir girdiyle servis yapıyor demektir — bu, bant
sınavındaki sapmanın olası kaynağıdır. Bu modül yalnız ÖLÇER ve ADRES gösterir; düzeltme çekirdek kararıdır.
Servis örneği: get_forecast(past_days=N) — tahmin modelinin geçmiş günleri (analiz değil). 24 s bellek önbelleği.
"""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from pvquant.ext.tahmin.backtest import ks, psi

DEGISKENLER = {"ghi": "Yatay ışınım", "temp_air": "Hava sıcaklığı", "wind_speed_10m": "Rüzgar hızı"}
_ONBELLEK: dict = {}


def _hukum(p: float) -> str:
    return "KAYMA" if p > 0.25 else ("dikkat" if p > 0.10 else "uyumlu")


def _kaynak() -> dict:
    return {"egitim": "arşiv meteosu (analiz)", "servis": "tahmin meteosu (0–24 s)",
            "not": "rezidüel özellikleri (POA, hücre sıcaklığı, gök açıklığı) eğitimde arşivden, serviste tahminden türer"}


def kayma_hesapla(arsiv: pd.DataFrame, tahmin: pd.DataFrame, gunduz_esik: float = 20.0) -> dict:
    """SAF. İki çerçeve de saatlik UTC index; kolonlar ghi, temp_air, wind_speed_10m. Ortak saatlerde PSI/KS/sapma."""
    idx = arsiv.index.intersection(tahmin.index)
    if len(idx) < 48:
        return {"n_saat": int(len(idx)), "ozellikler": [], "hukum": "yetersiz", "kaynak": _kaynak()}
    a, t = arsiv.loc[idx], tahmin.loc[idx]
    out = []
    for ad, etiket in DEGISKENLER.items():
        if ad not in a or ad not in t:
            continue
        aa, tt = a[ad].astype(float), t[ad].astype(float)
        if ad == "ghi":
            m = (aa > gunduz_esik) | (tt > gunduz_esik); aa, tt = aa[m], tt[m]
        if len(aa) < 24:
            continue
        p = psi(aa, tt); d = ks(aa, tt); sapma = float((tt - aa).mean())
        ort = float(aa.mean()); sapma_pct = (sapma / ort * 100.0) if ort else np.nan
        out.append({"ad": ad, "etiket": etiket, "n": int(len(aa)), "psi": round(p, 4), "ks": round(d, 4),
                    "sapma": round(sapma, 3), "sapma_pct": (round(sapma_pct, 2) if not np.isnan(sapma_pct) else None), "hukum": _hukum(p)})
    en_kotu = max((o["psi"] for o in out), default=0.0)
    return {"n_saat": int(len(idx)), "ozellikler": out, "hukum": _hukum(en_kotu), "kaynak": _kaynak()}


def kayma_denetimi(plant: dict, gun: int = 30) -> dict:
    """Ağ: arşiv + tahmin(past_days) aynı pencerede; sonuç plant+gün önbelleğinde (24 s)."""
    from pvquant.io.meteo import OpenMeteoClient
    anahtar = (str(plant["id"]), gun, date.today().isoformat())
    if anahtar in _ONBELLEK:
        return _ONBELLEK[anahtar]
    c = OpenMeteoClient()
    bitis = date.today() - timedelta(days=2); bas = bitis - timedelta(days=gun)
    from pvquant.io.meteo import OpenMeteoError
    try:
        ars = c.get_historical(plant["lat"], plant["lon"], bas.isoformat(), bitis.isoformat()).to_dataframe()
        tah = c.get_forecast(plant["lat"], plant["lon"], days=1, past_days=min(gun + 2, 92)).to_dataframe()
    except OpenMeteoError as e:
        # v2.282: açık arşiv bu pencereyi kapsamıyorsa (kurulumdan önceki dönem / CAMS yok) 500 değil dürüst boş sonuç
        out = {"n_saat": 0, "ozellikler": [], "hukum": "—", "kaynak": _kaynak(), "gun": gun, "baslangic": bas.isoformat(), "bitis": bitis.isoformat(),
               "not": "eğitim meteosu bu pencere için henüz yok — açık arşiv kurulumdan sonra birikiyor (uydu ışınım kaydı operatör ayarıdır)"}
        print(f"[kayma] eğitim meteosu alınamadı: {e}")   # ayrıntı yalnız günlükte (ortam değişkeni adları panelde görünmez)
        _ONBELLEK[anahtar] = out
        return out
    for df in (ars, tah):
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
    out = kayma_hesapla(ars, tah); out["gun"] = gun; out["baslangic"] = bas.isoformat(); out["bitis"] = bitis.isoformat()
    _ONBELLEK[anahtar] = out
    return out
