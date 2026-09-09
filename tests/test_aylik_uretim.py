"""v2.68 (Issue #1): aylik_ozet saf fonksiyon durusmasi — DB'siz."""
import numpy as np
import pandas as pd

from pvquant.services.ingest_service import aylik_ozet


def _df(n_saat=24 * 45, kwh=100.0):
    idx = pd.date_range("2025-03-01", periods=n_saat, freq="h", tz="UTC")
    return pd.DataFrame({"energy_kwh": kwh, "power_kw": kwh}, index=idx)


def test_iki_ay_utc_takvimi():
    o = aylik_ozet(_df())
    assert list(o["ay"]) == ["2025-03", "2025-04"]
    assert o.loc[0, "saat"] == 744 and abs(o.loc[0, "uretim_mwh"] - 74.4) < 0.01
    assert o.loc[0, "kapsam_pct"] == 100.0


def test_yerel_takvim_ay_sinirini_kaydirir():
    # 1 Mart 00:00 UTC = 1 Mart 03:00 IST -> IST Mart'i 741 saat gorur
    o = aylik_ozet(_df(), tz="Europe/Istanbul")
    assert o.loc[0, "ay"] == "2025-03" and o.loc[0, "saat"] == 741


def test_energy_kwh_bos_power_kw_yedegi():
    df = _df()
    df["energy_kwh"] = np.nan
    assert (aylik_ozet(df)["uretim_mwh"] == aylik_ozet(_df())["uretim_mwh"]).all()


def test_bos_girdi_bos_cikti():
    o = aylik_ozet(pd.DataFrame())
    assert o.empty and list(o.columns) == ["ay", "uretim_mwh", "saat", "kapsam_pct"]


def test_ic_bosluk_ayi_satir_olarak_dogar():
    """v2.316: gozlenen ilk->son ay arasindaki bos takvim ayi listeden DUSMEZ —
    uretim NaN (API null basar), saat 0, kapsam 0. Bastaki aylar uretilmez."""
    mart = _df(n_saat=24 * 10)                                   # 2025-03
    mayis = pd.DataFrame({"energy_kwh": 100.0, "power_kw": 100.0},
                         index=pd.date_range("2025-05-01", periods=24 * 10,
                                             freq="h", tz="UTC"))
    o = aylik_ozet(pd.concat([mart, mayis]))
    assert list(o["ay"]) == ["2025-03", "2025-04", "2025-05"]    # Nisan atlanmadi
    nisan = o[o["ay"] == "2025-04"].iloc[0]
    assert np.isnan(nisan["uretim_mwh"])                          # 0 uydurulmadi
    assert nisan["saat"] == 0 and nisan["kapsam_pct"] == 0.0
    # onceki davranis korunur: bastaki aylara dolgu yok
    assert o.iloc[0]["ay"] == "2025-03"
