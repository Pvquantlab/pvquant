# Emsaller dizini — «yeni kalıp icat etmeden önce buraya bak»

Her satır: kalıp → dosya → kritik kural. Yeni mühürde yeni kalıp çıkarsa buraya satır eklenir.

## Vitrin

| Kalıp | Dosya | Kritik kural |
|---|---|---|
| Panel kesiti (kart yerine tek-yüzey hücreler) | `vitrin/TurkiyePiyasasi.tsx` + `.vt-kesit` | 1 px gap=çizgi; hücreler eylemsiz (R21); etiket durum noktası; künye tabana yaslı |
| Kart veri diyagramları (anlam taşıyan mini-SVG) | `vitrin/KartCizimleri.tsx` | amber YALNIZ sapma+alarm (test pini); kılavuz+eksen tiki dili; sembol ikon yasak |
| Hero eylem sütunu + TL bağı | `vitrin/Hero.tsx` | dar ekranda çift-DOM tek görünür; mikro metin düğme altında |
| Canlı gök + crosshair'li referans eğrisi | `vitrin/ReferansEgri.tsx`, `gunesSaati.ts` | NOAA hesabı TRT gün sırası düzeltmeli; crosshair getComputedTextLength kıstırma; touch kalıcı |
| Disiplin bandı + dürüst dipnot | `vitrin/DisiplinBandi.tsx` | «iki test takımının toplamı, aşağı yuvarlanmış» — otomasyon İDDİA EDİLMEZ; sup aria-hidden + .vt-srgizli |
| Bölüm çubuğu (şerit-içi scroll) | `vitrin/BolumCubugu.tsx` + `bolumler.ts` | sayfa zıplatmaz (yalnız şerit scrollLeft, scroll-margin:0); IO küme + belge sırası sonuncu |
| Dört adım zinciri + ayna tablosu | `vitrin/DortAdim.tsx` | ok'lar GRID HÜCRESİ (::after kart overflow'una kırpılır!); ayna role=table, ✓ alt-metinsiz |
| İş ızgarası (4 masa, fayda kalıbı) | `vitrin/IsIzgarasi.tsx` | rakamlı vaat/müşteri iması yasak (test); künye dl/dt/dd |
| Scroll-reveal (R25) | `.vt [data-canlan]` + Ö10 dersi | gizleme YALNIZ keyframe `from` + fill:backwards; sınıf ilk render'da; print animation:none |
| Benekli/grenli SVG dili | `vitrin/varlik/`, feTurbulence tarifi | rasterşiz; bellek: svg-benek-dither-tekniği (13.10'dan beri vitrin zemininde KULLANILMIYOR; rozet/çizimde sürer) |
| Rozet ikon ailesi + menü kutusu | `vitrin/Rozet.tsx`, `vitrin.css` `.vt .vt-mega .vt-rz` | 24 birim, 2 birim çizgi; yatay çizgi ve tepeler tam birimde (24 px'te keskin); genişlik ≤ 20 birim; ortak uçtan çıkan iki eğri kısa/uzun kolla ayrılır (eğrilik farkı) — teğet ayrılış kılcal yarık + «çizme» bırakır (v2.455); merkez çizginin eğrilik yarıçapı her yerde ≥ yarı çizgi kalınlığı (1 birim), yoksa çizginin iç kenarı kırılır (v2.456); kutu 44/r10/zemin .08, kenar her DPR'de 1 CSS px — .5 px kıl çizgi motorlar arası tutarsız (Firefox'ta görünmez, Chrome 3×'te bulanık); en keskin = dik/yatay tam birim çizgi — eğik eğri/büyük yay 2×'te gri ara piksel/beyaz %20+ (Portföy %5): «net değil» şikâyetinde önce bu oranı ölç; veri ikonu Lucide grafik dili (r2 L eksen + çubuk; v2.457 aralık çubukları) |
| Jua katmanı: hero üç katman + cam hap + 300'lük başlık | `vitrin.css` sonu «JUA KATMANI», `Hero.tsx`, envanter `Desktop/jua/jua-tasarim-envanteri.md` | katman dosyanın SONUNDA kalır (sonraki cila ondan önce yazılmaz); perde dizeleri masaüstü/mobil ayrı; h1 vurgusu italik gradyan = R24'ün yeni biçimi; bölüm çubuğu top:0 + padding-top:--vt-ust-y |

## Panel

| Kalıp | Dosya | Kritik kural |
|---|---|---|
| Hero tahmin grafiği (utility-grade) | `sayfalar/ProductionForecastChart.tsx` | D2 tek-kaynak pencere; D3 now-noktası; V1 dar bant (sıfıra demirli dağ YASAK); V2 AC limiti düz kesik |
| İmza bant motifi | `lib/BandImza.tsx` + `pdf.py _imza_bandi` | AYNI kontrol noktaları iki ortamda; renkler var(--chart-*) |
| İnce EChart sarmalayıcı | `lib/EChart.tsx` | sözleşme grafik-tema.md'de; tema fabrikaları Mühür B'de |
| KPI/çip dili | `santralim/*`, Kpi bileşeni | uyari tonu amber DEĞİL; değer nowrap; tire disiplini (`?? 0` yasak) |
| Ayar/form dili | `index.css .ayar/.girdi` | etikette uppercase yok (birim bozulur) |
| Tablo oluğu | `table.veri` | `th+th/td+td{padding-left}` — oluk ilk sütun dolgusuyla OLMAZ (v2.309) |
| Üç kipli tema | `Kabuk` temaKipi oto\|acik\|koyu | pvq_tema localStorage; oto varsayılan |
| Palet/modal kalıbı | Kabuk ⌘K + YeniSantral | kart örtünün ÇOCUĞU + stopPropagation (v2.308 dersi: kardeş çizim örtü altında kalır) |

## Süreç emsalleri

- Metin seçimi: blok başına 5 kurumsal-anlaşılır seçenek sun, kullanıcı seçer (v2.392).
- Tasarım adımı: 3 aday + gerçek içerikli önizleme → kullanıcı seçer → uygula (v2.304-307).
- Bulut teslimi devralma: DEVIR.md + temiz patch kalıbı (v2.393).
- **Üst çubuk hapı rengi/yüksekliği (15.10.2026):** üç seçenek (lacivert cam / buz cam / derin gök) panoda sunuldu; kullanıcı önce C, sonra iki sekmede yan yana görüp B «buz cam»ı seçti. Yükseklik sayfa taramasıyla (hero düğmesi 56, başlık 92) 64 px. Açılır panel ve çekmece hapın CTA rengiyle aynı aile — hap açık, panel siyah bırakılmaz. Kararsızlıkta iki varyantı iki portta yan yana açmak işe yaradı.
- **İkon rötuşu «formu koru, kaliteyi yükselt» (17.10.2026, v2.455):** göz kararı değil ölçü — en kalın yer, kılcal yarık boyu, mürekkep ağırlık merkezi (aile ile kıyas); parametre taraması → «ayak temizliği ↔ özgün forma sapma» Pareto ön yüzü; 1×/2×/3× piksel büyüteci + canlı menü kırpması; sonda tek önce/sonra panosu. Çok motorlu sınama (v2.456): Chrome CDP, WebKit = Playwright önbelleği, Firefox = stok uygulama + puppeteer-core WebDriver BiDi (setViewport deviceScaleFactor); Firefox --screenshot devPixelsPerPx'i yok sayar. Kutu (çerçeve) aileye ortak: yalnız ölçüyle haklı değişiklik, o da tüm kutulara.
- **Bulut turu teslim kalıbı (20–21.10.2026, PR #7/#9/#10/#11):** bulutta ssh ve bellek yok → iş = dal + rapor
  (`perf/RAPOR-FABLE5.md`, `docs/ICERIK-TURKIYE-…`, `docs/SON-KONTROL-…`) + PR; dağıtım ve defter/bellek adımı yerel
  oturumdan. Bulut kredi düşümü ortamdan okunamaz — raporda «doğrulanamadı» yazılır, uydurulmaz. Replika (`perf/replika`,
  Caddy sabit sürüm) ile 4 motor × görünüm × hat matrisi; «sonra» ölçümü kod değişmese de ikinci bağımsız kontrol sayılır.
- **Metin denetimi dört ölçüt (21.10.2026):** (a) Türkiye piyasası uyumu, (b) santral sahibi ilk okuyuşta anlar mı,
  (c) kurumsal ton (edebî fiil, boş sıfat yok), (d) tutarlılık (bölüm adı değişince göndermeler de). Yalnız metin
  düğümü değişir; yapı/CSS/test pini korunur; yeni ifade var / eski ifade yok DOM yoklaması 3 motor × 3 görünüm.
- **Taban imaj sabitleme (20.10.2026, 158d3e1):** `caddy:2` yüzen etiketi 2.10.1–2.10.2'de precompressed → 206 veriyordu;
  `Dockerfile.web` 2.11.7'ye sabit. Güncelleme = changelog + replika sınaması, bilinçli tek satır.
- **Yavaş hat kararı günlük tazelenir (21.10.2026, #11):** `heroHazir.ts` kayıttaki 7 günlük «yavaş hat» kararı günde bir
  yeniden ölçülür — tek yanlış ölçüm videoyu 7 gün kapatmasın.
- **Performans turu — panel geçişleri (24.10.2026, yerelde):** `docs/PANEL-TUR7-2026-10-23.md` §10. Ölçüm:
  `betikler/gecis-olcum.mjs` (örnek kip üretim derlemesi, CDP; ilk/tekrar/akış/hızlı ardışık/heap/konsol) + `profil.mjs`
  (CDP Profiler). Dersler: döngü içinde `new Intl.DateTimeFormat/NumberFormat` kurma → `src/lib/bicim.ts` önbelleği
  (Santralim 4× CPU 179→40 ms); tembel parçaları panel açılınca boş zamanda ön-yükle (ilk ziyaret ~200→~40 ms);
  grafikleri görünür olunca başlat (`EChart` IO); boyutlu iskelet; tema `data-tema`'yı index.html'de ilk boyamadan
  önce (yalnız jetonlu). Ölçüm tuzakları: `.env.local` üretim derlemesine sızar (park et); python http.server'da
  örnek kip `undefined/v1/...` 404'leri; aynı sayfaya «geçiş» h1 değişmediğinden zaman aşımı sayar (betik atlar);
  4× CPU'da ±10 ms gürültü.
- **Yedinci tur — bilgi ayırıcı standardı (23.10.2026, toplu commit bekliyor):** `docs/PANEL-TUR7-2026-10-23.md`. Orta nokta
  «·» bilgi ayırıcısı olarak kalktı (panel 164 + vitrin 29 satır): metaveri dizileri `Meta` (`src/lib/Meta.tsx`, ince
  dikey ayraç — ayraç dilimin solunda mutlak, kap −19 px kenar + `clip-path: inset(0)` ile satır başındaki ayraç
  görünmez), iki sayı `Kpi.ikinci`, düzyazı virgül/noktalı virgül/parantez, uyarılar `ul.not-listesi`, künye notu blok
  satır, «son yükleme» → «son veri» (alan = son ölçüm damgası). Dersler: `.meta > span { nowrap }` dar ekranda uzun dilimi
  taşırır → ≤560 px ve künye satırlarında `white-space: normal`; `table.veri.sayisal` nowrap dar kartta kırpar → tablo
  `.grafik-kaydir` içinde; vitrin dizgilerinde no-break boşluk (U+00A0) düz metin eşleşmesini bozar, `repr()` ile bak;
  JSX dizi öğesi `Meta`'ya verilirken `key` ver (oxlint jsx-key). Cümle başı tire de yasak (bkz. bilesen-dili).
  Sekizinci tur ekleri (23.10, yerelde): uzun çizgi ad+işlem ayırıcısı yasak → `ul.islem-listesi` (santral arşivi),
  `Kart` «Başlık — açıklama» dizgisini `.kart-alt` ile tipografik böler; API uçları `.cip-kod` çipleri; `Meta` kırpma
  hatası `inset(0)` → `inset(0 0 0 19px)` (ölçüm: kap 755 / ilk dilim 774 / ayraç 764 px — ayraç kabın içindeydi).
- **Altıncı tur — santral bilgileri, Kalibrasyon, Tahminler (23.10.2026):** `docs/PANEL-TUR6-2026-10-23.md`. Eksik
  satır = durum sözcüğü + neden (`.kunye-durum` + `.kunye-not`); boş durum `.bos-durum` (kutu yok); uzun teknik not
  `<details class="aciklama">` (metin aynen); geçmiş P50 soluk mavi (`--chart-p50-past`), **lejant örneği çizimle aynı**
  (kesikli yalnız kesikli çizilen); grafik kromu tek şerit; KGÜP `.program-ozet` + `.dugme-grubu`; sentetik sonuç
  «model hesabı · ölçüm değil» rozeti. Ders: örnek verinin tarihi geçmişte → `SAHTE_ZAMAN` ile çek; aynı tablonun ayrık
  alt kümeleri (geçerli/şüpheli saat) etiketle ayrılır, toplam türetilmez.
- **Beşinci tur — Portföy yönetim formları (23.10.2026):** `docs/PANEL-TUR5-2026-10-23.md`. `.form-izgara` kalıbı
  (etiket üstte, 36 px kontrol, onay grubu/düğme hizalı), paylaşım formu yarım sütundan kartın altına tam satıra,
  Hesap/ekip `.alt-bolum` ayraçları, «Pasifleştir» `.dugme-tehlike`, santral tablosu sans tabular + «N gün eski»
  rozeti + klavye odağı. Ders: örnek kipte boş listeler (santral tablosu, ekip) yerelde görülemez — kaynak + canlı
  teyit; JSX yorumu `{cond && ( ... )}` parantezinin içine değil üstüne.
- **Dördüncü tur — künye kartı ve mono disiplini (23.10.2026):** `docs/PANEL-TUR4-2026-10-23.md`. Santral bilgileri
  tablosu → `dl.kunye` (etiket/değer kolonları, değer sola; mono yalnız sayı/tarih/kimlik; durum cümleleri gövde
  ailesi). Veri yükleme: karar/form kartları 1240 px, veri tabloları tam genişlik — tek kural. Üst çubuk + telemetri
  `--yan` yüzeyinde (çerçeve). QA betikleri artık KALICI: `betikler/kare.mjs` (5 genişlik tam sayfa kare + taşma),
  `betikler/pngfark.mjs` (bağımlılıksız piksel kıyası), `betikler/denetim.mjs` (hesaplanmış punto/kontrast/düğme
  yüksekliği, iki tema) — scratchpad iki turda silindi, bir daha yazılmaz. Kullanım başlıkları dosyaların içinde.
- **Üçüncü tur — ölçek bir kademe (22.10.2026 gece):** `docs/PANEL-TUR3-2026-10-22.md`. Ders: 2560 px ekran
  görüntüsünde 14 px gövde «küçük» görünür ve kullanıcı bunu üç brief'te yineledi — ölçüm «standart» dese de fiziksel
  ekran büyüklüğü karar verdirir; gövde 15, tablo 14, eksen 12–13 px. Satır içi boyutlar betikle (grafik satırları ayrı
  tablo: axisLabel/nameTextStyle/textStyle). Koyu temada üç kademe yüzey (zemin/yan/kart 1,04/1,12) «tonlar yakın»
  bulgusunu çözer. Boş grafik yerine koşullu kompakt boş durum (veri yokluğu gizlenmeden).
- **İki tema ölçümlü denetim (22.10.2026 akşam):** rapor `docs/PANEL-DENETIM-2026-10-22.md`. Yöntem: ham CDP
  `denetim.mjs` — her görünür metin düğümü için hesaplanmış aile/punto/ağırlık, yarı saydam katmanları harmanlayan etkin
  zemin ve WCAG kontrast; düğme/girdi yükseklikleri; grafik jetonlarının kart üstü kontrastı; iki temada aynı düğüm
  kümesi → punto histogramı birebir = ölçüler temadan bağımsız kanıtı. Ekran görüntüsünde «küçük» görünen yazı CSS
  değeriyle doğrulanır (2560 px kare yarıya iner). Vitrin bozulmadı kanıtı: `git stash` ile değişikliksiz kare + piksel
  kıyası. Tuzak: scratchpad bir sonraki kullanıcı turunda silinebiliyor — betikleri (kare/pngfark/denetim) yeniden
  yazmak gerekti; kalıcı gerekiyorsa `.claude/skills/pvquant-tasarim/betikler/` altına alınmalı.
- **Tek tasarım sistemi — panel vitrinin kesimine geçti (22.10.2026):** rapor `docs/PANEL-TASARIM-2026-10-22.md`. Vitrinin
  jua katmanı tek doğruluk kaynağı alındı (Inter Tight, mürekkep #0B0E15, gece #0B0E15, hap düğme/çip, 12 px kart köşesi);
  panel gövde/tabloda Inter Variable + Plex Mono'yu korudu, KPI sayıları Inter Tight'a geçti (jetonlar.md istisnası).
  Kart başlıkları mono büyük harf 11 px'ten Inter Tight 15/600 cümle düzenine; satır içi tip ölçeği betikle bir kademe
  (9→10 … 13,5→14; 240 değer, 12 dosya). Yöntem: (1) değişiklik ÖNCESİ 5 genişlik × 11 sayfa tam sayfa kare (ham CDP,
  `kare.mjs`), (2) jetonlar + bileşen CSS, (3) satır içi boyutlar tek betikle (`boyut.py`, kuru koşu→yaz), (4) SONRA aynı
  kareler + vitrin/yöntem piksel kıyası (`pngfark.mjs`, bağımlılıksız PNG çözücü) — /yontem 4 genişlikte BİREBİR, vitrin
  375'te birebir, 1440'ta yalnız canlı animasyon bölgesi çekimden çekime oynar (iki «sonra» çekimi de aynı kutuda ayrışır).
  Dersler: `.soluk` sınıfı 60+ yerde kullanılıp hiç tanımlanmamıştı; `minmax(340px,1fr)` dolgu 4 px artınca 375'te taştı →
  `min(Npx,100%)`; `.env.local` örnek kipi bozar — scratchpad'e park edip sonunda geri koy; fontlar.test/hiz.test
  Space Grotesk'i pinliyordu (sunum testi, güncellendi). web-design-guidelines denetiminden mobil girdi 16 px +
  `touch-action: manipulation` çıktı.
- **Panel dili = piyasa dili (22.10.2026, v2.462):** anti-slop 7'nin panel karşılığı. Standart `docs/PANEL-DIL-2026-10-22.md` §2
  (26 terim; «koşu»→tahmin, «naif»→referans tahmin, «bant»→tahmin aralığı, «zarf»→aralık, «D‑1»→bir gün önce, «AC tavanı»→
  AC sınırı, «künye»→santral bilgileri). Yöntem: tüm eski→yeni çiftleri tek betikte, her eski metin dosyada tam bir kez
  bulunmak zorunda (sessiz yanlış eşleşme yok); aynı liste raporun eki. Bekçi `web/test/panel/dil.test.ts` (yorum ve
  tanımlayıcı kapsam dışı; «naif» gibi ASCII tanımlayıcılar için desen daraltılır). API'den gelen görünür metinler
  (`isler_service.ISIM_TR`, `alarm_service.KURAL_ETIKET`, servis «not» cümleleri) sunum katmanında ÇEVRİLMEZ, raporlanır.
  Yerel doğrulama: `.env.local` kenara → örnek kip (API'siz) ile 9 sayfa, `scrollWidth>clientWidth` taraması.
- **Üç motor turu — Firefox/WebKit (24.10.2026, yerelde):** `docs/PANEL-TUR7-2026-10-23.md` §11; betik
  `betikler/motor-test.mjs` (Playwright; `PW_DIR=<scratch>/pw` ile paket, tarayıcılar ms-playwright önbelleği).
  Dersler: (1) esnek öğeye `display:inline` verme — WebKit bloklaşan kutuyu geniş ölçüp içini dar sarar (telemetri
  dilimi 122 px'te iki satır); inline-flex + `white-space:normal` üç motorda aynı. (2) ECharts `graphic` metni eksen
  sütununa sığmalı: 12 px mono «AC 3.560» ≈ 62 px > 52 px dar pay → pay 60 + 11 px; sağ uca taşımak bant tepesine biner.
  (3) Tembel (IO) grafik kaydırmasız tam sayfa karede boş kalır — kareden önce sona kaydır. (4) Firefox 4190 (sieve)
  portunu yasaklar («Navigation interrupted by another navigation» = uygulama değil port); python http.server Firefox'ta
  belge vermez → `vite preview` + 4273. (5) Vitrin yüklenirken ikinci gezinme WebKit'te iptal edilen tembel import'tan
  «React #306» düşürür — jetonu init-script ile ver, tek gezinme. (6) WebKit'te `requestIdleCallback` yok → yedek şart.
- **Portföy geçişi kök neden turu (24.10.2026, yerelde, commit bekliyor):** `docs/PANEL-TUR7-2026-10-23.md` §12. Dersler:
  (1) «tek kapı» (allSettled) yalnız tüm uçlar hızlıysa doğru — canlıda DSG 1 s, tahmin 500: kritik içerik kendi
  isteğiyle, yan kartlar boyutlu yer tutucuyla. (2) `getir` hatayı belleğe almaz → 500 dönen uç her girişte yeniden gider;
  kısa «başarısız oldu» hafızası (15 sn) + dürüst «sunucu hatası» metni. (3) Çocuk effect'leri ebeveynden önce koşar:
  kritik istekleri `useState` başlatıcısında başlat. (4) Dönüşte bayat-önce (`bellektenOku`) + «güncelleniyor» çipi;
  60 sn tazelik ve hesap sınırı aynı. (5) Vurgu acil, içerik geçiş. (6) Canlı sunucu süresi: konteynerde servis
  fonksiyonunu zamanla (`docker compose exec api python -`), sonra sahte API'ye taşı (`betikler/sahte-api.mjs`) ve gerçek
  tıklamayla ölç (`betikler/portfoy-olcum.mjs`); Chrome eklentisi/canlı giriş yoksa tek dürüst yol bu. (7) «Henüz tahmin
  yok» ile sunucu hatası aynı metinse arayüz yalan söyler — hata ayrı dal.
- **Açık tema geçiş turu (24.10.2026, sekizinci tur):** `docs/PANEL-TUR8-2026-10-24.md`. Dersler: (1) «Tema yavaş»
  şikâyeti veri kapısıydı — oto kipte açık yüzlü sayfalar (Doğruluk/Kalibrasyon/Aylık) tek kapıda bekliyordu; önce tema
  CSS'i değil bekleme biçimi ölçülür (`betikler/panel-gecis-olcum.mjs` + `sahte-api-panel.mjs`, gecikmeler VARSAYIM).
  (2) Portföy kalıbı artık ortak: `bellekten.*` (client) + `YerTutucu` (parcalar) + «hesaplanıyor» (yolda) / «alınamadı»
  (başarısız) ayrımı; yeni veri sayfası bu kalıpla açılır, allSettled kapısı test tarafından yasak (`test/panel/gecis.test.ts`).
  (3) Tema gözlemcisi yalnız `data-tema` — `.tema-gecisi` sınıfı tetik değildir. (4) Grafik girdileri (`forecast/actual/plant/
  features`) her zaman hafızalı/sabit referans; inline map yeni option kurdurur. (5) Taze yanıt bayatla aynıysa eski
  referans korunur (`ayniysaEskisi`) — grafik ikinci kez çizilmez. (6) Ölçüm tuzağı: `startTransition` eski sayfayı ekranda
  tutar; «içerik» ölçütü yeni sayfanın h1'i görünmeden sayılmaz. (7) Yer tutucu yüksekliği oturmuş kartla eşlenir
  (`perf/analiz/acik-tema/kart-yukseklik.mjs`); 4× CPU'da kademeli yerleşme «tam» süresini uzatabilir, raporda saklanmaz.
- **Faz 0 güvenlik tabanı mührü (24.10.2026, v2.479):** `docs/FAZ0-GUVENLIK-2026-10-24.md`. Dersler: (1) Caddyfile tek dosya
  bind-mount (`./Caddyfile:/etc/caddy/Caddyfile:ro`): `git pull` dosyayı yeni inode ile yazar, konteyner ESKİ içeriği görür;
  `caddy reload` «config is unchanged» der → Caddyfile değişen her mühürde `docker compose up -d --force-recreate caddy`.
  (2) RLS testinde reddedilen INSERT oturumu iptal eder: `pytest.raises` `tenant_baglami` bloğunun DIŞINDA (commit patlar);
  `text()` içinde `'{"v":1}'` literal'i `:1` bağ parametresi sanılır → `CAST(:v AS jsonb)`. (3) DB'li testleri CI'ya bırakma:
  yerelde `docker run timescale/timescaledb:latest-pg16` + `PVQ_DB_URL` + `alembic upgrade head` ile 6 dk'da aynı koşul.
  (4) Sürüm numarası çakışması: push reddedilince `git pull --rebase`, uzaktaki numara doluysa yeniden numaralandır (migration
  adı dahil). (5) `docker compose up -d` imaj değişse de bazen web/worker'ı yeniden oluşturmaz → konteyner imaj kimliğini
  imajla kıyasla, gerekirse `--force-recreate`.
- **Faz 1 platform kimliği API'si (24.10.2026, biriktirildi):** `docs/FAZ1-PLATFORM-2026-10-24.md`. Dersler: (1) ikinci yüz
  = ikinci KAPSAM (jeton iddiası `kapsam`), ayrı tablo, ayrı bağımlılık; `gecerli_kullanici` öteki kapsamı 403'ler — tek
  yönlü değil, iki yönlü ret. (2) Yönlendirici ayrı dosyada (`apps/api/yonetim.py`) + limiter ayrı modülde (`hiz.py`),
  dairesel import yok. (3) Denetim izi kendi işleminde ve asla ana işi düşürmez; sır (geçici parola, düz anahtar, davet
  bağlantısı) asla ayrıntıya yazılmaz — test bunu doğrular. (4) Davet = rastgele parola + mevcut parola_sifirlama akışı
  (72 sa); posta kapalıysa bağlantı bir kez yanıtta. (5) DB'li uçtan uca test etiketle temizlenir (uuid parçası e-posta/ad
  içinde) — paralel koşulara dayanır. (6) Yerelde CI koşulu: timescale konteyneri + alembic upgrade head + tam takım ~5,5 dk.
