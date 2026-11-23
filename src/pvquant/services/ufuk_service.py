"""v2.279 — Tablo 3.2 satır 3: ufukla büyüyen belirsizlik — geçmiş hatadan ufuk-bazlı σ(h) tabanı (★ onaylı, son katman).

Ensemble üyeleri açık gök haftasında hemfikirdir (yayılım ~10 kW) ve bant ufukla büyümez; oysa gerçek hata ufukla büyür.
Bu katman son N günün gündüz artıklarından (p50 − gerçek) ufuk kovası başına σ(h) çıkarır (pvquant.ext.tahmin.
ensemble_belirsizlik.ufuk_sigma: monoton büyüyen), servis bandının yarı genişliğini z·σ(h) ile ALTTAN sınırlar
(yalnız genişletir, daraltmaz; p10 ≥ 0, p90 ≤ tavan). Sıra: model/ensemble ham bant → ufuk σ → sapma → konformal.
Ayar: ufuk_sigma_katmani otomatik|kapali. Sonuç plants.params_json.ufuk_sigma (gece işi).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from pvquant.config import get_settings
from pvquant.services import kalite_sozlugu as _ks   # v2.598 (F4-C): flag süzgeci tek sözlükten
from pvquant.services.karne_kurali import yayin_kosu_sql as _yayin_sql   # v2.597 (F4-B): yayımlanmış koşu süzgeci

KOVA_SAAT = 24          # ufuk kovası genişliği (saat)
Z10 = 1.2816            # P10/P90 için normal z
Z25 = 0.6745            # G2-C2 (23.11): P25/P75 için normal z — iç bant da σ(h) ile ALTTAN sınırlanır (eskiden yalnız ham GEFS kantili; PICP50 ≈ 0,25)
K25_ALT_SINIR = 0.3     # G2-C2b: ampirik k−/k+ kırpma aralığı; üst sınır < Z10 → sıralama garantisi, alt sınır dejenere bant koruması
K25_UST_SINIR = 1.0
MIN_SAAT = 72
PENCERE_GUN = 60


def sigma_hesapla_df(df: pd.DataFrame, capacity_kwp: float) -> dict | None:
    """SAF. df: ts_utc, run_at, p50_kw, power_kw. Döner {kova(h): sigma_kw} monoton, n, kova_saat; yetersizse None."""
    if df is None or df.empty:
        return None
    x = df.dropna(subset=["p50_kw", "power_kw"]).copy()
    x = x[x["power_kw"] > 0.02 * capacity_kwp]
    if len(x) < MIN_SAAT:
        return None
    ts = pd.to_datetime(x["ts_utc"], utc=True); ra = pd.to_datetime(x["run_at"], utc=True)
    ufuk = ((ts - ra).dt.total_seconds() / 3600.0)
    x = x[ufuk >= 0]; ufuk = ufuk[ufuk >= 0]
    kova = (ufuk // KOVA_SAAT).astype(int)
    hata = (x["p50_kw"] - x["power_kw"]).astype(float)
    hata.index = x.index; kova.index = x.index
    from pvquant.ext.tahmin.ensemble_belirsizlik import ufuk_sigma
    s = ufuk_sigma(hata, kova, monoton=True).dropna()
    s = s[s.index.map(lambda k: int((kova == k).sum()) >= 12)]      # kova başına ≥12 saat
    if s.empty:
        return None
    ayar = {"sigma_kw": {str(int(k)): round(float(v), 1) for k, v in s.items()}, "n": int(len(x)), "kova_saat": KOVA_SAAT,
            "hesap_zamani": datetime.now(timezone.utc).isoformat(), "pencere_gun": PENCERE_GUN}
    k25 = k25_hesapla(hata, kova, ayar["sigma_kw"])
    if k25 is not None:
        ayar["k25"] = k25
    return ayar


def k25_hesapla(hata: pd.Series, kova: pd.Series, sigma_kw: dict) -> dict | None:
    """SAF (G2-C2b). İç bant katsayıları AMPİRİK: aynı artık kümesinde (p50 − gerçek) standardize artık z = (gerçek − p50)/σ(kova);
    alt = −Q25(z), üst = Q75(z) — normal varsayımı (0,6745) yerine gözlenen dağılımın çeyrekleri (sabit sette merkez sivri, alt kuyruk
    ağır, asimetrik). Kırpma [K25_ALT_SINIR, K25_UST_SINIR]: üst sınır Z10'un altında olduğundan p10 ≤ p25 ≤ p50 ≤ p75 ≤ p90 her zaman
    korunur; alt sınır dejenere (sıfır genişlik) bandı önler. Satır sayısı MIN_SAAT'in altındaysa ya da σ'sı olmayan kova varsa None →
    `uygula_df` Z25'e geri düşer. Yalnız hesaplandığı anda eldeki (geçmiş) artıkları kullanır; ileriye bakmaz."""
    sig = np.array([float(sigma_kw.get(str(int(k)), np.nan)) for k in kova], dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):   # QA C2b İ-4: σ=0 ya da eksik kova → inf/NaN, aşağıda düşer (uyarı yok)
        z = (-hata.to_numpy(dtype=float)) / sig
    z = z[np.isfinite(z)]
    if len(z) < MIN_SAAT:
        return None
    alt = float(np.clip(-np.quantile(z, 0.25), K25_ALT_SINIR, K25_UST_SINIR))
    ust = float(np.clip(np.quantile(z, 0.75), K25_ALT_SINIR, K25_UST_SINIR))
    return {"alt": round(alt, 4), "ust": round(ust, 4), "n": int(len(z)), "kaynak": "ampirik"}


