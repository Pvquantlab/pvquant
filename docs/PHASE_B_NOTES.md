# Phase B — Parser Güçlendirme Notları

Bu belge, PVQuant akıllı parser'ının Phase B geliştirmelerinin durumunu ve öğrenilen dersleri toplar.

## Amaç

Faz 1.5'te 30 santral test edildi. Akıllı parser'ın Türkiye SCADA formatlarını daha güvenilir okuması için Phase B'de aşağıdaki iyileştirmeler planlandı.

## Durum

| Adım | Konu | Durum |
|---|---|---|
| 1 | POA birim dönüşümü (kWh/m² → W/m²) | ✅ Tamamlandı |
| 2 | Fuzzy sütun adı eşleştirme (rapidfuzz) | ⏳ Planlı |
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

## Sonraki Adım — Fuzzy Matching (Adım 2)

Fikir: `rapidfuzz` ile eşik puanlı benzerlik. `"power kw active"` → `"AC Active Power(kW)"` gibi eşleşmeler. Eşik ~85 civarı olabilir. Ambigü eşleşmelerde en yüksek skorlu birden fazla adayı loglayıp kullanıcıya bildirmek düşünülebilir.
