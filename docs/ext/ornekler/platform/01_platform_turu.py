"""Üç santrallik portföy: toplama, alarm motoru, API anahtarı, paylaşım, tarife, raporlar."""
import numpy as np, pandas as pd
from datetime import datetime, timezone
from pvquant.ext.platform import alarm, api_anahtar, paylasim, portfoy, rapor_sablon, tarife, tazeleme
rng = np.random.default_rng(0)
idx = pd.date_range("2025-07-01", periods=24 * 31, freq="h", tz="UTC"); g = np.clip(np.sin((idx.hour + 3 - 6) / 12 * np.pi), 0, None)
P = portfoy.Portfoy({f"S{i}": portfoy.SantralKaydi(f"S{i}", f"Santral {i}", 5.0 * i, "Konya" if i < 3 else "Adana") for i in (1, 2, 3)})
ger = {k: pd.Series(s.kurulu_guc_mw * g * rng.uniform(0.5, 1, len(idx)), index=idx) for k, s in P.santraller.items()}
tah = {k: v * (1 + rng.normal(0, 0.1, len(idx))) for k, v in ger.items()}
print(portfoy.gunluk_ozet(tah, ger, P).head(3).round(2)); print(portfoy.agirlikli_kpi({"S1": {"wmape": 0.08}, "S2": {"wmape": 0.12}, "S3": {"wmape": 0.05}}, P))
m = alarm.AlarmMotoru(alarm.Ayar(acik_kurallar=("veri_gelmedi", "skill_dustu", "pr_dustu")))
print([a.mesaj for a in m.tara("S1", {"son_scada_saat_once": 60, "skill_7g": -0.1, "pr_30g": 0.66})])
depo = api_anahtar.Depo(); duz, kayit = api_anahtar.uret(depo, "tenant-A", {"tahmin:oku"}, "toplayıcı entegrasyonu"); print(duz[:12] + "…", api_anahtar.dogrula(depo, duz, "tahmin:oku").tenant_id)
pol = paylasim.Politika(); admin = paylasim.Kullanici("u1", "tenant-A", "admin"); dsg = paylasim.Kullanici("u9", "tenant-DSG", "viewer")
pol.paylas(admin, "tenant-DSG", "S1", {"tahmin:oku", "karne:oku"}, takma_ad="Konya-α"); print(pol.izin_var_mi(dsg, "tahmin:oku", "S1", "tenant-A"), pol.takma_ad(dsg, "S1", "Santral 1"))
y = [tarife.TarifeYapisi("ToU", tarife.CokZamanli(fiyatlar={"gunduz": 2400, "puant": 3300, "gece": 2000}), pd.Timestamp("2025-01-01", tz="UTC"))]
print(tarife.aylik(tarife.gelir(ger["S1"], y)).round(0))
rp, s = rapor_sablon.kapasite_testi(ger["S1"] * 1000, pd.Series(950 * g, index=idx), pd.Series(28.0, index=idx), pd.Series(2.0, index=idx), beklenen_fn=lambda rc: 5000 * rc["E"] / 1000, santral="Santral 1", donem="Temmuz 2025")
print(rp.markdown()[:400])
