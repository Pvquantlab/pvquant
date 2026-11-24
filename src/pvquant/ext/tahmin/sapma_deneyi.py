"""G3 — Sapma katmanı deneyi (Faz 1, bulgu F1-02; 25.11.2026).

Servis edilen P50 (trend/sapma katmanı DÂHİL) ile saf fizik P50 (`physics_kw`, katman ÖNCESİ) aynı saatlerde eşli kıyaslanır.
Yöntem, Faz 1 bağımsız değerlendirmesindeki `hesap/B_04_fizik_vs_p50.py` (22.11.2026) ile birebirdir:
  * gün-bloklu eşli bootstrap — günler yeniden örneklenir (saatler içinde bağımlı), fark istatistiği
    Δ = Σ|servis − gerçek| − Σ|fizik − gerçek| / Σ gerçek × 100 (WMAPE puanı; pozitif = servis daha kötü),
  * %90 güven aralığı (5–95 yüzdelik); GA tamamen 0'ın üstündeyse «servis anlamlı KÖTÜ», altındaysa «servis anlamlı İYİ», aksi «belirsiz».
Bu modül DB/ağ/saat bilmez; yalnız sayı alır. Karar (katmanı kapat/aç) kullanıcınındır: `karar()` yalnız öneri ve gerekçe üretir;
uygulama `Settings.sapma_katmani = "kapali"` ayarıdır (kod değişikliği gerekmez). Tahmin algoritmasına dokunmaz.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

N_BOOTSTRAP = 2000
TOHUM = 7
GUVEN_YUZDELIK = (5.0, 95.0)      # %90 GA
ASGARI_GUN = 10                   # bundan az günle sonuç «yetersiz» (bootstrap anlamsız)
KOTU, IYI, BELIRSIZ, YETERSIZ = "servis anlamlı KÖTÜ", "servis anlamlı İYİ", "belirsiz", "yetersiz"


def eslesmis_bootstrap(gercek, servis, fizik, gun, n_bs: int = N_BOOTSTRAP, tohum: int = TOHUM) -> dict:
    """gercek/servis/fizik: aynı uzunlukta kW dizileri; gun: her saatin gün etiketi (blok). Döner: WMAPE'ler, fark, GA, pay, sonuç."""
    y = np.asarray(gercek, dtype=float)
    f = np.asarray(servis, dtype=float)
    p = np.asarray(fizik, dtype=float)
    if not (len(y) == len(f) == len(p) == len(gun)):
        raise ValueError("gercek, servis, fizik ve gun aynı uzunlukta olmalı")
    ok = np.isfinite(y) & np.isfinite(f) & np.isfinite(p)
    y, f, p = y[ok], f[ok], p[ok]
    g = pd.factorize(pd.Series(np.asarray(gun, dtype=object)[ok]))[0]
    n = len(y)
    n_gun = int(g.max() + 1) if n else 0
    out = {"n": n, "n_gun": n_gun, "wmape_servis": None, "wmape_fizik": None, "fark_wmape_puan": None,
           "ga_alt": None, "ga_ust": None, "sapma_degistirdi_pay": None, "sonuc": YETERSIZ,
           "isaret": "fark = servis − fizik WMAPE puanı; pozitif = servis (sapma katmanı) daha kötü"}
    payda = float(np.abs(y).sum())
    if n == 0 or payda <= 0:
        return out
    out["wmape_servis"] = float(np.abs(f - y).sum() / payda * 100)
    out["wmape_fizik"] = float(np.abs(p - y).sum() / payda * 100)
    out["fark_wmape_puan"] = out["wmape_servis"] - out["wmape_fizik"]
    out["sapma_degistirdi_pay"] = float((~np.isclose(f, p)).mean())
    if n_gun < ASGARI_GUN:
        return out
    d_ae = pd.Series(np.abs(f - y) - np.abs(p - y)).groupby(g).sum().to_numpy()
    ysum = pd.Series(np.abs(y)).groupby(g).sum().to_numpy()
    rng = np.random.default_rng(tohum)
    bs = np.empty(n_bs)
    for i in range(n_bs):
        ix = rng.integers(0, n_gun, n_gun)
        pay = ysum[ix].sum()
        bs[i] = d_ae[ix].sum() / pay * 100 if pay > 0 else np.nan
    bs = bs[np.isfinite(bs)]
    if len(bs) < n_bs // 2:
        return out
    lo, hi = np.percentile(bs, GUVEN_YUZDELIK)
    out["ga_alt"], out["ga_ust"] = float(lo), float(hi)
    out["sonuc"] = KOTU if lo > 0 else (IYI if hi < 0 else BELIRSIZ)
    return out


