"""v2.281 — Tablo 3.5 satır 8: tarife / gelir yapılandırması — sabit, PTF-endeksli, YEKDEM (döviz endeksli).

params_json.tarife = {tip: 'sabit'|'ptf'|'yekdem', tl_mwh, prim_oran, sabit_ek_tl_mwh, usd_cent_kwh, kur_tl_usd, eskalasyon_yillik}.
Gelir = üretim × saatlik fiyat (pvquant.ext.platform.tarife). Bankable kartında yıllık gelir P50/P90 (TL), fatura şablonunda
aylık gelir. Dengesizlik simülatörü piyasa kurallarıyla ayrı hesaplanır (tarife dengesizliği değiştirmez).
"""
from __future__ import annotations

import json

import pandas as pd

from pvquant.ext.platform import tarife as tf

TIPLER = ("sabit", "ptf", "yekdem")


def dogrula(t: dict) -> dict:
    tip = t.get("tip")
    if tip not in TIPLER:
        raise ValueError(f"tip: {TIPLER}")
    out = {"tip": tip}
    if tip == "sabit":
        v = float(t.get("tl_mwh") or 0)
        if not (0 < v < 100000):
            raise ValueError("tl_mwh 0–100.000")
        out["tl_mwh"] = v
    elif tip == "ptf":
        out["prim_oran"] = float(t.get("prim_oran") or 0.0); out["sabit_ek_tl_mwh"] = float(t.get("sabit_ek_tl_mwh") or 0.0)
        if not (-0.5 <= out["prim_oran"] <= 1.0):
            raise ValueError("prim_oran −0,5–1,0")
    else:
        c = float(t.get("usd_cent_kwh") or 0); k = float(t.get("kur_tl_usd") or 0)
        if not (0 < c < 100 and 0 < k < 1000):
            raise ValueError("usd_cent_kwh / kur_tl_usd aralık dışı")
        out["usd_cent_kwh"] = c; out["kur_tl_usd"] = k
    e = float(t.get("eskalasyon_yillik") or 0.0)
    if not (0 <= e <= 1):
        raise ValueError("eskalasyon_yillik 0–1")
    out["eskalasyon_yillik"] = e
    return out


def yapi(t: dict) -> tf.TarifeYapisi:
    tip = t["tip"]
    if tip == "sabit":
        tar = tf.Sabit(float(t["tl_mwh"]))
    elif tip == "ptf":
        tar = tf.PtfEndeksli(float(t.get("prim_oran", 0.0)), float(t.get("sabit_ek_tl_mwh", 0.0)))
    else:
        tar = tf.Yekdem(float(t["usd_cent_kwh"]), float(t["kur_tl_usd"]))
    esk = tf.Eskalasyon(float(t.get("eskalasyon_yillik", 0.0)), 2026) if t.get("eskalasyon_yillik") else None
    return tf.TarifeYapisi(tip, tar, pd.Timestamp("2000-01-01", tz="UTC"), None, esk)


def tarife_getir(plant: dict) -> dict | None:
    pj = plant.get("params_json") or {}
    if isinstance(pj, str):
        pj = json.loads(pj)
    return pj.get("tarife")


def ortalama_fiyat_tl_mwh(t: dict, ptf_ort: float | None = None) -> float | None:
    """Yıllık gelir kabası için tek fiyat: sabit → tl_mwh; yekdem → cent×10×kur; ptf → PTF ort×(1+prim)+ek (PTF yoksa None)."""
    if t["tip"] == "sabit":
        return float(t["tl_mwh"])
    if t["tip"] == "yekdem":
        return float(t["usd_cent_kwh"]) * 10.0 * float(t["kur_tl_usd"])
    if ptf_ort is None:
        return None
    return float(ptf_ort) * (1 + float(t.get("prim_oran", 0.0))) + float(t.get("sabit_ek_tl_mwh", 0.0))


def gelir_df(uretim_kwh: pd.Series, t: dict, ptf: pd.Series | None = None) -> pd.DataFrame:
    """Saatlik üretim (kWh) → gelir tablosu (TL); PTF tipi için ptf serisi gerekir."""
    idx = pd.DatetimeIndex(uretim_kwh.index)
    idx = idx.tz_localize("UTC") if idx.tz is None else idx
    u = pd.Series(uretim_kwh.values, index=idx).astype(float) / 1000.0
    return tf.gelir(u, [yapi(t)], ptf=ptf)
