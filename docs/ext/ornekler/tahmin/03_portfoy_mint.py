"""Üç santral + iki bölge + toplam: bağımsız tahminleri MinT ile tutarlı hale getir."""
import numpy as np, pandas as pd
from pvquant.ext.tahmin import portfoy

taban = ["S1", "S2", "S3"]; hiy = {"Toplam": taban, "Konya": ["S1", "S2"], "Adana": ["S3"]}
S, dug = portfoy.toplama_matrisi(hiy, taban)
rng = np.random.default_rng(0); idx = pd.date_range("2026-06-01", periods=24, freq="h", tz="UTC")
gercek_taban = pd.DataFrame({s: 10 * (i + 1) * np.clip(np.sin((idx.hour - 6) / 12 * np.pi), 0, None) for i, s in enumerate(taban)}, index=idx)
gercek = pd.DataFrame(gercek_taban.values @ S.T, index=idx, columns=dug)
tahmin = gercek * (1 + rng.normal(0, 0.1, gercek.shape))            # bağımsız, tutarsız tahminler
hatalar = pd.DataFrame(rng.normal(0, 1, (200, len(dug))) * gercek.max().values * 0.1, columns=dug)
uz = portfoy.mint(tahmin, S, dug, hatalar, "shrink")
print("tutarlı mı:", portfoy.tutarlilik_kontrol(uz, S, dug))
print("RMSE bağımsız:", float(np.sqrt(((tahmin - gercek) ** 2).mean().mean())), "MinT:", float(np.sqrt(((uz - gercek) ** 2).mean().mean())))
