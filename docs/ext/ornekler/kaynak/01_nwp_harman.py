"""Üç NWP kaynağını indir, harmanla, P10/P50/P90 GHI yaz. Ağ + eccodes gerekir."""
from pvquant.ext.kaynak import atif, harman, nwp_ecmwf, nwp_gfs, nwp_icon

lat, lon = 37.87, 32.49
e = nwp_ecmwf.oku(nwp_ecmwf.indir("veri/ecmwf"), lat, lon)
i = nwp_icon.oku(nwp_icon.indir("veri/icon", adimlar=list(range(0, 79)))[0].parent, lat, lon)
g = nwp_gfs.oku(nwp_gfs.indir("veri/gfs", lat, lon, adimlar=list(range(0, 121)))[0].parent, lat, lon)
h = harman.harmanla({"ecmwf": e, "icon": i, "gfs": g})
print(h.agirliklar, h.uye_sayisi)
print(h.df[["ghi", "ghi_p10", "ghi_p90", "temp_air"]].head(48))
print(atif.kunye(["ecmwf", "icon", "gfs"]))
