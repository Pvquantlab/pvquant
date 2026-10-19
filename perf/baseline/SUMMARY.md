# Temel ölçüm (baseline) — pvquant.com, `main` d6ab50a (v2.458)

Ölçüm tarihi: 18.10.2026 · Kod değişikliği YAPILMADAN alınmıştır. Ham veri bu klasörde; tablolar `TABLOLAR.md`
(üretici: `olc/ozet.mjs`, elle düzenlenmez). Bu dosya yöntem, bulgular ve sınırlamaları özetler.

## 1. Neyi, nerede ölçtük

**Barındırma gerçeği.** Site Vercel'de değil: kendi VPS'te (EclitGO), Docker içinde iki Caddy (kenar: TLS, h2+h3,
zstd/gzip, `/v1/*` → API; statik: önceden sıkıştırılmış br/gzip, `/assets` 1 yıl immutable). Vercel önizlemesi ve
Vercel Speed Insights bu yüzden **uygulanamaz** (Vercel hesabında pvquant projesi yok — MCP ile bakıldı).

**Replika.** Üretimle aynı derleme (`perf/replika/derle.sh once d6ab50a` → Dockerfile.web'deki komutların aynısı;
`index.html` canlıdakiyle bayt bayt aynı) ve üretimin **kendi Caddyfile'ları** (yalnız portlar değişti) yerelde
koşar: `https://localhost:18443` (kenar) → statik. `/v1/*` canlı API'ye vekillenir. Farklar: h3 yok (h1/h2),
sertifika yerel CA (Chromium'da SPKI sabitlemesiyle önbellek çalışır), sunucu aynı makinede.

**Ağ kısıtlama.** Tarayıcıdan bağımsız TCP vekili (`perf/replika/kisitla.mjs`): yön başına ortak bant kovası,
paket başı tek yön gecikme, bağlantı başına 1 RTT el sıkışma, 256 KB akış denetimi. Profiller:
«hizli3g» = DevTools Fast 3G (RTT 562,5 ms, ↓1,6 Mbps ↑750 kbps), «yavas4g» = Lighthouse mobil Slow 4G
(RTT 150 ms, ↓1,6 Mbps ↑750 kbps), «yok» = kısıtsız. Her yüklemeden önce hat boşalana dek beklenir (önceki
sayfanın terk edilmiş indirmeleri ölçüme karışmasın).

**Matris.** Motorlar Playwright 1.64.1 derlemeleri: Chromium 156.0.8078.4, Firefox 157.0, WebKit 27.2 (başsız).
Görünümler 390×844 @3 (dokunmatik, mobil), 768×1024 @2 (dokunmatik, mobil), 1440×900 @2, 1920×1080 @1.
Ağ: yok / hizli3g / yavas4g. Önbellek: soğuk (yeni bağlam) + sıcak (aynı sekmede ikinci yükleme). Sayfalar:
`/` ve `/yontem` (üst menüdeki «Ürün, Doğruluk, Türkiye piyasası, Fiyatlandırma, Hakkında» bu iki belgenin
çapalarıdır — ayrı URL'leri yok; panel girişinin de URL'si yok, `/` üzerinde etkileşimle açılır ve etkileşim
ölçümünde «Panele giriş → form» süresi olarak ölçüldü). Her hücre 3 koşu, **medyan**. 216 matris satırı.

**Diğer geçişler.** Ekran görüntüleri (36: motor × görünüm × {/, /yontem, giriş}; tam sayfa; hareket azaltma
açık → video yerine poster, deterministik) `screens/` altında (depoda değil; boyut). Etkileşim/kare süreleri
(36 koşu). Lighthouse 12.8.2 (Chromium, mobil + masaüstü ön ayarı, 3 koşu; replika ve canlı).

## 2. Düzenekte bulunan ve düzeltilen hatalar (sonuçlara güvenmek için)

1. **Vekil bayt sırasını bozuyordu.** Parça başına ayrı `setTimeout`, yoğun olay döngüsünde libuv'nin önbellekli
   saati yüzünden aynı ana düşen parçaların yerini değiştirebiliyordu → TLS kaydı çözülemiyor: Chromium
   `ERR_SSL_PROTOCOL_ERROR`, Firefox `NS_ERROR_NET_PARTIAL_TRANSFER`/`NS_ERROR_ABORT`, WebKit «TLS error».
   Kısıtlı ağdaki 288 yüklemenin 19'unda (17 satır) bağlantıdaki tüm istekler birden düşüyordu. Tek zamanlayıcılı
   FIFO'ya çevrildi; 52 paralel indirmeyle bütünlük sınandı (0 bozuk). Etkilenen 17 satır `matris-vekil-hatasi.jsonl`'a
   taşındı ve yeniden ölçüldü. TLS bütünlüğü bozulmayı her seferinde yakaladığı için hatasız satırlar geçerlidir.
2. Firefox/WebKit tek karede 32 767 aygıt pikselinden uzun görüntü alamıyor → tam sayfa görüntü dilimlenip birleştirilir.
3. Giriş ekranında `<form>` yok → «giriş göründü» koşulu `.giris-form input` oldu.
4. Firefox ve WebKit `layout-shift`/`longtask` girdilerini desteklemiyor (gözlemci sessizce boş döner) → CLS/TBT
   bu motorlarda «ölçülemedi» (—) yazılır, 0 değil. Yerine tüm motorlarda kendi kayma izleyicimiz (önemli öğelerin
   belge içi konumu her karede) kullanıldı.

## 3. Bulgular (sayılar `TABLOLAR.md`'den; medyan)

**LCP «/», soğuk.** Kısıtsız: Chromium 416–784 ms, Firefox 177–596, WebKit 116–764.
Yavaş 4G: Chromium 390 → 1 128, **768 → 4 216, 1920 → 4 852** (LCP öğesi video karesi); Firefox 1 039–1 389;
WebKit 1 800–2 823. Hızlı 3G: Chromium 768 → 5 968, 1920 → 6 808 (video); diğerleri ~2,9–4,4 sn.
Chromium'da LCP öğesi görünüme göre değişiyor: 390 = hero paragrafı, 1440 = h1, **768 ve 1920 = videonun ilk
karesi** (poster sayılmıyor). Firefox'ta hep h1, WebKit'te paragraf/bölüm/poster.

**Firefox / Chromium LCP oranı** (kabul: Firefox, Chromium'dan %20'den fazla yavaş olmamalı): «/»'de Firefox her
hücrede Chromium'dan hızlı (0,23–0,98). Tek aşım `/yontem` kısıtsız 768: 309 ↔ 136 ms (×2,27; mutlak 173 ms).
Yani laboratuvarda Firefox'un «ilk görüntüsü» yavaş değil; yavaşlık hissi başka yerden geliyor (aşağıda).

**Lighthouse (medyan, 3 koşu).**

| hedef · sayfa · tür | Perf | Erişil. | En iyi uyg. | SEO | LCP | TBT | CLS |
|---|---:|---:|---:|---:|---:|---:|---:|
| canlı · / · mobil | **85** (71–85) | 100 | 100 | 91 | 4 217 | 91 | 0 |
| canlı · / · masaüstü | 100 | 100 | 100 | 91 | 793 | 0 | 0 |
| canlı · /yontem · mobil | 99 | 100 | 100 | 91 | 1 812 | 35 | 0 |
| canlı · /yontem · masaüstü | 100 | 100 | 100 | 91 | 412 | 0 | 0 |
| replika · / · mobil | **75** (47–85) | 100 | 100 | 91 | 7 506 | 124 | 0 |
| replika · / · masaüstü | 93 | 100 | 100 | 91 | 1 764 | 0 | 0 |

«/» mobilde LCP öğesi hero paragrafı (`p.vt-giris`); gecikmenin tamamı «Render Delay» (3,6–9,8 sn; TTFB ~0,6, yükleme
gecikmesi 0). Koşudan koşuya 4,2 ↔ 10,4 sn oynaması, gözlenen LCP anının videonun indirilmeye başladığı anla yarıştığını
gösteriyor (Lighthouse'un benzetimi, gözlenen LCP'den önce başlayan istekleri hesaba katar). Kriter (≥90) karşılanmıyor.

**Etkileşim ve kare süreleri** (başsız; video oynarken; medyan): WebKit her görünümde 60 kare/sn, menü 41–69 ms.
**Firefox'ta kaydırma çöküyor**: 1440'ta kaydırma kare p95 216 ms (%32 kare >33 ms), 1920'de 376 ms; boşta (hero, video
oynuyor) 60 kare/sn. Menü açılışı Firefox 101–539 ms. Chromium başsız kabukta her şey yavaş (boşta p95 117–650 ms):
bu, başsız Chromium'un yazılım GPU'sundan (SwiftShader) geliyor olabilir — pencereli stok Chrome ile ayrıştırıldı
(Faz 2, `analiz/ab/`). Firefox 120 sn içinde `load`'a ulaşamayan 1 koşu (1920 #3; 1 koşu daha ilk denemede, 390 #3).

