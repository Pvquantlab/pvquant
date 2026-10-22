# Panel görsel uyumlaştırma — tek tasarım sistemi (22.10.2026)

Amaç: pazarlama sayfası (vitrin) ile yönetim paneli aynı kurumsal SaaS ürününe ait okunsun. Yalnız
sunum katmanı (`web/src/index.css`, panel TSX'lerinde satır içi boyut/sınıf, iki sunum testi) değişti;
yazılım çekirdeğine (modeller, hesaplar, API, veritabanı, servisler, zamanlanmış işler, kimlik) dokunulmadı
(§9 git kanıtı). Durum: **CANLI — v2.464 (e3599ed), CI #538 yeşil, sunucuda yalnız web imajı yenilendi;
canlı index.html ve 16 JS parçası yerel referans derlemeyle sha256 birebir (22.10.2026).**

## 1. Tespit edilen farklar (önce)

Vitrinin görünen tasarımı `vitrin.css`'in sonundaki «JUA KATMANI»ndan okunur (13.10.2026'dan beri kök
jetonları ezer); panelin değerleri `index.css` `:root`'tan. Gerçek değerler:

| Boyut | Vitrin (gerçek) | Panel (önce) | Fark |
|---|---|---|---|
| Yazı ailesi | Inter Tight tek aile (300 başlık · 400 gövde · 500 etiket/düğme · 600 kart başlığı) | Inter Variable gövde + Space Grotesk h1 + IBM Plex Mono her yerde (kart başlığı, çip, sekme, tablo başlığı, telemetri, seçici, girdi, segment) | Üç aile; mono krom «terminal» görünümü |
| Başlık kesimi | h3 kart 24/600 −.015em; eyebrow 13/500 +.14em büyük harf | Kart başlığı Plex Mono 11 px büyük harf +.1em; h1 Space Grotesk 24–26/700 | Aile ve ağırlık uyumsuz |
| Tip ölçeği | gövde 17/26 · kart 16 · künye 14 | gövde 14 · notlar 11–12,5 · etiketler 10–11 · eksen 9–10 | Panelde 9–11 px yoğunluğu |
| Mürekkep | #0B0E15 / #404551 / #6B7280 | #101D30 / #2C3E57 / #45586F (mavi-gri) | Farklı merdiven |
| Koyu zemin | #0B0E15 (gece), cam kart beyaz .02–.03 + kenar .10 | #0B1424 lacivert, kart #17243C | Vitrinde karşılığı olmayan ikinci koyu ton |
| Açık zemin | beyaz / krem #FEF0E6, kart #FAFAFA, kenar #E5E6EA | #E3E9F2 mavi-gri kâğıt | Vitrinde karşılığı yok |
| Birincil düğme | 999 px hap; açıkta mürekkep (#0B0E15) + beyaz yazı, koyu çubukta beyaz hap | 4 px köşe, yeşil dolgu | Biçim ve renk farklı |
| Köşe | 24–28 kart, 999 düğme/çip, 12–18 pencere | 4 kontrol / 6 kart | — |
| Yerleşim | `.vt-kap` 1360 + kenar payı, ortalı | `.icerik` max 1560, sola yaslı → 2560 px ekranda sağda ~800 px boşluk | Geniş ekranda dengesiz |
| Sayı tipografisi | Inter Tight tabular (karne sayıları 300/40) | Plex Mono 500/27 | — |

## 2. Ortak tasarım sistemi (karar)

**Tipografi (en yüksek öncelik)**
- `--display: 'Inter Tight'` — vitrinin tek ailesi panelin başlık/etiket/düğme/KPI ailesi oldu. Dosyalar
  vitrin `fontlar.ts`'ten zaten ana pakette (Vitrin.tsx tembel değil); ek bayt yok. Space Grotesk kalktı
  (iki woff2 daha az iner). Türkçe alt küme (ğ/ş/İ) vitrinle aynı dosyalardan.
- Gövde ve tablo 12–14 px'te **Inter Variable** kalır: optik boyut ekseni küçük puntoda Inter Tight'tan
  okunaklı; Inter Tight ≥13 px rollerde. (Aynı tasarımın iki kesimi — tek karakter.)
- **Plex Mono** yalnız veri: tablo gövdesi, eksen, kod/anahtar/adres, zaman damgası. Mono tablolarda ilk
  sütun (etiket) gövde ailesine alındı.
- Ölçek: sayfa h1 **26/600** · bölüm h2 **20/600** · kart h3 **15/600** cümle düzeni · gövde **14** · ikincil
  **13** · tablo **13,5** · etiket/eyebrow **12/500 +.10em** · nav **14,5** · düğme **13,5** · KPI **30/500**
  tabular. Satır içi boyutlar tek betikle bir kademe yukarı (9→10 · 10→11 · 11→12 · 12→12,5 · 12,5→13 ·
  13→13,5 · 13,5→14; 240 değer).
- KPI/özet sayıları Inter Tight 500 tabular (vitrinin karne sayısı kesimi). jetonlar.md'ye «22.10 istisnası»
  olarak işlendi; tek jetonla geri alınabilir.

**Renk**
- Mürekkep merdiveni vitrinden: metin #0B0E15 · ikincil #404551 · soluk **#5B6270** (vitrinin #6B7280'i 13 px
  metinde açık zeminde 4,3:1 kalıyordu; #5B6270 zeminde 5,1 · kartta 6,1).
- Koyu yüz = vitrin gecesi: zemin **#0B0E15**, kart **#14161D** (opak; zemin + %3,5 beyaz — D1 «opak kart»
  kuralı korunur), kenar beyaz .12, metin #FFF / #D2D5DC (12,3:1) / #A3A9B4 (7,7:1).
