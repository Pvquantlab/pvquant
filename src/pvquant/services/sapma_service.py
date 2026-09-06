"""v2.274 — Dalga 2 (★ onaylı): trend/sapma düzeltme katmanı (OCF trend_adjuster kalıbı) — çekirdeğe dokunmayan SON katman.

Son 7 günün 0–24 s ufuklu P50'si ile gerçekleşen arasındaki saat-bazlı (yerel saat) oran ileri taşınır:
  oran_s = median(gerçek / P50) (gündüz, P50 > %1 kapasite), 0,8–1,2 arası kelepçe; tüm kantiller aynı oranla çarpılır.
Devreye girme şartları (hepsi): SCADA tazeliği ≤ 3 gün · en az 5 gün · en az 40 gündüz saati · genel oran 1'den en az %3 uzak.
Rezidüel model (Mod C) sapmayı zaten öğrenir; bu katman yalnız KALİBRASYONDAN SONRA oluşan kaymayı (kirlenme, arıza,
sensör) yakalar — küçük sapmada uyumaz, çift sayım yapmaz. Ayar: sapma_katmani 'otomatik' | 'kapali'.
Uygulama sırası: model/ensemble ham bant → SAPMA → konformal (konformal q̂ bu düzeltilmiş banttan öğrenir).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from pvquant.config import get_settings

PENCERE_GUN = 7
TAZELIK_GUN = 3
MIN_GUN = 5
MIN_SAAT = 40
ESIK = 0.03
KELEPCE = (0.8, 1.2)


def oranlar_hesapla(df: pd.DataFrame, capacity_kwp: float, tz: str) -> dict:
    """SAF. df: ts_utc, power_kw, p50 (0–24 s öncülü). Döner {aktif, neden, oran_genel, oran_saat{0..23}, n_saat, n_gun}."""
    if df is None or df.empty:
        return {"aktif": False, "neden": "veri yok", "n_saat": 0, "n_gun": 0}
    x = df.dropna(subset=["power_kw", "p50"]).copy()
    x = x[x["p50"] > 0.01 * capacity_kwp]
    if x.empty:
        return {"aktif": False, "neden": "gündüz saati yok", "n_saat": 0, "n_gun": 0}
    ts = pd.DatetimeIndex(x["ts_utc"])
    ts = ts.tz_localize("UTC") if ts.tz is None else ts
    yerel = ts.tz_convert(tz)
    x["oran"] = (x["power_kw"] / x["p50"]).clip(0.0, 3.0)
    x["saat"] = yerel.hour; x["gun"] = yerel.date
    n_gun = int(pd.Series(x["gun"]).nunique()); n_saat = int(len(x))
    genel = float(x["oran"].median())
    out = {"n_saat": n_saat, "n_gun": n_gun, "oran_genel": round(genel, 3)}
    if n_gun < MIN_GUN or n_saat < MIN_SAAT:
        return {**out, "aktif": False, "neden": f"yetersiz veri ({n_gun} gün / {n_saat} saat)"}
    if abs(genel - 1.0) < ESIK:
        return {**out, "aktif": False, "neden": f"sapma küçük (%{100 * (genel - 1):+.1f}); model zaten uyumlu"}
    saatlik = x.groupby("saat")["oran"].median().clip(*KELEPCE)
    oran_saat = {int(h): round(float(saatlik.get(h, np.clip(genel, *KELEPCE))), 3) for h in range(24)}
    return {**out, "aktif": True, "neden": None, "oran_saat": oran_saat, "kelepce": KELEPCE}


def uygula_df(h: pd.DataFrame, ayar: dict | None, tz: str, kolonlar=("p50_kw", "p10_kw", "p25_kw", "p75_kw", "p90_kw")) -> pd.DataFrame:
    """SAF. Aktif ayar varsa saat-bazlı oranla çarpar; yoksa değişmez döner."""
    if not ayar or not ayar.get("aktif"):
        return h
    idx = pd.DatetimeIndex(h.index)
    idx = idx.tz_localize("UTC") if idx.tz is None else idx
    saat = idx.tz_convert(tz).hour
    oran = np.array([ayar["oran_saat"].get(int(s), ayar["oran_saat"].get(str(int(s)), 1.0)) for s in saat], dtype=float)
    h = h.copy()
    for k in kolonlar:
        if k in h and h[k].notna().any():
            h[k] = h[k].astype(float) * oran
    return h


def ayar_getir(tenant_id, plant: dict) -> dict:
    """DB: son 7 gün (son ölçüme bağlı) P50 vs gerçekleşen; tazelik şartı."""
    if get_settings().sapma_katmani == "kapali":
        return {"aktif": False, "neden": "katman kapalı (ayar)"}
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        son = s.execute(text("SELECT max(ts_utc) FROM scada_hourly WHERE plant_id=:p AND flag='valid'"), {"p": plant["id"]}).scalar()
        if son is None:
            return {"aktif": False, "neden": "ölçüm yok"}
        yas = (pd.Timestamp.now(tz="UTC") - pd.Timestamp(son).tz_convert("UTC")).days
        if yas > TAZELIK_GUN:
            return {"aktif": False, "neden": f"son ölçüm {yas} gün önce (>{TAZELIK_GUN})"}
        df = pd.read_sql(text(
            "SELECT f.ts_utc, s.power_kw, f.p50_kw AS p50 FROM forecast_values f JOIN forecast_runs r ON r.id=f.run_id "
            "JOIN scada_hourly s ON s.plant_id=f.plant_id AND s.ts_utc=f.ts_utc AND s.flag='valid' "
            "WHERE f.plant_id=:p AND f.ts_utc >= :son - (:g * INTERVAL '1 day') "
            "AND f.ts_utc - r.run_at BETWEEN INTERVAL '0 hour' AND INTERVAL '24 hour' ORDER BY f.ts_utc"),
            s.connection(), params={"p": plant["id"], "son": son, "g": PENCERE_GUN}, parse_dates=["ts_utc"])
    out = oranlar_hesapla(df, float(plant["capacity_kwp"]), plant.get("tz") or "UTC")
    out["son_olcum"] = son.isoformat()
    return out
