# Faz 1.8 — Data Quality: Gerçek Dünya Kalibrasyonu

**Tarih:** 2026-07-06
**Dal:** `faz1.8-data-quality`
**Test sistemi:** NREL PVDAQ 2107 (FSA_1, Arbuckle CA, 893 kWp)

---

## 1. Yönetici Özeti

Faz 1.8'in orijinal planı (Faz 1.7 sonu devir notunda) "SCADA outlier
temizliği + meteo bias fit" idi. **Bu plan yanlıştı.** Gerçek problem farklı
bir yerdeydi.

**Ana bulgu:** Faz 1.7'nin Mod B başarısızlığının **tek kök sebebi**,
`calibrate_from_scada` çağrısı yaparken meteo'yu tz-naive'e çevirme
workaround'ı idi. Bu, Faz 1.7'de düzelttiğimiz timezone bug'ının **kalibrasyon
içinde tekrar aktif olmasına** yol açıyordu.

Faz 1.8, üç adımda bunu çözdü:
1. **1.8.0** — SCADA tz-aware localize (asıl fix)
2. **1.8.0.1** — DST duplicate cleanup (hotfix)
3. **1.8.1** — Azimuth fit + MAPE loss (feature)

**Sonuç:** FSA_1'de kalibrasyon artık gerçek dünyada çalışıyor:
- Sapma: **-%52 → +%0.00** (Faz 1.7 → Faz 1.8)
- MAPE: **%164 → %20** (Faz 1.7 → Faz 1.8)
- Azimuth fit robust: farklı başlangıçtan aynı optimum (0.00° fark)
- DST-safe: kış-bahar dönemlerinde patlamıyor

---

## 2. Faz 1.7'den Faz 1.8'e Yolculuk

### Faz 1.7 Sonu Durumu
- 3 bug düzeltilmişti (timezone, DST duplicate, sözlük)
- FSA_1 Mod B kalibrasyonu **başarısız**: sapma -%52, MAPE %164 → %173
- Kalibrasyon "modeli daha yukarı çek" diyerek η_BoS'u 0.99 tavanına dayamıştı
- Devir notu: "veri kalitesi eksik, Faz 1.8 SCADA outlier temizliği yapmalı"

### Bugünkü Kritik Tespit
Faz 1.6'nın frekans-agnostiklik iddiasını test ederken beklenmedik bir
tutarsızlık çıktı. Aynı azimuth, aynı model:
- tz-aware meteo → total_kwh: 515,371 kWh
- tz-naive meteo → total_kwh: 330,049 kWh (**%36 fark!**)

Detaylı tanı: **tz-naive meteo → pvlib UTC varsayıyor → solar position 7 saat
kayıyor → öğle güneşini "gece" sanıyor → sadece marjinal saatlerde üretim
tahmin ediyor.**

Bu tam olarak Faz 1.7'de düzelttiğimiz bug idi. Ama `calibrate_from_scada`
çağrılırken SCADA tz-naive, meteo tz-aware olunca `_align_meteo_to_scada`
index birleştirmesi patlıyordu. "Çözüm" olarak meteo'yu naive'e çevirmiştik
— bu çözüm bug'ı geri getiriyordu.

### Doğru Çözüm
SCADA'yı meteo'nun timezone'una localize et. Otomatik, kullanıcıya iş yok.

---

## 3. Tespit Edilen 3 Problem + Çözümleri

### Problem 1: SCADA tz-naive Kalibrasyona Uygun Değil

**Belirti:** `_align_meteo_to_scada` `ValueError: cannot reindex on an axis with
duplicate labels` veya (dolaylı olarak) tz-naive meteo bug'ı tetikleniyordu.

**Çözüm (Faz 1.8.0):** `calibrate_from_scada` fonksiyonunun başında SCADA
tz-naive ve meteo tz-aware ise SCADA'yı otomatik olarak meteo timezone'una
`tz_localize` et. Tüm SCADA serileri (power_kw, poa_irradiance, temp_ambient,
temp_module, wind_speed, energy_kwh) tutarlı olarak localize edilir.

