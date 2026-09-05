"""Sentetik P10/P50/P90 + gerçekleşen → karne satırı, reliability, PIT; sonra CQR ile düzeltip yeniden ölç."""
import numpy as np, pandas as pd
from pvquant.ext.tahmin import dogrulama, konformal

rng = np.random.default_rng(0); n = 24 * 60; kap = 1000.0
idx = pd.date_range("2026-05-01", periods=n, freq="h", tz="UTC")
gunes = np.clip(np.sin((idx.hour - 6) / 12 * np.pi), 0, None)
p50 = pd.Series(kap * 0.7 * gunes, index=idx)
gercek = p50 * (1 + rng.normal(0, 0.25, n)) * (gunes > 0)
q = pd.DataFrame({"p10": p50 * 0.9, "p50": p50, "p90": p50 * 1.1})   # bilerek dar bant (underdispersed)
m = dogrulama.gunduz_maskesi(gercek, p50, kap)
print("önce:\n", dogrulama.olasiliksal_ozet(gercek[m], q[m], kap).round(4))
print(dogrulama.reliability(gercek[m], q[m]))
kal = idx[: n // 2]; test = idx[n // 2:]
c = konformal.CQR(alpha=0.2, grup="saat").kalibre_et(gercek[kal][m[kal]], q.loc[kal, "p10"], q.loc[kal, "p90"])
a, u = c.uygula(q.loc[test, "p10"], q.loc[test, "p90"], tavan=kap)
q2 = pd.DataFrame({"p10": a, "p50": q.loc[test, "p50"], "p90": u})
print("sonra (test):\n", dogrulama.olasiliksal_ozet(gercek[test][m[test]], q2[m[test]], kap).round(4))
