"""v2.279 — Tablo 3.2 satır 3: ufukla büyüyen belirsizlik — geçmiş hatadan ufuk-bazlı σ(h) tabanı (★ onaylı, son katman).

Ensemble üyeleri açık gök haftasında hemfikirdir (yayılım ~10 kW) ve bant ufukla büyümez; oysa gerçek hata ufukla büyür.
Bu katman son N günün gündüz artıklarından (p50 − gerçek) ufuk kovası başına σ(h) çıkarır (pvquant.ext.tahmin.
ensemble_belirsizlik.ufuk_sigma: monoton büyüyen), servis bandının yarı genişliğini z·σ(h) ile ALTTAN sınırlar
(yalnız genişletir, daraltmaz; p10 ≥ 0, p90 ≤ tavan). Sıra: model/ensemble ham bant → ufuk σ → sapma → konformal.
Ayar: ufuk_sigma_katmani otomatik|kapali. Sonuç plants.params_json.ufuk_sigma (gece işi).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from pvquant.config import get_settings

KOVA_SAAT = 24          # ufuk kovası genişliği (saat)
Z10 = 1.2816            # P10/P90 için normal z
MIN_SAAT = 72
PENCERE_GUN = 60


def sigma_hesapla_df(df: pd.DataFrame, capacity_kwp: float) -> dict | None:
    """SAF. df: ts_utc, run_at, p50_kw, power_kw. Döner {kova(h): sigma_kw} monoton, n, kova_saat; yetersizse None."""
    if df is None or df.empty:
        return None
    x = df.dropna(subset=["p50_kw", "power_kw"]).copy()
    x = x[x["power_kw"] > 0.02 * capacity_kwp]
    if len(x) < MIN_SAAT:
        return None
    ts = pd.to_datetime(x["ts_utc"], utc=True); ra = pd.to_datetime(x["run_at"], utc=True)
    ufuk = ((ts - ra).dt.total_seconds() / 3600.0)
    x = x[ufuk >= 0]; ufuk = ufuk[ufuk >= 0]
    kova = (ufuk // KOVA_SAAT).astype(int)
    hata = (x["p50_kw"] - x["power_kw"]).astype(float)
    hata.index = x.index; kova.index = x.index
    from pvquant.ext.tahmin.ensemble_belirsizlik import ufuk_sigma
    s = ufuk_sigma(hata, kova, monoton=True).dropna()
    s = s[s.index.map(lambda k: int((kova == k).sum()) >= 12)]      # kova başına ≥12 saat
    if s.empty:
        return None
    return {"sigma_kw": {str(int(k)): round(float(v), 1) for k, v in s.items()}, "n": int(len(x)), "kova_saat": KOVA_SAAT,
            "hesap_zamani": datetime.now(timezone.utc).isoformat(), "pencere_gun": PENCERE_GUN}


def uygula_df(h: pd.DataFrame, ayar: dict | None, run_at: pd.Timestamp, tavan_kw: float | None) -> pd.DataFrame:
    """SAF. Yarı genişlik ≥ z·σ(kova); yalnız genişletir. Gece (p50 ≈ 0) dokunmaz."""
    if not ayar or not ayar.get("sigma_kw") or "p10_kw" not in h:
        return h
    h = h.copy()
    idx = pd.DatetimeIndex(h.index); idx = idx.tz_localize("UTC") if idx.tz is None else idx
    ra = pd.Timestamp(run_at); ra = ra.tz_localize("UTC") if ra.tz is None else ra.tz_convert("UTC")
    kova = ((idx - ra) / pd.Timedelta(hours=1) // ayar.get("kova_saat", KOVA_SAAT)).astype(int)
    sig = ayar["sigma_kw"]; anahtarlar = sorted(int(k) for k in sig)
    def s_of(k):
        if str(k) in sig:
            return float(sig[str(k)])
        return float(sig[str(max(a for a in anahtarlar if a <= k))]) if any(a <= k for a in anahtarlar) else float(sig[str(anahtarlar[0])])
    sigma = np.array([s_of(int(k)) for k in kova])
    p50 = pd.to_numeric(h["p50_kw"], errors="coerce")
    gunduz = p50 > 0
    p10 = pd.to_numeric(h["p10_kw"], errors="coerce"); p90 = pd.to_numeric(h["p90_kw"], errors="coerce")
    alt = (p50 - Z10 * sigma).clip(lower=0.0); ust = p50 + Z10 * sigma
    if tavan_kw:
        ust = ust.clip(upper=float(tavan_kw))
    yeni10 = np.where(gunduz & p10.notna(), np.minimum(p10.fillna(alt), alt), p10)
    yeni90 = np.where(gunduz & p90.notna(), np.maximum(p90.fillna(ust), ust), p90)
    h["p10_kw"] = yeni10; h["p90_kw"] = yeni90
    return h


def gece_ufuk_sigma(tenant_id, plant: dict, gun: int = PENCERE_GUN) -> dict | None:
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    from pvquant.services import plant_service
    with tenant_baglami(tenant_id) as s:
        df = pd.read_sql(text(
            "SELECT f.ts_utc, r.run_at, f.p50_kw, s.power_kw FROM forecast_values f JOIN forecast_runs r ON r.id=f.run_id "
            "JOIN scada_hourly s ON s.plant_id=f.plant_id AND s.ts_utc=f.ts_utc AND s.flag='valid' "
            "WHERE f.plant_id=:p AND f.ts_utc >= (SELECT max(ts_utc) FROM scada_hourly WHERE plant_id=:p AND flag='valid') - (:g * INTERVAL '1 day')"),
            s.connection(), params={"p": plant["id"], "g": gun}, parse_dates=["ts_utc", "run_at"])
    ayar = sigma_hesapla_df(df, float(plant["capacity_kwp"]))
    if ayar is None:
        return None
    plant_service.params_birlestir(tenant_id, plant["id"], ufuk_sigma=ayar)
    return ayar


def ayar_getir(plant: dict) -> dict | None:
    if get_settings().ufuk_sigma_katmani == "kapali":
        return None
    pj = plant.get("params_json") or {}
    if isinstance(pj, str):
        pj = json.loads(pj)
    return pj.get("ufuk_sigma")
