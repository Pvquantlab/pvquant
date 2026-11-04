"""v2.281 — Tablo 3.5 satır 8: tarife / gelir yapılandırması — sabit, PTF-endeksli, YEKDEM (döviz endeksli), çok zamanlı.

params_json.tarife = {tip: 'sabit'|'ptf'|'yekdem'|'cok_zamanli', tl_mwh, prim_oran, sabit_ek_tl_mwh, usd_cent_kwh, kur_tl_usd, eskalasyon_yillik,
  v2.520 (P5a) YEKDEM alanları: rejim ('otomatik' | 'cetvel1' | '7189'), tesis_tipi ('gunes' | 'gunes_depolamali'), yerli_katki (bool, 7189),
  yerli_katki_usd_cent (Cetvel I, II sayılı Cetvel)}.
Gelir = üretim × saatlik fiyat (pvquant.ext.platform.tarife). Bankable kartında yıllık gelir P50/P90 (TL), fatura şablonunda aylık gelir.
Dengesizlik simülatörü piyasa kurallarıyla ayrı hesaplanır (tarife dengesizliği değiştirmez).
YEKDEM (v2.520): fiyat gün bazında yekdem_service'ten gelir — Cetvel I ¢ × 10 × günün TCMB alış kuru, 7189 ayın EPİAŞ ilanı (+ yerli katkı);
`plant` verilmeyen eski çağrılar ve TCMB/ilan verisi olmayan günler için elle girilen kur × ¢ (eski davranış) sürer.
"""
from __future__ import annotations

import json

import pandas as pd

from pvquant.ext.platform import tarife as tf

TIPLER = ("sabit", "ptf", "yekdem", "cok_zamanli")
REJIMLER = ("otomatik", "cetvel1", "7189")
TESIS_TIPLERI = ("gunes", "gunes_depolamali")


def _sayi(t: dict, ad: str, alt: float, ust: float, zorunlu: bool = False, alt_dahil: bool = False) -> float | None:
    v = t.get(ad)
    if v in (None, ""):
        if zorunlu:
            raise ValueError(f"{ad} gerekli")
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError(f"{ad} sayı olmalı")
    if not ((alt <= x if alt_dahil else alt < x) and x < ust):
        raise ValueError(f"{ad} {alt}–{ust} aralığında olmalı")
    return x


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
    elif tip == "yekdem":
        # v2.520 (P5a): ¢ ve kur isteğe bağlı — fiyat rejime göre TCMB kuru / EPİAŞ ilanından gelir; elle kur yalnız yedek
        rejim = t.get("rejim") or "otomatik"
        if rejim not in REJIMLER:
            raise ValueError("rejim otomatik / cetvel1 / 7189 olmalı")
        tesis = t.get("tesis_tipi") or "gunes"
        if tesis not in TESIS_TIPLERI:
            raise ValueError("tesis_tipi gunes / gunes_depolamali olmalı")
        out["rejim"] = rejim; out["tesis_tipi"] = tesis
        c = _sayi(t, "usd_cent_kwh", 0, 100); k = _sayi(t, "kur_tl_usd", 0, 1000); y = _sayi(t, "yerli_katki_usd_cent", 0, 20, alt_dahil=True)
        if c is not None:
            out["usd_cent_kwh"] = c
        if k is not None:
            out["kur_tl_usd"] = k
        if y is not None:
            out["yerli_katki_usd_cent"] = y
        out["yerli_katki"] = bool(t.get("yerli_katki"))
    else:   # cok_zamanli — gündüz 06–17 / puant 17–22 / gece 22–06 (İstanbul)
        for ad2 in ("gunduz_tl_mwh", "puant_tl_mwh", "gece_tl_mwh"):
            v = float(t.get(ad2) or 0)
            if not (0 < v < 100000):
                raise ValueError(f"{ad2} 0–100.000")
            out[ad2] = v
    e = float(t.get("eskalasyon_yillik") or 0.0)
    if not (0 <= e <= 1):
        raise ValueError("eskalasyon_yillik 0–1")
    out["eskalasyon_yillik"] = e
    return out


