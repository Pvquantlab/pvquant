# 19.10 — Firefox: hero keskinleştirmesi WebGL tuvalinde

Sorun (REPORT §8, KOK-NEDENLER K1): `#vt-keskin` (feConvolveMatrix) Firefox WebRender'da yok → her video karesi işlemcide süzülüyor,
kaydırma ağır. Önceki deneme (`6dfbb35`, feOffset×4 + feComposite×4) videoda kare düşürdüğü için geri alınmıştı.

Deney (enjeksiyon, `olc/iz/keskin-webgl.js`; replika `sonra3` = c9944cf): tek geçişli parça gölgelendiricisi, her sunulan video karesinde
(requestVideoFrameCallback) doku + çizim. Kod sürümü: `web/src/features/vitrin/keskinGL.ts` (replika `sonra4` = c9944cf + keskinGL).

## Görüntü eşdeğerliği (stok Firefox 158 / Chrome 155, pencereli, 1440x900@2, video 10,0 sn'de duraklatıldı) — `olc/iz/webgl-esdeger.mjs`
Konsol çıktısı (iç bölge, kenar 6 px hariç; «ozgun» = sayfanın CSS süzgeci):

    firefox-stok firefox/158.0 1440x900
       ozgun-tekrar  iç: en büyük 0 · ort 0 · >2 %0.000 · >4 %0.000 · >8 %0.000
       webgl-css     iç: en büyük 36 · ort 2.52 · >2 %36.709 · >4 %10.630 · >8 %2.770
       webgl-aygit   iç: en büyük 101 · ort 9.959 · >2 %61.549 · >4 %42.441 · >8 %32.393
       filtresiz     iç: en büyük 136 · ort 14.323 · >2 %53.350 · >4 %44.793 · >8 %37.643
       webgl-kimlik  iç: en büyük 136 · ort 15.137 · >2 %64.610 · >4 %47.396 · >8 %38.089
       webgl-css-1x  iç: en büyük 185 · ort 13.547 · >2 %60.901 · >4 %46.221 · >8 %37.717
       kimlik↔filtresiz iç: en büyük 15 · ort 1.905 · >2 %21.417 · >4 %3.089 · >8 %0.232
    chrome 155.0.8059.84 1440x900
       webgl-css     iç: en büyük 101 · ort 13.141 · >2 %95.408 · >4 %82.878 · >8 %49.178
       webgl-aygit   iç: en büyük 39 · ort 7.998 · >2 %97.809 · >4 %87.511 · >8 %42.133
       filtresiz     iç: en büyük 91 · ort 6.179 · >2 %42.135 · >4 %34.217 · >8 %24.413
       webgl-kimlik  iç: en büyük 100 · ort 10.934 · >2 %96.345 · >4 %83.470 · >8 %46.901
       kimlik↔filtresiz iç: en büyük 24 · ort 7.792 · >2 %98.381 · >4 %88.490 · >8 %41.339

Kenar enerjisi (`olc/iz/kenar.mjs`, ortalama Sobel): Firefox ozgun 18,201 · webgl-css 18,130 · webgl-css-1x 11,203 · webgl-aygit 12,436 ·
filtresiz 8,242 | Chrome ozgun 12,964 · webgl-aygit 12,459 · filtresiz 8,604.
Sonuç: Gecko çekirdeği aygıt çözünürlüğünde, komşuları 1 CSS pikseli uzaktan alarak uyguluyor (webgl-css); 1x hesaplayıp büyütmüyor
(webgl-css-1x uzak). Kalan ortalama 2,5/255 fark ardışık düzenden (kimlik çekirdeği ↔ süzgeçsiz video: 1,9/255 — video ölçekleme süzgeci).
Chrome'da WebGL↔video karşılaştırması renk yönetimi farkıyla kirli (kimlik↔filtresiz 7,8/255) — Chrome'da tuval kullanılmıyor.

## Gerçek derleme (sonra4) — `olc/iz/son-esdeger.mjs` (stok Firefox 158; tuval ↔ aynı sayfada CSS süzgecine dönüş ↔ önceki derleme)

    1440x900 sonra4 {"tuval":true,"videoSuzgec":"none","t":10}
       sonra4 tuval ↔ aynı sayfa CSS süzgeci: en büyük 38 · ort 2.81 · >2 %41.3 · >4 %13.7 · >8 %4.1
       sonra4-css ↔ sonra3: en büyük 0 · ort 0.00 · >2 %0.0 · >4 %0.0 · >8 %0.0
       kenar enerjisi: sonra4 tuval 21.925 · sonra4 CSS 22.013 · sonra3 22.013
    390x844 sonra4 {"tuval":true,"videoSuzgec":"none","t":10}
       sonra4 tuval ↔ aynı sayfa CSS süzgeci: en büyük 74 · ort 3.49 · >2 %38.5 · >4 %19.7 · >8 %8.9
       sonra4-css ↔ sonra3: en büyük 0 · ort 0.00 · >2 %0.0 · >4 %0.0 · >8 %0.0
       kenar enerjisi: sonra4 tuval 17.006 · sonra4 CSS 16.994 · sonra3 16.994

## Maliyet
- Deney, aynı sayfada dönüşümlü (`boya.jsonl`, 3 koşu, 1440@2): kaydırma CPU mevcut 2,67/1,59/1,61 · webgl 0,35/0,65/0,35 ·
  filtresiz-video 0,33/0,36/0,63 çekirdek; kaydırmada sunulan video karesi (3 sn) mevcut 8/14/14 · webgl 17/17/17.
