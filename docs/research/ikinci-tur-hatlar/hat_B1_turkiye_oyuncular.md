# Hat B1 — Türkiye yerli oyuncular (ajan raporu özeti, 5 Eyl 2026)

## Kamu altyapısı
- EPİAŞ EPYS https://epys.epias.com.tr · Şeffaflık https://seffaflik.epias.com.tr · kayıt https://www.epias.com.tr/piyasa-kayit-sureci/ ; DSG verisi Şeffaflık'ta "DSG Dengesizlik Miktarı"
- EPDK tedarik lisansı sorgu (toplayıcılık/depolama filtresi) https://lisans.epdk.gov.tr/epvys-web/faces/pages/lisans/elektrikTedarik/elektrikTedarikOzetSorgula.xhtml ; 2025 sonu 28.323 lisans (snippet)
- Toplayıcılık lisansı: 2025'ten itibaren 38–47 şirket (TSKB vs ERTV tutarsız) — Artiva, Kıvanç, Met Turkey, Aktor, Maki, Perfect…
- TÜBİTAK MAM RİTM: yalnız rüzgar, 6–72 s, GFS/ECMWF/WRF+ML, olasılıksal yok https://mam.tubitak.gov.tr/enerji/urunler/ritm/ ; TEİAŞ sayfası "güneş ve rüzgar" https://www.teias.gov.tr/arge/ritm
- TEİAŞ + TÜBİTAK "Güneş Üretim Tahmin Sistemi" (26 Tem 2026 haberi): 40.000+ GES / ~26,7 GW, 6 s–3 gün, hibrit YZ, YTBS'ye entegre; olasılıksal belirtilmiyor. https://turkiyegazetesi.com.tr/ekonomi/teiastan-gunese-dijital-takip-sebeke-yonetiminde-yapay-zeka-donemi-1805282

## GES izleme / O&M SaaS (yerli)
- Solarify (Loggma): YZ izleme, iş emri, 12 alarm tipi, OSOS/EDAŞ/TEİAŞ uyumu, PPC (Ek-18); 300 kWp+; MAXIMA 370+ MW, Akfen; olasılıksal yok https://solarify.io/tr/
- Solar8 (gesizleme.com): yerli kart + YZ arıza öngörüsü, string izleme https://gesizleme.com/
- MapperX: drone termografi + izleme + bakım (IEC 62446) https://mapperx.com/santral-yonetimi/
- SolarTools: IoT + LSTM/RF/GBM üretim tahmini ("%95+"), V-I eğrisi arıza; deterministik https://www.solartools.com.tr/platform/ges-izleme
- Retgen (Rast): 2 GW+ izleme, SCADA/tracker https://retgen.com/
- SolarRelax (CNS, 2016): 100+ müşteri, 1.000+ inverter, basit üretim tahmini https://www.solarrelax.com/
- Ranaliz: enerji+GES izleme, YZ asistan tahmin; Körfez https://ranaliz.com/
- Enoptimal: GES izleme + canlı PTF + saatlik mahsuplaşma + BESS; 3.000+ tesis https://enoptimal.com/tr
- GESmetrik (Paff): 1 May 2026 saatlik mahsuplaşma için lisanssız GES gelir takibi; 100 $/sayaç/ay https://gesmetrik.com/
- Solarinsider (403), Reengen (IoT platform), SolarVeyo/Pvxis/Nu Teknoloji/Mavi Takip erişilemedi

## Üretim tahmini sağlayıcıları
- UrClimate (Alkazar): RES+GES gün öncesi, WRF + çok modelli YZ, 243 RES / 56 GES; GÜVEN BANTLARI var (tek olasılıksal öğe) https://res.urclimate.com/
- APLUS Enerji: 14 günlük saatlik/günlük tahmin, MAPE/MAE, deterministik https://aplusenerji.com.tr/raporlar/
- VTC Enerji: V-Forecast, V-Plant Manager (KGÜP/EAK otomasyonu), V-Market; enercast + Sirocco partner (15 dk) https://vtcenerji.com/
- Corius: LSTM/XGBoost/Prophet ensemble; GÖP/GİP fiyat https://corius.com.tr/sektorler/enerji
- Buluttan: hiper-yerel hava zekâsı (Zoomcast) https://www.buluttan.com/tr
- SONUÇ: P10/P90 olasılıksal GES tahminini açıkça pazarlayan yerli firma BULUNAMADI (yalnız akademik: ODTÜ, Gazi)

## DSG / portföy / toplayıcılar
- Enerjisa Üretim (en büyük DSG'lerden) https://www.enerjisauretim.com.tr/enerji-tedarigi/hizmetler
- Limak Enerji Ticaret: DSG/Toplayıcılık 30+ santral, üretim optimizasyonu, tahmin https://www.limakenerji.com.tr/hizmetlerimiz/dengeden-sorumlu-grup-toplayicilik
- Zeros Enerji: ilk toplayıcılık lisansı, 1.000 MWe+ https://www.zerosenergy.com/toplayicilik/
- Zorlu Dengeleme ve Enerji Yönetimi (23 Eki 2025 lisans); Enerjisa Müşteri Çözümleri (27 Mar 2025); Minas Enerji; Energy Pool Türkiye (EPIQ.live, Everest DERMS); enerjiticareti.com DSG danışmanlığı

## Ticaret/KGÜP yazılımı
- smartPulse (2018; Ekim 2025'te Volue satın aldı): GÖP/GİP algoritmik ticaret, 600+ santral, 20+ tahmin sağlayıcı entegrasyonu; kendi olasılıksal tahmini yok https://www.smartpulse.io/tr/

## SCADA/üretici portalları
- Huawei FusionSolar, SMA Sunny Portal, Solar-Log (resmi TR distribütör teyit edilemedi); Piagrid rehberi: FusionSolar, Sunny Portal, Solarify, Mavi Takip, Solar-Log https://www.piagrid.com/rehber/ges-uzaktan-izleme

## Yanlış aday / bulunamadı
- Solarvis = GES tasarım-teklif-CRM SaaS'ı (izleme değil) https://solarvis.co/
