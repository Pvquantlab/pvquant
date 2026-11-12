"""v2.589 (Faz 3 F3-B) — PORTFÖY TAHMİNİ VE BELİRSİZLİĞİ (saf; DB yok).

Neden: portföy P10/P90'ı santral P10/P90'larını toplayarak kurulamaz — santral hataları tam bağımlı değildir; naif toplam bandı şişirir,
bağımsız varsayım daraltır. Santral marjinalleri (konformal kalibre bant) KORUNUR; santraller arası bağımlılık geçmiş artıklardan büzülmüş
korelasyon matrisiyle (Schäfer–Strimmer, `ext/tahmin/portfoy._buzulmus_kov`) alınır.

Saatlik: her santral için iki yönlü yarı genişlik σᵢ⁻ = P50−P10, σᵢ⁺ = P90−P50; portföy σₚ² = Σᵢⱼ ρᵢⱼ σᵢ σⱼ (her yön ayrı);
P10 = ΣP50 − σₚ⁻, P90 = ΣP50 + σₚ⁺; [0, Σ kapasite] kırpma. Yanında iki sınır: tam bağımlı (naif toplam, ρ=1) ve bağımsız (ρ=I).
ρ için en az MIN_GUN ortak gün yoksa ρ=1 (ihtiyatlı) ve durum «yetersiz_veri». Merkez (P50) her zaman bottom-up toplam; MinT'e dokunulmaz.
Gün/dönem: saatler arası bağımlılık için günlük portföy artık toplamlarının ampirik kantili (gün bloğu); çok günlük dönem için gün bloğu
bootstrap. Yeterli gün yoksa naif toplam + «doğrulanmadı».
Doğrulama: portföy toplamının PICP80 / P(y<P10) / P(y>P90) / Winkler sınavı (son DOGRULAMA_GUN gün); PICP80 ∈ [70, 90] ve yeterli gün →
«doğrulandı», aksi «doğrulanmadı». Doğrulanmamış bant hiçbir yüzeyde «istatistiksel olarak güvenilir» diye sunulmaz.
Eksik saat/santral 0 sayılmaz: NaN kalır ve listelenir."""
from __future__ import annotations

from pvquant.zaman import PIYASA_TZ

import numpy as np
import pandas as pd

from pvquant.ext.tahmin.dogrulama import aralik_skoru, picp
from pvquant.ext.tahmin.portfoy import _buzulmus_kov

YONTEM_SURUMU = "2026-11-11"
MIN_GUN = 14            # ρ ve günlük ampirik kantil için en az ortak gün
DOGRULAMA_GUN = 30      # «doğrulandı» için en az gün
PICP_ARALIK = (70.0, 90.0)
GUNDUZ_ORAN = 0.02
TAM_GUN_SAAT = 20
BOOT_REPS = 2000
BOLGE_ESIK_KM = 50.0
DURUM_AD = {"dogrulandi": "Doğrulandı", "dogrulanmadi": "Doğrulanmadı", "yetersiz_veri": "Yetersiz veri"}
DURUM_ACIKLAMA = {
    "dogrulandi": "Belirsizlik aralığı son dönem gerçekleşmeleriyle sınandı; 10 günden 8'inde gerçekleşen üretim aralığın içinde kaldı.",
    "dogrulanmadi": "Belirsizlik aralığı istatistiksel olarak doğrulanmadı; karar verirken aralığı yaklaşık kabul edin.",
    "yetersiz_veri": "Santraller arası bağımlılık için yeterli ortak geçmiş yok; aralık ihtiyatlı (tam bağımlı) varsayımla verildi ve doğrulanmadı.",
}
KORELASYON_YONTEMI = "Schäfer–Strimmer büzülmüş korelasyon (geçmiş saatlik artıklar, gündüz)"


