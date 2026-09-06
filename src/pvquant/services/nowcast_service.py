"""v2.266 — Dalga 5.18: kısa ufuk (0–6 saat) — ölçüm persistansı, uydu DEĞİL.

Gerçek uydu bulut-hareket nowcast'ı (EUMETSAT gerçek zamanlı lisans + işlem altyapısı) bu dalgada yok; bunun
yerine pvquant.ext.kaynak.nowcast'ın rampalı harman matematiği GÜÇ uzayında uygulanır: son 3 saatin
ölçülen/tahmin oranı (r) ileri taşınır, ufuk h için w(h)=exp(-h/τ) ağırlığıyla P50'ye harmanlanır
(τ=2 s; ötesi P50). Koşul: SCADA tazeliği ≤ 3 saat — dosya yüklemeli santralde bu katman dürüstçe "—" der.
Model çekirdeğine dokunmaz; yalnız sunum katmanı, kayıt yazmaz.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

TAU_SAAT = 2.0
UFUK_SAAT = 6
TAZELIK_SINIRI_SAAT = 3.0
PENCERE_SAAT = 3
ORAN_SINIR = (0.2, 1.8)   # aşırı oranlar (sensör/kesinti) persistansa alınmaz


def rampali_persistans_guc(gercek: pd.Series, p50: pd.Series, simdi: pd.Timestamp | None = None,
                           tau_saat: float = TAU_SAAT, ufuk_saat: int = UFUK_SAAT, pencere_saat: int = PENCERE_SAAT) -> dict:
    """SAF. gercek/p50: UTC saatlik kW. Döner {oran, n_saat, ufuk:[{ts, p50_kw, nowcast_kw, agirlik}], durum}.
    Oran son `pencere_saat` saatte p50>0 olan saatlerin ölçüm/tahmin ortalamasıdır; yoksa (gece) durum='gece' ve
    nowcast=P50 (ağırlık 0 — uydurma yok)."""
    g = gercek.dropna()
    if g.empty:
        return {"durum": "olcum_yok", "oran": None, "n_saat": 0, "ufuk": []}
    simdi = pd.Timestamp(simdi or g.index[-1])
    simdi = simdi.tz_localize("UTC") if simdi.tz is None else simdi.tz_convert("UTC")
    ix = p50.index.tz_localize("UTC") if p50.index.tz is None else p50.index.tz_convert("UTC")
    p = pd.Series(p50.values, index=ix).astype(float)
    gix = g.index.tz_localize("UTC") if g.index.tz is None else g.index.tz_convert("UTC")
    g = pd.Series(g.values, index=gix).astype(float)
    son = g[(g.index > simdi - pd.Timedelta(hours=pencere_saat)) & (g.index <= simdi)]
    ortak = son.index.intersection(p.index)
    ref = p.loc[ortak]; olc = son.loc[ortak]
    m = ref > 0
    oranlar = (olc[m] / ref[m]).clip(*ORAN_SINIR) if m.any() else pd.Series(dtype=float)
    hedef = p.index[(p.index > simdi) & (p.index <= simdi + pd.Timedelta(hours=ufuk_saat))]
    if len(hedef) == 0:
        return {"durum": "tahmin_yok", "oran": None, "n_saat": int(len(oranlar)), "ufuk": []}
    if oranlar.empty:
        return {"durum": "gece", "oran": None, "n_saat": 0,
                "ufuk": [{"ts": t.isoformat(), "p50_kw": round(float(p[t]), 1), "nowcast_kw": round(float(p[t]), 1), "agirlik": 0.0} for t in hedef]}
    r = float(oranlar.mean())
    h = ((hedef - simdi) / pd.Timedelta(hours=1)).astype(float)
    w = np.exp(-np.asarray(h) / tau_saat)
    nc = w * r * p.loc[hedef].values + (1.0 - w) * p.loc[hedef].values
    return {"durum": "ok", "oran": round(r, 3), "n_saat": int(len(oranlar)),
            "ufuk": [{"ts": t.isoformat(), "p50_kw": round(float(p[t]), 1), "nowcast_kw": round(float(v), 1), "agirlik": round(float(a), 3)}
                     for t, v, a in zip(hedef, nc, w)]}


def hesapla(tenant_id, plant: dict, simdi: pd.Timestamp | None = None) -> dict:
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    from pvquant.services import forecast_service
    pid = plant["id"]
    simdi = pd.Timestamp(simdi or pd.Timestamp.now(tz="UTC")).tz_convert("UTC")
    with tenant_baglami(tenant_id) as s:
        g = pd.read_sql(text("SELECT ts_utc, power_kw FROM scada_hourly WHERE plant_id=:p AND flag='valid' "
                             "AND ts_utc >= :a ORDER BY ts_utc"),
                        s.connection(), params={"p": pid, "a": simdi - pd.Timedelta(hours=PENCERE_SAAT + 1)},
                        index_col="ts_utc", parse_dates=["ts_utc"])
        son = s.execute(text("SELECT max(ts_utc) FROM scada_hourly WHERE plant_id=:p AND flag='valid'"), {"p": pid}).scalar()
    ortak = {"uydu": False, "yontem": "ölçüm persistansı (rampalı harman, τ=2 s)", "ufuk_saat": UFUK_SAAT,
             "son_olcum": son.isoformat() if son is not None else None,
             "tazelik_saat": round(float((simdi - pd.Timestamp(son).tz_convert("UTC")).total_seconds() / 3600), 1) if son is not None else None}
    if son is None or ortak["tazelik_saat"] > TAZELIK_SINIRI_SAAT:
        return {**ortak, "durum": "scada_bayat", "oran": None, "n_saat": 0, "ufuk": [],
                "not": "canlı SCADA gerektirir — son ölçüm 3 saatten eski; katman devre dışı"}
    df = forecast_service.son_kosu(tenant_id, pid)
    if df is None or df.empty:
        return {**ortak, "durum": "tahmin_yok", "oran": None, "n_saat": 0, "ufuk": [], "not": "koşu yok"}
    gi = g.index.tz_localize("UTC") if g.index.tz is None else g.index
    r = rampali_persistans_guc(pd.Series(g["power_kw"].values, index=gi), df["p50_kw"], simdi)
    return {**ortak, **r}
