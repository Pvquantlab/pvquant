# Hat A — Tahmin sağlayıcıları ikinci halka (ajan raporu özeti, 5 Eyl 2026)
Not: arama motorları bot engeli; ürün sayfaları doğrudan çekildi. Steadysun 2025 Wayback.

## Profiller (ufuk · olasılıksal · veri · doğrulama · piyasa · fiyat · URL)
1. Reuniwatt (FR): DayCast 10 g saatlik / HourCast 15 dk–6 s / InstaCast 30 dk @1 dk (gök kamerası Sky InSight, uydu SunSat); kantil YOK (teyit edilemedi); çoklu NWP+5 uydu+kamera, ML post-processing saha uyarlı; Backtests ürünü; API/FTP, MODBUS; portföy/ülke tahmini. https://reuniwatt.com/en/products-and-services/day-ahead-solar-forecasts-daycast/
2. Steadysun (FR): dakikalar–15 gün, 5 dk güncelleme, 1 dk adım; 11 KANTİL (P00…P100); 20+ meteo merkezi, WRF; portalda MAE/MBE/RMSE; REST ~350 ms; fiyat site/ay kademeli (Starter+ D+2, D+7, Expert+ D+16 uydu, Enterprise+), 30 gün deneme. https://steady-sun.com/faq/
3. Meteomatics (CH): solar_power parametresi, EURO1k 1 km, 15 dk güncelleme; ensemble üyeleri/kantil/spread (ECMWF-VAREPS 100 üye); Ocak 2025 Avrupa portföy nRMSE %4, AI ile %13 düşük hata; "~%20 dengesizlik maliyeti azaltma". https://www.meteomatics.com/en/energy-forecasting/solar-power/
4. DNV Forecaster (eski Vaisala/3TIER): 15 gün, saatlikten 5 dk'ya; "probabilistic power forecasts" (format belirsiz); API/SFTP/portal, 7/24. https://www.dnv.com/energy/services/forecaster/our-services/
5. UL Solutions (eski AWS Truepower): 145 GW, K.Amerika şebeke güneşinin %65'i; dakikalar–haftalar, 5 dk; POE değerleri + güven bantları (tam dağılım); aylık performans raporu. https://www.ul.com/software/renewable-energy-forecasting-energy-integration
6. ENFOR SolarFor (DK): dakikalar–birkaç hafta; kantil belirsizlik bantları (trading/bidding); on-prem veya hosted. https://enfor.dk/services/solarfor/
7. Meteologica (ES): 260 GW güneş, 80+ ülke, 100k varlık; 14 gün saatlik, günde 4 güncelleme; piyasa düzeyinde multi-model/ensemble/olasılıksal; xTraders portalı, 400+ trader. https://www.meteologica.com/services.html
8. energy & meteo systems / emsys (DE): Suncast ~400 GW, 350 müşteri; 5 dk–15 gün; durum-bağımlı belirsizlik, ülke düzeyinde model spread; hava durumuna göre NWP ağırlıklandırma; gerçek besleme vs teknik potansiyel; Meta Forecast harmanı. https://www.emsys-renewables.com/products/power_forecasts/solar-power-forecasts.php
9. Nnergix (ES): Sentinel izleme + 5 gün tahmin; olasılıksal yok; ücretsiz plan 10 sistem. https://www.nnergix.com/pricing
10. DTN: WeatherSentry Energy Edition (15 gün; 72 s saatlik); güneşe özel güç ürünü bulunamadı. 
11. Whiffle (NL): LES <100 m, 7 gün, gün içi; deterministik+olasılıksal; "%30 düşük RMSE" (kendi iddiası). https://whiffle.nl/whiffle-forecast/
12. Amperon (US): 4,9 GW, 103 varlık; 15 gün, alt-saatlik güncelleme; olasılıksal (Mart 2026 lansmanı, dağılım eğrisi); 4 satıcıdan 40k hava noktası; ERCOT teklif senaryoları. https://www.amperon.co/blog/quantifying-solar-uncertainty-with-probabilistic-forecasting
13. Open Climate Fix – Quartz Solar (UK, açık kaynak MIT): PVNet, GSP+site, 5 dk güncelleme, 0–48 s; API'de plevel_10/plevel_90; SEVIRI 11 kanal + ICON-EU/ECMWF/GFS + canlı PV; trend_adjuster (son 7 gün bias). https://api.quartz.solar/openapi.json · https://github.com/openclimatefix/PVNet
14. Volue Insight (eski Wattsight): Avrupa/Japonya üretim+fiyat, saatlik/15 dk; güneş ensemble teyit edilemedi. https://www.volue.com/data-and-forecasts
15. meteoblue (CH): Forecast API, MultiModel Ensemble; PV paketi dokümanı açılamadı.
16. Tomorrow.io: Weather API, 14 gün kurumsal, kendi uyduları; olasılıksal yok.
17. Vaisala Xweather: Solar Model 3 (Heliosat-V, 15 dk, 3 km), WeatherDesk 15 gün olasılıksal; ışınım doğrulaması 66 istasyon MBE %0,86, saatlik RMSE %15,06; kullandıkça öde. https://www.xweather.com/products/solar-irradiance-data
18. Overspeed (DE): Anemos, ENFOR ile 120 GW; istatistiksel belirsizlik; çoklu model+uydu+gölge tespiti; "%100 erişilebilirlik 10 yıl". https://www.overspeed.de/en/solutions/solar-power-forecasts
19. AleaSoft (ES): AleaBlue 10 gün + fiyat; üretim kantili teyit edilemedi.
20. Solar Analytics (AU): konut izleme; tahmin yok.
21. Dexter Energy (NL): P5/P10/P25/P50/P75/P90/P95; kantil regresyonu + conformal prediction + CRPS; vaka: 10 MW NL portföyü aFRR 4 s bloklarda P10 tabanı €65.552 ile sabit haircut'ları geçti. https://dexterenergy.ai/news/probabilistic-wind-and-solar-power-forecasting/
22. Rebase Energy (SE): Python-first API; ücretsiz 3 site; "From €800/month"; çoklu model ensemble "%20 doğruluk, %10 dengesizlik azalması". https://www.rebase.energy/pricing
23. Sunairio (US): 18 s/15 gün/12 ay/15 yıl; 1.000 ensemble üyesi "kalibre"; kendi SHED reanalizi 1950→. https://sunairio.com/technology/sunairio-one/
24. WindBorne (US): WeatherMesh-6 AI, balon verisi, 15 gün saatlik, 128 üye ensemble; enerji ticareti ürünü.
25. Jua (CH): EPT-2 foundation model, 100+ GW, Enel/RWE/EDF; güneş ayrıntısı teyit edilemedi.
26. Silurian (US): GFT, Hydro-Québec ile şebeke varlıklarına post-training; 6–72 s.
27. Brightband (US): açık AI ensemble hava modeli; enerji ürünü yok.
28. Sprixin 国能日新 (CN): 2000+ müşteri; 4 s / 72 s / 240 s; çok-model ensemble; TSO sapma cezası ("考核") düşürme hedefi. https://www.sprixin.com/Energy/forecast/windandlight/
29. REConnect Energy (IN): GRIDConnect 16.413 MW, 11 REMC; sapma/dengesizlik sorumluluğunu üstlenen QCA modeli. https://reconnectenergy.com/solutions/

