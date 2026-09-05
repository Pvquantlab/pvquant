"""Sentetik 1 MWp santral: aylık IEC KPI + SFA karne satırı + belirsizlik bütçesi."""
import numpy as np, pandas as pd
from pvquant.ext.standart import belirsizlik_butcesi as bb, iec61724, sfa_metrik

idx = pd.date_range("2025-01-01", "2025-12-31 23:00", freq="h", tz="UTC"); rng = np.random.default_rng(0)
g = np.clip(np.sin((idx.hour - 6) / 12 * np.pi), 0, None) * (0.6 + 0.4 * np.sin((idx.dayofyear - 80) / 365 * 2 * np.pi))
poa = pd.Series(950 * g * rng.uniform(0.5, 1.0, len(idx)), index=idx); ta = pd.Series(12 + 12 * np.sin((idx.dayofyear - 100) / 365 * 2 * np.pi) + 6 * g, index=idx)
tc = iec61724.hucre_sicakligi_faiman(poa, ta, pd.Series(2.0, index=idx))
e = 1000 * poa / 1000 * 0.82 * (1 - 0.0035 * (tc - 25))
k = iec61724.kpi(e, poa, 1000.0, t_cell=tc); print(k[["Y_r", "Y_f", "PR", "PR_stc", "PR_yillik_agirlikli", "CF", "bayrak"]].round(3)); print(iec61724.yillik_ozet(k).round(3))
tah = e * (1 + rng.normal(0, 0.15, len(idx))); ref = e.shift(24).fillna(0)
print(sfa_metrik.karne_satiri(e, tah, 1000.0, ref))
yillik = pd.Series([1700, 1650, 1720, 1680, 1600, 1750, 1690, 1710], index=range(2017, 2025))
b = bb.butce_kur(1700, yillik, N_yil=10); print(b.tablo().round(0)); print(b.katki().round(3)); print(bb.monte_carlo(1700, b.bilesenler, N_yil=10).round(0))
