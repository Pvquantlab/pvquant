# PVQuant Üretim Tahmini ve Doğruluk Raporu — Üretim Kılavuzu

Bu belge, `PVQuant_Konya_GES_RAPOR_16sayfa.html` dosyasının nasıl üretildiğini ve yeni
raporların aynı kalitede nasıl üretileceğini anlatır.

---

## 1. Rapor ne yapar

Santral sahibine üç soruyu yanıtlar:

1. **Önümüzdeki 16 gün ne kadar üreteceğim?** (sayfa 3–6)
2. **Bu tahmine ne kadar güvenebilirim?** (sayfa 7–10)
3. **Bu sayılar nasıl üretildi, neyi bilmiyorsunuz?** (sayfa 11–16)

Raporu rakiplerinden ayıran şey ikinci bölümdür: yayımlanan her tahmin ertesi gün gerçekleşen
üretimle karşılaştırılır ve sonuç raporda basılır. Bu bölüm çıkarılırsa rapor sıradan bir
tahmin çıktısına döner.

---

## 2. Sayfa planı

| # | Sayfa | İçerik |
|---|---|---|
| 1 | Kapak | Santral adı, dönem, iki sonuç sayısı, 16 günlük yelpaze grafiği, mod seçici |
| 2 | İçindekiler | Bölüm haritası, raporun üç kuralı, dört terimlik okuma anahtarı |
| 3 | Yönetici özeti | 8 gösterge kartı, değerlendirme, izleme kalemi kutusu |
| 4 | Günlük üretim | Yelpaze grafiği + günlük P90/P50/P10 çizelgesi + dönem toplamı |
| 5 | Saatlik profiller | Tipik gün profili + ilk 8 günün panelleri |
| 6 | Saat × gün matrisi | 16 gün × 15 saat, kum tonlamalı ısı çizelgesi |
| 7 | Doğruluk karnesi | Kazanç alanı grafiği + son 7 günün çizelgesi |
| 8 | Hata dağılımı | Saçılım + koridor, MAE dağılımı, sapma histogramı, bütünlük kuralları |
| 9 | Kalibrasyon | İyileşme şelalesi + bulunan katsayılar |
| 10 | Bağımsız test ve veri kalitesi | Holdout şeridi, aylık kapsama, bayrak çizelgesi |
| 11 | İklim zarfı | Aylık zarf + yıllık aşılma olasılığı eğrisi |
| 12 | Yıl × ay matrisi | 20 yıl × 12 ay üretim matrisi |
| 13 | Model zinciri | Dört halkalı zincir, saha kimliği, veri künyesi |
| 14 | Standartlar ve sınırlar | Çerçeveler, bilinen eksikler, tahmin evrimi |
| 15 | EK-A | Ölçütler, belirsizlik bütçesi, kısaltmalar |
| 16 | EK-B | Sözlük, referanslar, yasal bilgi, künye |

**Sayfa sayısı 16'da sabittir.** Yeni bir bölüm eklenecekse başka bir bölüm çıkmalıdır.

---

## 3. Tasarım sistemi

### Renk

| Amaç | Kod | Nerede |
|---|---|---|
| Marka / veri | `#0D4C68` | Başlık altı çizgileri, tablo başlıkları, grafik çizgileri |
| Marka açık | `#2B7B9B` | İkincil sütunlar, şelalede iyileştirme adımları |
| Kapak bloğu | `#082F42` | Yalnızca kapağın üst bloğu |
| Belirsizlik / büyüklük (kum) | dolgu `#F0E3C9`, kenar `#DCC79A` | Olasılık aralıkları, kazanç alanı, matris tonlaması |
| Durum · hedefte | `#2E7856` | Gösterge kartları |
| Durum · izlemede | `#A87519` | Gösterge kartları, kapsama grafiği, şelalede bedel adımı |
| Durum · eşik dışı | `#A83A2B` | Gösterge kartları |
| Ana metin | `#11171A` | Gövde, başlıklar, şekil açıklamaları |
| İkincil metin | `#414B46` | Etiketler, alt açıklamalar |
| Izgara | `#E2E7EA` | Grafik ızgara çizgileri |

**İki kural:**
- **Kum = belirsizlik ya da büyüklük.** Beklentinin etrafındaki pay her zaman kum rengidir.
- **Amber ve kırmızı yalnızca durum içindir.** Büyüklük göstermek için asla kullanılmaz —
  yüksek üretimin kırmızı basılması iyi bir günü sorun gibi gösterir.

