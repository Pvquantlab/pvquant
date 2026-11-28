"""G4-P4 (26.11.2026) — hata ayrıştırma: sentetik santral; (a) meteo = gerçek ışınım → ışınım hatası ≈0, (b) bulutlu saatlerde meteo
%+60 şişkin → bulutlu kuşak sapması pozitif, berrak kuşak ≈0; PR çökmesi saatleri sayılır; zaman varyantında aralık ortası en iyi."""
import numpy as np
import pandas as pd

from pvquant.services import retrospektif_kalibrasyon as rk

PLANT = {"name": "sentetik", "lat": 39.74, "lon": -105.18, "tilt": 40.0, "azimuth": 180.0, "capacity_kwp": 2.4}


def _veri(sisirme=0.0, cokme_saat=0):
    import pvlib
    idx = pd.date_range("2022-03-01", "2022-05-30 23:00", freq="1h", tz="UTC")
    loc = pvlib.location.Location(PLANT["lat"], PLANT["lon"])
    cs = loc.get_clearsky(idx + pd.Timedelta(minutes=30), model="ineichen")
    cs.index = idx
    rng = np.random.default_rng(7)
    kt = pd.Series(np.where(rng.random(len(idx)) < 0.3, 0.2, 1.0), index=idx)     # %30 saat bulutlu
    ghi_gercek = cs["ghi"] * kt
    poa_gercek, _ = rk._poa_motor_yolu(ghi_gercek, PLANT["lat"], PLANT["lon"], 40.0, 180.0)
    ghi_meteo = ghi_gercek * np.where(kt < 0.5, 1.0 + sisirme, 1.0)              # meteo bulutu kaçırıyor
    power = (2.4 * poa_gercek / 1000.0 * 0.8).clip(lower=0)
    if cokme_saat:
        parlak = power[power > 1.0].index[:cokme_saat]
        power.loc[parlak] = 0.01                                                   # kar/gölge: güneş var üretim yok
    scada = pd.DataFrame({"power_kw": power, "poa_wm2": poa_gercek, "t_air": 15.0}, index=idx)
    meteo = pd.DataFrame({"ghi": ghi_meteo, "temp_air": 14.0}, index=idx)
    return scada, meteo


def test_meteo_dogruysa_isinim_hatasi_sifira_yakin():
    s, m = _veri()
    o = rk.hata_ayristir(s, m, PLANT)
    assert o["isinim"]["wmape_pct"] < 1.0 and abs(o["isinim"]["bias_pct"]) < 1.0 and o["santral"]["pr_cokme_saat"] == 0
    zv = o["isinim"]["zaman_varyantlari"]
    assert zv["gunes_konumu_+30dk"] <= zv["gunes_konumu_+0dk"] and zv["gunes_konumu_+30dk"] <= zv["gunes_konumu_+60dk"] and o["hukum"]["zaman_hizasi_motor_dogru"]
    assert o["mevsim"]["holdout"]["n"] > 0 and o["mevsim"]["egitim"]["n"] > o["mevsim"]["holdout"]["n"]


def test_bulutlu_sisirme_ve_pr_cokmesi():
    s, m = _veri(sisirme=0.6, cokme_saat=12)
    o = rk.hata_ayristir(s, m, PLANT)
    b = o["isinim"]["berraklik_olculen"]
    assert b["bulutlu"]["bias_pct"] > 30 and abs(b["berrak"]["bias_pct"]) < 2.0 and o["isinim"]["wmape_pct"] > 2   # bulutlu saatlerin ışınım ağırlığı küçük → toplam WMAPE birkaç puan
    assert o["santral"]["pr_cokme_saat"] == 12 and o["hukum"]["baskin_bilesen"] in ("meteo_isinim", "belirsiz")
