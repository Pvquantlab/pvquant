# PVQuant vitrin — Fable 5 turu: tarayıcılar arası ölçüm, uyumluluk ve optimizasyon raporu (20.10.2026)

Dal: `main-bozzyl` (PR #7, taslak). Temel: `main` 1494f8e (= canlı v2.461'in web/ ağacı; 89ef100 ve 1494f8e yalnız perf/.gitignore).
Geri dönüş etiketi: `fable5-baslangic` = 002caed. Bu rapor dünkü `perf/REPORT.md` (v2.459 turu, K1–K13) üzerine kurulur; oradaki
bulgular tekrar keşfedilmedi, açık kalanlar ölçüldü.

**Ortam (bulut, Linux):** Ubuntu 24.04, 4 çekirdek, 15 GB, ekran kartı YOK (yazılım GPU). Playwright 1.64.1: Chromium 156.0.8078.4,
Firefox 157.0, WebKit 27.2 (Safari 26 motoru); Microsoft Edge 155.0.4283.62 (stok, Playwright `msedge` kanalı); Lighthouse 12.8.2;
Caddy 2.11.7. Replika = üretimdeki iki katmanlı Caddy'nin yerel kopyası (`perf/replika`), `/v1/*` canlı API'ye gider; kısıtlı hatlar
TCP vekiliyle (Slow 4G: 150 ms RTT / 1,6 Mbps; Fast 3G: 562 ms / 1,6 Mbps; kablo20: 40 ms / 20 Mbps). Her hücre 3 koşu medyanı,
her koşu soğuk (yeni bağlam) + sıcak (aynı bağlamda ikinci gezinme). Ham veri: `perf/analiz/fable5-once` (başlangıç, 1494f8e) ve
`perf/analiz/fable5-sonra` (çalışma ağacı HEAD).

## 1. Özet

1. **Edge ilk kez sınandı: Chromium'la aynı davranıyor.** 288 hücrelik matris (4 motor × 4 görünüm × 3 hat × 2 sayfa × 3 koşu).
   Edge'in soğuk ilk boyaması kısıtlı hatlarda Chromium'a göre −20…+92 ms (gürültü bandı ±150 ms), LCP öğeleri birebir aynı,
   CLS 0, konsol hatası 0, sıcak ziyarette Chromium gibi önbellekten (hattan 0 bayt). Tek fark: fontun gelişiyle doğan ikinci
   LCP adayı Edge'de daha sık (aşağıda §3.4).
2. **Üretim riski bulundu ve kapatıldı: `caddy:2` yüzen etiketi.** Caddy 2.10.1 ve 2.10.2, `precompressed` yolunda Range'siz GET'e
   `206 Partial Content` dönüyor (2.9.1, 2.10.0, 2.11.7 temiz). Canlı şu an 200 dönüyor; sunucudaki bir sonraki
   `docker compose build web` hangi 2.x'i çekerse onu kullanacaktı. `Dockerfile.web` 2.11.7'ye sabitlendi (commit 158d3e1).
3. **Çerez/KVKK: vitrin hiç çerez kullanmıyor** (dört motorda çalışma zamanında 0), üçüncü taraf köken yok, analitik yok; yalnız
   teknik localStorage anahtarları (§5).
4. **Bağımlılık: hiç içe aktarılmayan 4 paket kaldırıldı** (bricolage-grotesque, ibm-plex-sans, react-query, zustand; commit 09ea27d);
   dist bayt bayt aynı (sha256, 0 fark), `npm audit` 0 zafiyet.
5. **Önbellek: sıcak ziyarette Chromium, Edge ve Firefox HTML dışında hiçbir şeyi hattan çekmiyor** (video ve poster dahil).
   Playwright WebKit (Linux/GStreamer) videoyu her ziyarette 3 kez tam indiriyor — başlıklardan bağımsız, Safari'yi temsil etmiyor (§3.5).
6. **Bu sanal makinede ekran kartı olmadığı için hero (video + `feConvolveMatrix` süzgeci + cam) ana iş parçacığında çiziliyor:**
   Lighthouse «/» 70 (TBT 2,5–2,9 sn), etkileşim gecikmeleri yüzlerce ms. Dün aynı derleme ekran kartlı Mac'te 99/100 ve canlıda
   97/99'du. Bu rapordaki mutlak «/» puanları ortam sınırıdır; önce/sonra kıyası aynı ortamda yapıldı (§2), teşhis A/B §3.6.
7. **Değişmeyenler (bilinçli):** 768/1920 genişlikte Slow 4G poster-LCP ~4,0–5,6 sn (474 KB poster, fizik; §3.7); yavaş hatta
   fontun gelişinin ikinci LCP adayı doğurması (§3.4; düzeltme önerisi var, tasarım kuralı gereği uygulanmadı); tasarım, medya ve
   metin dokunulmadı.

## 2. Önce / sonra

Kod değişiklikleri (Caddy sürüm sabitleme, bağımlılık temizliği) derleme çıktısını değiştirmez — `perf/analiz/fable5-sonra/dist-fark.txt`
boş (sha256, 0 satır fark). Bu yüzden «sonra» ölçümü bir **ikinci bağımsız kontrol**dür: aynı kritik hücreler (390 ve 1440; soğuk + sıcak;
kısıtsız, Slow 4G, Fast 3G + yeni hat kablo20) taze replikada (ayrı port, taze Caddy, taze sertifika) yeniden koşuldu. Beklenen: fark
gürültü bandında (±150 ms); gürültü bandı dışına çıkan her hücre aşağıda açıklanır.

Sonuç (`analiz/fable5-sonra/KIYAS-FABLE5.md`, 192 hücre; kontrol matrisi 113. hücrede WebKit «Page crashed» ile kesildi, aynı komutla
kaldığı yerden sürdü, veri kaybı yok): **64 FCP hücresinin 64'ü gürültü bandında** (soğuk ve sıcak; en büyük fark 96 ms, Edge 1440
kısıtsız). Gürültü bandı dışına çıkan 7 hücrenin hepsi LCP ya da tekil sıcak koşu: Edge 390/1440 Slow 4G ve 390 Fast 3G LCP
1524 → 848, 2092 → 956, 3196 → 2044 (fontun gelişinin ikinci LCP adayı, §3.4 — «sonra»da 3 koşunun ikisinde çıkmadı), WebKit 1440
LCP 3024 → 3182 ve 4430 → 1996 (WebKit LCP API'si, §3.5), sıcak FCP Edge 1440 584 → 232 ve WebKit 1440 54 → 206 (tek koşu
oynaklığı; soğuk FCP aynı). Konsol/HTTP/başarısız istek: önce 0 (576 yükleme), sonra 0 (384 yükleme).

