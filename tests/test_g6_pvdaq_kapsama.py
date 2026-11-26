"""G6-P1 (26.11.2026) — mevsim kapsaması: beklenen saat takvimden (eksik gün eksik sayılır), yerel tz ile mevsim, DJF eşiği yalnız raporlanır."""
import numpy as np
import pandas as pd

from pvquant.ext.kaynak import pvdaq


def _yil(yil=2019, bosluk=()):
    idx = pd.date_range(f"{yil}-01-01", f"{yil + 1}-01-01", freq="1h", tz="Etc/GMT+7", inclusive="left").tz_convert("UTC")
    df = pd.DataFrame({"power_kw": 1.0, "energy_kwh": 1.0, "kapsama_dk": 60}, index=idx)
    df.index.name = "ts_utc"
    for a, b in bosluk:   # yerel tarih aralığı silinir (dosyada hiç yok)
        yerel = df.index.tz_convert("Etc/GMT+7")
        df = df[~((yerel >= pd.Timestamp(a, tz="Etc/GMT+7")) & (yerel < pd.Timestamp(b, tz="Etc/GMT+7")))]
    return df


def test_tam_yil_ve_eksik_gunler():
    k = pvdaq.mevsim_kapsama(_yil(), 2019)
    assert k["beklenen_saat"] == 8760 and k["saat"] == 8760 and k["gecerli"] == 8760 and k["gecerli_pct"] == 100.0
    assert all(k[f"{m}_pct"] == 100.0 for m in pvdaq.MEVSIMLER) and k["djf_uygun"] and k["djf_esik_pct"] == 95.0 and k["kwh"] == 8760
    # ocak 1–15 dosyada yok (360 saat) → DJF beklenen 90 gün = 2160 saat → %83,3; eksik dosya «var» sayılmaz
    k2 = pvdaq.mevsim_kapsama(_yil(bosluk=[("2019-01-01", "2019-01-16")]), 2019)
    assert k2["saat"] == 8400 and k2["djf_pct"] == round(100 * 1800 / 2160, 1) and not k2["djf_uygun"] and k2["jja_pct"] == 100.0


def test_nan_saatler_ve_yil_suzgeci_ve_bos():
    df = _yil()
    yerel = df.index.tz_convert("Etc/GMT+7")
    df.loc[yerel.month == 7, "power_kw"] = np.nan          # temmuz kapsama altı → NaN
    k = pvdaq.mevsim_kapsama(df, 2019)
    assert k["gecerli"] == 8760 - 31 * 24 and k["jja_pct"] == round(100 * (92 - 31) / 92, 1) and k["djf_pct"] == 100.0
    # yıl süzgeci: 2019 verisiyle 2020 sorulursa yalnız 31.12 2019 23:00 UTC→ yerel 2019 kalır: hiç saat yok
    k3 = pvdaq.mevsim_kapsama(df, 2020)
    assert k3["saat"] == 0 and k3["gecerli_pct"] == 0.0 and k3["beklenen_saat"] == 8784 and not k3["djf_uygun"]
    bos = pvdaq.mevsim_kapsama(pd.DataFrame(), 2019)
    assert bos["gecerli"] == 0 and bos["maks_kw"] is None and bos["djf_pct"] == 0.0
