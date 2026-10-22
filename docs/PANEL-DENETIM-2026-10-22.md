# Nihai tasarım denetimi — açık/koyu tema uyumlaştırması (22.10.2026, v2.464 üstüne)

Önceki tur: `docs/PANEL-TASARIM-2026-10-22.md` (v2.464 canlı). Bu tur: iki temanın **bağımsız, ölçüme dayalı**
denetimi ve kalan pürüzlerin giderilmesi. Yalnız `web/src` (9 dosya); çekirdek, API, veritabanı, vitrin kaynakları
değişmedi (§H). Durum: **CANLI — v2.465 (9f135cd), CI #540 yeşil, sunucuda yalnız web imajı yenilendi; canlı
index.html ve JS parçaları referans derlemeyle sha256 kıyaslandı (22.10.2026).**

## Yöntem

- Gerçek hesaplanmış stiller: ham CDP betiği `denetim.mjs` iki temada 9 sayfayı açıp her görünür metin düğümü için
  aile/punto/ağırlık/renk/etkin zemin (yarı saydam katmanlar harmanlanarak) → WCAG kontrast; düğme/girdi yükseklikleri;
  grafik jetonlarının kart zemini üstündeki kontrastı. Önce 1 374 / sonra 1 374 metin düğümü × 2 tema.
- Kareler: `kare.mjs`, Chrome 155 headless, örnek kip; **koyu 45 + açık 50 tam sayfa kare** (9 sayfa × 5 genişlik,
  + giriş), her karede yatay taşma ölçümü.
- Vitrin bozulmadı: bu turun değişiklikleri `git stash` ile geri alınıp aynı anda yeniden çekildi — vitrin ve /yontem
  **1440 ve 375 px'te piksel BİREBİR** (`pngfark.mjs`).
- Kullanıcının canlı ekran görüntüleri (27 adet, açık 22:15–22:16, koyu 22:17–22:18, 2560 px) kaynak kodla birlikte
  okundu; ekranda küçük görünen yazılar CSS değeriyle doğrulandı (2560 px ekran görüntüsü yarıya ölçeklendiği için
  13–14 px yazı 7 px görünür — gerçek punto küçük değil).

## A. Başlangıç durumu (ölçüldü)

**Başarılı (korundu):** iki tema aynı CSS kurallarını paylaşıyor — tema yalnız `:root` / `[data-tema="koyu"]` jetonlarını
değiştiriyor; punto/ağırlık/köşe/boşluk/ızgara iki temada **birebir aynı dağılım** (ölçüm: aynı 1 374 düğüm, aynı
punto histogramı). Inter Tight başlık/etiket/düğme, Inter Variable gövde, Plex Mono veri her iki temada tutarlı.
DOM metinlerinde **kontrast ihlali 0** (normal ≥4,5, büyük ≥3) iki temada da.

**Kısmen çözülmüş / kalan pürüzler:**
1. Açıklama paragrafları (`p.soluk`, 34 yer) 12,5–13 px — «normal açıklama 14–16» hedefinin altında; kullanıcı
   ekranında küçük okunuyordu.
2. Kısa kontroller: tema segmenti ve dönem segmentleri 25 px, sekmeler 28 px, grafik PNG/CSV 23 px, «Çıkış yap» 14 px.
3. Grafik ızgarası: koyu 1,32:1, açık 1,27:1 — kullanıcı bulgusu «koyu temada çizgiler zemine yakın» ölçümle doğrulandı;
   açık temada «en düşük ay» çubuğu #9AA6B5 beyazda **2,47:1** (grafik nesnesi eşiği 3 — tek gerçek kontrast ihlali).