# ---------------------------------------------------------------- hizalama
def hizala(tahminler: dict[str, pd.DataFrame]) -> dict:
    """tahminler: ad → DataFrame (indeks ts_utc, tz'li; kolonlar p50, p10, p90; kW). Ortak saat kümesi = kesişim; santral başına kesişim dışı
    saat sayısı `eksik_saat`. Tahmini olmayan (None/boş) santral `tahmin_yok` listesine düşer, kesişime girmez."""
    adlar = []; yok = []
    for ad, df in tahminler.items():
        if df is None or df.empty or "p50" not in df.columns:
            yok.append(ad)
        else:
            adlar.append(ad)
    if not adlar:
        bos = pd.DataFrame()
        return {"idx": pd.DatetimeIndex([], tz="UTC"), "santral": [], "tahmin_yok": yok, "eksik_saat": {}, "p50": bos, "p10": bos, "p90": bos}
    idx = None
    for ad in adlar:
        i = pd.DatetimeIndex(tahminler[ad].index)
        i = i.tz_localize("UTC") if i.tz is None else i.tz_convert("UTC")
        idx = i if idx is None else idx.intersection(i)
    idx = idx.sort_values()
    out = {"idx": idx, "santral": adlar, "tahmin_yok": yok, "eksik_saat": {}}
    for kol in ("p50", "p10", "p90"):
        cols = {}
        for ad in adlar:
            df = tahminler[ad]
            i = pd.DatetimeIndex(df.index); i = i.tz_localize("UTC") if i.tz is None else i.tz_convert("UTC")
            s = pd.Series(pd.to_numeric(df[kol], errors="coerce").values if kol in df.columns else np.nan, index=i)
            s = s[~s.index.duplicated(keep="last")]
            cols[ad] = s.reindex(idx)
        out[kol] = pd.DataFrame(cols, index=idx)
    for ad in adlar:
        out["eksik_saat"][ad] = int(len(pd.DatetimeIndex(tahminler[ad].index)) - len(idx))
    return out


# ---------------------------------------------------------------- korelasyon
def korelasyon(artiklar: pd.DataFrame | None, min_gun: int = MIN_GUN) -> dict:
    """artiklar: ts_utc × ad, saatlik artık (tahmin − gerçek, kW; gece/eksik NaN). Yalnız bütün santrallerin dolu olduğu saatler kullanılır.
    En az `min_gun` ortak gün ve ≥ 2 santral yoksa ρ = 1 (tam bağımlı, ihtiyatlı) ve durum «yetersiz_veri»."""
    if artiklar is None or artiklar.empty or artiklar.shape[1] == 0:
        return {"rho": None, "n_gun": 0, "n_saat": 0, "durum": "yetersiz_veri", "yontem": KORELASYON_YONTEMI, "lam": None}
    adlar = list(artiklar.columns)
    E = artiklar.dropna()
    idx = pd.DatetimeIndex(E.index)
    n_gun = int(pd.Series(idx.tz_convert("UTC").date if idx.tz is not None else idx.date).nunique()) if len(E) else 0
    if len(adlar) < 2:
        return {"rho": pd.DataFrame(np.eye(1), index=adlar, columns=adlar), "n_gun": n_gun, "n_saat": int(len(E)), "durum": "tek_santral", "yontem": KORELASYON_YONTEMI, "lam": None}
    if n_gun < min_gun or len(E) < 3 * len(adlar):
        return {"rho": pd.DataFrame(np.ones((len(adlar), len(adlar))), index=adlar, columns=adlar), "n_gun": n_gun, "n_saat": int(len(E)),
                "durum": "yetersiz_veri", "yontem": KORELASYON_YONTEMI, "lam": None}
    W = _buzulmus_kov(E.values.astype(float))
    sd = np.sqrt(np.clip(np.diag(W), 0, None))
    with np.errstate(divide="ignore", invalid="ignore"):
        R = W / np.outer(sd, sd)
    R = np.where(np.isfinite(R), R, 0.0)
    R = np.clip(R, -1.0, 1.0); np.fill_diagonal(R, 1.0)
    return {"rho": pd.DataFrame(R, index=adlar, columns=adlar), "n_gun": n_gun, "n_saat": int(len(E)), "durum": "yeterli", "yontem": KORELASYON_YONTEMI,
            "lam": None}


