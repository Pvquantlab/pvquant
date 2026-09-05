"""10 MW GES, Temmuz 2025 fiyat seviyesi (PTF≈2.982, SMF≈3.038): naif vs PVQuant programı, aylık TL ve kurtarılan."""
import numpy as np, pandas as pd
from pvquant.ext.turkiye import dengesizlik as d, kgup, segment
rng = np.random.default_rng(0)
idx = pd.date_range("2025-07-01", "2025-07-31 23:00", freq="h", tz="Europe/Istanbul").tz_convert("UTC")
g = np.clip(np.sin((idx.tz_convert("Europe/Istanbul").hour - 6) / 12 * np.pi), 0, None)
gercek = pd.Series(10 * g * rng.uniform(0.5, 1.0, len(idx)), index=idx)
naif = gercek.shift(24).fillna(gercek.mean() * g)                    # dün-aynı-saat
pvq = gercek * (1 + rng.normal(0, 0.08, len(idx)))                    # %8 saatlik hata
ptf = pd.Series(2982.0 * (0.8 + 0.4 * g), index=idx); smf = d.senaryo_spread(ptf, 0.2)
print(d.kiyas(naif, pvq, gercek, ptf, smf).round(0))
s = d.saatlik(pvq, gercek, ptf, smf); print(d.aylik_karne(s).round(3).T); print("teminat ≈", round(d.teminat(s)))
print("optimal teklif kantili:", round(d.optimal_teklif_kantili(2982, 3400, 2500), 3))
st = segment.Santral("Konya-1", segment.Segment.LISANSLI_SERBEST, 10.0)
print(segment.gelir(st, gercek, ptf)["gelir_tl"].sum().round(), "TL brüt; dengesizlik santralde:", st.dengesizlik_tasir_mi())
son = kgup.program_uret(pvq, "2025-07-15", "UEVCB-001", 10.0)
print(kgup.dogrula(son, 10.0), son.sicrama_saatleri, kgup.teslim_durumu(pd.Timestamp("2025-07-14 15:05", tz="Europe/Istanbul")))
