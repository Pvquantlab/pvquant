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

## Tablo

`table.veri` dili: mono sayı sütunları sağa, `th+th/td+td { padding-left }` oluk kuralı
(v2.309 dersi — oluk ilk sütun dolgusuyla sağlanmaz); başlık uppercase ise birim taşımaz.
Ayna/karşılaştırma tablosu: role=table + ✓ hücrelerinde alt-metin kuralı (emsaller.md).

## Durum göstergeleri

- Semantik aile: `--uyari(-metin)` / `--basari(-metin)` — koyu yüz türevleri TANIMLI
  (v2.309); AMBER DURUM RENGİ DEĞİLDİR.
- Durum çipi: nokta + mono etiket; yanıp sönme yasak; alarm rozeti yalnız okunmamış sayısı.
- Dolu/primary düğme sayfada EN FAZLA bir; gerisi outline/ghost.

## Form ve ayar dili

Panel `.ayar/.girdi/.girdi-etiket/.ayar-durum/.ayar-onay` kalıbı (v2.285-286);
etikette uppercase yok (birimler bozulur). Vitrin formu asla gerçek gönderilmez;
bal küpü `vt-bal` kalıbı korunur.

## Boş / yükleniyor / hata durumları

- Boş: yönlendiren tek cümle + (varsa) ilk adım bağlantısı; «No data» tek satırı yasak.
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
