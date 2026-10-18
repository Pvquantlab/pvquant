<!-- olc/ab-ozet.mjs tarafından üretildi; elle düzenlemeyin -->

## Boya / birleştirme A/B (hero ekranda, video oynarken; değişkenler yük SONRASI aynı sayfada; medyan)

Sürümler: firefox-stok firefox/158.0 · chrome 155.0.8059.84 · pw-webkit 27.2 · pw-firefox 157.0

### 5 sn boşta (hero, video oynuyor)

| sürücü · kip · görünüm | n | değişken | kare p50 (ms) | p95 | kaçan kare | ana iş parç. tıkanma (ms) | video kare/sn (rVFC) | düşen video karesi | CPU (çekirdek) |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| chrome · basli · 1440x900 | 3 | mevcut | 16,7 | 18,0 | %0 | 0 | 21,0 | 0 | 0,30 |
| chrome · basli · 1440x900 | 3 | filtresiz | 16,6 | 18,0 | %0 | 0 | 21,0 | 0 | 0,26 |
| chrome · basli · 1440x900 | 3 | filtresiz-video | 16,7 | 17,9 | %0 | 0 | 21,0 | 0 | 0,23 |
| chrome · basli · 1440x900 | 3 | camsiz | 16,8 | 33,2 | %11 | 0 | 20,8 | 0 | 0,26 |
| chrome · basli · 1440x900 | 3 | filtresiz+camsiz | 16,7 | 18,0 | %0 | 0 | 21,0 | 0 | 0,23 |
| chrome · basli · 1440x900 | 3 | video-durgun | 16,7 | 17,9 | %0 | 0 | 0,0 | 0 | 0,08 |
| chrome · basli · 1440x900 | 3 | ayrisik | 16,6 | 18,1 | %0 | 0 | 21,0 | 0 | 0,27 |
| chrome · basli · 390x844 | 3 | mevcut | 16,7 | 18,0 | %0 | 0 | 21,0 | 0 | 0,26 |
| chrome · basli · 390x844 | 3 | filtresiz | 16,6 | 18,1 | %0 | 0 | 21,0 | 0 | 0,25 |
| chrome · basli · 390x844 | 3 | filtresiz-video | 16,7 | 18,3 | %0 | 0 | 21,0 | 0 | 0,25 |
| chrome · basli · 390x844 | 3 | camsiz | 16,7 | 18,0 | %0 | 0 | 21,0 | 0 | 0,26 |
| chrome · basli · 390x844 | 3 | filtresiz+camsiz | 16,7 | 18,2 | %0 | 0 | 21,0 | 0 | 0,20 |
| chrome · basli · 390x844 | 3 | video-durgun | 16,7 | 18,0 | %0 | 0 | 0,0 | 0 | 0,10 |
| chrome · basli · 390x844 | 3 | ayrisik | 16,7 | 18,1 | %0 | 0 | 21,0 | 0 | 0,26 |
| firefox-stok · basli · 1440x900 | 3 | mevcut | 16,7 | 18,7 | %0 | 0 | 16,2 | 0 | 0,10 |
| firefox-stok · basli · 1440x900 | 3 | filtresiz | 17,1 | 24,2 | %2 | 0 | 16,2 | 0 | 0,21 |
| firefox-stok · basli · 1440x900 | 3 | filtresiz-video | 17,0 | 24,4 | %1 | 0 | 16,4 | 0 | 0,19 |
| firefox-stok · basli · 1440x900 | 3 | camsiz | 16,7 | 19,1 | %0 | 0 | 16,2 | 0 | 0,10 |
| firefox-stok · basli · 1440x900 | 3 | filtresiz+camsiz | 17,3 | 23,8 | %2 | 0 | 16,4 | 0 | 0,15 |
| firefox-stok · basli · 1440x900 | 3 | video-durgun | 16,7 | 18,9 | %1 | 0 | 0,0 | 0 | 0,02 |
| firefox-stok · basli · 1440x900 | 3 | ayrisik | 16,7 | 26,6 | %9 | 0 | 15,0 | 4 | 0,23 |
| firefox-stok · basli · 390x844 | 3 | mevcut | 16,7 | 19,3 | %0 | 0 | 16,8 | 0 | 0,10 |
| firefox-stok · basli · 390x844 | 3 | filtresiz | 17,1 | 22,7 | %0 | 0 | 16,8 | 0 | 0,16 |
| firefox-stok · basli · 390x844 | 3 | filtresiz-video | 17,1 | 22,5 | %0 | 0 | 16,8 | 0 | 0,16 |
| firefox-stok · basli · 390x844 | 3 | camsiz | 16,8 | 19,4 | %0 | 0 | 16,8 | 0 | 0,09 |
| firefox-stok · basli · 390x844 | 3 | filtresiz+camsiz | 16,7 | 19,1 | %0 | 0 | 16,8 | 0 | 0,14 |
| firefox-stok · basli · 390x844 | 3 | video-durgun | 16,8 | 19,3 | %0 | 0 | 0,0 | 0 | 0,02 |
| firefox-stok · basli · 390x844 | 3 | ayrisik | 17,0 | 23,2 | %1 | 0 | 16,8 | 0 | 0,16 |
| pw-firefox · bassiz · 1440x900 | 2 | mevcut | 16,6 | 18,2 | %1 | 0 | 16,4 | 0 | 0,29 |
| pw-firefox · bassiz · 1440x900 | 2 | filtresiz | 16,7 | 18,0 | %0 | 19 | 16,3 | 8 | 1,13 |
| pw-firefox · bassiz · 1440x900 | 2 | filtresiz-video | 16,7 | 18,0 | %0 | 0 | 16,4 | 6 | 1,14 |
| pw-firefox · bassiz · 1440x900 | 2 | camsiz | 16,7 | 18,1 | %0 | 0 | 16,5 | 0 | 0,15 |
| pw-firefox · bassiz · 1440x900 | 2 | filtresiz+camsiz | 16,6 | 17,9 | %0 | 0 | 16,4 | 0 | 0,90 |
| pw-firefox · bassiz · 1440x900 | 2 | video-durgun | 16,7 | 18,3 | %0 | 0 | 0,0 | 0 | 0,06 |
| pw-firefox · bassiz · 1440x900 | 2 | ayrisik | 16,7 | 18,0 | %0 | 23 | 16,3 | 79 | 1,08 |
| pw-webkit · basli · 1440x900 | 3 | mevcut | 17,0 | 19,0 | %0 | 0 | 21,0 | 0 | 0,20 |
| pw-webkit · basli · 1440x900 | 3 | filtresiz | 17,0 | 19,0 | %0 | 0 | 20,8 | 0 | 0,20 |
| pw-webkit · basli · 1440x900 | 3 | filtresiz-video | 17,0 | 19,0 | %0 | 0 | 20,8 | 0 | 0,20 |
| pw-webkit · basli · 1440x900 | 3 | camsiz | 17,0 | 19,0 | %0 | 0 | 21,0 | 0 | 0,20 |
| pw-webkit · basli · 1440x900 | 3 | filtresiz+camsiz | 17,0 | 19,0 | %0 | 0 | 21,0 | 0 | 0,19 |
| pw-webkit · basli · 1440x900 | 3 | video-durgun | 17,0 | 19,0 | %0 | 0 | 0,0 | 0 | 0,15 |
| pw-webkit · basli · 1440x900 | 3 | ayrisik | 17,0 | 19,0 | %0 | 0 | 20,8 | 0 | 0,20 |
| pw-webkit · basli · 390x844 | 3 | mevcut | 199,0 | 3480,0 | %0 | 0 | 0,8 | 0 | 0,13 |
| pw-webkit · basli · 390x844 | 3 | filtresiz | 17,0 | 18,5 | %0 | 0 | 20,4 | 1 | 0,20 |
| pw-webkit · basli · 390x844 | 3 | filtresiz-video | 17,0 | 19,0 | %0 | 0 | 20,8 | 0 | 0,20 |
| pw-webkit · basli · 390x844 | 3 | camsiz | 17,0 | 35,0 | %0 | 0 | 11,8 | 0 | 0,14 |
| pw-webkit · basli · 390x844 | 3 | filtresiz+camsiz | 1008,0 | 8614,0 | %13 | 0 | 0,8 | 0 | 0,16 |
| pw-webkit · basli · 390x844 | 3 | video-durgun | 1034,0 | 8618,0 | %33 | 0 | 0,0 | -2 | 0,17 |
| pw-webkit · basli · 390x844 | 3 | ayrisik | 2634,0 | 5096,0 | %25 | 0 | 0,8 | -6 | 0,12 |

