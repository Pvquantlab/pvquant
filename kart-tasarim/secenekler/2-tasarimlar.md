# 4. Aşama — Tasarım turu ⛔ DUR

**Çalışma varsayımları (kullanıcı kararı, 2026-10-05):** isim seçimi en sona bırakıldı. Önizlemelerde
**çalışma adı olarak isim kümesi A** kullanılıyor, gövde metinleri çalışma metnidir (5. aşamada
seçilecek). Kapsam önerisi §3.0 (her kart tek yeti grubu) varsayıldı. Seçilecek ad hangi küme olursa
olsun beş şablonun hepsi ona uyar: adlar tek veri alanından okunur.

## Ortak zemin (beş sistemde de aynı)

- **Beş mini-diyagram** (`onizleme/_uret/cizimler.mjs`, satır içi SVG, Plex Mono etiket):
  - K1 · yarının saatlik programı (mavi çubuk = tahmin) + bugünün teslim penceresi rayı
  - K2 · tahmin (kesikli mavi) ile gerçekleşen (dolu amber) arası taralı alan + rakamsız TL defteri
    (PVQuant sapması / basit yöntem / teminat etkisi, «fark» köşeli ayracı)
  - K3 · tahmin aralığından üç kanala akış (CSV şablonu, XLSX şablonu, API anahtarı) + saatlik/15 dk seçici
  - K4 · gelen ölçüm (amber noktalar = gerçekleşen) kesilir → «veri gecikti» kuralı; 8 kural üç grupta; gece karnesi şeridi
  - K5 · benekli iyimser–kötümser bant, soluk eski medyanlarla revizyon izi, «şimdi» çizgisi, 06:00 sabah koşusu → webhook
- **Kaldırılanlar:** ₺ jetonu, zil, `</>`, imleç, bayrak, onay rozeti; şeftali zeminler; gradyan levhalar.
- **Renk:** mavi yalnız tahmin, amber yalnız gerçekleşen, eylem rengi kartlarda yok. Şeftali bölümde
  yalnız (dokunulmayan) maket penceresinde kalır.
- **Rakam:** yalnız «8 kural» (üründe var olan sayı). Diyagramlarda TL tutarı yok, çubuklar ölçeksiz.
- Doğrulama: beş dosya 1440 / 900 / 390 px'de ekran görüntüsüyle denetlendi, yatay taşma yok
  (`onizleme/ekran/`). Vitrin testleri değişmeden geçiyor (20/20; depo kodu değişmedi).

## Beş sistem

| | Dosya | Fikir | Kaynak ders |
|---|---|---|---|
| **A · Künye kartı** | `onizleme/tasarim-A.html` | 3+2 ızgara korunur; kartlar «Hangi iş için?» bölümünün dört katlı dilini alır (zaman etiketi → ad → tek cümle → künye). İki geniş kartta diyagram solda. | Amperon etiket–değer, Aurora fayda kalıbı |
| **B · Gün şeridi** | `onizleme/tasarim-B.html` | Beş kart, ok uçlu bir zaman rayında bir günün sırasıyla dizilir: sabah koşusu → teslim → dışa verim → gece → ay boyunca. Tablet/telefonda ray dikeye döner. | Dexter (piyasa zaman çizelgesi), Solargis (iş akışı adları) |
| **C · Panel kesiti** | `onizleme/tasarim-C.html` | Kart kutuları kalkar; tek beyaz yüzey 1 px çizgilerle beş hücreye bölünür. Her hücre panelden kesilmiş bir modül gibi; künye değerleri mono «çip». | Vercel hairline ızgara, Linear yalın arayüz kesiti, Stripe «görsel = ürün parçası» |
| **D · Ana kart + dört** | `onizleme/tasarim-D.html` | Bölümün vaadi TL olduğu için «Sapma maliyeti» büyük ana karttır (ayrıca ay boyunca gün gün çubuk çiftleri çizilir); dört yeti 2×2 küçük kartta. | Bento hiyerarşisi; Modo «yöntemi görünür grafik» |
| **E · Satır listesi** | `onizleme/tasarim-E.html` | Tek yüzeyde beş numaralı satır («01 / 05», dört adımın diliyle): yazı · künye · diyagram yan yana. Teknik şartname gibi okunur. | Solcast teknik özellik dili, Datadog ürün listesi |

## Tek paragraf karşılaştırma

**A**, sayfayla en tutarlı ve en düşük riskli seçenek: bir alttaki iş ızgarasıyla aynı dili konuşur.
Ama beş kart yine eşit ağırlıkta, yani «şablon» hissini tam kırmaz. **B** en çok şey anlatan seçenek:
kart sırası ürünün bir günde ne yaptığını gösterir ve sayfadaki dört adım zincirinin ok dilini sürdürür.
Bedeli, beş dar sütunda metnin çok kısa tutulması ve K2'nin bir «an» değil «dönem» olması. **C**
en kurumsal ve en «gerçek ürün» görünen seçenek: kutu yığını yerine tek yüzey, Vercel/Linear sınıfı bir
disiplin. Riski, üstteki maket penceresiyle birlikte «iki panel» gibi görünmesi. **D** ağırlığa anlam
veren tek seçenek ve TL vaadini en güçlü anlatanı, ama ana kart maket penceresinin (o da sapma TL ekranı)
konusunu tekrarlar ve küçük kartlarda künye düşer. **E** en okunaklı ve en «rapor gibi» seçenek; dikeyde
en uzunu da o, bölümü ağırlaştırabilir.

**Önerim: C.** «AI üretti» hissini en kesin kıran seçenek bu: eşit kart kutuları yok, süs yok, her hücre
ürünün bir parçası. Maket penceresiyle çakışma riski önizlemede sınanamadı (pencere yer tutucu);
6. aşamada gerçek pencereyle birlikte ekran görüntüsünde denetlenmeli. İkinci tercih **A**: en güvenli seçenek, istenirse
C'nin mono çip künyesi A'ya da taşınabilir.

## Seçim (kullanıcı dolduracak)

- Tasarım sistemi: **C · Panel kesiti** (kullanıcı, 2026-10-05)
- Başka bir sistemden alınacak öğe: yok
