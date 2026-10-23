# Bileşen dili — kalıplar ve «ne zaman KULLANMA»

## Kart — ne zaman KULLANMA (skill'in ruhu)

Her metrik karta dönüşünce arayüz jenerikleşir. Kart yalnız bir KARAR birimini çerçeveler.
Alternatif merdiveni (önce bunlar denenır): satır içi değer → tablo özeti → grafik
anotasyonu → künye çipi → tek-yüzey kesit hücresi (TL bölümü emsali) → en son kart.
Kart-içinde-kart (2+ seviye çerçeve/gölge) yasak.

## KPI kalıbı

`değer (mono, tabular, birimli) + çapa (Δ hedef/dün/bant) + pencere etiketi`.
Değer etiketinden görsel olarak baskın. Mod/boş durumda yeşil rozet değil nötr çip;
eksik veri «—» (tire disiplini, `?? 0` yasak — v2.310 dersi).
**Tire yalnız DEĞER yerinde** (hücre, KPI, çip içindeki sayı): cümlenin başına tire KONMAZ («— henüz tahmin yok» yasak;
«Henüz tahmin yok.» — 23.10.2026 kullanıcı bulgusu: konuşma çizgisi / madde imi gibi okunuyor). Değer tiresinin ardına
neden gelecekse orta noktayla: «— · gece değerlendirmesinde birikiyor»; iki tire yan yana gelmez.

## Başlık sistemi (23.10.2026, sekizinci tur)

Sayfa h1 28/600 + 15 px ikincil alt metin (`Sayfa`); bölüm eyebrow `.ozet-bas`/`.etiket-ust` 12,5/500 büyük harf
soluk; **kart h3 16/600 + ayrı satırda `p.kart-alt` 13,5/400 ikincil** (`Kart alt="…"`; «Başlık — açıklama» dizgisi
tek yerden bölünür, ilk harf büyütülür); grafik/tablo grup başlığı eyebrow + `p.kart-alt`. Başlıkta uzun çizgi YOK;
ana başlık kısa, alt başlık açıklayıcı. Numara `.kart-no` yalnız gerçek sırada (Santralim 1–7), ayraç CSS,
`aria-hidden`; numarasız kartı sırf tutarlılık için numaralandırma. Sağ slot ilk satırın taban çizgisine hizalı.

## Künye / tanım listesi (23.10.2026)

Etiket–değer çiftleri (santral bilgileri, veri durumu) `table.veri` + `tbody.mono` ile DEĞİL, `dl.kunye` ile:
etiket solda sabit kolon, değer kendi kolonunda sola hizalı (vitrin `.vt-tanim` kalıbı). Mono yalnız
`.kunye-sayi` (sayı/tarih/kimlik, tabular); durum ve eksik-veri cümleleri `.kunye-not` gövde ailesi soluk;
uyarı `.kunye-uyari`. Sağa dayalı uzun cümle ve mono düz yazı yasak — «terminal» imzası.

## Tablo

`table.veri` dili: mono sayı sütunları sağa, `th+th/td+td { padding-left }` oluk kuralı
(v2.309 dersi — oluk ilk sütun dolgusuyla sağlanmaz); başlık uppercase ise birim taşımaz.
Ayna/karşılaştırma tablosu: role=table + ✓ hücrelerinde alt-metin kuralı (emsaller.md).

## Durum göstergeleri

- Semantik aile: `--uyari(-metin)` / `--basari(-metin)` — koyu yüz türevleri TANIMLI
  (v2.309); AMBER DURUM RENGİ DEĞİLDİR.
- Durum çipi: nokta + mono etiket; yanıp sönme yasak; alarm rozeti yalnız okunmamış sayısı.
- Dolu/primary düğme sayfada EN FAZLA bir; gerisi outline/ghost.

## Form ızgarası (23.10.2026, v2.468)

Satır içi formlar `.form-izgara`: etiket üstte (`.girdi-etiket`), kontroller 36 px, `auto-fit minmax(200px,1fr)`
hücreler, onay kutuları `.onay-grubu` içinde ve düğme kontrol satırıyla aynı taban çizgisinde; en çok 1100 px.
Satır içi `width/minWidth` YASAK — hücre genişliği ızgaradan. Uzun form yarım sütuna sıkışacaksa kartın altında tam
satır (`.alt-bolum` + eyebrow «Yeni …»). Tehlikeli işlem `.dugme-tehlike` (uyarı rengi, dolgu yok). Satır içi kod
`.kod`. Sayısal tablo `table.veri.sayisal` (gövde ailesi + tabular; mono yalnız kod/kimlik).

## Form ve ayar dili

Panel `.ayar/.girdi/.girdi-etiket/.ayar-durum/.ayar-onay` kalıbı (v2.285-286);
etikette uppercase yok (birimler bozulur). Vitrin formu asla gerçek gönderilmez;
bal küpü `vt-bal` kalıbı korunur.

## Bilgi ayırıcı standardı (23.10.2026, yedinci tur)

