"""Faz 1 Mod B fizik doğrulaması (27.11.2026) — pvlib 0.15 referansı ve fiziksel sınırlar (DB/ağ yok; formül/parametre değişmez).

Her adım bağımsız referansla sayısal kıyaslanır: güneş konumu (NREL SPA), Erbs ayrıştırma + kapanış, Perez POA, Faiman/NOCT/SAPM hücre
sıcaklığı, PVWatts DC, Barhdadi–Bennis bağıl verim (belgelenmiş kapalı form + STC değişmezi + monotonluk), basit AC (BoS·inv, kırpma).
Uçtan uca zincir: P_AC ≤ AC sınırı, ≥0, gece 0, P_DC ≤ 1,25·kWp, kWh = kW·1 sa, NaN meteo satırı koşuyu düşürmez. Bu dosya teşhis/
regresyon içindir: FAIL = fizik çekirdeği ya da pvlib sürümü değişti demektir."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pvlib
import pytest
from pvlib import irradiance as pvi
from pvlib import pvsystem, solarposition
from pvlib import temperature as pvt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_altin_cekirdek import PLANT, _meteo

from pvquant.models import irradiance as irr
from pvquant.models import power as pw
from pvquant.models import temperature as tmp
from pvquant.pipeline.forecast import forecast_7day
from pvquant.services.plant_spec_service import plant_spec_kur

LAT, LON = 37.9, 32.5
IX = pd.date_range("2026-06-21", periods=72, freq="h", tz="UTC")


@pytest.fixture(scope="module")
def gok():
    ref = solarposition.get_solarposition(IX, LAT, LON)
    ghi = pd.Series(np.clip(900 * np.sin(np.pi * (np.arange(72) % 24 - 3.5) / 13.0), 0, None), index=IX)
    d = irr.decompose_ghi_erbs(ghi, ref["zenith"], IX)
    dni_extra = pvi.get_extra_radiation(IX)
    am = pvlib.atmosphere.get_relative_airmass(ref["apparent_zenith"])
    poa = irr.transpose_perez(25.0, 180.0, ref["apparent_zenith"], ref["azimuth"], d["dni"], ghi, d["dhi"], dni_extra, am, albedo=0.25)
    return {"ref": ref, "ghi": ghi, "d": d, "dni_extra": dni_extra, "am": am, "poa": poa, "G": poa.global_.fillna(0),
            "ta": pd.Series(20.0, index=IX), "ws": pd.Series(2.5, index=IX)}


def test_gunes_konumu_spa_ile_ayni():
    sp = irr.solar_position(IX, LAT, LON)
    ref = solarposition.get_solarposition(IX, LAT, LON)
    assert np.allclose(sp["apparent_zenith"], ref["apparent_zenith"], atol=1e-6) and np.allclose(sp["azimuth"], ref["azimuth"], atol=1e-6)


def test_erbs_ayristirma_pvlib_ve_kapanis(gok):
    e = pvi.erbs(gok["ghi"], gok["ref"]["zenith"], IX)
    d = gok["d"]
    assert np.allclose(d["dni"].fillna(0), e["dni"].fillna(0), atol=1e-6) and np.allclose(d["dhi"].fillna(0), e["dhi"].fillna(0), atol=1e-6)
    g = gok["ghi"] > 0
    assert np.allclose((d["dhi"] + d["dni"] * np.cos(np.radians(gok["ref"]["zenith"])))[g], gok["ghi"][g], rtol=1e-3)   # kapanış
    assert (d["dni"].fillna(0) >= 0).all() and (d["dhi"].fillna(0) >= 0).all()


def test_perez_poa_pvlib_ile_ayni_ve_sinirlar(gok):
    r = pvi.get_total_irradiance(25.0, 180.0, gok["ref"]["apparent_zenith"], gok["ref"]["azimuth"], gok["d"]["dni"], gok["ghi"], gok["d"]["dhi"],
                                 dni_extra=gok["dni_extra"], airmass=gok["am"], albedo=0.25, model="perez")
    assert np.allclose(gok["poa"].global_.fillna(0), r["poa_global"].fillna(0), atol=1e-3)
    assert (gok["G"] >= 0).all() and (gok["G"][gok["ghi"] == 0] == 0).all()


def test_hucre_sicakligi_faiman_noct_sapm(gok):
    g_poa, ta, ws = gok["G"], gok["ta"], gok["ws"]
    assert np.allclose(tmp.cell_temperature_faiman(g_poa, ta, ws), pvt.faiman(g_poa, ta, ws), atol=1e-6)
    assert np.allclose(tmp.cell_temperature_noct(g_poa, ta, 45.0), ta + 25.0 / 800.0 * g_poa, atol=1e-9)
    prm = pvt.TEMPERATURE_MODEL_PARAMETERS["sapm"]["open_rack_glass_polymer"]
    assert np.allclose(tmp.cell_temperature_sapm(g_poa, ta, ws, "open_rack_glass_polymer"), pvt.sapm_cell(g_poa, ta, ws, **prm), atol=1e-6)
    sifir = tmp.cell_temperature_faiman(g_poa, ta, 0.0)                       # uç: rüzgâr 0 → sonlu, ≥ T_amb
    assert np.isfinite(sifir).all() and (sifir >= ta - 1e-9).all()
    assert np.isfinite(tmp.cell_temperature_faiman(g_poa, pd.Series(-15.0, index=IX), ws)).all()   # uç: −15 °C


def test_dc_guc_pvwatts_ve_barhdadi_bennis(gok):
    g_poa = gok["G"]
    tc = tmp.cell_temperature_faiman(g_poa, gok["ta"], gok["ws"])
    assert np.allclose(pw.pdc_pvwatts(g_poa, tc, 1000.0, -0.004), pvsystem.pvwatts_dc(g_poa, tc, 1000.0, -0.004), atol=1e-6)
    p = pw.BarhdadiBennisParams()
    assert (p.c1, p.c2, p.gamma) == (0.033, -0.0092, -0.0034)             # literatür katsayıları (c-Si) — değişirse kalibrasyon etkilenir
    g_ornek = pd.Series([100.0, 300.0, 600.0, 1000.0, 1200.0])
    t_ornek = pd.Series([15.0, 25.0, 35.0, 45.0, 55.0])
    ln = np.log(g_ornek / 1000.0)
    kapali = (1 + p.c1 * ln + p.c2 * ln**2) * (1 + p.gamma * (t_ornek - 25.0))   # belgelenmiş kapalı form
    assert np.allclose(pw.eta_rel_barhdadi_bennis(g_ornek, t_ornek, p), kapali, atol=1e-12)
    assert abs(float(pw.eta_rel_barhdadi_bennis(pd.Series([1000.0]), pd.Series([25.0]), p).iloc[0]) - 1.0) < 1e-12   # STC değişmezi
    assert float(pw.eta_rel_barhdadi_bennis(pd.Series([0.5]), pd.Series([25.0]), p).iloc[0]) == 0.0                   # G<1 → 0 (log(0) yok)
    seri = pw.pdc_barhdadi_bennis(pd.Series(np.linspace(50, 1200, 50)), pd.Series(25.0, index=range(50)), 1000.0, p)
    assert np.all(np.diff(seri.values) > 0)                                                                            # sabit T'de G ile monoton
    pdc = pw.pdc_barhdadi_bennis(g_poa, tc, 1000.0, p)
    assert (pdc.fillna(0) >= 0).all() and (pdc.fillna(0)[g_poa == 0] == 0).all()


def test_ac_basit_model_kirpma(gok):
    pdc = pd.Series(np.linspace(0, 1500, 16))
    pac = pw.pac_simple(pdc, 0.93, 0.97, 900.0)
    assert np.allclose(pac, np.minimum(900.0, pdc * 0.93 * 0.97)) and pac.max() == 900.0


def test_zincir_fiziksel_sinirlar_ve_nan_dayanikliligi():
    spec = plant_spec_kur(PLANT, None)
    m = _meteo()
    h = forecast_7day(m, spec).hourly
    assert (h["p_ac_kw"] <= PLANT["ac_limit_kw"] + 1e-6).all() and (h["p_ac_kw"] >= 0).all()
    assert (h["p_ac_kw"][m.ghi == 0] == 0).all()
    assert (h["p_dc_kw"] <= 1.25 * PLANT["capacity_kwp"]).all()
    assert np.allclose(h["energy_kwh"], h["p_ac_kw"], atol=1e-6)        # saatlik: kWh = kW·1 sa
    assert not h["p_ac_kw"].isna().any() and len(h) == 72
    m2 = _meteo()
    m2.ghi.iloc[30] = np.nan
    h2 = forecast_7day(m2, spec).hourly                                   # tek NaN saat koşuyu düşürmez
    assert len(h2) == 72 and np.isnan(h2["p_ac_kw"].iloc[30]) and h2["p_ac_kw"].drop(h2.index[30]).notna().all()