**Aktarım.** Kısıtsız soğuk «/»: Chromium 3,1 MB (+ Resource Timing'e yazılmayan süren video), Firefox 39,5 MB
(1440 videosunun tamamı yükten hemen sonra), WebKit 37–45 MB ve **sıcak yüklemede de 36–48 MB** (WebKit medya
yanıtlarını önbellekten kullanmıyor). Kısıtlı hatta video indirilmiyor (yavaş hat kuralı K1) — soğukta.

**Kayma.** Chromium CLS ≤ 0,028 (tüm hücreler). Kendi izleyicimiz (tüm motorlar): 390'da hero düğme grubu soğuk
yüklemede **25 px** zıplıyor (Chromium/Firefox/WebKit, kısıtlı hatta; Firefox kısıtsızda da), `/yontem` başlığı Firefox'ta
36–56 px. Kaynak: yedek fonttan web fontuna geçiş (FOUT) — Faz 2'de doğrulanır.

**Hatalar.** Düzenek hatası ayıklandıktan sonra 432 yüklemede konsol hatası 0, 4xx/5xx 0, başarısız istek 0.
Tek kayıt: Firefox'un `NS_ERROR_PARSED_DATA_CACHED` iç kodu (medya önbelleğinden karşılanan isteğin iptali; hata değil).

**Sayfa boyu farkı.** WebKit'te «/» 20–79 px daha uzun (390: 12 619 ↔ 12 540) → satır kırılımı farkı; Faz 2'de bölüm
bazında aranır. Yatay taşma hiçbir motorda yok.

## 4. Saha verisi

- **CrUX / PageSpeed Insights: yapılamadı.** Anahtarsız PSI API'si iki ayrı denemede (16.10 ve 18.10) `429 Quota
  exceeded (Queries per day)` döndü (`saha.json`). CrUX API anahtar istiyor; bu ortamda anahtar yok.
- **Vercel Speed Insights: uygulanamaz** (site Vercel'de değil).

## 5. Sınırlamalar

- Başsız motorlar GPU'ya dayalı CSS'i (cam bulanıklığı, filtre, video) yazılımda çizebilir; kare süreleri motorlar arası
  ve önce/sonra **kıyas** içindir. Gerçek GPU yolu Faz 2'de pencereli stok Chrome ve stok Firefox 158 ile ölçüldü.
- Playwright Firefox'u (157) stok Firefox değil (renk yönetimi kapalı, bazı tercihler farklı); stok Firefox 158 ayrıca kullanıldı.
- Firefox'ta `isMobile` yok (Playwright); 390/768 Firefox'ta dokunmatik ama masaüstü UA ile koşar.
- Replika h3 konuşmaz; üretimde Firefox/Safari h3 kullanabilir. `/v1/*` canlıya gider (gerçek gecikme içerir).
- Gerçek Safari, iOS Safari, Android Chrome, Brave, Edge: bu makinede otomatik sürülemedi (bkz. REPORT.md, elle kontrol listesi).
