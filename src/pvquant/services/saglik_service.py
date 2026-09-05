"""v2.256 — Dalga 3.11: santral sağlığı — bozunma oranı (%/yıl) ve performans eğilimi.

POA ölçümü olmayan santralde (Konya gibi) IEC PR hesaplanamaz; onun yerine 'model-normalize verim'
kullanılır: günlük Σgerçek / Σbeklenen(fizik, son koşu 0–24 s) — hava ve mevsim beklenene gömülüdür.
Bozunma: RdTools YoY (365 gün arayla oran değişimlerinin medyanı; ≥13 ay ister; pvquant.ext.tahmin.degradasyon).
Eğilim: son 3 ay vs önceki 12 ay ve doğrusal eğim (%/yıl). POA varsa IEC PR′ trendi de verilir.
Tire ilkesi: yetersiz veri → None + neden; iddia yok.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from pvquant.ext.tahmin import degradasyon


def gunluk_indeks(df: pd.DataFrame, capacity_kwp: float, min_beklenen_kwh: float | None = None) -> pd.Series:
    """SAF. df: ts_utc, power_kw, beklenen_kw (NaN olabilir). Günlük gerçek/beklenen oranı (yalnız beklenen dolu saatler)."""
    d = df.dropna(subset=["power_kw", "beklenen_kw"]).copy()
    if d.empty:
        return pd.Series(dtype=float)
    d["ts_utc"] = pd.to_datetime(d["ts_utc"], utc=True); d = d.set_index("ts_utc")
    g = d.resample("D").agg(gercek=("power_kw", "sum"), beklenen=("beklenen_kw", "sum"), n=("power_kw", "size"))
    esik = min_beklenen_kwh if min_beklenen_kwh is not None else 0.5 * capacity_kwp   # en az yarım saatlik tam güç kadar beklenen
    g = g[(g["beklenen"] >= esik) & (g["n"] >= 6)]
    return (g["gercek"] / g["beklenen"]).clip(0.2, 1.5)


def saglik_hesapla(indeks: pd.Series, pr_aylik: pd.Series | None = None) -> dict:
    """SAF. indeks: günlük normalize verim. Döner bozunma (YoY), eğilim, kapsama."""
    s = indeks.dropna()
    out = {"gun": int(len(s)), "ay": int(s.index.to_period("M").nunique()) if len(s) else 0, "indeks_ort": round(float(s.mean()), 4) if len(s) else None,
           "bozunma_yuzde_yil": None, "bozunma_ga": None, "egim_yuzde_yil": None, "son3_vs_onceki12_pct": None, "pr_egim_yuzde_yil": None, "not": ""}
    if len(s) < 60:
        out["not"] = "en az 60 gün gerekir"; return out
    tr = degradasyon.pr_trendi(s.resample("ME").mean())
    out["egim_yuzde_yil"] = None if tr["egim_yuzde_yil"] is None or np.isnan(tr["egim_yuzde_yil"]) else round(float(tr["egim_yuzde_yil"]), 2)
    out["son3_vs_onceki12_pct"] = None if tr["son3_vs_onceki12"] is None or np.isnan(tr["son3_vs_onceki12"]) else round(float(tr["son3_vs_onceki12"]), 2)
    try:
        y = degradasyon.yoy_degradasyon(s, bootstrap=200)
        out["bozunma_yuzde_yil"] = round(y["rd_yuzde_yil"], 2); out["bozunma_ga"] = [round(v, 2) for v in y["ga_%68"]]
    except ValueError:
        out["not"] = "bozunma için ≥13 ay gerekir (şimdilik eğilim)"
    if pr_aylik is not None and pr_aylik.dropna().size >= 6:
        p = degradasyon.pr_trendi(pr_aylik)
        out["pr_egim_yuzde_yil"] = None if np.isnan(p["egim_yuzde_yil"]) else round(float(p["egim_yuzde_yil"]), 2)
    return out


def saglik(tenant_id, plant: dict, gun: int = 800) -> dict:
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        df = pd.read_sql(text(
            "SELECT s.ts_utc, s.power_kw, b.physics_kw AS beklenen_kw FROM scada_hourly s "
            "LEFT JOIN LATERAL (SELECT f.physics_kw FROM forecast_values f JOIN forecast_runs r ON r.id=f.run_id "
            "  WHERE f.plant_id=s.plant_id AND f.ts_utc=s.ts_utc AND f.ts_utc - r.run_at BETWEEN INTERVAL '0 hour' AND INTERVAL '24 hour' "
            "  ORDER BY r.run_at DESC LIMIT 1) b ON true "
            "WHERE s.plant_id=:p AND s.flag='valid' AND NOT s.kirpma AND s.ts_utc >= now() - (:g * INTERVAL '1 day') ORDER BY s.ts_utc"),
            s.connection(), params={"p": plant["id"], "g": gun}, parse_dates=["ts_utc"])
    idx = gunluk_indeks(df, float(plant["capacity_kwp"]))
    out = saglik_hesapla(idx)
    out["pencere_gun"] = gun; out["kaynak"] = "model-normalize verim (gerçek / beklenen fizik)"
    return out
