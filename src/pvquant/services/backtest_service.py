"""v2.253 — Dalga 2.8a: konformal katmanın rolling-origin (kayan başlangıç) geriye dönük sınavı.

Her başlangıç t0 için: q̂ yalnız t0'dan ÖNCEKİ günlerden öğrenilir, sonraki test_gun güne uygulanır;
ham ve kalibre bandın PICP'si ve normalize genişliği raporlanır. Sızıntı yok (test günleri öğrenmeye girmez).
Cevapladığı soru: 'gece öğrenilen düzeltme ertesi haftaya taşınıyor mu?' — kalibre PICP hedef 0,80'e ham'dan
daha yakınsa katman işe yarıyor demektir. Model çekirdeğine dokunmaz.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from pvquant.services.konformal_service import q_hat_hesapla_df, uygula_df

HEDEF = 0.80


def _picp(y, lo, hi):
    ok = y.notna() & lo.notna() & hi.notna()
    return float(((y >= lo) & (y <= hi))[ok].mean()) if ok.any() else np.nan


def konformal_backtest_df(df: pd.DataFrame, capacity_kwp: float, egitim_gun: int = 21, test_gun: int = 7, adim_gun: int = 7,
                          alpha: float = 0.2) -> pd.DataFrame:
    """SAF. df: ts_utc, power_kw, p50, p10, p90 (ham). Satır/başlangıç: n_test, picp_ham, picp_kal, bant_ham_n, bant_kal_n, q_ort."""
    bos = pd.DataFrame(columns=["baslangic", "n_test", "picp_ham", "picp_kal", "bant_ham_n", "bant_kal_n", "q_ort"])
    if df is None or df.empty:
        return bos
    d = df.dropna(subset=["power_kw", "p10", "p90"]).copy()
    d["ts_utc"] = pd.to_datetime(d["ts_utc"], utc=True); d = d.sort_values("ts_utc")
    d = d[d.power_kw > 0.02 * capacity_kwp]
    if d.empty:
        return bos
    gun0 = d.ts_utc.min().normalize(); son = d.ts_utc.max()
    satir = []; t0 = gun0 + pd.Timedelta(days=egitim_gun)
    while t0 + pd.Timedelta(days=test_gun) <= son + pd.Timedelta(hours=1):
        eg = d[d.ts_utc < t0]; te = d[(d.ts_utc >= t0) & (d.ts_utc < t0 + pd.Timedelta(days=test_gun))]
        ayar = q_hat_hesapla_df(eg, capacity_kwp, alpha=alpha)
        if ayar is not None and len(te) >= 12:
            h = pd.DataFrame({"p50_kw": te.p50.values if "p50" in te else ((te.p10 + te.p90) / 2).values,
                              "p10_kw": te.p10.values, "p90_kw": te.p90.values}, index=pd.DatetimeIndex(te.ts_utc))
            y = uygula_df(h, ayar, tavan_kw=capacity_kwp)
            ger = pd.Series(te.power_kw.values, index=h.index)
            satir.append({"baslangic": t0.date().isoformat(), "n_test": int(len(te)),
                          "picp_ham": _picp(ger, h.p10_kw, h.p90_kw), "picp_kal": _picp(ger, y.p10_kw, y.p90_kw),
                          "bant_ham_n": float((h.p90_kw - h.p10_kw).mean() / capacity_kwp),
                          "bant_kal_n": float((y.p90_kw - y.p10_kw).mean() / capacity_kwp), "q_ort": ayar["ort_q"]})
        t0 += pd.Timedelta(days=adim_gun)
    return pd.DataFrame(satir) if satir else bos


def ozet(bt: pd.DataFrame) -> dict:
    if bt.empty:
        return {"pencere": 0, "picp_ham_ort": None, "picp_kal_ort": None, "hedef": HEDEF, "hukum": "yetersiz"}
    ham, kal = float(bt.picp_ham.mean()), float(bt.picp_kal.mean())
    yakin = abs(kal - HEDEF) < abs(ham - HEDEF)
    return {"pencere": int(len(bt)), "picp_ham_ort": round(ham, 3), "picp_kal_ort": round(kal, 3), "hedef": HEDEF,
            "hukum": "kalibrasyon hedefe yaklaştırıyor" if yakin else "kalibrasyon hedefe yaklaştırmıyor"}


def konformal_backtest(tenant_id, plant: dict, gun: int = 90) -> dict:
    from pvquant.services.konformal_service import gecmis_band_df
    df = gecmis_band_df(tenant_id, plant["id"], gun)
    bt = konformal_backtest_df(df, float(plant["capacity_kwp"]))
    return {**ozet(bt), "satirlar": [{k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()} for r in bt.to_dict("records")]}
