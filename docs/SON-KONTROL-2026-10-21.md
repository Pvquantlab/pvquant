# Son kontrol — Türkiye SaaS pazarına uygun içerik, terminoloji ve pazarlama dili denetimi (21.10.2026)

Ortam: **bulut oturumu** (kullanıcı kararı, 21.10: «Yerel oturumda devam etmeyelim. Bu oturumdan yapalım.»). Kod
incelemesi, düzeltmeler, testler, derleme, iki tur görsel/metin doğrulaması ve bu rapor burada yapıldı; canlıya alma
yapılmadı (ssh bulutta yok). Bulut kredi düşümü bu ortamdan okunamıyor — **doğrulanamadı**. Dal `main-bozzyl`
(PR #10), commit'ler a7e81f8 (dokuz düzeltme) ve 6439692 (/yontem «Vitrindeki»). Referans: kullanıcının 9 canlı ekran
görüntüsü (`docs/ekran-kontrol-2026-10-21/`) + kaynak kod; önceki tur raporu `docs/ICERIK-TURKIYE-2026-10-21.md`.

**Kapsam ve sınır:** yalnız metin. Renk, tipografi, görsel, animasyon, bölüm yapısı, responsive düzen ve çapalar
değişmedi (diff: 9 dosya, 18 satır, hepsi metin düğümü ya da test pini). Yeni sayı, doğruluk oranı, müşteri/referans
adı, özellik vaadi eklenmedi; «görünür yüzeyde yöntem/kaynak adı yok» kuralı (`gizlilik.test`) ve eylem sözlüğü
(«Karnenizi başlatın», «Karnemi başlat») korundu.

## 1. İncelenen bölümler

Ekran görüntüsü sırasıyla ve kaynak koddan: üst çubuk + mega menü (Ürün, Doğruluk, Türkiye piyasası, Hakkında) ve mobil
çekmece; hero (başlık, giriş, iki düğme, mikro satır); Dört adım (başlık, dört kart, ayna tablosu, çıkış notu); İş
birimleri (başlık, giriş, dört kart); kanıt şeridi; Açık karne (giriş, kilitli kart, dört kısa tanım, yöntem kapanışı,
referans eğrisi lejant/künye/tablo/ekran okuyucu açıklaması); Rakamlar (dört rakam, künye, dipnot); SSS (altı soru);
Başvuru; altbilgi (site haritası, ilkeler, alt satır); /yontem (giriş, Karne nasıl oluşur, Metrikler, Aralık ve yayın
disiplini, Türkiye piyasası beş kart + not); `index.html` başlık/açıklama/OG. Panel (giriş arkası) kapsam dışı.

Dört ölçütle okundu: (a) Türkiye enerji piyasası uyumu (KGÜP, dengesizlik maliyeti, teslim saati, toplayıcı/DSG, emre
amadelik, kurulu güç), (b) santral sahibi/ticaret/finansman okurunun ilk okuyuşta anlaması, (c) kurumsal ve güven veren
ton (abartı, boş sıfat, edebî ifade yok), (d) tutarlılık (aynı kavram her yerde aynı ad; bölüm adıyla göndermeler uyumlu).

## 2. Bulunan sorunlar ve düzeltmeler (eski → yeni)

| # | Yer | Eski | Yeni | Neden |
|---|---|---|---|---|
| 1 | Dört adım, çıkış notu bağlantısı | «işinize göre ayrıntısı iş kartlarında» | «…iş birimi kartlarında» | Bölüm 21.10'da «İş birimleri» oldu; gönderme eski adı taşıyordu (tutarlılık) |
| 2 | Altbilgi, ilkeler 5. madde | «Vitrin vaat etmez; karne panelde canlıdır» | «Bu sayfa vaat etmez; karne panelde canlıdır» | «Vitrin» ekibin iç adı; müşteri için anlamsız |
| 3 | Rakamlar, künye | «kaynak: depo, test takımı ve bulgu defteri» | «kaynak: yazılım deposu, otomatik test takımı ve bulgu kayıt defteri» | «Depo/defter» tek başına belirsiz; açık ad güven verir |
| 4 | Rakamlar, dipnot | «(hesap hattı + arayüz)» | «(hesaplama motoru + arayüz)» | «Hesap hattı» iç terim |
| 5 | SSS 6. soru başlığı | «Modelinize neden güvenelim?» | «Tahminlerinize neden güvenelim?» | Sayfa «model» demiyor, «tahmin» diyor; yöntem adı görünür yüzeyden uzak tutulur (test pini güncellendi) |
| 6 | /yontem Türkiye piyasası, «Teslim programı» kartı | etiket «D‑1 · teslim penceresi»; metin «…teslim penceresi kapanmadan hazırdır…»; künye «alarm çalar» | «Bir gün önce · teslim saati»; «…teslim saatinden önce hazırdır…»; «alarm uyarısı» | «D‑1» ve «pencere» piyasa jargonu; aynı sayfanın diğer yerleri «teslim saati» diyor; «çalar» gündelik |
| 7 | Aynı bölüm, «Alarm kuralları» kartı | «Gece ekrana kimse bakmazken kurallar bakar. Sabah ilk iş gece karnesini ve açık alarmları görürsünüz.» | «Gece ekran başında kimse yokken kurallar izler; sabah gece karnesi ve açık alarmlar hazırdır.» | «Kurallar bakar» edebî; kurumsal düz anlatım |
| 8 | Aynı bölüm, «Gün içi güncelleme» etiketi | «Sabah koşusundan itibaren» | «Sabah hesabından itibaren» | «Koşu» yazılım jargonu; kartın kendi metni zaten «sabah hesabı» diyor |
| 9 | Mega menü — Aylık beklenti | «aylık üretim zarfı» | «aylık üretim aralığı» | «Zarf» istatistik terimi; site «aralık» kullanıyor |
| 10 | Mega menü — Raporlar | «şemalı JSON» | «JSON çıktı» | «Şemalı» teknik niteleme, bilgi katmıyor |
| 11 | Mega menü — Aralık ve yayın disiplini | «Bant nasıl kurulur, yayın kapısı ne zaman açılır» | «Aralık nasıl kurulur, yayın koşulu nedir» | «Kapı» iç terim; kilitli kart «Yayın koşulu» diyor (tutarlılık) |
| 12 | Referans eğrisi, grafik etiketi | «AC tavanı» | «AC sınırı» | Sektör dili «AC/inverter sınırı»; Dört adım kartı da «inverter sınırı» diyor |
| 13 | Referans eğrisi, ekran okuyucu açıklaması | «Araştırma koşusu; …», «bu koşunun P90 değeri» | «Araştırma amaçlı örnek gün; …», «bu günün P90 değeri» | «Koşu» jargonu (görünmez metin ama okunur) |
| 14 | /yontem giriş ve Denetlenebilirlik kartı | «Vitrindeki ve paneldeki…», «Vitrindeki Açık karne…» | «Bu sitedeki ve paneldeki…», «Ana sayfadaki Açık karne…» | İç terim; ikinci turda tam sayfa görüntüsünde fark edildi |

Toplam 14 düzeltme, 18 satır. Hiçbiri cümle uzunluğunu anlamlı ölçüde değiştirmedi; taşma/kırpma oluşmadı (§4).

## 3. Korunanlar (bilinçli)

- **P50 / P10–P90** (referans eğrisi lejantı ve tablosu, menüdeki «yıllık P50–P99»): GES finansmanı ve ticaretinde
  standart gösterim; aynı pencerede «Tahmin», «Tahmin aralığı», «Gerçekleşen» sözcükleriyle birlikte verildiği için
  anlaşılır. Sitenin geri kalanı «iyimser–kötümser aralık» der; iki dil bilinçli olarak yan yana.
- **Metrik adları** («ortalama sapma», «basit yöntem», «sıkı referans», «bant kapsaması») ve kısa tanımları:
  `yontem-metni.ts` hesapla eşlenmiş tek kaynak, `mantik.test` pinleri; 21.10'da kullanıcı onayıyla yazıldı.
- **Kullanıcının seçtiği başlıklar** (kanıt şeridi, Dört adım, İş birimleri, kilitli karne) ve hero girişi («söyler»
  sade dil; kullanıcı gördü).
- **«Emre amadelik», «KGÜP», «DSG», «toplayıcı», «webhook (parantezde)», «SCADA», «API anahtarı»**: hedef okurun
  gündelik terimleri; ilk geçişte açıklamalı.
- **«Bant»** sözcüğü /yontem'in yöntem kartlarında («bandın genişliği»): metrik adı «bant kapsaması» ile aynı kavram;
  teknik okur için yazılmış bölüm.
- **SSS 1–5**, Başvuru, ilkeler 1–4, Rakamlar başlığı («Vaat değil, tarihli rakam.»), altbilgi alt satırı,
  `index.html` başlık/açıklama: bir önceki turda yazıldı, bu okumada sorun çıkmadı.
- **Tolerans yüzdeleri, rakip adları, doğruluk oranı vaadi, «yapay zekâ»** yine yazılmadı (dürüstlük anayasası).

## 4. Doğrulama (iki tur)

**Tur 1 — a7e81f8 (dokuz düzeltme) üzerinde, replika `fable5-icerik` (Caddy 2.11.7, üretim derleme adımları):**

| Kontrol | Sonuç |
|---|---|
| `npm test` (71 test; gizlilik/yapı/mantık/tıklama pinleri) | **71/71** |
| `npx tsc --noEmit`, `npm run build`, `npx oxlint src/features` | 0 / 0 / 0 (oxlint'teki 3 uyarı `sayfalar/ProductionForecastChart.tsx`'te, önceden var, dokunulmadı) |
| CDP taraması (`tarama.mjs`; «/» ve «/yontem»; 320/375/390/768/1081/1440/1920 px) | **taşma 0, çift id 0, isimsiz etkileşimli 0, alt'sız görsel 0, atlanan başlık 0**; küçük dokunma hedefi 7/8/8 (ana) ve 1 (/yontem) — önceki turlarla birebir aynı, metinle ilgisiz |
| Tam sayfa görüntüler: Chromium 156, Firefox 157, WebKit 27.2 × 390/768/1440/1920 × «/», «/yontem», giriş (36 görüntü, hareket azaltma kipi) | Çekildi; ilk ekranlar ve değişen bloklar gözle kontrol edildi, kırpılma/üst üste binme yok |
| Blok görüntüleri + DOM metin yoklaması (3 motor × 390/768/1440: Türkiye piyasası bölümü, mega menü Ürün/Doğruluk, Rakamlar, SSS 6, ilkeler, Dört adım çıkış notu, referans eğrisi) | 9 bağlamın 9'u temiz: 14 yeni ifadenin tamamı DOM'da, 16 eski ifadenin hiçbiri yok; Türkçe karakterler (ş, ı, ğ, İ, ç, ö, ü) üç motorda da doğru, «�» yok |

**Tur 2 — 6439692 (son durum) üzerinde, replika yeniden derlendi, bağımsız tekrar:**

| Kontrol | Sonuç |
|---|---|
| `npm test` / `tsc` / `build` / `oxlint` (ikinci commit sonrası yeniden) | 71/71 · 0 · 0 · 0 |
| CDP taraması, iki sayfa × 7 genişlik | **temiz** (taşma 0; küçük hedef sayıları tur 1 ile aynı) |
| Tam sayfa görüntüler 3 motor × 4 görünüm × 3 sayfa (36 görüntü) | Çekildi; yatay taşma 36'da da yok; /yontem ilk ekranı ve Türkiye piyasası bölümü üç motorda gözle kontrol edildi |
| DOM metin yoklaması 3 motor × 3 görünüm (16 yeni ifade var / 17 eski ifade yok / Türkçe karakter) | **9/9 temiz** |

**Sayfa yüksekliği — canlıdaki main (8d79554, aynı araçla derlenen taban replika) → son durum (6439692), Chromium, CSS px:**

| Görünüm | «/» | «/yontem» |
|---|---:|---:|
| 390×844 | 13 102 → 13 102 | 8 853 → **8 830** (−23: «Teslim programı» kartı dar ekranda bir satır kısaldı) |
| 768×1024 | 10 533 → 10 533 | 7 050 → 7 050 |
| 1440×900 | 7 928 → 7 928 | 5 188 → 5 188 |
| 1920×1080 | 8 029 → 8 029 | 5 231 → 5 231 |

Firefox ve WebKit son durumda Chromium'la ±1–24 px içinde (yazı tipi ölçümü farkı; önceki turlarla aynı). Düzen,
bileşen sayısı ve CSS değişmedi.

**Yapılmayan kontroller:** gerçek Safari/iOS ve Android cihaz (Linux WebKit/Chromium kullanıldı); canlı site (dağıtım
kullanıcıda); panel içi metinler (kapsam dışı). Ham veri `perf/analiz/fable5-icerik/sonkontrol1/`, `sonkontrol2/`
(depo dışı).

## 5. Sonuç ve açık kalanlar

- Metinler Türkiye GES piyasasının diliyle tutarlı; iç jargon (vitrin, koşu, zarf, kapı, hesap hattı, D‑1, pencere)
  görünür yüzeyden kalktı; bölüm adları ve göndermeler birbiriyle uyumlu; tasarım değişmedi.
- Çözülmemiş sorun yok. Tartışmaya açık tek nokta P50/P10–P90 gösterimi (§3) — finans okurunun lehine korundu;
  istenirse lejant «Tahmin (beklenen)» / «Tahmin aralığı (iyimser–kötümser)» yapılabilir, tablo başlıkları da aynı
  commit'te değişir.
- Teslim: PR #10 (`main-bozzyl` → `main`) bu iki commit + rapor ile güncellendi; birleştirme kullanıcı onayıyla,
  dağıtım kullanıcının sunucusundan (`git pull && docker compose build web && docker compose up -d`), ardından canlı
  kontrol.
