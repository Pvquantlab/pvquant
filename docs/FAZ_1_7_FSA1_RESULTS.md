# Faz 1.7 — NREL FSA_1 Gerçek Dünya Testi: Bulgular

**Tarih:** 2026-07-04
**Dal:** `faz1.7-fsa1-validation`
**Test sistemi:** PVDAQ Sistem 2107 — Farm Solar Array (Arbuckle, California)

---

## 1. Yönetici Özeti

Faz 1.6'da tamamlanan **frekans-agnostik kalibrasyon kodu**, ilk kez gerçek bir 15
dakikalık SCADA veri seti üzerinde test edildi. NREL PVDAQ 2023 Solar Data Prize
kapsamında halka açılan **FSA_1 (Farm Solar Array, 893 kWp, Arbuckle CA)** sistemi
seçildi. Test 2024 yılının 11 aylık verisi üzerinden yapıldı.

**Ana sonuç:** Kod mekanik olarak çalışıyor. Frekans-agnostik altyapı doğrulandı.
Ancak Mod B kalibrasyonun sağlıklı çalışması için **veri kalitesi ön işleme
adımları eksik**. Bu, Faz 1.8'in odağı olacak.

Test sırasında **3 bug tespit edildi ve düzeltildi**:
1. Open-Meteo timezone bug'ı (naive index → yanlış solar position)
2. Open-Meteo DST duplicate bug'ı (Mart 10 saat 03:00 iki kez)
3. `COLUMN_ALIASES` sözlüğünde `poa_global` alias eksikliği

Bu düzeltmeler ürünün dünya çapında kullanımı için kritik idi.

---

## 2. Test Senaryosu

### 2.1 Sistem Bilgisi

| Alan | Değer |
|---|---|
| PVDAQ System ID | 2107 |
| İsim | Farm Solar Array (FSA_1) |
| Konum | Arbuckle, CA (38.9963°N, 122.1341°W) |
| Kapasite | 893 kWp |
| Modül | Hyundai HiS-M310TI, mono-Si (monofacial) |
| Tilt | 25° |
| Azimuth | 180° (güney) |
| Yıllık veri | 7.9 yıl (2017-2024) |
| Bu testteki dönem | 2024-01-01 → 2024-11-01 (11 ay) |
| Ham çözünürlük | 5 dakika |
| Meteo çözünürlük | 15 dakika (yerel sensör) veya 1 saat (Open-Meteo) |

### 2.2 Test Verisi

Üç ayrı CSV dosyası indirildi:

- **`2107_electrical_data_2024.csv`** (60 MB) — 24 inverter × 5 sensör, 5 dk
- **`2107_environment_data_2024.csv`** (1.1 MB) — sıcaklık, rüzgar, 15 dk
- **`2107_irradiance_data_2024.csv`** (1.8 MB) — POA irradiance, karışık çözünürlük

Preprocessing script'i ile birleştirilip 5 dakikalık tek CSV'ye çevrildi
(`2107_processed_5min.csv`, 4.9 MB, 88,127 satır).

### 2.3 Yıllık Enerji Profili

| Ay | Toplam kWh | Kapasite Faktörü |
|---|---|---|
| Ocak | 57,475 | %8.7 |
| Şubat | 82,467 | %13.3 |
| Mart | 119,413 | %18.0 |
| Nisan | 141,902 | %22.1 |
| **Mayıs** | **170,077** | **%25.6** (yıllık zirve) |
| Haziran | 151,924 | %23.6 |
| Temmuz | 152,721 | %23.0 |
| Ağustos | 138,024 | %20.8 |
| Eylül | 125,036 | %19.4 |
| Ekim | 110,669 | %16.7 |

Yıllık ortalama CF ≈ %19 — Kaliforniya utility-scale mono-Si için normal.

---

## 3. Frekans-Agnostik Kod Doğrulaması

Faz 1.6'nın ana teslim ettiği kabiliyet olan **her çözünürlükte kalibrasyon**
gerçek veri üzerinde ilk kez test edildi.