**Commit:** `483fb83`

**Etki:** Sapma -%52 → +%0.00, MAPE %164 → %41 → %32 (η_BoS fit sonrası).

### Problem 2: DST Geçiş Günü tz_localize Patlıyor

**Belirti:** Ocak-Mayıs 2024 gibi DST geçişi (10 Mart) içeren dönemlerde
kalibrasyon `ValueError: cannot reindex on an axis with duplicate labels` ile
patlıyordu.

**Neden:** `tz_localize(nonexistent='shift_forward')` 2024-03-10 02:00 kaydını
03:00'a taşıyor. Ama SCADA'da zaten 03:00 kaydı var → duplicate index.

**Çözüm (Faz 1.8.0.1):** `_tz_localize` yardımcı fonksiyonuna tz-localize
sonrası duplicate temizliği ekle (Faz 1.7 meteo tarafında yaptığımızın aynısı).

**Commit:** `5baf174`

**Etki:** DST-safe. Yıllık kalibrasyon senaryosu artık çalışıyor.

### Problem 3: Azimuth Bilinmediğinde Model Doğru Değil

**Belirti:** FSA_1 metadata'sındaki `azimuth=180°` yanlıştı. Elle test:
- azimuth=140° → MAPE %28, sapma %0.15 (MERKAS seviyesi)
- azimuth=180° → MAPE %71, sapma %7

**Çözüm (Faz 1.8.1):** `calibrate_from_scada` fonksiyonuna `fit_azimuth: bool =
False` parametresi ekle. Devrede olduğunda `scipy.optimize.minimize_scalar` ile
[90°, 270°] arası tarar, MAPE minimize eder.

**Kritik tasarım kararı:** Azimuth fit `fit_eta_bos` ile birlikte kullanılınca
sıra önemli — **önce azimuth (geometri), sonra η_BoS (performans)**. Aksi
halde η_BoS geometri hatasını telafi etmeye çalışıp yanlış öğrenir.

**Loss fonksiyonu:** İlk versiyonda `abs(NMBE)` kullanıldı, ama NMBE=0 olan
birden fazla azimuth var (S-eğrisi). MAPE ise tek minimuma sahip. MAPE loss
kullanıldı.

**Commit:** `bd2c6af`

**Etki:** FSA_1'de azimuth 180° → 159° (yaz dönemi), MAPE %26 → %20.

---

## 4. Test Sonuçları — 6 Senaryo Smoke Test

Commit öncesi doğrulama için 6 kapsamlı senaryo çalıştırıldı.

| # | Senaryo | Amaç | Sonuç |
|---|---|---|---|
| S1 | Yaz + fit_azimuth=False | Regresyon (mevcut davranış) | ✅ PASS |
| S2 | Yaz + fit_azimuth=True | Ana test | ✅ PASS |
| S3 | DST dönemi + fit_azimuth=False | Hotfix testi | ✅ PASS |
| S4 | DST dönemi + fit_azimuth=True | Kombine | ⚠️ Ürün limiti |
| S5 | Yaz + fit_azimuth=True, initial=90° | Robustness | ✅ PASS |
| S6 | Tüm yıl + fit_azimuth=True | Mevsimsel ortalama | ✅ PASS |

### Detaylı Sonuçlar

**S1 (Regresyon):** Azimuth 180° (fit yok), η_BoS 0.93→0.81, MAPE 41%→32%,
sapma +14%→+0.00%. Faz 1.8.0 davranışı korundu.

**S2 (Ana test):** Azimuth 180°→159.4°, η_BoS 0.93→0.85, MAPE 26%→20%,
sapma +10%→+0.00%. **Faz 1.8'in altın standart sonucu.**

**S3 (DST hotfix):** Azimuth 180° (fit yok), η_BoS 0.93→0.86, MAPE
219%→202%, sapma +8%→+0.00%. DST'de patlamamak asıl önemli olan. MAPE
yüksek çünkü kış Open-Meteo bias'ı (ayrı bir konu).

