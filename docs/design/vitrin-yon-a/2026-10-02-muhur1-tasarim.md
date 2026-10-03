# Vitrin Yön A "Kanıt Masası" — Mühür 1: ana sayfa (tasarım)

**Tarih:** 02.10.2026
**Durum:** kullanıcı onayladı (sıralama, onay akışı, yaklaşım, bölüm 1–3)
**Taban:** `1b34e37` (v2.383)

**Dayanak:** `~/Desktop/vitrin-tasarim-arastirmasi/`
- `YON_ONERILERI.md` "Yön A"
- `IA_VE_KURGU.md` §3–§5
- `numuneler/yon-a.html`
- `PVQUANT_ENVANTER.md`

## 0. Kararlar

| konu | karar |
|---|---|
| yön | A "Kanıt Masası" |
| sıralama | **Mühür 1** ana sayfa, bugünkü verilerle → **Mühür 2** canlı referans eğrisi ucu → **Mühür 3** mega-menü, alt sayfalar, SEO |
| onay akışı | Yerel önizleme (masaüstü + mobil ekran görüntüsü) → kullanıcı onayı → `vN.NNN` Türkçe commit + push + CI yeşili. Canlıya dağıtım bu oturumun dışında. |
| yaklaşım | `Vitrin.tsx` bileşenlere bölünür; satır içi stil yerine `.vt` kapsamlı sınıf ve token |
| görsel sistem | §2 (bölüm 1 onayı). Kart kalıbı değişikliği, IA §9 madde 8'in onayıdır. |
| kurgu | §3 (bölüm 2 onayı): yeni giriş cümlesi, 25,4 bin TL dipnotu kalkar, dalga ve yıldız süsleri kalkar |
| bileşen ve veri | §4–§6 (bölüm 3 onayı) |

## 1. Kapsam

**Değişir:**
- `web/src/features/vitrin/`: vitrin ve `/yontem`.
- `web/src/index.css`: yalnız font yükleme satırı.
- `web/index.html`: Google preconnect satırları.
- `web/package.json`: font paketleri.

**Değişmez:** panel ekranları, `App.tsx` yönlendirme mantığı, API ve backend, Python testleri, rapor üretimi.

**Kapsam dışı (Mühür 2–3):**
- canlı eğri (`GET /v1/vitrin/referans-egri`) ve grafiğin canlı kipi;
- ürün turu penceresi;
- mühendislik disiplini sayıları (`vitrin-veri.json`);
- EPİAŞ bağlama bölümü;
- mega-menü ve alt sayfalar;
- ön-çizim, `robots.txt`, `sitemap.xml`;
- paylaşım görseli `og.png`.

### 1.1 Bağlayıcı kurallar (her metin ve her mühürde)

- **Gizlilik Anayasası** (`docs/design/CLAUDE.md`):
  - Ekranda görünen hiçbir metinde şunlar geçmez: Erbs · Perez · Faiman · Barhdadi · ModelSelector · calibrate() ·
    predict() · eta_bos · bifacial · BG= · η= · Open-Meteo · "literatür katsayıları".
  - Meteoroloji kaynağı yalnız "profesyonel meteoroloji verisi" diye anılır. Kaynak adı yalnız üç atıf yerinde
    geçebilir; vitrin bunlardan biri değil.
  - Mühür 2'deki canlı eğri künyesi de bu kurala tabidir: NWP model adı yazılmaz.
- **Kullanıcının vitrin kararları:**
  - "Sayılar canlı API'den çekilir, elle yazılmaz"; uydurma yedek sayı yok.
  - Statik ekran görüntüsü yok (v2.347).
  - Görünür e-posta adresi yok; yalnız form.
  - KVKK metni yazılmaz (hukukçu bekleniyor).
  - `/guvenlik` sayfası önerilmez (iptal edildi).
  - Referans santral yalnız "Referans santral · 10 MW üzeri · İç Anadolu" diye anılır: MW, ad, koordinat yok.
  - Kurumsal B2B dil.

## 2. Görsel sistem

### 2.1 Fontlar

**Vitrin ve `/yontem`:** IBM Plex Sans 400/500/600 ve IBM Plex Mono 400/500, `@fontsource` paketlerinden (SIL OFL).

**Google yükleme yolu tamamen kalkar:**
- `web/src/index.css` içindeki Google Fonts `@import` satırı silinir.
- `web/index.html` içindeki iki `preconnect` satırı silinir.

