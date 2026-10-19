# PVQuant — Tarayıcılar arası performans ve görsel tutarlılık raporu

Dal: `perf/cross-browser` (main'e birleştirilmedi, canlıya gönderilmedi). Temel: `main` d6ab50a (v2.458). Son kod commit'i: `160a22a`.
Ölçüm: 18–19.10.2026. «Önce» = d6ab50a, «sonra» = 160a22a (replika `final2`, veri `son/`); aynı replika düzeni (üretimdeki iki katmanlı
Caddy'nin yerel kopyası), aynı ağ vekili, aynı betikler, 3 koşu medyanı. Ham veri ve betikler `perf/` altında; §2 tabloları ham
dosyalardan betikle üretildi (`olc/rapor-tablo.mjs` → `son/RAPOR-TABLOLAR.md`, kabul ölçütleri `olc/kiyas.mjs` → `son/KIYAS.md`).

## 1. Özet

1. **Yavaş hatta açılış üç motorda hızlandı.** «/» Slow 4G ilk boyama (= telefonda LCP) 390 px'te Chromium 1104 → 812 ms, Firefox
   1226 → 773, WebKit 1313 → 721; Fast 3G'de 2,67–2,96 → 1,94–2,07 sn; /yontem Slow 4G 1,26–1,42 → 1,16–1,31 sn. Kök nedenler: Chromium
   `<head>`'deki font ön yüklemesi için çizimi ~100 ms bekletiyordu; 22 KB'lık CSS ayrı istekte JS/font/API ile bandı paylaşıyordu (CSS
   artık HTML'e gömülü); bu düzeltmenin /yontem'de yarattığı gerilemeyi ve hızlı hatta doğurduğu kısa yedek font geçişini bağımsız
   inceleme ve ölçüm yakaladı, ikisi de giderildi.
2. **Firefox'ta kaydırma hafifledi.** Hero videosundaki keskinleştirme (`feConvolveMatrix`, Firefox'ta işlemcide) Firefox'ta tek geçişli
   WebGL tuvalinde: stok Firefox 158, kaydırırken işlemci 1440@2 2,7–3,1 → 0,71–0,76 çekirdek, 390@3 1,8–1,9 → 0,38–0,42; kare p95
   49–68 → 18–19 ms; video kaydırırken tam hızda (1440'ta 3 sn'de 7–8 → 16–17 kare); düşen kare 0; görünüm 1x–3x'te aynı (kenar
   enerjisi ±%0,4).
   Ekran kartsız Firefox'ta tuval ilk saniyede kendini kapatır.
3. **Lighthouse «/» mobil 75 → 99** (koşular 47/75/85 → 84/99/99; 84'lük ilk koşu §2'de), masaüstü 93 → 100; /yontem 99 / 100
   korundu; TBT medyanı 68 ms, CLS 0.
4. **Önceki düzeltmeler korunuyor:** font gelince 25 px zıplama → 0–2 px; /yontem'de yanlış hero karesi → 0; yavaş hatta yenilemede
   Firefox/WebKit video indirmesi → 0; Firefox gereksiz latin-ext → 0/36; Safari kartları Chrome ölçüsünde; kartlar videodan önce.
   Chromium ve Firefox'ta 40/40 ekran görüntüsü piksel piksel aynı.
5. **Karşılanamayanlar ve bedeller (şeffaf):** 59 ölçütten 58'i karşılandı — Chromium 768×1024 Slow 4G LCP (474 KB'lık poster;
   ekran kartlı Chrome'da önce ve sonra ~4,0 sn, bant fiziği). Bedeller: index.html her yolda +22,8 KB (br); Lighthouse benzetimli FCP
   1,51 → 1,65 sn; Safari'de (WebKit) hızlı hatta ilk açılışta kısa yedek font → Inter Tight geçişi (20 Mbps'te 2/3, önce 0/3); yavaş hatta yedek
   yüz daha uzun görünür (kaydırmasız); Firefox'ta video oynarken boşta +~0,2 çekirdek; Firefox'un WebGL yolu Windows/Linux/Android'de
   sınanmadı (§7, §8).

## 2. Önce / sonra

**Lighthouse 12.8.2 (replika; Chromium; 3 koşu, medyan)**

| Sayfa · tür | Perf önce → sonra (koşular) | LCP | FCP | TBT | CLS | Erişil. / En iyi uyg. / SEO |
|---|---|---:|---:|---:|---:|---|
| `/` · mobil | **75 (47/75/85) → 99 (84/99/99)** | 7,51 sn → 1,80 sn | 1,51 sn → 1,65 sn | 124 → 68 ms | 0,000 → 0,000 | 100/100/91 → 100/100/91 |
| `/` · masaüstü | **93 (93/93/93) → 100 (100/100/100)** | 1 764 ms → 403 ms | 364 ms → 363 ms | 0 → 0 ms | 0,000 → 0,000 | 100/100/91 → 100/100/91 |
| `/yontem` · mobil | **99 (99/99/99) → 99 (99/99/99)** | 1,80 sn → 1,73 sn | 1,50 sn → 1,50 sn | 35 → 26 ms | 0,000 → 0,000 | 100/100/91 → 100/100/91 |
| `/yontem` · masaüstü | **100 (100/100/100) → 100 (100/100/100)** | 404 ms → 383 ms | 364 ms → 363 ms | 0 → 0 ms | 0,000 → 0,000 | 100/100/91 → 100/100/91 |

**«/» FCP, soğuk, medyan (ms): önce → sonra**

