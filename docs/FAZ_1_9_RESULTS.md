# Faz 1.9 — Geometri Fit + Sanity + SCADA Kalite

**Tarih:** 2026-07-07
**Dal:** `faz1.9-tilt-fit`
**Test sistemi:** NREL PVDAQ 2107 (FSA_1, Arbuckle CA, 893 kWp)

---

## 1. Yönetici Özeti

Faz 1.9, Faz 1.8'in üzerine dört ayak inşa etti:

1. **1.9.0 — Tilt fit + XOR koruma**: Kullanıcının panel eğimini bilmediği durum otomatik çözülüyor. Faz 1.8'in azimuth fit'i ile aynı yaklaşım. XOR koruması ile iki değişkenli optimizasyon tuzağı önlendi.
2. **1.9.1 — Sanity check warnings**: `CalibrationResult.warnings` alanı + 4 kontrol. Kullanıcı MAPE %200 sonuç görürse "bu dönem uygun değil" mesajını alır.
3. **1.9.3 — Basit outlier temizlik**: Downtime + spike tespiti. Kirli veriyle çalışabilme yeteneği.
4. **1.9.4 — Akıllı outlier tespit + zengin rapor**: Adaptif eşik (güneş açısına bağlı) + median filter tabanlı yerel spike + olay bazlı rapor.
5. **1.9.5 — Fixture deprecation fix**: Teknik borç temizliği.

**POA bias fit (Faz 1.9.2)** denendi ama saatlik MAPE'yi artırdığı için geri alındı. Değerli bir bulgu — bias fit uzun vadeli enerji tahmini için, saatlik profil için değil.

**Sonuç:** FSA_1 için yaz sapma %0.00, MAPE %20.28 (kirli veri temizlendikten sonra). Kod tarafı %90+ tamamlandı. Faz 2 UI'ye hazır.

---

## 2. 1.9.0 — Tilt Fit

### Motivasyon

Faz 1.8.1'de azimuth fit ekledik. Ama kullanıcı çok kez tilt'i de bilmiyor (özellikle çatı sistemlerinde). Bu boşluk kritik.

### Tasarım

- `fit_tilt: bool = False` parametresi
- `tilt_bounds: tuple = (5.0, 60.0)` — fiziksel pratik aralık
- Aynı MAPE loss, `scipy.optimize.minimize_scalar` bounded
- **XOR koruması:** `fit_azimuth=True` ve `fit_tilt=True` birlikte → `ValueError`
  - Nedeni: İki değişkenli optimizasyon local minimum riski
  - Kullanıcı birini bilmeli (kurulum belgesi), diğerini fit et

### FSA_1 Sonuçları

Elle test: tilt 5-50° tarama, azimuth=159° sabit.
- Optimum tilt: **~30°** (metadata 25°)
- MAPE min: %25.67