- Açık yüz: nötr zemin **#E8EAEE** (opak beyaz kart/zemin 1,20 ≥ v2.305 hedefi 1,15), kenar #D9DBE1.
- Yeşil `--marka` korunur: amblem, nav aktif, rozet-ok, odak halkası, başarı. Birincil düğme vitrin gibi:
  açıkta mürekkep hap/beyaz yazı (17:1), koyuda beyaz hap/mürekkep yazı.
- Grafik sözleşmesi değişmedi: mavi = tahmin, amber = yalnız gerçekleşen; `--chart-*` yalnız mürekkep/zemin
  tonları yeni merdivene bağlandı.
- Giriş ekranı sol yüzü: #0B0E15 + jua radyal ışıkları (lavanta .24 / camgöbeği .18), vurgu düz gök mavisi
  #8FD3FF; yeşil→mavi lacivert degrade kalktı.

**Köşe ve yerleşim**
- `--r` 8 (girdi/kontrol) · `--rk` 12 (kart/KPI) · `--r-hap` 999 (düğme, çip, rozet, sekme, segment, arama) ·
  pencere 16 (palet, alarm).
- Yan menü 236 px; `.icerik` max **1600 px, ana sütunda ortalı**; dolgu 28/36 (mobil 16); ızgara oluğu 16;
  kart dolgusu 20/22; satır içi `minmax(Npx, 1fr)` → `minmax(min(Npx, 100%), 1fr)` (375'te taşma kaynağı).

**Bileşenler**
- Düğme: hap, Inter Tight 500 13,5, kenarlı; hover zemin; `dugme-ana` yukarıdaki gibi; `disabled` .55.
- Girdi: gövde ailesi 13,5, 8 px köşe, kart zemini, odakta marka halkası (giriş ekranı kuralı); `.girdi.mono`
  adres/anahtar için mono kalır. Mobilde 16 px (iOS yakınlaştırma).
- Sekme/segment/arama: hap; sekme seçili = kart zemini + hafif gölge.
- Çip `.cip`: Inter Tight 500 12, hap; rozet aynı kesim.
- Kart: 12 px köşe, 1 px kenar, başlık 15/600 + ince ayraç; `.kart-no` bölüm numarası korunur.
- Eyebrow `.etiket-ust`: kart içi grup etiketi (API anahtarları, Webhook alıcıları, Parolamı değiştir, Ekip…).
- `.soluk` sınıfı 60+ notta kullanılıyordu ama hiç tanımlı değildi — tanımlandı (`--soluk`).
- Alarm paneli, palet: 16 px köşe, başlık 15/600, kart zemini (koyuda ayrı sabit renk kalktı).
- Dokunma: `touch-action: manipulation` (web-design-guidelines denetimi).

## 3. Sayfa bazında

| Sayfa | Görünen değişiklik |
|---|---|
| Hepsi | Yan menü/üst çubuk Inter Tight; kart başlıkları cümle düzeni; çipler hap; arka plan/kart/kenar yeni jetonlar; içerik ortalı |
| Portföy | KPI 30 px Inter Tight; «Dış erişim / Kuruluşlar arası / Hesap» grup etiketleri eyebrow; form girdileri 13,5/8 px; 375'te taşma giderildi |
| Santralim | Özet şeridi sayıları Inter Tight; «Santral bilgileri» etiket sütunu gövde ailesi; hava kartı 21 px; ayar satırları 14/600 başlık; grafik eksenleri 11,5–12,5 |
| Veri yükleme | «%5–10 / %1–3» Inter Tight; «Kalibre tahmine geç» vitrin hapı (koyuda beyaz) |
| Kalibrasyon | Kart başlıkları ve çipler; sapma önce→sonra sayıları Inter Tight |
| Tahminler | Segment hap; lejant gövde; eksen/etiket +1 px |
| Doğruluk | KPI'lar; güvenilirlik/PIT eyebrow'ları cümle düzeni; eksen 9→10, 10→11 |
| Aylık beklenti | KPI'lar; eksen 11→12; tablo 13,5 |
| Raporlar | Hazırla düğmeleri hap; tahmin geçmişi tarih sütunu gövde ailesi tabular |
| Hakkında | Başlık/kart kesimi |
| Giriş | Vitrin gecesi + ışıklar; başlık Inter Tight 500; mürekkep hap düğme; etiketler Inter Tight 500 |
| Alarm paneli, ⌘K paleti, yeni santral formu | 16 px köşe, yeni kesim |

## 4. Değişen dosyalar (18 — tümü `web/`)

- `web/src/index.css` — jetonlar, tip merdiveni, bileşen kuralları (ana değişiklik)
- `web/src/fontlar.ts` — Space Grotesk içe aktarmaları kalktı
- `web/src/App.tsx` — giriş ekranı font bekleme listesi: Space Grotesk → Inter Tight 500
- `web/src/features/sayfalar/parcalar.tsx` — Kpi `mono` sınıfı kalktı, Sayfa h1 boyutu CSS'e, birim 14 px
- `web/src/features/sayfalar/{Portfoy,Digerleri,Dogruluk,Aylik,Tahminler,Hakkinda,JsonOnizleme,BandImza,ProductionForecastChart}.tsx`,
  `web/src/features/santralim/{Santralim,Cubuklar}.tsx`, `web/src/shell/Kabuk.tsx` — yalnız satır içi
  `fontSize` kademesi, `className="mono"`→`etiket-ust`/`sayi-buyuk` (11 yer), `minmax(min(…))` (4 yer),
  ProductionForecastChart'ta jenerik `"monospace"` → `'IBM Plex Mono'` (10 yazı dizgisi). Mantık, veri, API
  çağrısı, olay işleyici değişmedi.
- `web/test/fontlar.test.ts`, `web/test/vitrin/hiz.test.ts` — Space Grotesk pinleri Inter Tight'a (sunum testi)
- Defter: `.claude/skills/pvquant-tasarim/referans/jetonlar.md`, `emsaller.md`

## 5. Duyarlı tasarım sonuçları

Ham CDP (`kare.mjs`, Chrome 155 headless), örnek kip, 5 genişlik × 12 kare (9 panel sayfası + giriş + vitrin
+ /yontem) = 60 tam sayfa kare; her karede `scrollWidth − clientWidth` ölçüldü.

| Genişlik | 375 | 768 | 1024 | 1440 | 1920 |
|---|---|---|---|---|---|
| Yatay taşma | 0 (ara turda Portföy 4 px → `min(340px,100%)` ile 0) | 0 | 0 | 0 | 0 |

Tema kipleri: oto (operasyon koyu / kanıt açık), zorla açık (Portföy, Santralim, Veri yükleme, Tahminler),
zorla koyu (Doğruluk, Raporlar, Aylık, Kalibrasyon) — hepsi görsel olarak denetlendi; 1920'de içerik ortalı.

## 6. Tarayıcı sonuçları

- Chromium 155 (headless, CDP) — tüm kareler; Claude tarayıcı paneli (Chromium) — canlı HMR denetimi.
- Firefox / Safari / Edge: **bu turda koşulmadı** (ortamda Playwright paketi yok; yalnız motor önbelleği var).
  Değişiklik standart CSS (grid, custom property, `min()`, `font-variant-numeric`) — 19.10 çapraz tarayıcı
  turunda doğrulanmış özellik kümesi; ayrı doğrulama önerilir, tamamlanmış sayılmaz.

## 7. İşlev koruma kontrolleri

- `npx tsc --noEmit -p tsconfig.app.json` → 0 hata.
- `npm test` → 73/73 (panel dili bekçisi dahil).
- `npm run build` → 0 (yalnız mevcut «chunk > 500 kB» uyarısı).
- `npx oxlint src` → 16 uyarı = main'deki 16 (aynı; hiçbiri bu değişiklikten).
- pytest: bkz. §7a.
- Vitrin bozulmadı: `pngfark.mjs` (bağımlılıksız PNG çözücü) ile önce/sonra piksel kıyası — **/yontem 375 ve
  1440 BİREBİR; vitrin 375 BİREBİR**; vitrin 1440'ta yalnız x 445–1349 / y 3504–3713 kutusu (İş birimleri
  Storyset levhaları, `.vt-is__levha` — sırayla yüklenen resimler) oynuyor; aynı kutu iki «sonra» çekimi
  arasında da ayrıştığından çekim zamanlaması, stil değil. `web/src/features/vitrin/` altında değişen dosya yok.
