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
# v2.296: ufuk kovaları — beceri karnesiyle aynı dil (0–24 / 24–72 / 72–168).
# Uzak ufkun artığı yakın ufuktan büyüktür; tek q̂ 5. günün bandına 1. günün düzeltmesini giydiriyordu.
KOVALAR = (("0-24", 0.0, 24.0), ("24-72", 24.0, 72.0), ("72-168", 72.0, 168.0))


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

    def _saatlik(alt: pd.DataFrame) -> dict:
        c = CQR(alpha=alpha, grup="saat").kalibre_et(alt["power_kw"].astype(float), alt["p10"].astype(float), alt["p90"].astype(float))
        return {str(k): round(float(v), 3) for k, v in c.q_hat.items()}

    if "ufuk_saat" not in d.columns:                       # eski çağrı biçimi (geriye dönük sınav) — davranış AYNI
        q = _saatlik(d)
        return {"alpha": alpha, "grup": "saat", "q_hat": q, "n": int(len(d)),
                "ort_q": round(float(np.mean([v for k, v in q.items() if k != "_genel"])), 3)}

    # v2.296: kova başına saatlik q̂; cılız kova YAZILMAZ (uygulama yakın kovaya düşer — tire ilkesi)
    q_kova: dict = {}; kova_n: dict = {}
    for ad, u0, u1 in KOVALAR:
        alt = d[(d["ufuk_saat"] >= u0) & (d["ufuk_saat"] < u1)]
        kova_n[ad] = int(len(alt))
        if len(alt) >= min_toplam:
            q_kova[ad] = _saatlik(alt)
    if not q_kova:
        return None
    s_hepsi = pd.concat([d["p10"] - d["power_kw"], d["power_kw"] - d["p90"]], axis=1).max(axis=1)
    n = len(s_hepsi)
    q_kova["_genel"] = round(float(np.quantile(s_hepsi.values, min(1.0, np.ceil((n + 1) * (1 - alpha)) / n))), 3)
    yakin = q_kova.get("0-24") or next(q_kova[a] for a, _, _ in KOVALAR if a in q_kova)
    return {"alpha": alpha, "grup": "saat_ufuk", "q_hat": q_kova, "n": int(len(d)), "kova_n": kova_n,
            "ort_q": round(float(np.mean([v for k, v in yakin.items() if k != "_genel"])), 3)}


def uygula_df(h: pd.DataFrame, ayar: dict | None, tavan_kw: float | None, run_at: pd.Timestamp | None = None) -> pd.DataFrame:
    """SAF. h: ts_utc indexli çerçeve, p10_kw/p90_kw HAM. Ham kopyaları p10_ham_kw/p90_ham_kw'ya alır;
    ayar varsa servis bandını yazar (p10 ≥ 0, p90 ≤ tavan, p10 ≤ p50 ≤ p90 korunur). Ayar yoksa ham = servis.
    v2.296: grup 'saat_ufuk' ise q̂ (ufuk kovası × saat) seçilir — run_at verilmezse ilk damga koşu anı sayılır;
    kovası öğrenilmemiş ufuk en yakın öğrenilmiş kovaya düşer (uydurma q̂ yok). Eski 'saat' ayarı aynen çalışır."""
    h = h.copy()
    h["p10_ham_kw"] = h["p10_kw"]; h["p90_ham_kw"] = h["p90_kw"]
    if not ayar or not ayar.get("q_hat"):
        return h
    q = ayar["q_hat"]; genel = float(q.get("_genel", 0.0))
    ix = pd.DatetimeIndex(h.index)
    saat = ix.tz_convert("UTC").hour if ix.tz is not None else ix.hour
    if ayar.get("grup") == "saat_ufuk":
        t0 = run_at if run_at is not None else ix[0]
        ufuk = (ix - t0).total_seconds() / 3600.0
        sirali = [ad for ad, _, _ in KOVALAR if ad in q]
        def _kova_adi(u: float) -> str:
            for ad, u0, u1 in KOVALAR:
                if u0 <= u < u1 and ad in q:
                    return ad
            # öğrenilmemiş/aralık dışı ufuk → en yakın öğrenilmiş kova (uzun ufukta sonuncusu)
            return sirali[-1] if u >= 24 and sirali else (sirali[0] if sirali else "_genel")
        qs = np.array([float(q.get(_kova_adi(float(u)), {}).get(str(int(s_)), genel)) if _kova_adi(float(u)) != "_genel" else genel
                       for u, s_ in zip(ufuk, saat)])
    else:
        qs = np.array([float(q.get(str(int(s_)), genel)) for s_ in saat])
    p10 = pd.to_numeric(h["p10_ham_kw"], errors="coerce"); p90 = pd.to_numeric(h["p90_ham_kw"], errors="coerce")
    p50 = pd.to_numeric(h["p50_kw"], errors="coerce")
    yeni10 = (p10 - qs).clip(lower=0.0); yeni90 = p90 + qs
    if tavan_kw:
        yeni90 = yeni90.clip(upper=float(tavan_kw))
    # sıralama korunur: p10 ≤ p50 ≤ p90; gece (ham NaN) dokunulmaz
    yeni10 = np.minimum(yeni10, p50); yeni90 = np.maximum(yeni90, p50)
    h["p10_kw"] = yeni10.where(p10.notna()); h["p90_kw"] = yeni90.where(p90.notna())
    return h


