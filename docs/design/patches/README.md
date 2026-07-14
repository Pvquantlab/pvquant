# Fable 5 Yamaları — 14 Temmuz 2026

Bu klasör, Fable 5'in ürettiği ve `git apply` ile repo'ya uygulanmış
teşhis + düzeltme yamalarını arşivler. Kod zaten uygulanmıştır; bu
dosyalar sadece geçmiş referansı içindir.

## Yamalar

**1. olu_sensor_yamasi.patch**
`measured_poa` fizik pipeline'ına bağlandıktan sonra ölü/yanlış
sensör verisi fizik tahminini sıfıra çekebiliyordu. İki savunma hattı:
- `pipeline/calibration.py`: kalibrasyon öncesi POA-GHI kaba kıyas
- `pipeline/forecast.py`: motor seviyesinde override akıl kontrolü

**2. uyari_gorunurluk_yamasi.patch**
`olu_sensor_yamasi`'nın notlarını `warnings` listesine de yazar
(UI'nın "Bulduklarımız" kartı sadece warnings'i basıyor).

**3. isinim_birim_yamasi.patch**
Kök neden: xlsx'te `Toplam Işıma (kWh/m²)` kolonu ingestion'da
W/m² sanılıyordu (1000× ölçek hatası). Ölü-sensör görünümünü
yaratan asıl problem buydu.
- `io/ingestion/transform.py`: `normalize_irradiance_wm2()` eklendi
- `io/ingestion/contracts.py`: `TransformSpec.irradiance_unit` alanı
- `tests/test_irradiance_unit.py`: 6 yeni test

## Uygulanma sırası

1. olu_sensor_yamasi (ilk savunma hattı)
2. uyari_gorunurluk_yamasi (UI görünürlüğü)
3. isinim_birim_yamasi (kök neden)

## Sonuç

MERKAS xlsx üzerinde UI kalibrasyonu:
- Öncesi: SAPMA %-100, MAPE %100 (fizik çıktıları sıfır)
- Sonrası: SAPMA %-3.23, MAPE %27.5, eta_BoS 0.897

Testler: 104 → 110 (6 yeni birim testi)
