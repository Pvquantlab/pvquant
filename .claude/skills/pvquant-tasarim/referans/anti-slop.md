# Anti-slop anayasası — «yasak → yerine ne»

Amaç tuhaflık değil: kasıtlı, olgun, teknik, ölçülü. ✓ = testle zorlanıyor.

## Yüzey

| Yasak (jenerik imza) | Yerine (PVQuant dili) |
|---|---|
| Her metriğe kart; eş boyutlu kart ızgarası | **Kart bir karar birimidir.** Karar ettirmiyorsa: satır içi değer, tablo özeti, grafik anotasyonu, künye çipi. Emsal: TL «panel kesiti» — kartlar tek yüzeyin 1 px çizgili hücreleri. |
| Bağlamsız dev KPI sayısı | KPI = değer + çapa (hedef/dün/bant) + pencere etiketi + birim. |
| Aşırı radius, cam (glassmorphism), dekoratif gölge | Köşe ölçeği sabit; cam KALKTI (v2.304-305) — geri gelmez; gölge yalnız yükselme anlamında. |
| Mor/mavi gradyan, gökkuşağı paleti | Mürekkep merdiveni + iki veri rengi (mavi=tahmin, amber=gerçekleşen ✓). 3. seri gerekiyorsa önce «grafik ikiye bölünür mü?» |
| Dekoratif ikon/emoji; stok görsel | İkon yalnız işlevsel; vitrin çizimlerinde sembol ikon yasak ✓; illüstrasyon = benekli SVG. |
| «Inter everywhere» | Üç rol: display / Inter gövde / Plex Mono veri (tabular-nums). |
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

## Süreç (Claude öz-denetimi)

- Yeni yüzeyden önce: konuya demirleme (bu ekranı KİM, hangi KARARLA okuyor?) + emsal taraması.
- Tasarım planı → uygulama → **özgünlük denetimi:** «bu ekran herhangi bir SaaS'ın ekranı
  olabilir mi?» Evet'se konuya özgü en az bir gerçek ayrıntı (birim, terim, eşik) ekleninceye
  kadar bitmemiştir.
- Yeni renk/font/köşe değeri icat etmek yasak — önce jeton tartışması (jetonlar.md).
