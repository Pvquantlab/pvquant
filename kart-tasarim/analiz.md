# 1. Aşama — Mevcut durum analizi

Kaynak: `web/src/features/vitrin/TurkiyePiyasasi.tsx`, `TextliCizimler.tsx`, `varlik/vinyet-*.svg`,
`vitrin.css` (satır 500–512, 582–587, 640–700), komşu bölümler `DortAdim.tsx` ve `IsIzgarasi.tsx`.
Ekran görüntüleri: depodaki vitrin yerelde çalıştırılarak alındı (`?vitrin`, 1440 px ve 390 px):
`arastirma-ekran/00–04`. Canlı pvquant.com'a bu oturumun ağ politikası izin vermedi; depo
`main` ile aynı içerikte (v2.392) olduğu için yerel görüntü canlıyla eşdeğer kabul edildi.

## 1.1 Bugünkü beş kart

| # | Ad | Gövde metni (özet) | Vinyet (ne çiziliyor) | Izgara |
|---|---|---|---|---|
| 1 | **Program hazır** | saatlik program + emre amadelik, teslim penceresinden önce dosya; gecikirse alarm | mavi saatlik çubuklar + kesik «teslim» çizgisi + **bayrak** + **onaylı belge ikonu** | 3'lü sıra |
| 2 | **Sapmanın TL kartı** | aylık TL karşılığı, basit yönteme göre kurtarılan tutar, teminat etkisi | mavi tahmin eğrisi + amber gerçekleşen + aradaki şeftali alan; altında büyüyen boş kutular; **₺ jetonu** | 3'lü sıra |
| 3 | **Toplayıcıya tek tık** | toplayıcı/DSG şablonları (saatlik/15 dk), API anahtarı | aralık eğrisi penceresi → **imleç + hedef halkası** → 15 dk ısı ızgarası; altta **`</>`** | 3'lü sıra |
| 4 | **Operatör masası** | teslim penceresi, emre amadelik, veri alarmı, «aylık bakım penceresine iklim beklentisi» | amber noktalar (gelen veri) → kesik boş noktalar (kesinti) + **zil**; altta 14 hücre, ikisi şeftali | 2'li geniş |
| 5 | **Ticaret masası** | iyimser–kötümser bant, TL gün gün, revizyon izi, API | iç içe bantlı tahmin eğrisi + **`</>`** + **₺ jetonu**; şeftali zemin | 2'li geniş |

Kart kalıbı: `vt-kart vt-vin-kart` → üstte 176 px yükseklikte `vt-levha` (gradyan zemin + gren) →
`vt-kart__govde` içinde yalnız `h3` + tek paragraf. Etiket yok, künye yok, bağlantı yok (R21: kartlar
eylemsiz, kalkmaz). 1081 px altında 3'lü sıra 2+1'e, 600 px altında tek sütuna iner; geniş iki
kartın dar ekranda ayrı «dar» vinyet çifti vardır.

## 1.2 Teşhis — «AI üretti» hissi nereden geliyor

1. **Bölüm kendi komşusundan daha fakir bir kart dili kullanıyor.** Hemen altındaki «Hangi iş
   için?» kartları *etiket → başlık → fayda → etiket–değer künyesi → bağlantı* hiyerarşisini taşıyor
   (ekran 03-isler). TL kartları ise *resim → başlık → paragraf*. Aynı sayfada iki ayrı kart dili var;
   basit olanı «şablondan çıkmış» görünüyor.
2. **Anlam taşımayan sembol ikonları tekrar ediyor.** ₺ jetonu (2 kez), `</>` (2 kez), imleç +
   hedef halkası, zil, bayrak, onay rozetli belge. Bunlar ürün verisini değil, «SaaS illüstrasyon
   kiti» metaforlarını çiziyor. İki kartta aynı jetonun ve aynı `</>`'nin görünmesi, kartların tek
   tek düşünülmediği izlenimini veriyor.
3. **Şeftali (güneş) dolguları dekor olarak kullanılıyor.** Zil, jeton, iki hücre ve iki kartın
   bütün zemini şeftali; üstteki maket penceresinin sahnesi de şeftali. Bölümün sıcak tonu bir
   anlama bağlı değil, rastgele iki kartı «öne çıkarıyor».
4. **İsimler üç ayrı dilde.** «Program hazır» bir durum bildirimi, «Sapmanın TL kartı» bir
   panel nesnesi, «Toplayıcıya tek tık» bir slogan, «Operatör/Ticaret masası» bir rol. Beş kartta üç
   adlandırma kalıbı.
