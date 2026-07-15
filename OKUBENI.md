# Tur 5 — Hibrit Model UI Entegrasyonu

## Paket içeriği
- hibrit_ui_cekirdek.patch : git apply ile (repo kökünde). İçinde:
  * src/pvquant/pipeline/hybrid_ui.py (YENİ) — eğitim orkestrasyonu,
    session sözleşmesi, tahmin adaptörü, sessiz fallback
  * src/pvquant/reporting/contracts.py — apply_hybrid_session +
    holdout_rmse_kw alanı (+ __init__ dışa açılım)
  * tests/test_ui_hybrid_integration.py (YENİ) — 8 test
- hybrid_ui.py / test_ui_hybrid_integration.py : patch tutmazsa elle
  kopyalanacak asıllar (patch ile birebir aynı)
- FRONTEND_ENTEGRASYON.md : 3 sayfaya kopyala-yapıştır bloklar

## Uygulama sırası (2-3 saatlik plan)
1. (20 dk) Patch + testler: git apply hibrit_ui_cekirdek.patch
   → PYTHONPATH=src pytest tests/ → 137/137 beklenir (129 + 8)
2. (45 dk) kalibrasyon.py butonu (FRONTEND md, bölüm 1) → UI'da
   uçtan uca dene: eğitim + "Hibrit devrede" kartı
3. (10 dk) raporlar.py tek satırı (bölüm 2) → PDF'te Mod C rozeti +
   HOLDOUT kutusu — TUR 5'İN ASIL HEDEFİ BURADA TAMAMLANIR
4. (30-45 dk, vakit kalırsa) tahminler.py bandı (bölüm 3)
Vakit sıkışırsa 4 düşer; 1-3 hedefi karşılar.

## Tasarım kararları (savunma için)
- UX (b): fizik önce, hibrit ikinci buton. Önce/sonra karşılaştırması
  görünür ("%27.5 → %18.5"), hata izolasyonu bedava, 60 sn kör
  spinner yok.
- Orkestrasyon UI'da değil pipeline'da (hybrid_ui.py): Streamlit'siz
  test edilebilir — 8 test bunun kanıtı. "Arayüz hesap yapmaz,
  çağırır" sözleşmesi korunur.
- Meteo paylaşımı: ghi/t_air/wind HistoricalData'ya enjekte edilir;
  models_v2'nin saha-meteo kısayolu devreye girer, ikinci API çağrısı
  OLMAZ.
- Sessiz fallback: run_hybrid_training istisna YÜKSELTMEZ; ok=False +
  logger.exception. UI mavi bilgi mesajı basar, fizik akışı sürer.
- Saatlik kantil dürüstlüğü: models_v2 yalnız dönem-toplamı kantili
  verir; saatlik bant toplam oranlarının ölçeklenmesidir ve bu not
  adaptör docstring'inde açıkça yazılıdır.