**Panelin fontları:**
- Aynı aileler, aynı eksen ve ağırlıklarla `@fontsource` paketlerinden gelir: Inter opsz 14–32 ve wght 400–700, Space Grotesk 500/600, IBM Plex Mono 400/500/600.
- Panelin görünümü değişmez.
- Gerekçe: vitrin ve panel tek CSS paketini paylaşıyor. `@import` kalırsa vitrin ziyaretçisi de Google'a istek atar ve KVKK kazancı boşa çıkar.
- Bir eksen ya da ağırlık paket olarak bulunamazsa panel o aile için değiştirilmez ve durum kullanıcıya bildirilir.

**Yükleme davranışı:** Font dosyası ancak o aile çizildiğinde iner; `font-display: swap`.

### 2.2 Renk token'ları

Token'lar `.vt` kök sınıfında tanımlanır, panele sızmaz. Kontrastlar WCAG 2.x formülüyle ölçüldü.

| token | değer | ölçüm |
|---|---|---|
| `--vt-zemin` | `#FFFFFF` | |
| `--vt-bant` | `#F2F5F3` | |
| `--vt-metin` | `#0F1E19` | zeminde 17,21; bantta 15,68 |
| `--vt-ikincil` | `#4A5852` | zeminde 7,48; bantta 6,81 |
| `--vt-kenar` | `#D8E0DB` | süs; tek başına bileşen sınırı değil |
| `--vt-kenar-guclu` | `#B9C5BF` | çizgili düğme kenarı; düğmeyi metni tanıtır |
| `--vt-alan-kenar` | `#7A8781` | form alanı kenarı: zeminde 3,74, bantta 3,41 (WCAG 1.4.11 eşiği 3:1) |
| `--vt-eylem` | `#0E7C5A` | bağlantı: zeminde 5,19, bantta 4,72; beyaz düğme metni 5,19 |
| `--vt-gece` | `#0B1424` | panelin koyusu; sayfadaki tek koyu bant |
| `--vt-gece-kart` | `#17243C` | |
| `--vt-gece-metin` | `#F4F8FD` | gecede 17,28; kartta 14,54 |
| `--vt-gece-ikincil` | `#A9B7C9` | gecede 9,04; kartta 7,61 |
| `--vt-gece-eylem` | `#3FB489` | bağlantı gecede 7,11; üstündeki `#0B1424` düğme metni 7,11 |
| `--vt-gece-kenar` | `rgba(255,255,255,.10)` | |
| `--vt-veri-tahmin` | `#2D6FB5` | zeminde 5,18 |
| `--vt-veri-gerceklesen` | `#C27803` | zeminde 3,51 (çizgi eşiği 3:1) |
| `--vt-veri-sinir` | `#5C6880` | zeminde 5,60; kesikli çizgi |

**Kurallar:**
- Eylem rengi yalnız düğme, bağlantı ve odak halkasında kullanılır. Başlık vurgusu ve bölüm süsü olmaz.
- Amber yalnız "gerçekleşen" anlamına gelir.
- Bugünkü "TL" ve "karneye" amber vurguları, amber başvuru düğmesi ve amber altın süsler kalkar.

### 2.2-ek — R16: V1 "Mürekkep & Güneş" kimlik takası (03.10.2026, kullanıcı talimatı)

Kullanıcı görsel keşif varyantlarından V1'i seçti ("Şimdi V1 olduğu gibi yapalım"). Bu ek, §2.1–2.3 ve
§2.5'in YALNIZ renk/tipografi/köşe değerlerini değiştirir; §1.1 bağlayıcı kuralları, §2.2 "Kurallar"
bloğu, bölüm kurgusu ve dürüstlük ilkeleri aynen yürürlüktedir. Kaynak: görsel keşif teslimi
(PALETLER.md V1 tablosu); aşağıdaki ölçümler bu depodaki değerlerle yeniden hesaplandı (WCAG 2.x).

| token | değer | ölçüm |
|---|---|---|
| `--vt-zemin` | `#FFFFFF` | |
| `--vt-bant` | `#F3F5F9` | |
| `--vt-metin` | `#0B1B3C` | zeminde 16,99; bantta 15,56 |
| `--vt-ikincil` | `#4A5974` | zeminde 7,07; bantta 6,47 |
| `--vt-ucuncul` | `#56647F` | zeminde 5,96 (künye/gök etiketi) |
| `--vt-kenar` | `#E3E8F0` | süs; tek başına bileşen sınırı değil |
| `--vt-kenar-guclu` | `#C9D1E0` | çizgili düğme kenarı; düğmeyi metni tanıtır |
| `--vt-alan-kenar` | `#56647F` | form alanı kenarı: zeminde 5,96, bantta 5,46 (eşik 3:1) |
| `--vt-eylem` | `#B11F47` | beyaz düğme metni 6,65; bağlantı zeminde 6,65, bantta 6,10 |
| `--vt-eylem-koyu` | `#8F1838` | dolu düğme hover zemini; beyaz metin 8,91 |
| `--vt-gece-ust/-gece/-alt` | `#09152F/#0B1B3C/#0E2046` | koyu bant dikey gradyanı (düz renk yerine) |
| `--vt-gece-kart` | `#17264A` | |
| `--vt-gece-metin` | `#F4F7FC` | gradyan uçlarında 16,86/14,89; kartta 13,84 |
| `--vt-gece-ikincil` | `#AEBBD3` | gecede 8,78; kartta 7,68 |
| `--vt-gece-eylem` | `#EF7396` | gül: ok/odak halkası; gradyanda 6,52–5,76, kartta 5,35 |
| `--vt-gunes` | `#FFB4A2` | YALNIZ illüstrasyon (gök şeridi diski, logo) — arayüz rengi değil |
| `--vt-veri-tahmin/-gerceklesen/-sinir` | `#2D6FB5/#C27803/#56647F` | 5,18 / 3,51 (çizgi eşiği 3:1) / 5,96 — sözleşme değişmedi |