### 3 sn kaydırma

| sürücü · kip · görünüm | n | değişken | kare p50 (ms) | p95 | kaçan kare | ana iş parç. tıkanma (ms) | video kare/sn (rVFC) | düşen video karesi | CPU (çekirdek) |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| chrome · basli · 1440x900 | 3 | mevcut | 16,8 | 34,7 | %15 | 0 | 7,0 | 0 | 0,33 |
| chrome · basli · 1440x900 | 3 | filtresiz | 16,7 | 33,5 | %9 | 0 | 7,0 | 0 | 0,39 |
| chrome · basli · 1440x900 | 3 | filtresiz-video | 16,7 | 33,1 | %8 | 0 | 7,0 | 0 | 0,39 |
| chrome · basli · 1440x900 | 3 | camsiz | 16,7 | 34,4 | %14 | 0 | 7,0 | 0 | 0,32 |
| chrome · basli · 1440x900 | 3 | filtresiz+camsiz | 16,7 | 32,9 | %8 | 0 | 7,0 | 0 | 0,33 |
| chrome · basli · 1440x900 | 3 | video-durgun | 16,8 | 48,5 | %15 | 0 | 0,0 | 0 | 0,28 |
| chrome · basli · 1440x900 | 3 | ayrisik | 16,7 | 34,0 | %13 | 0 | 6,7 | 0 | 0,32 |
| chrome · basli · 390x844 | 3 | mevcut | 16,7 | 18,1 | %0 | 0 | 6,7 | 0 | 0,38 |
| chrome · basli · 390x844 | 3 | filtresiz | 16,7 | 17,9 | %0 | 0 | 6,7 | 0 | 0,42 |
| chrome · basli · 390x844 | 3 | filtresiz-video | 16,7 | 18,0 | %0 | 0 | 6,7 | 0 | 0,42 |
| chrome · basli · 390x844 | 3 | camsiz | 16,7 | 17,9 | %0 | 0 | 6,7 | 0 | 0,29 |
| chrome · basli · 390x844 | 3 | filtresiz+camsiz | 16,7 | 17,9 | %0 | 0 | 6,7 | 0 | 0,22 |
| chrome · basli · 390x844 | 3 | video-durgun | 16,6 | 18,1 | %0 | 0 | 0,0 | 0 | 0,34 |
| chrome · basli · 390x844 | 3 | ayrisik | 16,7 | 18,0 | %0 | 0 | 6,7 | 0 | 0,38 |
| firefox-stok · basli · 1440x900 | 3 | mevcut | 16,6 | 28,9 | %7 | 2 | 4,7 | 0 | 1,60 |
| firefox-stok · basli · 1440x900 | 3 | filtresiz | 16,7 | 23,9 | %3 | 0 | 5,0 | 0 | 0,36 |
| firefox-stok · basli · 1440x900 | 3 | filtresiz-video | 16,6 | 23,1 | %2 | 0 | 5,3 | 0 | 0,33 |
| firefox-stok · basli · 1440x900 | 3 | camsiz | 16,6 | 25,7 | %6 | 0 | 4,7 | 0 | 1,18 |
| firefox-stok · basli · 1440x900 | 3 | filtresiz+camsiz | 16,7 | 22,0 | %3 | 0 | 5,7 | 0 | 0,25 |
| firefox-stok · basli · 1440x900 | 3 | video-durgun | 16,6 | 25,9 | %5 | 21 | 0,0 | 0 | 0,88 |
| firefox-stok · basli · 1440x900 | 3 | ayrisik | 16,6 | 23,0 | %3 | 0 | 5,0 | 0 | 0,32 |
| firefox-stok · basli · 390x844 | 3 | mevcut | 16,7 | 19,6 | %2 | 0 | 5,3 | 0 | 0,42 |
| firefox-stok · basli · 390x844 | 3 | filtresiz | 16,7 | 17,6 | %0 | 0 | 5,3 | 0 | 0,22 |
| firefox-stok · basli · 390x844 | 3 | filtresiz-video | 16,7 | 18,6 | %0 | 0 | 5,3 | 0 | 0,21 |
| firefox-stok · basli · 390x844 | 3 | camsiz | 16,7 | 18,8 | %2 | 0 | 5,3 | 0 | 0,36 |
| firefox-stok · basli · 390x844 | 3 | filtresiz+camsiz | 16,7 | 17,8 | %0 | 0 | 5,3 | 0 | 0,15 |
| firefox-stok · basli · 390x844 | 3 | video-durgun | 16,7 | 18,6 | %1 | 0 | 0,0 | 0 | 0,25 |
| firefox-stok · basli · 390x844 | 3 | ayrisik | 16,7 | 17,8 | %0 | 0 | 5,3 | 0 | 0,21 |
| pw-firefox · bassiz · 1440x900 | 2 | mevcut | 16,8 | 66,8 | %17 | 75 | 4,3 | 0 | 1,95 |
| pw-firefox · bassiz · 1440x900 | 2 | filtresiz | 16,7 | 33,9 | %11 | 0 | 5,3 | 1 | 1,27 |
| pw-firefox · bassiz · 1440x900 | 2 | filtresiz-video | 16,7 | 26,0 | %6 | 23 | 5,7 | 2 | 1,20 |
| pw-firefox · bassiz · 1440x900 | 2 | camsiz | 16,7 | 18,9 | %5 | 6 | 5,3 | 0 | 1,05 |
| pw-firefox · bassiz · 1440x900 | 2 | filtresiz+camsiz | 16,7 | 18,0 | %0 | 0 | 5,3 | 0 | 0,73 |
| pw-firefox · bassiz · 1440x900 | 2 | video-durgun | 16,7 | 32,8 | %7 | 16 | 0,0 | 0 | 1,29 |
| pw-firefox · bassiz · 1440x900 | 2 | ayrisik | 16,7 | 33,0 | %7 | 31 | 5,2 | 15 | 1,20 |
| pw-webkit · basli · 1440x900 | 3 | mevcut | 17,0 | 18,0 | %0 | 0 | 7,3 | 0 | 0,40 |
| pw-webkit · basli · 1440x900 | 3 | filtresiz | 17,0 | 18,0 | %0 | 0 | 7,0 | 0 | 0,42 |
| pw-webkit · basli · 1440x900 | 3 | filtresiz-video | 17,0 | 18,0 | %0 | 0 | 7,0 | 0 | 0,40 |
| pw-webkit · basli · 1440x900 | 3 | camsiz | 17,0 | 18,0 | %0 | 0 | 7,3 | 0 | 0,49 |
| pw-webkit · basli · 1440x900 | 3 | filtresiz+camsiz | 17,0 | 18,0 | %0 | 0 | 7,0 | 0 | 0,49 |
| pw-webkit · basli · 1440x900 | 3 | video-durgun | 17,0 | 18,0 | %0 | 0 | 0,0 | 0 | 0,38 |
| pw-webkit · basli · 1440x900 | 3 | ayrisik | 17,0 | 18,0 | %0 | 0 | 7,3 | 0 | 0,41 |
| pw-webkit · basli · 390x844 | 3 | mevcut | 438,5 | 4335,0 | %1 | 0 | 1,0 | 0 | 0,11 |
| pw-webkit · basli · 390x844 | 3 | filtresiz | 17,0 | 18,0 | %1 | 0 | 7,0 | 0 | 0,49 |
| pw-webkit · basli · 390x844 | 3 | filtresiz-video | 17,0 | 19,0 | %2 | 0 | 6,0 | 0 | 0,43 |
| pw-webkit · basli · 390x844 | 3 | camsiz | 5147,0 | 5147,0 | %0 | 0 | 0,7 | 0 | 0,20 |
| pw-webkit · basli · 390x844 | 3 | filtresiz+camsiz | 5058,0 | 5058,0 | %0 | 0 | 0,3 | 0 | 0,09 |
| pw-webkit · basli · 390x844 | 3 | video-durgun | 5076,0 | 5076,0 | %0 | 0 | 0,7 | 0 | 0,07 |
| pw-webkit · basli · 390x844 | 3 | ayrisik | 1771,5 | 5275,0 | %0 | 0 | 0,7 | 0 | 0,10 |

