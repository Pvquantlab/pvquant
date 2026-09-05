# Hat D — Meteo tedarik lisans/fiyat kıyası (ajan raporu özeti, 5 Eyl 2026)
- Open-Meteo Standard €29/ay (€319/yıl), 1M çağrı, ticari ✅ ama ensemble/arşiv/uydu YOK. Professional €99/ay (€1.099/yıl), 5M çağrı: + Historical (ERA5 0.25° 1940–, ERA5-Land, CERRA 5 km), Ensemble (IFS ENS 51 üye 15 g, GFS 31, ICON-EPS 40), Satellite Radiation (SARAH-3 0.05° 1983–, MTG 0.025° 2026). Enterprise 50M, SLA, teklif. Atıf CC BY 4.0 zorunlu. "99.9% uptime target" (sözleşmesel SLA yalnız Enterprise). Kod değişikliği sıfır ("only the domain and key parameter differ").
- Meteomatics: fiyat teklif; ens_select member:1-100 mean/median/quantile; EURO1k 1 km; ERA5 1940–; Extended SLA ek ücret.
- meteoblue Premium API 40k çağrı/ay €2.400/yıl; solar paketi TE.
- Solcast: Hobbyist non-commercial; ticari planlar teklif (Starter 6 s güncelleme / Pro 15 dk / Max 5 dk); −7..+14 gün; P10/P90 senaryoları; arşiv 3/7 yıl / 2007→.
- Solargis Forecast Basic (D0+7 saatlik) / Professional (D0+14, 5–15 dk); Evaluate €12.000 aboneliği ipucu.
- Tomorrow.io: solarGHI/DNI/DHI −7..+14 g; fiyat teklif; pricing 404.
- Visual Crossing: Free ticari ✔ 1.000 kayıt/gün; Professional $35/ay; Corporate $150/ay (gelişmiş güneş); Enterprise SLA; ensemble yok.
- OpenWeatherMap: One Call 4.0 ilk 1.000 çağrı/gün ücretsiz, sonra 0,0012 GBP; Solar Irradiance API 0,1 GBP/çağrı (16 gün GHI/DNI/DHI); history bulk 25 GBP/lokasyon; PV üretim tahmini 250 GBP/ay/lokasyon; ODbL atıf.
- Weatherbit Free CC BY-NC (ticari ❌); $45/$195/$475 ay; 10 gün saatlik ghi/dni/dhi; ensemble yok.
- Pirate Weather $3–$350/ay; 7 gün; yalnız GHI.
- Xweather Developer €0 15k erişim; €300/ay 1M; 15 gün; ghi/dni/dhi; ensemble yok.
- Meteostat CC BY 4.0 ama IŞINIM YOK.
- CAMS Solar Radiation TS: ücretsiz CC-BY, 2004→, 1 dk–1 s, GHI/BHI/DHI/BNI, Türkiye MSG alanında.
- PVGIS API v5.3: ücretsiz, kısıtsız; SARAH3 2005–2023 (Konya için test edildi), ERA5 2005–2020; 30 çağrı/sn/IP.
- NASA POWER: ücretsiz; saatlik 2001→ (Ankara test); 1° ışınım (kaba).
- ECMWF Open Data: CC BY 4.0; ssrd/ssr/2t/10u/10v/tcc HRES+ENS (50+1) 0.25°, 15 gün (0–144 s 3 saatlik, sonra 6 s); yalnız son 12 run (~2–3 gün).
- DWD ICON-EU open data: CC BY 4.0; aswdir_s/aswdifd_s/asob_s/t_2m/u,v_10m/clct/h_snow; 0.0625° (~7 km), +120 s, 8 run/gün; alan 23.5°W–45°E, 29.5–70.5°N → TÜRKİYE TAMAMEN İÇİNDE.
- NOAA GFS/GEFS (AWS): public domain; DSWRF/TMP/UGRD/VGRD/TCDC/SNOD; GFS 16 g 0.25°; GEFS 30+1 üye 0.25°.
- Météo-France: Licence Ouverte 2.0; AROME Türkiye DIŞI; ARPEGE 0.1° 42°E'ye kadar (Doğu Anadolu dışarıda); 0.25° global evet.

## Üç yol
A) Open-Meteo Professional: €1.099/yıl; kod değişikliği ~0; ensemble+arşiv+uydu açılır; risk düşük (SLA sözleşmesel değil).
B) Ham NWP (ECMWF+ICON+GFS/GEFS): veri €0; altyapı €1.5–2.5k/yıl; kurulum 2–3 kişi-ay (~€15k) + bakım 0,2 FTE (~€14k/yıl) → 1. yıl ≈ €30k, sonra ≈ €15.5k/yıl; ilk sürüm kalitesi Open-Meteo'dan kötü olabilir; tek avantaj ham üye verisi/sınırsız hacim.
C) Ticari (Solcast/Meteomatics): fiyat teklif (düşük–orta beş haneli EUR beklenir); en yüksek kalite (5–15 dk uydu nowcast, GTI, P10/P90 hazır); SLA sözleşmeli.
Çağrı bütçesi: 50 santral ≈ 22k çağrı/ay, 500 santral ≈ 220k/ay (tahmin 4×/gün + ensemble 2×/gün) → 5M limitinin %5'i altında; 20 yıl arşiv backfill ≈ 780 çağrı/santral tek sefer.

## Öneri (ajan)
1 Hemen Open-Meteo Professional (yıllık €1.099) + ürün içi atıf "Weather data by Open-Meteo.com (CC BY 4.0)". 2 Kalibrasyon/iklim için PVGIS-SARAH3 + CAMS + NASA POWER yedek (bankable uydu hikâyesi). 3 Yol B'yi şimdi yapma; ECMWF Open Data'dan minimal yedek çekici (1–2 hafta) acil durum planı. 4 Yol C'yi 500 santral / kurumsal eşiğinde (gün içi, P10/P90 taahhüdü) değerlendir. 5 Kullanma: Weatherbit Free, Solcast Hobbyist, Meteostat, AROME, Pirate Weather.