def _yekdem_tarife(t: dict, plant: dict | None, bas, bit):
    """v2.520: plant + gün aralığı verildiyse gün bazlı seri (yekdem_service); hiç fiyatı yoksa ya da plant yoksa eski ¢ × elle kur.
    v2.532 (03.11.2026 doğrulama arşivi DK-294, kanıt A): 7189 rejiminde fiyat TL bazlı aylık EPİAŞ ilanıdır (Ek-2 güncelleme + USD sınır kontrolü);
    ilan yoksa ¢ × kur yedek dalı KULLANILMAZ — hata verilir. Yedek dal yalnız Cetvel I (ya da rejimi türetilemeyen) tesiste kalır."""
    if plant is not None and bas is not None and bit is not None:
        from pvquant.services import yekdem_service
        pj = yekdem_service._pj(plant)
        pj2 = {**pj, "tarife": {**(pj.get("tarife") or {}), **t}}
        s = yekdem_service.gunluk_fiyat_serisi(pj2, bas, bit)
        if s["toplam_tl_mwh"].notna().any():
            return tf.YekdemSeri(s["toplam_tl_mwh"])
        if yekdem_service.rejim_turet(pj2)["rejim"] == "7189":
            raise ValueError("7189 sayılı CK rejiminde YEK fiyatı aylık EPİAŞ ilanıdır; bu dönem için ilan kayıtlı değil, ¢ × kur ile fiyat üretilmez "
                             "(Yönetim › Fiyat ve kur'dan ilan girilir)")
    if t.get("usd_cent_kwh") and t.get("kur_tl_usd"):
        return tf.Yekdem(float(t["usd_cent_kwh"]), float(t["kur_tl_usd"]))
    raise ValueError("YEKDEM fiyatı için TCMB kuru ya da aylık EPİAŞ ilanı yok; Santral ayarları › Satış tarifesi'nde yedek kur girilebilir")


def yapi(t: dict, plant: dict | None = None, bas=None, bit=None) -> tf.TarifeYapisi:
    tip = t["tip"]
    if tip == "sabit":
        tar = tf.Sabit(float(t["tl_mwh"]))
    elif tip == "cok_zamanli":
        tar = tf.CokZamanli(fiyatlar={"gunduz": float(t["gunduz_tl_mwh"]), "puant": float(t["puant_tl_mwh"]), "gece": float(t["gece_tl_mwh"])})
    elif tip == "ptf":
        tar = tf.PtfEndeksli(float(t.get("prim_oran", 0.0)), float(t.get("sabit_ek_tl_mwh", 0.0)))
    else:
        tar = _yekdem_tarife(t, plant, bas, bit)
    esk = tf.Eskalasyon(float(t.get("eskalasyon_yillik", 0.0)), 2026) if t.get("eskalasyon_yillik") else None
    return tf.TarifeYapisi(tip, tar, pd.Timestamp("2000-01-01", tz="UTC"), None, esk)


def tarife_getir(plant: dict) -> dict | None:
    pj = plant.get("params_json") or {}
    if isinstance(pj, str):
        pj = json.loads(pj)
    return pj.get("tarife")


def ortalama_fiyat_tl_mwh(t: dict, ptf_ort: float | None = None, plant: dict | None = None) -> float | None:
    """Yıllık gelir kabası için tek fiyat: sabit → tl_mwh; yekdem → bugünün YEK fiyatı (v2.520; plant verilmişse) yoksa cent×10×kur;
    ptf → PTF ort×(1+prim)+ek (PTF yoksa None)."""
    if t["tip"] == "sabit":
        return float(t["tl_mwh"])
    if t["tip"] == "yekdem":
        if plant is not None:
            from pvquant.services import yekdem_service
            try:
                g = yekdem_service.gun_fiyati(plant)
            except Exception:   # noqa: BLE001 — DB yoksa eski formül
                g = None
            if g and g.get("toplam_tl_mwh"):
                return float(g["toplam_tl_mwh"])
        if t.get("usd_cent_kwh") and t.get("kur_tl_usd"):
            return float(t["usd_cent_kwh"]) * 10.0 * float(t["kur_tl_usd"])
        return None
    if t["tip"] == "cok_zamanli":
        return None   # dürüst: yıllık kaba gelir için üretim profili gerekir; fatura saatlik hesapla tam çalışır
    if ptf_ort is None:
        return None
    return float(ptf_ort) * (1 + float(t.get("prim_oran", 0.0))) + float(t.get("sabit_ek_tl_mwh", 0.0))


def gelir_df(uretim_kwh: pd.Series, t: dict, ptf: pd.Series | None = None, plant: dict | None = None) -> pd.DataFrame:
    """Saatlik üretim (kWh) → gelir tablosu (TL); PTF tipi için ptf serisi gerekir. v2.520: plant verilirse YEKDEM fiyatı gün bazlı."""
    idx = pd.DatetimeIndex(uretim_kwh.index)
    idx = idx.tz_localize("UTC") if idx.tz is None else idx
    u = pd.Series(uretim_kwh.values, index=idx).astype(float) / 1000.0
    bas = bit = None
    if len(idx) and t.get("tip") == "yekdem":
        ist = idx.tz_convert("Europe/Istanbul"); bas, bit = ist.min().date(), ist.max().date()
    return tf.gelir(u, [yapi(t, plant=plant, bas=bas, bit=bit)], ptf=ptf)