Video 20 sn içinde oynamaya başlamayan koşular (geçersiz sayılmaz ama not edilir): once|pw-webkit|basli|1440x900|1, once|pw-webkit|basli|1440x900|3, once|pw-webkit|basli|390x844|1

## Yükleme yolu A/B — «mevcut» ↔ «videosuz» (kenar sunucu *.mp4 → 404; aynı derleme) · medyan

Bayt: vekilin alıcıya yazdığı (TLS dahil; süren medya indirmeleri dahil), gezinme başından.

| motor · görünüm · ağ · değişken | n | soğuk FCP | soğuk LCP | poster yüklendi | levha (adet / son) | video playing | bayt load | +5 sn | +10 sn | +20 sn | sıcak: video playing | sıcak bayt +12 sn | sıcak kayıt |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| chromium · 1440x900 · hizli3g · mevcut | 3 | 2744 | 3352 | 5698 | 8 / 18664 | — | 0,66 MB | 1,55 MB | 2,54 MB | 3,20 MB | — | 0,00 MB | y:true |
| chromium · 1440x900 · hizli3g · videosuz | 3 | 2864 | 3340 | 5827 | 8 / 18797 | — | 0,66 MB | 1,54 MB | 2,59 MB | 3,20 MB | — | 0,00 MB | y:true |
| chromium · 1440x900 · kablo20 · mevcut | 3 | 356 | 844 | 835 | 8 / 2685 | 4382 | 0,66 MB | 11,50 MB | 23,99 MB | 35,47 MB | 1547 | 9,01 MB | y:false |
| chromium · 1440x900 · kablo20 · videosuz | 3 | 352 | 824 | 815 | 8 / 2523 | — | 0,66 MB | 3,20 MB | 3,20 MB | 3,20 MB | — | 0,00 MB | y:false |
| chromium · 1440x900 · yavas4g · mevcut | 3 | 1364 | 1640 | 3889 | 8 / 16436 | — | 0,66 MB | 1,59 MB | 2,64 MB | 3,20 MB | — | 0,00 MB | y:true |
| chromium · 1440x900 · yavas4g · videosuz | 3 | 1336 | 1596 | 3833 | 8 / 16456 | — | 0,66 MB | 1,65 MB | 2,65 MB | 3,20 MB | — | 0,00 MB | y:true |
| chromium · 390x844 · hizli3g · mevcut | 3 | 2776 | 2776 | 5817 | 8 / 19661 | — | 0,66 MB | 1,56 MB | 2,48 MB | 3,20 MB | — | 0,00 MB | y:true |
| chromium · 390x844 · hizli3g · videosuz | 3 | 2696 | 2696 | 5689 | 8 / 19744 | — | 0,66 MB | 1,52 MB | 2,48 MB | 3,20 MB | — | 0,00 MB | y:true |
| chromium · 390x844 · kablo20 · mevcut | 3 | 528 | 532 | 533 | 8 / 3404 | 1406 | 0,15 MB | 10,13 MB | 10,13 MB | 10,13 MB | 550 | 0,00 MB | y:false |
| chromium · 390x844 · kablo20 · videosuz | 3 | 520 | 520 | 515 | 8 / 1818 | — | 0,19 MB | 3,20 MB | 3,20 MB | 3,20 MB | — | 0,00 MB | y:false |
| chromium · 390x844 · yavas4g · mevcut | 3 | 1100 | 1100 | 3819 | 8 / 16597 | — | 0,66 MB | 1,65 MB | 2,63 MB | 3,20 MB | — | 0,00 MB | y:true |
| chromium · 390x844 · yavas4g · videosuz | 3 | 1104 | 1104 | 3823 | 8 / 16610 | — | 0,66 MB | 1,66 MB | 2,65 MB | 3,20 MB | — | 0,00 MB | y:true |
| firefox · 1440x900 · hizli3g · mevcut | 3 | 2884 | 2884 | 5946 | 8 / 18935 | — | 0,66 MB | 1,52 MB | 2,58 MB | 3,20 MB | — | 2,30 MB | y:true |
| firefox · 1440x900 · hizli3g · videosuz | 3 | 2936 | 2936 | 5929 | 8 / 19602 | — | 0,66 MB | 1,56 MB | 2,44 MB | 3,20 MB | — | 0,00 MB | y:true |
| firefox · 1440x900 · kablo20 · mevcut | 3 | 357 | 395 | 539 | 8 / 5179 | 2821 | 0,66 MB | 12,77 MB | 25,15 MB | 35,40 MB | 355 | 13,63 MB | y:false |
| firefox · 1440x900 · kablo20 · videosuz | 3 | 286 | 404 | 522 | 8 / 1706 | — | 0,66 MB | 3,20 MB | 3,20 MB | 3,20 MB | — | 0,00 MB | y:false |
| firefox · 1440x900 · yavas4g · mevcut | 3 | 1290 | 1290 | 3920 | 8 / 16686 | — | 0,66 MB | 1,62 MB | 2,65 MB | 3,20 MB | — | 2,40 MB | y:true |
| firefox · 1440x900 · yavas4g · videosuz | 3 | 1282 | 1282 | 3821 | 8 / 16626 | — | 0,66 MB | 1,60 MB | 2,60 MB | 3,20 MB | — | 0,00 MB | y:true |
| firefox · 390x844 · hizli3g · mevcut | 3 | 2939 | 2939 | 5931 | 8 / 19006 | — | 0,66 MB | 1,56 MB | 2,55 MB | 3,20 MB | 2271 | 2,29 MB | y:true |
| firefox · 390x844 · hizli3g · videosuz | 3 | 2722 | 2722 | 5769 | 8 / 19024 | — | 0,66 MB | 1,56 MB | 2,55 MB | 3,20 MB | — | 0,00 MB | y:true |
| firefox · 390x844 · kablo20 · mevcut | 3 | 275 | 407 | 514 | 8 / 4386 | 977 | 0,66 MB | 10,14 MB | 10,14 MB | 10,14 MB | 238 | 0,00 MB | y:false |
| firefox · 390x844 · kablo20 · videosuz | 3 | 260 | 408 | 476 | 8 / 1648 | — | 0,66 MB | 3,20 MB | 3,20 MB | 3,20 MB | — | 0,00 MB | y:false |
| firefox · 390x844 · yavas4g · mevcut | 3 | 1295 | 1295 | 3837 | 8 / 16476 | — | 0,66 MB | 1,64 MB | 2,66 MB | 3,20 MB | 1422 | 2,38 MB | y:true |
| firefox · 390x844 · yavas4g · videosuz | 3 | 1278 | 1278 | 3896 | 8 / 16625 | — | 0,66 MB | 1,61 MB | 2,65 MB | 3,20 MB | — | 0,00 MB | y:true |
| webkit · 1440x900 · hizli3g · mevcut | 3 | 3016 | 4289 | 6287 | 8 / 19867 | — | 0,74 MB | 1,61 MB | 2,55 MB | 3,27 MB | — | 2,17 MB | y:false |
| webkit · 1440x900 · hizli3g · videosuz | 3 | 2911 | 4219 | 5918 | 8 / 18964 | — | 0,66 MB | 1,52 MB | 2,56 MB | 3,20 MB | — | 0,07 MB | y:false |
| webkit · 1440x900 · kablo20 · mevcut | 3 | 410 | 410 | 710 | 8 / 2163 | 3802 | 0,66 MB | 11,72 MB | 24,24 MB | 34,73 MB | 3636 | 25,82 MB | y:false |
| webkit · 1440x900 · kablo20 · videosuz | 3 | 413 | 413 | 773 | 8 / 2068 | — | 0,66 MB | 3,20 MB | 3,20 MB | 3,20 MB | — | 0,07 MB | y:false |
| webkit · 1440x900 · yavas4g · mevcut | 3 | 1258 | 2789 | 4071 | 8 / 16797 | — | 0,74 MB | 1,66 MB | 2,72 MB | 3,27 MB | — | 2,31 MB | y:false |
| webkit · 1440x900 · yavas4g · videosuz | 3 | 1251 | 2546 | 3930 | 8 / 16588 | — | 0,66 MB | 1,59 MB | 2,62 MB | 3,20 MB | — | 0,07 MB | y:false |
| webkit · 390x844 · hizli3g · mevcut | 3 | 2892 | 3460 | 5909 | 8 / 19446 | — | 0,66 MB | 1,51 MB | 2,47 MB | 3,20 MB | 6016 | 2,18 MB | y:false |
| webkit · 390x844 · hizli3g · videosuz | 3 | 2887 | 3431 | 5871 | 8 / 19895 | — | 0,66 MB | 1,52 MB | 2,38 MB | 3,20 MB | — | 0,07 MB | y:false |
| webkit · 390x844 · kablo20 · mevcut | 3 | 402 | 885 | 650 | 8 / 3469 | 2086 | 0,66 MB | 10,14 MB | 10,14 MB | 10,14 MB | 1315 | 7,01 MB | y:false |
| webkit · 390x844 · kablo20 · videosuz | 3 | 352 | 811 | 619 | 8 / 2055 | — | 0,66 MB | 3,20 MB | 3,20 MB | 3,20 MB | — | 0,07 MB | y:false |
| webkit · 390x844 · yavas4g · mevcut | 3 | 1361 | 1882 | 4022 | 8 / 16773 | — | 0,66 MB | 1,58 MB | 2,61 MB | 3,20 MB | 4472 | 2,30 MB | y:false |
| webkit · 390x844 · yavas4g · videosuz | 3 | 1242 | 1777 | 3918 | 8 / 16844 | — | 0,66 MB | 1,56 MB | 2,60 MB | 3,20 MB | — | 0,07 MB | y:false |

