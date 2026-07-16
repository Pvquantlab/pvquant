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

REFPLANT xlsx üzerinde UI kalibrasyonu:
- Öncesi: SAPMA %-100, MAPE %100 (fizik çıktıları sıfır)
- Sonrası: SAPMA %-3.23, MAPE %27.5, eta_BoS 0.897

Testler: 104 → 110 (6 yeni birim testi)

## Tur 4 Yamaları — 15 Temmuz 2026

**4. kozmetik_ve_icerik.patch**
Sayı formatı bug'ı (1.234.5 -> 1.234,5), Türkçe dönem (14 – 21 Temmuz 2026),
santral adı normalize (`_yillik_SCADA` gibi ekleri kırpar), holdout MAPE
kutusu, pozitif kalibrasyon notu, grafik başlıkları kısaltıldı, footer
düzenlendi. 6 yeni test.

**5. logo_ve_marka.patch**
PVQuant SVG logosu + PDF'te ReportLab primitifleriyle birebir çizim
(svglib bağımlılığı yok). Petrol yeşili kutu + 3 beyaz üretim barı +
amber güneş.

## Sonuç (Tur 4 sonrası)

REFPLANT UI'dan PDF: logo + "REFPLANT GES" (normalize) + "15 – 22 Temmuz 2026"
Türkçe dönem + 206,0 MWh (virgül) + 4.514 kWp (binlik nokta) + yeşil
✓ Kalibrasyon notu. Testler: 129 passed.
