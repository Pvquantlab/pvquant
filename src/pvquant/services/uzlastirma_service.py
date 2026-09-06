"""v2.280 — Tablo 3.2 satır 11: portföy / hiyerarşik uzlaştırma (MinT — Wickramasuriya, Athanasopoulos & Hyndman 2019).

Hiyerarşi: portföy (toplam) → santraller. Taban tahminler santralların son koşuları (P50 ve bant); üst düğüm için bağımsız
tahmin yoksa (portföy düzeyinde ayrı model yok) bottom-up = toplam (zaten tutarlı). ≥2 santral ve ≥14 gün ortak artık
geçmişi varsa MinT-shrink: santral artık kovaryansı (büzülmüş) ile ağırlıklı en küçük kareler — bir santralin sistematik
hatası ötekilerle dengelenir; sonuç yine toplamı tutar (tutarlilik_kontrol). Kantiller taban kantilleri ayrı ayrı
uzlaştırılarak (yaklaşık). Tek santralde dürüstçe 'bottom-up (uzlaştırma gerekmez)'. Kayıt yazmaz; sunum katmanı.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from pvquant.ext.tahmin import portfoy as hp

MIN_GUN = 14


def uzlastir_df(tahminler: dict[str, pd.DataFrame], artiklar: pd.DataFrame | None) -> tuple[pd.DataFrame, dict]:
    """SAF. tahminler[santral] = ts index'li p50/p10/p90 (kW). artiklar: kolon=santral, satır=saat (p50−gerçek) ya da None.
    Döner (portföy çerçevesi p50/p10/p90 + santral başına uzlaşık p50, meta)."""
    adlar = list(tahminler)
    if not adlar:
        raise ValueError("santral yok")
    idx = None
    for df in tahminler.values():
        idx = df.index if idx is None else idx.intersection(df.index)
    if idx is None or len(idx) == 0:
        raise ValueError("ortak saat yok")
    S, dugumler = hp.toplama_matrisi({"portfoy": adlar}, adlar)
    out = pd.DataFrame(index=idx)
    meta = {"santral": len(adlar), "yontem": "bottom-up", "n_saat": int(len(idx))}
    yeterli = artiklar is not None and len(adlar) >= 2 and artiklar.dropna().shape[0] >= MIN_GUN * 8
    for kol in ("p50", "p10", "p90"):
        taban = pd.DataFrame({a: tahminler[a][kol].reindex(idx).astype(float) for a in adlar})
        top = taban.sum(axis=1)
        if yeterli and kol == "p50":
            Y = pd.concat([top.rename("portfoy"), taban], axis=1)[dugumler]
            E = pd.concat([artiklar[adlar].sum(axis=1).rename("portfoy"), artiklar[adlar]], axis=1)[dugumler]
            uz = hp.mint(Y, S, dugumler, E, yontem="shrink").clip(lower=0.0)
            meta["yontem"] = "MinT (büzülmüş kovaryans)"; meta["tutarli"] = hp.tutarlilik_kontrol(uz, S, dugumler)
            out["p50"] = uz["portfoy"]
            for a in adlar:
                out[f"{a}__p50"] = uz[a]
        else:
            out[kol] = top
            if kol == "p50":
                for a in adlar:
                    out[f"{a}__p50"] = taban[a]
    out["p10"] = np.minimum(out["p10"], out["p50"]); out["p90"] = np.maximum(out["p90"], out["p50"])
    return out, meta


def portfoy_tahmini(tenant_id, gun: int = 7) -> dict:
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    from pvquant.services import forecast_service
    with tenant_baglami(tenant_id) as s:
        santraller = [dict(r._mapping) for r in s.execute(text("SELECT id, name, tz, capacity_kwp FROM plants WHERE NOT archived ORDER BY name"))]
        art = pd.read_sql(text(
            "SELECT p.name, f.ts_utc, f.p50_kw - s.power_kw AS artik FROM forecast_values f JOIN forecast_runs r ON r.id=f.run_id "
            "JOIN scada_hourly s ON s.plant_id=f.plant_id AND s.ts_utc=f.ts_utc AND s.flag='valid' JOIN plants p ON p.id=f.plant_id "
            "WHERE f.ts_utc >= now() - interval '60 days' AND f.ts_utc - r.run_at BETWEEN INTERVAL '0 hour' AND INTERVAL '24 hour' "
            "AND s.power_kw > 0.02 * p.capacity_kwp"), s.connection(), parse_dates=["ts_utc"])
    tahminler = {}
    for p in santraller:
        df = forecast_service.son_kosu(tenant_id, str(p["id"]))
        if df is None or df.empty:
            continue
        d = pd.DataFrame({"p50": df["p50_kw"], "p10": df["p10_kw"], "p90": df["p90_kw"]})
        d.index = pd.DatetimeIndex(d.index); d.index = d.index.tz_localize("UTC") if d.index.tz is None else d.index
        tahminler[p["name"]] = d
    if not tahminler:
        return {"durum": "kosu_yok", "santral": len(santraller)}
    artiklar = art.pivot_table(index="ts_utc", columns="name", values="artik") if not art.empty else None
    uz, meta = uzlastir_df(tahminler, artiklar)
    tz = santraller[0].get("tz") or "Europe/Istanbul"
    yerel = uz.index.tz_convert(tz)
    g = uz.groupby(yerel.date).agg({"p50": "sum", "p10": "sum", "p90": "sum"}) / 1000.0
    say = uz.groupby(yerel.date).size()
    gunler = [{"gun": d.isoformat(), "p50_mwh": round(float(r["p50"]), 1), "p10_mwh": round(float(r["p10"]), 1), "p90_mwh": round(float(r["p90"]), 1),
               "saat": int(say[d])} for d, r in g.iterrows() if say[d] >= 20][:gun]
    santral_gunluk = {a: round(float(uz[f"{a}__p50"].groupby(yerel.date).sum().iloc[0]) / 1000.0, 1) for a in tahminler if f"{a}__p50" in uz}
    return {"durum": "ok", **meta, "kapasite_kwp": float(sum(p["capacity_kwp"] for p in santraller)), "gunler": gunler,
            "santral_bugun_mwh": santral_gunluk, "artik_gun": int(art["ts_utc"].dt.date.nunique()) if not art.empty else 0,
            "not": ("Tek santral: portföy = santral; uzlaştırma gerekmez." if len(tahminler) == 1 else
                    ("Santral artıklarının büzülmüş kovaryansıyla en küçük kareler; toplam korunur." if meta["yontem"].startswith("MinT") else
                     f"MinT için ≥2 santral ve ≥{MIN_GUN} gün ortak artık gerekir — şimdilik bottom-up (toplam)."))}
