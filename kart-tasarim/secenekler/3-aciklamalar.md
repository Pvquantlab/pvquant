# 5. Aşama — Açıklama turu ⛔ DUR

**Bağlam:** seçilen tasarım **C · Panel kesiti** (kullanıcı, 2026-10-05). Kart adları hâlâ çalışma adı
(isim kümesi A; isim seçimi en sona ertelendi). Künye çipleri her kartta sabittir; aşağıdaki
metinler yalnız gövde cümlesidir.

**Canlı önizleme:** `onizleme/aciklama-C.html` — üstteki seçiciyle beş ton arasında geçilir
(betik yok, CSS `:has`). Ekran görüntüleri: `onizleme/ekran/aciklama-C-t{1..5}-{1440,390}.jpg`.

## Kurallar ve süzgeç

- Her metin tek fayda cümlesi (ton 5'te iki kısa cümle); teknik değer künye çiplerinde.
- Her iddia görev §0 yeti listesinden; kaynak satırı her kartın altında.
- Anayasa 1–3 süzgeci metin verisinde betikle tarandı: yöntem/kaynak adı yok; rakam yalnız «15»
  (dk dilimi) ve «8» (kural sayısı), ikisi de üründe var olan değerler; yüzde, müşteri, «akıllı»,
  «yapay zekâ», «tek tık», «sorunsuz» yok.
- Uzunluk: en uzun metin 158 karakter. Masaüstü ve 390 px'de taşma yok.

## Beş ton

| Ton | Ad | Nasıl okur |
|---|---|---|
| 1 | Fayda önce | Okurun eline geçen sonuçla başlar, nasılını ikinci yarıda söyler. |
| 2 | Ürün özne | «PVQuant … yapar» kalıbı; en açık ve en kurumsal, ama beş kez tekrarlanınca tekdüzeleşebilir. |
| 3 | Gününüzden bir an | Okurun iş gününde somut bir ana bağlanır; en insani ton. |
| 4 | Kısa künye cümlesi | Tek satır, fiilsiz ya da tek fiilli; ayrıntıyı künye çipleri taşır. En yalın. |
| 5 | Sorun → çözüm | Önce kısa bir gerçek, sonra ürünün karşılığı; iki cümle. |

## K1 · Teslim programı

Künye çipleri: `saatlik` `emre amadelik` `alarm çalar`  
Kaynak: §0: saatlik üretim programı + emre amadelik bildirimi, teslim penceresi gecikince çalan alarm

| Ton | Metin | Karakter |
|---|---|---|
| 1 · Fayda önce | Yarının saatlik programı ve emre amadelik bildirimi teslim penceresi kapanmadan hazırdır; bir gecikme olursa alarm sizi uyarır. | 127 |
| 2 · Ürün özne | PVQuant yarının saatlik üretim programını ve emre amadelik bildirimini hazırlar, teslim penceresini izler ve gecikmede alarm verir. | 131 |
| 3 · Gününüzden bir an | Teslim penceresi açıldığında yarının programı ve emre amadelik bildirimi dosya olarak elinizdedir. Bir şey gecikirse ilk siz duyarsınız. | 136 |
| 4 · Kısa künye cümlesi | Saatlik program ve emre amadelik, teslim penceresi kapanmadan hazır. | 68 |
| 5 · Sorun → çözüm | Program teslimi bir son saate bağlıdır. Dosya pencere kapanmadan hazırlanır; gecikme olursa alarm çalar. | 104 |

## K2 · Sapma maliyeti

Künye çipleri: `TL · aylık` `basit yönteme karşı` `teminat etkisi`  
Kaynak: §0: tahmin hatasının aylık TL karşılığı + basit yönteme göre fark + teminat etkisi

| Ton | Metin | Karakter |
|---|---|---|
| 1 · Fayda önce | Tahmin hatasının size aylık kaç TL'ye mal olduğunu, basit yönteme göre farkı ve teminata etkisini tek yerde görürsünüz. | 119 |
| 2 · Ürün özne | PVQuant tahmin hatasını aylık TL'ye çevirir; basit yönteme göre farkı ve teminat etkisini aynı tabloda gösterir. | 112 |
| 3 · Gününüzden bir an | Ay sonunu beklemeden sapmanın kaça mal olduğunu bilirsiniz; basit yöntemle kıyas ve teminat etkisi hemen yanındadır. | 116 |
| 4 · Kısa künye cümlesi | Tahmin hatasının aylık TL karşılığı, basit yönteme göre farkıyla. | 65 |
| 5 · Sorun → çözüm | Yüzde, bütçe toplantısında az şey söyler. Sapmanın aylık TL karşılığını, basit yönteme göre farkı ve teminat etkisini görürsünüz. | 129 |

## K3 · Şablonlu dışa verim

Künye çipleri: `CSV · XLSX` `saatlik ya da 15 dk` `API anahtarı`  
Kaynak: §0: tahmin aralığının toplayıcı/DSG şablonlarında (saatlik ya da 15 dk) CSV/XLSX dışa verimi + API anahtarıyla akış

| Ton | Metin | Karakter |
|---|---|---|
| 1 · Fayda önce | Tahmin aralığını toplayıcınızın ya da DSG'nin şablonunda indirirsiniz; biçimi elle düzeltmeniz gerekmez. İsterseniz API anahtarıyla doğrudan sisteminize akar. | 158 |
| 2 · Ürün özne | PVQuant tahmin aralığını toplayıcı ve DSG şablonlarında, saatlik ya da 15 dakikalık dilimle verir; API anahtarıyla sistemden sisteme de akar. | 141 |
| 3 · Gününüzden bir an | Dosyayı karşı tarafın beklediği biçimde indirirsiniz: toplayıcı ya da DSG şablonu, saatlik ya da 15 dakikalık. Kendi sisteminiz varsa API anahtarı yeter. | 153 |
| 4 · Kısa künye cümlesi | Toplayıcı ve DSG şablonlarında dosya, ya da API ile doğrudan akış. | 66 |
| 5 · Sorun → çözüm | Her alıcı başka bir dosya biçimi ister. Tahmin aralığı her birinin şablonunda hazırlanır; dosya istemeyen sistemler API anahtarıyla bağlanır. | 141 |

## K4 · Alarm kütüphanesi

Künye çipleri: `8 kural` `veri · teslim · performans` `gece karnesi`  
Kaynak: §0: 8 kurallık alarm kütüphanesi (veri/teslim/performans); gece karnesi

| Ton | Metin | Karakter |
|---|---|---|
| 1 · Fayda önce | Sekiz kural veri, teslim ve performans tarafını sizin yerinize izler; gece karnesi her sabah hazırdır. | 102 |
| 2 · Ürün özne | PVQuant'ın alarm kütüphanesi sekiz kuralla veri, teslim ve performans nöbetini tutar; gece karnesini her sabah hazırlar. | 120 |
| 3 · Gününüzden bir an | Gece ekrana kimse bakmazken kurallar bakar. Sabah ilk iş gece karnesini ve açık alarmları görürsünüz. | 101 |
| 4 · Kısa künye cümlesi | Veri, teslim ve performans için 8 kural; her sabah gece karnesi. | 64 |
| 5 · Sorun → çözüm | Nöbet bir kişinin dikkatine bağlı kalmamalı. Sekiz kural veri, teslim ve performansı izler; gece karnesi her sabah hazırdır. | 124 |

## K5 · Gün içi aralık

Künye çipleri: `iyimser–kötümser` `gün içi revizyon` `sabah webhook’u`  
Kaynak: §0: iyimser–kötümser bant, gün içi revizyon izi, sabah koşusu webhook’u

| Ton | Metin | Karakter |
|---|---|---|
| 1 · Fayda önce | İyimser–kötümser bant gün içinde güncellendikçe önceki hâlleri izde kalır; sabah koşusu bitince webhook sisteminize haber verir. | 128 |
| 2 · Ürün özne | PVQuant tahmini iyimser–kötümser bant olarak verir, gün içindeki her revizyonun izini tutar ve sabah koşusu bitince webhook gönderir. | 133 |
| 3 · Gününüzden bir an | Sabah koşusu bittiğinde sisteminize haber gider. Gün boyunca bant değiştikçe neyin ne zaman değiştiğini görürsünüz. | 115 |
| 4 · Kısa künye cümlesi | Gün içinde revize edilen bant, izi ve sabah webhook'u. | 54 |
| 5 · Sorun → çözüm | Tek bir sayı riskin ne kadar olduğunu söylemez. Bant iyimser ve kötümser sınırı gösterir; gün içi revizyonlar iz bırakır, sabah koşusu webhook ile duyurulur. | 157 |

## Değerlendirme

- **Ton 1 · Fayda önce:** ilk okuyuşta en anlaşılır olanı; kurumsal ama «siz» diliyle insani. Çiplerle
  en az tekrar eden ton (cümle sonucu söylüyor, çipler değeri).
- **Ton 2 · Ürün özne:** en açık, ama beş hücrede beş kez «PVQuant …» tekdüze okunur. K5'teki «bant
  olarak verir», dört adım bölümündeki «Tek sayı değil … bant» cümlesine yakın düşer.
- **Ton 3 · Gününüzden bir an:** en insani ve akılda kalan; K4'ün «Gece ekrana kimse bakmazken kurallar
  bakar.» cümlesi bölümün en güçlü satırı olabilir. Bedeli: K3'te en uzun metinlerden biri.
- **Ton 4 · Kısa künye cümlesi:** en yalın, ama C'de cümle çiplerin tekrarına dönüşüyor (önizlemede
  görülüyor). Ancak çipler kaldırılırsa anlamlı olur.
- **Ton 5 · Sorun → çözüm:** ikna edici, ama ilk cümleler («Yüzde, bütçe toplantısında az şey söyler.»)
  beş kez arka arkaya okununca slogan kalıbına kayar; tek kartta kullanılırsa güçlü.

## Önerim

**Ton 1, K4 için Ton 3.** Beş kart tek sesle, faydayla açılır; nöbet kartında «Gece ekrana kimse
bakmazken kurallar bakar.» gibi tek bir insani an, hücreleri tekdüzelikten kurtarır. Karışık kullanmak
istemezseniz yalın Ton 1.

## Seçim (kullanıcı dolduracak)

- Ton: ☐ 1 ☐ 2 ☐ 3 ☐ 4 ☐ 5 — ya da kart kart: K1 … · K2 … · K3 … · K4 … · K5 …
- Metinde değişiklik: …