## Kümeler
1 Gözlem-ağırlıklı nowcast (Reuniwatt, Steadysun, Xweather, OCF, Whiffle) · 2 Kurumsal/TSO tam servis (UL, DNV, emsys, Meteologica, ENFOR, Overspeed, Sprixin, REConnect) · 3 Trader-odaklı olasılıksal+fiyat (Dexter, Amperon, Volue, AleaSoft, Rebase) · 4 Hava-API (Meteomatics, meteoblue, Tomorrow.io, DTN) · 5 Foundation-model (Jua, Silurian, WindBorne, Sunairio, Brightband)

## Yeni sektör pratikleri (ilk 11'e göre)
1 Kantil vektörü standartlaşıyor (11 kantil, P5–P95; P10/50/90 minimum) · 2 Kamera/uydu/NWP üç katmanlı ufuk (30 dk / 6 s / 15 g) · 3 LES <100 m · 4 Foundation-model post-training + saha üretimiyle ML ("saha-kalibreli" AI oyuncularının da dili) · 5 Büyük ensemble = kalibrasyon iddiası (1.000/128/100 üye; underdispersion satış argümanı) · 6 Piyasa ürününe bağlı kantil seçimi (Dexter aFRR P10 vaka) · 7 Portföy/ülke tahmini ayrı ürün hattı · 8 Gerçek besleme vs teknik potansiyel (kısıntı) · 9 Fiyat modelleri: site/ay kademe, ücretsiz 3 site + €800/ay, 10 sisteme kadar ücretsiz, sapma sorumluluğu üstlenen sabit ücret · 10 Doğrulama şeffaflığı ışınımda güçlü, güçte kendi iddiası; portalda MAE/RMSE · 11 Trend/bias düzeltme katmanı API parametresi (OCF trend_adjuster) · 12 7/24 nöbet + %100 erişilebilirlik = SLA

## PVQuant konumu (ajan değerlendirmesi)
Çekirdek (15 g saatlik P10/50/90 + saha-kalibreli hibrit) DNV/UL/Meteomatics ufuk ve olasılık düzeyiyle örtüşüyor; onlar 5 dk adım + gün içi uydu nowcast da veriyor — PVQuant'ta 6 s altı katman yok. 60 günlük karne pazarda NADİR şeffaflık (Steadysun/OCF portalda metrik gösterir ama periyodik öz-değerlendirmeyi ürün yapmaz) — gerçek farklılaştırıcı. Fiyat: MW başına değil site-kademesine göre. Kantil tek başına yetmez: hangi piyasa ürününe (KGÜP sapması, gün içi, YAL/YAT) bağlandığı sayısal vakayla gösterilmeli. En ucuz kısa vadeli kazanç: OCF tarzı açık uydu-NWP füzyonu + trend düzeltme katmanı. Eksik: gün içi ufuk, bağımsız doğrulama yayını.