**«/» soğuk FCP, medyan (ms): önce → sonra**

| hat | ch 390 | ch 1440 | ed 390 | ed 1440 | fi 390 | fi 1440 | we 390 | we 1440 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Kısıtsız | 156 → 148 | 280 → 284 | 212 → 200 | 428 → 332 | 98 → 85 | 96 → 96 | 135 → 143 | 149 → 136 |
| Slow 4G | 828 → 824 | 944 → 948 | 844 → 848 | 984 → 956 | 766 → 750 | 750 → 778 | 718 → 755 | 761 → 761 |
| Fast 3G | 2 064 → 2 056 | 2 208 → 2 172 | 2 044 → 2 044 | 2 188 → 2 204 | 1 999 → 1 986 | 2 005 → 1 999 | 1 995 → 1 987 | 1 994 → 1 996 |
| Kablo 20 Mbps (yalnız sonra) | 396 | 556 | 404 | 572 | 321 | 321 | 305 | 325 |

**«/» soğuk LCP, medyan (ms): önce → sonra** (390/1440'ta LCP öğesi metin; Edge'deki büyük farklar §3.4, WebKit §3.5)

| hat | ch 390 | ch 1440 | ed 390 | ed 1440 | fi 390 | fi 1440 | we 390 | we 1440 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Kısıtsız | 156 → 148 | 280 → 284 | 212 → 200 | 428 → 332 | 98 → 85 | 96 → 96 | 1 724 → 1 824 | 2 869 → 2 900 |
| Slow 4G | 828 → 824 | 944 → 972 | 1 524 → 848 | 2 092 → 956 | 766 → 750 | 764 → 778 | 2 241 → 2 329 | 3 024 → 3 182 |
| Fast 3G | 2 064 → 2 088 | 2 216 → 2 172 | 3 196 → 2 044 | 2 192 → 2 216 | 1 999 → 1 986 | 2 005 → 1 999 | 2 386 → 2 364 | 4 430 → 1 996 |
| Kablo 20 Mbps (yalnız sonra) | 396 | 556 | 404 | 1 720 | 321 | 321 | 1 461 | 2 983 |

