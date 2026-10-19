<!-- olc/ab-ozet.mjs tarafından üretildi; elle düzenlemeyin -->

## Boya / birleştirme A/B (hero ekranda, video oynarken; değişkenler yük SONRASI aynı sayfada; medyan)

Sürümler: chrome 155.0.8059.84 · pw-webkit 27.2 · firefox-stok firefox/158.0

### 5 sn boşta (hero, video oynuyor)

| sürücü · kip · görünüm | n | değişken | kare p50 (ms) | p95 | kaçan kare | ana iş parç. tıkanma (ms) | video kare/sn (rVFC) | düşen video karesi | CPU (çekirdek) |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| chrome · basli · 1440x900 | 3 | mevcut | 16,7 | 18,2 | %0 | 0 | 21,0 | 0 | 0,29 |
| chrome · basli · 390x844 | 3 | mevcut | 16,7 | 17,9 | %0 | 0 | 21,0 | 0 | 0,27 |
| firefox-stok · basli · 1440x900 | 3 | mevcut | 16,7 | 18,9 | %0 | 0 | 16,4 | 0 | 0,10 |
| firefox-stok · basli · 390x844 | 3 | mevcut | 16,7 | 18,5 | %0 | 0 | 16,2 | 0 | 0,09 |
| pw-webkit · basli · 1440x900 | 3 | mevcut | 17,0 | 19,0 | %0 | 0 | 21,0 | 0 | 0,20 |

### 3 sn kaydırma

| sürücü · kip · görünüm | n | değişken | kare p50 (ms) | p95 | kaçan kare | ana iş parç. tıkanma (ms) | video kare/sn (rVFC) | düşen video karesi | CPU (çekirdek) |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| chrome · basli · 1440x900 | 3 | mevcut | 16,7 | 18,3 | %3 | 0 | 7,0 | 0 | 0,50 |
| chrome · basli · 390x844 | 3 | mevcut | 16,7 | 18,0 | %0 | 0 | 6,7 | 0 | 0,45 |
| firefox-stok · basli · 1440x900 | 3 | mevcut | 16,6 | 165,0 | %11 | 109 | 1,3 | 0 | 3,12 |
| firefox-stok · basli · 390x844 | 3 | mevcut | 16,8 | 68,5 | %12 | 13 | 4,3 | 0 | 2,11 |
| pw-webkit · basli · 1440x900 | 3 | mevcut | 17,0 | 18,0 | %1 | 0 | 7,0 | 0 | 0,50 |

Video 20 sn içinde oynamaya başlamayan koşular (geçersiz sayılmaz ama not edilir): sonra|chrome|basli|1440x900|1, sonra|chrome|basli|1440x900|2, sonra|chrome|basli|1440x900|3, sonra|chrome|basli|390x844|1, sonra|chrome|basli|390x844|2, sonra|chrome|basli|390x844|3, sonra|pw-webkit|basli|1440x900|1, sonra|pw-webkit|basli|1440x900|2, sonra|pw-webkit|basli|1440x900|3

## Yükleme yolu A/B — «mevcut» ↔ «videosuz» (kenar sunucu *.mp4 → 404; aynı derleme) · medyan

Bayt: vekilin alıcıya yazdığı (TLS dahil; süren medya indirmeleri dahil), gezinme başından.

