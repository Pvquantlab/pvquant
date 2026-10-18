# PVQuant — Tarayıcılar arası performans ve görsel tutarlılık raporu

Dal: `perf/cross-browser` (main'e birleştirilmedi, canlıya gönderilmedi). Temel: `main` d6ab50a (v2.458).
Ölçüm tarihi: 18.10.2026. Ham veri ve betikler `perf/` altında; her sayı bir dosyaya izlenebilir.

## 1. Özet

1. **Lighthouse «/» mobil 75 → 99** (replika, 3 koşu: 47/75/85 → 99/99/99; canlıdaki önce-değer 85), masaüstü 93 → 100; «/yontem»
   99 / 100 korundu. Kök neden iki parçalıydı: React kabuğu ilk boyamadan önce devralıyordu ve 474 KB poster metin LCP'siyle aynı anda
   yüksek öncelikle iniyordu (`fdb8c6c`, `13e9f12`; ikisi birlikte gerekli — ayrı ayrı ölçüldü).
2. **Zıplamalar bitti:** mobilde hero düğmeleri font gelince 25 px zıplıyordu (üç motorda) → 0–2 px; `/yontem`'de ana sayfa hero'sunun
   bir kare görünmesi ve 36–56 px «kayma» → 0. Firefox için ek kök neden bulundu ve düzeltildi (yüklenmemiş `local()` yedeği atlıyor).
3. **Gereksiz indirme bitti:** yavaş hatta yenilemede Firefox/WebKit hero videosunu yine indiriyordu (12 sn'de 2,2–2,4 MB) → 0; Firefox
   gereksiz latin-ext fontları artık inmiyor. 20 Mbps'te aşağıdaki kart görselleri videoyla yarışmıyor: Firefox 1440'ta 5,18 → 1,76 sn,
   Firefox 390'da 4,39 → 1,69 sn (bedeli: video hareketi 0,4–0,9 sn geç başlıyor; poster aynı kare).
4. **Tasarım korundu:** Chromium ve Firefox'ta 40/40 ekran görüntüsü piksel piksel aynı; WebKit'te tek bilinçli değişiklik Safari'de 19 px
   uzun çıkan kart görsellerinin Chrome ölçüsüne inmesi (sayfa 20–77 px kısaldı). 432 yüklemede konsol hatası / başarısız istek 0.
5. **Çözülemeyenler (şeffaf):** Firefox'ta hero videosundaki SVG keskinleştirme filtresinin kaydırma maliyeti sürüyor (stok Firefox 158,
   1440@2: ~2,3 çekirdek, %6–7 kaçan kare). GPU'da çalışan, piksel olarak eşdeğer bir yapı denendi; ama videoyu takılttığı için
   (5 sn'de 18–53 düşen kare) geri alındı. 59 kabul ölçütünden 3'ü karşılanmadı (§2): Chromium 768 px'te yavaş 4G LCP (poster
   baytıyla fiziksel sınır) ve kısıtsız ağda Firefox/Chromium LCP oranı (Chromium çok hızlandı; mutlak fark ~80–120 ms).

## 2. Önce / sonra

Tüm tablolar betikle üretildi: [`after/KIYAS.md`](after/KIYAS.md) (kabul ölçütleri + matris), [`after/TABLOLAR.md`](after/TABLOLAR.md),
[`after/ab/AB-TABLOLAR.md`](after/ab/AB-TABLOLAR.md), [`analiz/yukleme-once-sonra.md`](analiz/yukleme-once-sonra.md). «Önce» = d6ab50a,
«sonra» = a1fb5b8; aynı replika düzeni, aynı ağ vekili, aynı betikler, 3 koşu medyanı.

**Lighthouse 12.8.2 (replika; Chromium)**

| Sayfa · tür | Perf önce → sonra (koşular) | LCP | TBT | CLS | Erişil. / En iyi uyg. / SEO |
|---|---|---:|---:|---:|---|
| `/` · mobil | **75 → 99** (47/75/85 → 99/99/99) | 7,51 → 1,88 sn | 124 → 52 ms | 0 → 0 | 100 / 100 / 91 → aynı |
| `/` · masaüstü | **93 → 100** | 1 764 → 405 ms | 0 → 0 | 0 → 0 | aynı |
| `/yontem` · mobil | 99 → 99 | 1,80 → 1,80 sn | 35 → 37 ms | 0 → 0 | aynı |
| `/yontem` · masaüstü | 100 → 100 | 404 → 407 ms | 0 → 0 | 0 → 0 | aynı |

Canlı (önce, aynı gün): `/` mobil 85 (71–85), masaüstü 100. `/yontem` mobil FCP 1,50 → 1,65 sn: önceki değer, ana sayfa kabuğunun
yanlış rota karesini sayıyordu (K5); şimdi /yontem'in kendi ilk boyaması ölçülüyor.

**LCP «/», soğuk, medyan (ms) — seçili hücreler** (tamamı `after/KIYAS.md`)

| | Chromium 390 | Chromium 1440 | Chromium 768 | Firefox 390 | Firefox 1440 | WebKit 390 | WebKit 1440 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Kısıtsız | 416 → 96 | 708 → 136 | 636 → 552 | 177 → 219 | 271 → 218 | 587 → 742 | 116 → 224 |
| Slow 4G | 1 516 → 1 208 | 2 224 → 1 588 | 4 624 → 4 256 | 1 299 → 1 231 | 1 287 → 1 030 | 1 807 → 1 804 | 2 567 → 2 729 |
| Fast 3G | 4 056 → 2 796 | 4 480 → 3 324 | 7 096 → 6 088 | 3 179 → 2 877 | 3 028 → 2 636 | 3 405 → 3 367 | 4 213 → 4 269 |

Gürültü düzeyi: aynı derlemenin farklı oturumlarda yavaş 4G FCP'si WebKit'te ~100 ms oynuyor (ör. son derleme WebKit 390 «/» FCP
1 339 ↔ 1 228 ms, `analiz/ara3/`); bu eşiğin altındaki WebKit farkları iyileşme ya da gerileme sayılmadı. WebKit kısıtsız LCP
artışı (116 → 224 ms vb.) ölçümsel: WebKit React'in koyduğu aynı görünümlü düğümü yeni LCP adayı sayıyor ve devir artık FCP
bildirimini bekliyor; ilk boyama anı değişmiyor (§8.7).

**Öğe kayması (px, kendi izleyicimiz, tüm motorlar)** — `/`: 390'da 25 → 0–2 (üç motor, üç ağ); `/yontem`: 36–56 → 0.
Chromium CLS her hücrede ≤ 0,028 → ≤ 0,01.

**Bant ve video (vekil bayt sayacı)** — `analiz/yukleme-once-sonra.md`

| | Önce | Sonra |
|---|---|---|
| Yavaş hatta yenileme (12 sn): Firefox / WebKit video baytı | 2,29–2,40 / 2,17–2,31 MB | 0,00 / 0,00–0,07 MB |
| 20 Mbps, 8 kart görselinin tamamlanması — Firefox 1440 / Firefox 390 / Chromium 390 / WebKit 390 | 5,18 / 4,39 / 3,40 / 3,47 sn | 1,76 / 1,69 / 1,77 / 2,08 sn |
| 20 Mbps, video «playing» — Firefox 1440 / Chromium 390 / WebKit 390 | 2,82 / 1,41 / 2,09 sn | 3,30 / 1,96 / 2,79 sn |
| Firefox latin-ext font inişi (soğuk /yontem, 36 yükleme; matrisin en büyük 10 kaynağından) | 600: 19/36, 500: 9/36 | 0/36, 0/36 |

**Etkileşim (başsız; menü açma ms)** — Firefox 1920: 539 → 360, 1440: 290 → 255; WebKit/Chromium değişmedi ya da iyileşti.
Başsız Chromium'un kare süreleri (p95 100–630 ms) yazılım GPU'sundan; pencereli stok Chrome'da p95 ≈ 18 ms (`analiz/ab`).

**Pahalı birleştirme envanteri (Firefox, «/», ilk ekran; `olc/envanter.mjs`, önce = sonra)** — `backdrop-filter` 3 öğe: üst hap 1180×64
(blur 24 px + saturate 160 %), hero paragraf kartı 560×207 (blur 20 + saturate 150 %), yapışkan «Bu sayfada» çubuğu 1440×141 (blur 12)
→ ilk ekranın %15'i (1440) / %32'si (390). `filter` 5 öğe: video ve poster `url(#vt-keskin)` (her biri tam ekran 1440×900) + 3 düğme
parıltısı `blur(12px)` → ilk ekran alanının %201'i (üst üste binen katmanlar). `mix-blend-mode: multiply` + `mask` 1 öğe (hero `::after`,
tam ekran; 390'da yok). Hiçbiri değiştirilmedi (tasarım). A/B ile maliyetin büyük kısmının video filtresinde olduğu gösterildi
(kaydırmada filtre kapalı 0,36 ↔ cam kapalı 1,18 ↔ ikisi açık 1,60 çekirdek).

**Firefox kaydırma (stok Firefox 158, pencereli, aynı oturumda dönüşümlü, oynatma başladıktan hemen sonra)** — 1440@2: p95 29,0 → 30,2 ms,
kaçan kare %6 → %7, CPU 2,32 → 2,44 çekirdek; 390@3: 63,6 → 65,0 ms, %9 → %10 (`analiz/ara4/`). **Değişmedi (açık madde).**
Boşta video: iki derlemede de 0 düşen kare.

**Kabul ölçütleri** — 59 ölçütten 56'sı karşılandı (`after/KIYAS.md`). Karşılanmayanlar:

| Ölçüt | Değer | Neden |
|---|---|---|
| LCP ≤ 2,5 sn, Slow 4G, Chromium 768×1024 «/» | 4 624 → 4 256 ms | LCP öğesi `<video poster>` (hero ekrandan kısa → Chromium posteri LCP sayıyor). 474 KB poster + ~160 KB kritik kaynak 1,6 Mbps'te ≈ 3,2 sn + gecikmeler: poster baytı ve hero ölçüsü sahip kuralıyla sabit olduğundan bu hücrede ≤ 2,5 sn fiziksel olarak mümkün değil. Telefon genişliğinde (390) 1 208 ms ✅; Lighthouse mobil 1,88 sn ✅. |
| Firefox/Chromium LCP ≤ 1,20 · `/` · kısıtsız · 390 | 0,43 → 2,28 (219 / 96 ms) | Chromium 416 → 96 ms'ye indi; Firefox 177 → 219 ms (mutlak fark 123 ms, kısıtsız yerel ağ). Kısıtlı ağların tamamında oran ≤ 1,20. |
| Firefox/Chromium LCP ≤ 1,20 · `/` · kısıtsız · 1440 | 0,38 → 1,60 (218 / 136 ms) | Aynı nedenle; Firefox 271 → 218 ms ile kendisi iyileşti. |

## 3. Kök nedenler ve kanıt

Ayrıntı: [`analiz/KOK-NEDENLER.md`](analiz/KOK-NEDENLER.md). Kısaca:

| # | Belirti | Kök neden | Kanıt (çalıştırılmış ölçüm) | Commit |
|---|---|---|---|---|
| K1 | Firefox'ta kaydırma takılıyor; hero Chrome'dan sert/grenli | `feConvolveMatrix` Firefox WebRender'da yok (CPU yolu) + Gecko çekirdeği CSS pikselinde uyguluyor | Stok Firefox 158, pencereli A/B: kaydırmada 1,60 → 0,36 çekirdek (filtresiz); kenar enerjisi FF 12,94 ↔ Chrome 9,43 | `6dfbb35` → **geri alındı** `a1fb5b8` (video kare düşürüyordu); AÇIK |
| K2 | Lighthouse mobil «/» 47–85, LCP savruluyor | React kabuğu ilk boyama bildiriminden önce devralıyor + poster LCP'den önce yüksek öncelikle iniyor | Ayrıştırma: önce 64/85/75 · yalnız devir 82–85 · yalnız poster 75–76 · ikisi 99/99/99 | `fdb8c6c`, `13e9f12` |
| K3 | Yavaş hatta yenilemede Firefox/WebKit video indiriyor | Önbellek testi yalnız Chromium biçimini tanıyor | Sıcak 3G: Firefox 2,3 MB, WebKit 2,2 MB (videosuz kontrol 0) | `0686656` |
| K4 | Mobilde düğmeler 25 px zıplıyor; Firefox fazladan font indiriyor | Yedek font (SF) Inter Tight'tan geniş; latin-ext aralığı çakışıyor | Kayma izleyicisi 25 px (üç motor); fontTools satır simülasyonu; Firefox /yontem latin-ext 17/36; Firefox yüklenmemiş `local()` yüzü atlıyor (FontFace «unloaded») | `89e910f`, `7c8c46d` |
| K5 | /yontem'de ana sayfa hero'su bir kare görünüyor | Kabuğu silen betik CSS'i bekliyor | /yontem başlığı Firefox 36–56 px «kayıyor» (19/36) | `fa0c598` |
| K6 | Safari'de kartlar 19 px uzun | WebKit `aspect-ratio`'yu kenar boşluksuz genişlikten hesaplıyor | Enjeksiyonla 4 görünümde WebKit = Chromium | `b6daa3e` |
| K7 | Kaydıran ziyaretçi kartları boş görüyor (Firefox'ta en çok) | Video ile kart görselleri aynı anda bant paylaşıyor | 20 Mbps: Firefox 1440 kartlar 5,18 ↔ 1,71 sn (videosuz) | `02c875d` |

## 4. Commit bazlı değişiklikler

| Commit | Değişiklik | Beklenen etki | Risk |
|---|---|---|---|
| `49d8f2b` | Temel ölçüm + düzenek | — | — |
| `0686656` | K1 yavaş-hat kararını yalnız ağdan aktarılmış poster ölçümü yazar; önbellek biçimleri okur; kart önden indirmesi kararı okur | Yavaş hatta yenilemede Firefox/WebKit video indirmez | Düşük; bayt alanı olmayan eski Safari'de yalnız «yavaş» yazılır |
| `fa0c598` | `<head>`'de satır içi karar + tek CSS kuralı: kabuksuz yollarda kabuk ilk karede gizli | /yontem'de yanlış hero karesi ve sahte kayma biter | Düşük; karar ifadesi gövde betiğiyle aynı (11 durum testli) |
| `89e910f` | Metrik eşlemeli `local()` yedek yüz + latin-ext aralık daraltması | FOUT'ta satır sayısı korunur (zıplama yok); Firefox'ta ~38–76 KB az font | Web fontu HİÇ yüklenemeyen ziyaretçi SF yerine ölçeklenmiş Arial görür |
| `6dfbb35` | Firefox ≥132'de aynı çekirdek WebRender ilkelleriyle, 1 aygıt pikseli | Firefox kaydırma CPU'su ~%80 düşer; görünüm Chrome referansına yaklaşır | **Geri alındı** (`a1fb5b8`): boşta video 5 sn'de 18–53 kare düşürdü |
| `fdb8c6c` | React devri FCP bildiriminden sonra (1 sn emniyet) | Gözlenen LCP kabuğun ilk boyamasına sabitlenir | Sıcak açılışta hero altı içerik React gelene dek (ilk görünüm dışında) boş |
| `13e9f12` | Poster ön yüklemesi FCP bildiriminden sonra | Lighthouse mobil 99; metin LCP'si posterle yarışmaz | Poster birkaç on ms geç başlar (zemin gradyanı o kadar uzun görünür) |
| `b6daa3e` | Kart görsel kutusunda `width: calc(100% - 24px)` | Safari kartları Chrome'la aynı ölçü | Düşük; Chromium/Firefox ölçüleri birebir aynı kaldı |
| `02c875d` | Video, kart önden indirmesi bitince (en geç 4 sn) iner | Kartlar videodan önce tamamlanır | Hareketin başlama anı ötelenir (ölçüm §2) |
| `bc8071c` | Faz 2 analiz, A/B verisi ve araçlar | — | — |
| `7c8c46d` | Yedek yüz `<head>`'de satır içi, `document.fonts.load` ile CSS'ten önce hazır (tek kaynak) | Firefox'ta da ilk kare doğru satır sayısı (390: 25 → 1 px) | +~1,8 KB ham index.html (her rota) |
| `a1fb5b8` | `6dfbb35`'in geri alınması | Firefox hero videosu eskisi gibi akıcı (0 düşen kare) | Firefox kaydırma maliyeti açık kalır (§8) |

## 5. Görsel regresyon

Yöntem: `olc/ekran.mjs` — 3 motor × 4 görünüm × {`/` tam sayfa, `/` ilk ekran, `/yontem` tam sayfa, `/yontem` ilk ekran, giriş
ekranı} = 60 görüntü; hareket azaltma açık (video yerine poster, deterministik), tembel görseller kaydırılıp çözülür.
Kıyas `olc/piksel.mjs` (pixelmatch 7, eşik 0,1, kenar yumuşatma ayrı). **Gürültü tabanı**: aynı «önce» derlemesi iki kez çekildi
(`analiz/gurultu/`) → 60 görüntünün 58'i piksel piksel aynı; yalnız WebKit 768 ve 1920 «/» tam sayfada bir görsel bandı
çekimden çekime değişiyor (WebKit tam sayfa görüntüsünde tembel görsel bazen boyanmadan yakalanıyor — aynı «sonra» derlemesinin iki
çekiminde 390'da da gözlendi; görsellerin hepsinin yüklenip tamamlandığı ayrıca doğrulandı).

| Kapsam | Sonuç |
|---|---|
| Chromium — 20 görüntü | **20/20 piksel piksel aynı** |
| Firefox — 20 görüntü | **20/20 piksel piksel aynı** |
| WebKit — `/yontem`, giriş, ilk ekranlar (16) | **16/16 piksel piksel aynı** |
| WebKit — `/` tam sayfa (4) | Bilinçli değişiklik (K6): sayfa 20–77 CSS px kısaldı. Bölüm bazında (`olc/piksel-bolum.mjs`, `after/piksel-bolum.json`): hero, şerit **aynı**; yalnız `#isler` boyu değişti (390: 2897 → 2820 px); altındaki bölümlerde %0,01–1,8 fark yalnız yazı kenarlarında — bölüm kesirli piksel kadar yukarı kaydığı için yumuşatma pikselleri (altbilgi kırpımıyla gözle doğrulandı); «katmanlar»daki büyük bant gürültü tabanı. |

Kart görseli değişikliği (WebKit, K6): kutu 326×280 → 326×261 (390), 298×258 → 298×238 (1440) — Chromium/Firefox ile birebir aynı ölçü.

**Ekran görüntüsüyle doğrulanamayanlar:** video oynarken görünüm (görüntüler hareket azaltma kipinde poster üzerinden alındı);
Firefox'un oynayan videoyu ekranda süzüp süzmediği (ekran kaydı izni yok, §8.2).

## 6. Bağımsız doğrulama

⟨doğrulama iş akışı bekleniyor⟩

## 7. Test edilemeyenler ve 10 dakikalık elle kontrol listesi

**Bu ortamda test edilemedi (yapılamadı):**

| Hedef | Neden | Yerine ne ölçüldü |
|---|---|---|
| Gerçek Safari (macOS) | Otomasyon için Safari'de «Uzaktan Otomasyona İzin Ver» (güvenlik ayarı) açılması gerekiyor; açılmadı | Playwright WebKit 27.2 (aynı motor, farklı kabuk) |
| iOS Safari (gerçek cihaz) | Cihaz yok; bu makinede iOS Simülatörü de kurulu değil (`xcrun simctl` boş) | WebKit 390×844 @3, dokunmatik, isMobile |
| Android Chrome | Cihaz/öykünücü yok | Chromium 390×844 @3, isMobile |
| Brave, Edge | Kurulu değil (ikisi de Chromium tabanlı) | Chromium + stok Chrome 155 |
| Saha verisi (CrUX / PSI) | Anonim PSI kotası iki ayrı günde 429; CrUX API anahtarı yok | — |
| Vercel önizleme / Speed Insights | Site Vercel'de değil (VPS + Caddy) | Üretimle bayt bayt aynı yerel replika |
| HTTP/3 (üretimde açık) | Replika h1/h2 konuşuyor | — |
| Gerçek GPU'da Firefox/Chrome ölçümleri | Matris başsız koşar | Boya A/B'si pencereli stok Firefox 158 ve stok Chrome ile |

**10 dakikalık elle kontrol listesi** (canlıya almadan önce bir önizleme kopyasında ya da hemen sonra):

1. **Firefox (Mac, Retina)** — `/` aç, video başlasın; Chrome'da da aç ve hero'yu yan yana kıyasla: (a) poster anında ve (b) video
   oynarken keskinlik farkı var mı? (Firefox posteri daha sert gösterir — bilinen, açık madde; oynarken farkı not edin.)
   Hızlıca aşağı-yukarı kaydırın: hafif takılma bilinen açık madde (§8.1).
2. **Firefox** — video oynarken sayfayı 3 kez yenile: sekme simgesi dönmeyi bırakmalı, video başlamalı (Playwright'ın Firefox
   derlemesinde görülen takılma stok Firefox'ta yeniden üretilemedi).
3. **Safari (Mac)** — «Hangi iş için» kartlarındaki görseller Chrome'daki kadar yüksek olmalı (önce 19 px uzundu).
4. **iPhone Safari, 4G** — `/` ilk açılışta hero metni ve düğmeler font gelince zıplamamalı; menü açılmalı; video başlamalı.
5. **Android Chrome** — aynı kontrol (4).
6. **Chrome DevTools → Network «Slow 4G»** — `/` aç, sonra yenile: ikinci açılışta `.mp4` isteği OLMAMALI (yavaş hat kararı).
   Aynısını Firefox'ta (ağ kısıtlama ile) dene: mp4 olmamalı.
7. **Firefox Network paneli** — `/` ve `/yontem`'de `inter-tight-latin-ext-*.woff2` inmemeli.
8. **`/yontem` doğrudan aç** — ilk karede ana sayfa hero'su görünmemeli. Oturum açıkken `/` aç — vitrin görünmemeli.
9. **Chrome DevTools → Lighthouse (mobil + masaüstü)** — `/` ve `/yontem` ≥ 90 olmalı.
10. **Konsol** — üç tarayıcıda `/`, `/yontem`, giriş ekranı: hata olmamalı.

## 8. Kalan riskler

1. **Firefox kaydırma maliyeti ÇÖZÜLMEDİ.** Hero videosundaki `feConvolveMatrix` Firefox'ta CPU yolunda (WebRender'da yok):
   1440@2 kaydırırken 1,60 çekirdek, %7 kaçan kare; keskinleştirme Chrome'dakinin iki katı ölçekte. GPU'ya taşıyan eşdeğer
   denendi ve görsel olarak eşdeğerdi, ama videoyu takılttığı için geri alındı (`a1fb5b8`). Kalan seçenek: tek geçişli WebGL
   süzgeci (sahip kararı; orta-yüksek iş ve renk yolu riski).
2. **Firefox'un oynayan videoyu ekranda gerçekten süzüp süzmediği doğrulanamadı**: bu makinede ekran kaydı izni yok; tarayıcı
   ekran görüntüleri kendi yeniden çizimiyle alınıyor. Özgün yolun boşta yalnız ~0,1 çekirdek harcaması, oynayan videonun ekranda
   süzülmüyor olabileceğini düşündürüyor (Firefox'ta hareket hâlinde Chrome'dan yumuşak görünebilir). Elle kontrol listesinde (§7).
3. **Video hareketi daha geç başlar** — kart görselleri önden inene dek (en geç 4 sn). Poster aynı kare olduğu için sıçrama yok.
4. **React devri ilk boyama bildirimini bekler** — sıcak açılışta ilk ekranın altındaki bölümler birkaç yüz ms React'i bekler
   (ilk ekran kabuktan gelir). Çapalı derin bağlantıda (`/#karne`) kaydırma o kadar geç olur.
5. **Web fontu hiç yüklenemeyen ziyaretçi** (Lockdown Mode, kurumsal vekil) artık SF yerine ölçeklenmiş Arial görür.
6. **768 ve 1920 genişlikte LCP = poster** (hero ekrandan kısa olduğu için Chromium posteri LCP sayıyor). Yavaş 4G'de 474 KB poster
   fizik olarak ~3,5 sn'den önce gelemez; poster baytı ve hero ölçüsü sahip kuralıyla sabit → bu hücrelerde LCP ≤ 2,5 sn karşılanamaz.
7. **WebKit'in LCP API'si** React'in kabuk paragrafının yerine koyduğu aynı görünümlü düğümü yeni aday sayıyor; devir artık FCP
   bildirimini beklediği için kısıtsız ağda WebKit LCP kaydı 0,1–0,35 sn geç düşüyor (ekranda görünen an değişmiyor).
8. **Video sıcak ziyarette yeniden iniyor** (üç motorda da büyük medya kısmen önbelleğe alınıyor) — değiştirilmedi.
9. **Ölçüm ortamı**: replika h3 konuşmuyor, `/v1/*` canlı API'ye gidiyor, sunucu aynı makinede; matris başsız. Canlıda Lighthouse
   ve stok tarayıcı kontrolü (§7) önerilir.

## 9. Production onayı

Bu dal `main`'e birleştirilmedi ve canlıya gönderilmedi. Karar sizin:

> **`perf/cross-browser` dalını (etkin düzeltmeler: 0686656 · fa0c598 · 89e910f · fdb8c6c · 13e9f12 · b6daa3e · 02c875d · 7c8c46d; 6dfbb35 a1fb5b8 ile geri alındı) `main`'e birleştirip canlıya almayı onaylıyor musunuz? — EVET / HAYIR**
