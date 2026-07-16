# Multi-Resolution Plan — Frekans-Agnostik Model

**Belge tarihi:** 1 Temmuz 2026
**Faz:** 1.6 — Frekans Agnostikleştirme
**Kapsam:** PVQuant modelinin 1 dk / 5 dk / 15 dk / 30 dk / 1 saat frekanslarında çalışabilmesi
**Öncesi:** Faz 1.5 (Sözlük Genişletme — Adım 2.5 tamamlandı)
**Öncelik:** Yüksek (gerçek dünya test öncesi mimari sağlamlaştırma)

---

## 1. Yönetici Özeti

PVQuant modeli şu an **saatlik veri varsayımı** ile çalışıyor. Bu, ürünü B2C konut segmentine sıkıştırır ve dünya standartı utility-scale (15 dakikalık) SCADA sistemleriyle uyumsuz kalır.

Bu belge, modelin **frekans-agnostik** hale getirilmesi için:

- Tespit edilen 7 kategoride frekans varsayımını
- Her birini çözmek için gerekli değişiklikleri
- Sıralama, risk ve efor tahminini
- Test stratejisini

belgeler.

**Tahmini toplam iş:** 4-6 saat (yoğun konsantrasyon)

**Değişecek dosya sayısı:** 4 ana + 2-3 yardımcı

**Bozacağı test:** Muhtemel (mevcut sentetik veriler saatlik — dönüşüm gerekebilir)

---


<!-- Faz 1.6 TAMAMLANDI (Adim 6) -->

---

## ✅ TAMAMLANDI — Faz 1.6

**Tamamlanma tarihi:** 2026-07-03

Model artik **frekans-agnostik**. 1 dakika, 5 dakika, 15 dakika, 30 dakika ve
1 saatlik SCADA verileriyle calisir. Ana odak: dunya capinda utility-scale
santralleri (15 dk standart) destekleyebilmek.

### Commit Zinciri

| Adim | Commit | Aciklama |
|---|---|---|
| Plan | `1bc02d2` | docs: add multi-resolution model plan |
| Adim 1 | `b5049f2` | feat(pipeline): timestep detection utilities |
| Adim 2 | `5ace061` | feat(pipeline): frequency-agnostic energy and capacity factor |
| Adim 3.1 | `18920fb` | feat(pipeline): add meteo alignment utility |
| Adim 3.3 | `e8b436e` | feat(pipeline): frequency-agnostic calibration |
| Adim 4 | `27e4719` | feat(models_v2): auto-detect timestep in BarhdadiBennisModel |

### Neler Yapildi

- **`pipeline/utils.py`**: `_detect_timestep_hours`, `_detect_timestep_minutes`,
  `_align_meteo_to_scada` yardimci fonksiyonlari.
- **`pipeline/forecast.py`**: Enerji hesabi ve kapasite faktoru cozunurluk agnostik.
- **`pipeline/calibration.py`**: `to_hourly()` cagrisi kaldirildi. SCADA ham
  cozunurlukte kullaniliyor. Meteo otomatik olarak SCADA index'ine hizalaniyor
  (1h meteo + 15dk SCADA gibi durumlar destekleniyor).
- **`api/routes/calibration.py`**: FastAPI endpoint'i de agnostik.
- **`models_v2/barhdadi_bennis.py`**: Model API'sinde hardcoded `timestep_minutes=60`
  otomatik tespite cevrildi.

### Test Durumu (Faz 1.6 sonu)

- **88 test yesil** (2.14 saniye)
- Yeni testler:
  - `test_pipeline_utils.py`: `TestAlignMeteoToScada` (8 test)
  - `test_calibration_multi_resolution.py`: 13 test (1h regresyon + 15dk kabiliyet)
- Regresyon: mevcut testlerin hicbiri bozulmadi.

### Kapsam Disi Kalanlar (Faz 2'ye Ertelendi)

- `hourly` -> `timeseries` isim degisikligi (UI etkilenir, ayri is)
- `forecast_horizon_hours` -> `forecast_horizon_periods` (Open-Meteo hala 1h)
- Streamlit UI cozunurluk secici
- Cikti raporlama farkli cozunurlukte

### Sonraki Faz

