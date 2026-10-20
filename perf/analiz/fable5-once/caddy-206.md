# Caddy «precompressed» + 206 bulgusu (20.10, bulut Linux)

Replika ilk kurulumda Caddy 2.10.2 ile başlatıldı; her GET'e (Range başlığı yokken) `206 Partial Content` + `Content-Range: bytes 0-N/N`
döndü. Canlı (pvquant.com) aynı yapılandırmayla 200 dönüyor. Küçültülmüş yapılandırmalarla ayrıştırma (/tmp/claude-0/c206, tek
dosyalık kök, `curl -H 'Accept-Encoding: gzip, deflate, br, zstd'`):

| Yapılandırma | 2.9.1 | 2.10.0 | 2.10.1 | 2.10.2 | 2.11.7 |
|---|---|---|---|---|---|
| `file_server` (yalın) | — | — | — | 200 | — |
| `file_server { precompressed br gzip }` | — | — | — | **206** | — |
| `encode zstd gzip` + `file_server` | — | — | — | 200 | — |
| `header Cache-Control no-cache` + `file_server` | — | — | — | 200 | — |
| `encode` + `precompressed` (Caddyfile.web ile aynı) | 200 | 200 | **206** | **206** | 200 |
| aynı, `Accept-Encoding` yok (ham dosya) | — | — | — | 200 | — |

Kök neden: Caddy 2.10.1–2.10.2'nin `precompressed` yan dosya yolunda Range'siz isteğe 206 dönmesi (2.11.x'te yok). Tarayıcılar
sayfayı yine açıyor (Chromium/Firefox/WebKit/Edge duman sınaması geçti) ama 206 yanıtı HTTP anlambilimine göre kısmi içeriktir;
önbellekleme ve ara vekiller için güvenilmez. Replika bu yüzden 2.11.7'ye alındı (Docker Hub'da `caddy:2` etiketi 20.10.2026'da
2.11.7'yi gösteriyor, digest 173b26306d71) ve matris sıfırdan yeniden başlatıldı (206'lı ilk 10 dakikalık veri silindi).

Üretim riski: `Dockerfile.web` `FROM caddy:2` (yüzen etiket). Sunucudaki `docker compose build web` hangi 2.x'i çekerse onu kullanır;
2.10.1/2.10.2 çekilseydi canlı site her metin varlığına 206 dönecekti. Canlı şu an 200 (19.10 derlemesi). Karar: sürümü sabitle.