**«/» sıcak FCP, medyan (ms): önce → sonra**

| hat | ch 390 | ch 1440 | ed 390 | ed 1440 | fi 390 | fi 1440 | we 390 | we 1440 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Kısıtsız | 208 → 228 | 204 → 212 | 116 → 144 | 584 → 232 | 55 → 53 | 69 → 62 | 127 → 81 | 54 → 206 |
| Slow 4G | 248 → 228 | 308 → 332 | 256 → 272 | 340 → 368 | 203 → 198 | 210 → 198 | 199 → 207 | 197 → 212 |
| Fast 3G | 656 → 664 | 732 → 732 | 672 → 688 | 772 → 772 | 612 → 606 | 616 → 617 | 618 → 614 | 626 → 621 |
| Kablo 20 Mbps (yalnız sonra) | 124 | 200 | 172 | 232 | 85 | 79 | 98 | 99 |

**«/yontem» soğuk FCP (= LCP), medyan (ms): önce → sonra**

| hat | ch 390 | ch 1440 | ed 390 | ed 1440 | fi 390 | fi 1440 | we 390 | we 1440 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Kısıtsız | 152 → 160 | 192 → 180 | 212 → 188 | 240 → 248 | 160 → 143 | 171 → 156 | 245 → 203 | 218 → 266 |
| Slow 4G | 1 244 → 1 176 | 1 196 → 1 216 | 1 256 → 1 244 | 1 260 → 1 252 | 1 195 → 1 228 | 1 194 → 1 214 | 1 317 → 1 401 | 1 346 → 1 305 |
| Fast 3G | 2 840 → 2 824 | 2 928 → 2 928 | 2 932 → 2 880 | 2 944 → 2 880 | 2 831 → 2 940 | 2 912 → 2 879 | 2 981 → 3 011 | 2 927 → 3 024 |
| Kablo 20 Mbps (yalnız sonra) | 396 | 392 | 460 | 440 | 379 | 394 | 421 | 435 |

«/yontem» sıcak FCP: dört motorda 64–140 (kısıtsız), 198–285 (Slow 4G), 606–704 (Fast 3G), 128–172 (kablo20) ms; önce→sonra farkı ≤ 32 ms.

**Lighthouse 12.8.2 (replika, bu ortam; 3 koşu): önce → sonra**

| Sayfa · tür | perf (koşular) | LCP | FCP | TBT | CLS |
|---|---|---:|---:|---:|---:|
| `/` · mobil | 70 (70/71/70) → 70 (70/69/70) | 1,80 → 1,80 sn | 1,50 → 1,50 sn | 2,5–2,9 → 2,8–3,6 sn | 0 → 0 |
| `/` · masaüstü | 69 (69/69/69) → 69 (69/69/69) | 0,82 → 0,83 sn | 0,37 → 0,37 sn | 1,8–2,4 → 1,7–2,6 sn | 0 → 0 |
| `/yontem` · mobil | 99 (99/99/99) → 99 (99/99/99) | 1,80 → 1,80 sn | 1,50 → 1,50 sn | 32–101 → 43–64 ms | 0 → 0 |
| `/yontem` · masaüstü | 100 (100/100/100) → 100 (100/100/100) | 0,41 → 0,41 sn | 0,37 → 0,37 sn | 0 → 0 | 0 → 0 |

Karşılaştırma: dün aynı derleme ekran kartlı Mac'te «/» mobil 99 (TBT 68 ms), masaüstü 100; canlıda 97/99. Bu makinede «/»nin
TBT'si yalnızca yazılım çiziminden (§3.6); «/yontem» (video yok) iki ortamda da 99/100. İlk Lighthouse serisi (`lh-fable5-once-KIRLI.jsonl`)
WebKit video deneyiyle eşzamanlı koştuğu için atıldı (53–70), temiz seri yukarıda.