| | Ch 390 | Ch 768 | Ch 1440 | Ch 1920 | Fi 390 | Fi 768 | Fi 1440 | Fi 1920 | We 390 | We 768 | We 1440 | We 1920 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Kısıtsız | 124 → 80 | 156 → 92 | 216 → 108 | 300 → 160 | 177 → 75 | 369 → 71 | 108 → 66 | 184 → 70 | 161 → 86 | 106 → 200 | 116 → 211 | 228 → 207 |
| Slow 4G | 1 104 → 812 | 1 256 → 824 | 1 280 → 840 | 1 212 → 852 | 1 226 → 773 | 1 123 → 760 | 1 287 → 780 | 1 304 → 770 | 1 313 → 721 | 1 297 → 711 | 1 299 → 727 | 1 303 → 725 |
| Fast 3G | 2 700 → 2 032 | 2 748 → 2 048 | 2 736 → 2 052 | 2 908 → 2 068 | 2 671 → 1 993 | 2 714 → 2 013 | 2 816 → 1 999 | 2 893 → 1 996 | 2 897 → 1 954 | 2 954 → 1 941 | 2 961 → 1 950 | 2 957 → 1 950 |

**«/» LCP, soğuk, medyan (ms): önce → sonra**

| | Ch 390 | Ch 768 | Ch 1440 | Ch 1920 | Fi 390 | Fi 768 | Fi 1440 | Fi 1920 | We 390 | We 768 | We 1440 | We 1920 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Kısıtsız | 416 → 80 | 636 → 488 | 708 → 108 | 784 → 820 | 177 → 75 | 596 → 71 | 271 → 66 | 184 → 70 | 587 → 519 | 500 → 596 | 116 → 211 | 764 → 664 |
| Slow 4G | 1 104 → 812 | 4 196 → 4 308 | 1 644 → 840 | 4 404 → 4 760 | 1 299 → 773 | 1 123 → 760 | 1 287 → 780 | 1 304 → 770 | 1 807 → 1 710 | 1 748 → 760 | 2 567 → 2 409 | 1 824 → 792 |
| Fast 3G | 2 700 → 2 036 | 5 992 → 5 924 | 3 596 → 2 056 | 6 996 → 6 376 | 3 179 → 1 993 | 2 714 → 2 013 | 3 028 → 1 999 | 2 893 → 1 996 | 3 405 → 3 377 | 3 392 → 1 988 | 4 213 → 4 249 | 3 516 → 2 032 |

**«/yontem» FCP (= LCP), soğuk, medyan (ms): önce → sonra**

| | Ch 390 | Ch 768 | Ch 1440 | Ch 1920 | Fi 390 | Fi 768 | Fi 1440 | Fi 1920 | We 390 | We 768 | We 1440 | We 1920 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Kısıtsız | 124 → 100 | 136 → 100 | 184 → 124 | 156 → 128 | 138 → 94 | 309 → 92 | 132 → 98 | 139 → 105 | 175 → 110 | 118 → 110 | 145 → 116 | 160 → 124 |
| Slow 4G | 1 300 → 1 172 | 1 420 → 1 180 | 1 320 → 1 188 | 1 420 → 1 192 | 1 265 → 1 164 | 1 264 → 1 165 | 1 385 → 1 173 | 1 365 → 1 171 | 1 333 → 1 293 | 1 347 → 1 301 | 1 392 → 1 307 | 1 340 → 1 284 |
| Fast 3G | 3 048 → 2 820 | 3 028 → 2 860 | 3 124 → 2 832 | 3 144 → 2 876 | 3 031 → 2 810 | 2 916 → 2 811 | 2 903 → 2 818 | 2 910 → 2 818 | 2 996 → 2 955 | 2 998 → 2 940 | 3 025 → 2 936 | 3 036 → 2 942 |

En büyük öğe kayması (soğuk, tüm motor × görünüm × ağ × sayfa hücrelerinin en kötü medyanı): 36 → 2 px · Chromium CLS en kötü medyan: 0,016 → 0,000
Konsol hatası / 4xx-5xx / başarısız istek (sonra matrisi, 432 yükleme): 0

**Firefox kaydırma ve boşta (stok Firefox 158.0, pencereli; 0dee665 ↔ final2, dönüşümlü 3 koşu, açılıştan ~5 sn sonra)** — 0dee665'te
Firefox'un süzgeç yolu d6ab50a ile aynı (ilk deneme `6dfbb35` geri alınmıştı), bu yüzden «önce» olarak o kullanıldı.

| Görünüm | Kaydırma CPU (çekirdek) | Kaydırma kare p95 (ms) | Kaçan kare | Kaydırmada sunulan video karesi (3 sn) | Düşen video karesi | Boşta CPU |
|---|---|---|---|---|---|---|
| 1440 @2 | 2,72 / 3,07 / 2,73 → 0,71 / 0,76 / 0,71 | 49 / 67 / 68 → 19 / 18 / 18 | %6 / 8 / 6 → %4 / 2 / 4 | 8 / 7 / 8 → 16 / 17 / 16 | 0 / 0 / 0 → 0 / 0 / 0 | 0,15 / 0,27 / 0,15 → 0,40 / 0,37 / 0,38 |
| 390 @3 | 1,85 / 1,86 / 1,80 → 0,40 / 0,38 / 0,42 | 52 / 51 / 65 → 18 / 19 / 19 | %10 / 10 / 10 → %1 / 1 / 1 | 14 / 15 / 14 → 16 / 15 / 16 | 0 / 0 / 0 → 0 / 0 / 0 | 0,11 / 0,11 / 0,11 → 0,31 / 0,33 / 0,31 |

