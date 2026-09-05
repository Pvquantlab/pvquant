# Hat C — Literatür / standart / veri seti / açık NWP (ajan raporu özeti, 5 Eyl 2026)

## A) Kılavuz ve standartlar
- IEA PVPS Task 16 (Solar Resource for High Penetration): Regional Solar Power Forecasting (2020), Firm Power Generation (2023/2026), 2027'de üç tahmin kıyaslaması bekleniyor. Ücretsiz. https://iea-pvps.org/research-tasks/solar-resource-for-high-penetration-and-large-scale-applications/
- Best Practices Handbook 4. baskı (Ekim 2024, Sengupta ve diğ.; uydu, ML, all-sky imaging, olasılıksal tahmin, veri kalitesi bölümleri) https://iea-pvps.org/key-topics/best-practices-handbook-for-the-collection-and-use-of-solar-resource-data-for-solar-energy-applications-fourth-edition/ ; 3. baskı https://www.osti.gov/biblio/1778700
- Le Gal La Salle, David, Lauret 2025 (Forecasting 7(2):30): EVC diyagramı + OEV metriği — olasılıksal tahminin operasyonel-ekonomik değeri. https://iea-pvps.org/key-topics/journal-article-tools-probabilistic-forecasts-2025/
- IEA PVPS Task 13: Extreme Weather Impacts (2025), Optimisation for Climates (2025), Digital Twins (2026), Project Decisions (2026), Soiling Losses notu (2025). https://iea-pvps.org/publications/?task=67
- IEA Wind Task 51 (eski 36) Recommended Practice for Renewable Forecasting Solutions, 2. baskı 2022 (Möhrlen-Zack-Giebel, Elsevier açık erişim): seçim süreci / kıyaslama-deneme tasarımı / değerlendirme. https://iea-wind.org/task51/task51-publications/task51-recommended-practices/
- ASTM E2848-13(2023): saha PV kapasitesini ışınım-sıcaklık-rüzgar regresyonuyla raporlama (kabul testi). https://store.astm.org/e2848-13r23.html
- PVPMC blind modeling 2021/2023 + IEA bifacial-tracker egzersizi. https://pvpmc.sandia.gov/model-validation/2023-blind-modeling-comparisons/
- WMO/WWRP JWGFVR "Forecast Verification: Issues, Methods and FAQ" (rank histogram, reliability, MET, R verification). https://www.cawcr.gov.au/projects/verification/
- ECMWF Forecast User Guide Bölüm 7 (belirsizlik). https://confluence.ecmwf.int/display/FUG/Forecast+User+Guide
- TEYİT EDİLEMEDİ: ESIG rehberleri (403), IEC 61724-2/-3 başlıkları, SolarPower Europe O&M sürümü, DNV/UL bankability belgeleri, EPRI raporları, WMO-No.1091. IEC 63202-1 = hücre LID ölçümü (kapsam dışı).