Orta nokta «·» bilgi ayırıcısı olarak KULLANILMAZ (iki sayı arasında işlem işareti gibi okunur, etiketsiz bilgileri tek
satıra yığar). Kural tablosu:
- **Farklı türden kısa bilgiler** (sayı, tarih, pencere, durum, kaynak) → `Meta` bileşeni (`src/lib/Meta.tsx`): her bilgi
  kendi dilimi, dilimler ince dikey ayraçla (ayraç her dilimin solunda mutlak; kap −19 px kenar + `clip-path: inset(0 0 0
  19px)` → satır BAŞINDAKİ dilimin ayracı kırpılır; `inset(0)` yetmez, kabın kutusu o şeridi içerir — 23.10 ölçüldü).
- **Kod/yol çipleri** (API uçları) → `.cip.cip-kod`: `.cip` hapının mono içerikli türevi (13 px, 28 px, `--kenar`); eylem
  düğmesi `.dugme.kucuk` (32 px) ile aynı aile — çip bilgi, düğme eylem. Uçlar `.uc-listesi` (eyebrow + `.uc-sira` +
  `.uc-not` Meta). Çip, rozet, telemetri,
  vitrin künyesi aynı bileşen; boş/false öğe atlanır; dilim içinde kırılma yok, dizi dilim sınırından sarar.
- **Aynı karttaki iki sayı** (bugün/yarın, ortalama/standart sapma, alarm/gecikme) → `Kpi.ikinci` {etiket, deger, birim}:
  ana değer büyük, ikincisi kendi etiketi ve birimiyle ayrı satır. «1.914,2 · 1.827,6 MWh» YASAK.
- **Düzyazı / not / KPI alt satırı** → virgül, noktalı virgül, parantez («%92,1 (sıcaklık düzeltmeli %93,0)»).
- **Etiket + niteleyici** (KPI etiketi, tablo satır etiketi) → virgül ya da parantez: «Tahmin hatası (WMAPE), 0–24 saat».
- **Uyarı / not listeleri** → `ul.not-listesi` satır satır (`join(" · ")` yasak).
- **Künye notu** → `.kunye-not` blok satır (durumun altında), satır içi ayraç yok.
- **Grafik**: tooltip başlığı `<b>saat</b> <soluk>geçmiş/tahmin</soluk>`; eksen adı «[yerel saat]»; «şimdi» hapı etiket + değer.
- **Alan adı dürüstlüğü**: `son_scada` = son ÖLÇÜM zaman damgası → etiket «son veri» (yükleme/güncelleme değil).
- Kalan tek orta nokta: avatar baş harfi yer tutucusu («·») ve kod yorumları.
- **Uzun çizgi «—» (23.10, sekizinci tur):** ad + işlem («Edikli GES — arşivle») ve ad + nitelik ayırıcısı olarak YASAK:
  işlem satır listesinde (`ul.islem-listesi`: ad solda, düğme sağda), nitelik `Meta`/virgül/parantezle. Kart başlığındaki
  «Başlık — açıklama» dizgisi kalır; `Kart` onu `.kart-alt` ile tipografik böler (çizgi görünmez). Durum mesajlarında
  nokta / noktalı virgül / iki nokta. KORUNAN: değer yerindeki tek «—», aralıklarda kısa çizgi «P10–P90», eksi «−»,
  tablo «ham → ayarlı», sembolden söz eden cümle, eyebrow etiketleri, sekme başlığı, vitrin başlıkları.

## Durum sözcüğü + neden (23.10.2026, altıncı tur)

Eksik/hesaplanamayan değer tek uzun soluk cümle DEĞİL: kısa durum sözcüğü (`.kunye-durum.eksik`: «Tanımlı değil»,
«Hesaplanamadı», «Belirtilmedi», «Yüklenmedi») + ` · ` + neden (`.kunye-not`). Tire yalnız sayı yerinde (KPI, hücre).
Uzun teknik açıklama (nasıl okunur, yöntem, piyasa kuralı) `<details class="aciklama">` ile katlanır — metin aynen,
kimlik satırı (mod, aralık kaynağı) görünür kalır. Sentetik/model sonucu ölçüm sanılmasın: `.rozet-notr`
«model hesabı · ölçüm değil».

## Boş / yükleniyor / hata durumları

- Boş: `.bos-durum` = başlık satırı (`.bos-bas`, gövde 500) + neden/ilk adım (`p`, soluk); kutu/çerçeve yok.
  «No data» tek satırı ve «— … — …» çift tireli cümle yasak.
- Yükleniyor: iskelet ya da «Yükleniyor…» soluk metin; spinner süsü değil.
- Hata: ne oldu + ne yapılır («sayfayı yenileyin»); özür/jargon yok.
- Yayın kapalıysa dürüst dil: «yayın açılınca» (KanitSeridi emsali).

## Yoğunluk ve ritim

4/8 px ölçeği; grup içi boşluk < gruplar arası (en yaygın slop imzası: her şey eşit 16 px);
satır ≤90ch; mobilde tıklama hedefi ≥44 px; 320 px'te taşma sıfır (üst çubuk ≤359 dolgu
kısma emsali); fold üstü gerçek veri alanı / krom ≥ %50.

## Hareket

Tek orkestrasyon anı (bölüm belirmesi R25: keyframe `from` ile gizleme + fill:backwards,
statik opacity-0 YASAK — v2.391 Ö10 dersi); durum geçişi ≤200 ms; print'te animation:none;
reduced-motion her şeyi keser.