**Faz 1.7 — Gercek Dunya Testi**: NREL FSA_1 (Arbuckle, CA) 15 dakikalik veri
seti ile Mod B testi. Kullanici gercek 15dk SCADA yukleyecek, kalibrasyon
sonuclari incelenecek.

---

## 2. Kod Tabanı Analizi — Ne Buldum?

### 2.1 İyi Haberler ✅

**A) `contracts.py` zaten hazır** (satır 100):
```python
class ForecastInput(BaseModel):
    resolution_minutes: int = Field(..., ge=1, le=60)
    data: pd.DataFrame
```
Mimari **zaten çözünürlük kavramını biliyor**. Sadece kullanılmıyor.

**B) `historical_data` çözünürlük agnostik** — sadece timestamp ve power_kw ister.

**C) Fizik formülleri intrinsic olarak çözünürlük agnostik**:
- Erbs, Perez, Faiman, Barhdadi-Bennis — hepsi anlık formüller
- Formüle bir W/m² girdiğinizde bir kW çıktı verir, süre bilgisine ihtiyaç duymazlar

### 2.2 Sorunlu Alanlar ❌

Kod tabanında **7 kategori** frekans varsayımı tespit ettim:

---

## 3. Frekans-Bağımlılık Haritası

### KATEGORİ 1: Enerji Hesabı Varsayımı (KRİTİK)

**Yer:** `pipeline/forecast.py`, satır 307-308

```python
# --- 8. Saatlik enerji (kWh = kW × 1h) ---
energy_kwh = p_ac  # saatlik adımda kW = kWh
```

**Sorun:** kWh = kW × saat formülünde saat sabit 1 varsayılıyor. 15 dakikalık veri için `energy_kwh = p_ac * 0.25` olmalı.

**Etki:** Yanlış enerji toplamı → yanlış yıllık sapma → **yanlış kalibrasyon**.

**Çözüm:**
```python
# Zaman aralığını timeseries'ten tespit et
dt_hours = _detect_timestep_hours(p_ac.index)  # 1.0, 0.25, 0.0833...
energy_kwh = p_ac * dt_hours
```

**Zorluk:** 🟡 Orta — yardımcı fonksiyon yazılmalı.

---

### KATEGORİ 2: Kalibrasyon Zorla Saatliğe İndiriyor (KRİTİK)

**Yer:** `pipeline/calibration.py`, satır 127-133

```python
scada_hourly = scada.to_hourly()
actual_power = scada_hourly.power_kw

if scada_hourly.hours_count < 100:
    raise ValueError(f"Yetersiz SCADA verisi: {scada_hourly.hours_count} saat")
```

**Sorun:** SCADA verisi ne olursa olsun saatliğe indiriliyor. 15 dakikalık veri girilse bile modeli 15 dakikalık test edemiyoruz.

**Etki:** 15 dakikalık avantajı (4× daha fazla veri noktası) kayboluyor.

**Çözüm:**
```python
# SCADA'nın kendi çözünürlüğünü koru
scada_data = scada.to_dataframe()  # Ham çözünürlükte
timestep_hours = _detect_timestep_hours(scada_data.index)
min_samples = int(100 / timestep_hours)  # Örn: 15 dk için 400
if len(scada_data) < min_samples:
    raise ValueError(...)
```

**Zorluk:** 🟡 Orta — `SCADAData` sınıfına `.to_dataframe()` metodu ekleyelim mi yoksa mevcut `to_hourly()`'yi parametrize mi edelim?

---

### KATEGORİ 3: BarhdadiBennisModel'de Sabit timestep (KRİTİK)

**Yer:** `models_v2/barhdadi_bennis.py`, satır 256

```python
scada = SCADAData(
    power_kw=df["power_kw"].astype(float),
    ...
    timestep_minutes=60,  # ⚠️ HARDCODED
)
```

**Sorun:** SCADAData'ya sabit 60 dakika söyleniyor. Modelin **kalbi** burada — kalibrasyon buradan başlıyor.

**Etki:** ForecastInput'un `resolution_minutes` alanı boş yere var — burası zaten hardcoded.

**Çözüm:**
```python
# Timestamp'ten otomatik tespit
detected_minutes = _detect_timestep_minutes(df.index)
scada = SCADAData(
    ...
    timestep_minutes=detected_minutes,
)
```

**Zorluk:** 🟢 Kolay — tek satır değişiklik, yardımcı fonksiyon çağrısı.

---