**Boşta video, 30 sn (stok Firefox, pencereli, 1440×900@2; 5 sn'lik 6 pencere)**

| Koşu | Tuval | Düşen / toplam kare | Sunulan kare (rVFC) | CPU (çekirdek) |
|---|---|---|---|---|
| 1 | tuval/süzgeç-yok | 0/105 0/105 0/105 0/104 0/105 0/105 | 79 81 80 81 81 81 | 0,59 0,36 0,37 0,36 0,36 0,32 |
| 2 | tuval/süzgeç-yok | 0/105 0/105 0/105 0/104 0/105 0/105 | 79 81 80 80 80 80 | 0,64 0,38 0,35 0,37 0,35 0,31 |

index.html: 10 897 B (br 2 966) → 156 029 B (br 25 735) · ayrı CSS isteği: var → yok (gömülü)

**Geniş ekranda poster-LCP, ekran kartlı (pencereli) Chromium, Slow 4G, 3 dönüşümlü koşu, medyan** (`son/poster-lcp-basli.txt`) —
başsız matriste Chromium süzgeçli posteri yazılımla taradığı için 768/1920 LCP hücreleri 0,6–0,9 sn şişkin ve oynak:

| | FCP önce → sonra | LCP önce → sonra | Poster isteği başlangıç → bitiş (sonra) |
|---|---:|---:|---|
| 768×1024 | 1208 → 856 ms | 3952 → 4040 ms | 859 → 3913 ms |
| 1920×1080 | 1388 → 968 ms | 4020 → 4032 ms | 971 → 3903 ms |

(768 «sonra» 1. koşu pencere açılışında FCP 5796 ms ile sapık; medyan ona dayanmıyor.)

**Açılışta ilk görünür metin — web fontuyla mı, yedek yüzle mi** (390×844, 3'er dönüşümlü koşu, d6ab50a ↔ 160a22a;
`son/font-ilk-metin.txt`; ilk metin = LCP API'sinin ilk metin adayı, üç motorda da destekleniyor; parantez içinde FCP medyanı):

| Hat | İlk metin yedek yüzle: Chromium önce → sonra | Firefox | WebKit |
|---|---|---|---|
| Kısıtsız | 0/3 → 0/3 (FCP 104 → 80 ms) | 0/3 → 0/3 (82 → 81) | 0/3 → 0/3 (117 → 107) |
| 20 Mbps / 40 ms | 0/3 → 0/3 (516 → 316) | 0/3 → 0/3 (299 → 299) | 0/3 → **2/3** (334 → 235) |
| Slow 4G | 3/3 → 3/3 (1124 → 804) | 3/3 → 3/3 (1295 → 794) | 2/3 → 3/3 (1267 → 698) |

Yavaş hatta fontlar ~1,4 sn'de geliyor: ilk metin önce de sonra da (WebKit önce 2/3) yedek yüzle; sonra daha erken görünüyor, yedek yüz
daha uzun kalıyor. Yedek yüz metrik eşlemeli, satırlar kaymıyor (en büyük öğe kayması 0–2 px).

**Bant ve video (vekil bayt sayacı; `analiz/yukleme-once-sonra.md`, ölçülen derleme a1fb5b8 — bu yollar sonra değişmedi)**

| | Önce | Sonra |
|---|---|---|
| Yavaş hatta yenileme (12 sn): Firefox / WebKit video baytı | 2,29–2,40 / 2,17–2,31 MB | 0,00 / 0,00–0,07 MB |
| 20 Mbps, 8 kart görselinin tamamlanması — Firefox 1440 / Firefox 390 / Chromium 390 / WebKit 390 | 5,18 / 4,39 / 3,40 / 3,47 sn | 1,76 / 1,69 / 1,77 / 2,08 sn |
| 20 Mbps, video «playing» — Firefox 1440 / Chromium 390 / WebKit 390 | 2,82 / 1,41 / 2,09 sn | 3,30 / 1,96 / 2,79 sn |
| Firefox latin-ext font inişi (soğuk /yontem, 36 yükleme) | 600: 19/36, 500: 9/36 | 0/36, 0/36 (son matris) |

**Gürültü ve yorum.** Aynı derlemenin kısıtlı hat FCP/LCP'si koşudan koşuya ve oturumdan oturuma ±150–200 ms oynayabiliyor (önceki
derlemelerde gözlendi); bu yüzden ±150 ms altındaki tekil farklar iyileşme/gerileme sayılmadı. Bu eşiğin üstündeki gerilemeler:
Chromium 1920 Slow 4G poster-LCP +356 ms ve 768 +112 ms (başsız yazılım taraması; ekran kartlı ölçümde fark yok, yukarıda); WebKit
kısıtsız FCP 768/1440'ta +94/+95 ms (önceki «sonra» derlemesinde de görülmüştü, e1e6b3c zincirinde 149/109 ms — oynak, nedeni
ayrıştırılmadı). Başsız Chromium/Firefox matrisinde etkileşim TBT'si ve kare süreleri yazılım GPU'sundan; kriter olarak Lighthouse TBT'si
alındı. Lighthouse «/» mobil 1. koşu (84): sayfa 112 ms'de yüklenmiş ama tarayıcı 1150 ms'ye dek hiç kare üretmemiş (ilk boyama = FCP =
1150 ms; 2. ve 3. koşuda 201 / 192 ms) — seri başındaki taze tarayıcı açılışına özgü; aynı imza gömülü CSS deneyinin ilk koşusunda da var
(`analiz/ara-font/lighthouse-gozlenen.txt`); e1e6b3c (97/98/99) ve 0dee665 (99/99/99) serilerinde görülmedi. Kök nedeni belirlenemedi;
kriter 3 koşunun medyanı.

**Kabul ölçütleri** — 59 ölçütten 58'i karşılandı (`son/KIYAS.md`). Kapsam: Lighthouse yalnız «/» ve «/yontem»; TBT Lighthouse'tan;
Firefox/Chromium oranı «Firefox en çok %20 yavaş» diye okundu (24/24 hücre). Karşılanmayan:

| Ölçüt | Değer | Neden |
|---|---|---|
| LCP ≤ 2,5 sn, Slow 4G, Chromium 768×1024 «/» | 4196 → 4308 ms (başsız); ekran kartlı 3952 → 4040 ms | LCP öğesi `<video poster>` (hero ekrandan kısa → Chromium posteri LCP sayıyor). 474 KB poster Slow 4G'de tek başına ~2,3 sn; poster baytı ve hero ölçüsü sahip kuralıyla sabit → bu hücrede ≤ 2,5 sn fiziksel olarak mümkün değil. Telefon genişliğinde (390) 812 ms ✅; Lighthouse mobil 1,80 sn ✅. |