def _birlesik(S: pd.DataFrame, R: np.ndarray) -> pd.Series:
    """σₚ = sqrt(sᵀ R s) satır satır; herhangi bir santral NaN ise NaN (eksik 0 sayılmaz)."""
    A = S.values.astype(float)
    var = np.einsum("ti,ij,tj->t", np.nan_to_num(A), R, np.nan_to_num(A))
    out = np.sqrt(np.clip(var, 0.0, None))
    out[np.isnan(A).any(axis=1)] = np.nan
    return pd.Series(out, index=S.index)


# ---------------------------------------------------------------- saatlik bant
def saatlik_bant(h: dict, rho: pd.DataFrame | None, kapasiteler: dict[str, float]) -> pd.DataFrame:
    """h: `hizala` çıktısı. Döner (indeks ts_utc): p50, p10, p90 (ρ ile), p10_naif/p90_naif (tam bağımlı), p10_bagimsiz/p90_bagimsiz (ρ=I),
    sigma_alt/sigma_ust, eksik (bool), {ad}__p50 katkıları. Kapasite tavanı Σ kapasite; taban 0."""
    adlar = h["santral"]
    if not adlar:
        return pd.DataFrame(columns=["p50", "p10", "p90", "p10_naif", "p90_naif", "p10_bagimsiz", "p90_bagimsiz", "sigma_alt", "sigma_ust", "eksik"])
    P50, P10, P90 = h["p50"][adlar], h["p10"][adlar], h["p90"][adlar]
    kap = float(sum(float(kapasiteler.get(ad, 0.0) or 0.0) for ad in adlar))
    n = len(adlar)
    R = rho.reindex(index=adlar, columns=adlar).values.astype(float) if rho is not None else np.ones((n, n))
    R = np.where(np.isfinite(R), R, 1.0)
    s_alt = (P50 - P10).clip(lower=0.0); s_ust = (P90 - P50).clip(lower=0.0)
    p50 = P50.sum(axis=1, skipna=False)
    out = pd.DataFrame(index=h["idx"])
    out["p50"] = p50
    out["sigma_alt"] = _birlesik(s_alt, R); out["sigma_ust"] = _birlesik(s_ust, R)
    out["p10"] = (p50 - out["sigma_alt"]).clip(lower=0.0)
    out["p90"] = (p50 + out["sigma_ust"]).clip(upper=kap) if kap > 0 else p50 + out["sigma_ust"]
    out["p10_naif"] = P10.sum(axis=1, skipna=False).clip(lower=0.0)
    out["p90_naif"] = P90.sum(axis=1, skipna=False).clip(upper=kap) if kap > 0 else P90.sum(axis=1, skipna=False)
    out["p10_bagimsiz"] = (p50 - _birlesik(s_alt, np.eye(n))).clip(lower=0.0)
    out["p90_bagimsiz"] = (p50 + _birlesik(s_ust, np.eye(n))).clip(upper=kap) if kap > 0 else p50 + _birlesik(s_ust, np.eye(n))
    out["eksik"] = P50.isna().any(axis=1) | P10.isna().any(axis=1) | P90.isna().any(axis=1)
    for ad in adlar:
        out[f"{ad}__p50"] = P50[ad]
    return out


# ---------------------------------------------------------------- gün ve dönem
def gunluk_artiklar(artiklar: pd.DataFrame, tz: str, tam_gun_saat: int = 1) -> pd.Series:
    """Günlük portföy artığı (kWh): bütün santrallerin dolu olduğu saatlerde Σ santral artığı, yerel güne göre toplanır.
    Gündüz artıkları zaten NaN'siz; bir günde en az `tam_gun_saat` ortak saat yoksa gün düşer."""
    if artiklar is None or artiklar.empty:
        return pd.Series(dtype=float)
    E = artiklar.dropna()
    if E.empty:
        return pd.Series(dtype=float)
    idx = pd.DatetimeIndex(E.index); idx = idx.tz_localize("UTC") if idx.tz is None else idx
    g = E.sum(axis=1).groupby(idx.tz_convert(tz).date)
    say = g.size()
    return g.sum()[say >= tam_gun_saat].astype(float)


