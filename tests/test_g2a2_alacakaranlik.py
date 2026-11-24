"""G2-A2 (24.11.2026) — F1-08 alacakaranlık (açık gök < 20 W/m² saatlerinde GHI sıfırlanmaz) ve F1-09 kaba NWP adımının
gündüz ağırlıklı, enerji korunumlu saatliğe indirgenmesi (kış gündoğumu saati sıfırlanmaz). Saf testler."""
from __future__ import annotations

import numpy as np
import pandas as pd

from pvquant.ext.kaynak import harman, nowcast
from pvquant.ext.kaynak.atif import KAYNAKLAR
from pvquant.ext.kaynak.ortak import MeteoCerceve, acik_gok_ghi, kaba_adimi_saatlige_indir

LAT, LON = 37.87, 32.49


# ── F1-09: kaba adım ───────────────────────────────────────────────────────────
def test_kaba_adim_tam_gunduz_blogu_eski_formulle_birebir():
    """Bütün saatleri gündüz olan 3 saatlik blokta sonuç v/cs_ort·cs (eski kural) ile aynı kalır."""
    hedef = pd.date_range("2026-06-10 00:00", periods=24, freq="h", tz="UTC")
    cs = acik_gok_ghi(hedef, LAT, LON)
    seri = pd.Series({pd.Timestamp("2026-06-10 09:00", tz="UTC"): 500.0, pd.Timestamp("2026-06-10 12:00", tz="UTC"): 600.0})   # 3 s adım; (09Z, 12Z] bloğu
    out = kaba_adimi_saatlige_indir(seri, LAT, LON, hedef)
    blok = (hedef >= pd.Timestamp("2026-06-10 09:00", tz="UTC")) & (hedef < pd.Timestamp("2026-06-10 12:00", tz="UTC"))
    assert (cs[blok] > 20).all()
    eski = (600.0 / cs[blok].mean()) * cs[blok]
    assert np.allclose(out[blok].values, eski.values, rtol=1e-9)
    assert abs(out[blok].sum() - 600.0 * 3) < 1e-6          # enerji korunur


def test_kaba_adim_kis_gundogumu_saati_sifirlanmaz():
    """6 saatlik kış bloğunda açık gök ORTALAMASI < 20 ama Σcs > 0: eski kural kt=0 → gündoğumu saati 0 idi; şimdi pozitif."""
    hedef = pd.date_range("2026-01-15 00:00", periods=24, freq="h", tz="UTC")
    cs = acik_gok_ghi(hedef, LAT, LON)
    # gündoğumu civarını kapsayan 6 saatlik blok: bitiş damgası ilk cs>0 saatinden 1 saat sonra
    ilk = int(np.argmax(cs.values > 0))
    bitis = hedef[ilk + 1]; bas = bitis - pd.Timedelta(hours=6)
    blok = (hedef >= bas) & (hedef < bitis)
    assert cs[blok].mean() < 20 and cs[blok].sum() > 0, "kurgu: ortalama < 20, toplam > 0"
    v = 6.0   # W/m² blok ortalaması (NWP'nin verdiği küçük ama sıfır olmayan ışınım)
    out = kaba_adimi_saatlige_indir(pd.Series({bas: 0.0, bitis: v}), LAT, LON, hedef)   # iki damga → 6 s adım; blok [bas, bitis)
    assert out[hedef[ilk]] > 0.0, "gündoğumu saati sıfır kalmamalı"
    assert (out[blok][cs[blok] <= 0] == 0.0).all(), "karanlık saatler 0"
    assert out[blok].sum() <= v * 6 + 1e-9                 # kt ≤ 1,3 kırpması enerjiyi artırmaz
    assert (out >= 0).all() and out.notna().all()


def test_kaba_adim_tamamen_gece_blogu_sifir():
    hedef = pd.date_range("2026-01-15 00:00", periods=24, freq="h", tz="UTC")
    out = kaba_adimi_saatlige_indir(pd.Series({pd.Timestamp("2026-01-15 00:00", tz="UTC"): 0.0, pd.Timestamp("2026-01-15 03:00", tz="UTC"): 4.0}), LAT, LON, hedef)
    gece = (hedef >= pd.Timestamp("2026-01-15 00:00", tz="UTC")) & (hedef < pd.Timestamp("2026-01-15 03:00", tz="UTC"))
    assert (out[gece] == 0.0).all()                        # Σcs = 0 → kt = 0 (eski davranışla aynı)


# ── F1-08: alacakaranlık ───────────────────────────────────────────────────────
def _cerceve(ghi: pd.Series) -> MeteoCerceve:
    return MeteoCerceve(pd.DataFrame({"ghi": ghi, "temp_air": 10.0, "wind_speed_10m": 2.0, "cloud_cover": 20.0}, index=ghi.index), LAT, LON, KAYNAKLAR["ecmwf"])


def test_harman_alacakaranlikta_ham_ghi_gecer():
    idx = pd.date_range("2026-11-15 00:00", periods=24, freq="h", tz="UTC")
    cs = acik_gok_ghi(idx, LAT, LON)
    alaca = (cs > 0) & (cs < 20.0)
    assert alaca.any(), "kurgu: Kasım'da alacakaranlık saati olmalı"
    ghi = (cs * 0.8).copy()
    ghi[alaca] = 8.0                     # modeller alacakaranlıkta 8 W/m² veriyor
    h = harman.harmanla({"e": _cerceve(ghi), "i": _cerceve(ghi)})
    assert (h.df.loc[alaca, "ghi"] > 0).all(), "alacakaranlık GHI sıfırlanmamalı (F1-08)"
    assert (h.df.loc[alaca, "ghi"] <= cs[alaca] * 1.3 + 1e-9).all()
    gunduz = cs >= 20
    assert np.allclose(h.df.loc[gunduz, "ghi"], (cs * 0.8)[gunduz], rtol=0.02)   # gündüz davranışı değişmedi


def test_sapma_duzelt_alacakaranlikta_nwp_gecer():
    idx = pd.date_range("2026-11-15 00:00", periods=24, freq="h", tz="UTC")
    cs = acik_gok_ghi(idx, LAT, LON)
    alaca = (cs > 0) & (cs < 20.0)
    nwp = (cs * 0.7).copy()
    nwp[alaca] = 6.0
    gecmis_idx = pd.date_range("2026-11-10 00:00", periods=24 * 5, freq="h", tz="UTC")
    gcs = acik_gok_ghi(gecmis_idx, LAT, LON)
    out = nowcast.sapma_duzelt(nwp, gcs * 0.7, gcs * 0.7, LAT, LON)      # geçmişte sapma yok → düzeltme 0
    assert (out[alaca] > 0).all() and np.allclose(out[alaca], 6.0)
    assert np.allclose(out[cs >= 20], nwp[cs >= 20], rtol=1e-6)
