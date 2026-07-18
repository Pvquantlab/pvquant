# PVQuant Deck v1.0 — Satış Sunumu Rehberi

_Fable 5 Zeyilname v2.28 mühürlü — 6 slayt, 60-gün pilot CTA, konuşma notları birebir sabit._

**Slayt başlığı (deck adı):** Yükle. Kalibre et. Kanıtla.

---

## Marka Disiplini (Anayasa K2/K3 sahne dili)

- **Başlıklar:** Inter 28 (mono ölçüm dilidir — başlık dili değil; K3'ün tersi de kuraldır)
- **Sayılar + kare-altı mono cümleler:** JetBrains Mono
- **Zemin:** beyaz `#F8FAFC`
- **Yeşil aksan (`#0F6E56`):** sayı vurgusu + başlık altı 2px çizgi + kapanış üç-satırının rengi
- **Gece zemin (`#0B1F2A`) — SADECE Kapak + Kapanış** (login panelinin estetiği, deck'i açıp kapatan parantez)
- **Amber deck'te YOK** (dikkat rengi satışta dikkat dağıtır)
- Slayt başına ≤2 renk
- Geçiş animasyonu **SIFIR** (K8 sahnede de geçerli)

---

## Layout Şeması (Kare slaytlar için — Login, Kalibrasyon, Tahminler, Santralim)

    +---------------------------------------------------+
    | BAŞLIK (Inter 28, üst-sol)                        |
    | ══ (2px yeşil çizgi)                              |
    |                                                   |
    |                                                   |
    |         +---------------------------+             |
    |         |                           |             |
    |         |      EKRAN KARESİ         |             |
    |         |       (merkez %70)        |             |
    |         |                           |             |
    |         +---------------------------+             |
    |                                                   |
    |      mono cümle (alt-orta, JetBrains Mono)        |
    |                                                   |
    |                                              [3]  |
    +---------------------------------------------------+

Sağ-alt köşe: sayfa no, JetBrains Mono 10

---

## Slayt 1 — Kapak (gece zeminli `#0B1F2A`)

**Görsel:**
- Marka: **PVQuant** (Inter Bold, beyaz)
- Slogan: _Santralinizin kanıtlı üretim tahmini_ (Inter, açık gri)
- Alt bant: 3 aksan yeşili küçük nokta veya minik gün ışığı eğrisi motifi

**Konuşma notu (~15 sn) — Keynote notes alanına birebir:**

> "PVQuant, güneş santralleri için üretim tahmini yapar — ama farkımız tahmin etmek değil, kanıtlamak. On dakikada üç şey göstereceğim: verinizi nasıl yüklediğinizi, sistemin kendini nasıl sınadığını ve her sabah elinize ne geçeceğini."

---

## Slayt 2 — Login (Kare 1, beyaz zemin)

**Başlık:** LOGIN

**Görsel:** `docs/tur/tur_01_login_v11.png` (⚠ TUR v1.1 SONRASI — Login kartında **MAPE %38,7 → %14,8** görünecek)

**Mono cümle (alt-orta):**
> Kapıda kanıt: referans santral holdout sonucu.

**Konuşma notu (~25 sn):**

> "Daha kapıda iddiayı görüyorsunuz: Konya'daki referans santralda genel fizik modeli %38,7 hata yapıyordu; sistem santralın kendi verisiyle kalibre olunca %14,8'e indi — hata yarıdan fazla düştü. Bu sayı pazarlama değil; modelin hiç görmediği son dönem üzerinde yapılmış sınavın sonucu. Ve baştan söyleyeyim: bu o santralın sayısı. Sizinkini birlikte ölçeceğiz — ürünün işi zaten bu."

---

## Slayt 3 — Kalibrasyon (Kare 2, beyaz zemin)

**Başlık:** KALİBRASYON

**Görsel:** `docs/tur/tur_05_kalibrasyon.png`

**Mono cümle (alt-orta):**
> Para eden an: yıllık sapma %38,7 → %14,8, hibrit kapı sınavıyla.

**Konuşma notu (~30 sn):**

> "Sistemin özü bu ekran. SCADA verinizi yüklüyorsunuz — bir yıl idealdir, üç ay yeter. Model önce santralınızı tanıyor: kayıplar, panel davranışı, eğim... Referans santralda verinin kendisi invertör tavanını bile ele verdi — plaka etiketine bakmadan, üretim deseninden. Sonra yapay zekâ katmanı devreye girmek için sınava giriyor: verinizin hiç görmediği son diliminde kendini kanıtlayamazsa açılmıyor. Açıldıysa ekranda: %38,7'den %14,8'e."

**Not (Fable 5 S4):** AC keşfi konuşma notunda tek cümle olarak gömülü. Slayt açılmaz, madde yazılmaz. Büyük hikaye ("verinizi ilk hafta didikleyip invertörünüzü buluruz") **Q&A kozudur** — *"modeliniz bizim santralı ne kadar tanır ki?"* itirazı geldiğinde anlatılır.

---

## Slayt 4 — Tahminler (Kare 3, beyaz zemin)

**Başlık:** TAHMİNLER

**Görsel:** `docs/tur/tur_06_tahminler_7g.png`

**Mono cümle (alt-orta):**
> Her sabah 168 saat — P10-P90 belirsizlik bandıyla.

**Konuşma notu (~25 sn):**

> "Her sabah saat beşte sistem kendi kendine 168 saatlik tahmin üretir — yedi gün, saat saat. Koyu çizgi beklenen üretim; yeşil bant belirsizlik aralığı: size 'kesin şu olacak' demiyoruz, 'yüzde sekseni bu bandın içinde' diyoruz. Dengesizlik maliyeti yöneten ekip için bu bir sayı değil, karar aracıdır."

---

## Slayt 5 — Santralim (Kare 4, beyaz zemin)

**Başlık:** SANTRALİM

**Görsel:** `docs/tur/tur_09_santralim_kapanis_v11.png` (⚠ TUR v1.1 SONRASI — Konya GES canlı verisiyle eğri kendiliğinden çiziliyor)

**Mono cümle (alt-orta):**
> İşletmecinin 30 saniyelik sabahı.

**Konuşma notu (~20 sn):**

> "Ve işletmecinin sabahı: otuz saniye. Bugün ne üreteceğiz, model ne durumda, veride sorun var mı — tek ekran. Bir ayrıntı: anomali bulursak silmeyiz, bayraklarız. Verinizde ne olduysa izini görürsünüz."

---

## Slayt 6 — Kapanış (gece zeminli `#0B1F2A`)

**Görsel:** Temiz gece zemin, üç mono satır ortada, altında tek soru

**Metin (üç satır, JetBrains Mono, yeşil `#0F6E56`):**

    60 gün pilot · kurulum bizden · çıkış serbest

_(satırlar arası boşluk; ortada büyük punto)_

**Altında büyük punto (Inter Bold, beyaz):**
> Hangi üç santralınızla başlayalım?

**Konuşma notu (~30 sn):**

> "Teklifim net: altmış günlük pilot — kurulum bizden, çıkış serbest. İlk hafta verinizi yükleyip kalibre ediyoruz; altmış gün sonra önünüze slayt değil, kendi santralınızın karnesini koyuyoruz ve kararı o karneyle veriyorsunuz. Tek sorum var: hangi üç santralınızla başlayalım?"

---

## Q&A Kozu — Hazır Cevaplar

### İtiraz: "Modeliniz bizim santralı ne kadar tanır ki?"

**Cevap:**
> "Doğru soru. Referans santralda ilk hafta bize gösterdi ki genel fiziksel modelimiz o santralı %39 hata ile bilmiyordu. SCADA verisini üzerine koyunca kalibrasyon o santrale özgü kayıpları öğrendi — hatta plaka etiketine bakmadan invertör kapasitesinin tavanına ulaştığı saatleri buldu. Sizinkinde ilk hafta yapacağımız iş bu: veriyi didikleyip santralınızı size anlatmak. Sonrasında model artık genel değil, sizin santralınız."

### İtiraz: "60 gün uzun."

**Cevap:**
> "Karneyi dolduran süre bu. Model dün geldi diye 'iyidir' demiyoruz — 60 gün boyunca her gece kendini ölçüyor. Sizin karar vereceğiniz sayı bu karnede olacak, benim iddiam değil."

### İtiraz: "Fiyat?"

**Cevap:**
> "60. günde konuşuyoruz. O gün elinizde karne var — biri sözü verilen sayı, diğeri gerçekleşen sayı. Karar orada verilir; fiyat karneye göre teklif edilir. Şu an fiyat konuşmak, karneyi görmeden söz vermek olur."

---

## Deck Kurulumu — İki Yol

### Yol A — Fable 5 kurar (önerilen)

Fable 5'in v2.28 teklifi:
> "Kareler çekilince (login + Santralim, v2.12 standardı) ikisini buraya at — `.pptx`'i ben kurarım; tasarım disiplinini piksel düzeyinde uygulamak benim işim, senin işin sahnede anlatmak."

**Sen ne yaparsın:**
1. **Tur v1.1** iki kare çek:
   - `tur_01_login_v11.png` — Chrome gizli pencere, `localhost:8501`, login sayfası (yeni sayılarla: MAPE %38,7 → %14,8)
   - `tur_09_santralim_kapanis_v11.png` — Konya GES Santralim ekranı, güncel canlı eğri
2. İki kareyi Fable 5'e gönder + bu belgeyi paylaş → `.pptx` gelir
3. Sen sahneye çıkarsın

### Yol B — Sen kurarsın

Tercih Fable 5'in değil ama seçenek olarak:

- Keynote (Mac native)
- PowerPoint (Windows uyumlu, ekip paylaşımı kolay)

Bu belgedeki layout şemasını + marka disiplinini + konuşma notlarını birebir uygula.

---

## Envanter — Deck v1.0 için hazır malzemeler

- **Metin (konuşma notları):** ✅ Fable 5 v2.28 mühürlü, birebir
- **Marka disiplini:** ✅ Inter başlık + Mono sayı + yeşil aksan + gece parantezi
- **Layout şeması:** ✅ Kare düzeni sabit
- **Görseller:** 3/4 kare hazır (`tur_05`, `tur_06`, `tur_03` — mevcut docs/tur/'da)
- **Görseller bekleyen:** 2 kare (tur v1.1 — login + Santralim, yeni sayılarla)
- **CTA:** ✅ 60 gün pilot, kurulum bizden, çıkış serbest
- **Q&A kozu:** ✅ 3 hazır itiraz cevabı

**Sonraki adım:** Tur v1.1 iki kare → Fable 5'e teslim → `.pptx` gelir → üç üretici görüşmesini ayarla.

---

## Skill Genişlemesi Kaydı (Fable 5 v2.28 kayıt)

**v2.20 mühründeki hibrit-daralır öngörüsü yön olarak yanlış çıktı.** Kırpma keşfi:
- Fiziği **0.5 puan** düşürdü (%39,2 → %38,7 — beklenti bandının tam alt ucu)
- Hibrit'i **3 puan birden** düşürdü (%17,8 → %14,8)
- Skill %54,6 → %61,8 (**geniş sürpriz**)

**Sebep:** Kırpma fiziğin tepe hatasını azaltınca hibrit **daha temiz bir rezidüel yapıyla** eğitildi — artık invertör tavanını taklit etmeye enerji harcamıyor, gerçek desenleri öğreniyor.

**Satış cümlesinin gücü:** %38,7 → %14,8 = **hatanın %62'sini düşürmek**. Eskisinden güçlü.
