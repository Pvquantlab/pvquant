"""v2.254 — Dalga 3.9: kırpma (clipping) ve şebeke kısıntısı (curtailment) maskesi + 'kısıtlama olmasaydı' senaryosu.

Kaynak yöntem: pvquant.ext.tahmin.kisitlama (pvanalytics kalıbı): kırpma = AC tavanına yapışık plato;
kısıntı = beklenenin çok altında ve DÜZ giden, sıfır olmayan segment (bulut düşüşü düz değildir).
Beklenen = aynı saat için son koşunun physics_kw'si (0–24 s ufuk) — kalibre fizik, hava dâhil.
Etkiler: kırpma → scada_hourly.kirpma=true (ölçüm 'valid' kalır: karne sayar; kalibrasyon dışlar).
kısıntı → flag='kisinti' (silinmez; kalibrasyon ve karne otomatik dışlar; bir sonraki koşu yeniden
değerlendirir, gerekirse 'valid'e döner). Kayıp = Σ(beklenen − gerçek) kısıntı saatlerinde.
Tire ilkesi: beklenen yoksa kısıntı ARANMAZ (uydurma referans yok); kırpma tavan bilinmiyorsa aranmaz.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from pvquant.ext.tahmin import kisitlama


def bayrakla_df(df: pd.DataFrame, tavan_kw: float | None, capacity_kwp: float) -> pd.DataFrame:
    """SAF. df: ts_utc, power_kw, beklenen_kw (NaN olabilir). Döner df + kirpma, kisinti (bool), kayip_kwh."""
    d = df.copy()
    d["ts_utc"] = pd.to_datetime(d["ts_utc"], utc=True)
    d = d.sort_values("ts_utc").set_index("ts_utc")
    d["kirpma"] = False; d["kisinti"] = False; d["kayip_kwh"] = 0.0
    if d.empty or "power_kw" not in d:
        return d.reset_index()
    guc = d["power_kw"].astype(float)
    if tavan_kw and tavan_kw > 0:
        d["kirpma"] = kisitlama.clipping_maskesi(guc, tavan_kw=float(tavan_kw)).values
    if "beklenen_kw" in d and d["beklenen_kw"].notna().any():
        m = d["beklenen_kw"].notna()
        cur = kisitlama.curtailment_maskesi(guc[m], d.loc[m, "beklenen_kw"].astype(float), kapasite=float(capacity_kwp))
        d.loc[m, "kisinti"] = cur.reindex(d.index[m]).fillna(False).values
        d.loc[d["kisinti"], "kayip_kwh"] = (d.loc[d["kisinti"], "beklenen_kw"] - guc[d["kisinti"]]).clip(lower=0.0)
    # kırpma ile kısıntı aynı saatte olamaz (tavanda plato kısıntı değildir)
    d.loc[d["kirpma"], "kisinti"] = False; d.loc[d["kirpma"], "kayip_kwh"] = 0.0
    return d.reset_index()


def _oku(tenant_id, plant_id, gun: int) -> pd.DataFrame:
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        return pd.read_sql(text(
            "SELECT s.ts_utc, s.power_kw, s.flag, s.kirpma, b.physics_kw AS beklenen_kw FROM scada_hourly s "
            "LEFT JOIN LATERAL (SELECT f.physics_kw FROM forecast_values f JOIN forecast_runs r ON r.id=f.run_id "
            "  WHERE f.plant_id=s.plant_id AND f.ts_utc=s.ts_utc AND f.ts_utc - r.run_at BETWEEN INTERVAL '0 hour' AND INTERVAL '24 hour' "
            "  ORDER BY r.run_at DESC LIMIT 1) b ON true "
            "WHERE s.plant_id=:p AND s.flag IN ('valid','kisinti') AND s.ts_utc >= now() - (:g * INTERVAL '1 day') ORDER BY s.ts_utc"),
            s.connection(), params={"p": plant_id, "g": gun}, parse_dates=["ts_utc"])


def gece_hijyen(tenant_id, plant: dict, gun: int = 10) -> dict:
    """Son `gun` günü yeniden değerlendirir; kirpma ve flag'i yazar. Döner sayım."""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    df = _oku(tenant_id, plant["id"], gun)
    if df.empty:
        return {"saat": 0, "kirpma": 0, "kisinti": 0, "geri_alinan": 0}
    b = bayrakla_df(df[["ts_utc", "power_kw", "beklenen_kw"]], plant.get("ac_limit_kw"), float(plant["capacity_kwp"]))
    b = b.merge(df[["ts_utc", "flag", "kirpma"]].rename(columns={"kirpma": "kirpma_eski"}), on="ts_utc", how="left")
    yeni_flag = np.where(b["kisinti"], "kisinti", "valid")
    geri = int(((b["flag"] == "kisinti") & ~b["kisinti"]).sum())
    satirlar = [{"p": plant["id"], "ts": r.ts_utc.to_pydatetime(), "k": bool(r.kirpma), "f": f}
                for r, f in zip(b.itertuples(), yeni_flag) if bool(r.kirpma) != bool(r.kirpma_eski) or f != r.flag]
    if satirlar:
        with tenant_baglami(tenant_id) as s:
            s.execute(text("UPDATE scada_hourly SET kirpma=:k, flag=:f WHERE plant_id=:p AND ts_utc=:ts"), satirlar)
    return {"saat": int(len(b)), "kirpma": int(b["kirpma"].sum()), "kisinti": int(b["kisinti"].sum()), "geri_alinan": geri, "guncellenen": len(satirlar)}


