"""v2.273 — Dalga 2 (★ onaylı): ensemble üyeleriyle üye başına fizik koşusu → ampirik kantiller (Mayer & Yang 2022 kalıbı).

Her GEFS üyesi (meteo_uye) ayrı bir MeteoData olur; fizik boru hattı (forecast_7day) her üye için koşar → 31 güç serisi.
Hibrit modelin (Mod C) öğrendiği düzeltme üyelere ORANLA taşınır: r_t = P50_hibrit / P50_fizik_kontrol (gündüz, 0,5–2 arası),
böylece bant hibrit medyanın etrafında kurulur; kantiller üyelerden ampirik (P10/P25/P75/P90), P50 hibritin kendisi kalır.
Konformal katman (v2.252) bu HAM bandın üstüne aynı şekilde uygulanır. Model çekirdeğine dokunulmaz; bant KAYNAĞI değişir
(ayar bant_kaynagi='otomatik': üye yoksa eski model bandı).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from pvquant.config import get_settings

TAULAR = {"p10": 0.10, "p25": 0.25, "p75": 0.75, "p90": 0.90}


def uye_kantilleri(uye_guc: pd.DataFrame, p50_hibrit: pd.Series, p50_fizik_kontrol: pd.Series, capacity_kwp: float,
                   oran_sinir: tuple[float, float] = (0.5, 2.0)) -> pd.DataFrame:
    """SAF. uye_guc: index=saat, kolon=üye (kW). Döner p10/p25/p75/p90 (kW), P50 ile tutarlı (p10≤p25≤p50≤p75≤p90)."""
    idx = uye_guc.index
    h = p50_hibrit.reindex(idx).astype(float); f = p50_fizik_kontrol.reindex(idx).astype(float)
    gunduz = f > 0.01 * capacity_kwp
    oran = (h / f.where(gunduz)).clip(*oran_sinir).fillna(1.0)
    G = uye_guc.mul(oran, axis=0)
    out = pd.DataFrame(index=idx)
    for ad, t in TAULAR.items():
        out[ad] = G.quantile(t, axis=1)
    out["p10"] = np.minimum(out["p10"], h.fillna(out["p10"])); out["p25"] = np.minimum(out["p25"], h.fillna(out["p25"]))
    out["p75"] = np.maximum(out["p75"], h.fillna(out["p75"])); out["p90"] = np.maximum(out["p90"], h.fillna(out["p90"]))
    out = out.clip(lower=0.0)
    out["yayilim"] = G.std(axis=1)
    return out


def uye_meteodata(uye_df: pd.DataFrame, temel, lat: float, lon: float):
    """Üye çerçevesi → MeteoData; üyede eksik kolonlar (nem/yağış/kar) temel (deterministik) meteodan."""
    from pvquant.io.meteo import MeteoData
    idx = uye_df.index
    def kol(ad, yedek):
        s = uye_df[ad] if ad in uye_df and not uye_df[ad].isna().all() else None
        if s is None and yedek is not None:
            s = yedek.reindex(idx).interpolate(limit_direction="both")
        return s
    return MeteoData(ghi=uye_df["ghi"].astype(float), temp_air=kol("temp_air", temel.temp_air), wind_speed_10m=kol("wind_speed_10m", temel.wind_speed_10m),
                     relative_humidity=None, cloud_cover=kol("cloud_cover", temel.cloud_cover), latitude=lat, longitude=lon, timezone="UTC",
                     precipitation=(temel.precipitation.reindex(idx) if temel.precipitation is not None else None), snowfall=None,
                     kaynak="gefs", nwp_model="GEFS üye")


def bant_uret(plant: dict, spec, temel_meteo, h: pd.DataFrame, days: int) -> tuple[pd.DataFrame | None, dict]:
    """Ağ/DB: taze üyeler varsa üye başına fizik koşusu → kantiller; yoksa (None, {'kaynak':'model'})."""
    cfg = get_settings()
    if cfg.bant_kaynagi == "model":
        return None, {"kaynak": "model"}
    from pvquant.io import acik_nwp
    from pvquant.pipeline.forecast import forecast_7day
    uyeler = acik_nwp.arsivden_uyeler(float(plant["lat"]), float(plant["lon"]), days)
    if not uyeler or len(uyeler) < cfg.ensemble_min_uye:
        return None, {"kaynak": "model", "not": f"üye yok ya da az ({len(uyeler or {})} < {cfg.ensemble_min_uye})"}
    guc = {}
    for u, df in uyeler.items():
        try:
            md = uye_meteodata(df, temel_meteo, float(plant["lat"]), float(plant["lon"]))
            fr = forecast_7day(md, spec)
            guc[u] = fr.hourly["p_ac_kw"].reindex(h.index)
        except Exception as e:   # noqa: BLE001 — tek üye düşerse geri kalanı yeter
            print(f"[ensemble] üye {u} atlandı: {type(e).__name__}: {e}")
    if len(guc) < cfg.ensemble_min_uye:
        return None, {"kaynak": "model", "not": f"fizik koşusu geçen üye az ({len(guc)})"}
    G = pd.DataFrame(guc).dropna(how="all")
    q = uye_kantilleri(G, h["p50_kw"], h["physics_kw"], float(plant.get("ac_limit_kw") or plant["capacity_kwp"]))
    return q, {"kaynak": "gefs", "uye": int(len(guc)), "yayilim_ort_kw": round(float(q["yayilim"].mean()), 1)}
