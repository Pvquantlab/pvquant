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
| Display/başlık | `--display` = **Inter Tight** (22.10.2026 tek tasarım sistemi; Space Grotesk kalktı): h1 26/600 −.02em · h2 20/600 · kart h3 15/600 −.01em (`.kart-bas h3`, cümle düzeni, büyük harf YOK) · giriş hero 64/500 −.03em | Inter Tight **300** (−0,035em, satır 0,96; h2 −0,028em/1,02) |
| Gövde | Inter (`--font`) 14/1,55 · ikincil 13 · tablo 13,5 (optik boyut ekseni küçük puntoda kalır) | Inter Tight 400 (16/24 taban; giriş 19/1,5; hero 22/1,45) |
| Etiket/düğme | Inter Tight 500: eyebrow `.etiket-ust` 12px +.10em büyük harf · nav 14,5 · düğme 13,5 · çip/rozet 12 · sekme 13; düğme/çip/sekme/segment **hap 999** (`--r-hap`) | Inter Tight 500 (eyebrow 12px +0,14em büyük harf; hap düğme 999px) |
| VERİ/eksen/künye | IBM Plex Mono + `tabular-nums` tablo gövdesi, eksen, kod, zaman damgası (mono tablolarda İLK sütun etiket → gövde ailesi). **22.10 istisnası (tek tasarım sistemi):** KPI başlık sayıları `.kpi-dg` / `.ozet .dg` / `.yan-ozet .dg` / `.sayi-buyuk` Inter Tight 500 30px tabular — vitrinin karne sayısıyla aynı kesim; tek jeton (`--display`) ile geri alınabilir | **Vitrin istisnası (13.10, kullanıcı kararı):** Inter Tight + `tabular-nums` (300 büyük sayı, 400/500 künye); Plex Mono vitrinde kullanılmaz |

- Etikette `text-transform: uppercase` birimleri bozar (kWp→KWP) — birim taşıyan metne asla.
- Türkçe büyük harf: `lang="tr"` şart; JS `/i` bayrağı İ'yi KATLAMAZ (regex'te sınıf kullan).

## Yüzey kuralları

- Panel çift yüz (22.10.2026 tek tasarım sistemi, `docs/PANEL-TASARIM-2026-10-22.md`): koyu yüz vitrinin
  gecesi — zemin **#0B0E15** (= `--vt-gece`), kart **#14161D** OPAK (zemin + %3,5 beyaz; cam/doku KALKTI, geri
  gelmez), kenar beyaz .12, metin #FFFFFF / ikincil #D2D5DC / soluk #A3A9B4. Açık yüz nötr gri — zemin **#E8EAEE**
  (kart/zemin 1,20 ≥ 1,15 hedefi), kart beyaz, kenar #D9DBE1, mürekkep vitrinin merdiveni #0B0E15 / #404551 / #5B6270
  (vitrinin #6B7280'i 13 px'te zeminde 4,3 kalıyordu). D1 laciverti (#0B1424) ve E2 mavi-gri kâğıdı (#E3E9F2) TARİHSEL.
  Üçüncü tur (22.10 gece, `docs/PANEL-TUR3-2026-10-22.md`): tip ölçeği gövde 15 · ikincil 13,5 · etiket 12,5 · kart 16 ·
  bölüm 21 · sayfa 28 · KPI 32 · nav 15,5 · tablo 14 · düğme 14/34 px · girdi 14/36 px; grafik eksen/lejant 12–13,5 px;
  `.icerik` 1840 px; yan menü 248; KOYU üç kademe zemin #0B0E15 / yan #10131B / kart #181B23, kenar .14, yüzey .07.
  İkinci denetim (22.10 akşam, `docs/PANEL-DENETIM-2026-10-22.md`): açık yan menü `--yan` #F2F3F5 (zeminden bir ton
  açık); ızgara koyu `--chart-grid` .14 / `--izgara` .11, açık .13 / .12; açık `--ch-dusuk` #7F8B9A (≥3:1 grafik nesnesi);
  kontroller: `.dugme` ≥32 px, sekme/segment 30 px; açıklama paragrafı `p.soluk` 13,5 px.
  Tema üçlüsü oto|açık|koyu (`pvq_tema`). Birincil düğme `.dugme-ana` = vitrinin dolu hapı: açıkta mürekkep/beyaz yazı,
  koyuda beyaz/mürekkep yazı; yeşil `--marka` seçim/durum/odak rengi olarak kalır (nav aktif, rozet-ok, odak halkası, amblem).
  Giriş ekranı sol yüzü: #0B0E15 + jua radyal ışıkları (lavanta/camgöbeği), vurgu düz gök mavisi #8FD3FF.
- Vitrin (13.10 jua katmanı): üç zemin — beyaz / krem #FEF0E6 / koyu #0B0E15; hero = zemin → video →
  dikey perde (`--vt-jua-perde`, mobil ayrı) → içerik. Koyu yüzeylerde pembe/camgöbeği radyal ışık
  (`--vt-jua-isik`, opaklık .35). Gren ve fotoğraf zeminleri KALKTI. Üst çubuk yüzen cam hap
  (`--vt-cam-*`; anti-slop istisnası, kullanıcı kararı). Marka ışıkları `--vt-jua-gok/lavanta/camgobegi` (#8FD3FF/#AA85FF/#0AB8DC; jua pembesi santral videosuyla çatıştığı için 13.10'da düştü)
  yalnız: h1 italik gradyan vurgusu, birincil düğme halesi, radyal ışık. **Şeftali #FABD8F alınmadı** —
  amber sözleşmesi. Gölge ölçeği `--vt-golge-*` yalnız yükselme anlamında (menü/pencere).
- Köşe ölçeği: vitrin `--vt-r-xs..l/tam` (jua katmanı: r-m 24, r-l 28; altbilgi üst köşe 50; düğme 999); panel (22.10)
  `--r` 8 kontrol/girdi · `--rk` 12 kart/KPI · `--r-hap` 999 düğme/çip/sekme/segment/arama · pencere (palet, zil) 16;
  yeni köşe değeri icat edilmez.
- Panel yerleşimi (22.10): yan menü 236 px; `.icerik` max 1600 px, ana sütunda ORTALANIR (margin auto), dolgu 28/36,
  mobil 16; ızgara oluğu 16; kart dolgusu 20/22; satır içi `minmax(Npx, 1fr)` daima `minmax(min(Npx, 100%), 1fr)`.
- Boşluk ritmi 4/8 px; süre `--vt-sure*` (120/200/320 ms), reduced-motion her animasyonu keser.

## Jeton-dışı değer yasağı

Bileşen kodunda ham hex/px (jeton karşılığı varken) inceleme kapısına takılır;
`betikler/tarama.mjs` computed-style taramasında set-dışı değerleri raporlar.
- **Üst çubuk «Buz cam» (15.10.2026, kullanıcı B seçti; C «derin gök» iki sekmede denendi, «daha az göz yoruyor» ile B):** `--vt-ust-buz: rgba(255,255,255,.80)` + blur(24px) saturate(160%), `--vt-ust-murekkep: #0B1B3C` (yazı/CTA/açılır panel/çekmece), hap 64 px, `--vt-ust-y` 96/88. Siyah hap (#0F131B) kalktı; amber/eylem rengine dokunmaz.