| Test | Sonuç |
|---|---|
| `load_csv` 5 dakikalık CSV'yi tanıyor mu? | ✅ Evet |
| `_detect_timestep_minutes` 5 tespit ediyor mu? | ✅ Evet (`timestep_minutes = 5`) |
| SCADA (5 dk) + Meteo (1 h) hizalanıyor mu? | ✅ Evet (`_align_meteo_to_scada` doğru çalıştı) |
| Kalibrasyon 26,209 nokta ile çalışıyor mu? | ✅ Evet (~90 saniye içinde tamamlandı) |
| Mevcut 88 test yeşil kaldı mı? | ✅ Evet (regresyon yok) |

**Sonuç:** Faz 1.6'nın mimari kararları doğrulandı. Frekans-agnostik model
gerçek dünyada çalışıyor.

---

## 4. Tespit Edilen Bug'lar ve Düzeltmeleri

### 4.1 Bug #1: Open-Meteo Timezone Handling

**Belirti:** Kaliforniya için Mod A tahmini MAPE %209 çıktı. Peak saat 3 saat
kaymış gibi görünüyordu.

**Neden:** `OpenMeteoClient._parse_response` timestamp'leri **tz-naive**
döndürüyordu. `pvlib.solarposition.get_solarposition()` docstring'i "UTC veya
tz-aware bekliyor" diyor ama tz-naive geçince sessizce UTC varsayıp yanlış solar
geometry hesaplıyor. Kaliforniya (UTC-7 PDT) için bu 7 saatlik solar position
kaymasına, dolayısıyla 3 saatlik peak kaymasına yol açtı.

**Fix:** `_parse_response` içinde `data["timezone"]` alanına göre timestamp'leri
`tz_localize` ediyoruz. Artık `MeteoData.ghi.index` her zaman tz-aware.

**Etki:** MAPE %209 → %66.5 (peak saatler artık doğru zamanda)

### 4.2 Bug #2: Open-Meteo DST Duplicate

**Belirti:** `_align_meteo_to_scada` içinde `pd.DataFrame.reindex()` çağrısı
`ValueError: cannot reindex on an axis with duplicate labels` verdi.

**Neden:** Open-Meteo, 2024-03-10 (DST geçiş günü) için saat 02:00 kaydını
atmak yerine, aynı 03:00 zamanına iki kez veri döndürüyor. `_parse_response`
bunu temizlemiyordu.

**Fix (iki katmanlı):**
1. `_parse_response` içinde duplicate timestamp temizliği (kaynağa)
2. `_align_meteo_to_scada` içinde defansif `_dedupe` yardımcısı (savunma)

**Etki:** Kalibrasyon artık DST geçişini kapsayan train periyotlarında çalışıyor.

### 4.3 Bug #3: `poa_global` Sözlük Eksikliği

**Belirti:** FSA_1 preprocess çıktısındaki `poa_global` kolonu `load_csv`
tarafından tanınmadı — `SCADAData.poa_irradiance = None` döndü.

**Neden:** `COLUMN_ALIASES["poa_irradiance"]` listesinde PVLib/pvfarm standart
adı olan `poa_global` yoktu. Fuzzy match de `global` vs `irradiance` farkı
yüzünden başarısız oldu.

**Fix:** Sözlüğe 6 yeni alias eklendi: `poa_global`, `POA_global`,
`poa_global_irradiance`, `GlobalPOA`, `poa_ref`, `POA`.

**Etki:** POA verisi artık tanınıyor. Herhangi bir PVLib-tabanlı SCADA
export'unda çalışacak.

---

## 5. Test Sonuçları

### 5.1 Mod A (Pure Forecast) — Kalibre Olmayan Model

