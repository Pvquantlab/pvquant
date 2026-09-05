"""EPİAŞ Şeffaflık: PTF/SMF çek ve örnek dengesizlik maliyeti. EPIAS_KULLANICI/EPIAS_SIFRE gerekir."""
import numpy as np, pandas as pd
from pvquant.ext.kaynak import epias

c = epias.SeffaflikIstemci()
ptf = c.ptf("2025-07-01", "2025-07-07"); smf = c.smf("2025-07-01", "2025-07-07")
print(ptf.head()); print(smf.head())
# sentetik 10 MW santral: KGÜP vs gerçekleşen
idx = pd.date_range("2025-07-01", periods=24 * 7, freq="h", tz="Europe/Istanbul")
kgup = pd.Series(np.clip(8 * np.sin((idx.hour - 6) / 12 * np.pi), 0, None), index=idx)
gercek = kgup * (1 + 0.1 * np.random.default_rng(1).standard_normal(len(idx)))
p = pd.Series(2650.0, index=idx); s = pd.Series(2500.0, index=idx)
print(epias.dengesizlik_maliyeti(kgup, gercek, p, s)["maliyet_tl"].sum().round())
