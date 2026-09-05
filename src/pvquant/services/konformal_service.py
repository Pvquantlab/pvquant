"""v2.252 — Dalga 2.7: konformal (CQR) P10–P90 kalibrasyonu; reliability ile kapatılan döngü.

Fikir (Romano, Patterson & Candès 2019): son N günün HAM bandı ile gerçekleşen arasındaki uyumsuzluk
s = max(P10 − y, y − P90) toplanır; grup (UTC saat) başına (1−α)(1+1/n) yüzdeliği q̂. Servis edilen bant:
[P10_ham − q̂, P90_ham + q̂]. q̂ NEGATİF olabilir → bant DARALIR (canlı bulgu: PICP %91, hedef %80).
Döngü: gece bant sınavı servis edileni ölçer; q̂ hamdan öğrenilir → kendi kuyruğunu kovalamaz.
Model çekirdeğine dokunmaz: hybrid_residual'ın kantilleri okunur, düzeltme SONRADAN uygulanır (★ onaylı).
Tire ilkesi: grup başına < min_n örnek → o saat için genel q̂; toplam < min_toplam → ayar yazılmaz.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from pvquant.ext.tahmin.konformal import CQR

ALPHA = 0.2          # %80 bant (P10–P90)
MIN_TOPLAM = 24 * 7  # en az bir haftalık gündüz saati
MIN_GRUP = 20


def q_hat_hesapla_df(df: pd.DataFrame, capacity_kwp: float, alpha: float = ALPHA, min_toplam: int = MIN_TOPLAM) -> dict | None:
    """SAF. df kolonları: ts_utc, power_kw, p10 (ham), p90 (ham). Gündüz (>%2 kapasite) ve bant dolu saatler.
    Döner: {"alpha","grup","q_hat":{"0":..,"23":..,"_genel":..},"n","ort_q":..} ya da None (yetersiz veri)."""
    if df is None or df.empty:
        return None
    d = df.dropna(subset=["power_kw", "p10", "p90"]).copy()
    d["ts_utc"] = pd.to_datetime(d["ts_utc"], utc=True)
    d = d[d.power_kw > 0.02 * capacity_kwp].set_index("ts_utc").sort_index()
    if len(d) < min_toplam:
        return None
    c = CQR(alpha=alpha, grup="saat").kalibre_et(d["power_kw"].astype(float), d["p10"].astype(float), d["p90"].astype(float))
    q = {str(k): round(float(v), 3) for k, v in c.q_hat.items()}
    return {"alpha": alpha, "grup": "saat", "q_hat": q, "n": int(len(d)),
            "ort_q": round(float(np.mean([v for k, v in c.q_hat.items() if k != "_genel"])), 3)}


def uygula_df(h: pd.DataFrame, ayar: dict | None, tavan_kw: float | None) -> pd.DataFrame:
    """SAF. h: ts_utc indexli çerçeve, p10_kw/p90_kw HAM. Ham kopyaları p10_ham_kw/p90_ham_kw'ya alır;
    ayar varsa servis bandını yazar (p10 ≥ 0, p90 ≤ tavan, p10 ≤ p50 ≤ p90 korunur). Ayar yoksa ham = servis."""
    h = h.copy()
    h["p10_ham_kw"] = h["p10_kw"]; h["p90_ham_kw"] = h["p90_kw"]
    if not ayar or not ayar.get("q_hat"):
        return h
    q = ayar["q_hat"]; genel = float(q.get("_genel", 0.0))
    saat = pd.DatetimeIndex(h.index).tz_convert("UTC").hour if pd.DatetimeIndex(h.index).tz is not None else pd.DatetimeIndex(h.index).hour
    qs = np.array([float(q.get(str(int(s)), genel)) for s in saat])
    p10 = pd.to_numeric(h["p10_ham_kw"], errors="coerce"); p90 = pd.to_numeric(h["p90_ham_kw"], errors="coerce")
    p50 = pd.to_numeric(h["p50_kw"], errors="coerce")
    yeni10 = (p10 - qs).clip(lower=0.0); yeni90 = p90 + qs
    if tavan_kw:
        yeni90 = yeni90.clip(upper=float(tavan_kw))
    # sıralama korunur: p10 ≤ p50 ≤ p90; gece (ham NaN) dokunulmaz
    yeni10 = np.minimum(yeni10, p50); yeni90 = np.maximum(yeni90, p50)
    h["p10_kw"] = yeni10.where(p10.notna()); h["p90_kw"] = yeni90.where(p90.notna())
    return h


def q_hat_hesapla(tenant_id, plant: dict, gun: int = 60) -> dict | None:
    """DB: son `gun` günün HAM bandı (p10_ham_kw yoksa p10_kw — migration öncesi koşular ham demektir)
    + gerçekleşen → q̂; konformal_ayar'a yazar (UPSERT). Yetersizse ayar SİLİNMEZ, eski kalır; None döner."""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    pid = plant["id"]
    with tenant_baglami(tenant_id) as s:
        df = pd.read_sql(text(
            "SELECT f.ts_utc, s.power_kw, COALESCE(f.p10_ham_kw, f.p10_kw) AS p10, COALESCE(f.p90_ham_kw, f.p90_kw) AS p90 "
            "FROM forecast_values f JOIN forecast_runs r ON r.id=f.run_id "
            "JOIN scada_hourly s ON s.plant_id=f.plant_id AND s.ts_utc=f.ts_utc AND s.flag='valid' "
            "WHERE f.plant_id=:p AND f.ts_utc >= now()-(:g * INTERVAL '1 day') "
            "AND f.ts_utc - r.run_at BETWEEN INTERVAL '0 hour' AND INTERVAL '24 hour'"),
            s.connection(), params={"p": pid, "g": gun}, parse_dates=["ts_utc"])
    ayar = q_hat_hesapla_df(df, float(plant["capacity_kwp"]))
    if ayar is None:
        return None
    with tenant_baglami(tenant_id) as s:
        s.execute(text(
            "INSERT INTO konformal_ayar(tenant_id,plant_id,alpha,grup,q_hat_json,n,pencere_gun,hesap_zamani) "
            "VALUES(:t,:p,:a,:g,CAST(:q AS jsonb),:n,:pg,now()) "
            "ON CONFLICT (plant_id) DO UPDATE SET alpha=EXCLUDED.alpha, grup=EXCLUDED.grup, q_hat_json=EXCLUDED.q_hat_json,"
            " n=EXCLUDED.n, pencere_gun=EXCLUDED.pencere_gun, hesap_zamani=now()"),
            {"t": tenant_id, "p": pid, "a": ayar["alpha"], "g": ayar["grup"], "q": json.dumps(ayar["q_hat"]), "n": ayar["n"], "pg": gun})
    return ayar


def ayar_getir(tenant_id, plant_id) -> dict | None:
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        r = s.execute(text("SELECT alpha, grup, q_hat_json, n, pencere_gun, aktif, hesap_zamani FROM konformal_ayar WHERE plant_id=:p"), {"p": plant_id}).first()
    if r is None or not r.aktif:
        return None
    q = json.loads(r.q_hat_json) if isinstance(r.q_hat_json, str) else r.q_hat_json
    saatlik = [v for k, v in q.items() if k != "_genel"]
    return {"alpha": float(r.alpha), "grup": r.grup, "q_hat": q, "n": int(r.n), "pencere_gun": int(r.pencere_gun),
            "hesap_zamani": r.hesap_zamani.isoformat() if hasattr(r.hesap_zamani, "isoformat") else str(r.hesap_zamani),
            "ort_q": round(float(np.mean(saatlik)), 3) if saatlik else None}
