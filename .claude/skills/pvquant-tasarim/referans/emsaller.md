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
