# Jetonlar — iki yüz, tek sözleşme

Kaynak dosyalar (gerçek değerler HER ZAMAN oradan okunur, burası harita):
- Panel: `web/src/index.css` (`:root` + koyu yüz blokları) — N0–N900 mürekkep merdiveni,
  `--chart-*` uzayı, `--font` (Inter), `--mono` (IBM Plex Mono, tabular-nums), `--display`.
- Vitrin: `web/src/features/vitrin/vitrin.css` — `--vt-*` uzayı. Kök blok (satır 1–60) tarihsel;
  **13.10.2026'dan beri dosyanın SONUNDAKİ «JUA KATMANI» kazanır**: mürekkep #0B0E15, gövde #404551,
  koyu zemin #0B0E15 (hero #05070C), krem bant #FEF0E6, eylem #B11F47 yalnız odak halkasında,
  tek aile Inter Tight. Kaynak envanter: Desktop/jua/jua-tasarim-envanteri.md.

## Veri renk sözleşmesi (İHLAL EDİLEMEZ)

- **Mavi #2D6FB5 = tahmin.** Panel: `--chart-p50-*`, bantlar mavi alfa türevleri.
  Vitrin: `--vt-veri-tahmin`.
- **Amber = YALNIZ gerçekleşen üretim.** Başka hiçbir şeyde kullanılamaz — uyarı rengi
  AYRIDIR (`--uyari`/`--vt-uyari` #B8421F ailesi; koyu yüzde `--uyari-metin` türevleri).
- **İKİ-AMBER KARARI (Mühür A, 05.10.2026):** panel `--chart-actual: #E8940A`, vitrin
  `--vt-veri-gerceklesen: #C27803`. Bu BİLİNÇLİ: amberin tonu zemine göre seçilir —
  koyu/lacivert panel zemininde #E8940A kontrast için, beyaz vitrin zemininde #C27803
  (daha koyu, AA metin-komşuluğu) kullanılır. Kural: «amber tek ANLAM, zemine göre iki ton»;
  üçüncü bir amber tonu icat edilmez, iki ton birbirinin zeminine taşınmaz.
- **Eylem #B11F47 (vitrin):** yalnız düğme/bağlantı/odak; dekor ve grafikte yasak
  (tek istisna: R24 h1 vurgusu — emsaller.md).

## Tipografi rolleri

| Rol | Panel | Vitrin |
|---|---|---|
| Display/başlık | `--display` | Inter Tight **300** (−0,035em, satır 0,96; h2 −0,028em/1,02) |
| Gövde | Inter (`--font`) | Inter Tight 400 (16/24 taban; giriş 19/1,5; hero 22/1,45) |
| Etiket/düğme | — | Inter Tight 500 (eyebrow 12px +0,14em büyük harf; hap düğme 999px) |
| VERİ/eksen/künye | IBM Plex Mono + `tabular-nums` — sayı asla gövde fontuyla dizilmez | **Vitrin istisnası (13.10, kullanıcı kararı):** Inter Tight + `tabular-nums` (300 büyük sayı, 400/500 künye); Plex Mono vitrinde kullanılmaz |

- Etikette `text-transform: uppercase` birimleri bozar (kWp→KWP) — birim taşıyan metne asla.
- Türkçe büyük harf: `lang="tr"` şart; JS `/i` bayrağı İ'yi KATLAMAZ (regex'te sınıf kullan).

## Yüzey kuralları

- Panel çift yüz: koyu **D1 «Düz lacivert»** (zemin #0B1424, kart #17243C, OPAK — cam/doku
  KALKTI, geri gelmez) + açık **E2 «Derin mavi kâğıt»** (zemin #E3E9F2). Tema üçlüsü
  oto|açık|koyu (`pvq_tema`).
- Vitrin (13.10 jua katmanı): üç zemin — beyaz / krem #FEF0E6 / koyu #0B0E15; hero = zemin → video →
  dikey perde (`--vt-jua-perde`, mobil ayrı) → içerik. Koyu yüzeylerde pembe/camgöbeği radyal ışık
  (`--vt-jua-isik`, opaklık .35). Gren ve fotoğraf zeminleri KALKTI. Üst çubuk yüzen cam hap
  (`--vt-cam-*`; anti-slop istisnası, kullanıcı kararı). Marka ışıkları `--vt-jua-gok/lavanta/camgobegi` (#8FD3FF/#AA85FF/#0AB8DC; jua pembesi santral videosuyla çatıştığı için 13.10'da düştü)
  yalnız: h1 italik gradyan vurgusu, birincil düğme halesi, radyal ışık. **Şeftali #FABD8F alınmadı** —
  amber sözleşmesi. Gölge ölçeği `--vt-golge-*` yalnız yükselme anlamında (menü/pencere).
- Köşe ölçeği: vitrin `--vt-r-xs..l/tam` (jua katmanı: r-m 24, r-l 28; altbilgi üst köşe 50; düğme 999); yeni köşe değeri icat edilmez.
- Boşluk ritmi 4/8 px; süre `--vt-sure*` (120/200/320 ms), reduced-motion her animasyonu keser.

## Jeton-dışı değer yasağı

Bileşen kodunda ham hex/px (jeton karşılığı varken) inceleme kapısına takılır;
`betikler/tarama.mjs` computed-style taramasında set-dışı değerleri raporlar.
- **Üst çubuk «Buz cam» (15.10.2026, kullanıcı B seçti; C «derin gök» iki sekmede denendi, «daha az göz yoruyor» ile B):** `--vt-ust-buz: rgba(255,255,255,.80)` + blur(24px) saturate(160%), `--vt-ust-murekkep: #0B1B3C` (yazı/CTA/açılır panel/çekmece), hap 64 px, `--vt-ust-y` 96/88. Siyah hap (#0F131B) kalktı; amber/eylem rengine dokunmaz.
- **Amblem «dolu disk» (15.10.2026, kullanıcı M2 + S4 seçti):** disk radyal altın #FFD866→#F5A300 (`gradientUnits=userSpaceOnUse`, cx 14 cy 13 r 9 @32), 8 ışın 2,7 px currentColor (vitrin) / `--marka` (panel); `.vt-logo__isaret` 30 px; favicon mürekkep kare + aynı işaret. Altın ≠ grafik amberleri (anti-slop istisnası).