def ozet(tenant_id, plant_id, gun: int = 30) -> dict:
    """Kısıtsız senaryo özeti: kırpma/kısıntı saat ve gün sayıları, kısıntı kaybı (kWh), beklenen kapsaması."""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        r = s.execute(text(
            "SELECT count(*) AS saat, count(*) FILTER (WHERE s.kirpma) AS kirpma, count(*) FILTER (WHERE s.flag='kisinti') AS kisinti, "
            "count(DISTINCT date(s.ts_utc)) FILTER (WHERE s.flag='kisinti') AS kisinti_gun, "
            "count(DISTINCT date(s.ts_utc)) FILTER (WHERE s.kirpma) AS kirpma_gun, "
            "COALESCE(sum(GREATEST(b.physics_kw - s.power_kw, 0)) FILTER (WHERE s.flag='kisinti'), 0) AS kayip_kwh, "
            "count(b.physics_kw) AS beklenen_saat "
            "FROM scada_hourly s LEFT JOIN LATERAL (SELECT f.physics_kw FROM forecast_values f JOIN forecast_runs r ON r.id=f.run_id "
            "  WHERE f.plant_id=s.plant_id AND f.ts_utc=s.ts_utc AND f.ts_utc - r.run_at BETWEEN INTERVAL '0 hour' AND INTERVAL '24 hour' "
            "  ORDER BY r.run_at DESC LIMIT 1) b ON true "
            "WHERE s.plant_id=:p AND s.flag IN ('valid','kisinti') AND s.ts_utc >= now() - (:g * INTERVAL '1 day')"),
            {"p": plant_id, "g": gun}).mappings().first()
    saat = int(r["saat"] or 0)
    return {"pencere_gun": gun, "saat": saat, "kirpma_saat": int(r["kirpma"] or 0), "kirpma_gun": int(r["kirpma_gun"] or 0),
            "kisinti_saat": int(r["kisinti"] or 0), "kisinti_gun": int(r["kisinti_gun"] or 0),
            "kisinti_kayip_kwh": round(float(r["kayip_kwh"] or 0), 1),
            "beklenen_kapsama": round(int(r["beklenen_saat"] or 0) / saat, 3) if saat else None,
            "kisinti_aranabildi": bool(r["beklenen_saat"])}