- Düğme/form/tablo davranışı: yalnız sınıf ve stil değişti; `onClick`/`onSubmit`/API çağrısı satırlarına
  dokunulmadı (`git diff` TSX'lerde yalnız `fontSize`, `className`, `minmax`, font dizgileri).

### 7a. pytest
`.venv/bin/python3 -m pytest -q` (db ayakta) → **682 passed, 0 failed** (5 dk 23 sn; 76 uyarı mevcut). İlk koşu
RLS izolasyon testinde DB bağlantısı olmadığından `-x` ile durmuştu (597 geçti, 1 ortam hatası); `docker compose
up -d db` sonrası tam koşu temiz. Backend bu turda değişmedi — koşu yalnız ritüel gereği.

## 8. Çekirdek koruma kanıtı

`git status --short` → değişen 18 dosyanın tamamı `web/` altında; `src/pvquant/`, `apps/`, `alembic/`,
`docker-compose*`, `Caddyfile*`, `.github/` değişmedi (`git status --short | grep -v '^ M web/'` boş).
`web/src/api/` (istemci sözleşmesi) ve `web/src/features/vitrin/` değişmedi.

## 9. Güvenle uygulanamayan / bilinçli dışarıda bırakılan

- Tablo gövdelerindeki uzun düz yazı («11.737 işaretlendi; hiçbir satır silinmedi») mono kaldı — hücre bazında
  sınıf eklemek 60+ TSX dokunuşu; bir sonraki turda.
- Aylık GHI grafiğinde değer etiketleri hata çubuğuyla biniyor (önceden de böyle; grafik seçeneği, bu turun kapsamı dışı).
- Örnek kipte Doğruluk «Kapsanan dönem: NaN undefined» (örnek veri eksikliği; önce de vardı, canlıda yok).
- Portföy KPI «—» Inter Tight'ta kalın bir çizgi gibi okunuyor; tire disiplini korunduğu için bırakıldı.
- Firefox/Safari/Edge doğrulaması (§6).

## 10. Onay sonrası

Mühür ritüeli: Türkçe NE/NEDEN/KANIT commit (vN) → push → CI tarayıcıdan → ssh dağıtım (yalnız web imajı) →
canlı sha ve kare kıyası → bellek. `web/.env.local` scratchpad'den geri konuldu (yerel API adresi).
