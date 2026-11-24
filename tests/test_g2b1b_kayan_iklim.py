"""G2-B1b (24.11.2026) — genç santralde CLIPER kayan iklimsel yedeği: ay×saat iklimseli (≥20 gün) boşken son 30 günün saat-bazlı
ortalaması (≥20 gün) iklimsel yerine geçer; yalnız `iklimsel_yedek=True` ile (karne); bağımsız motor varsayılanı değişmez."""
from __future__ import annotations

import numpy as np
import pandas as pd

from pvquant.ext.tahmin import referans as ref
from pvquant.services import bagimsiz_dogrulama_service as bd

LAT, LON = 37.87, 32.49


def _gecmis(bas: str, gun: int, kwp: float = 1000.0) -> pd.Series:
    ix = pd.date_range(bas, periods=gun * 24, freq="h", tz="UTC")
    saat = np.arange(len(ix)) % 24
    y = np.clip(kwp * 0.8 * np.sin(np.pi * (saat - 4) / 12.0), 0, None)   # 04–16 UTC gündüz çanı, sabit
    return pd.Series(y, index=ix)


def test_kayan_saatlik_iklim_saat_ortalamasi_ve_min_gun():
    g = _gecmis("2026-10-01", 25)
    hedef = pd.date_range("2026-10-26", periods=24, freq="h", tz="UTC")
    out = ref.kayan_saatlik_iklim(g, hedef, gun=30, min_gun=20)
    assert out.notna().all() and np.allclose(out.values, g.iloc[:24].values)   # sabit profil → saat ortalaması = profil
    assert ref.kayan_saatlik_iklim(g, hedef, gun=30, min_gun=26).isna().all()   # 25 gün < 26 → NaN (sayı uydurulmaz)
    assert ref.kayan_saatlik_iklim(g.iloc[0:0], hedef).isna().all()


def test_kayan_iklim_yalniz_son_30_gunu_kullanir():
    eski = _gecmis("2026-08-01", 40) * 0.5                 # eski dönem yarı güç
    yeni = _gecmis("2026-10-01", 30)
    g = pd.concat([eski, yeni])
    hedef = pd.date_range("2026-10-31", periods=24, freq="h", tz="UTC")
    out = ref.kayan_saatlik_iklim(g, hedef, gun=30, min_gun=20)
    assert np.allclose(out.values, yeni.iloc[:24].values)   # eski (yarı güç) dönem ortalamaya girmez


def _e(bas: str, run_at: str, n: int = 24) -> pd.DataFrame:
    ts = pd.date_range(bas, periods=n, freq="h", tz="UTC")
    return pd.DataFrame({"ts_utc": ts, "run_at": pd.Timestamp(run_at, tz="UTC")})


def test_genc_santral_cliper_yedeksiz_nan_yedekli_dolu():
    g = _gecmis("2026-10-01", 25)                                        # 25 gün: ay×saat (Ekim) 25 ≥ 20 → DOLU olurdu; 2 aya yay
    g = pd.concat([_gecmis("2026-09-18", 13), _gecmis("2026-10-01", 12)])   # Eylül 13 g + Ekim 12 g → hiçbir ay ≥ 20 gün
    e = _e("2026-10-13 00:00", "2026-10-12 06:00")
    seri0, info0 = bd.cliper(e, g, pd.Timestamp("2026-10-13", tz="UTC"), LAT, LON)
    assert seri0.isna().all() and info0 is None                           # motor tanımı: dürüst tire
    seri1, info1 = bd.cliper(e, g, pd.Timestamp("2026-10-13", tz="UTC"), LAT, LON, iklimsel_yedek=True)
    gunduz = e.ts_utc.dt.hour.between(5, 15)
    assert seri1[gunduz.values].notna().all() and (seri1.dropna() >= 0).all()
    assert info1["iklimsel_kaynak"] == "kayan30" and 0.0 <= info1["agirlik_persistans"] <= 1.0


def test_olgun_santralda_yedek_sonucu_degistirmez():
    g = _gecmis("2026-09-01", 55)                                        # hedef ayı (Ekim) 25 gün ≥ 20 → ay×saat dolu
    e = _e("2026-10-27 00:00", "2026-10-26 06:00")
    a, ia = bd.cliper(e, g, pd.Timestamp("2026-10-27", tz="UTC"), LAT, LON)
    b, ib = bd.cliper(e, g, pd.Timestamp("2026-10-27", tz="UTC"), LAT, LON, iklimsel_yedek=True)
    assert ia is not None and ia["iklimsel_kaynak"] == "ay_saat" and ib["iklimsel_kaynak"] == "ay_saat"
    pd.testing.assert_series_equal(a, b)


def test_karne_cliper_genc_santralda_dolu():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from apps.worker.main import karne_cliper
    g = pd.concat([_gecmis("2026-09-18", 13), _gecmis("2026-10-01", 12)])
    df = _e("2026-10-13 00:00", "2026-10-12 06:00")
    out = karne_cliper(df, g, pd.Timestamp("2026-10-13", tz="UTC"), LAT, LON)
    assert out.notna().sum() >= 8                                       # karne: genç santralde tire yerine kayan iklimsel yedek