## 3. Kök nedenler ve kanıt

Ayrıntı: [`analiz/KOK-NEDENLER.md`](analiz/KOK-NEDENLER.md). Kısaca:

| # | Belirti | Kök neden | Kanıt (çalıştırılmış ölçüm) | Commit |
|---|---|---|---|---|
| K1 | Firefox'ta kaydırma takılıyor | Hero videosundaki `feConvolveMatrix` Firefox WebRender'da yok: her video karesi işlemcide süzülüyor | Stok Firefox 158, pencereli: kaydırmada süzgeç kapalı 0,36 ↔ açık 1,60 çekirdek; cam (backdrop-filter) ikincil (1,18) | `0304003` + `22fb97f` + `d853320` (ilk deneme `6dfbb35` video kare düşürdüğü için `a1fb5b8` ile geri alındı) |
| K2 | Lighthouse mobil «/» 47–85, LCP savruluyor | React kabuğu ilk boyama bildiriminden önce devralıyor + 474 KB poster metin LCP'siyle aynı anda yüksek öncelikle iniyor | Ayrıştırma (ara derlemeler): yalnız devir 82–85 · yalnız poster 75–76 · ikisi 99/99/99 | `fdb8c6c`, `13e9f12` |
| K3 | Yavaş hatta yenilemede Firefox/WebKit video indiriyor | Önbellek testi yalnız Chromium biçimini tanıyor | Sıcak 3G: Firefox 2,3 MB, WebKit 2,2 MB (videosuz kontrol 0) | `0686656` |
| K4 | Mobilde düğmeler 25 px zıplıyor; Firefox fazladan font indiriyor | Yedek font (SF) Inter Tight'tan geniş; latin-ext aralığı çakışıyor | Kayma izleyicisi 25 px (üç motor); Firefox /yontem latin-ext-600 19/36; Firefox yüklenmemiş `local()` yüzü atlıyor | `89e910f`, `7c8c46d` |
| K5 | /yontem'de ana sayfa hero'su bir kare görünüyor | Kabuğu silen betik CSS'i bekliyordu | /yontem başlığı ≥30 px «kayıyor»: Firefox 17/36, Chromium 3/36 → 0 | `fa0c598` |
| K6 | Safari'de kartlar 19 px uzun | WebKit `aspect-ratio`'yu kenar boşluksuz genişlikten hesaplıyor | Enjeksiyonla 4 görünümde WebKit = Chromium | `b6daa3e` |
| K7 | Kaydıran ziyaretçi kartları boş görüyor | Video ile kart görselleri aynı anda bant paylaşıyor | 20 Mbps: Firefox 1440 kartlar 5,18 ↔ 1,71 sn (videosuz) | `02c875d` |
| K8 | Chrome'da yavaş hatta ilk boyama ~100 ms boşa bekliyor | Chromium, `<body>` oluşmadan eklenen font ön yüklemelerini ilk boyamayı engelleyen kaynak sayıyor (CSS'ten sonra ≤100 ms zamanlayıcı) | İzleme (Chromium 156 + kurulu Chrome 155): CSS'ten sonra `BeginLifecycleUpdatesIfRenderingReady` false, ~100 ms sonra zamanlayıcıyla true; `<body>`'ye alınca CSS bitişi → FCP 154–228 → 57–119 ms | `1353dc1` |
| K9 | Yavaş hatta ilk boyama CSS'i bekliyor, CSS bandı paylaşıyor | 22 KB'lık CSS ayrı istekte JS (74 KB), 4 font ve API ile aynı anda iniyor; bitişi 0,8–1,4 sn | Gömülünce FCP (Slow 4G, 390) Chromium 1112 → 692, Firefox ~1250 → 684, WebKit ~1280 → 693 ms; yayılım ±10 ms | `c9944cf` |
| K10 | /yontem ve panelde ilk boyama geriledi (K9 düzeltmesinin yan etkisi; bağımsız inceleme buldu) | Modül betiği gömülü stilin ardına alınınca JS'le çizilen yollarda JS isteği ~22 KB gecikti | Chromium Slow 4G /yontem FCP 1272–1372 → 1388–1512; düzeltmeyle 1180–1196 ms | `44fefcc` |
| K11 | Firefox tuvali yoğunluk değişince eski çözünürlükte; 1366×768@1'de ince desen kayıyor (bağımsız inceleme) | Tampon yalnız CSS boyu değişince yenileniyordu; Firefox `device-pixel-content-box`'ta fiziksel ekranı bildiriyor; tamsayı kutu (776 ↔ 775,6) | Yoğunluk 2 → 1 → 1,5 → 3: tampon artık 1425 → 2138 → 4275 px; 1366@1 fark 20,4 → 5,4 ÷255 | `22fb97f` |
| K12 | Ekran kartsız birleştirmede (software WebRender) Firefox tuvali sayfayı kilitliyor (son doğrulama zinciri buldu) | WebGL bağlamı «performans engeli»ni geçiyor ama tuval her karede işlemciye geri okunuyor | Başsız Firefox: boşta kare aralığı ortancası 16,7 → 99,8 ms; ilk saniye sınamasıyla tuval ~0,5 sn'de sökülüyor, sonra 16,7 ms | `d853320` |
| K13 | Hızlı hatta başlık ilk karelerde yedek fontla görünüyor (K8/K9 düzeltmelerinin yan etkisi; bağımsız inceleme sordu) | Sayfa artık fontlardan ~30–75 ms önce çiziliyor | 20 Mbps: ilk metin yedek yüzle Chromium 3/3, Firefox 3/3 (önce 0/3); 100 ms beklemeyle 0/3 | `160a22a` |

## 4. Commit bazlı değişiklikler