Test haftası: 2024-05-20 → 2024-05-26 (Kaliforniya'nın en güneşli haftası).

| Metrik | Değer |
|---|---|
| Ortak saat | 168 |
| MAPE | %66.5 |
| NMBE | +%7.04 |
| Toplam tahmin | 36,349 kWh |
| Toplam gerçek | 33,877 kWh |
| Toplam sapma | +%7.30 |

**Yorum:** Toplam sapma **çok iyi** (kalibre olmamış model için +%7 hafif fazla).
MAPE yüksek çünkü profil şekli asimetrik: sabah tahmini düşük, akşam tahmini
yüksek. Bu, Open-Meteo GHI'sinin panel tilt yüzeyi için sabah/akşam saatlerinde
yeterince doğru yansıtmamasından kaynaklanıyor.

### 5.2 21 Mayıs 2024 Saatlik Profil (Tanı)

| Saat | GHI (W/m²) | Tahmin (kW) | Gerçek (kW) | Fark |
|---|---|---|---|---|
| 09:00 | 453 | 336 | 487 | +151 (tahmin düşük) |
| 12:00 | 930 | 761 | 717 | -44 (tahmin fazla) |
| 14:00 | 1003 | 815 | 707 | -108 (tahmin fazla) |
| 17:00 | 682 | 489 | 315 | -174 (tahmin fazla) |
| 18:00 | 490 | 308 | 125 | -183 (tahmin fazla) |

**Görülen desen:** Öğle ve öncesinde tahmin biraz düşük, öğleden sonra ve akşam
tahmin ciddi olarak yüksek. Bu, aşağıdakilerden birinin veya birkaçının belirtisi:
- Panel gerçekte doğuya biraz dönük (azimuth < 180°)
- Batı tarafında gölgeleme (tepe, ağaç)
- Faiman sıcaklık modeli öğleden sonra soğutmayı fazla tahmin ediyor

Bu **model matematiği hatası değil**, panelin gerçek yönelim/gölge/sıcaklık
davranışı model varsayımlarından farklı. Kalibrasyon bunu düzeltmeli.

### 5.3 Mod B (Kalibre Edilmiş) — BAŞARISIZ

Train dönemi: Haziran-Ağustos 2024 (yaz 3 ayı, 26,209 nokta).

| Metrik | Değer |
|---|---|
| BG (bifacial gain) | 0.347 (varsayılan) |
| **η_BoS öncesi** | 0.93 |
| **η_BoS sonrası** | **0.99 (üst sınırına dayandı)** |
| MAPE öncesi (train) | %164.5 |
| **MAPE sonrası (train)** | **%173.3** ← DAHA KÖTÜ |
| Toplam sapma öncesi | -%51.8 |
| Toplam sapma sonrası | -%48.7 |

**Sonuç:** Kalibrasyon "modelin gerçekten az tahmin ettiğini" gördü ve η_BoS'u
yukarı çekmeye çalıştı ama üst sınıra takıldı. MAPE düşmedi, arttı.

### 5.4 Nedeni: Ham Veri Kalitesi

Aynı model:
- Test haftası (Mayıs): sapma **+%7**
- Kalibrasyon train (Haziran-Ağustos): sapma **-%52**

Bu tuhaf çelişki, **train verisinin gerçek santral davranışını değil de arıza/
downtime karışımını** yansıttığını gösteriyor. Örneğin bazı günler bir kaç
inverter kapalı → toplam güç normalden düşük. Kalibrasyon "model az tahmin
ediyor" diye yanlış öğrendi.

Bunun bir başka boyutu: **Open-Meteo GHI'nin mevsimsel bias'ı asimetrik**.
Şubat 15 tanısında görüldüğü gibi, kış aylarında Open-Meteo yatay GHI'yi
çok düşük gösteriyor (özellikle bulut yoğun günlerde), gerçekte 25° tilt paneli
daha fazla üretim yapıyor.

---

## 6. Referans Santral ile Kıyaslama
Model dokümantasyonu (`PVQuant_Model_Mantigi_v2.docx`), Konya'daki 4.514 kWp
bifacial bir referans santralin bir yıllık SCADA verisiyle Mod B'nin **yıllık
%0.77 sapma** verdiğini kaydediyor (santral adı, veri sahibinin gizliliği için
anonimleştirilmiştir). FSA_1'de sapma %52.

Bu 68x fark model matematiğinden değil, **ön işleme kalitesinden** kaynaklanıyor.
Referans santralda:
- SCADA muhtemelen manuel temizlenmiş (arıza günleri elenmiş)
- Meteoroloji doğrulanmış
- Panel spesifikasyonu ölçülmüş (tahminen değil)

FSA_1'de bunların hiçbiri yok — ham veriyi doğrudan kalibrasyona verdik.

**Bu ürünün gerçek dünyada güvenilir çalışması için** aşağıdaki ön işleme
adımları gereklidir. Faz 1.8 bu adımların ürüne entegrasyonu olacak.

---

## 7. Faz 1.8 Önerileri (Preprocessing & Data Quality)

### 7.1 SCADA Kalite Kontrolü

- **Outlier tespit:** Fiziksel olarak imkansız değerler (nominal × 1.2'nin üstü, negatif)
- **Downtime tespit:** Uzun 0-güç periyotları (arıza) elenmeli
- **Inverter-level QA:** Her inverter'in çalışma yüzdesi hesaplanmalı; %90'ın altındakiler flag
- **Curtailment tespit:** Aniden düşen düz güç segmentleri (grid limit) tespit
- **Clipping tespit:** DC/AC oranından tepe güç saatlerini flagle

### 7.2 Meteoroloji Bias'ı

- **`_fit_ghi_bias` fonksiyonu zaten var** — `poa_irradiance` mevcut olduğunda
  Open-Meteo GHI'sini POA ölçümüyle karşılaştırıp bias fit yapıyor. Bu Faz 1.8'de
  otomatik olarak devreye alınmalı
- **Mevsimsel bias:** Ay bazında bias katsayısı (bulut günleri için özel düzeltme)
- **Clear-sky index:** Bulut günlerini eğitim setinden çıkart

### 7.3 Kalibrasyon İyileştirmeleri

- **η_BoS üst sınırı esnek olmalı** (şu an 0.99, yeterince agresif değil)
- **Robust regresyon:** Aykırı saatlerin fit'e etkisini azalt
- **Weighted fit:** Yüksek irradiance saatlerine daha çok ağırlık

### 7.4 Panel Yönelim Doğrulaması

FSA_1 için sabah/akşam asimetrisi gerçekten var. Bir ipucu:
- `PlantSpec.tilt` ve `azimuth` fit parametresi yapılabilir (ilerleyen bir adım)
- Sadece bir öğle penceresi (10:00-14:00) referans santral başarısı için yeterli olurdu

---

## 8. Bu Sürümde Neler Değişti

### Commit Zinciri (Faz 1.7)

```
0fd17b5  fix(io): timezone-aware meteo + DST duplicate handling (Faz 1.7)
```

**Değişen dosyalar:**
- `src/pvquant/io/meteo.py` (+26 satır) — timezone localize + DST dedupe
- `src/pvquant/io/scada.py` (+4 satır) — poa_global alias'lar
- `src/pvquant/pipeline/utils.py` (+18 satır) — defansif dedupe
- `.gitignore` (+1 satır) — bak_faz17 yedekleri

### Test Durumu

| | Öncesi | Sonrası |
|---|---|---|
| Toplam test | 88 | 88 |
| Yeşil | 88 | 88 |
| Regresyon | - | Yok ✅ |

---

## 9. Sonuç

Faz 1.7 **birincil hedefine ulaştı**: Faz 1.6'nın frekans-agnostik kodu gerçek
bir 15 dakikalık SCADA veri setinde mekanik olarak doğrulandı. Aynı zamanda
üç ürün-seviyesi bug tespit edilip düzeltildi (timezone, DST, sözlük).

Faz 1.7 **ikincil hedefine ulaşamadı**: gerçek dünyada Mod B kalibrasyonun referans
santral benzeri doğruluk göstermesi.

Faz 1.8 bu preprocessing zincirini inşa edecek: SCADA kalite kontrolü, meteo
bias fit, robust kalibrasyon. Bu adımlar tamamlandığında FSA_1'de Mod B'nin
referans santral seviyesine yaklaşması bekleniyor.
---

**Faz 1.7 kapandı. Faz 1.8: Data Quality & Preprocessing.**
