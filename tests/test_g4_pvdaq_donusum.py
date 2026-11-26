"""G4 hazırlık (26.11.2026) — PVDAQ dakikalık → saatlik dönüşüm: tz, ortalama/enerji, kapsama eşiği, gürültü kırpma."""
import numpy as np
import pandas as pd

from pvquant.ext.kaynak import pvdaq


def _gun(tarih="2018-06-21", eksik_dk=0):
    idx = pd.date_range(f"{tarih} 00:00", periods=1440, freq="min")
    if eksik_dk:
        idx = idx[:-eksik_dk]
    saat = idx.hour + idx.minute / 60.0
    poa = np.clip(1000 * np.sin(np.pi * (saat - 6) / 12), 0, None)            # 06–18 yerel gündüz
    df = pd.DataFrame({"measured_on": idx, "ac_power__584": poa * 1.8 - 1.3, "dc_power__583": poa * 2.0,
                       "poa_irradiance__582": poa - 5.0, "ambient_temp__589": 20.0, "module_temp_1__590": 20.0 + poa / 40})
    return df


def test_tz_ve_saat_basi_damga(tmp_path):
    p = tmp_path / "system_33__date_2018_06_21.csv"
    _gun().to_csv(p, index=False)
    d = pvdaq.dakikalik_oku(str(p))
    s = pvdaq.saatlige_indir(d)
    assert s.index.tz is not None and str(s.index.tz) == "UTC"
    assert s.index.min() == pd.Timestamp("2018-06-21 07:00", tz="UTC")            # 00:00 Etc/GMT+7 = 07:00 UTC
    assert len(s) == 24 and (s["kapsama_dk"] == 60).all()
    ogle = s.loc[pd.Timestamp("2018-06-21 19:00", tz="UTC")]                       # 12:00 yerel
    assert 1.7 < ogle["power_kw"] < 1.81 and abs(ogle["energy_kwh"] - ogle["power_kw"]) < 1e-9 and ogle["poa_wm2"] > 950
    gece = s.loc[pd.Timestamp("2018-06-21 07:00", tz="UTC")]
    assert gece["power_kw"] == 0.0 and gece["poa_wm2"] == 0.0                     # −1,3 W gürültü ve −5 W/m² kırpıldı


def test_kapsama_esigi_ve_enerji(tmp_path):
    p = tmp_path / "system_33__date_2018_06_21.csv"
    _gun(eksik_dk=40).to_csv(p, index=False)   # son saat 20 dk
    s = pvdaq.saatlige_indir(pvdaq.dakikalik_oku(str(p)))
    son = s.iloc[-1]
    assert son["kapsama_dk"] == 20 and np.isnan(son["power_kw"]) and np.isnan(son["energy_kwh"])
    s2 = pvdaq.saatlige_indir(pvdaq.dakikalik_oku(str(p)), asgari_dk=10)
    assert s2.iloc[-1]["kapsama_dk"] == 20 and abs(s2.iloc[-1]["energy_kwh"] - s2.iloc[-1]["power_kw"] * 20 / 60) < 1e-9


def test_dizin_donustur_ozet(tmp_path):
    for t in ("2018-06-21", "2018-06-22"):
        _gun(t).to_csv(tmp_path / f"system_33__date_{t.replace('-', '_')}.csv", index=False)
    (tmp_path / "baska.csv").write_text("x\n")
    saat, o = pvdaq.dizin_donustur(str(tmp_path))
    assert o["dosya"] == 2 and o["dakika_satir"] == 2880 and o["saat"] == 48 and o["gecerli_saat"] == 48 and o["gun"] == 3   # UTC'de 3 takvim günü
    assert o["tz"] == "Etc/GMT+7" and saat.index.is_monotonic_increasing
    bos, o2 = pvdaq.dizin_donustur(str(tmp_path), desen="yok_*.csv")
    assert bos.empty and o2["dosya"] == 0 and o2["ilk"] is None