**Canlı (pvquant.com) Lighthouse, bu buluttan (2 koşu):** `/` mobil 56/55 (LCP 4,2 sn: TTFB 790 ms + 3,4 sn «render delay»), masaüstü
66/67, `/yontem` mobil 99/98. Bulutun çıkış vekili her isteğe gecikme ekliyor (sunucu yanıtı 160 ms ama gözlenen TTFB 790 ms) ve
ekran kartı yok; bu sayılar canlının durumunu değil bulutun ağ/çizim sınırını gösterir. Dünkü canlı ölçüm (Mac): 97/99/99, 100.

## 3. Bulgular ve kök nedenler

### 3.1 Caddy 2.10.1–2.10.2 «precompressed» → 206 (üretim riski; kapatıldı)

Replika ilk kurulumda Caddy 2.10.2 ile başlatıldı; her GET'e `206 Partial Content` + `Content-Range: bytes 0-N/N` döndü, canlı
200 dönüyordu. Tek dosyalık kökte ayrıştırma (`analiz/fable5-once/caddy-206.md`): yalın `file_server` 200; `precompressed br gzip`
206; `encode` tek başına 200; sürümler: 2.9.1 → 200, 2.10.0 → 200, 2.10.1 → 206, 2.10.2 → 206, 2.11.7 → 200. Tarayıcılar sayfayı
yine açıyor (dört motor duman sınaması), ama 206 kısmi içerik anlambilimi taşır; önbellek ve ara vekiller için güvenilmez.
Docker Hub'da `caddy:2` 20.10.2026'da 2.11.7'yi gösteriyor (digest 173b26306d71); canlı 19.10'da derlendiği için büyük olasılıkla
2.11.x. **Düzeltme:** `FROM caddy:2.11.7` (158d3e1). Bedel: Caddy güncellemesi artık bilinçli bir satır değişikliği.
Replika 2.11.7'ye alındı ve 206'lı ilk 10 dakikalık matris verisi atılıp matris sıfırdan koşuldu.

### 3.2 Edge matrisi