| Commit | Değişiklik | Beklenen etki | Risk |
|---|---|---|---|
| `49d8f2b` | Temel ölçüm + düzenek | — | — |
| `0686656` | K3: yavaş-hat kararını yalnız ağdan aktarılmış poster ölçümü yazar; önbellek biçimleri okur | Yavaş hatta yenilemede Firefox/WebKit video indirmez | Düşük; bayt alanı olmayan eski Safari'de yalnız «yavaş» yazılır |
| `fa0c598` | K5: `<head>`'de satır içi karar + tek CSS kuralı | /yontem'de yanlış hero karesi biter | Düşük; karar ifadesi gövde betiğiyle aynı (testli) |
| `89e910f` | K4: metrik eşlemeli `local()` yedek yüz + latin-ext aralık daraltması | FOUT'ta satır sayısı korunur; Firefox'ta ~38–76 KB az font | Web fontu HİÇ yüklenemeyen ziyaretçi SF yerine ölçeklenmiş Arial görür |
| `6dfbb35` | K1 ilk deneme: WebRender ilkelleri (8 primitif) | — | **Geri alındı** (`a1fb5b8`): boşta video 5 sn'de 18–53 kare düşürdü |
| `fdb8c6c` | K2: React devri FCP bildiriminden sonra (1 sn emniyet) | Gözlenen LCP kabuğun ilk boyamasına sabitlenir | Sıcak açılışta ilk ekran altı React'i bekler |
| `13e9f12` | K2: poster ön yüklemesi FCP bildiriminden sonra | Lighthouse mobil 99; metin LCP'si posterle yarışmaz | Poster birkaç on ms geç başlar |
| `b6daa3e` | K6: kart görsel kutusunda `width: calc(100% - 24px)` | Safari kartları Chrome'la aynı ölçü | Düşük |
| `02c875d` | K7: video, kart önden indirmesi bitince (en geç 4 sn) iner | Kartlar videodan önce tamamlanır | Hareketin başlama anı ötelenir |
| `7c8c46d` | K4: yedek yüz `<head>`'de satır içi, `document.fonts.load` ile CSS'ten önce | Firefox'ta da ilk kare doğru satır sayısı | +~1,8 KB ham HTML |
| `a1fb5b8` | `6dfbb35`'in geri alınması | Firefox videosu akıcı | — |
| `4dbe9ef` | `fonts.load` reddi yakalanır | Arial'sız sistemde konsol hatası yok | Gerçek Android'de sınanmadı |
| `a0fc589` | Çapalı açılışta devir beklemez | İlk kare hedef bölüm | Yok |
| `0dee665` | Hero sökülünce levha dinleyicisi bırakılır | Küçük sızıntı biter | Yok |
| `1353dc1` | K8: font ön yüklemeleri `<body>` başında | Chromium ilk boyamayı fontlar için bekletmez | Fontlar artık gömülü stilin ardında keşfediliyor (gerçek TCP'de bir gidiş-dönüş geç olabilir) |
| `c9944cf` | K9: giriş CSS'i HTML'e gömülü, modül betiği stilin ardında | Yavaş hatta FCP ~0,4–0,6 sn erken (üç motor) | index.html br 3,0 → 25,6 KB her yolda; Lighthouse benzetimli FCP biraz geç (§2); **JS'le çizilen yollarda gerileme yarattı → `44fefcc`** |
| `0304003` | K1: Firefox'ta tek geçişli WebGL tuvali | Firefox kaydırma CPU'su ~%75 düşer, video kaydırırken tam hız | **Yoğunluk/1x eşleme (`22fb97f`) ve yazılım birleştirme (`d853320`) sonradan düzeltildi** |
| `44fefcc` | K10: kabuksuz yollarda `modulepreload` stilden önce | /yontem ve panelde JS erken iner | Düşük; tek istek (çift indirme yok, ölçüldü) |
| `22fb97f` | K11: tampon = kesirli kutu × dpr, `matchMedia(resolution)`, GL hata/kayıp geri dönüşleri | Yoğunluk değişiminde ve 1x ekranda görünüm aynı | Düşük |
| `e1e6b3c` | Eskiyen yorumlar; işlev biçimli `String.replace` | Davranış değişmez | Yok |
| `d853320` | K12: ilk saniye kare sınaması (ortanca > 25 ms → CSS süzgecine dön, 7 gün hatırla) | Ekran kartsız Firefox'ta kilitlenme yok | Çok yavaş/yüklü makinede yanlışlıkla CSS süzgecine dönebilir (eski davranış) |
| `160a22a` | K13: vitrinde ilk kare web fontunu ≤100 ms bekler (Chromium, Firefox) | Hızlı hatta yedek→Inter Tight geçişi görünmez | Yavaş hatta FCP ~+100 ms (kazancın çoğu kalır); WebKit'te uygulanmaz (§8) |
| `5b39d12`, `bc8071c`, `77cc40c`, `c6149fb`, `8c0a308`, `8239b80`, `bb5b8b1` | Ölçüm verisi, araçlar, rapor | — | — |

**Commit düzeyinde bilinen kusurlar (düzeltilmedi, geçmiş yeniden yazılmadı):** `89e910f` iki font kök nedenini tek commit'te topluyor;
`0686656` mesajı «53/53» diyor, gerçek 52/52; `0686656`'daki K3 sayıları eski vekil verisinden; `13e9f12` «poster LCP sayılmıyor» diyor —
768/1920'de sayılıyor; `6dfbb35` «Chromium çıktısıyla ≤2/255» diyor — 1440@2'de en çok 11/255; `a1fb5b8` var olmayan bir dosyaya atıf
yapıyor (veri `analiz/ara-sonra2/`'de); `49d8f2b` 768/1920 LCP öğesine «video karesi» diyor — doğrusu `<video poster>`. 19.10:
`1353dc1` ve `c9944cf` «görünen hiçbir şey değişmez» diyor — son görünüm için doğru, ama hızlı hatta ilk karelerde yedek font
geçişi doğdu (`160a22a` giderdi); `c9944cf` yalnız «/»yi ölçmüştü, /yontem gerilemesini görmedi (`44fefcc`); `0304003` «Firefox'taki
görünüm aynı kalır» diyor — yalnız 2x/3x'te ölçülmüştü, 1366×768@1'de geçerli değildi ve yoğunluk değişimini ele almıyordu (`22fb97f`),
ekran kartsız birleştirmede sayfayı kilitliyordu (`d853320`); `160a22a` ve `analiz/ara-font/OKU.md` «WebKit'te LCP API'si yok, FCP'ye göre»
diyor — Playwright WebKit (Safari 26 motoru) LCP API'sini destekliyor; ölçüm betiği zaten onu kullanıyordu, yalnız açıklama yanlış.

## 5. Görsel regresyon

**Ekran görüntüleri** (`olc/ekran.mjs`): 3 motor × 4 görünüm × {`/` tam sayfa, `/` ilk ekran, `/yontem` tam sayfa, `/yontem` ilk ekran,
giriş ekranı} = 60 görüntü; hareket azaltma açık (video yerine poster, deterministik), tembel görseller kaydırılıp çözülür. Kıyas
`olc/piksel.mjs` (pixelmatch 7, eşik 0,1, kenar yumuşatma ayrı); «önce» = d6ab50a, «sonra» = 160a22a (`son/piksel.json`).
Gürültü tabanı: aynı «önce» derlemesi iki kez çekildiğinde 60 görüntünün 58'i aynı; WebKit 768/1920 «/» tam sayfada bir görsel bandı
çekimden çekime değişiyor (`analiz/gurultu/`).

| Kapsam | Sonuç |
|---|---|
| Chromium — 20 görüntü | **20/20 piksel piksel aynı** |
| Firefox — 20 görüntü | **20/20 piksel piksel aynı** |
| WebKit — `/yontem`, giriş, ilk ekranlar (16) | **16/16 piksel piksel aynı** |
| WebKit — `/` tam sayfa (4) | Bilinçli değişiklik (K6, kart görseli 19 px kısaldı): sayfa 20–231 px (aygıt pikseli) kısa. Bölüm bazında (`olc/piksel-bolum.mjs`, `son/piksel-bolum.json`): hero ve şerit **aynı** (%0,00); yalnız `#isler`'in boyu değişti; altındaki bölümlerde %0,00–1,83 fark yalnız yazı kenarlarında (bölüm kesirli piksel kadar yukarı kaydığı için yumuşatma pikselleri); «katmanlar»daki %0,48–0,89 gürültü tabanı bandı. |

Kart görseli değişikliği (WebKit, K6): kutu 326×280 → 326×261 (390), 298×258 → 298×238 (1440) — Chromium/Firefox ile birebir aynı ölçü.

**Firefox WebGL tuvali ↔ özgün CSS süzgeci** (video karesi 10,0 sn'de duraklatılmış; aynı sayfada tuval ↔ CSS süzgecine dönüş; ortalama
kanal farkı ÷255 ve kenar enerjisi; `analiz/webgl-son/son-esdeger.txt`, stok Firefox 158 pencereli; CSS'e dönüş yolu önceki derlemeyle
piksel piksel aynı):

| Görünüm | Ortalama fark | > 8/255 piksel | Kenar enerjisi tuval ↔ CSS |
|---|---:|---:|---|
| 1366×768 @1 | 5,40 | %17,3 | 19,02 ↔ 19,03 |
| 1440×900 @1 | 2,78 | %3,9 | 19,49 ↔ 19,52 |
| 1920×1080 @1 | 2,56 | %2,3 | 17,58 ↔ 17,58 |
| 1440×900 @2 | 2,81 | %4,1 | 21,93 ↔ 22,01 |
| 390×844 @3 | 3,49 | %8,9 | 17,01 ↔ 16,99 |

Keskinlik düzeyi birebir; kalan fark video ölçekleme süzgecinden (kimlik çekirdeği ↔ süzgeçsiz video 1440@2'de 1,9/255). 1366@1'de
ince panel deseninin alt-piksel yerleşimi farklı (görsel kırpımla incelendi; sahne, renk ve keskinlik aynı).

**Açılış sırasındaki geçici görünüm** (son görüntü değil; §2 tablosu, `son/font-ilk-metin.txt`): ilk görünür metin yedek yüzle mi
(önce → sonra): kısıtsız hatta üç motorda 0/3 → 0/3; 20 Mbps'te Chromium 0/3 → 0/3, Firefox 0/3 → 0/3, **WebKit 0/3 → 2/3** (§8.3);
yavaş 4G'de iki derlemede de ilk metin çoğunlukla yedek yüzle (font ~1,4 sn'de geliyor), sonra daha erken görünüyor. Yedek yüz metrik
eşlemeli: en büyük öğe kayması 0–2 px.

**Ekran görüntüsüyle doğrulanamayanlar:** oynayan videonun görünümü (görüntüler hareket azaltma kipinde poster üzerinden); tuvalin
oynarken görünümü yalnız duraklatılmış karede kıyaslandı.

## 6. Bağımsız doğrulama

**1. tur (18.10)** — taze ajanlarla 5 aşamalı iş akışı (`analiz/dogrulama-1.json`, sentez `analiz/dogrulama-1-sentez.md`): kod incelemesi,
43 sayının ham dosyadan yeniden hesabı, süreç denetimi, bağımsız yeniden ölçüm. Bulunanlar: «önce» replikasının sertifikası yenilenmiş,
Chromium kısıtlı hat satırları geçersiz SPKI ile ölçülmüştü (taslaktaki «iyileşme» bundan geliyordu; 48 satır yeniden ölçüldü), Android'de
`fonts.load` reddi (`4dbe9ef`), çapalı açılış ara karesi (`a0fc589`), dinleyici sızıntısı (`0dee665`), rapor sayı/atıf hataları.

**2. tur (19.10)** — 19.10 commit'lerine bağımsız kod incelemesi (yalnız okuma + `npm test`). Bulgular ve sonuç:
1. *Önemli:* gömülü stil JS'le çizilen yollarda FCP'yi geriletiyor → kendi ölçümümle doğrulandı (Chromium Slow 4G /yontem +100…+230 ms),
   `44fefcc` ile düzeltildi; şimdi önceki derlemeden de hızlı.
2. *Önemli:* tuval yoğunluk değişimini izlemiyor → doğrulandı; ilk düzeltme denemesi (`device-pixel-content-box`) 1x'te tuvali
   yumuşattı (Firefox fiziksel ekranı bildiriyor — sondayla gösterildi), son çözüm `22fb97f`.
3. *Küçük:* kurulum istisnası posterin erimesini engelleyebiliyor → `22fb97f`.
4. *Küçük:* ilk karede GL hatası denetlenmiyor; Windows/Linux/Android ölçülmedi → `getError` + geri dönüş `22fb97f`; platformlar §7.
5. *Küçük:* fontlar stilin ardında keşfediliyor, yedek font daha uzun görünüyor, yorumlar eskidi → ölçüldü: hızlı hatta yeni bir yedek
   font geçişi doğmuştu (`160a22a`); yorumlar `e1e6b3c`.
6. *Küçük:* testler bunları yakalamıyordu → `teslim.test.ts` ve `keskin.test.ts` genişletildi (70 test).

**Kendi son doğrulama zincirim** (`son/zincir.sh`: tam matris, Lighthouse, 60 görüntü, etkileşim, Firefox A/B, boşta video) e1e6b3c'de
ayrıca K12'yi buldu (`analiz/ara-son-e1e6b3c/etkilesim.jsonl`) → `d853320`. Rapordaki tüm «sonra» sayıları 160a22a için aynı zincirin
yeniden koşusundan (`son/`).

## 7. Test edilemeyenler ve 10 dakikalık elle kontrol listesi

**Bu ortamda test edilemedi (yapılamadı):**

| Hedef | Neden | Yerine ne ölçüldü |
|---|---|---|
| Gerçek Safari (macOS) | Otomasyon için Safari'de «Uzaktan Otomasyona İzin Ver» (güvenlik ayarı) gerekiyor; açılmadı | Playwright WebKit (aynı motor, farklı kabuk) |
| iOS Safari (gerçek cihaz) | Cihaz ve iOS Simülatörü yok | WebKit 390×844 @3, dokunmatik |
| Android Chrome, Firefox Android | Cihaz/öykünücü yok | Chromium 390×844 @3; Firefox masaüstü 390×844 @3 |
| Firefox'un WebGL yolu Windows (ANGLE/D3D11) ve Linux'ta | Makine yok | macOS stok Firefox 158 (donanım) + başsız Firefox (yazılım birleştirme; ilk saniye sınamasının devreye girdiği gösterildi) |
| Gerçek TCP yavaş başlangıcı | Ağ vekili gecikme + bant uyguluyor, yavaş başlangıç yok; sistem düzeyi şekillendirme (dnctl/pfctl) güvenlik ayarı gerektirir | Vekil + Lighthouse benzetimi (lantern yavaş başlangıcı modeller; gömülü CSS'te benzetimli FCP biraz geç, §2) |
| Brave, Edge | Kurulu değil | Chromium + stok Chrome 155 |
| Saha verisi (CrUX / PSI) | Anonim PSI kotası doldu; CrUX anahtarı yok | — |
| HTTP/3 (üretimde açık) | Replika h1/h2 | — |
| Firefox `privacy.resistFingerprinting` | Ayrı profil gerektirir, denenmedi | — |

**10 dakikalık elle kontrol listesi** (canlıya almadan önce bir önizleme kopyasında ya da hemen sonra):

1. **Firefox (Mac, Retina)** — `/` aç, video başlasın; hızlıca aşağı-yukarı kaydır: akıcı olmalı. Chrome'la yan yana hero
   keskinliğini kıyasla (Firefox'un keskinleştirmesi bilinçli olarak eskisi gibi Chrome'dan biraz sert, §8).
2. **Firefox** — DevTools konsolunda `document.querySelector('canvas.vt-hero__keskin')?.className` → video oynarken
   `vt-hero__keskin is-hazir` olmalı (WebGL yolu etkin). Pencereyi Retina'dan harici 1x ekrana sürükle: görüntü yumuşamamalı.
3. **Firefox, donanım hızlandırması kapalı** (Ayarlar → Genel → Performans → «Mümkün olduğunda donanım hızlandırmasını kullan» kapalı,
   yeniden başlat) — `/` aç: sayfa takılmamalı; 1–2 sn sonra yukarıdaki komut `vt-hero__keskin` döndürmeli (tuval kendini kapattı).
   Sonra ayarı geri aç ve `localStorage.removeItem('pvq_keskin_yazilim')`.
4. **Chrome DevTools → Network (bir kısıtlama ön ayarı seçili, önbellek kapalı)** — `/` aç: ayrı bir `index-*.css` isteği OLMAMALI
   (CSS HTML'de), metin HTML iner inmez görünmeli; `/yontem` aç: `index-*.js` isteği HTML'le birlikte en başta başlamalı ve bir kez inmeli.
5. **Chrome ve Firefox, hızlı bağlantı, önbellek boş** (gizli pencere) — `/` aç: başlık doğrudan Inter Tight ile görünmeli, harf biçimi
   değişen bir «göz kırpma» olmamalı.
6. **Safari (Mac)** — «Hangi iş için» kart görselleri Chrome'daki kadar yüksek olmalı. Hızlı bağlantıda ilk açılışta başlıkta çok
   kısa bir yedek font → Inter Tight geçişi görülebilir (bilinen, §8).
7. **iPhone Safari, 4G** — font gelince düğmeler zıplamamalı; menü açılmalı; video başlamalı.
8. **Yavaş hatta yenileme** (posteri 2 sn'den uzun indiren bir kısıtlama, ör. 1,6 Mbps) — ikinci açılışta `.mp4` isteği OLMAMALI;
   aynısı Firefox'ta.
9. **`/yontem` doğrudan aç** — ilk karede ana sayfa hero'su görünmemeli. Oturum açıkken `/` aç — vitrin görünmemeli, panel gelmeli.
10. **Chrome DevTools → Lighthouse (mobil + masaüstü)** — `/` ve `/yontem` ≥ 90; üç tarayıcıda konsol hatasız.

## 8. Kalan riskler

1. **HTML her yolda büyüdü:** index.html br 3,0 → 25,7 KB (gömülü CSS). Değişmediyse 304 ile yeniden doğrulanır; dağıtımdan sonraki ilk
   ziyarette her yolda iner (önce de CSS dosyası inerdi). Lighthouse lantern'ı daha büyük HTML'i bir gidiş-dönüş uzun sayıyor:
   benzetimli FCP biraz geç, TBT penceresi FCP öne geldiği için büyüdü (sayılar §2; skor ve eşikler karşılanıyor).
2. **Gerçek ağda kazanç vekildekinden küçük olabilir:** vekil TCP yavaş başlangıcını uygulamıyor; fontlar artık gömülü stilin ardında
   keşfedildiği için gerçek bir soğuk bağlantıda bir gidiş-dönüş geç istenebilir (yedek yüz biraz daha uzun görünür; kaydırmasız).
3. **WebKit (Safari, iOS) hızlı hatta kısa yedek font geçişi:** 20 Mbps'te 3 koşunun 2'sinde ilk metin yedek yüzle (~30–75 ms), önce 0/3.
   Font beklemesi WebKit'te uygulanmadı çünkü WebKit, ilk düzende gizli içerik görünce açılsa bile fontlar inene dek hiçbir şey
   çizmiyor (yavaş 4G FCP ~0,7 → ~1,8 sn).
4. **Yavaş hatta yedek yüz daha uzun görünür:** ilk metin yavaş 4G'de ~0,7–0,8 sn'de yedek yüzle çıkıyor, Inter Tight ~1,4 sn'de geliyor
   (önce ilk metin ~1,1–1,3 sn'de yine yedek yüzle çıkıyordu). Metrik eşleme sayesinde satırlar kaymıyor (0–2 px).
5. **Firefox'un WebGL yolu yalnız macOS'ta (donanım + başsız yazılım) ölçüldü.** Windows (ANGLE) ve Linux'ta sınanmadı; korumalar:
   `failIfMajorPerformanceCaveat`, ilk karede `getError`, bağlam kaybında söküm, ilk saniye kare sınaması (ortanca > 25 ms → CSS süzgeci,
   7 gün). Yüklü bir makinede sınama yanlışlıkla CSS süzgecine dönebilir — bu eski davranıştır.
6. **Firefox'ta video oynarken boşta +~0,2 çekirdek** (son zincir: CSS süzgeciyle 0,11–0,27 → tuvalle 0,31–0,40; süzgeçsiz video
   düzeyi); karşılığında kaydırmada ~%75 az işlemci ve oynatmanın ilk 5 sn'sinde CSS süzgeciyle 3,6, tuvalle 0,6–1,4 çekirdek
   (`analiz/webgl-son/`, `son/video-zaman.jsonl`).
7. **Firefox'ta keskinleştirme Chrome'dakinden sert kalıyor** (Gecko çekirdeği CSS pikselinde uyguluyor; tuval bunu bilinçli olarak
   koruyor — değiştirmek Firefox'ta görünür değişiklik ve poster↔video erimesinde keskinlik sıçraması olurdu). 1366×768@1'de tuval ile
   CSS süzgeci arasında ince panel deseninde ortalama 5,4/255 fark kalıyor (keskinlik aynı).
8. **Chromium 768 ve 1920 genişlikte LCP = 474 KB'lık poster:** Slow 4G'de poster tek başına ~2,3 sn sürüyor, ≤ 2,5 sn karşılanamaz
   (poster baytı sahip kuralıyla sabit). Başsız Chromium süzgeçli posteri yazılımla taradığı için matristeki bu hücreler ~0,6–0,9 sn
   şişkin (pencereli Chromium'da poster inişi + ~120 ms).
9. **Video hareketi daha geç başlar** (kart görselleri önden inene dek, en geç 4 sn); **React devri ilk boyama bildirimini bekler**;
   **web fontu hiç yüklenemeyen ziyaretçi** SF yerine ölçeklenmiş Arial görür; **video sıcak ziyarette yeniden iniyor** (değişmedi).
10. **Ölçüm ortamı:** replika h3 konuşmuyor, `/v1/*` canlı API'ye gidiyor, sunucu aynı makinede, matris başsız; canlıda Lighthouse ve
    stok tarayıcı kontrolü (§7) önerilir.

## 9. Production onayı

Bu dal `main`'e birleştirilmedi ve canlıya gönderilmedi. Karar sizin:

> **`perf/cross-browser` dalını (etkin düzeltmeler: 0686656 · fa0c598 · 89e910f · fdb8c6c · 13e9f12 · b6daa3e · 02c875d · 7c8c46d · 4dbe9ef · a0fc589 · 0dee665 · 1353dc1 · c9944cf · 0304003 · 44fefcc · 22fb97f · e1e6b3c · d853320 · 160a22a; 6dfbb35 a1fb5b8 ile geri alındı) — bilinçli görünür farklarla birlikte (Safari kart görseli 280 → 261 px; web fontu gelene dek yedek SF yerine ölçeklenmiş Arial; Safari'de hızlı hatta ilk açılışta kısa yedek font → Inter Tight geçişi; video hareketinin kartlar inene dek, en çok 4 sn ötelenmesi) ve bedellerle (her yolda +22,8 KB HTML; Firefox'ta video oynarken boşta +~0,2 çekirdek) — `main`'e birleştirip canlıya almayı onaylıyor musunuz? — EVET / HAYIR**