### Tipografi

- **Başlıklar:** Source Serif 4 · 700 · 26 pt (kapakta 34 pt)
- **Gövde ve çizelgeler:** IBM Plex Sans · 400/500/600
- **Kimlik ve kod alanları:** IBM Plex Mono · 400
- **Bölüm başlığı ölçeği:** 11 pt kalın siyah + altında 0,9 pt marka rengi çizgi
- **Alt başlık:** 9,4 pt
- Yazı tipleri belgeye base64 olarak gömülüdür. **Alt-küme (subset) dosyaları kullanılmaz** —
  latin ve latin-ext birleştirilmiş tam TTF gerekir, aksi hâlde PDF'te Türkçe karakterler bozulur.

### Sayfa yapısı

- A4 (210 × 297 mm), kenar boşlukları 14 mm üst / 18 mm yan / 11 mm alt
- Üstbilgi: solda `PVQuant · Kanıta dayalı üretim tahmini`, sağda `Santral · dönem`
- Altbilgi: solda mod rozeti, sağda `Sayfa n / 16`
- Kapak bu düzenin dışındadır (tam genişlikte koyu blok)

---

## 4. Grafik dili

**Standart biçim: yelpaze.** Koyu çizgi beklenti (P50), etrafındaki kum alan %80 olasılık
aralığı (P10–P90). Alanın kenarına ince çizgi çizilir; açık dolgu düşük kaliteli baskıda kaybolur.

**Her grafik bir iddia taşır ve o iddianın sayısı grafiğin içindedir.** Örnekler:
- Saçılım grafiğinde: “±%10 koridorunda gün-öncesi %65 · 24–72 s %49”
- MAE panelinde: “Sabah 0,19 MW, öğlen 0,58 MW — ikisi de üretimin yaklaşık %6'sı”
- Şelalede: her adımın altında “kalan hata” satırı

**Dikkat çekilen dönem** açık gri şerit + üstünde etiketle işaretlenir (örn. “cephe geçişi”).

**Eksen kuralları:**
- Eksen başlıkları kalın siyah, rakamlar orta kalın koyu gri, ızgara açık
- Sıfırdan başlamayan eksen kullanılıyorsa şekil açıklamasında **yazılır**
- Değişimler yüzde puanı ise etiket “puan” yazar (“−1,8 puan”), yüzde değil
- Eksi işareti tipografik eksidir (−), kısa çizgi değil

**Isı çizelgesi:** tek renk kum tonlaması (`#FEFBF5 → #C49E52`), ton eğrisi `t**0.88`.
Sayılar her hücrede koyu kalır; beyaz yazıya geçilmez.

---

## 5. Yazım ilkeleri

- **Teknik jargon müşteri diline çevrilir.** “run” yerine “tahmin”, “holdout MAPE” yerine
  “bağımsız testte hata”, `yanlis_yil` yerine “hatalı yıl bloğu”. Kısaltmalar birim olarak
  kalabilir (WMAPE, MAPE), çünkü müşterinin danışmanı karşılığını arar.
- **Her bölüm bir hükümle başlar.** “Belirsizlik dar.” “Doğrulama 87 gündür kesintisiz.”
  Paragraf sonra gelir.
- **Kötü sonuç gizlenmez.** Zayıf gün karnede kalır, bedel ödeten kalibrasyon adımı şelalede
  görünür, bilinen sınırlar ayrı bir bölümde yazılır. Raporun inandırıcılığı buna bağlıdır.
- **Sayfa 2'deki üç kural tüm rapor boyunca geçerlidir:** veri yoksa boş kalır, her sayı tek
  kaynaktan gelir, her tahmin ertesi gün sınanır.

---

## 6. Veri kuralları

- **Eksik veri asla sıfırla doldurulmaz**, “—” basılır. Gece saatleri, ölçülmemiş günler,
  tamamlanmamış aylar hep böyle işaretlenir.
- **Türetilebilen hiçbir sayı elle yazılmaz.** Histogram kutuları, medyan ve yüzdelikler tek bir
  dağılımdan; iklim zarfı, uzun dönem ortalaması ve Pxx değerleri tek bir arşivden hesaplanır.
  Elle yazılan sayı, er ya da geç grafiğiyle çelişir.
- **Aynı sayı iki sayfada görünüyorsa aynı kaynaktan gelmelidir.** Örnek: günlük toplamlar hem
  sayfa 4'ün çizelgesinde hem sayfa 6'nın alt satırında; iklim ortalaması hem sayfa 11'in
  çizgisinde hem sayfa 12'nin son satırında.
