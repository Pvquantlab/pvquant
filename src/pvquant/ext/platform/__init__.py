"""pvquant.ext.platform — ürün/platform modülleri (rapor 3.5; entegrasyon öncesi, çatı-bağımsız çekirdekler).

  portfoy       → çok santral toplama: kapasite-ağırlıklı KPI, toplam tahmin/gerçekleşen, en iyi/en kötü, alarm özeti
  tazeleme      → otomatik tazeleme: değişim damgası, koşullu istek (ETag), geri çekilmeli yoklama politikası, SSE üreteci, SPA kancası
  alarm         → kural kütüphanesi (şiddet, histerezis, tekilleştirme) + okundu/atama/eskalasyon durumu
  rapor_sablon  → şablon raporlar: kapasite testi (ASTM E2848), beklenen-gerçekleşen, fatura, kullanılabilirlik → yapı + Markdown/HTML
  api_anahtar   → API anahtarı üretimi/doğrulama (hash), kapsam, oran sınırı (token bucket), döndürme, webhook HMAC imzası
  paylasim      → rol tabanlı veri paylaşımı (SFA kalıbı): roller, izin kümesi, kuruluşlar arası paylaşım, politika + denetim izi
  tarife        → tarife/gelir yapılandırması: sabit, çok zamanlı (ToU), PTF-endeksli, YEKDEM (USD-endeksli), eskalasyon; saatlik gelir
BESS/kontrol bilerek yok (rapor 3.5: kapsam dışı). Hiçbir modül web çatısına bağlı değildir; `fastapi_ornek.py` bağlamayı gösterir.
"""
__version__ = "0.1.0"