5. **Roller bir alttaki bölümle çakışıyor.** «Ticaret masası» adı hem burada hem «Hangi iş için?»
   ızgarasında (test pinli) geçiyor; «Operatör masası» ile «Operasyon nöbeti» aynı kitleyi iki kez
   anlatıyor. `IsIzgarasi.tsx` yorumu bile «TL bölümündeki pencere kartları işlev gösterimidir, kitle
   listesi değil» diyor, ama iki geniş kart kitle listesi gibi davranıyor.
6. **Gövdeler virgülle dizilmiş özellik yığını.** «Program teslim penceresi, emre amadelik, veri
   gecikince çalan alarm, …» — fayda cümlesi yok, jargon (DSG, emre amadelik) gövdede. Aynı yetiler
   kartlar arasında tekrar ediyor: «TL gün gün» üç kez (kart 2, kart 5, bölüm notu), «API» iki kez,
   «emre amadelik» iki kez. Tekrar, dolgu hissini artırıyor.
7. **3+2 ızgaradaki ağırlık anlamsız.** Geniş iki kart daha önemli olduğu için değil, sırası
   geldiği için geniş. Göz hangi kartın ana kart olduğunu anlayamıyor.
8. **«Tek tık» abartı, «aylık bakım penceresine iklim beklentisi» kapsam dışı.** İlki dışa verim +
   API akışını bir pazarlama klişesine indiriyor. İkincisi §0'daki gerçek yeti listesinde yok;
   yeni tasarımda kullanılmayacak (ürün sahibi doğrularsa ayrı iş olarak eklenebilir).
9. **Vinyetlerde boşluk ve merkezleme.** 176 px'lik levhaların ortasında küçük bir resim duruyor;
   kenarlardan geniş boş alan kalıyor. Bu, stok illüstrasyon kartlarının tipik görünümü.

## 1.3 Korunmaya değer olanlar

- **Benekli/grenli SVG dili** (`feTurbulence` gren, `non-scaling-stroke` mürekkep çizgisi). Dört
  adım levhalarıyla ortak, rastersiz ve kimliğe özgü. Yeni kartlar bu dokuyu korur.
- **Mavi/amber veri sözleşmesi vinyetlerde doğru uygulanmış:** kart 1'in çubukları mavi (program =
  tahmin), kart 2'de amber yalnız gerçekleşen eğri, kart 4'te amber yalnız gelen ölçüm noktaları.
  Yeni sistemin omurgası bu olmalı: **görseli renk değil veri anlamı taşır.**
- **Kart 2'nin tahmin–gerçekleşen eğri çifti** bölümün en anlamlı çizimi: sapmanın kendisini
  gösteriyor. Ayrıca kart 3'ün 96 hücrelik 15 dk ızgarası gerçek bir dosya biçimini anlatıyor.
- **Satır içi SVG kararı** (yazı taşıyan çizimlerde Plex Mono'nun uygulanması, inceleme bulgusu 7).
- **Kartların eylemsizliği (R21)** ve gölgesiz, kenarsız beyaz yüz (`vt-bolum--bant .vt-kart`).
- **Komşu bölümdeki künye kalıbı** (`vt-is__kunye`, mono değer). Yeni kartların bu kalıbı
  paylaşması sayfayı tek dil yapar.
- **Bölüm notu** «Sapmanın TL karşılığı panelde, kendi santralinizin verisiyle hesaplanır.» (test pinli).

## 1.4 Kısıtlar ve bağımlılıklar (sonraki aşamalar için)

- `yapi.test.ts`: `id="para"`, bölüm notu cümlesi pinli; «25,4 bin TL|4,5 MW» yasak. Kart adları
  pinli değil. «Ticaret masası» yalnız `IsIzgarasi.tsx` için pinli; TL kartından kalkması testi kırmaz.
- `gizlilik.test.ts`: vitrin klasöründeki **her dosya** (SVG'ler dahil) yasaklı terim taramasından
  geçer; yeni SVG'lerde de kaynak/yöntem adı olamaz.
- Satır içi stil yasak (`style={` yalnız `Rozet.tsx`'te serbest); her CSS seçicisi `.vt` ile başlar.
- **Dokunulmayacak:** maket penceresi (`PncEkranAna`/`PncEkranIkinci`). Bu çizimin içinde «Sapmanın
  TL kartı» ve «Program hazır» yazıyor; kart adları değişirse pencere başlığıyla kart adı arasında
  ad uyumsuzluğu oluşur. Pencere ayrı işin konusu, bu nedenle `UYGULAMA.md`'de not olarak düşülecek.
- Bütçe: 1081 px üstü 3+2, 601–1080 px 2+1(+2), ≤600 px tek sütun. Yeni şablon üç kırılımda da
  çalışmalı.
