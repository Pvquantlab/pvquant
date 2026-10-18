# Faz 2 — Kök neden analizi (belirti → kök neden → kanıt)

Kaynaklar: temel ölçüm (`perf/baseline/`), salt okuma kod incelemesi (6 alan × analist + şüpheci,
`kok-neden-ham.json`), düzeltme tasarımı + çekişmeli eleştiri (`duzeltme-tasarimi.json`), A/B deneyleri
(`ab/AB-TABLOLAR.md`, `filtre*/esdeger-*.json`), Firefox kaynak kodu (mozilla-central / release / ESR
`StaticPrefList.yaml`). Her maddede «doğrulandı» yalnız ÇALIŞTIRILMIŞ bir ölçüme dayanır.

Durum etiketleri: **DOĞRULANDI** (ölçümle) · **DÜZELTİLDİ** (commit) · **ÇÜRÜTÜLDÜ** · **AÇIK** (ölçüldü, düzeltilmedi; gerekçe yazılı).

---

## K1 — Firefox'ta kaydırma takılıyor; hero fotoğrafı Chrome'dakinden «sert/grenli» görünüyor
- **Belirti.** Başsız matris: Firefox 1440 kaydırma kare p95 216 ms (%32 kare >33 ms), 1920'de 376 ms; WebKit 18 ms.
  Pencereli stok Firefox 158 (gerçek GPU), 1440@2: kaydırırken tarayıcı süreç ağacı **1,60 çekirdek**, %7 kaçan kare.
- **Kök neden.** Video ve poster `filter: url(#vt-keskin)` (tek primitif `feConvolveMatrix`) taşıyor. Firefox bu primitifi
  WebRender'da çalıştırmıyor: `gfx.webrender.svg-filter-effects.feconvolvematrix = false` (mozilla-central, release 158.0.1,
  ESR 140) → öğe CPU (blob) yoluna düşüyor, kaydırmada her karede yeniden süzülüyor. Ek olarak Gecko çekirdeği **CSS pikseli**
  ölçeğinde uyguluyor (Chromium aygıt pikselinde): Retina'da iki kat kaba, belirgin fazla keskin.
- **Kanıt.** A/B (`ab/AB-TABLOLAR.md`, stok Firefox, pencereli, 3 koşu medyan, kaydırma): mevcut 1,60 çekirdek / %7 kaçan;
  filtresiz 0,36 / %3; camsız (filtre açık) 1,18 / %6 → maliyetin büyük kısmı filtre, cam ikincil. Chrome'da filtre/cam
  değişkenleri arasında fark yok (0,32–0,39 çekirdek). Ölçek: kenar enerjisi (komşu aygıt pikseli farkı, 1440@2 poster)
  Chrome 9,43 · Firefox 12,94 · filtresiz 5,47; ayrışık d=1/dpr Firefox'ta 9,45.
- **Denenen düzeltme (geri alındı).** `6dfbb35` — Gecko ≥ 132'de aynı çekirdek `feOffset`×4 + aritmetik `feComposite`×4
  (WebRender'da GPU), ofset 1 aygıt pikseli. Piksel eşdeğerliği sağlandı (d=1 CSS px → Firefox özgün çıktısıyla ≤ 2/255; d=1/dpr →
  Chromium özgün çıktısıyla ≤ 2/255) ve kaydırma CPU'su 1,60 → 0,32–0,49 çekirdeğe indi. **Ama** son derlemenin pencereli stok
  Firefox ölçümünde hero videosu 30 sn boyunca her 5 sn'de 18–53 / ~105 kare düşürdü (özgün filtre ve filtresiz: 0;
  `ara-sonra2/video-zaman-7c8c46d.jsonl`). A/B'deki 0–8 düşen kare, değişkenin oynatmadan 40–60 sn sonra ölçülmesindendi.
  Görünür animasyon bozulması olduğu için `a1fb5b8` ile geri alındı.
- **Durum: AÇIK.** Firefox'ta kaydırma maliyeti (1440@2: 1,60 çekirdek, %7 kaçan kare) ve CSS pikseli ölçeğindeki keskinleştirme
  sürüyor. Tasarımı koruyan seçenekler (sahip kararı): (a) videoyu tek geçişli WebGL gölgelendiricisiyle süzmek (yalnız yeni video
  karesinde çizim; renk yolu ve bağlam kaybı riski, orta-yüksek iş); (b) bugünkü hâliyle kabul.