## B) İnceleme makaleleri (DOI Crossref teyitli)
- Yang ve diğ. 2020 Verification of deterministic solar forecasts, Solar Energy 210, 10.1016/j.solener.2020.04.019 (33 yazarlı konsensüs; metrik+referans standardı)
- Yang ve diğ. 2022 RSER 161, 10.1016/j.rser.2022.112348
- Yang & van der Meer 2021 Ten overarching thinking tools, RSER 140, 10.1016/j.rser.2021.110735
- van der Meer, Widén, Munkhammar 2018 RSER 81, 10.1016/j.rser.2017.05.212
- Doubleday, Van Scyoc Hernandez, Hodge 2020 Benchmark probabilistic solar forecasts, Solar Energy 206, 10.1016/j.solener.2020.05.051
- Mayer 2022 Benefits of physical and ML hybridization, RSER 168, 10.1016/j.rser.2022.112772
- Mayer & Yang 2022 Calibrated ensemble of model chains, RSER 168, 10.1016/j.rser.2022.112821
- Mayer & Yang 2023 Calibration of deterministic NWP forecasts, IJF 39, 10.1016/j.ijforecast.2022.03.008
- Hong ve diğ. 2016 GEFCom2014, IJF 32, 10.1016/j.ijforecast.2016.02.001
- Fulton ve diğ. 2024 PVNet (ICLR CCAI #46): uydu SEVIRI + ICON-EU + geçmiş üretim geç-füzyon. https://www.climatechange.ai/papers/iclr2024/46
- ECMWF AIFS (EGU24/25; AIFS-CRPS olasılıksal); Open Data'da AIFS Single ve AIFS ENS, ssrd mevcut.
- Foundation modeller: GraphCast/GenCast (Apache-2.0 kod, CC BY 4.0), Aurora (MIT, ticari için e-posta), FourCastNet (BSD-3), NeuralGCM (Apache/CC BY-SA) — HİÇBİRİNDE yüzey ışınımı çıktısı teyit edilemedi; pratik yol AIFS.
- ARPA-E PERFORM veri seti teyit edilemedi.

## C) Veri setleri
- PVOD (Yao 2021, Solar Energy 230) — lisans teyit edilemedi
- Sheffield PV_Live (GB, 30 dk, CC BY 4.0, ticari evet) https://www.solar.sheffield.ac.uk/pvlive/
- OCF HuggingFace: uk_pv (30k sistem, CC BY 4.0 gated), dwd-icon-eu (CC BY 4.0), 22 model MIT. https://huggingface.co/openclimatefix
- NREL PVDAQ (OEDI, ~512 GB, CC BY 4.0) https://data.openei.org/submissions/4568
- Renewables.ninja: CC BY-NC 4.0 → TİCARİ HAYIR
- Energy-Charts API (Fraunhofer ISE): CC BY 4.0, atıf zorunlu, 2–20 istek/dk https://api.energy-charts.info/
- ENTSO-E Transparency şartları teyit edilemedi
- DKASC: 5.000 hücre üstü yeniden dağıtım izinli → ŞARTLI https://dkasolarcentre.com.au/download/terms-conditions
- SARAH-3 (CM SAF): 1983→, 0.05°, SIS/SID/DNI, ±65°, CC BY 4.0, DOI 10.5676/EUM_SAF_CM/SARAH/V003 — Türkiye kapsam içinde
- CAMS gridded solar radiation: 0.1°, 15 dk, 2005–2024, CC-BY https://ads.atmosphere.copernicus.eu/datasets/cams-gridded-solar-radiation
- BSRN: TÜRKİYE'DE İSTASYON YOK (PANGAEA teyitli); en yakın Lampedusa, Budapest, Romanya. SURFRAD ABD kamu malı.

## D) Ücretsiz + ticari kullanıma uygun NWP/ışınım
- ECMWF Open Data (IFS + AIFS Single + AIFS ENS): CC-BY-4.0, "yeniden dağıtılabilir ve ticari kullanılabilir, atıfla"; 0.25°, GRIB2, 00/06/12/18 UTC, 0–144 s 3 saatlik sonra 6 saatlik 240/360 s; ssrd tüm modellerde; yuvarlanan arşiv 2–3 gün → kendi arşivini biriktir. https://www.ecmwf.int/en/forecasts/datasets/open-data
- DWD ICON / ICON-EU / ICON-D2: CC BY 4.0 ("Quelle: Deutscher Wetterdienst"); aswdir_s, aswdifd_s, asob_s teyitli; kayıt yok. https://opendata.dwd.de/weather/nwp/
- NOAA GFS/GEFS/HRRR (NOMADS): kamu malı; DSWRF; ticari evet, atıf zorunlu değil. https://nomads.ncep.noaa.gov/
- Météo-France AROME 0.01° / PE ARPEGE 34 üye 0.1° (20–72°N, 32°W–42°E — Türkiye'nin batısı): Licence Ouverte 2.0, ticari evet, atıf zorunlu. https://www.data.gouv.fr/datasets/pe-arpege-eurat01
- CAMS Solar Radiation Time-Series: 2004→, 1 dk/15 dk/saatlik; GHI/BHI/BNI/DHI + clear-sky; CC-BY, DOI 10.24381/5cab0912; ticari evet. https://ads.atmosphere.copernicus.eu/datasets/cams-solar-radiation-timeseries

## Ajanın "en değerli 10": 1 ECMWF Open Data AIFS ENS+IFS ENS · 2 DWD ICON · 3 IEA Wind RP 2. baskı · 4 Yang 2020 · 5 Doubleday-Hodge 2020 · 6 Mayer & Yang 2022 · 7 BPH 4. baskı · 8 Le Gal La Salle 2025 EVC/OEV · 9 CAMS time-series · 10 Energy-Charts API
