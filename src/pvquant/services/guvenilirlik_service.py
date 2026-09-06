"""v2.271 — Dalga 1 tamamlayıcısı: olasılıksal doğrulama paneli — güvenilirlik diyagramı, PIT, keskinlik, aralık skoru.

Rapor 3.3: bant sınavı (PICP/pinball/CRPS, v2.248) vardı; eksik olan KANTİL GÜVENİLİRLİĞİ (her τ için gözlenen
kapsama vs nominal; ideal köşegen), PIT histogramı (düz = kalibre) ve keskinlik/aralık skorunun ham ↔ kalibre kıyasıydı.
Kaynak: son N günün 0–24 s ufuklu koşuları (gecmis_band_df kalıbı) — ham bant (p10_ham/p90_ham) ve servis edilen
kalibre bant (p10/p90) yan yana. Gündüz saatleri (ölçüm ya da tahmin > %1 kapasite). pvquant.ext.tahmin.dogrulama.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from pvquant.ext.tahmin import dogrulama as d

MIN_SAAT = 72
TAULAR = ("p10", "p50", "p90")


def hesapla_df(df: pd.DataFrame, capacity_kwp: float) -> dict:
    """SAF. df kolonları: ts_utc, power_kw, p50, p10_ham, p90_ham, p10_kal, p90_kal (kal yoksa ham)."""
    if df is None or df.empty:
        return {"durum": "veri_yok", "n_saat": 0}
    x = df.dropna(subset=["power_kw", "p50", "p10_ham", "p90_ham"]).copy()
    x = x.set_index(pd.DatetimeIndex(x["ts_utc"])) if "ts_utc" in x else x
    for k in ("p10_kal", "p90_kal"):
        if k not in x or x[k].isna().all():
            x[k] = x[k.replace("kal", "ham")]
    m = d.gunduz_maskesi(x["power_kw"], x["p50"], capacity_kwp)
    x = x[m]
    if len(x) < MIN_SAAT:
        return {"durum": "yetersiz", "n_saat": int(len(x)), "min_saat": MIN_SAAT}
    y = x["power_kw"]
    ham = pd.DataFrame({"p10": x["p10_ham"], "p50": x["p50"], "p90": x["p90_ham"]})
    kal = pd.DataFrame({"p10": x["p10_kal"], "p50": x["p50"], "p90": x["p90_kal"]})
    def rel(q):
        r = d.reliability(y, q)
        return [{"tau": float(t), "gozlenen": round(float(g), 3), "sapma": round(float(s), 3), "n": int(n)}
                for t, g, s, n in zip(r["tau"], r["gozlenen"], r["sapma"], r["n"])]
    pit = d.pit_histogram(y, kal, kutu=10)
    return {
        "durum": "ok", "n_saat": int(len(x)), "gun_sayisi": int(pd.Series(x.index.date).nunique()),
        "guvenilirlik": {"ham": rel(ham), "kalibre": rel(kal)},
        "pit": [{"kutu": str(i), "oran": round(float(v), 3)} for i, v in pit.items()],
        "pit_max_sapma": round(float((pit - 0.1).abs().max()), 3),
        "keskinlik": {"ham": round(d.bant_genisligi(ham["p10"], ham["p90"], capacity_kwp), 3),
                      "kalibre": round(d.bant_genisligi(kal["p10"], kal["p90"], capacity_kwp), 3)},
        "aralik_skoru_n": {"ham": round(d.aralik_skoru(y, ham["p10"], ham["p90"], 0.2) / capacity_kwp, 3),
                           "kalibre": round(d.aralik_skoru(y, kal["p10"], kal["p90"], 0.2) / capacity_kwp, 3)},
        "picp80": {"ham": round(d.picp(y, ham["p10"], ham["p90"]), 3), "kalibre": round(d.picp(y, kal["p10"], kal["p90"]), 3)},
    }


def hesapla(tenant_id, plant: dict, gun: int = 60) -> dict:
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        df = pd.read_sql(text(
            "SELECT f.ts_utc, s.power_kw, f.p50_kw AS p50, COALESCE(f.p10_ham_kw, f.p10_kw) AS p10_ham, "
            "COALESCE(f.p90_ham_kw, f.p90_kw) AS p90_ham, f.p10_kw AS p10_kal, f.p90_kw AS p90_kal "
            "FROM forecast_values f JOIN forecast_runs r ON r.id=f.run_id "
            "JOIN scada_hourly s ON s.plant_id=f.plant_id AND s.ts_utc=f.ts_utc AND s.flag='valid' "
            "WHERE f.plant_id=:p AND f.ts_utc >= (SELECT max(ts_utc) FROM scada_hourly WHERE plant_id=:p AND flag='valid') - (:g * INTERVAL '1 day') "
            "AND f.ts_utc - r.run_at BETWEEN INTERVAL '0 hour' AND INTERVAL '24 hour' ORDER BY f.ts_utc"),
            s.connection(), params={"p": plant["id"], "g": gun}, parse_dates=["ts_utc"])
    out = hesapla_df(df, float(plant["capacity_kwp"]))
    out["pencere_gun"] = gun
    return out