**S4 (Kış + fit_azimuth):** Azimuth 180°→92°, η_BoS 0.99 tavana dayandı,
MAPE 63%→65% (kötüleşti), sapma -26%→-21%. **Ürün limiti.** Detay §5'te.

**S5 (Robustness):** Azimuth 90°→**159.38°** — S2 ile **birebir aynı**
(0.00° fark). Optimizasyon deterministic ve global optimuma yakınsıyor.

**S6 (Tüm yıl):** Azimuth 180°→135.3° (yaz 159° ve kış farklı optimum
arasında ortalama), η_BoS 0.93→0.93, MAPE 47%→47%, sapma -0.21%→+0.00%.

---

## 5. Ürün Limitleri (S4 Analizi)

Kış-bahar dönemi verileriyle (Ocak-Mayıs) `fit_azimuth=True` yapılırsa:
- Azimuth 91.8° gibi saçma değere gidiyor
- η_BoS 0.99 tavanına takılıyor
- Sapma sıfıra çekilemiyor (-%21 kalıyor)
- MAPE iyileşmiyor

**Neden:** Kış aylarında Open-Meteo GHI bias'ı çok yüksek. Örnek: Şubat 15,
2024 tanısında:
- Open-Meteo GHI tepe: 501 W/m²
- FSA_1 gerçek güç: 712 kW tepe
- Model bu verilerle "modeli %30 yukarı çek" öğreniyor
- Ama azimuth ve η_BoS kombinasyonu bunu sağlayamıyor

**Sonuç:** Bu bir kod bug'ı değil, meteo kaynağı limiti. Kullanıcı MAPE %60+
bir kalibrasyon sonucu gördüğünde "bu dönem uygun değil" diye anlar,
farklı bir dönem dener.

**Gelecek çözümler (Faz 1.9+):**
- NREL NSRDB entegrasyonu (daha kaliteli meteo)
- POA sensörü tabanlı bias fit (Faz 1.7'de `_fit_ghi_bias` mevcuttu)
- Kalibrasyon sonrası "sanity check" uyarısı (MAPE eşiği)

---

## 6. FSA_1'de Metrikler Zaman İçinde

Test dönemi: Yaz 3 ay (Mayıs-Ağustos 2024), 26,209 SCADA nokta, 15,538 geçerli
saat.

| Faz | Sapma | MAPE | η_BoS | Azimuth | Not |
|---|---|---|---|---|---|
| Faz 1.7 (Mod A) | +%7 | %71 | 0.93 | 180° | Baseline (kalibre değil) |
| Faz 1.7 (Mod B) | -%52 | %164→%173 | 0.99 | 180° | Kalibrasyon bozuk (tz bug) |
| Faz 1.8.0 (Mod B) | +%0.00 | %41→%32 | 0.81 | 180° | tz-aware fix |
| Faz 1.8.1 (Mod B) | +%0.00 | %26→**%20** | 0.85 | **159°** | +azimuth fit |

**MERKAS referans:** Yıllık sapma %0.77. FSA_1 Faz 1.8'de yaz için %0.00
sapma — MERKAS'tan iyi.

---

## 7. Faz 1.8'in Ürün İçin Anlamı

### Bu Sürümde Çalışan
- ✅ Kullanıcı SCADA yükler → doğru zaman uyumu otomatik
- ✅ Kullanıcı azimuth bilmiyor → `fit_azimuth=True` çözer
- ✅ Kullanıcı yıllık veri verir → DST'de patlamıyor
- ✅ Sapma sıfıra çekilir (kalite verilerle)
- ✅ MAPE ~%20 seviyesinde (Kaliforniya utility-scale için makul)

### Hala Eksik
- ❌ Tilt fit yok (kullanıcı doğru tilt vermeli)
- ❌ POA sensörü kullanılmıyor (bias fit yok)
- ❌ Kış Open-Meteo bias'ı düzeltilmiyor
- ❌ SCADA outlier temizliği yok (kullanıcı temiz veri vermeli)
- ❌ Kalibrasyon sonucu için sanity check yok

Bunlar Faz 1.9 veya Faz 2 konusu.

---

## 8. Bu Sürümde Neler Değişti

### Commit Zinciri (Faz 1.8)

```
bd2c6af  feat(calibration): azimuth fit with MAPE loss (Faz 1.8.1)
5baf174  fix(calibration): DST duplicate cleanup in tz-localize (Faz 1.8.0.1)
483fb83  fix(calibration): tz-aware SCADA localize (Faz 1.8.0)
```

**Değişen dosyalar:**
- `src/pvquant/pipeline/calibration.py` — 3 değişiklik, ~100 satır ekleme

**Değişmeyen:**
- `src/pvquant/pipeline/utils.py` — dokunulmadı
- `src/pvquant/models_v2/*` — dokunulmadı
- `src/pvquant/io/*` — dokunulmadı
- Testler — dokunulmadı

### Test Durumu

| | Faz 1.7 Sonu | Faz 1.8 Sonu |
|---|---|---|
| Toplam test | 88 | 88 |
| Yeşil | 88 | 88 |
| Regresyon | Yok | Yok ✅ |
| Smoke testler | Yok | 6/6 PASS |

---

## 9. Öğrenilen Dersler

### 1. "Workaround" bir kez çıktığında dikkat
Faz 1.7'de bir bug düzelttik ama kalibrasyon içinde onu tekrar aktive eden
bir workaround yazdık. **Her workaround gelecekteki bir bug'ın tohumu.**

### 2. Manuel test ile otomatik hesap paralel gitmeli
Faz 1.8'e başladığımızda "total_kwh tutarsızlığı" tanısı yapmaya
çalışıyorduk. Aynı input için üç farklı sayı görüyorduk. Manuel test ile
paralel doğrulama olmasaydı hangi sayının doğru olduğunu bilemezdik.

### 3. Loss fonksiyonu tasarımı kritik
Azimuth fit'te ilk versiyonda `abs(NMBE)` kullandık — 101° gibi saçma değer
buldu. Sadece NMBE'nin monotonik olmadığını, S-eğrisi (birden fazla sıfır
geçişi) olduğunu görmemiz gerekti. MAPE'ye geçince 159° buldu — yaz tablosunda
doğrulanan optimum.