def gecmis_band_df(tenant_id, plant_id, gun: int = 60, ufuk_ust_saat: int = 24) -> pd.DataFrame:
    """DB: son `gun` günün HAM bandı (p10_ham_kw yoksa p10_kw — migration öncesi koşular ham demektir)
    + p50 + gerçekleşen + ufuk_saat. Varsayılan pencere 0–24 s (geriye dönük sınav v2.253 aynı kalır);
    v2.296 q̂ öğrenimi ufuk_ust_saat=168 ile uzak ufuk artıklarını da okur."""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        return pd.read_sql(text(
            "SELECT f.ts_utc, s.power_kw, f.p50_kw AS p50, COALESCE(f.p10_ham_kw, f.p10_kw) AS p10, "
            "COALESCE(f.p90_ham_kw, f.p90_kw) AS p90, "
            "EXTRACT(EPOCH FROM (f.ts_utc - r.run_at)) / 3600.0 AS ufuk_saat "
            "FROM forecast_values f JOIN forecast_runs r ON r.id=f.run_id "
            "JOIN scada_hourly s ON s.plant_id=f.plant_id AND s.ts_utc=f.ts_utc AND s.flag='valid' "
            "WHERE f.plant_id=:p AND f.ts_utc >= now()-(:g * INTERVAL '1 day') "
            "AND f.ts_utc - r.run_at BETWEEN INTERVAL '0 hour' AND (:u * INTERVAL '1 hour') ORDER BY f.ts_utc"),
            s.connection(), params={"p": plant_id, "g": gun, "u": ufuk_ust_saat}, parse_dates=["ts_utc"])


def q_hat_hesapla(tenant_id, plant: dict, gun: int = 60) -> dict | None:
    """DB: son `gun` günün HAM bandı + gerçekleşen → q̂; konformal_ayar'a yazar (UPSERT).
    Yetersizse ayar SİLİNMEZ, eski kalır; None döner."""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    pid = plant["id"]
    df = gecmis_band_df(tenant_id, pid, gun, ufuk_ust_saat=168)   # v2.296: uzak ufuk artıkları da
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
    if r.grup == "saat_ufuk":   # v2.296: ort_q yakın kovadan (servis edilen ilk gün); kova ortalamaları ayrıca
        kovalar = {k: round(float(np.mean([v for a, v in q[k].items() if a != "_genel"])), 3)
                   for k, _, _ in KOVALAR if k in q and isinstance(q[k], dict)}
        yakin = next(iter(kovalar.values()), None)
        return {"alpha": float(r.alpha), "grup": r.grup, "q_hat": q, "n": int(r.n), "pencere_gun": int(r.pencere_gun),
                "hesap_zamani": r.hesap_zamani.isoformat() if hasattr(r.hesap_zamani, "isoformat") else str(r.hesap_zamani),
                "ort_q": yakin, "kova_ort_q": kovalar}
    saatlik = [v for k, v in q.items() if k != "_genel"]
    return {"alpha": float(r.alpha), "grup": r.grup, "q_hat": q, "n": int(r.n), "pencere_gun": int(r.pencere_gun),
            "hesap_zamani": r.hesap_zamani.isoformat() if hasattr(r.hesap_zamani, "isoformat") else str(r.hesap_zamani),
            "ort_q": round(float(np.mean(saatlik)), 3) if saatlik else None}
