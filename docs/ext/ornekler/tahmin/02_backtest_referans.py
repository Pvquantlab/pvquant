"""Rolling-origin backtest: basit kt-persistans modeli vs iklimsel+persistans optimal birleşim referansı."""
import numpy as np, pandas as pd
from pvquant.ext.tahmin import backtest, referans, dogrulama
from pvquant.ext.tahmin.fizik_terimler import acik_gok

lat, lon = 37.87, 32.49; kap = 1000.0
idx = pd.date_range("2026-01-01", periods=24 * 200, freq="h", tz="UTC")
cs = acik_gok(idx, lat, lon)["ghi"]
rng = np.random.default_rng(1)
kt = pd.Series(np.clip(0.75 + 0.2 * np.sin(np.arange(len(idx)) / 240) + rng.normal(0, 0.15, len(idx)), 0.05, 1.0), index=idx)
gercek = kap * kt * cs / 1000
pers = referans.akilli_persistans(gercek, cs, cs); iklim = referans.iklimsel(gercek.loc[: idx[24 * 120]], idx)
ref, w = referans.optimal_birlesim(gercek.loc[: idx[24 * 120]], pers.loc[: idx[24 * 120]], iklim.loc[: idx[24 * 120]], pers, iklim)
print("optimal w:", w)
X = pd.DataFrame({"pers": pers, "iklim": iklim, "cs": cs}).fillna(0)
def fp(Xtr, ytr, Xte):
    A = np.c_[np.ones(len(Xtr)), Xtr.values]; b, *_ = np.linalg.lstsq(A, ytr.values, rcond=None)
    return np.clip(np.c_[np.ones(len(Xte)), Xte.values] @ b, 0, kap)
katlar = backtest.rolling_origin(X, gercek, fp, ilk_egitim_gun=90, test_gun=7, adim_gun=14)
print(backtest.kat_tablosu(katlar).round(3))
m = dogrulama.gunduz_maskesi(gercek, ref, kap)
print("referans skoru (persistansa göre):", dogrulama.deterministik(gercek, ref, kap, referans=pers, maske=m).tablo().round(4))
print(backtest.kayma_denetimi(X.iloc[: 24 * 100], X.iloc[24 * 100:]))