Edge (Chromium 155 tabanlı) Chromium 156 ile aynı yükleme yolunu izliyor: aynı LCP öğeleri (390: giriş paragrafı, 1440: h1, 768/1920:
`<video poster>`), aynı kaynak sırası, CLS 0,000 (24/24 hücre), kayma izleyicisi ≤ 2 px, konsol/HTTP/başarısız istek 0 (144 yükleme).
Soğuk FCP farkı (Edge − Chromium, medyan): «/» Slow 4G +16/+24/+40/+56 ms (390/768/1440/1920), Fast 3G −20/+4/−20/−20; «/yontem»
Slow 4G +12/+20/+64/+20, Fast 3G +92/+40/+16/+36; kısıtsız hatta +56…+148 (kısıtsız hatta yüzlerce ms'lik koşu oynaklığı var).
Hepsi ±150 ms gürültü bandında. Sıcak ziyaret: hattan 0,00 MB (390/768), 0,56 MB (1440/1920 — levha PNG'lerinin soğuk pencerede
bitmeyen kısmı), Chromium'la aynı kalıp. Etkileşim (§3.6) Chromium'la aynı düzeyde. **Edge'e özgü bir kusur bulunmadı.**

### 3.3 Önbellek başlıkları ve sıcak ziyaret

Başlıklar (replika = canlı, curl -D): `index.html` ve SPA yolları `Cache-Control: no-cache` + ETag + Last-Modified → her ziyarette
yeniden doğrulanır, değişmediyse 304 (~300 B); `assets/*` `public, max-age=31536000, immutable`; `.br/.gz` eşleri `precompressed`;
`Vary: Accept-Encoding`; HTTP/3 `alt-svc` canlıda var (replika h1/h2). `favicon.svg`, `icons.svg`, `robots.txt`, `/vitrin/og.png`
de `no-cache` ile gidiyor: hash'siz dosyalar oldukları için doğru, maliyet gerçek tarayıcıda gezinme başına bir koşullu istek (304;
başsız motorlar favicon istemediği için matriste görünmez). `icons.svg` kaynaktan hiçbir yerde istenmiyor (dist'te duruyor, zararsız).

Sıcak ziyaret (aynı bağlamda ikinci gezinme), «/», hattan geçen bayt (vekil sayacı, Slow 4G, medyan): Chromium 0,37/0,81/0,77/0,70 MB
(390/768/1440/1920; soğuk pencerede bitmeyen levha PNG'lerinin devamı), Edge 0,00/0,00/0,56/0,56, Firefox 0,00/0,00/0,00/0,00, WebKit
0,00/0,00/0,44/0,62. Kısıtsız hatta sıcak aktarım (Resource Timing): Chromium 0 KB, Edge 1 KB, Firefox 25 KB (HTML yeniden
doğrulama), WebKit 390'da 13,5 MB ve 768/1440'ta 28,7 MB — **video** (§3.5). «/yontem» sıcak: dört motorda 0–25 KB. Chromium'da
sıcak «/»te video (6,9 / 37 MB) ve poster önbellekten geliyor (aktarım 0, `encodedBodySize` tam) — dünkü raporun «video sıcak ziyarette
yeniden iniyor» notu bu ortamda doğrulanmadı (Chromium/Edge/Firefox'ta inmiyor; WebKit/Linux'ta iniyor).

### 3.4 Yavaş hatta fontun gelişi aynı paragrafı ikinci LCP adayı yapıyor (Chromium 2/18, Edge 8/18 koşu)

390 ve 1440'ta LCP öğesi metin (giriş paragrafı / h1). Kısıtlı hatta Inter Tight ~1,4–3,9 sn'de geliyor; metrik eşlemeli yedek yüzle
çizilen paragrafın metin kutuları web fontuyla biraz büyüyünce Chromium aynı öğe için yeni (daha büyük) LCP girdisi üretiyor:
Chromium 390 Slow 4G 832 → 1576 ms (1/3 koşu), 1440 Fast 3G 2208 → 3988 (1/3); Edge 390 Slow 4G 844 → 1700 ve 828 → 1524 (2/3),
Fast 3G 2044 → 3196, 2056 → 3324 (2/3), 1440 Slow 4G 984 → 2092, 1036 → 2288 (2/3). Lighthouse mobil «/» LCP'sinin iki gündür
tam 1,80 sn (FCP 1,50) çıkması da aynı mekanizma: LCP = fontun gelişi. Kullanıcı metni ilk boyamada görüyor; değişen yalnız ölçülen
LCP. **Düzeltme adayı (uygulanmadı):** yedek yüzün `size-adjust`'ını son metin kutusu web fontununkinden küçük kalmayacak şekilde
%1–2 büyütmek (web.dev'in önerdiği yol) — satır kırılımı değişirse K4'teki 0–2 px kayma geri gelir; «tasarım/yazı ölçüsü dokunulmaz»
kuralı ve ölçülmemiş kayma riski nedeniyle bu turda yapılmadı, yerel oturumda piksel kıyasıyla denenebilir.

### 3.5 WebKit (Linux, Playwright): video önbelleği ve LCP API'si

- **Video:** `olc/iz/webkit-video-onbellek.mjs` — kendi HTTP sunucusuyla dört başlık çeşidi (Caddy'nin aynısı / `Vary` yok /
  `Accept-Ranges` yok / `no-store`), aynı bağlamda iki açılış, sunucu tarafında sayılan bayt: WebKit 37 MB'lık dosyayı her açılışta
  3 kez istiyor (200 tam + iki `206 10984-son`, 112 MB), ikinci açılışta aynı; `Accept-Ranges` olmadan 2 × 200 (75 / 43 MB).
  Chromium ve Firefox: ilk açılış tek 206, ikinci açılış 0 istek (önbellek); `no-store`da Chromium yeniden indiriyor (beklenen).
  Sonuç: başlıklar doğru; davranış Linux WebKit'in (GStreamer) medya yoluna özgü, Safari'nin (AVFoundation) değil. Gerçek Safari'de
  sıcak ziyaret video baytı ölçülmedi (yapılamadı; yerel oturum listesi §7).
- **LCP API'si:** WebKit h1/paragrafı ilk boyamadan ~1,7–5,5 sn sonra ikinci kez (alan +%1,7) bildiriyor; hareket azaltmada
  (video yok) ve font geldikten sonra da (`olc/iz/hero-zaman.mjs`) → font/video değil, WebKit'in LCP uygulaması. Dün Mac'te de
  görülmüştü (390'da 519 ms). WebKit için kriter FCP: «/» soğuk 135/136/149/132 ms (kısıtsız), 718/739/761/748 (Slow 4G),
  1995/1995/1994/1974 (Fast 3G) — Chromium ve Firefox'la aynı bant.
- **Kart görselleri:** WebKit Resource Timing levha PNG'leri için 0 bayt/0 süre bildiriyor (yüklenmiyor değil; `hero-zaman` 8/8
  src'nin 741 ms'de verildiğini gösterdi). Özet tablolarındaki WebKit «aktarım» bu yüzden PNG'leri saymaz.

### 3.6 Ekran kartsız çizim: hero'nun ana iş parçacığı maliyeti (teşhis)

Bu makinede dört motor da yazılımla birleştiriyor. Lighthouse «/» TBT 2,5–2,9 sn (mobil benzetimi), 1,8–2,4 sn (masaüstü);
«/yontem» 0–101 ms. Etkileşim (`olc/etkilesim.mjs`, kısıtsız, sıcak; menü açma girdi→kare, boşta/kaydırma kare p95):

| Motor | 390: menü / boşta p95 / kaydırma p95 | 1440: menü / boşta p95 / kaydırma p95 |
|---|---|---|
| Chromium | 124–317 ms / 200–217 / 283–333 | 1095–1243 / 1033–1183 / 600–1483 |
| Edge | 115–299 / 167–200 / 167–200 | 1061–1113 / 550–1067 / 633–1317 |
| Firefox | 113–129 / 17,3 / 50–67 | 328–405 / 17,3 / 266–267 |
| WebKit | 655–788 / 22–24 / 676–823 | 1147–1314 / 1201–1485 / 280–470 |

Firefox'ta WebGL tuvali yazılım GL'de hiç kurulmuyor (`failIfMajorPerformanceCaveat`; `yazilim-ff.txt`: «gizli/css», boşta 16,4 ms
ortanca, kilitlenme yok, 7 günlük kayıt yazılmıyor) — Linux'ta geri dönüş yolu doğrulandı; ekran kartlı Linux/Windows yolu bu
makinede sınanamadı.

Payların ayrıştırması (A/B, `olc/ab-boya.mjs`, aynı sayfada yük sonrası değişken; 5 sn boşta, video oynarken; kare p95 ms / süreç
ağacı CPU çekirdek; 2 koşu; `analiz/fable5-once/ab`):

| Motor · görünüm | mevcut | süzgeçsiz (video+poster `filter:none`) | camsız (`backdrop-filter:none`) | süzgeçsiz+camsız | video durgun |
|---|---|---|---|---|---|
| Chromium 1440 | 767 / 667 ms · 1,4–1,6 | **67 / 67 · 1,4** | 633 / 683 · 1,6–1,8 | 50 / 50 · 1,4 | 17 · 0,2 |
| Chromium 390 | 200 / 233 · 1,2–1,4 | **17 / 17 · 0,6–0,8** | 183 / 233 · 1,2 | 17 / 17 · 0,4–0,6 | 17 · 0,0–0,2 |
| WebKit 1440 | 22 / 21 · 3,0–3,2 | 22 / 22 · 3,2–3,4 | 23 / 22 · 3,4 | 24 / 21 · 3,2–3,4 | 17 · 0,2 |
| WebKit 390 | 22 · 3,2 | 20 · 3,2 | 24 · 3,2 | 23 · 3,0 | 17 · 0,2 |

Yazılım çiziminde Chromium'un kare süresinin > %90'ı videodaki `feConvolveMatrix` süzgecinden (süzgeç kalkınca 767 → 67, 200 → 17
ms; cam tek başına 767 → 633); WebKit'te kare süresi iyi (22 ms) ama CPU 3 çekirdek, süzgeçten bağımsız → yazılım video çözme
(GStreamer). Dün ekran kartlı Mac'te aynı süzgeç Chromium'da ücretsizdi (kaydırma p95 18–19 ms); yani bu, ekran kartı
hızlandırması olmayan ortamlara (kapalı ayar, uzak masaüstü, sanal makine, eski entegre GPU'lu sürücü kara listesi) özgü bir maliyettir.
Bu sayılar ekran kartı olan gerçek cihazları temsil etmez (dün Mac'te Chromium 1440 kaydırma p95 18–19 ms). Ekran kartı
hızlandırması kapalı masaüstü tarayıcıları ve uzak masaüstü oturumları için gerçek bir maliyet göstergesidir; «süzgeç/animasyon
kaldırılmaz» kuralı gereği düzeltme yapılmadı, öneri §8.

### 3.7 768 ve 1920 genişlikte poster-LCP (değişmedi, fizik)

Chromium/Edge 768 Slow 4G LCP 4476/4468 ms, 1920 5636/5588 (başsız yazılım taraması dünkü gibi ~0,6–0,9 sn şişiriyor; ekran kartlı
Chrome'da dün 4,0 sn). 474 KB poster 1,6 Mbps'te tek başına 2,3 sn; istek ilk boyama bildiriminden sonra (~0,86 sn) başlıyor. Posteri
yalnız bu genişliklerde HTML ayrıştırılırken başlatmak LCP'yi en iyi ~3,2 sn'ye çeker (≤ 2,5 yine karşılanmaz), FCP'yi ~0,5 sn
geriletir, 1440'ta metin LCP'sini bozar, görünüme bağlı bir istisna ekler. Deney yapılmadı; poster baytı ve hero kompozisyonu sahip
kuralıyla sabit.

## 4. Commit bazlı değişiklikler

| Commit | NE | NEDEN / KANIT | Risk |
|---|---|---|---|
| 158d3e1 | `Dockerfile.web`: `caddy:2` → `caddy:2.11.7` | 2.10.1–2.10.2 precompressed → 206 (`caddy-206.md`); canlı 200, gelecek derleme riski | Güncelleme artık elle |
| 09ea27d | `web/package.json`: 4 kullanılmayan paket kaldırıldı | 0 içe aktarma; dist sha256 fark 0; npm test 71/71, tsc 0 | Yok |
| 2114bb0, e9ab082, cd88ccf, 8029829, f36e853… | perf araçları ve veriler (Edge motoru, hedefler, envanterler, zincir) | — | — |

Kod değişikliği olmayan, ölçümle kapatılan konular: Edge, önbellek başlıkları, sıcak ziyaret, çerez/KVKK, INP laboratuvarı, Firefox/Linux
WebGL geri dönüşü, 768 poster-LCP.

**Kapılar (web/, ayrı çıkış kodları, 20.10 14:36):** `npm test` 0 (71/71), `npx tsc --noEmit -p tsconfig.app.json` 0, `npm run build` 0
(2,7 sn), `npx oxlint src/features` 0 (2 önceden var olan uyarı: `sayfalar/parcalar.tsx` fast-refresh; bu turda dokunulmadı).
Python: kaynak değişmedi; CI (`.github/workflows/ci.yml`, PR #7) `test` ve `web` işleri her commit'te yeşil (2114bb0 … 4675cba).
Dağıtım YAPILMADI (bulutta ssh yok): canlıya alma yerel oturumda (`git pull && docker compose build web && docker compose up -d`,
sonra `curl -I` ile 200 ve Caddy sürümü). UI'ye dokunulmadığı için tasarım skill'i ve piksel kıyası bu turda gerekmedi.

## 5. Çerez / KVKK envanteri

Kaynak taraması + çalışma zamanı (dört motor, «/» ve «/yontem», 8 sn + kaydırma; `cerez-kvkk.md`, `cerez-sina.txt`): **çerez 0**,
`Set-Cookie` yok (`/`, `/v1/dogrulama`), üçüncü taraf köken yok (fontlar kendi sunucudan, analitik yok). localStorage: anonim
vitrin ziyaretçisinde yalnız `pvq_yavas_hat` (poster hız kararı, 7 gün) ve Firefox + yazılım birleştirmede `pvq_keskin_yazilim`
(7 gün); giriş sonrası `pvq_token`, `pvq_plant`, `pvq_tema`; sessionStorage `pvq_parca_yenile` (parça yükleme hatası kilidi).
Hiçbiri kişisel veri/izleme değil; KVKK çerez bildirimi gerektiren bir öğe yok.

## 6. Bağımlılık envanteri

`npm audit --omit=dev` 0 zafiyet. Kaldırılan (0 içe aktarma): `@fontsource-variable/bricolage-grotesque`, `@fontsource/ibm-plex-sans`,
`@tanstack/react-query`, `zustand` (5 paket; dist aynı). Güncel olmayanlar (güncellenmedi — ölçülmüş kazanç yok, derleme zinciri
değişince piksel doğrulaması baştan gerekir): react/react-dom 19.2.8 → 19.3.1, vite 8.2.0 → 8.3.4, @vitejs/plugin-react 6.0.5 → 6.1.2,
oxlint 1.76 → 1.89, typescript 6.0.3 (7.0.2 var), @types/*. Üretim imajları: `node:20-alpine` (derleme), `caddy:2.11.7` (artık sabit).

## 7. Yapılamayanlar (bu bulutta) ve yerel oturum listesi

| Hedef | Neden | Yerine |
|---|---|---|
| Gerçek Safari (macOS), iOS Safari | Yok | Playwright WebKit 27.2 (Linux/GStreamer; medya yolu farklı) |
| Firefox Windows/Linux ekran kartlı WebGL | Ekran kartı yok | Yazılım GL geri dönüşü doğrulandı |
| Ekran kartlı Lighthouse/etkileşim | Ekran kartı yok | Dünkü Mac verisi (REPORT.md) + bu ortamda önce/sonra |
| Canlı Lighthouse (temsilî) | Bulut çıkış vekili TTFB 790 ms | Replika; dünkü canlı 97/99 |
| HTTP/3 | Replika h1/h2 | — |
| Saha verisi (CrUX/INP) | Anahtar yok; site CrUX eşiğinin altında olabilir | Laboratuvar etkileşim ölçümü |
| Dağıtım (`ssh root@…`) | ssh anahtarı yok | Yerel oturum |
| Bulut kullanım/kredi düşümü | **Doğrulanamadı** — claude.ai kullanım sayfasından teyit edilmeli | — |

Yerel oturumda (10 dk): Safari'de «/» iki kez aç → Web Inspector Network: ikinci açılışta `.mp4` isteği var mı (§3.5); Chrome DevTools
Performance'ta «/» Slow 4G: paragraf LCP'si fontun gelişinde mi (§3.4); `docker compose build web` sonrası `docker image inspect` ile
Caddy 2.11.7; `curl -I https://pvquant.com/ -H 'Accept-Encoding: br'` → 200.

## 8. Öneriler (uygulanmadı)

1. Yedek yüz `size-adjust` ayarı (§3.4) — piksel kıyasıyla denenmeli.
2. Ekran kartı hızlandırması kapalı tarayıcılar için Chromium/WebKit'te de «ilk saniye kare sınaması → CSS süzgecini kaldır» (Firefox K12
   kalıbı) — süzgeç tasarım kararı olduğu için sahibin onayı gerekir.
3. `favicon.svg`/`robots.txt`/`og.png` için kısa `max-age` (ör. 1 saat): gezinme başına bir 304 eksilir; görünür etkisi yok.
4. Güncel olmayan paketler ayrı bir turda, piksel doğrulamasıyla.
5. Caddy sürümü artık sabit: güncellemeyi (changelog + replika sınaması) takvime bağlamak.

## 9. Bulut kullanımı

Bu oturumun kredi/kullanım düşümü bu ortamdan okunamadı — **doğrulanamadı**; kullanıcı claude.ai kullanım sayfasından teyit edecek.
Ölçüm süreleri (duvar saati): başlangıç matrisi 72 dk (288 hücre; 206'lı ilk 10 dk atıldı), etkileşim 20 dk, Lighthouse 4 seri × ~5 dk,
kontrol matrisi 47 dk (192 hücre), A/B 10 dk; toplam ~3,5 saat sıralı ölçüm.