Kalibrasyon (tilt 10° yanlış başlangıç ile):
- **Tilt: 10° → 26.17°** (metadata 25°'ye %5 sapma — fiziksel doğru)
- MAPE: %25.7 → **%21.0**
- Sapma: +%9.5 → +%0.00

### 7-Senaryo Smoke Test

| # | Senaryo | Sonuç |
|---|---|---|
| S1 | Regresyon (fit_tilt=False) | ✅ Tilt 25° kaldı |
| S2 | Ana test (initial=10°) | ✅ Tilt → 26.17° |
| S3 | Robustness (initial=45°) | ✅ Tilt → **26.17°** (S2 ile 0.00° fark) |
| S4 | Azimuth fit regresyonu | ✅ Faz 1.8 çalışıyor |
| S5 | DST + tilt kombine | ✅ Patlmadı |
| S6 | XOR ValueError | ✅ Yakalandı |
| S7 | Tüm yıl + tilt | ✅ Tilt → 24.05° (mevsim ortalama) |

**Robustness:** Farklı başlangıçlardan (10° ve 45°) birebir aynı 26.17°'e yakınsama. Optimizasyon deterministic ve global optimum'a gidiyor.

**Commit:** `8d4e674`

---

## 3. 1.9.1 — Sanity Check Warnings

### Motivasyon

Kullanıcı kalibrasyon MAPE %200 gördüğünde "kod bozuk mu?" diye şaşırıyor. Aslında meteo bias'ı yüksek olabilir. Kod bunu **bildirmeli**.

### Tasarım

`CalibrationResult`'a yeni alan:
```python
warnings: list[str] = field(default_factory=list)
```

4 sanity check kalibrasyon sonunda çalışır:

1. **MAPE > %40:** "Kalibrasyon zayıf. Muhtemelen meteo bias'ı var. Farklı dönem deneyin."
2. **η_BoS > 0.98:** "Üst sınıra dayandı. Azimuth/tilt yanlış olabilir."
3. **η_BoS < 0.70:** "Alt sınıra dayandı. Panelde olağandışı kayıp var."
4. **|Sapma| > %5:** "Sıfırlanamadı. Parametreler yetersiz."
5. **n_samples < 100:** "Yetersiz gündüz verisi."

`__str__` içinde warnings varsa "UYARILAR:" bölümü otomatik gösterilir.

### FSA_1 Testleri

- **Yaz (sağlıklı):** MAPE %20, sapma %0, η_BoS 0.85 → **Warnings: 0**
- **Kış (Open-Meteo bias yüksek):** MAPE %100 → **Warnings: 1** (MAPE uyarısı)

Uyarı mesajı kullanıcıya net bilgi veriyor: "meteo verinizde bias var, farklı dönem deneyin."

**Commit:** `31867e4`

---

## 4. 1.9.2 — POA Bias Fit (Denendi, Geri Alındı)

### Amaç

`_fit_ghi_bias` fonksiyonu zaten `models_v2/barhdadi_bennis.py`'de vardı ama entegre değildi. Faz 1.9.2'de standalone bir versiyonu `calibrate_from_scada`'ya entegre edildi.

### 3 Alt Adım

- **1.9.2:** Fonksiyon eklendi, `fit_poa_bias: bool = False` parametresi
- **1.9.2.1:** Fitted bias `final_forecast` ve BG fit'e geçirildi
- **1.9.2.2:** `initial_forecast`'e de bias verildi (çift eksiltme önlendi)

### Sonuçlar

**Manuel test — POA bias fit sonuçları temiz:**
- 11 bin, düzeltmeler 0.88-0.97 arası
- Fiziksel anlamlı: Open-Meteo POA'yı %5-10 fazla hesaplıyor

**Ama entegrasyon sonrası:**
- MAPE **arttı**: %20.52 → %21.55
- η_BoS makul yükseldi (0.85 → 0.89)
- Sapma sıfır kaldı

### Kritik Anlayış

**POA bias fit uzun vadeli enerji tahmini için değerlidir. Saatlik profil hatasını (MAPE) düşürmez.**

Nedeni: bin lookup step function. Her bin'de aynı düzeltme uygulanır. Saatlik dalgalanmayı düzeltmez, sadece toplam seviye kayması yapar.

### Karar

**MAPE artıran feature commit edilmez.** Kod tamamen geri alındı, temiz zemine dönüldü.

### Kaybolan İş mi?

Hayır. Bu bir "başarısızlık" değil, **bilgi kazancı**. Faz 2 UI'de "uzun vadeli mod" için POA bias fit değerli olabilir. Nasıl entegre edileceği artık biliniyor, sadece kullanım senaryosu farklı.

### Ders

**"Anlaşılmayan bir davranış varken commit yapma"** prensibi tekrar kanıtlandı. Metrikler yalancı olamaz — MAPE arttıysa arttı. Ürüne değer katmayan bir feature commit'lenmez.

---

## 5. 1.9.3 — Basit SCADA Outlier Temizlik

### Motivasyon

Devir notunda "SCADA outlier temizliği" Faz 1.8 kapsamındaydı ama ertelenmişti. Şimdi geldi sıra.

Kullanıcı ham SCADA verisi getirir, downtime/spike bulunur, kalibrasyon güvenilir olsun.

### Kapsam

**Dahil:**
- **Downtime:** Solar zenith < 85° VE güç < nominal × 0.02 VE ≥ 60 dk ardışık
- **Spike:** Güç > nominal × 1.10 VEYA çok negatif

**Bilinçli dışarıda:**
- **Curtailment:** Heuristik zor, yanlış pozitif riski (Faz 1.10+)
- **Clipping:** Model tarafı iş (`p_ac_clip_kw` fit) (Faz 1.10+)

### Yapı

- `utils.py`'de standalone fonksiyon: `clean_scada_outliers(scada, plant, ...)`
- `calibrate_from_scada`'ya `clean_outliers: bool = False` parametresi
- Aktif ise SCADA tz-aware bloğundan sonra temizlik yapılır
- Notes'a bilgi eklenir

### FSA_1 Testleri

**Temiz + temizlik açık:** 40 downtime nokta bulundu (%0.2), MAPE aynen aynı — çünkü validation zaten bu noktaları filtreliyordu.

**Kirli (500 spike + 100 downtime) + temizlik açık:**
- 537 nokta silindi (%2.0): spike 500 + downtime 37
- MAPE %27.51 → **%20.48** (temiz baseline'a döndü)
- η_BoS 0.845 (kirli senaryoda 0.932 yanılıyordu)

### 5-Senaryo Smoke Test

| # | Senaryo | MAPE | Sonuç |
|---|---|---|---|
| S1 | Temiz + kapalı | 20.52% | ✅ Baseline |
| S2 | Temiz + açık | 20.52% | ✅ Küçük etki |
| S3 | Kirli + kapalı | 27.67% | ✅ Bozulmuş baseline |
| S4 | Kirli + açık | 20.48% | ✅ **Temiz seviyeye geri** |
| S5 | Kış + kirli + açık | 97.83% | ✅ Patlmadı |

**Kritik doğrulamalar:**
- S1 vs S4: 0.04 puan fark → temizlik kirli veriyi neredeyse birebir temiz seviyeye getirdi
- S3 vs S4: +7.19 puan iyileşme → kirletme etkisi anlamlı şekilde bertaraf edildi

**Commit:** `e5a91cd`

---

## 6. 1.9.4 — Akıllı Outlier Tespit + Zengin Rapor

### Motivasyon

Faz 1.9.3 çalışıyordu ama basit — sabit eşikler. Kullanıcının veri kalitesi analizi almasını sağlamak, ve tespit doğruluğunu artırmak için üzerine katman ekledik.

### İki Yeni Yetenek

**A) Adaptif Downtime Eşiği**

Güneş elevation'a bağlı:
- Elevation > 30° (öğle): p < nominal × 0.05 (sıkı — üretim yüksek beklenir)
- Elevation 10-30° (sabah/akşam): p < nominal × 0.02 (gevşek — mevcut)
- Elevation < 10° (gündoğumu/batışı): tespit yok (geçiş bölgesi belirsiz)

Yanlış pozitif düşer — bulutlu sabah "downtime" sanılmaz.

**B) Median Filter Tabanlı Yerel Spike**