### KATEGORİ 4: ForecastResult "hourly" Etiketi (KOZMETIK ama YAYGIN)

**Yer:** `pipeline/forecast.py` ve `models_v2/barhdadi_bennis.py`

`hourly` isimli attribute her yerde geçiyor:
- `forecast.py:107` → `hourly: pd.DataFrame`
- `forecast.py:116` → `self.hourly["p_ac_kw"]`
- `forecast.py:129` → `hours = len(self.hourly)`
- `forecast.py:311` → `hourly = pd.DataFrame(...)`
- `barhdadi_bennis.py:207-220` → `pipeline_result.hourly[...]` (5 kullanım)

**Sorun:** Sadece bir isim ama yanlış varsayım aktarıyor. "Bu saatlik veri" varsayımıyla kod yazılıyor.

**Etki:** Doğruluk düşük ama okuyanı yanıltıyor.

**Çözüm — İki seçenek:**

**A) İsim değiştir:** `hourly` → `timeseries` (semantic olarak doğru)
- Etki: Tüm çağıran kodlar değişir (Streamlit UI, tests, scripts)
- Risk: Yüksek regresyon

**B) İsmi koru, docstring düzelt:** `hourly` kalsın ama docstring "kullanıcı çözünürlüğünde timeseries" desin
- Etki: Sadece belge
- Risk: Yok
- Ama sürekli yanıltıcı isim ile yaşamak zorunda kalırız

**Öneri:** **A** — ama Faz 1.6 kapsamında değil, **Faz 2**'ye ertelesin. Çünkü UI ve testleri de etkileyecek büyük iş.

**Zorluk:** 🔴 Zor (kapsamlı) veya 🟢 Kolay (ertelenirse)

---

### KATEGORİ 5: capacity_factor Yanlış Hesaplıyor (ORTA KRİTİK)

**Yer:** `pipeline/forecast.py`, satır 124-132

```python
@property
def capacity_factor(self) -> float:
    hours = len(self.hourly)
    if hours == 0 or self.plant.p_nom_kwp == 0:
        return 0.0
    return float(self.total_kwh / (self.plant.p_nom_kwp * hours))
```

**Sorun:** `hours = len(self.hourly)` — 15 dakikalık veride 96 kayıt varken, `hours` 96 değil, 24 olmalı!

**Etki:** 15 dakikalık veride kapasite faktörü **4 kat düşük** görünür. Metrikler yanlış.

**Çözüm:**
```python
dt_hours = _detect_timestep_hours(self.hourly.index)
total_hours = len(self.hourly) * dt_hours
return float(self.total_kwh / (self.plant.p_nom_kwp * total_hours))
```

**Zorluk:** 🟢 Kolay — 2 satır değişiklik.

---

### KATEGORİ 6: Daily Resample "1D" Hardcoded (DÜŞÜK)

**Yer:** `pipeline/forecast.py`, satır 326

```python
daily_energy = energy_kwh.resample("1D").sum()
```

**Sorun:** Bu aslında **doğru** — günlük özet günlük olmalı, çözünürlükten bağımsız. Ama energy_kwh doğru hesaplandığı sürece.

**Bağlam:** Bu satır Kategori 1 çözüldükten sonra otomatik doğru çalışır (energy_kwh doğru hesaplanınca günlük toplam da doğru).

**Zorluk:** ✅ Zaten doğru — sadece Kategori 1'e bağımlı.

---

### KATEGORİ 7: forecast_horizon_hours Sabit 168 (DÜŞÜK)

**Yer:** `contracts.py`, satır 125

```python
forecast_horizon_hours: int = Field(default=168, ge=1, le=336)
```

**Sorun:** 168 saat = 7 gün varsayımı. Ama zaman aralığı bilgisi olmadan bu sabit anlamsız — kullanıcı 15 dk çözünürlükte 168 saat isteyebilir (672 kayıt) veya 1 saatlik 168 kayıt.

**Etki:** Şu an için düşük — Open-Meteo API'sı zaten saatlik meteo verisi veriyor. Ama gelecekte Solcast (5 dk) entegre edilirse önemli.

**Çözüm:** Şimdilik dokunmayalım. `forecast_horizon_periods` gibi bir alan eklenebilir ama iş büyür.

**Zorluk:** ✅ Şimdilik yok — Faz 2'ye ertele.

---

