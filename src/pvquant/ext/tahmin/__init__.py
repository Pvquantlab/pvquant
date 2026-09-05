"""pvquant.ext.tahmin — tahmin bilimi modülleri (rapor 3.2; entegrasyon öncesi, çekirdeğe dokunmaz).

  dogrulama        → olasılıksal + deterministik doğrulama (reliability/PIT, pinball, CRPS, PICP, SFA seti)
  konformal        → CQR ve ACI ile P10–P90 kalibrasyonu
  ensemble_belirsizlik → ensemble yayılımından ufukla büyüyen belirsizlik (spread-skill, EMOS-lite)
  kisitlama        → curtailment / clipping tespiti ve kalibrasyon maskesi
  backtest         → rolling-origin backtest + eğitim/servis kayması denetimi
  referans         → iklimsel referans, akıllı persistans, optimal konveks birleşim (Yang 2019)
  fizik_terimler   → clear-sky (McClear/Ineichen), IAM, spektral düzeltme
  kirlenme         → soiling (HSU/Kimber) ve kar örtüsü kaybı
  degradasyon      → yıllık bozunma oranı (YoY) ve PR / sıcaklık-düzeltmeli PR trendi
  alt_saatlik      → saatlik → 15 dk indirgeme ve 15 dk uzlaştırma yardımcıları
  portfoy          → hiyerarşik uzlaştırma (bottom-up / top-down / MinT)
Tüm seriler saatlik (ya da 15 dk) UTC; güç kW/MW, ışınım W/m².
"""
__version__ = "0.1.0"