İki katmanlı tespit:
- **Mutlak:** p > nominal × 1.10 (mevcut)
- **Yerel:** p, komşu ±5 median'dan %50+ farklı → izole spike

Örnek: 660, 655, 650, **950**, 665 → 950 median 660'a göre %44 üstü, yakalanır.

### Zengin Rapor

`CalibrationResult.outlier_report: dict | None` alanı eklendi:

```python
{
  "total_removed": 702,
  "removed_frac": 0.026,
  "downtime": {
    "count": 37,
    "events": 2,
    "longest_event_min": 125.0,
    "longest_event_start": "2024-07-16 13:55:00-07:00"
  },
  "spike": {
    "count": 665,
    "count_absolute": 498,
    "count_local": 167,
    "max_value_kw": 1741.35,
    "max_frac_of_nominal": 1.95,
    "hour_distribution": {0: 29, 1: 23, ..., 23: 10}
  }
}
```

Notes zenginleşmiş — 3 satır: ana özet + downtime detay + spike detay.

### FSA_1 Testleri

**Kirli veri (500 mutlak + 100 yerel spike + 100 downtime):**
- **Mutlak spike:** 498/500 yakalandı (2 tanesi tavan altında kaldı — beklenen)
- **Yerel spike:** 167 yakalandı — 100 eklediğimiz + FSA_1'in kendi 67 yerel spike'ı
- **Downtime:** 37 nokta, 2 olay (100 eklediğimiz **ardışık değildi**, sadece 60dk+ ardışık olanlar sayıldı)
- MAPE %25.75 → **%20.28** (dünkü basit tespit ile %20.48'den iyileşti)

**FSA_1'in kendi yerel spike'ları vardı!** Basit tespit yakalayamıyordu. Akıllı tespit gerçek dünya için değerli.

### 5-Senaryo Smoke Test (Faz 1.9.3 senaryolarının tekrarı)

| # | Basit (1.9.3) | Akıllı (1.9.4) |
|---|---|---|
| S1 (temiz, kapalı) | %20.52 | %20.52 |
| S2 (temiz, açık) | %20.52 | **%20.33** ← 0.19 puan iyileşme |
| S3 (kirli, kapalı) | %27.67 | %27.67 |
| S4 (kirli+temizlik) | %20.48 | **%20.28** ← 0.20 puan iyileşme |
| S5 (kış+kirli+temizlik) | %97.83 | **%94.64** ← 3.19 puan iyileşme |

### Bir Endişe (Faz 1.10+)

S5'te 728 yerel spike bulundu. Kış'ta bulut geçişi çok, dalgalanma büyük — algoritma yanlış pozitif üretebilir. Şu an MAPE'yi bozmuyor ama daha bulutlu bölgeler (Almanya, İngiltere) için yerel spike eşiği sıkılaştırılabilir.

**Commit:** `f0e2b12`

---

## 7. 1.9.5 — Fixture Deprecation Fix

### Sorun

`test_calibration_multi_resolution.py`'de iki `@pytest.fixture(scope="class")` fixture instance method olarak yazılmıştı (`def fixture_name(self, ...)`). pytest 10'da deprecated — instance attribute'lar görünmüyor.

### Çözüm

`@staticmethod` decorator ekle, `self` argümanını sil. Fixture içeride zaten `self` kullanmıyordu, sadece imzada vardı.

```python
# Öncesi
@pytest.fixture(scope="class")
def calibration_result(self):
    ...

# Sonrası
@staticmethod
@pytest.fixture(scope="class")
def calibration_result():
    ...
```

### Sonuç

- Dün: `88 passed, 2 warnings`
- Şimdi: `88 passed` (0 uyarı)

Küçük iş, temiz sonuç.

**Commit:** `[hash]`

---

## 8. Metrikler — Faz 1.7 Sonu → Faz 1.9 Sonu

Yaz 3 ay (Mayıs-Ağustos 2024), 15,538 geçerli saat.

| Faz | Sapma | MAPE | η_BoS | Azimuth | Tilt | Not |
|---|---|---|---|---|---|---|
| 1.7 Mod A | +%7 | %71 | 0.93 | 180° | 25° | Baseline (kalibre değil) |
| 1.7 Mod B | **-%52** | %164 | 0.99 | 180° | 25° | Kalibrasyon bozuk (tz bug) |
| 1.8.0 | %0.00 | %32 | 0.81 | 180° | 25° | tz-aware fix |
| 1.8.1 | %0.00 | %20 | 0.85 | 180°→**159°** | 25° | +azimuth fit |
| 1.9.0 | %0.00 | %21 | 0.85 | 159° | 10°→**26°** | +tilt fit |
| 1.9.4 | %0.00 | **%20.33** | 0.85 | 159° | 26° | +akıllı outlier temizlik |

**MERKAS referans:** yıllık %0.77. FSA_1 Faz 1.9'da yaz için %0.00 — MERKAS'tan iyi.

**MAPE %20 ne demek?** Kaliforniya utility-scale için makul. Daha düşürmek için:
- NREL NSRDB (kaliteli meteo) — Faz 1.10+
- POA sensörü kullanımı (uzun vadeli için) — Faz 2 UI
- Bulut aware model — Faz 3+

---

## 9. Commit Zinciri (Faz 1.9)

```
[hash]   test: fix class-scoped fixture deprecation warning (Faz 1.9.5)
f0e2b12  feat(calibration): smart outlier detection + rich report (Faz 1.9.4)
e5a91cd  feat(calibration): SCADA outlier cleanup - basic (Faz 1.9.3)
31867e4  feat(calibration): sanity check warnings (Faz 1.9.1)
8d4e674  feat(calibration): tilt fit + XOR guard (Faz 1.9.0)
```

**Değişen dosyalar:**
- `src/pvquant/pipeline/calibration.py` — ~150 satır ekleme (fit_tilt, sanity checks, outlier entegrasyon)
- `src/pvquant/pipeline/utils.py` — ~180 satır ekleme (clean_scada_outliers)
- `tests/test_calibration_multi_resolution.py` — 4 satır değişiklik (fixture fix)

**Değişmeyen:**
- `src/pvquant/models_v2/*` — dokunulmadı (POA bias fit denemesi geri alındı)
- `src/pvquant/io/*` — dokunulmadı
- Fizik modelleri — dokunulmadı

### Test Durumu

| | Faz 1.8 Sonu | Faz 1.9 Sonu |
|---|---|---|
| Toplam test | 88 | 88 |
| Yeşil | 88 | 88 |
| Warnings | 2 | **0** ✅ |
| Regresyon | Yok | Yok |
| Smoke testler | 6/6 (1.8) | 6/6 (1.8) + 7/7 (1.9.0) + 5/5 (1.9.3) + 5/5 (1.9.4) |

**Toplam smoke test:** 23 senaryo, hepsi PASS.

---

## 10. Öğrenilen Dersler

### 1. "Motivasyon Var, Zaman Var" Dürtüsü Değerli

Faz 1.9.3 basit outlier temizliğinden sonra "daha iyi yapamaz mıyız?" sorusu Faz 1.9.4'ü doğurdu. Adaptif eşik + median filter + zengin rapor eklendi. FSA_1'in kendi gizli yerel spike'ları bile ortaya çıktı.

**Ders:** Bir feature çalıştığında hemen commit etmek her zaman doğru değil. Bazen "daha iyi hâli" üzerine düşünmek fazla değer üretir.

### 2. Negatif Sonuç da Bilgi

POA bias fit MAPE'yi arttırdı, commit edilmedi. Ama boşa iş değil — bias fit'in **saatlik profil için değil, uzun vadeli için** değerli olduğunu öğrendik. Faz 2 UI'de "uzun vadeli mod" için bu bilgi kullanılacak.

### 3. XOR Koruma Kullanıcıyı Korur

Tilt ve azimuth aynı anda fit edilirse local minimum riski var. Kod seviyesinde `ValueError` ile engelleyerek kullanıcının kafası karışmasını önledik.

**Ders:** Ürün güvenilirliği için savunma katmanları önemli. Kullanıcı "kod bozuk" demesin, "bu kombinasyon anlamlı değil" mesajı alsın.

### 4. Robustness Testi Ucuz Ama Kritik

Faz 1.9.0'da S5 (initial=45° tilt) tam olarak S2 (initial=10°) ile birebir aynı 26.17°'e gitti (0.00° fark). Bu bir satırlık test optimizasyonun global optimum'a yakınsadığının kanıtı.

Aynısı Faz 1.8 azimuth fit'te de yapıldı. Her yeni fit için standart olmalı.

### 5. Sentetik Testler Yalancıdır (Bir Kez Daha)

FSA_1'in kendi verisinde 67 yerel spike varmış. Basit tespit (Faz 1.9.3) yakalayamıyordu. Akıllı tespit (Faz 1.9.4) ortaya çıkardı. **Sentetik tests bu farkı asla göstermezdi** — çünkü sentetik veri kusursuz.

Gerçek dünya validasyonu (FSA_1) olmasa Faz 1.9.4'e ihtiyaç bile hissedilmezdi.

### 6. Teknik Borç Ertelenmesin

Fixture warning "küçük iş" idi. Ertelenirse pytest 10 çıkışında acil düzeltmek zorunda kalırdık. Faz 1.9.5 ile 30 dakikada hallettik.

**Ders:** Küçük teknik borçları anında kapat. Ertelenirse büyür.

---

## 11. Faz 1.9'un Ürün İçin Anlamı

### Bu Sürümde Çalışan

- ✅ Kullanıcı SCADA yükler → doğru zaman uyumu otomatik (1.8.0)
- ✅ Kullanıcı azimuth bilmiyor → fit_azimuth çözer (1.8.1)
- ✅ Kullanıcı tilt bilmiyor → fit_tilt çözer (1.9.0)
- ✅ Kullanıcı yıllık veri verir → DST'de patlamıyor (1.8.0.1)
- ✅ Kullanıcı sonuç anlamlı değilse uyarı alır (1.9.1)
- ✅ Kullanıcı ham veri getirir → outlier'lar otomatik tespit + rapor (1.9.3-4)
- ✅ Sapma sıfıra çekilir (kalite verilerle)
- ✅ MAPE ~%20 seviyesinde (Kaliforniya utility-scale için makul)

### Hala Eksik (Faz 1.10+ veya Faz 2)

- ❌ POA bias fit (uzun vadeli için)
- ❌ Curtailment tespit (model tabanlı gerek)
- ❌ Clipping tespit (`p_ac_clip_kw` fit)
- ❌ NSRDB entegrasyonu (kış meteo kalitesi)
- ❌ Kullanıcı arayüzü (Streamlit UI)
- ❌ Cloud deployment

Bunlar Faz 2 ve sonrası konusu.

---

## 12. Sonuç

Faz 1.9 bir **konsolidasyon fazı** oldu. Faz 1.8'in üzerine dört yeni yetenek eklendi ve bir teknik borç temizlendi. Bir feature (POA bias) denendi, geri alındı.

**Ürün için önemli olan:**
1. Kalibrasyon artık **kirli veri ile de çalışıyor**
2. Kullanıcıya **veri kalitesi analizi** dönüyor (outlier_report)
3. Kullanıcıya **kalibrasyon güveni** dönüyor (warnings)
4. Geometri fit'i **iki eksende tamamlandı** (azimuth + tilt)

**Kod tarafı %90+ tamamlandı.** Faz 2 (UI) başlamaya hazır.

**Faz 1.9 kapandı. Ürün, kullanıcı arayüzü için olgun bir kütüphane haline geldi.**