## 4. Yardımcı Fonksiyon: `_detect_timestep_hours()`

Bu, çözümün merkezinde. Bir kez yaz, her yerde kullan.

**Konum önerisi:** `src/pvquant/pipeline/utils.py` (yeni dosya) veya `forecast.py` içine private fonksiyon.

**İmza:**
```python
def _detect_timestep_hours(index: pd.DatetimeIndex) -> float:
    """Zaman ekseninden ortalama adımı saat cinsinden döner.

    Args:
        index: DatetimeIndex (en az 2 kayıt).

    Returns:
        Saat cinsinden adım. Örn: 1.0 (saatlik), 0.25 (15 dk), 0.0833 (5 dk).

    Raises:
        ValueError: 2'den az kayıt varsa veya adımlar tutarsızsa.
    """
    if len(index) < 2:
        raise ValueError("En az 2 kayıt gerekli")

    diffs = index.to_series().diff().dropna()
    median_diff = diffs.median()

    # Tutarlılık kontrolü — %90'ının medyana yakın olmasını bekle
    close_to_median = (diffs - median_diff).abs() < pd.Timedelta("1min")
    if close_to_median.mean() < 0.90:
        raise ValueError(
            f"Zaman adımı tutarsız: medyan {median_diff}, "
            f"kayıtların sadece %{close_to_median.mean()*100:.0f}'ı bu adımda"
        )

    return median_diff.total_seconds() / 3600.0
```

**Ek yardımcı:**
```python
def _detect_timestep_minutes(index: pd.DatetimeIndex) -> int:
    """Aynısı ama dakika cinsinden ve int."""
    hours = _detect_timestep_hours(index)
    return int(round(hours * 60))
```

**Test:**
```python
def test_detect_timestep():
    # 1 saatlik
    idx = pd.date_range("2024-01-01", periods=24, freq="1H")
    assert _detect_timestep_hours(idx) == 1.0

    # 15 dakikalık
    idx = pd.date_range("2024-01-01", periods=96, freq="15min")
    assert abs(_detect_timestep_hours(idx) - 0.25) < 1e-6

    # 5 dakikalık
    idx = pd.date_range("2024-01-01", periods=288, freq="5min")
    assert abs(_detect_timestep_hours(idx) - 5/60) < 1e-6

    # Tutarsız — hata vermeli
    idx = pd.DatetimeIndex(["2024-01-01 00:00", "2024-01-01 00:15", "2024-01-01 02:00"])
    with pytest.raises(ValueError):
        _detect_timestep_hours(idx)
```

---

## 5. Uygulama Sırası (Öncelik Sırası)

Her adım **bağımsız** olarak test edilir, işe yaradığından emin olunur, ondan sonra bir sonraki adıma geçilir.

### ADIM 1: Yardımcı Fonksiyon (30 dk)

- `pipeline/utils.py` oluştur
- `_detect_timestep_hours()` ve `_detect_timestep_minutes()` yaz
- `tests/test_utils.py` yaz — 4-5 test case
- **Çıktı:** Test geçen yardımcı fonksiyon.
- **Risk:** Yok.

### ADIM 2: Enerji Hesabı Düzeltmesi (45 dk)

- `forecast.py:307-308` — energy_kwh hesabını düzelt
- `forecast.py:124-132` — capacity_factor düzelt
- **Regresyon:** Saatlik verilerle mevcut testleri çalıştır — hiçbiri bozulmamalı (çünkü 1.0 × p_ac = p_ac)
- **Test:** Yeni test — 15 dakikalık sentetik veri, enerji doğru mu?
- **Çıktı:** Enerji hesabı çözünürlük agnostik.
- **Risk:** 🟡 Orta — mevcut 30 santral kalibrasyonu **etkilenmemeli** çünkü hepsi saatlik. Ama doğrulanmalı.

### ADIM 3: Kalibrasyon Çözünürlük-Aware (60 dk)

- `calibration.py:127-133` — `to_hourly()` çağrısını kaldır, ham çözünürlüğü koru
- Minimum örnek sayısı hesabını dinamik yap
- `SCADAData` sınıfına gerekirse `.to_dataframe()` ekle (mevcut kodda var olabilir)
- **Regresyon:** 30 santral için kalibrasyon tekrar çalıştır — sonuçlar aynı olmalı
- **Test:** 15 dk sentetik veri ile kalibrasyon çalışıyor mu?
- **Çıktı:** Kalibrasyon çözünürlük agnostik.
- **Risk:** 🟠 Yüksek — kalibrasyon kritik. Çok dikkatli test edilmeli.