Tipografi ve kalıp farkları:
- Başlıklar (h1–h3) `--vt-baslik`: **Bricolage Grotesque Variable** (`@fontsource-variable/bricolage-grotesque`,
  SIL OFL, opsz ekseni); gövde/mono aileleri ve §2.3 boyut tablosu aynen.
- Düğme köşesi 6 px → **12 px**; dolu düğme hover'ı parlaklık yerine `--vt-eylem-koyu` zemin.
- Koyu banttaki dolu düğme ahududu kalır + `inset 0 0 0 1px rgba(255,255,255,.32)` iç kenar;
  koyu bantta bağlantı metni beyaz, yalnız ok ve odak halkası gül.
- Hero'nun üstünde `GokSeridi` (statik güneş-yükseklik yayları, 38° K; aria-hidden + mono künye;
  masaüstü/mobil SVG CSS ile seçilir). Tek sayısal içerik ilkesine aykırı değil: eksen/sayı yok.
- Marka işareti: ahududu kare yerine V1'in ufuk+yay+güneş diski işareti (mürekkep çizgi + `--vt-gunes` disk).

### 2.2-ek-2 — R18/R19: V1 yapısal genişleme (03.10.2026, kullanıcı kararı)

Kullanıcı V1 taslağını dalla karşılaştırıp Mühür 1'in yapıyı da almasına karar verdi; §1'deki
"mega-menü Mühür 3" ertelemesi ve §3.2/§4'teki "temsili eğri, eksen/sayı/tarih yok" tanımı bu ekle
geçersizdir. Fiyatlandırma ve Hakkında SAYFALARI hâlâ kapsam dışıdır.

**R18 — mega menü ve dürüst bağlantı kuralı.** Üst çubuk IA §3 düzenine geçer: Ürün ▾, Doğruluk ▾,
Türkiye piyasası ▾ (açılır), Fiyatlandırma (düz → `#basla`), Hakkında ▾. Yapraklar yalnız bugün var
olan yüzeye bağlanır (`#karne`, `/yontem`, `/yontem#yt-tanimlar`, `/yontem#yt-disiplin`, `#para`,
`#basla`, `#ilkeler` — altbilgiye eklendi). Yalnız panelde yaşayan özellikler (Ürün ▾'nin tamamı,
"Veri kaynakları ve lisanslar") bağlantısız tanıtım girdisidir ve mono "Panelde" künyesi taşır;
hiçbir yerde yüzeyi olmayan girdi (Sürüm günlüğü) menüye girmez — vitrin vaat etmez. Görünür menü
metinlerinde kaynak/kitaplık adı geçmez (Gizlilik Anayasası; gizlilik testi pvlib/gefs/ecmwf/
sarah/pvgis/nasa/nwp desenlerini tarar). Etkileşim: tıkla-aç (hover değil), tek panel açık, Esc
düğmeye odak iade ederek kapatır, nav dışına tık/odak ve çapa değişimi kapatır, ≤1080'de kırılım
kapatır, arka plan `rgba(11,27,60,.4)` örtüyle kararır; ≤1080 çekmece düz gerçek bağlantı listesi kalır.

