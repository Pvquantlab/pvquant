# Phase B — Parser Güçlendirme Notları

Bu belge, PVQuant akıllı parser'ının Phase B geliştirmelerinin durumunu ve öğrenilen dersleri toplar.

## Amaç

Faz 1.5'te 30 santral test edildi. Akıllı parser'ın Türkiye SCADA formatlarını daha güvenilir okuması için Phase B'de aşağıdaki iyileştirmeler planlandı.

## Durum

| Adım | Konu | Durum |
|---|---|---|
| 1 | POA birim dönüşümü (kWh/m² → W/m²) | ✅ Tamamlandı |
| 2 | Fuzzy sütun adı eşleştirme (rapidfuzz) | ✅ Tamamlandı |
| 3 | Encoding / delimiter otomatik algılama | ⏳ Planlı |
| 4 | Metadata (header üstü) satır atlama | ⏳ Planlı |
| 5 | Saat dilimi doğrulama (tepe analizi) | ⏳ Planlı |
| 6 | Yükleme sonrası veri kalite raporu | ⏳ Planlı |

## Adım 1 — POA Birim Dönüşümü (2026-07-01, commit f51a65c)

### Sorun
Bazı SCADA sistemleri POA'yı `kWh/m²` (saatlik integral, pik ~0.8-1.2) olarak raporlar. PVQuant motoru `W/m²` (pik ~800-1100) bekler. Sütun adı tanınmadığında POA sessizce Open-Meteo'ya düşüyor ve modelin ölçülen POA ile kalibre olma şansı kayboluyordu.

### Çözüm
1. `_normalize_poa_units()` yardımcı fonksiyonu eklendi. Pik değere bakarak birim tespiti yapıyor: `max < 10` ise kWh/m² varsayıp ×1000 dönüştürüyor.
2. Sütun sözlüğüne `poa_irradiance_kwh_m2` alias'ı eklendi.
3. `load_csv()` içindeki POA okuma çağrısı bu normalizasyonla sarmalandı.

### Doğrulama (mega_ges_karapinar CSV)
- Ham veri pik: 0.857 kWh/m² → dönüştürülmüş: 857 W/m² ✓
- Yıllık toplam POA: 1641 kWh/m² (Karapınar bölgesi için tipik)
- POA artık tanınıyor; önceden `poa_irradiance_kwh_m2` sütunu yok sayılıyordu

### Bilinen açık konu
Bu santralde kalibrasyon sapması −13.99% çıkıyor. Bu POA dönüşümünün bir sorunu değil; sistem parametrelerinin (η_BoS, gamma, panel özellikleri) bu spesifik santral için yeniden değerlendirilmesi gerekiyor. Ayrı bir Faz 1.5 konusu olarak ele alınmalı.

## Adım 2 — Fuzzy Sütun Adı Eşleştirme (2026-07-01, commit 05b2911)

### Çözüm
`_detect_column()` fonksiyonuna `rapidfuzz.WRatio` tabanlı fuzzy fallback eklendi. Önce tam eşleşme denenir (mevcut davranış korunur); bulunamazsa fuzzy skoruna bakılır. Eşik değeri **85**.

### Test Sonuçları
İngilizce sütun adlarındaki biçim varyantları doğru yakalanıyor:

| Sütun | Hedef | Skor |
|---|---|---|
| `AC_Active_Power_kW` | `power_kw` | 90.0 |
| `ac active power kw` | `power_kw` | 91.9 |
| `POA-Irradiance-Wm2` | `poa_irradiance` | 90.0 |
| `Module.Temperature` | `temp_module` | 85.0 (sınırda) |
| `ambient_temp_celsius` | `temp_ambient` | 90.0 |
| `module_temperature` | `temp_module` | 90.0 |
| `wind_speed_ms` | `wind_speed` | 87.0 |

**Skor aralığı: 85.0–91.9** — eşik iyi kalibre.

### Tasarım Kararları
- **Sadece tam eşleşme başarısız olursa** fuzzy devreye giriyor → regresyon riski yok
- Her fuzzy eşleşmede `logger.info` log yazılıyor (debug için)
- Anlamsal çeviri (Türkçe→İngilizce) fuzzy'nin işi değil; gerekirse sözlük genişletilir
- Uygulama global/İngilizce olduğu için Türkçe alias'lar sözlüğe eklenmedi

### Bağımlılık
`rapidfuzz>=3.0` — `requirements.txt`'e eklendi (commit ile birlikte).

## Sonraki Adım — Encoding / Delimiter Otomatik Algılama (Adım 3)

Fikir: `chardet` ile encoding tespiti, `csv.Sniffer` ile delimiter (`,` vs `;` vs `\t`) tespiti. Türkiye SCADA'sı sıklıkla `;` ve UTF-8-BOM veya cp1254 encoding kullanır.