- Gerçek derlemeler dönüşümlü (`../webgl-son/k1..k3/boya.jsonl`, açılıştan ~5 sn sonra, aynı konum):
  1440@2 kaydırma CPU 2,66/2,70/2,69 → 0,68/0,80/0,73 · p95 49,0/66,1/49,0 → 17,7/33,3/32,7 ms · video karesi 8/8/8 → 17/15/17;
  390@3 1,79/1,71/1,70 → 0,31/0,30/0,32 · p95 66,9/66,6/66,4 → 17,5/17,6/18,6 ms · kaçan kare %9–11 → %1. Düşen video karesi her yerde 0.
- Boşta 30 sn (`../webgl-son/video-zaman.jsonl`, 5 sn'lik pencereler): sonra4 0 düşen / 103–106, CPU 0,82–1,2 (ilk pencere) → 0,30–0,36;
  sonra3 0 düşen, CPU 3,59 (ilk pencere) → 0,07–0,18. Durağan oynatmada +~0,2 çekirdek (süzgeçsiz video 0,18–0,34 ile aynı düzey);
  texSubImage2D bunu değiştirmedi (`../webgl-son/alt/`).
- `olc/iz/ekran-hiz.mjs` GEÇERSİZ (ekran görüntüsü alma hızı iki derlemede farklı ve videoyu yavaşlatıyor; rVFC sayacı ikinci
  bölgede çift sayıyor) — sonuç kullanılmadı.

## Bağımsız inceleme sonrası (19.10, `22fb97f`) — `../webgl-son/`
- **Yoğunluk değişimi** (`dpr-degis.txt`, stok Firefox 158, setViewport deviceScaleFactor 2 → 1 → 1,5 → 3 → 2): tampon 2850×1800 →
  1425×900 → 2138×1350 → 4275×2700 → 2850×1800 (önce: hep 2850×1800). Firefox 158 ResizeObserver `device-pixel-content-box`'ta
  fiziksel ekranın yoğunluğunu bildiriyor (1x/3x geçersiz kılmada da 601 = 300,5 × 2) ve yoğunluk değişince tetiklenmiyor;
  `matchMedia('(resolution: …dppx)')` her değişimde tetikleniyor (`olc/iz/ro-sina.mjs`). Bu yüzden tampon = kesirli CSS kutusu × dpr.
- **1x ekranlar** (`son-esdeger.txt`, tuval ↔ aynı sayfada CSS süzgeci, ortalama fark ÷255 · kenar enerjisi tuval ↔ CSS):
  1366×768@1 5,40 (19,02 ↔ 19,03) · 1440×900@1 2,78 (19,49 ↔ 19,52) · 1920×1080@1 2,56 (17,58 ↔ 17,58) · 1440×900@2 2,81 (21,93 ↔ 22,01) ·
  390×844@3 3,49 (17,01 ↔ 16,99). Önceki sürüm 1366@1'de 20,39 idi: tamsayı kutu (clientHeight 776 ↔ gerçek 775,6) ve tamponu kutuya
  germe varsayımı; 1x'te çok ince panel deseni ~0,4 px kayıyordu (`1366-geometri.txt`: kimlik tuvali ↔ süzgeçsiz video 7,6 → kesirli
  kutuyla 1,56). Firefox tuvali germiyor: tampon satırı aygıt pikseline birebir oturuyor.
- **Reddedilenler:** mipmap (WebGL2) ve piksel alanında 2×2 / 3×3 kutu örneklemesi CSS süzgecinden uzaklaştırıyor (1440@1: 11,0 / 5,9 /
  6,5 ↔ 2,5; kenar enerjisi 13,5 / 15,5 ↔ 16,4) — Gecko da çift doğrusal örnekliyor (`kucultme-varyant.txt`); hedef dikdörtgeni aygıt
  pikseline yuvarlamak da kötüleştiriyor (`snap.txt`).
- **Ara sonuç (hatalı sürüm, belge için):** `dpr1-esdeger.txt` — device-pixel-content-box'lı ilk düzeltme 1x'te 2x tampon kullanıyordu
  (1920@1 5,59 · 1440@1 8,38 · 1366@1 18,82; tuval CSS'ten %10 yumuşak). `bayat-kare.txt`'teki 1440@1 5,60 de o sürümden.
- **Bayat kare yok** (`bayat-kare.txt`): duraklat + sar sonrası rVFC bir kez geliyor, tuval yeni kareyi çiziyor.

## Yazılımla birleştirme (19.10, `d853320`)
Son doğrulama zincirinin başsız Firefox etkileşim ölçümü (`../ara-son-e1e6b3c/etkilesim.jsonl`): tuval etkinken boşta kare aralığı
ortancası 1440'ta 100–133, 1920'de 150–200 ms (önceki derlemede 16,7). `../webgl-son/yazilim-ff.txt`: Playwright Firefox 157 başsızda
WebGL bağlamı failIfMajorPerformanceCaveat'i geçiyor, tuval etkin, ortanca 99,8 ms (CSS süzgeçli derleme 16,7). Düzeltme: ilk saniye
kare sınaması (ortanca > 25 ms → söküm + 7 gün kayıt). `yazilim-ff2.txt`: 1. açılışta tuval 1656 ms'de etkin, 2173 ms'de söküldü,
sonra 16,7 ms; 2. açılışta hiç kurulmadı. `../webgl-son/sinama/`: stok Firefox 158 (donanım) tuval 30 sn etkin kaldı, düşen kare 0.