def k25_oku(ayar: dict | None) -> tuple[float, float]:
    """SAF. Ayardaki ampirik k25 varsa (alt, üst); yoksa ya da geçersizse (Z25, Z25) — güvenli geri dönüş."""
    k = (ayar or {}).get("k25") if isinstance(ayar, dict) else None
    try:
        alt, ust = float(k["alt"]), float(k["ust"])
    except (TypeError, KeyError, ValueError):
        return Z25, Z25
    if not (np.isfinite(alt) and np.isfinite(ust)):
        return Z25, Z25
    return float(np.clip(alt, K25_ALT_SINIR, K25_UST_SINIR)), float(np.clip(ust, K25_ALT_SINIR, K25_UST_SINIR))


def uygula_df(h: pd.DataFrame, ayar: dict | None, run_at: pd.Timestamp, tavan_kw: float | None) -> pd.DataFrame:
    """SAF. Yarı genişlik ≥ z·σ(kova) — dış bant p10/p90 Z10 ile, iç bant p25/p75 Z25 ile (G2-C2); yalnız genişletir.
    Gece (p50 ≈ 0) ve iç bandı olmayan (NaN) satırlara dokunmaz."""
    if not ayar or not ayar.get("sigma_kw") or "p10_kw" not in h:
        return h
    h = h.copy()
    idx = pd.DatetimeIndex(h.index); idx = idx.tz_localize("UTC") if idx.tz is None else idx
    ra = pd.Timestamp(run_at); ra = ra.tz_localize("UTC") if ra.tz is None else ra.tz_convert("UTC")
    kova = ((idx - ra) / pd.Timedelta(hours=1) // ayar.get("kova_saat", KOVA_SAAT)).astype(int)
    sig = ayar["sigma_kw"]; anahtarlar = sorted(int(k) for k in sig)
    def s_of(k):
        if str(k) in sig:
            return float(sig[str(k)])
        return float(sig[str(max(a for a in anahtarlar if a <= k))]) if any(a <= k for a in anahtarlar) else float(sig[str(anahtarlar[0])])
    sigma = np.array([s_of(int(k)) for k in kova])
    p50 = pd.to_numeric(h["p50_kw"], errors="coerce")
    gunduz = p50 > 0
    p10 = pd.to_numeric(h["p10_kw"], errors="coerce"); p90 = pd.to_numeric(h["p90_kw"], errors="coerce")
    alt = (p50 - Z10 * sigma).clip(lower=0.0); ust = p50 + Z10 * sigma
    if tavan_kw:
        ust = ust.clip(upper=float(tavan_kw))
    yeni10 = np.where(gunduz & p10.notna(), np.minimum(p10.fillna(alt), alt), p10)
    yeni90 = np.where(gunduz & p90.notna(), np.maximum(p90.fillna(ust), ust), p90)
    h["p10_kw"] = yeni10; h["p90_kw"] = yeni90
    # G2-C2 (23.11, bulgu C2-5): iç bant (p25/p75) aynı kuralla — yarı genişlik ≥ Z25·σ(kova), yalnız genişletir, gece dokunmaz,
    # iç bant yoksa (A/B model bandı, NaN) uydurulmaz. p10/p50/p90 satırları yukarıda değişmedi; Z25·σ ≤ Z10·σ olduğundan
    # p10 ≤ p25 ≤ p50 ≤ p75 ≤ p90 sırası korunur (tavan kırpması da monoton).
    if "p25_kw" in h and "p75_kw" in h:
        p25 = pd.to_numeric(h["p25_kw"], errors="coerce")
        p75 = pd.to_numeric(h["p75_kw"], errors="coerce")
        k_alt, k_ust = k25_oku(ayar)   # G2-C2b: ampirik asimetrik katsayı (gece işi ayarı); yoksa Z25 — p10/p90 Z10'da kalır
        alt25 = (p50 - k_alt * sigma).clip(lower=0.0)
        ust25 = p50 + k_ust * sigma
        if tavan_kw:
            ust25 = ust25.clip(upper=float(tavan_kw))
        h["p25_kw"] = np.where(gunduz & p25.notna(), np.minimum(p25.fillna(alt25), alt25), p25)
        h["p75_kw"] = np.where(gunduz & p75.notna(), np.maximum(p75.fillna(ust25), ust25), p75)
    return h


def gece_ufuk_sigma(tenant_id, plant: dict, gun: int = PENCERE_GUN) -> dict | None:
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    from pvquant.services import plant_service
    with tenant_baglami(tenant_id) as s:
        df = pd.read_sql(text(
            "SELECT f.ts_utc, r.run_at, f.p50_kw, s.power_kw FROM forecast_values f JOIN forecast_runs r ON r.id=f.run_id "
            f"JOIN scada_hourly s ON s.plant_id=f.plant_id AND s.ts_utc=f.ts_utc AND {_ks.sql_kosulu('karne', 's')} "
            f"WHERE f.plant_id=:p AND f.ts_utc >= (SELECT max(ts_utc) FROM scada_hourly WHERE plant_id=:p AND {_ks.sql_kosulu('karne')}) - (:g * INTERVAL '1 day') "
            f"AND {_yayin_sql('r')}"),
            s.connection(), params={"p": plant["id"], "g": gun}, parse_dates=["ts_utc", "run_at"])
    ayar = sigma_hesapla_df(df, float(plant["capacity_kwp"]))
    if ayar is None:
        return None
    plant_service.params_birlestir(tenant_id, plant["id"], ufuk_sigma=ayar)
    return ayar


def ayar_getir(plant: dict) -> dict | None:
    if get_settings().ufuk_sigma_katmani == "kapali":
        return None
    pj = plant.get("params_json") or {}
    if isinstance(pj, str):
        pj = json.loads(pj)
    return pj.get("ufuk_sigma")