def gunluk(saatlik: pd.DataFrame, tz: str, gunluk_artik: pd.Series | None, min_gun: int = MIN_GUN, tam_gun_saat: int = TAM_GUN_SAAT) -> tuple[pd.DataFrame, dict]:
    """Günlük MWh beklentisi: p50 = Σ saat / 1000 (yalnız ≥ tam_gun_saat saati olan ve eksiksiz günler). Bant: günlük portföy artığının (tahmin − gerçek)
    ampirik kantili — y = p50 − e → P10 = p50 − q90(e), P90 = p50 − q10(e); ≥ min_gun gün yoksa naif toplam (Σ saatlik p10/p90) ve «dogrulanmadi»."""
    if saatlik is None or saatlik.empty:
        return pd.DataFrame(columns=["p50_mwh", "p10_mwh", "p90_mwh", "p10_naif_mwh", "p90_naif_mwh", "saat"]), {"yontem": None, "durum": "yetersiz_veri", "n_gun": 0}
    idx = pd.DatetimeIndex(saatlik.index).tz_convert(tz)
    gr = saatlik.assign(_g=idx.date).groupby("_g")
    say = gr.size()
    g = pd.DataFrame({"p50_mwh": gr["p50"].sum(min_count=1) / 1000.0, "p10_naif_mwh": gr["p10_naif"].sum(min_count=1) / 1000.0,
                      "p90_naif_mwh": gr["p90_naif"].sum(min_count=1) / 1000.0, "saat": say, "eksik": gr["eksik"].any()})
    g = g[(g["saat"] >= tam_gun_saat) & ~g["eksik"]].drop(columns=["eksik"])
    ga = gunluk_artik.dropna() if gunluk_artik is not None else pd.Series(dtype=float)
    if len(ga) >= min_gun:
        q10, q90 = float(np.quantile(ga.values, 0.10)), float(np.quantile(ga.values, 0.90))
        g["p10_mwh"] = (g["p50_mwh"] - q90 / 1000.0).clip(lower=0.0); g["p90_mwh"] = g["p50_mwh"] - q10 / 1000.0
        meta = {"yontem": "günlük portföy artığının ampirik kantili (gün bloğu)", "durum": "ampirik", "n_gun": int(len(ga)), "q10_kwh": round(q10, 1), "q90_kwh": round(q90, 1)}
    else:
        g["p10_mwh"] = g["p10_naif_mwh"]; g["p90_mwh"] = g["p90_naif_mwh"]
        meta = {"yontem": "naif toplam (saatlik P10/P90 toplamı; saatler ve santraller tam bağımlı varsayıldı)", "durum": "yetersiz_veri", "n_gun": int(len(ga))}
    g["p10_mwh"] = np.minimum(g["p10_mwh"], g["p50_mwh"]); g["p90_mwh"] = np.maximum(g["p90_mwh"], g["p50_mwh"])
    return g[["p50_mwh", "p10_mwh", "p90_mwh", "p10_naif_mwh", "p90_naif_mwh", "saat"]], meta


