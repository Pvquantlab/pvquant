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


# ---------------- v2.297: ufuk kovası sınavı ----------------
def ufuk_kova_sinavi_df(df: pd.DataFrame, capacity_kwp: float, egitim_gun: int = 30, test_gun: int = 7,
                        adim_gun: int = 7, alpha: float = 0.2) -> dict:
    """SAF. df: ts_utc, power_kw, p50, p10, p90, ufuk_saat (ham bant, 0–168 s).
    Kayan başlangıçla üç bandı kıyaslar: HAM · TEK q̂ (yalnız 0–24'ten öğrenilen eski düzen, her ufka aynı)
    · KOVA q̂ (v2.296). Cevap: kova boyutu uzak ufkun kapsamasını hedefe (0,80) yaklaştırıyor mu?"""
    from pvquant.services.konformal_service import KOVALAR, q_dizisi
    bos = {"pencere": 0, "kovalar": [], "hukum": "yetersiz"}
    if df is None or df.empty or "ufuk_saat" not in df.columns:
        return bos
    d = df.dropna(subset=["power_kw", "p10", "p90"]).copy()
    d["ts_utc"] = pd.to_datetime(d["ts_utc"], utc=True); d = d.sort_values("ts_utc")
    d = d[d.power_kw > 0.02 * capacity_kwp]
    if d.empty:
        return bos
    gun0 = d.ts_utc.min().normalize(); son = d.ts_utc.max()
    top: dict = {ad: {"n": 0, "ham": [], "tek": [], "kova": [], "bant_kova": []} for ad, _, _ in KOVALAR}
    pencere = 0
    t0 = gun0 + pd.Timedelta(days=egitim_gun)
    while t0 + pd.Timedelta(days=test_gun) <= son + pd.Timedelta(hours=1):
        eg = d[d.ts_utc < t0]; te = d[(d.ts_utc >= t0) & (d.ts_utc < t0 + pd.Timedelta(days=test_gun))]
        a_kova = q_hat_hesapla_df(eg, capacity_kwp, alpha=alpha)
        a_tek = q_hat_hesapla_df(eg[eg.ufuk_saat < 24.0].drop(columns=["ufuk_saat"]), capacity_kwp, alpha=alpha)
        t0 += pd.Timedelta(days=adim_gun)
        if a_kova is None or a_tek is None or a_kova.get("grup") != "saat_ufuk" or len(te) < 24:
            continue
        pencere += 1
        saat = pd.DatetimeIndex(te.ts_utc).hour
        q_k = q_dizisi(a_kova, saat, te.ufuk_saat.values)
        q_t = q_dizisi(a_tek, saat)
        for ad, u0, u1 in KOVALAR:
            m = (te.ufuk_saat.values >= u0) & (te.ufuk_saat.values < u1)
            if m.sum() < 12:
                continue
            y = te.power_kw.values[m]; lo = te.p10.values[m]; hi = te.p90.values[m]
            icinde = lambda l, h: float(((y >= l) & (y <= h)).mean())
            lo_t = np.clip(lo - q_t[m], 0, None); hi_t = np.clip(hi + q_t[m], None, capacity_kwp)
            lo_k = np.clip(lo - q_k[m], 0, None); hi_k = np.clip(hi + q_k[m], None, capacity_kwp)
            top[ad]["n"] += int(m.sum())
            top[ad]["ham"].append(icinde(lo, hi)); top[ad]["tek"].append(icinde(lo_t, hi_t))
            top[ad]["kova"].append(icinde(lo_k, hi_k))
            top[ad]["bant_kova"].append(float((hi_k - lo_k).mean() / capacity_kwp))
    kovalar = []
    for ad, _, _ in KOVALAR:
        v = top[ad]
        if not v["ham"]:
            continue
        kovalar.append({"kova": ad, "n": v["n"],
                        "picp_ham": round(float(np.mean(v["ham"])), 3),
                        "picp_tek": round(float(np.mean(v["tek"])), 3),
                        "picp_kova": round(float(np.mean(v["kova"])), 3),
                        "bant_kova_n": round(float(np.mean(v["bant_kova"])), 3)})
    if not kovalar:
        return bos
    uzak = [k for k in kovalar if k["kova"] != "0-24"]
    if uzak:
        yaklasan = sum(1 for k in uzak if abs(k["picp_kova"] - HEDEF) <= abs(k["picp_tek"] - HEDEF))
        hukum = ("kova boyutu uzak ufku hedefe yaklaştırıyor" if yaklasan == len(uzak)
                 else "kova boyutu uzak ufukta karışık" if yaklasan else "kova boyutu uzak ufku yaklaştırmıyor")
    else:
        hukum = "uzak ufuk örneği yok"
    return {"pencere": pencere, "kovalar": kovalar, "hedef": HEDEF, "hukum": hukum}


def ufuk_kova_sinavi(tenant_id, plant: dict, gun: int = 90) -> dict:
    from pvquant.services.konformal_service import gecmis_band_df
    df = gecmis_band_df(tenant_id, plant["id"], gun, ufuk_ust_saat=168)
    return ufuk_kova_sinavi_df(df, float(plant["capacity_kwp"]))
