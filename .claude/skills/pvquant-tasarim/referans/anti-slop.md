# Anti-slop anayasası — «yasak → yerine ne»

Amaç tuhaflık değil: kasıtlı, olgun, teknik, ölçülü. ✓ = testle zorlanıyor.

## Yüzey

| Yasak (jenerik imza) | Yerine (PVQuant dili) |
|---|---|
| Her metriğe kart; eş boyutlu kart ızgarası | **Kart bir karar birimidir.** Karar ettirmiyorsa: satır içi değer, tablo özeti, grafik anotasyonu, künye çipi. Emsal: TL «panel kesiti» — kartlar tek yüzeyin 1 px çizgili hücreleri. |
| Bağlamsız dev KPI sayısı | KPI = değer + çapa (hedef/dün/bant) + pencere etiketi + birim. |
| Aşırı radius, cam (glassmorphism), dekoratif gölge | Köşe ölçeği sabit; PANELDE cam KALKTI (v2.304-305) — geri gelmez. **Vitrin istisnası (13.10, kullanıcı kararı, jua referansı):** yalnız yüzen üst çubuk hapı + mega menü camdır (`--vt-cam-*`); başka yüzeye yayılmaz. Gölge yalnız yükselme anlamında. |
| Mor/mavi gradyan, gökkuşağı paleti | Mürekkep merdiveni + iki veri rengi (mavi=tahmin, amber=gerçekleşen ✓). 3. seri gerekiyorsa önce «grafik ikiye bölünür mü?» **Vitrin istisnası (13.10):** pembe→lavanta→camgöbeği gradyanı YALNIZ h1 vurgusu, birincil düğme halesi ve koyu zemin radyal ışığında; grafik/veri yüzeyine asla; şeftali tonu yok (amber çakışması). |
| Dekoratif ikon/emoji; stok görsel | İkon yalnız işlevsel; vitrin çizimlerinde sembol ikon yasak ✓; illüstrasyon = benekli SVG. |
| «Inter everywhere» | Panel: üç rol display / Inter gövde / Plex Mono veri. Vitrin (13.10): Inter Tight tek aile ama ÜÇ AĞIRLIK ROLÜ (300 başlık / 400 gövde / 500 etiket-düğme) + Plex Mono veri (tabular-nums) — sayı asla gövde fontuyla dizilmez. |
| Her elemana fade-slide | Hareket tek orkestrasyon anında (R25); durum geçişi ≤200 ms; reduced-motion keser ✓. |
| Aşırı beyaz boşluk | Mühendis yoğunluğu: boşluk hiyerarşi anlatmıyorsa yoğunluk kazanır. |
| Pill/çip enflasyonu | Çip yalnız künye (etiket–değer) ve durum için. |
| Numaralı süs imleri (01/02/03) | Yalnız içerik GERÇEKTEN sıralıysa (süreç/zaman çizgisi). |

## Veri dürüstlüğü (ürünün ruhu)

1. Sayı uydurulmaz ✓; temsili grafik «temsili görünüm · sonuç değil» etiketi taşır ✓.
2. Amber başka hiçbir şeyde ✓; uyarı ayrı ton. 3. Eylem rengi dekor/grafikte yasak ✓.
4. Grafik bir karar sorusuna cevap vermiyorsa grafik değildir — tablo ya da cümle.
5. Boş/yükleniyor/hata dürüst: tire, «yayın açılınca», iskelet; asla sahte eğri.
6. Görünür yüzeyde yöntem/kaynak adı yok ✓ (vitrin); panelde müşteri dili (env adı yazılmaz).
7. Görünür yüzeyde ekip iç terimi yok (21.10.2026, `docs/SON-KONTROL-2026-10-21.md`): «vitrin», «koşu»,
   «zarf», «kapı», «hesap hattı», «D‑1», «pencere», «dilim», «ağaç/matris», «kantil», «şemalı» yazılmaz;
   müşteri dili: üretim programı (KGÜP), dengesizlik maliyeti, teslim saati, gün içi düzeltme,
   iyimser–kötümser aralık, kurulu güç (MW). P50/P90 yalnız finans bağlamında ve açıklamalı
   (`docs/ICERIK-TURKIYE-2026-10-21.md` §2 terim tablosu tek kaynak).

## Süreç (Claude öz-denetimi)

- Yeni yüzeyden önce: konuya demirleme (bu ekranı KİM, hangi KARARLA okuyor?) + emsal taraması.
- Tasarım planı → uygulama → **özgünlük denetimi:** «bu ekran herhangi bir SaaS'ın ekranı
  olabilir mi?» Evet'se konuya özgü en az bir gerçek ayrıntı (birim, terim, eşik) ekleninceye
  kadar bitmemiştir.
- Yeni renk/font/köşe değeri icat etmek yasak — önce jeton tartışması (jetonlar.md).