def donem_bandi(gunluk_artik: pd.Series | None, n_gun: int, reps: int = BOOT_REPS, seed: int = 0, min_gun: int = MIN_GUN) -> dict | None:
    """Çok günlük dönem (hafta=7, ay=30…) için gün bloğu bootstrap: n_gun günlük artık, yerine koyarak `reps` kez örneklenir, toplamın q10/q90'ı (kWh).
    Dönem P10 = Σp50 − q90, P90 = Σp50 − q10. Yetersiz gün → None (uydurulmaz)."""
    ga = gunluk_artik.dropna() if gunluk_artik is not None else pd.Series(dtype=float)
    if len(ga) < min_gun or n_gun < 1:
        return None
    rng = np.random.default_rng(seed)
    top = rng.choice(ga.values, size=(reps, n_gun), replace=True).sum(axis=1)
    return {"n_gun": int(n_gun), "ornek_gun": int(len(ga)), "reps": int(reps), "q10_kwh": float(np.quantile(top, 0.10)), "q90_kwh": float(np.quantile(top, 0.90)),
            "yontem": "gün bloğu bootstrap (günlük portföy artıkları)"}


# ---------------------------------------------------------------- kapsama sınavı
def kapsama_sinavi(e: pd.DataFrame, kapasite: float, min_gun: int = DOGRULAMA_GUN, tz: str = "UTC") -> dict:
    """e: indeks ts_utc; kolonlar y, p50, p10, p90 (portföy toplamı, kW). Gündüz: y ya da p50 > GUNDUZ_ORAN × kapasite. PICP80 (%), P(y<P10), P(y>P90),
    bant genişliği / kapasite (%), Winkler (kW). Durum: yetersiz_veri (< min_gun gün) | dogrulandi (PICP80 ∈ PICP_ARALIK) | dogrulanmadi."""
    if e is None or e.empty:
        return {"n_saat": 0, "n_gun": 0, "picp80": None, "p10_alti": None, "p90_ustu": None, "bant_genisligi_oran": None, "winkler_kw": None, "durum": "yetersiz_veri",
                "durum_ad": DURUM_AD["yetersiz_veri"], "aciklama": DURUM_ACIKLAMA["yetersiz_veri"], "hedef_picp": 80.0, "kabul_araligi": list(PICP_ARALIK)}
    d = e.dropna(subset=["y", "p50", "p10", "p90"]).copy()
    kap = float(kapasite)
    d = d[(d["y"] > GUNDUZ_ORAN * kap) | (d["p50"] > GUNDUZ_ORAN * kap)] if kap > 0 else d
    idx = pd.DatetimeIndex(d.index)
    n_gun = int(pd.Series(idx.tz_convert(tz).date).nunique()) if len(d) and idx.tz is not None else int(pd.Series(idx.date).nunique()) if len(d) else 0
    out = {"n_saat": int(len(d)), "n_gun": n_gun, "hedef_picp": 80.0, "kabul_araligi": list(PICP_ARALIK)}
    if len(d) < 3:
        out.update({"picp80": None, "p10_alti": None, "p90_ustu": None, "bant_genisligi_oran": None, "winkler_kw": None, "durum": "yetersiz_veri"})
    else:
        y, lo, hi = d["y"].astype(float), d["p10"].astype(float), d["p90"].astype(float)
        out["picp80"] = round(picp(y, lo, hi) * 100, 1)
        out["p10_alti"] = round(float((y < lo).mean()) * 100, 1); out["p90_ustu"] = round(float((y > hi).mean()) * 100, 1)
        out["bant_genisligi_oran"] = round(float((hi - lo).mean()) / kap * 100, 1) if kap > 0 else None
        out["winkler_kw"] = round(aralik_skoru(y, lo, hi, 0.2), 1)
        if n_gun < min_gun:
            out["durum"] = "yetersiz_veri"
        else:
            out["durum"] = "dogrulandi" if PICP_ARALIK[0] <= out["picp80"] <= PICP_ARALIK[1] else "dogrulanmadi"
    out["durum_ad"] = DURUM_AD[out["durum"]]; out["aciklama"] = DURUM_ACIKLAMA[out["durum"]]
    return out


# ---------------------------------------------------------------- bölge göstergesi (bilgi)
def _haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    la1, lo1, la2, lo2 = map(np.radians, (a[0], a[1], b[0], b[1]))
    h = np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2
    return float(2 * 6371.0 * np.arcsin(np.sqrt(h)))