### Soğuk yüklemede indirilen font dosyaları (motor başına, tüm koşuların birleşimi)

- **chromium** (36 yükleme): inter-tight-latin-400-normal-iW8qmuJY.woff2 ×36 · inter-tight-latin-500-normal-BFXNXuvF.woff2 ×36 · inter-tight-latin-600-normal-BgSTtRxb.woff2 ×36 · inter-tight-tr-400-B33n_V-o.woff2 ×36 · inter-tight-tr-500-mVGzgBfJ.woff2 ×36 · inter-tight-tr-600-CHm7J1s7.woff2 ×36
- **firefox** (36 yükleme): inter-tight-latin-400-normal-iW8qmuJY.woff2 ×36 · inter-tight-latin-500-normal-BFXNXuvF.woff2 ×36 · inter-tight-latin-600-normal-BgSTtRxb.woff2 ×36 · inter-tight-latin-ext-500-normal-D3akd6m-.woff2 ×3 · inter-tight-tr-400-B33n_V-o.woff2 ×36 · inter-tight-tr-500-mVGzgBfJ.woff2 ×36 · inter-tight-tr-600-CHm7J1s7.woff2 ×36
- **webkit** (36 yükleme): inter-latin-opsz-normal-BwkfbSeq.woff2 ×10 · inter-tight-latin-400-normal-iW8qmuJY.woff2 ×36 · inter-tight-latin-500-normal-BFXNXuvF.woff2 ×36 · inter-tight-latin-600-normal-BgSTtRxb.woff2 ×36 · inter-tight-tr-400-B33n_V-o.woff2 ×36 · inter-tight-tr-500-mVGzgBfJ.woff2 ×36 · inter-tight-tr-600-CHm7J1s7.woff2 ×36
