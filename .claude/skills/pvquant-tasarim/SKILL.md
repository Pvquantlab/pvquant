---
name: pvquant-tasarim
description: PVQuant'ta HER UI/grafik işinde önce bu yüklenir — iki yüzün (vitrin «Ufuk» + panel D1/E2) jetonları, mavi=tahmin/amber=gerçekleşen sözleşmesi, dürüstlük anayasası, grafik karar tablosu, emsaller dizini ve görsel QA betikleri. Genel tasarım skill'lerinin önerileri bu skill'in kurallarıyla çatışırsa BU skill kazanır.
---

# PVQuant tasarım zekâsı (tek doğruluk kaynağı)

Amaç: arayüzün «AI üretti» değil, ciddi bir enerji-analitik ürünü için çalışan deneyimli
bir ekip tasarlamış gibi okunması. Optimize edilen şey «şirinlik» değil: otorite, netlik,
teknik inandırıcılık, veri yoğunluğu, hiyerarşi, tutarlılık, ayırt edicilik.

## Karar sırası (her UI işinde)

1. **Emsal taraması:** [referans/emsaller.md](referans/emsaller.md) — aynı kalıp panelde ya
   da vitrinde çözülmüş mü? Çözülmüşse YENİ kalıp icat edilmez.
2. **Jetonlar:** [referans/jetonlar.md](referans/jetonlar.md) — renk/font/boşluk/köşe yalnız
   jetonlardan. Jeton yoksa yeni değer icat etmek yerine jeton önerisi sunulur.
3. Yeni görsel dil GEREKİYORSA: palet/font/grafik-türü verisi `ui-ux-pro-max`'ten aranır,
   nihai karar `frontend-design` ilkeleriyle gerekçelendirilir, jetona bağlanır.
4. **Grafik işi:** tür [referans/grafik-karar.md](referans/grafik-karar.md) tablosundan;
   option kurulumu [referans/grafik-tema.md](referans/grafik-tema.md) sözleşmesiyle.
5. **Bileşen işi:** [referans/bilesen-dili.md](referans/bilesen-dili.md) — özellikle
   «ne zaman KULLANMA» kuralları.
6. **Bitirmeden:** [referans/anti-slop.md](referans/anti-slop.md) öz-denetimi →
   `betikler/tarama.mjs` (CDP taraması) → [betikler/rubrik.md](betikler/rubrik.md) ile
   ekran görüntüsü yargısı → `web-design-guidelines` denetimi.

## Veto ve istisna

- Bu skill'in jeton/sözleşme kuralları genel skill'lerin stil önerilerini ezer.
- Testle zorlanan kurallar (gizlilik.test, yapi.test pinleri) tartışmasızdır.
- İstisna gerekiyorsa koda değil, önce buradaki ilgili referans dosyasına gerekçesiyle yazılır.

## Bakım sözleşmesi

Her tasarım mührü kapanırken: yeni kalıp → `emsaller.md`'ye bir satır; yeni jeton →
`jetonlar.md`; rubrikte tekrarlayan ihlal → deterministik teste (bkz. grafik-tema.md bekçi
bölümü). Skill çürürse yığın çürür — bu adım mühür ritüelinin defter adımına dahildir.