**R19 — hero gerçek numune grafiği.** Temsili eğri kalkar; hero 01.10.2026 araştırma koşusunun
GERÇEK sayılarını çizer (`numuneGun.ts`; kaynak: vitrin tasarım araştırması `numune_veri.json` —
gerçekleşen EPİAŞ Şeffaflık, bant/P50 o gecenin koşusu, kapasiteye oran). Dürüstlük araç değiştirir:
sayı gizlemek yerine açık künye — "araştırma koşusu, canlı panel çıktısı değil". Eksenler, AC tavanı,
08:00–12:00 açıklaması, saat ortası damga sözleşmesi (değer saat ortalaması, nokta saat+0,5'te),
"Tablo görünümü" (details, tek ondalık) ve ≤600 px'te dar geometrili ikinci SVG (eksen yazısı
~10 px altına inmez). Künyede hava modeli adı geçmez ("01.10 gece koşusu, PVQuant fizik modeli").
Kapalı karne kilitli karta (kilit + KISA_TANIMLAR 2×2, tek kaynak), altbilgi Doğruluk sütunlu
haritaya genişler; birincil CTA'larda ok (`--ok`, erişilebilirlikte gizli). Sayfalar arası çapalar
ilk çizimden sonra `useCapaKaydir` ile hedefe kaydırılır.

### 2.3 Tipografi

| rol | masaüstü | ≤ 600 px | yazı |
|---|---|---|---|
| h1 | 56/64, 600, −0,01em | 36/42 | Plex Sans |
| h2 | 36/44, 600 | 26/32 | Plex Sans |
| h3 | 20/28, 600 | 20/28 | Plex Sans |
| giriş paragrafı | 20/30 | 18/28 | Plex Sans, ikincil renk |
| gövde | 17/27 | 16/25 | Plex Sans |
| sayı | 40/44, 500 | 32/36 | Plex Mono, `tabular-nums` |
| künye | 12/16 | 12/16 | Plex Mono, ikincil renk |

Büyük harfli mono "kaş" etiketleri kalkar. Bölüm başlığı doğrudan h2 ile başlar.

### 2.4 Izgara ve ritim

- **Kapsayıcı:** en çok 1200 px içerik; yan boşluk 32 px (> 1080), 24 px (600–1080), 20 px (< 600).
- **Bölüm dikey boşluğu:** 96 / 72 / 56 px. İnce şeritlerde (kanıt şeridi) 48 px.
- **Kırılım noktaları:** 1080 (menü çekmeceye geçer, ızgaralar daralır) ve 600 (tek sütun).
- Yatay taşma hiçbir genişlikte olmaz.

### 2.5 Bileşen kalıpları

- **Düğme:**
  - 44 px yükseklik, 6 px köşe, 600 ağırlık.
  - Dolu: eylem rengi, beyaz metin.
  - Çizgili: `--vt-kenar-guclu` kenar, metin rengi.
  - Hover'da hafif parlaklık; `:focus-visible`'da 2 px eylem renginde halka, 2 px boşluk.
- **Metin bağlantısı:** eylem rengi, 600 ağırlık, sonunda " →"; hover'da alt çizgi.
- **Kart:**
  - 10 px köşe, gölge yok, kenar yok.
  - Beyaz bölümde `--vt-bant` zeminli, bantlı bölümde beyaz zeminli.
  - İçerik: mono numara (`01`), h3 başlık, tek cümle.
  - Renkli üst kenar ve ikon kullanılmaz.
- **Künye:** mono 12, ikincil renk. Verinin kaynağını söyler.
- **Durum çipi:** mono 11,5, yuvarlak kenarlı, ikincil renk ve nokta. Örnek: "yayın kapalı".

### 2.6 Hareket

