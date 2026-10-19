# 19.10 — ilk boyama: font ön yüklemesinin yeri ve CSS'in HTML'e gömülmesi

Replikalar (olc/ortak.mjs): `sonra` = 0dee665 derlemesi (karşılaştırma tabanı) · `arag` = sonra + font preload'ları `<body>` başındaki
betikle (G1) · `arah` = sonra + font preload'ları `<body>` başında statik (G2) · `arai` = arah + giriş CSS'i `<style>` olarak gömülü,
modül betiği stilin ardında. Deney kopyaları derlemesiz üretildi: `olc/iz/deney-font.mjs`, `olc/iz/deney-css.mjs` (index.html.br/.gz
yeniden yazılır). Kaynakta uygulanan sürümün derlediği index.html, `arai`ninkiyle boşluk dışında birebir aynı (diff, 19.10).

Dosyalar (konsol çıktıları olduğu gibi):
- `izleme.txt` — Chromium izlemesi (olc/iz/iz.mjs + kisa.mjs/ara.mjs): CSS bitince çizimin ~100 ms zamanlayıcıyla beklediği an.
- `kritik-yol-chromium.txt` — olc/kritik-yol.mjs, yavaş 4G, 5'er koşu dönüşümlü (sonra/arah, sonra/arah/arai).
- `kritik-yol-firefox-webkit.txt` — aynı ölçüm Firefox ve WebKit'te, 3'er koşu (sonra/arai).
- `lighthouse/`, `tekrar/lighthouse/` (../ara-arai) — Lighthouse 12, arai ve sonra.

G1 reddedildi: gövdedeki klasik betik bekleyen stil sayfasını bekliyor (betik CSS'ten sonra çalıştı), fontlar ~530 ms geç başladı.

## Poster ertelemesini yalnız dar ekrana sınırlama (araj) — UYGULANMADI
`araj` = sonra3 (font <body> + CSS gömülü) + poster ön yüklemesi yalnız ≤760 px'te FCP bildirimini bekler, geniş ekranda betik
çalışınca başlar (`olc/iz/deney-poster.mjs`). Ölçüm `olc/iz/lcp.mjs` (Chromium, yavaş 4G, 5'er dönüşümlü koşu; `lcp-poster-chromium.txt`):
poster isteği ~90–110 ms erken başlıyor (768: 639–701 ↔ 709–757 ms; 1920: 637–665 ↔ 726–765 ms) ama bitişi aynı (hat dolu; 768 medyan
3901 ↔ 3894 ms, 1920 3909 ↔ 3898 ms). LCP 768 medyan 4208 ↔ 4288 ms (koşu yayılımı 4064–4448 içinde), 1920 karar verilemez
(4336–5900). FCP geniş ekranda 12–28 ms geç. CSS gömüldükten sonra ilk boyama ~0,7 sn'ye indiği için ertelemenin bedeli ölçülebilir
olmaktan çıktı → değişiklik yapılmadı.

Yan bulgu: başsız Chromium posteri (feConvolveMatrix süzgeçli) yazılımla tarıyor (izleme: 65 RasterTask × ~30 ms; commit 722 ms bekliyor),
geniş ekranda poster LCP'si inişinden 0,6–0,9 sn sonra. Pencereli Chromium'da (GPU) poster bitişi + ~120 ms (LCP 4012–4020 ms,
`lcp-poster-chromium.txt` sonu). Matristeki Chromium 768/1920 LCP değerleri bu yüzden gerçek Chrome'dan yüksek (önce ve sonra eşit şişkin).