def deney_tablosu(e: pd.DataFrame, grup: str = "kova", servis: str = "p50_kw", fizik: str = "physics_kw", gercek: str = "y",
                  gun: str = "gun", **bs_args) -> pd.DataFrame:
    """e: değerlendirilebilir saat satırları (bagimsiz_dogrulama_service.degerlendirilebilir çıktısı gibi: y, p50_kw, physics_kw, gun, kova).
    Her grup için bir satır + «tum» satırı."""
    satirlar = []
    gruplar = [(k, g) for k, g in e.groupby(grup, sort=False)] if grup in e.columns else []
    for ad, g in [*gruplar, ("tum", e)]:
        if g.empty:
            continue
        r = eslesmis_bootstrap(g[gercek], g[servis], g[fizik], g[gun], **bs_args)
        satirlar.append({grup: str(ad), **{k: v for k, v in r.items() if k != "isaret"}})
    return pd.DataFrame(satirlar)


def karar(tablo: pd.DataFrame) -> dict:
    """Tablodan öneri: herhangi bir kovada servis anlamlı İYİ ise katman kalır («otomatik»); hiç İYİ yok ve ≥1 KÖTÜ ise «kapali» önerilir;
    aksi «belirsiz». Yalnız öneri — uygulama kullanıcı onayıyla ayar değişikliğidir."""
    if tablo is None or tablo.empty or "sonuc" not in tablo.columns:
        return {"oneri": "belirsiz", "gerekce": "tablo boş", "kotu": 0, "iyi": 0, "belirsiz": 0, "yetersiz": 0}
    t = tablo[tablo.iloc[:, 0].astype(str) != "tum"] if len(tablo) > 1 else tablo
    say = {k: int((t["sonuc"] == v).sum()) for k, v in (("kotu", KOTU), ("iyi", IYI), ("belirsiz", BELIRSIZ), ("yetersiz", YETERSIZ))}
    if say["iyi"] > 0:
        oneri, gerekce = "otomatik", f"{say['iyi']} kovada servis anlamlı iyi → katman kalsın"
    elif say["kotu"] > 0:
        oneri, gerekce = "kapali", f"{say['kotu']} kovada servis anlamlı kötü, hiçbirinde anlamlı iyi değil → katmanı kapatmak önerilir"
    else:
        oneri, gerekce = "belirsiz", "hiçbir kovada anlamlı fark yok → mevcut ayar korunur, deney sürer"
    return {"oneri": oneri, "gerekce": gerekce, **say}


def markdown(tablo: pd.DataFrame, grup: str = "kova") -> str:
    """Rapor satırları (sayı uydurulmaz: None → «—»)."""
    def _f(v, b="{:.1f}"):
        return "—" if v is None or (isinstance(v, float) and not np.isfinite(v)) else b.format(v)
    sat = [f"| {grup} | n / gün | WMAPE servis | WMAPE fizik | Fark (puan) | GA %90 | Sapma değiştirdi | Sonuç |", "|---|---|---|---|---|---|---|---|"]
    for _, r in tablo.iterrows():
        ga = "—" if r["ga_alt"] is None else f"[{r['ga_alt']:+.2f}, {r['ga_ust']:+.2f}]"
        pay = "—" if r["sapma_degistirdi_pay"] is None else f"%{r['sapma_degistirdi_pay'] * 100:.0f}"
        sat.append(f"| {r[grup]} | {int(r['n'])} / {int(r['n_gun'])} | {_f(r['wmape_servis'])} | {_f(r['wmape_fizik'])} | "
                   f"{_f(r['fark_wmape_puan'], '{:+.2f}')} | {ga} | {pay} | {r['sonuc']} |")
    return "\n".join(sat)