## K2 — Lighthouse mobil «/» 47–85 (≥90 kriteri), LCP 4,2–10,5 sn arası savruluyor
- **Belirti.** Replika 75 (47–85), canlı 85 (71–85); LCP öğesi hero paragrafı, gecikmenin tamamı «render delay».
- **Kök neden (iki parça, ikisi de gerekli).** (a) `createRoot` kabuğu hydrate etmeden silip yeniden kuruyor; devir ilk boyama
  bildiriminden önce gelince gözlenen LCP React'in tam sayfa karesine kayıyor (koşudan koşuya başka an). (b) 474 KB poster,
  CSS iner inmez **yüksek öncelikle** başlıyor; Lighthouse benzetimi LCP'den önce başlayan yüksek öncelikli görseli LCP yoluna
  katıyor (Slow 4G'de ≈ +2,4 sn). Gerçek kullanıcıda (b) ilk boyama aralığında metinle bant paylaşımıdır.
- **Kanıt (ayrıştırma, `ara/lighthouse`, 3'er koşu).** Önce: 64/85/75 (LCP 10,5/4,2/7,5 sn). Yalnız (a): 82/84/85 (LCP 4,1–4,2;
  gözlenen FCP = LCP = 251 ms). Yalnız (b): 76/75/75 (LCP 7,4–9,2). (a)+(b): **99/99/99**, LCP 1,73 sn, TBT ~50 ms.
- **Düzeltme.** `fdb8c6c` (devir FCP bildiriminden sonra; 1 sn emniyet), `13e9f12` (poster ön yüklemesi FCP bildiriminden sonra).

## K3 — Yavaş hatta yenilemede Firefox/WebKit videoyu yine indiriyor (K1 kuralı motor bağımlı)
- **Kök neden.** `posterYavasMi()` önbellekten gelişi yalnız Chromium biçimiyle tanıyordu (`transferSize === 0 && decodedBodySize > 0`).
  Firefox bellek önbelleğinde poster için Resource Timing girdisi yazmıyor → kapı açılıyor; WebKit 0/0/0 girdi yazıp süreyi ~0
  ölçüyor ve 7 günlük «yavaş» kaydını `{y:false}` ile eziyor.
- **Kanıt.** `baseline/matris.jsonl`, kısıtlı hat, sıcak «/»: Firefox 18/18 satırda poster girdisi yok; WebKit 23/23 satırda poster
  0 B ve 21/23'te mp4 isteği; Chromium 24/24'te mp4 yok. Bayt etkisi: `ab/AB-TABLOLAR.md` (vekil sayacı, sıcak yükleme).
- **Düzeltme.** `0686656` — kararı yalnız gövdesi aktarılmış ölçüm yazar; önbellek biçimleri okur. 5 biçim + 7 gün kuralı testte.

## K4 — Mobilde hero düğmeleri 25 px zıplıyor (FOUT); Firefox gereksiz latin-ext fontu indiriyor
- **Kök neden.** Yedek yüz system-ui (macOS'ta SF) Inter Tight'tan geniş: 390 px'te paragraf 9 ↔ 8 satır → 16 × 1,55 = 24,8 px.
  Fontsource latin-ext `unicode-range`'i Türkçe alt kümenin ve latin'in çizdiği ğ Ğ İ ı ş Ş ₺'yi de kapsıyor; Firefox o yüzü de başlatıyor.
- **Kanıt.** Kayma izleyicisi: 390'da `.vt-hero__eylem` 25 px (soğuk, kısıtlı hat, üç motor). fontTools ile metrikler ve satır
  simülasyonu (320–767 px: SF ile 172/448, yedekle 436/448 genişlikte Inter Tight'la aynı satır). Firefox soğuk /yontem
  latin-ext-600 17/36, -500 9/36 koşu.
- **Düzeltme.** `89e910f` — metrik eşlemeli `local()` yedek yüz + latin-ext aralık daraltması. Son görüntü değişmez.
  Ara «sonra» ölçümü (`ara-sonra1/`): Chromium ve WebKit 25 → 0–2 px, **Firefox 25 px kaldı**. Neden: Firefox ilk aile yüklenirken
  listedeki henüz yüklenmemiş `local()` yüzü atlayıp sistem fontuna düşüyor (yedek yüzlerin FontFace durumu baştan sona
  «unloaded»; ölçüldü). `7c8c46d` — yedek yüz `<head>`'de satır içi ve `document.fonts.load` ile CSS'ten önce hazır: Firefox
  ilk karede 563 → 539 (son 538), Chromium/WebKit 538 (değişmez).

## K5 — /yontem'de ana sayfa hero'su bir kare görünüyor (yanlış rota karesi)
- **Kök neden.** Kabuk her yolun HTML'inde; silme kararı gövde sonundaki betikte ve o betik CSS'i bekliyor → motor betikten önce
  bir kare üretebiliyor. **Kanıt.** /yontem başlığı Firefox'ta 36–56 px «kayıyor» (19/36 koşu), Chromium 36 px (5/36).
- **Düzeltme.** `fa0c598` — `<head>` başında aynı karar + `html.vt-kabuksuz #root>[data-kabuk]{display:none}`.

## K6 — Safari'de «Hangi iş için» kartları 19 px uzun (sayfa 79 px uzun)
- **Kök neden.** Gerilen esnek öğede (`width:auto` + `margin:12px` + `aspect-ratio:10/8`) WebKit oranı kenar boşlukları
  düşülmemiş genişlikten hesaplıyor (350/1,25 = 280 ↔ 326/1,25 = 261).
- **Kanıt.** `olc/bolum-boy.mjs`: yalnız #isler farklı; enjeksiyonla 4 görünümde WebKit Chromium'la birebir, Chromium/Firefox değişmedi.
- **Düzeltme.** `b6daa3e` — `width: calc(100% - 24px)` (aynı etkin genişlik).

---

## K7 — Video, aşağıdaki kart görselleriyle bant yarıştırıyor (Firefox'ta en çok)
- **Belirti.** 20 Mbps / 40 ms hatta («kablo20») soğuk «/»: 8 Storyset kartının tamamlanma anı Firefox 1440'ta 5,18 sn
  (videosuz kontrol 1,71), Firefox 390 4,39 (1,65), Chromium 390 3,40 (1,82), WebKit 390 3,47 (2,06); Chromium/WebKit 1440 +0,1–0,2 sn.
- **Kök neden.** Video indirmesi `load`'da, kartların önden indirmesi de `load` + poster sonrasında başlıyor; sunucu (Go h2)
  akışları sırayla besliyor. Kısıtlı hatlarda (1,6 Mbps) etki yok çünkü K1 kuralı videoyu zaten kapatıyor (A/B'de mevcut = videosuz).
- **Kanıt.** `ab/AB-TABLOLAR.md` (vekil bayt sayacı + Resource Timing; «videosuz» = aynı derleme, kenar `*.mp4 → 404`).
- **Düzeltme.** `02c875d` — video, kart kuyruğu bitince ya da en geç 4 sn'de iner. Bedel: hareketin başlama anı ötelenir
  (ölçüm REPORT.md'de).

## Ölçülen ama düzeltilmeyenler (AÇIK) — gerekçeleriyle

- **Playwright Firefox'ta (157) aynı adrese yeniden gezinmede `load` olayı gelmiyor** (~%8; etkileşim ölçümünde 2/36 koşu,
  boya ölçümünde 1). Teşhis (`olc/load-takilma2.mjs`): takılma anında fontlar yüklü, bitmemiş kaynak yok, poster tamam;
  `<video>`'ya `<source>` eklenmesi engellenince 40 denemede 0 (poster engellenince sürüyor) → video kaynak seçimiyle ilgili bir
  yarış. **Stok Firefox 158'de yeniden üretilemedi** (başsız 40 + pencereli 25 deneme, video inerken 0–1,5 sn içinde yenileme:
  0 takılma). Kanıt yalnız düzenek derlemesini gösterdiği için kodda değişiklik YAPILMADI; matris her yüklemeden önce
  `about:blank`'e gittiği için etkilenmedi (432 yüklemede 0).
- **Videonun tamamı açılıştan hemen sonra iniyor** (1440: ~35 MB / 20 sn, 20 Mbps'te üç motorda da). Medya dosyası bayt bayt
  aynı kalmak zorunda (sahip kuralı); kesmek/yeniden kodlamak yasak. İstemci tarafı MSE ile parçalı oynatma ayrı ve büyük bir iş.
  Sıralama (K7) bandı kartlara önce verir; toplam bayt değişmez.
- **Sıcak ziyaretlerde video yeniden iniyor** (20 Mbps, 12 sn'de: Chromium 1440 3,6–9,6 MB, Firefox 13,6 MB, WebKit 25,8 MB).
  Tarayıcıların büyük medya için kısmi/aralıklı önbellek davranışı; sunucu başlıkları doğru (immutable, 1 yıl). Düzeltmesi
  (Service Worker ile aralık önbelleği) kapsam dışı ve riskli; raporda «kalan risk».
- **Chromium 768 ve 1920'de LCP öğesi videonun ilk karesi** (yavaş 4G'de 4,2–4,9 sn). Düzeltmelerden sonra yeniden ölçülecek
  (devir ve poster değişiklikleri LCP adaylarını etkiler); sonuç REPORT.md'de.

## Ölçüm yöntemi notları (sonuçların yorumu için)

- **Vekil sürümü.** Temel matrisin kısıtlı-hat satırları ilk olarak sıra bozan eski vekille ölçülmüştü; adil kıyas için 144 satır güncel
  vekille yeniden ölçüldü (eski satırlar `baseline/matris-eski-vekil.jsonl`). Aynı «önce» derlemesi eski vekille Firefox 390 yavaş 4G'de
  FCP 1,01–1,08 sn, güncel vekille 1,18–1,32 sn verdi (`olc/kritik-yol.mjs`) — vekil farkı tek başına ~150 ms oynatıyordu.
- **Oturumlar arası gürültü.** Aynı derleme farklı oturumlarda yavaş 4G FCP'de WebKit'te ~100 ms oynuyor (son derleme WebKit 390 «/»:
  1 339 ↔ 1 228 ms, `ara3/`). Bu eşiğin altındaki farklar iyileşme/gerileme sayılmadı. Satır içi yedek fontun WebKit'i geciktirdiği
  şüphesi bu yüzden çürütüldü (Gecko'ya özel değişken WebKit'te daha hızlı değildi; ayrıca `MozAppearance` algısı Firefox 157'de
  çalışmadı → değişken reddedildi).
- **Ölçüm konumu.** Firefox kaydırma maliyeti oynatma başlangıcına yakınken daha yüksek (1440@2: ~2,3–2,8 çekirdek; 40–60 sn sonra
  ~1,3–1,6). Önce/sonra kıyası bu yüzden aynı oturumda dönüşümlü ve aynı konumda yapıldı (`ara4/`): fark yok.

## Çürütülenler (ölçüm ya da kodla)

- Başsız Chromium'daki kare süreleri (boşta p95 117–650 ms) gerçek GPU'da yok: pencereli stok Chrome'da tüm değişkenlerde
  boşta p95 ≈ 18 ms, CPU 0,2–0,4 çekirdek → başsız kabuğun yazılım GPU'su (düzenek yapaylığı).
- Cam bulanıklığı (backdrop-filter) Firefox takılmasının birincil kaynağı DEĞİL: filtre açıkken camı kapatmak 1,60 → 1,18 çekirdek;
  filtreyi kapatmak 1,60 → 0,36. Cam kaldırılmadı (tasarım), gerek de yok.
- `will-change: transform` ile filtreli öğeyi ayrı katmana almak Firefox kaydırmasını düzeltmiyor (duman testi: 41 kare/sn, 1,9 çekirdek).
- Laboratuvarda Firefox'un ilk görüntüsü Chromium'dan YAVAŞ DEĞİL: «/» LCP oranı Firefox/Chromium 0,23–0,98.
- Kod incelemesinde çürütülenler (`kok-neden-ham.json`): ECharts'ın vitrine inmesi; bulut JPG'lerinin posterle yarışması (CSS ölü);
  Caddy'nin medyayı yeniden sıkıştırması, Range/206 sorunu, yanlış Cache-Control; 103 Early Hints kazancı; data-URI SVG
  zeminin ilk boyamayı geciktirmesi; `transform: scaleX(-1)` maliyeti; /v1/dogrulama isteğinin LCP ile yarışması; StrictMode/
  useCanlandir kaynaklı uzun görevler; kabuktan React'e devirde boş kare.
