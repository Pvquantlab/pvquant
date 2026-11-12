"""10.11.2026 v2.574 (Faz 1 paketi F1-C, Stage 4–5) — BAĞIMSIZ DOĞRULAMA MOTORU: yayımlandığı andaki tahmin × uygun ölçüm × referanslar.

Tek sözlük (SOZLUK_SURUMU). Çekirdek tahmin matematiğine dokunmaz; `forecast_values`/`forecast_runs`'ı yalnız OKUR, sonucu kendi
yalnız-ekleme tablosuna (`dogrulama_sonuc`) yazar. Mevcut gece karnesi (`skill_daily`) değişmez; ikisi yan yana yaşar.

Koşu seçimi (saat başına TEK tahmin, çift sayım yok; karne_kurali ile aynı dışlamalar: backtest, arşiv meteo, sentetik tohum):
  program     teslim günü D için D-1 KGÜP kesimi öncesi son koşunun D saatleri (karne_kurali.program_kovasi)
  gun_oncesi  yerel gün D için D 00:00 öncesi yayımlanmış SON koşu (gün başlamadan elde olan en taze tahmin; gün içi revizyon dâhil)
  gun_ici     yalnız gün içi revizyon koşuları, saat başına en son revizyon (karne_kurali)
  ufuk        ana kovalar 0-24 / 24-72 / 72-168 / 168+ (saat başına en erken koşu; karne_kurali) — ufuk kesiti için
Gündüz maskesi: gerçek > GUNDUZ_ORAN·kapasite VEYA tahmin > GUNDUZ_ORAN·kapasite (tahminin «gece» dediği ama üretim olan saat ve
üretim olmayan ama tahmin olan saat kaçmaz). Gece saatleri ayrı sayılır («gece davranışı»).
Metrikler (gündüz, uygun saatler; birimler açık): WMAPE havuzlanmış Σ|f−y|/Σy (% — payda yetersizse None, günlük ortalama WMAPE ayrıca),
MAE kW, RMSE kW, nMAE/nRMSE (kapasite kWp'ye bölü, %), MBE kW ve nMBE % (işaret: tahmin − gerçek; pozitif = fazla tahmin), günlük enerji
sapması kWh/gün (Σ(f−y) günlük ortalaması); PICP80 (y ∈ [P10, P90] oranı), P(y<P10), P(y>P90), ortalama bant genişliği / kapasite,
Winkler α=0,2 kW. Eksik/dışlanan saat hiçbir yerde 0 sayılmaz (olcum_uygunluk_service).
Referanslar aynı saat kümesinde: fizik (aynı koşunun physics_kw), bilgi kümesi tutarlı persistans (yayın anından önce ölçülmüş son aynı
saat × açık gök oranı), CLIPER örneklem dışı (iklimsel + persistans; ağırlık dönem ÖNCESİ veride). Beceri = 1 − WMAPE/WMAPE_ref.
Her sonuç yeniden üretim metası taşır: sözlük sürümü, kural, koşu kümesi ve saat kümesi SHA-256 özeti, kapasite, yazılım sürümü.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd

from pvquant.services import kalite_sozlugu as _ks  # v2.598 (F4-C): flag süzgeci tek sözlükten
from pvquant.services import karne_kurali as kk
from pvquant.zaman import PIYASA_TZ

SOZLUK_SURUMU = "2026-11-10"
KURALLAR = ("program", "gun_oncesi", "gun_ici", "ufuk")
GUNDUZ_ORAN = 0.02
ASGARI_SAAT = 3                 # bir kesitte metrik için en az gündüz saati
PAYDA_ASGARI_ORAN = 0.01        # WMAPE paydası < oran × kapasite × n_saat ise «hesaplanamaz»
PERSISTANS_KELEPCE = 4.0
MEVSIM = {12: "kis", 1: "kis", 2: "kis", 3: "ilkbahar", 4: "ilkbahar", 5: "ilkbahar", 6: "yaz", 7: "yaz", 8: "yaz", 9: "sonbahar", 10: "sonbahar", 11: "sonbahar"}
ALPHA = 0.2


# ---------------------------------------------------------------- yardımcılar
def _utc(x) -> pd.Timestamp:
    t = pd.Timestamp(x)
    return t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")


def _r(v, n=2):
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if np.isnan(f) or np.isinf(f) else round(f, n)


def _sha(seq) -> str:
    return hashlib.sha256("\n".join(str(x) for x in seq).encode()).hexdigest()[:16]


# ---------------------------------------------------------------- koşu seçimi
def kosu_sec(tahmin: pd.DataFrame, kural: str, tz: str, simulasyon: bool = False) -> pd.DataFrame:
    """tahmin: ts_utc, run_at, run_id, p50_kw, p10_kw, p90_kw, physics_kw, model, meteo_source, etiket. Döner: seçilen satırlar + ufuk_s, kova.
    simulasyon=True (v2.577, F1-F2): geriye bakışlı koşular (model='backtest', arşiv meteo) AÇIKÇA dâhil edilir — yalnız «geriye dönük simülasyon»
    etiketli çalışmalar için; sonuç kaydedilmez (kaydet reddeder) ve rapor etiketi bunu yazar."""
    if kural not in KURALLAR:
        raise ValueError("kural " + "|".join(KURALLAR))
    if tahmin is None or tahmin.empty:
        return pd.DataFrame(columns=list(tahmin.columns if tahmin is not None else []) + ["ufuk_s", "kova"])
    d = tahmin.copy()
    if simulasyon:
        d["model"] = "simulasyon"; d["meteo_source"] = "simulasyon"   # dışlama süzgeci bu etiketleri tanımaz → dâhil
    d["ts_utc"] = pd.to_datetime(d["ts_utc"], utc=True); d["run_at"] = pd.to_datetime(d["run_at"], utc=True)
    if kural == "program":
        return kk.program_kovasi(d)
    if kural == "gun_ici":
        s = kk.karne_secimi(d)
        return s[s["kova"] == kk.KOVA_GUN_ICI] if not s.empty else s
    if kural == "ufuk":
        return kk.ana_kovalar(kk.karne_secimi(d))
    # gun_oncesi
    d = d[~kk.geriye_bakisli(d)].copy()
    d["_gun"] = d["ts_utc"].dt.tz_convert(tz).dt.date
    parcalar = []
    for gun, g in d.groupby("_gun"):
        bas = pd.Timestamp(gun, tz=tz)
        uygun = g[g["run_at"] < bas]
        if uygun.empty:
            continue
        son = uygun[uygun["run_at"] == uygun["run_at"].max()].copy()
        son["ufuk_s"] = (son["ts_utc"] - son["run_at"]).dt.total_seconds() / 3600
        son["kova"] = "gun_oncesi"
        parcalar.append(son.drop_duplicates("ts_utc"))
    if not parcalar:
        return pd.DataFrame(columns=list(d.drop(columns=["_gun"]).columns) + ["ufuk_s", "kova"])
    return pd.concat(parcalar, ignore_index=True).drop(columns=["_gun"])


# ---------------------------------------------------------------- eşleme ve maske
def eslestir(secim: pd.DataFrame, saatler: pd.DataFrame, tz: str) -> pd.DataFrame:
    """secim (kosu_sec çıktısı) × saatler (olcum_uygunluk.siniflandir çıktısı: ts_utc, kwh, durum, neden, kirpma). Dönem ızgarasındaki
    her saat için bir satır: tahmin yoksa p50 NaN (tahmin_yok), ölçüm uygun değilse y NaN ve neden dolu. Gündüz/gece maskesi eklenir."""
    s = saatler.copy(); s["ts_utc"] = pd.to_datetime(s["ts_utc"], utc=True)
    t = secim.copy() if secim is not None and not secim.empty else pd.DataFrame(columns=["ts_utc", "run_at", "run_id", "p50_kw", "p10_kw", "p90_kw", "physics_kw", "ufuk_s", "kova"])
    if not t.empty:
        t["ts_utc"] = pd.to_datetime(t["ts_utc"], utc=True)
    d = s.merge(t[[c for c in ("ts_utc", "run_at", "run_id", "p50_kw", "p10_kw", "p90_kw", "physics_kw", "ufuk_s", "kova", "etiket") if c in t.columns]], on="ts_utc", how="left")
    d["y"] = d["kwh"].where(d["durum"] == "olculdu")
    for c in ("p50_kw", "p10_kw", "p90_kw", "physics_kw"):
        if c not in d:
            d[c] = np.nan
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["gun"] = d["ts_utc"].dt.tz_convert(tz).dt.date
    d["saat_yerel"] = d["ts_utc"].dt.tz_convert(tz).dt.hour
    d["ay"] = d["ts_utc"].dt.tz_convert(tz).dt.strftime("%Y-%m")
    d["hafta"] = d["ts_utc"].dt.tz_convert(tz).dt.strftime("%G-W%V")
    d["mevsim"] = d["ts_utc"].dt.tz_convert(tz).dt.month.map(MEVSIM)
    return d


def gunduz_maskesi(d: pd.DataFrame, kapasite: float) -> pd.Series:
    esik = GUNDUZ_ORAN * float(kapasite)
    return (d["y"].fillna(0) > esik) | (d["p50_kw"].fillna(0) > esik)


def degerlendirilebilir(d: pd.DataFrame, kapasite: float) -> pd.DataFrame:
    """Metriklere giren satırlar: gündüz, ölçüm uygun, tahmin var."""
    m = gunduz_maskesi(d, kapasite) & d["y"].notna() & d["p50_kw"].notna()
    return d[m]


# ---------------------------------------------------------------- metrikler
def metrikler(e: pd.DataFrame, kapasite: float, tahmin_kolonu: str = "p50_kw") -> dict:
    """e: degerlendirilebilir çıktısı. Tüm birimler açık; payda yetersizse WMAPE None (sayı uydurulmaz)."""
    kap = float(kapasite)
    n = int(len(e))
    out = {"n_saat": n, "n_gun": int(e["gun"].nunique()) if n else 0, "birim": {"mae": "kW", "rmse": "kW", "mbe": "kW", "wmape": "%", "nmae": "% kurulu güç", "enerji_sapma": "kWh/gün"},
           "bias_isareti": "tahmin − gerçek; pozitif = fazla tahmin"}
    if n < ASGARI_SAAT:
        out.update({"wmape": None, "wmape_gunluk_ort": None, "mae_kw": None, "rmse_kw": None, "nmae": None, "nrmse": None, "mbe_kw": None, "nmbe": None,
                    "enerji_sapma_kwh_gun": None, "picp80": None, "p10_alti": None, "p90_ustu": None, "bant_genisligi_oran": None, "winkler_kw": None, "bant_n": 0,
                    "not": f"en az {ASGARI_SAAT} gündüz saati gerekir"})
        return out
    y = e["y"].astype(float).values; f = e[tahmin_kolonu].astype(float).values
    err = f - y
    payda = float(np.abs(y).sum())
    out["wmape"] = _r(np.abs(err).sum() / payda * 100) if payda >= PAYDA_ASGARI_ORAN * kap * n and payda > 0 else None
    if out["wmape"] is None:
        out["not"] = "WMAPE paydası yetersiz (gerçekleşen toplam çok küçük)"
    g = e.assign(_ae=np.abs(err), _y=y).groupby("gun")
    # v2.577: gün başına da aynı payda kuralı — gerçekleşeni çok küçük gün (kesinti, kar) günlük WMAPE'yi %1000'lere taşıyor ve ortalamayı
    # anlamsızlaştırıyordu (Solentegre 2025 simülasyonu: 28.04 günü %1230). O günler havuzlanmış WMAPE'de zaten paydaya girer; ortalamadan düşer.
    gun_payda = g["_y"].sum(); gun_n = g.size()
    gun_wm = (g["_ae"].sum() / gun_payda.where(gun_payda >= PAYDA_ASGARI_ORAN * kap * gun_n) * 100).dropna()
    out["wmape_gunluk_ort"] = _r(gun_wm.mean()) if len(gun_wm) else None
    out["wmape_gunluk_n"] = int(len(gun_wm))
    out["mae_kw"] = _r(np.abs(err).mean()); out["rmse_kw"] = _r(np.sqrt((err ** 2).mean())); out["mbe_kw"] = _r(err.mean())
    out["nmae"] = _r(np.abs(err).mean() / kap * 100); out["nrmse"] = _r(np.sqrt((err ** 2).mean()) / kap * 100); out["nmbe"] = _r(err.mean() / kap * 100)
    out["enerji_sapma_kwh_gun"] = _r(e.assign(_e=err).groupby("gun")["_e"].sum().mean(), 1)
    b = e[e["p10_kw"].notna() & e["p90_kw"].notna()]
    out["bant_n"] = int(len(b))
    if len(b) >= ASGARI_SAAT:
        yb, lo, hi = b["y"].astype(float).values, b["p10_kw"].astype(float).values, b["p90_kw"].astype(float).values
        out["picp80"] = _r(((yb >= lo) & (yb <= hi)).mean() * 100, 1)
        out["p10_alti"] = _r((yb < lo).mean() * 100, 1); out["p90_ustu"] = _r((yb > hi).mean() * 100, 1)
        out["bant_genisligi_oran"] = _r((hi - lo).mean() / kap * 100, 1)
        w = (hi - lo) + (2 / ALPHA) * (lo - yb) * (yb < lo) + (2 / ALPHA) * (yb - hi) * (yb > hi)
        out["winkler_kw"] = _r(w.mean(), 1)
    else:
        out.update({"picp80": None, "p10_alti": None, "p90_ustu": None, "bant_genisligi_oran": None, "winkler_kw": None})
    return out


def gece_davranisi(d: pd.DataFrame, kapasite: float) -> dict:
    """Gece (maske dışı) saatlerde tahmin ne diyor: tahmin > 0 saat sayısı ve enerjisi; gerçek > 0 (ölçüm hatası imzası)."""
    g = d[~gunduz_maskesi(d, kapasite)]
    return {"n_saat": int(len(g)), "tahmin_pozitif_saat": int((g["p50_kw"].fillna(0) > 0).sum()), "tahmin_kwh": _r(g["p50_kw"].fillna(0).sum(), 1),
            "gercek_pozitif_saat": int((g["y"].fillna(0) > 0).sum())}


# ---------------------------------------------------------------- kesitler
def _kesit(e: pd.DataFrame, kapasite: float, anahtar: str, adlar: dict | None = None, en_az: int = ASGARI_SAAT) -> list[dict]:
    out = []
    for k, g in e.groupby(anahtar, sort=True):
        if len(g) < en_az:
            continue
        m = metrikler(g, kapasite)
        out.append({"kesit": (adlar or {}).get(k, str(k)), "n_saat": m["n_saat"], "wmape": m["wmape"], "mae_kw": m["mae_kw"], "nmbe": m["nmbe"],
                    "enerji_sapma_kwh_gun": m["enerji_sapma_kwh_gun"], "picp80": m["picp80"]})
    return out


def kesitler(e: pd.DataFrame, kapasite: float) -> dict:
    out = {"gun": _kesit(e, kapasite, "gun"), "hafta": _kesit(e, kapasite, "hafta"), "ay": _kesit(e, kapasite, "ay"), "mevsim": _kesit(e, kapasite, "mevsim"),
           "saat": _kesit(e, kapasite, "saat_yerel")}
    if "ufuk_s" in e and e["ufuk_s"].notna().any():
        u = e.copy(); u["_ufuk"] = pd.cut(u["ufuk_s"], [0, 24, 48, 72, 168, 999], labels=["0-24", "24-48", "48-72", "72-168", "168+"], include_lowest=True).astype(object)
        out["ufuk"] = _kesit(u.dropna(subset=["_ufuk"]), kapasite, "_ufuk")
    # düşük / orta / yüksek üretim günleri: günlük ölçülen enerjinin üçte birlikleri (dönem içi)
    gunluk = e.groupby("gun")["y"].sum()
    if len(gunluk) >= 6:
        q1, q2 = gunluk.quantile([1 / 3, 2 / 3])
        sinif = gunluk.map(lambda v: "dusuk" if v <= q1 else ("yuksek" if v > q2 else "orta"))
        u = e.copy(); u["_sinif"] = u["gun"].map(sinif)
        out["uretim_sinifi"] = _kesit(u, kapasite, "_sinif", {"dusuk": "düşük üretim günleri", "orta": "orta", "yuksek": "yüksek üretim günleri"})
        out["uretim_sinifi_esik_kwh"] = {"dusuk_ust": _r(q1, 1), "yuksek_alt": _r(q2, 1)}
    else:
        out["uretim_sinifi"] = []
    out["en_zayif_gunler"] = sorted([g for g in out["gun"] if g["wmape"] is not None], key=lambda g: -g["wmape"])[:5]
    return out


# ---------------------------------------------------------------- referanslar
def _acik_gok(ts: pd.DatetimeIndex, lat: float, lon: float) -> pd.Series:
    import pvlib
    return pvlib.location.Location(float(lat), float(lon), tz="UTC").get_clearsky(ts, model="haurwitz").ghi


def persistans(e: pd.DataFrame, gecmis: pd.Series, lat: float, lon: float) -> pd.Series:
    """Bilgi kümesi tutarlı persistans: hedef saat t, yayın anı r → k = en küçük tam sayı ile t−24k < r; değer y(t−24k)·cs(t)/cs(t−24k).
    gecmis: ölçülmüş (uygun) saatlik kWh serisi (UTC indeks). Gözlem yoksa NaN (uydurulmaz)."""
    if e.empty:
        return pd.Series(dtype=float, index=e.index)
    ts = pd.to_datetime(e["ts_utc"], utc=True); ra = pd.to_datetime(e["run_at"], utc=True)
    k = np.floor((ts - ra).dt.total_seconds() / 86400).astype(int) + 1
    k = k.clip(lower=1)
    kaynak = ts - pd.to_timedelta(k * 24, unit="h")
    g = gecmis.copy(); g.index = pd.to_datetime(g.index, utc=True)
    ham = kaynak.map(g)
    cs = _acik_gok(pd.DatetimeIndex(sorted(set(ts) | set(kaynak))), lat, lon)
    oran = (ts.map(cs) / kaynak.map(cs)).clip(1.0 / PERSISTANS_KELEPCE, PERSISTANS_KELEPCE)
    p = ham * oran
    p[(kaynak.map(cs) <= 5.0) | ham.isna()] = np.nan
    return pd.Series(p.values, index=e.index)


def cliper(e: pd.DataFrame, gecmis: pd.Series, donem_bas: datetime, lat: float, lon: float) -> tuple[pd.Series, dict | None]:
    """CLIPER örneklem dışı: iklimsel (ay×saat, ≥20 gün) ve persistans; ağırlık dönem ÖNCESİ 30 günde öğrenilir (gün öncesi persistans ile)."""
    from pvquant.ext.tahmin import referans as ref
    bos = pd.Series(np.nan, index=e.index)
    if e.empty:
        return bos, None
    g = gecmis.copy(); g.index = pd.to_datetime(g.index, utc=True)
    onc = g[g.index < _utc(donem_bas)]
    if onc.empty:
        return bos, None
    ts = pd.DatetimeIndex(pd.to_datetime(e["ts_utc"], utc=True))
    ikl = ref.iklimsel(onc, ts, min_gun=20)
    if ikl.isna().all():
        return bos, None
    # ağırlık: dönem öncesi son 30 günde gün-öncesi persistans (k=1) vs iklimsel
    egitim = onc[onc.index >= _utc(donem_bas) - pd.Timedelta(days=30)]
    if len(egitim.dropna()) < 24 * 7:
        return bos, None
    cs = _acik_gok(pd.DatetimeIndex(sorted(set(egitim.index) | set(egitim.index - pd.Timedelta(hours=24)))), lat, lon)
    _oran = pd.Series((egitim.index.map(cs) / (egitim.index - pd.Timedelta(hours=24)).map(cs)).values, index=egitim.index).clip(1 / PERSISTANS_KELEPCE, PERSISTANS_KELEPCE)
    _oran[pd.Series((egitim.index - pd.Timedelta(hours=24)).map(cs).values, index=egitim.index) <= 5.0] = float("nan")
    pers_e = egitim.shift(freq="24h").reindex(egitim.index) * _oran
    ikl_e = ref.iklimsel(onc[onc.index < egitim.index.min()] if (onc.index < egitim.index.min()).any() else onc, egitim.index, min_gun=20)
    w = ref.optimal_agirlik(egitim, pers_e, ikl_e)
    pers_h = persistans(e, gecmis, lat, lon)
    out = (w * pers_h.values + (1 - w) * ikl.values)
    out = pd.Series(out, index=e.index).clip(lower=0)
    out[pers_h.isna().values | ikl.isna().values] = np.nan
    return out, {"agirlik_persistans": _r(w, 3), "egitim_saat": int(len(egitim.dropna()))}


def referanslar(e: pd.DataFrame, kapasite: float, gecmis: pd.Series | None, donem_bas: datetime, lat: float, lon: float, model_wmape: float | None) -> dict:
    out = {}
    def _kayit(ad, seri, ek=None):
        ee = e.assign(_ref=pd.to_numeric(seri, errors="coerce").values).dropna(subset=["_ref"])
        m = metrikler(ee, kapasite, "_ref") if len(ee) >= ASGARI_SAAT else {"n_saat": int(len(ee)), "wmape": None, "mae_kw": None, "nmbe": None}
        # model aynı saat kümesinde (adil kıyas)
        mm = metrikler(ee, kapasite) if len(ee) >= ASGARI_SAAT else {"wmape": None}
        beceri = _r((1 - mm["wmape"] / m["wmape"]) * 100, 1) if (m.get("wmape") not in (None, 0) and mm.get("wmape") is not None) else None
        out[ad] = {"n_saat": m["n_saat"], "wmape": m.get("wmape"), "mae_kw": m.get("mae_kw"), "nmbe": m.get("nmbe"), "model_wmape_ayni_saatler": mm.get("wmape"),
                   "beceri_pct": beceri, "sonuc": (None if beceri is None else ("model daha iyi" if beceri > 0 else ("referans daha iyi" if beceri < 0 else "eşit"))), **(ek or {})}
    _kayit("fizik", e["physics_kw"], {"tanim": "aynı koşunun saf fizik modeli P50'si"})
    if gecmis is not None and len(gecmis):
        _kayit("persistans", persistans(e, gecmis, lat, lon), {"tanim": "yayın anından önce ölçülmüş son aynı saat × açık gök oranı (bilgi kümesi tutarlı)"})
        c, cinfo = cliper(e, gecmis, donem_bas, lat, lon)
        if cinfo:
            _kayit("cliper", c, {"tanim": "iklimsel (ay×saat) + persistans, ağırlık dönem öncesi 30 günde", **cinfo})
        else:
            out["cliper"] = {"n_saat": 0, "wmape": None, "beceri_pct": None, "sonuc": None, "tanim": "hesaplanamadı: dönem öncesi yeterli ölçüm (ay×saat ≥20 gün, 7 gün eğitim) yok"}
    else:
        out["persistans"] = {"n_saat": 0, "wmape": None, "beceri_pct": None, "sonuc": None, "tanim": "hesaplanamadı: geçmiş ölçüm yok"}
        out["cliper"] = {"n_saat": 0, "wmape": None, "beceri_pct": None, "sonuc": None, "tanim": "hesaplanamadı: geçmiş ölçüm yok"}
    return out


# ---------------------------------------------------------------- bütünlük ve meta
def butunluk(d: pd.DataFrame, e: pd.DataFrame, dokum: dict, kapasite: float) -> dict:
    gunduz = d[gunduz_maskesi(d, kapasite)]
    dis = gunduz[gunduz["y"].isna() | gunduz["p50_kw"].isna()]
    neden = dis["neden"].where(dis["y"].isna(), "tahmin_yok").value_counts().to_dict()
    return {"olcum": dokum, "gunduz_saat": int(len(gunduz)), "degerlendirilen_saat": int(len(e)),
            "degerlendirilen_pct": _r(len(e) / len(gunduz) * 100, 1) if len(gunduz) else None,
            "gunduz_dislanan": {str(k): int(v) for k, v in sorted(neden.items(), key=lambda kv: -kv[1])},
            "kirpma_saat_degerlendirilen": int(e["kirpma"].fillna(False).astype(bool).sum()) if "kirpma" in e else 0,
            "gece": gece_davranisi(d, kapasite)}


def meta(d: pd.DataFrame, e: pd.DataFrame, kural: str, kaynak: str, kapasite: float, plant: dict, donem_bas, donem_bit, kosular: pd.DataFrame | None) -> dict:
    run_ids = sorted({str(r) for r in e["run_id"].dropna().unique()}) if "run_id" in e else []
    m = {"sozluk_surumu": SOZLUK_SURUMU, "kural": kural, "kaynak": kaynak, "kapasite_kwp": float(kapasite), "gunduz_orani": GUNDUZ_ORAN,
         "donem": {"bas": str(donem_bas), "bit": str(donem_bit), "tz": plant.get("tz")}, "kosu_sayisi": len(run_ids), "kosu_kumesi_sha": _sha(run_ids),
         "saat_kumesi_sha": _sha(sorted(e["ts_utc"].astype(str))), "hesap_zamani": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    try:   # v2.600 (F4-F): hangi mevzuat kural kümesiyle (program kesimi vb.) hesaplandı
        from pvquant.ext.turkiye import kural_sicili as _ks
        m["kural_sicili_sha"] = _ks.sicil_sha16()
    except Exception:   # noqa: BLE001
        m["kural_sicili_sha"] = None
    try:
        from pvquant.surum import yazilim_surumu
        m["yazilim_surumu"] = yazilim_surumu()
    except Exception:   # noqa: BLE001
        m["yazilim_surumu"] = None
    if kosular is not None and not kosular.empty and run_ids:
        k = kosular[kosular["run_id"].astype(str).isin(run_ids)]
        m["kosu_kunyesi"] = {"mode": sorted({str(x) for x in k["mode"].dropna().unique()}) if "mode" in k else [],
                             "model": sorted({str(x) for x in k["model"].dropna().unique()}) if "model" in k else [],
                             "meteo_source": sorted({str(x) for x in k["meteo_source"].dropna().unique()}) if "meteo_source" in k else [],
                             "kalibrasyon_id": sorted({str(x) for x in k["kalibrasyon_id"].dropna().unique()}) if "kalibrasyon_id" in k else [],
                             "yazilim_surumu": sorted({str(x) for x in k["yazilim_surumu"].dropna().unique()}) if "yazilim_surumu" in k else [],
                             "nwp_yasi_saat_ort": _r(((k["run_at"] - k["nwp_kosu_zamani"]).dt.total_seconds() / 3600).mean(), 1) if "nwp_kosu_zamani" in k and k["nwp_kosu_zamani"].notna().any() else None,
                             "ilk_run_at": str(k["run_at"].min()), "son_run_at": str(k["run_at"].max())}
    return m


# ---------------------------------------------------------------- saf uçtan uca
def hesapla_saf(tahmin: pd.DataFrame, saatler: pd.DataFrame, dokum: dict, plant: dict, donem_bas, donem_bit, kural: str = "program",
                kaynak: str = "scada", gecmis: pd.Series | None = None, kosular: pd.DataFrame | None = None, simulasyon: bool = False) -> dict:
    tz = plant.get("tz") or PIYASA_TZ; kap = float(plant["capacity_kwp"])
    secim = kosu_sec(tahmin, kural, tz, simulasyon)
    d = eslestir(secim, saatler, tz)
    e_tum = degerlendirilebilir(d, kap)
    if kural == "ufuk":
        # aynı saat birden çok kovada: üst düzey metrik ve bütünlük yalnız 0-24 kovası (saat başına tek tahmin); ufuk kesiti tüm kovalardan
        d = d[d["kova"].isna() | (d["kova"] == "0-24")].drop_duplicates("ts_utc")
        e = degerlendirilebilir(d, kap)
    else:
        e = e_tum
    m = metrikler(e, kap)
    kes = kesitler(e, kap) if len(e) >= ASGARI_SAAT else {"gun": [], "en_zayif_gunler": []}
    if kural == "ufuk" and len(e_tum) >= ASGARI_SAAT:
        kes["ufuk"] = kesitler(e_tum, kap).get("ufuk", [])
    return {"metrik": m, "kesit": kes,
            "referans": referanslar(e, kap, gecmis, donem_bas, float(plant["lat"]), float(plant["lon"]), m.get("wmape")) if len(e) >= ASGARI_SAAT else {},
            "butunluk": butunluk(d, e, dokum, kap), "meta": {**meta(d, e, kural, kaynak, kap, plant, donem_bas, donem_bit, kosular), "simulasyon": bool(simulasyon)}}


# ---------------------------------------------------------------- DB
def tahmin_oku(tenant_id, plant_id, bas: datetime, bit: datetime) -> tuple[pd.DataFrame, pd.DataFrame]:
    """[bas, bit) saatlerini kapsayan tüm koşuların değerleri (geriye bakışlı dâhil; seçim kuralı sonra eler) ve koşu künyeleri."""
    from sqlalchemy import text

    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        df = pd.read_sql(text(
            "SELECT f.ts_utc, f.run_id, r.run_at, f.p50_kw, f.p10_kw, f.p90_kw, f.physics_kw, r.model, r.meteo_source, "
            "COALESCE(r.etiket, r.meteo_ozet_json->>'etiket') AS etiket FROM forecast_values f JOIN forecast_runs r ON r.id = f.run_id "
            "WHERE f.plant_id = CAST(:p AS uuid) AND f.ts_utc >= :a AND f.ts_utc < :b ORDER BY f.ts_utc, r.run_at"),
            s.connection(), params={"p": plant_id, "a": bas, "b": bit}, parse_dates=["ts_utc", "run_at"])
        kosular = pd.read_sql(text(
            "SELECT id AS run_id, run_at, mode, model, meteo_source, kalibrasyon_id, ml_model_id, nwp_kosu_zamani, yazilim_surumu, "
            "COALESCE(etiket, meteo_ozet_json->>'etiket') AS etiket FROM forecast_runs WHERE plant_id = CAST(:p AS uuid) "
            "AND run_at >= :a - INTERVAL '20 days' AND run_at < :b"), s.connection(), params={"p": plant_id, "a": bas, "b": bit},
            parse_dates=["run_at", "nwp_kosu_zamani"])
    return df, kosular


def gecmis_olcum_oku(tenant_id, plant_id, bas: datetime, bit: datetime, geriye_gun: int = 400) -> pd.Series:
    """Referanslar için ölçülmüş saatlik seri (flag='valid'; kWh ≈ kW×1 sa), dönemden geriye_gun gün öncesinden dönem sonuna."""
    from sqlalchemy import text

    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        df = pd.read_sql(text(f"SELECT ts_utc, COALESCE(energy_kwh, power_kw) AS kwh FROM scada_hourly WHERE plant_id = CAST(:p AS uuid) AND {_ks.sql_kosulu('karne')} "
                              "AND ts_utc >= :a AND ts_utc < :b ORDER BY ts_utc"),
                         s.connection(), params={"p": plant_id, "a": bas - timedelta(days=geriye_gun), "b": bit}, parse_dates=["ts_utc"])
    if df.empty:
        return pd.Series(dtype=float)
    return df.drop_duplicates("ts_utc").set_index("ts_utc")["kwh"].astype(float)


def donem(plant: dict, gun: int, bugun: date | None = None) -> tuple[datetime, datetime, date, date]:
    """Son `gun` tam yerel gün: [bugün−gun, bugün) santral dilimi → UTC sınırlar."""
    tz = plant.get("tz") or PIYASA_TZ
    b = bugun or pd.Timestamp.now(tz=tz).date()
    bas_g, bit_g = b - timedelta(days=gun), b
    bas = pd.Timestamp(bas_g, tz=tz).tz_convert("UTC").to_pydatetime(); bit = pd.Timestamp(bit_g, tz=tz).tz_convert("UTC").to_pydatetime()
    return bas, bit, bas_g, bit_g


def hesapla(tenant_id, plant: dict, gun: int = 30, kural: str = "program", kaynak: str = "scada", bugun: date | None = None, simulasyon: bool = False) -> dict:
    from pvquant.services import olcum_uygunluk_service as ou
    bas, bit, bas_g, bit_g = donem(plant, gun, bugun)
    tahmin, kosular = tahmin_oku(tenant_id, plant["id"], bas, bit)
    saatler, dokum = ou.saat_durumlari(tenant_id, plant, bas, bit, kaynak)
    gecmis = gecmis_olcum_oku(tenant_id, plant["id"], bas, bit)
    sonuc = hesapla_saf(tahmin, saatler, dokum, plant, bas_g, bit_g, kural, kaynak, gecmis, kosular, simulasyon)
    sonuc["plant_id"] = str(plant["id"]); sonuc["santral"] = plant.get("name"); sonuc["gun"] = gun
    return sonuc


def kaydet(tenant_id, sonuc: dict, plant_id=None) -> str:
    """YALNIZ EKLEME. Simülasyon sonucu (meta.simulasyon) KAYDEDİLMEZ: dogrulama_sonuc yalnız yayımlandığı anda saklanmış tahminin sınavını tutar."""
    from sqlalchemy import text

    from pvquant.db import tenant_baglami
    m = sonuc["meta"]
    if m.get("simulasyon"):
        raise ValueError("geriye dönük simülasyon sonucu kaydedilmez (yayımlandığı anda saklanmış tahmin değil)")
    with tenant_baglami(tenant_id) as s:
        return str(s.execute(text(
            "INSERT INTO dogrulama_sonuc(tenant_id, plant_id, donem_bas, donem_bit, kural, kaynak, sozluk_surumu, metrik_json, kesit_json, referans_json, butunluk_json, meta_json) "
            "VALUES(CAST(:t AS uuid), CAST(:p AS uuid), :a, :b, :k, :kay, :sv, CAST(:m AS jsonb), CAST(:ke AS jsonb), CAST(:r AS jsonb), CAST(:bu AS jsonb), CAST(:me AS jsonb)) RETURNING id"),
            {"t": tenant_id, "p": plant_id, "a": m["donem"]["bas"], "b": m["donem"]["bit"], "k": m["kural"], "kay": m["kaynak"], "sv": m["sozluk_surumu"],
             "m": json.dumps(sonuc["metrik"], default=str), "ke": json.dumps(sonuc.get("kesit"), default=str), "r": json.dumps(sonuc.get("referans"), default=str),
             "bu": json.dumps(sonuc.get("butunluk"), default=str), "me": json.dumps(m, default=str)}).scalar())


def son(tenant_id, plant_id, kural: str = "program", gun: int = 30, azami_yas_saat: float = 36.0) -> dict | None:
    """En son kaydedilmiş sonuç (aynı kural ve dönem uzunluğu); bayatsa None."""
    from sqlalchemy import text

    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        r = s.execute(text("SELECT id, hesap_zamani, donem_bas, donem_bit, kural, kaynak, sozluk_surumu, metrik_json, kesit_json, referans_json, butunluk_json, meta_json "
                           "FROM dogrulama_sonuc WHERE plant_id = CAST(:p AS uuid) AND kural=:k AND donem_bit - donem_bas = :g "
                           "ORDER BY hesap_zamani DESC LIMIT 1"), {"p": plant_id, "k": kural, "g": gun}).mappings().first()
    if r is None:
        return None
    if (datetime.now(timezone.utc) - r["hesap_zamani"]).total_seconds() > azami_yas_saat * 3600:
        return None
    return {"id": str(r["id"]), "hesap_zamani": r["hesap_zamani"].isoformat(timespec="seconds"), "kaynak": r["kaynak"], "gun": gun,
            "metrik": r["metrik_json"], "kesit": r["kesit_json"], "referans": r["referans_json"], "butunluk": r["butunluk_json"], "meta": r["meta_json"], "kayitli": True}


def portfoy(tenant_id, plants: list[dict], gun: int = 30, kural: str = "program", bugun: date | None = None) -> dict:
    """Saatlik havuzlanmış portföy: tüm santrallerin değerlendirilebilir saatleri tek havuzda; kapasite = toplam kWp."""
    from pvquant.services import olcum_uygunluk_service as ou
    parcalar, kap, santral = [], 0.0, []
    for p in plants:
        try:
            bas, bit, bas_g, bit_g = donem(p, gun, bugun)
            tahmin, _ = tahmin_oku(tenant_id, p["id"], bas, bit)
            saatler, dokum = ou.saat_durumlari(tenant_id, p, bas, bit)
            tz = p.get("tz") or PIYASA_TZ
            e = degerlendirilebilir(eslestir(kosu_sec(tahmin, kural, tz), saatler, tz), float(p["capacity_kwp"]))
            e = e.assign(_plant=str(p["id"]))
            parcalar.append(e); kap += float(p["capacity_kwp"])
            santral.append({"plant_id": str(p["id"]), "ad": p.get("name"), "n_saat": int(len(e)), "kapsama_pct": dokum.get("kapsama_pct")})
        except Exception as ex:   # noqa: BLE001 — bir santralın hatası portföyü düşürmez, kayda geçer
            santral.append({"plant_id": str(p["id"]), "ad": p.get("name"), "hata": f"{type(ex).__name__}: {ex}"})
    e = pd.concat(parcalar, ignore_index=True) if parcalar else pd.DataFrame(columns=["y", "p50_kw", "p10_kw", "p90_kw", "gun"])
    m = metrikler(e, kap) if kap > 0 and len(e) else {"n_saat": 0, "wmape": None}
    return {"metrik": m, "kapasite_kwp": kap, "santraller": santral, "kural": kural, "gun": gun, "sozluk_surumu": SOZLUK_SURUMU,
            "kesit": {"gun": _kesit(e, kap, "gun")} if kap > 0 and len(e) >= ASGARI_SAAT else {"gun": []}}
