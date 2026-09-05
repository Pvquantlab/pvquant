"""Ölçülen son 3 saatten 0–6 s nowcast; NWP ile rampalı harman (sentetik NWP)."""
import numpy as np, pandas as pd
from pvquant.ext.kaynak import nowcast
from pvquant.ext.kaynak.atif import KAYNAKLAR
from pvquant.ext.kaynak.ortak import MeteoCerceve, acik_gok_ghi

lat, lon = 37.87, 32.49
idx = pd.date_range("2026-06-10 00:00", periods=48, freq="h", tz="UTC")
cs = acik_gok_ghi(idx, lat, lon)
nwp = MeteoCerceve(pd.DataFrame({"ghi": cs * 0.8, "temp_air": 25.0, "wind_speed_10m": 2.0}, index=idx), lat, lon, KAYNAKLAR["ecmwf"])
olcum = (cs * 0.55).loc[: idx[9]]     # sabah 09:00'a kadar bulutlu ölçüm
h = nowcast.rampali_harman(nwp, olcum, tau_saat=2.0)
print(pd.DataFrame({"nwp": nwp.df["ghi"], "nowcast": h.df["ghi"]}).loc[idx[8]: idx[18]].round(0))