### ADIM 4: BarhdadiBennisModel Timestep Detection (15 dk)

- `barhdadi_bennis.py:256` — hardcoded `timestep_minutes=60`'ı otomatik tespite çevir
- **Regresyon:** Model API'sı üzerinden kalibrasyon yap, aynı sonuç geliyor mu?
- **Çıktı:** Model API'sı çözünürlük agnostik.
- **Risk:** 🟢 Düşük — tek satır değişim.

### ADIM 5: Kapsamlı Test (60 dk)

- 1 saatlik test — mevcut REFPLANT regresyonu
- 15 dakikalık test — sentetik veri veya FSA'nın 15 dk resample'ı
- 5 dakikalık test — FSA'nın irradiance'ı zaten 5 dk
- Kapasite faktörü, sapma metrikleri, MAPE — hepsi tutarlı mı?
- **Çıktı:** Frekans-agnostik olduğu kanıtlanmış model.

### ADIM 6: Docs + Commit (30 dk)

- `docs/PHASE_B_NOTES.md`'ye Faz 1.6 notu ekle
- `docs/MULTI_RESOLUTION_PLAN.md`'yi güncelle: "TAMAMLANDI"
- Commit: `feat: multi-resolution model support (1min-1h)`
- Push (GitHub Desktop)

**Toplam süre tahmini:** 4-6 saat (aralarda test ile)

---

## 6. Risk Analizi

| Risk | Olasılık | Etki | Azaltma |
|---|---|---|---|
| Mevcut 30 santral kalibrasyonu bozulur | Düşük | Yüksek | Adım 2 ve 3'te regresyon testi zorunlu |
| SCADAData.to_hourly() dependent kodlar | Orta | Orta | Grep ile ara, tek tek incele |
| Streamlit UI etkilenir | Yüksek | Düşük | Adım 5'te UI test edilmeli |
| Testler saatlik varsayıyor | Yüksek | Düşük | tests/ klasörüne yeni test dosyaları ekle, eskileri koru |
| 15 dk verilerde gürültü çok yüksek → BG fit başarısız | Orta | Orta | minimize_scalar bounds ayarı gerekebilir |

---

## 7. Kabul Kriterleri

Bu iş "tamamlandı" demek için:

- [ ] `_detect_timestep_hours()` yardımcı fonksiyonu yazılmış, test geçiyor
- [ ] Enerji hesabı, kapasite faktörü çözünürlüğe göre doğru
- [ ] Kalibrasyon 1h, 15dk, 5dk verilerde çalışıyor
- [ ] 30 mevcut santralin kalibrasyonu tekrar çalıştırıldığında **aynı sonuçlar** çıkıyor
- [ ] En az 1 gerçek 15 dk veri ile end-to-end test geçmiş
- [ ] Docs güncellenmiş
- [ ] Commit ve push atılmış

---

## 8. Kapsam Dışı — Faz 2'ye Ertelenenler

Bunlar önemli ama Faz 1.6'nın kapsamı dışında:

1. **`hourly` → `timeseries` rename** — UI ve testleri etkiler, ayrı bir iş
2. **`forecast_horizon_hours` → `forecast_horizon_periods`** — Şu an Open-Meteo saatlik, gerek yok
3. **Streamlit UI'da çözünürlük seçici** — Backend hazır olduktan sonra
4. **Çıktı raporlama farklı çözünürlükte** ("15 dk çalış, saatlik göster")
5. **Otomatik agrega opsiyonu** (`.resample('1H')` output)
6. **Solcast/Solargis entegrasyonu** — Farklı çözünürlük getirebilir

---

## 9. Sonraki Adımlar

Bu belge onaylanınca:

1. Yeni bir dal aç: `git checkout -b faz1.6-multi-resolution`
2. Adım 1'den başla, sırayla ilerle
3. Her adımda commit at
4. Adım 5'te merge PR aç, sen incele
5. Onaylanınca `faz1.5-persistence`'e merge et
6. Sonrasında **gerçek dünya testi** (FSA verisi) — Faz 1.7

---

**Belge sonu.**