def bolge_gostergesi(koordinatlar: dict[str, tuple[float, float]], esik_km: float = BOLGE_ESIK_KM) -> dict:
    """Koordinat yakınlığına göre «aynı meteoroloji bölgesi» göstergesi (yalnız bilgi; hesap ρ'yu kullanır). `esik_km` içindekiler aynı bölgede (bağlı bileşen)."""
    adlar = list(koordinatlar)
    ebeveyn = list(range(len(adlar)))

    def kok(i: int) -> int:
        while ebeveyn[i] != i:
            ebeveyn[i] = ebeveyn[ebeveyn[i]]; i = ebeveyn[i]
        return i
    ciftler = []
    for i, a in enumerate(adlar):
        for j in range(i + 1, len(adlar)):
            km = _haversine_km(koordinatlar[a], koordinatlar[adlar[j]])
            ciftler.append({"a": a, "b": adlar[j], "km": round(km, 1), "ayni_bolge": bool(km <= esik_km)})
            if km <= esik_km:
                ebeveyn[kok(j)] = kok(i)
    gruplar: dict[int, list[str]] = {}
    for i, ad in enumerate(adlar):
        gruplar.setdefault(kok(i), []).append(ad)
    return {"esik_km": esik_km, "ciftler": ciftler, "bolgeler": list(gruplar.values()), "bolge_sayisi": len(gruplar)}


# ---------------------------------------------------------------- birleşik özet (saf)
def portfoy_tahmini(tahminler: dict[str, pd.DataFrame], kapasiteler: dict[str, float], artiklar: pd.DataFrame | None, tz: str = PIYASA_TZ,
                    koordinatlar: dict[str, tuple[float, float]] | None = None, kapsama: dict | None = None) -> dict:
    """Saf uçtan uca: hizala → ρ → saatlik bant → günlük → durum. `kapsama` (önceki sınav sonucu) verilirse belirsizlik durumu ondan alınır;
    verilmezse ρ yeterliyse «dogrulanmadi», değilse «yetersiz_veri»."""
    h = hizala(tahminler)
    ko = korelasyon(artiklar)
    saatlik = saatlik_bant(h, ko["rho"], kapasiteler)
    ga = gunluk_artiklar(artiklar, tz) if artiklar is not None else pd.Series(dtype=float)
    g, g_meta = gunluk(saatlik, tz, ga)
    if kapsama and kapsama.get("durum"):
        durum = kapsama["durum"]
    else:
        durum = "yetersiz_veri" if ko["durum"] in ("yetersiz_veri",) else "dogrulanmadi"
    if len(h["santral"]) == 1:
        durum = kapsama["durum"] if kapsama and kapsama.get("durum") else "dogrulanmadi"
    return {"saatlik": saatlik, "gunluk": g, "gunluk_meta": g_meta, "korelasyon": ko, "hizalama": {"santral": h["santral"], "tahmin_yok": h["tahmin_yok"], "eksik_saat": h["eksik_saat"], "n_saat": int(len(h["idx"]))},
            "bolge": bolge_gostergesi(koordinatlar) if koordinatlar and len(koordinatlar) > 1 else None,
            "kapasite_kwp": float(sum(float(kapasiteler.get(a, 0.0) or 0.0) for a in h["santral"])),
            "belirsizlik": {"durum": durum, "durum_ad": DURUM_AD[durum], "aciklama": DURUM_ACIKLAMA[durum], "rho_durum": ko["durum"], "rho_n_gun": ko["n_gun"]},
            "yontem": {"surum": YONTEM_SURUMU, "merkez": "bottom-up Σ P50 (santral tahminleri değişmez)",
                       "bant": "santral yarı genişlikleri × büzülmüş korelasyon; yanında tam bağımlı (naif) ve bağımsız sınırlar", "gun": g_meta.get("yontem")}}
