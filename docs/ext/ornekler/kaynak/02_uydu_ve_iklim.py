"""PVGIS SARAH-3 saatlik seri → yıllık toplam → belirsizlik bütçesi + TMY. Ağ gerekir (kayıt yok)."""
from pvquant.ext.kaynak import belirsizlik, tmy, uydu_isinim

lat, lon = 37.87, 32.49
c = uydu_isinim.pvgis_saatlik(lat, lon, 2005, 2023)
y = belirsizlik.yillik_toplam(c.df["ghi"])
b = belirsizlik.butce(y, sigma_kaynak=0.04, sigma_model=0.03, N_yil=10)
print("P50", round(b.p50), "P90(1 yıl)", round(b.olasiliklar[90]), "P90(10 yıl)", round(b.olasiliklar_N_yil[90]))
print(belirsizlik.aylik_p_degerleri(c.df["ghi"]).round(1))
t, secim = tmy.tmy_uret(c.df[["ghi", "temp_air", "wind_speed_10m"]])
print("TMY ay→yıl", secim, "TMY GHI kWh/m²", round(t["ghi"].sum() / 1000))
yil, toplam, _ = tmy.pxx_yili(c.df, 90); print("P90 senaryo yılı", yil, round(toplam))