- Yalnız düğme ve bağlantı geçişleri, 150 ms.
- `prefers-reduced-motion: reduce` altında geçiş yok.
- Kart kaldırma (hover'da yukarı kayma) yok.

## 3. Sayfa kurgusu

Mevcut çapalar korunur, çünkü dışarıdan verilmiş bağlantılar kırılmasın: `#katmanlar`, `#para`, `#karne`, `#sss`,
`#basla`. Metinlerde **hitap "siz"**.

### 3.1 Üst çubuk

- **Masaüstü (> 1080 px):**
  - Yapışkan, 64 px, beyaz zemin, alt kenar `--vt-kenar`.
  - Solda logo: `GunesLogo` geometrisi ve "PVQuant".
  - Ortada bağlantılar: Nasıl çalışır (`#katmanlar`) · Türkiye piyasası (`#para`) · Açık karne (`#karne`) · SSS (`#sss`) ·
    Yöntem (`/yontem`).
  - Sağda çizgili "Panele giriş" (`onPanel`) ve dolu "Başvuru" (`#basla`).
- **≤ 1080 px:**
  - Logo, "Başvuru" ve "Menü" düğmesi.
  - "Menü", üst çubuğun altından ekranın dibine kadar açılan bir çekmece açar: aynı beş bağlantı ve en altta "Panele giriş".
- **`/yontem` kipi:** `App.tsx` bu sayfaya `onPanel` vermez; yönlendirme değişmez.
  - Sayfa içi bağlantılar ana sayfaya gider (`/#katmanlar` …).
  - "Başvuru" `/#basla`'ya gider.
  - "Panele giriş" yerine "← Ana sayfa" bağlantısı çıkar.

### 3.2 Hero

- **Düzen:** iki sütun, metin 5/12, grafik 7/12. ≤ 1080 px'te grafik metnin altına iner.
- **h1:** "Kanıtla konuşan üretim tahmini."
- **Giriş paragrafı:** "Her saat için bir aralık, her ay için bir iklim beklentisi, her gece gerçekleşenle karşılaştırılan bir karne.
  Vaat değil, ölçüm."
- **Eylemler:** dolu "Karnenizi başlatın" (`#basla`) ve metin bağlantısı "Açık karneyi inceleyin" (`#karne`).
- **Grafik penceresi** (`ReferansEgri`, `veri = null` → temsili kip):
  - **Başlık satırı:** "Referans santral · 10 MW üzeri · İç Anadolu". Tarih yok.
  - **Lejant:** Tahmin (P50) · İyimser–kötümser aralık (P10–P90) · Gerçekleşen · AC tavanı.
  - **Çizim:** sabit, sentetik bir gün şekli. Tahmin bandı %12 yıkamalı; P50 2 px `--vt-veri-tahmin`; gerçekleşen 2 px
    `--vt-veri-gerceklesen` (sabah bulutlu, sonra banda giren bir şekil); AC tavanı kesikli.
  - **Ek yok:** eksen sayısı, saat etiketi, tarih, ipucu ya da "canlı" rozeti yoktur.
  - **Künye:** "temsili eğri — gerçek eğri yayın açılınca burada".
  - **Erişilebilirlik:** `role="img"` ve başlık/açıklama metni ("Temsili çizim; gerçek veri değildir").

### 3.3 Canlı kanıt şeridi

Bant zeminli ince şerit. Veri `/v1/dogrulama`'dan gelir (§4.2).

- **Açık:** dört kutu.

  | etiket | değer | alt satır |
  |---|---|---|
  | "Ortalama sapma · son {pencere_gun} gün" | `%{wmape_pct}` | "üretime ağırlıklı saatlik hata" |
  | "Basit yönteme göre" | `%{beceri_naif_pct}` | "daha az hata" |
  | "Bant kapsaması · hedef %{bant_hedef_pct}" | `%{bant_kapsama_pct}` | "gerçekleşen, söylenen aralıkta kaldı" |
  | "Sınav günü" | `{pencere_gun}` | "her gece bir sınav" |

  - Altında künye: "GET /v1/dogrulama · güncelleme {son_gun}".
  - Bir alan `null` ise o değerin yerinde "—" ve "henüz hesaplanmadı" yazar. Uydurma yedek değer yazılmaz.
- **Kapalı:**
  - Tek kart: durum çipi "yayın kapalı".
  - Cümle: "Açık karne yayını kapalı. Referans santral 30 sınav gününü doldurunca sayılar burada kendiliğinden görünür."
  - "yayın açılınca" etiketi ve dört alan adı.
  - Sağda "Yöntemi okuyun" (`/yontem`).
  - Kutu ve tire çizilmez.
- **Yükleniyor:** dört iskelet çizgi; tire yok.
- **Hata** (uç yanıt vermedi): "Karne şu an alınamadı; sayfa yenilenince yeniden denenir." ve "Yöntemi okuyun".

### 3.4 Dört adım (`#katmanlar`)

**h2:** "Tahmin dört adımda doğar — her adımı panelde görünür."

**Kartlar** (cümleler bugünkü `KATMANLAR`'dan aynen):

| no | başlık | cümle | etiket |
|---|---|---|---|
| 01 | Fizik modeli | Santralın geometrisinden yola çıkar — panel eğimi, tavan, kayıplar. | Panelde: Kalibrasyon |
| 02 | Öğrenen model | Fiziğin gözden kaçırdığını santralın kendi geçmişinden öğrenir. | Panelde: Kalibrasyon |
| 03 | Dürüst aralık | Tek sayı değil, gerçek hatayla ayarlanmış iyimser–kötümser bandı verir. | Panelde: Tahminler |
| 04 | Gece karnesi | Her gece tahmin gerçekleşenle yüzleşir; kanıt birikir. | Panelde: Doğruluk |

- "Panelde: …" etiketi düz metindir; alt sayfalar Mühür 3'te gelince bağlantı olur.
- **Düzen:** 4 sütun (> 1080), 2×2 (600–1080), tek sütun (< 600).

### 3.5 Türkiye piyasası (`#para`, bant zeminli)

- **h2:** "Sapma burada soyut değil — TL yazar." Vurgu rengi yok.
- **Giriş paragrafı:** bugünkü metin aynen ("Üretim programı her gün öğleden sonra bildirilir; …").
- **Kartlar:** üç kart aynen ("Program hazır" · "Sapmanın TL kartı" · "Toplayıcıya tek tık").
- **İki masa:** "Operatör masası" ve "Ticaret masası" metinleri aynen, kart kalıbında.
- **Dipnot:** "Sahadan ölçüm: 4,5 MW … 25,4 bin TL …" **kalkar**. Yerine düz cümle: "Sapmanın TL karşılığı panelde,
  kendi santralinizin verisiyle hesaplanır."

### 3.6 Açık karne (`#karne`, `--vt-gece` zeminli tek koyu bant)

- **h2:** "Sözümüze değil, karneye bakın." Renk vurgusu yok.
- **Giriş paragrafı:** "Sistem her gece tahminini gerçekleşen üretimle karşılaştırır. Sonuç saklanmaz, süslenmez — panelde gün gün
  birikir."
- **Açık durum: Açık karne kutusu** (`--vt-gece-kart`):
  - **Başlık satırı:** "Açık karne — {santral_etiketi}". Sağında künye: "son {pencere_gun} gün · güncelleme {son_gun}".
  - **Dört değer:** PVQuant `%{wmape_pct}` ("saatlik ortalama sapma") · Basit yöntem `%{naif_wmape_pct}` ("dünü
    tekrarlar") · Sıkı referans `%{siki_referans_wmape_pct}` ("iklim + akıllı süreklilik") · Bant kapsaması
    `%{bant_kapsama_pct}` ("hedef %{bant_hedef_pct}").
    - PVQuant ve bant değerleri gece metin renginde.
    - Referans değerleri gece ikincil renginde. Yeşil ya da amber vurgu yok.
  - **Aylık tablo** (`aylar[]`): ay · sınav günü · PVQuant · basit yöntem · bant kapsaması. Mono, `tabular-nums`.
  - **Not:** `{not}` ve "Sapma yüzdeleri üretime ağırlıklı ortalamadır — küçük olan iyidir."
  - Bugünkü yinelenen "PANELDEN — CANLI SAYILAR" üçlü KPI kutusu kalkar.
- **Kapalı / hata:** kutu yerine tek satır: "Yayın kapısı kapalı. 30 sınav günü dolunca dört değer ve aylık tablo burada
  görünür." Künye: "GET /v1/dogrulama".
- **Yöntem kutusu:** her durumda görünür. Metin §3.10'daki ortak sabitten gelir: kısa dört tanım ve "Yöntemin tamamı"
  bağlantısı.
- **Bandın sonu:** dolu "Kendi karnenizi başlatın" (`#basla`) ve "Yöntemin tamamı" (`/yontem`). Bugünkü "Derine inmek ister
  misiniz?" kartı kalkar.
- **Süsler:** `Dalga` geçişi ve `YildizAlani` süsü kalkar.

### 3.7 SSS (`#sss`, beyaz zemin)

- **h2:** "Sık sorulan sorular".
- Beş soru ve cevap bugünküyle aynen (kurulum, SCADA'sız çalışma, fiyatlandırma, doğruluk, veri güvenliği).
- Açılır-kapanır `details`/`summary`; artı ve eksi işareti mono.

### 3.8 Başvuru (`#basla`, bant zeminli)

- **h2:** "Kendi karnenizi başlatın."
- **Giriş paragrafı:** bugünkü metin aynen ("E-postanızı bırakın; …").
- **Form:**
  - Mantık ve uç bugünküyle aynı: `api.vitrinBasvuru`, bal küpü `web`, durumlar.
  - Alanlar: E-posta *, Santral adı, Kurulu güç (MW).
  - Dolu eylem düğmesi "Karnemi başlat".
  - Başarı ve hata metinleri aynen; hata `role="alert"`.
  - Alt not: "Veri yüklemeniz gerekmez; e-postanız yalnız dönüş için kullanılır."
- Görünür e-posta adresi yok.

### 3.9 Altbilgi

- **Sütun 1:** logo ve "Güneş santralları için saatlik üretim tahmini — fizikten başlar, geçmişinizden öğrenir, her gece
  kendini sınar."
- **Sütun 2 "Sayfa":** Nasıl çalışır · Türkiye piyasası · Açık karne · SSS · Başvuru · Yöntem ve doğrulama · Panele giriş.
  - Bugünkü altı "PANEL" düğmesi kalkar; hepsi aynı giriş ekranına gidiyordu.
- **Sütun 3 "İlkeler":** beş cümle aynen.
- **Alt satır:** "© PVQuant 2026".

### 3.10 `/yontem` ve ortak yöntem metni

- **Sayfa:** aynı üst çubuk (yönteme özgü: logo ana sayfaya döner, "← Ana sayfa"), aynı altbilgi ve token'lar.
  - Bölümleri ve metni korunur.
  - Bugünkü şafak degradesi, gece-yeşili ve amber süsler A diline çevrilir.
- **Tek kaynak:** `yontem-metni.ts` adlı ortak modülde `ADIMLAR` (bugünkü `Yontem.tsx`'ten aynen) ve `METRIKLER` durur.
  - Karne bandının yöntem kutusu da `/yontem` da buradan okur.
  - `METRIKLER`'de üç tanım hesapla eşlenir (kaynak: `apps/worker/main.py` `gece_skill`, `ext/tahmin/dogrulama.py`
    `picp`, `services/dogrulama_service.py`):
    - **Ortalama sapma (WMAPE):** "…toplanır ve o günün toplam gerçekleşen üretimine bölünür; pencere değeri, günlük değerlerin ortalamasıdır. …" ve "Gündüz saati: gerçekleşen üretimin kurulu gücün %2'sini aştığı saat." Uygulamada düzeltildi: pencere değeri `dogrulama_service` `avg(mape)`, yani günlük WMAPE'lerin ağırlıksız ortalaması.
    - **Basit yöntem:** "“Yarın = dün aynı saat” kuralı; değer, güneşin iki gün arasındaki konum farkına göre (açık-gök
      ışınımı oranıyla) ölçeklenir. …" Bugünkü metnin devamı aynen.
      - Kod: `naif = dünkü üretim × açık-gök(t) / açık-gök(t − 24 sa)`, oran [1/4, 4] ile sınırlı.
      - Planlama sırasında düzeltildi: ilk taslaktaki "gök açıklığı farkı" ifadesi hesabı yanlış anlatıyordu.
    - **Bant kapsaması:** "Gerçekleşen üretimin, önceden ilan edilen iyimser–kötümser aralık içinde kaldığı gündüz saatlerinin
      oranı; her gün ayrı hesaplanır, pencere boyunca ortalanır. Hedef %80'dir — …" Bugünkü metnin devamı aynen.
- **Koordinasyon:** Karne yöntemi ayrı bir oturumda inceleniyor. O oturum hesap tanımını değiştirirse yalnız bu sabit
  güncellenir; iki sayfa birlikte düzelir.

## 4. Bileşenler ve veri

### 4.1 Dosyalar (`web/src/features/vitrin/`)

| dosya | görevi | dışarıya verdiği |
|---|---|---|
| `Vitrin.tsx` | bölümleri dizer; `useDogrulama` bir kez çağrılır | `Vitrin({ onPanel })` |
| `vitrin.css` | `.vt` kapsamında token'lar ve bütün sınıflar | — |
| `fontlar.ts` | `@fontsource` CSS içe aktarımları (vitrin) | — |
| `GunesLogo.tsx` | logo SVG (bugünkü `Marka` geometrisi) | `GunesLogo({ boy })` |
| `UstCubuk.tsx` | masaüstü bağlantıları + mobil çekmece; `kip="yontem"`de bağlantılar `/#…` olur ve "Panele giriş" yerine "← Ana sayfa" çıkar | `UstCubuk({ onPanel?, kip: "ana" \| "yontem" })` |
| `Hero.tsx` | hero metni ve grafik penceresi | `Hero()` |
| `ReferansEgri.tsx` | SVG eğri; Mühür 1'de yalnız temsili kip | `ReferansEgri({ veri: null })` |
| `KanitSeridi.tsx` | dört canlı sayı ya da durum satırı | `KanitSeridi({ durum })` |
| `DortAdim.tsx` | dört kart | `DortAdim()` |
| `TurkiyePiyasasi.tsx` | üç kart + iki masa + dipnot cümlesi | `TurkiyePiyasasi()` |
| `AcikKarne.tsx` | gece bandı, karne kutusu, yöntem kutusu | `AcikKarne({ durum })` |
| `Sss.tsx` | beş soru | `Sss()` |
| `Basvuru.tsx` | başlık + form (bugünkü `BasvuruFormu` mantığı) | `Basvuru()` |
| `Altbilgi.tsx` | altbilgi; `onPanel` yoksa (`/yontem`) "Panele giriş" çıkmaz, bağlantılar `/#…` olur | `Altbilgi({ onPanel? })` |
| `useDogrulama.ts` | `/v1/dogrulama` durum kancası | `useDogrulama(): DogrulamaDurumu` |
| `yontem-metni.ts` | `ADIMLAR`, `METRIKLER` | sabitler |
| `Yontem.tsx` | `/yontem` sayfası, aynı bileşen ve token'larla | `Yontem()` |

- Bölümler kendi metinlerini taşır.
- Bileşenler `api` istemcisini doğrudan çağırmaz. Yalnız `useDogrulama` ve `Basvuru` çağırır.
- `App.tsx`'teki `Vitrin` ve `Yontem` içe aktarımları aynı adla kalır.

### 4.2 `useDogrulama`

```ts
type DogrulamaDurumu =
  | { tur: "yukleniyor" }
  | { tur: "acik"; veri: Dogrulama }   // api.dogrulama() → durum: "acik"
  | { tur: "kapali" }                  // → durum: "kapali"
  | { tur: "hata" };                   // → null (ağ hatası ya da !ok)
```

- Tek istek atılır. Bileşen ayrılınca durum güncellenmez.
- Yeniden deneme yok; sayfa yenilenince yeniden denenir.

### 4.3 `ReferansEgri`

- **Mühür 1:** `veri: null` → temsili kip (§3.2).
  - Şekil, bileşen dosyasındaki sabit kontrol noktalarından çizilir.
  - Sayı, eksen ya da tarih üretilmez.
- **Mühür 2:** canlı kipi bu bileşene ekler: `veri: EgriVerisi`, eksenler, ipucu, tablo görünümü ve dar ekran geometrisi.
  `numuneler/yon-a.html`'deki grafik o kipin örneğidir.

## 5. Erişilebilirlik

- **Kontrast:** bütün metin çiftleri ≥ 4,5:1, grafik çizgileri ≥ 3:1, form alanı kenarı ≥ 3:1 (§2.2).
- **Klavye ve yapı:**
  - Sayfa başında "İçeriğe geç" bağlantısı.
  - `header`, `nav` (aria-label "Ana menü"), `main`, `footer` işaretleri.
  - Bütün etkileşimlerde `:focus-visible` halkası.
- **Çekmece:**
  - Düğmede `aria-expanded` ve `aria-controls`.
  - Açılınca odak ilk bağlantıya gider. Esc ve bağlantı tıklaması kapatır; odak düğmeye döner.
  - Açıkken arka sayfa kaymaz. 1080 px üstüne genişleyince kendiliğinden kapanır.
- **SSS:** yerleşik `details`/`summary`.
- **Grafik:** `role="img"` ve `title`/`desc`.
- **Dokunma:** hedefler ≥ 44 px.
- **Hareket:** `prefers-reduced-motion` uygulanır.

## 6. Doğrulama ve mühür

1. `npm --prefix web run build` (`tsc -b` + `vite build`) ve `npm --prefix web run lint` temiz geçmeli.
2. Tarayıcı paneli (`launch.json` "web"):
   - 1440 / 768 / 375 px'te yatay taşma yok (`scrollWidth` = genişlik).
   - `document.fonts` Plex Sans ve Plex Mono yüklü.
   - Ağ sekmesinde `fonts.googleapis.com` ya da `fonts.gstatic.com` isteği yok.
3. Durumlar:
   - Yerel API'nin gerçek yanıtıyla durum gözlenir.
   - Açık, kapalı ve hata durumları yalnız tarayıcıda, `fetch`'i geçici olarak taklit ederek gösterilir; depoya taklit girmez.
   - **Başvuru formu testte gönderilmez.** Yerel API e-posta gönderebilir.
4. Çekmece klavyeyle sınanır: Tab, Esc, odak dönüşü.
5. Yasaklı terim taraması (§1.1): vitrin dosyalarında ve derlenmiş `dist` çıktısının vitrin metinlerinde sıfır eşleşme.
6. Panel değişmedi mi: giriş ekranı ve bir panel sayfası, değişiklik öncesi ve sonrası ekran görüntüsüyle kıyaslanır;
   font aileleri aynı.
7. Kullanıcıya önizleme: masaüstü ve mobil ekran görüntüleri, gerçek içerikle.
8. Onaydan sonra mühür:
   - `v2.384` Türkçe commit (bu spec dahil), push, GitHub Actions yeşili.
   - Backend değişmediği için pytest etkilenmez.

## 7. Riskler ve notlar

- **Karne yöntemi oturumu:** Ayrı oturum, gündüz örneklemi ve yöntem metni üzerinde çalışıyor; aynı dosyalara dokunabilir.
  Metin tek sabitte toplandığı için birleştirme kolay olur. Çakışma çıkarsa o oturumun hesap kararı esas alınır.
- **Font paketleri:** Panelin Inter opsz ekseni paket olarak doğrulanmalı (§2.1 son madde).
- **`og.png`:** Paylaşım kartı eski görseli göstermeye devam eder (Mühür 3).
- **Yerel API kapalıysa:** Önizlemede kanıt şeridi ve karne "hata" durumunda görünür. Bu doğru davranıştır; öteki durumlar
  taklitle gösterilir.
