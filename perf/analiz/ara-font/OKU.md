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
