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