4. Açık temada yan menü ile içerik zemini aynı ton (#E8EAEE); ayrım yalnız 1 px çizgi.
5. `.yan-ozet .et` 10,5 px (en küçük punto); grafik dışa aktarma düğmeleri hâlâ mono + 4 px köşe (hap diline aykırı).

**Vitrinle süren fark (bilinçli):** vitrin gövdesi 17/26 px, panel 14/1,55 — veri yoğunluğu için; kart köşesi vitrin 24–28,
panel 12; panel tablo/eksen/kod Plex Mono (vitrinde yok). Bunlar «aynı ürün, iki yüzey» kararı; değiştirilmedi.

## B. Yapılan değişiklikler (yalnız sunum)

| # | Değişiklik | Dosya |
|---|---|---|
| 1 | `p.soluk` açıklama paragrafları 12,5/13 → **13,5 px** (33 yer, tek regex) | Portfoy, Digerleri, Dogruluk, Aylik, Tahminler, Hakkinda |
| 2 | `.dugme` **min 32 px**, flex ortalı; `.sekme button` ve `.seg button` **30 px** (13 px yazı) | index.css |
| 3 | «Çıkış yap» 28 px dokunma alanı, Inter Tight 500 13 px, alt çizgi 3 px | Kabuk.tsx |
| 4 | Grafik dışa aktarma düğmeleri (PNG/CSV) ve «şimdi» hapı: Inter Tight 500, 999 köşe, ≥28 px | ProductionForecastChart.tsx |
| 5 | Koyu: `--chart-grid` .10→**.14** (1,32→1,52), `--izgara` .09→.11, `--chart-daybreak` .16→.18 | index.css |
| 6 | Açık: `--chart-grid` .11→**.13**, `--izgara` .10→.12, `--ch-dusuk` #9AA6B5→**#7F8B9A** (2,47→3,46) | index.css |
| 7 | Açık yan menü `--yan` **#F2F3F5** (zeminden bir ton açık; soluk metin 5,5:1) | index.css |
| 8 | `.yan-ozet .et` 10,5 → 11 px | index.css |

Mantık, veri bağları, olay işleyici, API çağrısı değişmedi (`git diff`: yalnız CSS, satır içi `fontSize`, stil nesneleri).

## C. Açık tema sonucu

Vitrinin beyaz/gri yüzey dili: beyaz kartlar nötr gri zeminde (1,20), yan menü ayrı ton, mürekkep #0B0E15/#404551/#5B6270
(vitrinin merdiveni), hap düğme/çip, Inter Tight başlıklar. Ölçüm: 1 374 metin düğümünde kontrast ihlali 0; en düşük
normal-metin kontrastı 4,96 (ısı haritası hücresi), soluk metin kartta 6,1 / zeminde 5,1 / yan menüde 5,5. Grafik:
eksen yazısı 6,1, ızgara 1,32, çubuklar ≥3,4. Pazarlama sayfasından panele geçiş: aynı aile, aynı hap, aynı mürekkep;
fark yalnız yoğunluk ve veri fontu.

## D. Koyu tema sonucu

Vitrinin gecesi (#0B0E15) + opak kart (#14161D), beyaz hap birincil düğme, yeşil seçim/durum. Ölçüm: kontrast ihlali 0;
beyaz metin 18:1, ikincil 12,3, soluk 7,7; eksen yazısı 7,7; ızgara 1,52 (idi 1,32); en düşük ay çubuğu 3,4; kenar 1,41.
Odak halkası yeşil 2 px (zeminde 7,5:1). Kart/zemin ayrımı 1,19 — vitrinin cam karne kartıyla aynı mantık.

## E. Tema tutarlılığı

Tema değişince yalnız 44 renk jetonu değişir; tip ölçeği, ağırlık, satır yüksekliği, köşe, boşluk, kontrol yükseklikleri,
ızgara ve içerik genişliği **ortak CSS**. Ölçümle: iki temada aynı 1 374 düğüm, aynı punto histogramı
(10,5–11,5: yalnız yan özet etiketi/⌘K; 12: 71; 12,5: ~200; 13–13,5: ~270; 14–15: ~180; 17–30: başlık/KPI).
Tema geçişi (`pvq_tema`, oto/açık/koyu) ve atomik geçiş sınıfı değişmedi; tema değişince konum kayması yok
(aynı yerleşim kuralları, karelerde sayfa yükseklikleri iki temada aynı).

## F. Testler

- `npx tsc --noEmit` 0 · `npm test` 73/73 · `npm run build` 0 · `npx oxlint src` 16 uyarı = main (aynı).
- pytest bu turda koşulmadı: backend dosyası değişmedi (v2.464'te 682/682).
- Kareler: koyu 45 + açık 50 (375/768/1024/1440/1920 × 9 sayfa + giriş) — **taşma 0**; 20 kare gözle incelendi
  (koyu Portföy/Tahminler 1440, Doğruluk 768; açık Portföy 375, Santralim 1440 …).
- Vitrin/yontem: bu turun değişiklikleriyle/değişikliksiz 1440 ve 375 px'te **piksel birebir**.
- Tarayıcı: Chromium 155 (headless CDP) + Claude tarayıcı paneli. **Firefox / Safari / Edge koşulmadı** (ortamda
  Playwright paketi yok) — doğrulanmış sayılmaz.

## G. Değiştirilen dosyalar (9, tümü `web/src`)

`index.css`, `shell/Kabuk.tsx`, `features/sayfalar/ProductionForecastChart.tsx`, `features/sayfalar/{Portfoy,Digerleri,
Dogruluk,Aylik,Tahminler,Hakkinda}.tsx` (yalnız `p.soluk` satır içi `fontSize`). Defter: `jetonlar.md`, `emsaller.md`.

## H. Çekirdek koruma

`git status --short` → değişen dosyaların tamamı `web/src/`; `src/pvquant/`, `apps/`, `alembic/`, `web/src/api/`,
`web/src/features/vitrin/` değişmedi. Satır içi değişiklikler yalnız `fontSize`, stil nesneleri ve CSS.

## I. Kalan sorunlar

- Firefox/Safari/Edge doğrulaması (F).
- Tablo hücrelerindeki uzun düz yazılar (ör. «11.737 işaretlendi; hiçbir satır silinmedi») hâlâ Plex Mono — hücre
  bazında sınıf gerekir; ayrı tur.
- Aylık GHI grafiğinde değer etiketleri hata çubuğuyla binişiyor (eski; grafik seçeneği).
- `.yan-ozet .et` 11 px ve ⌘K kısayol kutusu 10,5 px: bilerek küçük (etiket/kısayol), 12 px eşiğinin altında kalan tek
  iki öğe.
- Örnek kipte Doğruluk «Kapsanan dönem: NaN undefined» (örnek veri; canlıda yok).

## J. Uzman değerlendirmesi (10 üzerinden; ölçüm yerine geçmez)

| Kriter | Vitrin | Panel açık | Panel koyu | Gerekçe |
|---|---|---|---|---|
| Tipografi | 9 | 8,5 | 8,5 | Aynı aile ve kesim; panel bilerek daha yoğun ölçek |
| Okunabilirlik | 9 | 8,5 | 8,5 | Kontrast ihlali 0; en küçük 11 px iki etiket |
| Renk sistemi | 9 | 8,5 | 9 | Mürekkep merdiveni ve gece zemini vitrinden; yeşil panel-özel seçim rengi |
| Kartlar | 9 | 8,5 | 8,5 | 12 px köşe, 20/22 dolgu, 1 px kenar; vitrin 24–28 |
| Düğmeler | 9 | 8,5 | 8,5 | Hap, ≥28–32 px; birincil düğme vitrinle aynı |
| Formlar | — | 8 | 8 | 13,5 px girdi, 8 px köşe, odak halkası; mobilde 16 px |
| Grafikler | 9 | 8 | 8,5 | Eksen ≥6:1, ızgara 1,3–1,5; etiket binişmesi (Aylık) açık |
| Yerleşim | 9 | 8,5 | 8,5 | 1600 px ortalı; formlar sınırlı; boş durumlar tek cümle |
| Responsive | 9 | 9 | 9 | 5 genişlikte taşma 0, 375'te kenar 16 px |
| Genel bütünlük | — | 8,5 | 8,5 | Aynı ürün hissi; kalan fark yoğunluk ve veri fontu |