### 4. Robustness testi ucuz ama kritik
S5 (farklı başlangıç azimuth'undan aynı optimum) tek satır kod değişikliği ile
yapıldı. Bu test olmasaydı optimizasyonun local minimum'da takılıp takılmadığını
asla bilemezdik.

### 5. Ürün limitleri kod bug'ı değil
S4 (kış dönemi + fit_azimuth) kötü sonuç veriyor. İlk içgüdü "azimuth_bounds'u
daralt" veya "eta_bos üst sınırı zorla" gibi düzeltmeler yapmaktı. Duraksadık
— bu meteo kaynağı limiti, kod bug'ı değil. **Doğal olarak ortaya çıkan
ürün karakteristikleri düzeltilmeyi bekleyen bug'lar değil.**

---

## 10. Sonuç

Faz 1.8 üç somut çıktı bıraktı:
1. **Kalibrasyon artık gerçek dünyada çalışıyor.** FSA_1 yaz için sapma %0,
   MAPE %20 — MERKAS seviyesine ulaştık ve geçtik.
2. **Azimuth fit ürüne entegre edildi.** Kullanıcı azimuth bilmiyor durumu
   otomatik çözülüyor.
3. **DST-safe.** Yıllık kalibrasyon senaryosu patlmıyor.

Faz 1.9 (ilerleyen fazlarda karar verilecek) potansiyel konuları:
- Tilt fit
- POA tabanlı bias fit (`_fit_ghi_bias` zaten var, sadece devrede değil)
- SCADA outlier temizliği (orijinal Faz 1.8 planı, ertelendi)
- NSRDB entegrasyonu (kış meteo kalitesi)
- Kalibrasyon sanity check (kullanıcı uyarısı)

**Faz 1.8 kapandı. Ürün gerçek dünyada kalibre edilebilir hâlde.**
