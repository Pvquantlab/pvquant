"""v2.281 — Tablo 3.3 satır 6: kullanılabilirlik (IEC 61724-3 kalıbı) — olay günlüğü olmadan OTOMATİK tespit.

Üretim mümkün saat: 0–24 s öncülü fizik beklentisi > %2 kapasite. Veri erişilebilirliği = geçerli ölçüm satırı / mümkün saat.
Arıza (otomatik): ölçüm satırı var, gücü < %0,5 kapasite ama beklenti > %10 kapasite → 'sıfır üretim' saati. Şebeke kesintisi /
kısıntı ayrımı olay günlüğü olmadan yapılamaz — 'kisinti' bayraklı saatler hariç tutulur, kalanı arıza sayılır; dürüstçe
"otomatik tespit" etiketiyle sunulur. Enerji tabanlı: kayıp = beklenti − ölçüm (arıza saatleri). Özet PR kartına ve alarm
kuralına (kullanilabilirlik_dustu, opt-in) beslenir.
"""
from __future__ import annotations

import pandas as pd

MIN_MUMKUN_SAAT = 40


def hesapla_df(df: pd.DataFrame, capacity_kwp: float) -> dict:
    """SAF. df: ts_utc, beklenen_kw (fizik, 0–24 s), power_kw (NaN = satır yok), flag."""
    if df is None or df.empty:
        return {"durum": "veri_yok"}
    x = df.copy()
    mumkun = x["beklenen_kw"].astype(float) > 0.02 * capacity_kwp
    x = x[mumkun]
    if len(x) < MIN_MUMKUN_SAAT:
        return {"durum": "yetersiz", "mumkun_saat": int(len(x))}
    var = x["power_kw"].notna()
    haric = x.get("flag", pd.Series("", index=x.index)).astype(str).eq("kisinti")
    ariza = var & ~haric & (x["power_kw"].astype(float) < 0.005 * capacity_kwp) & (x["beklenen_kw"].astype(float) > 0.10 * capacity_kwp)
    payda = int((var & ~haric).sum())
    A_t = 1 - int(ariza.sum()) / payda if payda else None
    kayip = (x["beklenen_kw"].astype(float) - x["power_kw"].astype(float)).clip(lower=0).where(ariza, 0.0).sum()
    E = float(x.loc[var & ~haric, "power_kw"].astype(float).sum())
    A_e = E / (E + float(kayip)) if (E + float(kayip)) > 0 else None
    return {"durum": "ok", "mumkun_saat": int(len(x)), "veri_orani": round(float(var.mean()), 3), "haric_saat": int(haric.sum()),
            "ariza_saat": int(ariza.sum()), "A_t": (round(float(A_t), 4) if A_t is not None else None),
            "A_e": (round(float(A_e), 4) if A_e is not None else None), "kayip_kwh": round(float(kayip), 1),
            "not": "arıza saatleri otomatik tespit (beklenti >%10 iken üretim ≈0); olay günlüğü yok — şebeke kesintisi ayrılamaz"}


def hesapla(tenant_id, plant: dict, gun: int = 30) -> dict:
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        df = pd.read_sql(text(
            "SELECT f.ts_utc, f.physics_kw AS beklenen_kw, s.power_kw, s.flag FROM forecast_values f JOIN forecast_runs r ON r.id=f.run_id "
            "LEFT JOIN scada_hourly s ON s.plant_id=f.plant_id AND s.ts_utc=f.ts_utc "
            "WHERE f.plant_id=:p AND f.ts_utc - r.run_at BETWEEN INTERVAL '0 hour' AND INTERVAL '24 hour' "
            "AND f.ts_utc >= (SELECT max(ts_utc) FROM scada_hourly WHERE plant_id=:p AND flag IN ('valid','kisinti')) - (:g * INTERVAL '1 day') "
            "AND f.ts_utc <= (SELECT max(ts_utc) FROM scada_hourly WHERE plant_id=:p AND flag IN ('valid','kisinti'))"),
            s.connection(), params={"p": plant["id"], "g": gun}, parse_dates=["ts_utc"])
    if not df.empty:
        df = df.sort_values("ts_utc").drop_duplicates("ts_utc", keep="last")
    out = hesapla_df(df, float(plant["capacity_kwp"]))
    out["pencere_gun"] = gun
    return out