- **Kısmi dönem tam dönem gibi gösterilmez.** Devam eden ay ne ortalamaya ne renk ölçeğine girer.

---

## 7. Üretim akışı

```
pvq.py                 ortak modül: palet, gömülü fontlar, temel CSS,
                       üstbilgi/altbilgi, build(), grafik motorları, iklim arşivi
build_s01.py … s16.py  sayfa üreticileri (her biri tek sayfa HTML + PDF yazar)
merge_html.py          16 sayfayı tek HTML'de birleştirir (CSS'i sayfa başına kapsüller)
```

**Sayfa üretmek:**

```bash
python3 build_s07.py        # tek sayfa
python3 merge_html.py       # tümünü birleştir
```

`build()` her çağrıda sayfa sayısını basar. **“1 sayfa” demiyorsa taşma vardır** — metni
kısaltın ya da grafiğin yüksekliğini düşürün. Taşan içerik sessizce kırpılır, fark edilmezse
altbilgi kaybolur.

**PDF motoru WeasyPrint'tir.** `wkhtmltopdf` kullanılmaz: CSS grid desteklemez, düzeni bozar.

**Her sayfa üretildikten sonra görsel olarak kontrol edilir:**

```bash
pdftoppm -png -r 130 -f 1 -l 1 çıktı.pdf onizleme
```

Çakışan etiketler, kırpılan eksen yazıları ve taşan kutular yalnızca bakarak görülür.

---

## 8. Yayın öncesi kontrol listesi

- [ ] Her sayfa tam tek A4 (`build()` çıktısı “1 sayfa”)
- [ ] Hiçbir etiket çizgiyle, sütunla veya başka etiketle çakışmıyor
- [ ] Eksen başlıkları ve lejantlar kalın siyah
- [ ] Sıfırdan başlamayan eksenler şekil açıklamasında belirtilmiş
- [ ] Aynı sayı iki sayfada aynı değerde
- [ ] Eksik veri “—” ile işaretli, sıfır yok
- [ ] Kum yalnızca belirsizlik/büyüklük, amber-kırmızı yalnızca durum
- [ ] “run”, “JSON”, “şema” gibi iç terimler metinde yok
- [ ] Bilinen sınırlar bölümü güncel
- [ ] Yer tutucular gerçek değerlerle değiştirilmiş (rapor kimliği, iletişim, canlı bağlantı)

---

## 9. Bilinen tuzaklar

| Sorun | Belirti | Çözüm |
|---|---|---|
| Font alt-kümeleri | PDF'te “Ağustos” → “A, ustos” | latin + latin-ext birleştirilmiş tam TTF kullan |
| `wkhtmltopdf` | İki sütunlu bloklar alt alta düşer | WeasyPrint kullan |
| SVG içinde `linearGradient` | Bazı çubuklar hiç görünmez | Gradient yerine kademeli düz renk |
| Sınıf adı çakışması | Çizelge başlıkları büyük harfe döner, sayılar serif olur | Sayfaya özel sınıf adı ver (`.lb`, `.val`) |
| Çift eksen etiketi | Rakamlar üst üste biner | Grafik çerçevesinde `xticks=False` |
| Esnek yerleşimde eşitsiz satırlar | Alt çizgiler metnin üstünden geçer | Gerçek çizelge kullan |
| Taşan sayfada `margin-top:auto` | Bloklar üst üste biner | İçeriği kısalt; auto boşluk negatif alanı çözmez |

---

## 10. Yeni bir santral için raporu üretmek

1. `pvq.py` içindeki iklim arşivini yeni santralin verisiyle değiştirin.
2. Günlük tahmin dizisini (`p50`, `hw`) ve saatlik profil taban eğrisini güncelleyin.
3. Karne verilerini (`wm`, `sk`, `h72`) ve kalibrasyon adımlarını girin.
4. Saha kimliği ve veri künyesi tablolarını santralin künyesiyle güncelleyin.
5. Üstbilgideki santral adı ve dönemi `pvq.HEAD` içinde değiştirin.
6. Tüm sayfaları üretip `merge_html.py` ile birleştirin.
7. Kontrol listesini uygulayın.

Sayfa metinleri santrale göre değişir; **tasarım sistemi ve grafik dili değişmez.** Raporun
tanınırlığı bu tutarlılıktan gelir.