| motor · görünüm · ağ · değişken | n | soğuk FCP | soğuk LCP | poster yüklendi | levha (adet / son) | video playing | bayt load | +5 sn | +10 sn | +20 sn | sıcak: video playing | sıcak bayt +12 sn | sıcak kayıt |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| chromium · 1440x900 · hizli3g · mevcut | 3 | 2656 | 2800 | 5669 | 8 / 19053 | — | 0,66 MB | 1,42 MB | 2,47 MB | 3,20 MB | — | 0,00 MB | y:true |
| chromium · 1440x900 · kablo20 · mevcut | 3 | 344 | 344 | 619 | 8 / 2012 | 4811 | 0,66 MB | 12,11 MB | 24,43 MB | 38,39 MB | 1185 | 22,97 MB | y:false |
| chromium · 1440x900 · yavas4g · mevcut | 3 | 1168 | 1168 | 3904 | 8 / 16972 | — | 0,66 MB | 1,52 MB | 2,56 MB | 3,20 MB | — | 0,00 MB | y:true |
| chromium · 390x844 · hizli3g · mevcut | 3 | 2768 | 2768 | 5816 | 4 / 13011 | — | 0,66 MB | 1,52 MB | 2,01 MB | 2,01 MB | — | 0,00 MB | y:true |
| chromium · 390x844 · kablo20 · mevcut | 3 | 320 | 320 | 565 | 8 / 1773 | 1962 | 0,66 MB | 10,14 MB | 10,14 MB | 10,14 MB | 349 | 0,00 MB | y:false |
| chromium · 390x844 · yavas4g · mevcut | 3 | 1292 | 1292 | 3923 | 4 / 10767 | — | 0,66 MB | 1,60 MB | 2,01 MB | 2,01 MB | — | 0,00 MB | y:true |
| firefox · 1440x900 · hizli3g · mevcut | 3 | 2854 | 2854 | 5931 | 0 / — | — | 0,66 MB | 0,66 MB | 0,66 MB | 0,66 MB | — | 0,00 MB | y:true |
| firefox · 1440x900 · kablo20 · mevcut | 3 | 295 | 431 | 606 | 8 / 1756 | 3298 | 0,66 MB | 12,77 MB | 25,22 MB | 35,09 MB | 354 | 13,68 MB | y:false |
| firefox · 1440x900 · yavas4g · mevcut | 3 | 1215 | 1215 | 3934 | 0 / — | — | 0,66 MB | 0,66 MB | 0,66 MB | 0,66 MB | — | 0,00 MB | y:true |
| firefox · 390x844 · hizli3g · mevcut | 3 | 2863 | 2863 | 5972 | 0 / — | — | 0,66 MB | 0,66 MB | 0,66 MB | 0,66 MB | — | 0,00 MB | y:true |
| firefox · 390x844 · kablo20 · mevcut | 3 | 303 | 304 | 598 | 8 / 1688 | 1865 | 0,15 MB | 10,14 MB | 10,14 MB | 10,14 MB | 249 | 0,00 MB | y:false |
| firefox · 390x844 · yavas4g · mevcut | 3 | 1213 | 1213 | 3925 | 0 / — | — | 0,66 MB | 0,66 MB | 0,66 MB | 0,66 MB | — | 0,00 MB | y:true |
| webkit · 1440x900 · hizli3g · mevcut | 3 | 2896 | 4202 | 6225 | 3 / 12465 | — | 0,74 MB | 1,59 MB | 1,81 MB | 1,81 MB | — | 0,00 MB | y:true |
| webkit · 1440x900 · kablo20 · mevcut | 3 | 415 | 415 | 768 | 8 / 2292 | 4201 | 0,74 MB | 11,22 MB | 23,72 MB | 34,99 MB | 3603 | 25,63 MB | y:false |
| webkit · 1440x900 · yavas4g · mevcut | 3 | 1254 | 2702 | 3917 | 3 / 10182 | — | 0,66 MB | 1,52 MB | 1,74 MB | 1,74 MB | — | 0,07 MB | y:true |
| webkit · 390x844 · hizli3g · mevcut | 3 | 2858 | 3482 | 5892 | 1 / 9262 | — | 0,66 MB | 1,12 MB | 1,12 MB | 1,12 MB | — | 0,07 MB | y:true |
| webkit · 390x844 · kablo20 · mevcut | 3 | 426 | 876 | 723 | 8 / 2076 | 2791 | 0,74 MB | 10,21 MB | 10,21 MB | 10,21 MB | 1351 | 6,94 MB | y:false |
| webkit · 390x844 · yavas4g · mevcut | 3 | 1339 | 1827 | 4165 | 1 / 7073 | — | 0,74 MB | 1,19 MB | 1,19 MB | 1,19 MB | — | 0,00 MB | y:true |

### Soğuk yüklemede indirilen font dosyaları (motor başına, tüm koşuların birleşimi)

- **chromium** (18 yükleme): inter-tight-latin-400-normal-iW8qmuJY.woff2 ×18 · inter-tight-latin-500-normal-BFXNXuvF.woff2 ×18 · inter-tight-latin-600-normal-BgSTtRxb.woff2 ×18 · inter-tight-tr-400-B33n_V-o.woff2 ×18 · inter-tight-tr-500-mVGzgBfJ.woff2 ×18 · inter-tight-tr-600-CHm7J1s7.woff2 ×18
- **webkit** (18 yükleme): inter-latin-opsz-normal-BwkfbSeq.woff2 ×13 · inter-tight-latin-400-normal-iW8qmuJY.woff2 ×18 · inter-tight-latin-500-normal-BFXNXuvF.woff2 ×18 · inter-tight-latin-600-normal-BgSTtRxb.woff2 ×18 · inter-tight-tr-400-B33n_V-o.woff2 ×18 · inter-tight-tr-500-mVGzgBfJ.woff2 ×18 · inter-tight-tr-600-CHm7J1s7.woff2 ×18
- **firefox** (18 yükleme): inter-tight-latin-400-normal-iW8qmuJY.woff2 ×18 · inter-tight-latin-500-normal-BFXNXuvF.woff2 ×18 · inter-tight-latin-600-normal-BgSTtRxb.woff2 ×18 · inter-tight-tr-400-B33n_V-o.woff2 ×18 · inter-tight-tr-500-mVGzgBfJ.woff2 ×18 · inter-tight-tr-600-CHm7J1s7.woff2 ×18
