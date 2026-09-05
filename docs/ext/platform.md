# pvquant.ext.platform — ürün/platform modülleri (rapor 3.5; entegrasyon öncesi paket)

3.5 tablosunun yedi başlığının çatı-bağımsız Python çekirdekleri (BESS/kontrol bilerek yok). Depoya bağlı değildir;
FastAPI'ye bağlama `pvquant.ext.platform/fastapi_ornek.py`'de, SPA tarafı `tazeleme.USE_TAZELEME_JS`'te gösterilir.

| 3.5 satırı | Modül | Ne yapar |
|---|---|---|
| Portföy görünümü ve toplama | `portfoy` | Santral kayıtları, toplam seri (eksikte NaN), eksik haritası, kapasite-ağırlıklı KPI, en iyi/en kötü sıralama, günlük özet (İstanbul günü), alarm özeti |
| Otomatik tazeleme / canlı veri | `tazeleme` | Değişim damgası + ETag, koşullu 304 yanıt, görünürlük/hata geri çekilmeli yoklama politikası, SSE üreteci, React `useTazeleme` kancası |
| Alarm kural çeşitliliği + şiddet + okundu | `alarm` | 8 kurallık kütüphane (şiddet, histerezis, SLA eskalasyonu), motor: tara/okundu/ata/kapat; **varsayılan yalnız 2 kural açık** (El Kitabı P4 §3) |
| Şablon rapor çeşitliliği | `rapor_sablon` | Kapasite testi (ASTM E2848 regresyonu, %95 karar), beklenen-gerçekleşen (aylık, en zayıf aylar), fatura özeti (KDV), kullanılabilirlik; Markdown/HTML |
| Dışa dönük API + anahtarlar | `api_anahtar` | `pvq_<prefix>_<secret>` üretimi (hash saklanır), sabit-zamanlı doğrulama, kapsamlar, token-bucket oran sınırı, döndürme (grace), webhook HMAC imza/doğrulama |
| Rol tabanlı veri paylaşımı | `paylasim` | viewer/editor/admin + kuruluşlar arası zaman sınırlı paylaşım nesnesi (yalnız okuma izinleri), politika değerlendirme, takma ad (anonim), denetim izi |
| Tarife / gelir yapılandırması | `tarife` | Sabit, çok zamanlı (İstanbul saati dilimleri, doğrulamalı), PTF-endeksli (prim/taban/tavan), YEKDEM (USD-cent/kWh × aylık kur), eskalasyon (yıllık % / endeks), tarih dilimli yapılar, aylık gelir |

## Kurulum ve test
```bash
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
pytest -q     # 7 test, ağ gerektirmez
```

## Entegrasyon notları
- `alarm`: canlı üründe iki kural ilkesi korunur; yeni kural açmak `Ayar.acik_kurallar` ile bilinçli ürün kararıdır.
- `tazeleme`: telemetri şeridindeki "tazelenir" iddiası ancak bu katman canlıyken yazılır.
- `api_anahtar`: mevcut `api_keys` tablosuyla eşlenir (prefix, hash, tenant_id, scopes, revoked, expires_at, rpm); düz anahtar yalnız üretimde bir kez gösterilir.
- `paylasim`: RLS ile uyumlu — paylaşım kayıtları da tenant'a bağlı; sorgular politikadan geçer.
- `rapor_sablon`: yöntem adları rapor gövdesinde geçmez; mevcut 16 sayfalık PDF'e ek sayfa ya da ayrı kısa rapor.
