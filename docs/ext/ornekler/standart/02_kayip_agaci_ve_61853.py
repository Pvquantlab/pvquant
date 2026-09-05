"""Saatlik meteo'dan kayıp ağacı + IEC 61853 sentetik matris → ADR → enerji derecesi."""
import numpy as np, pandas as pd, pvlib
from pvquant.ext.standart import iec61853, kayip_agaci
lat, lon = 37.87, 32.49
idx = pd.date_range("2025-06-01", "2025-06-30 23:00", freq="h", tz="UTC")
cs = pvlib.location.Location(lat, lon, tz="UTC").get_clearsky(idx + pd.Timedelta(minutes=30)); cs.index = idx
o, ghi, poa = kayip_agaci.oranlari_saatlikten(cs.ghi * 0.8, cs.dni * 0.8, cs.dhi * 0.8, pd.Series(28.0, index=idx), pd.Series(2.0, index=idx), lat, lon, 25, 180)
a = kayip_agaci.agac(ghi, poa, alan_m2=5000, eta_stc=0.20, oranlar=o, sebeke_kwh=None)
print(a.tablo[["etiket", "kayip_pct", "cikan"]].round(2)); print("şebeke kWh:", round(a.sebeke_kwh))
M = iec61853.matris_uret(400.0); adr = iec61853.matris_uydur(M, 400.0)
tc = pd.Series(28.0, index=idx) + poa * 0 + cs.ghi * 0.8 / 30
print(iec61853.enerji_derecesi(cs.ghi * 0.8, tc, adr))
