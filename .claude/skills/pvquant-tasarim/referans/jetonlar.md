# Jetonlar — iki yüz, tek sözleşme

Kaynak dosyalar (gerçek değerler HER ZAMAN oradan okunur, burası harita):
- Panel: `web/src/index.css` (`:root` + koyu yüz blokları) — N0–N900 mürekkep merdiveni,
  `--chart-*` uzayı, `--font` (Inter), `--mono` (IBM Plex Mono, tabular-nums), `--display`.
- Vitrin: `web/src/features/vitrin/vitrin.css` satır 1–60 — `--vt-*` uzayı
  (mürekkep #0B1B3C, gövde #4A5974, Gece sisi #E8EDF8, eylem #B11F47, Bricolage + Plex).

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
| Display/başlık | `--display` | Bricolage Grotesque |
| Gövde | Inter (`--font`) | IBM Plex Sans |
| VERİ/eksen/grafik içi | IBM Plex Mono + `tabular-nums` — sayı asla gövde fontuyla dizilmez | IBM Plex Mono |
| Eyebrow etiketi + künye ÇİPİ | — | **Plex Sans** 600/500 (v2.406 kullanıcı turu: etiket veri değil kategori işaretidir; mono yalnız gerçek veri yüzeylerinde — eksen, tablo, pencere şeridi) |

- Etikette `text-transform: uppercase` birimleri bozar (kWp→KWP) — birim taşıyan metne asla.
- Türkçe büyük harf: `lang="tr"` şart; JS `/i` bayrağı İ'yi KATLAMAZ (regex'te sınıf kullan).

## Yüzey kuralları

- Panel çift yüz: koyu **D1 «Düz lacivert»** (zemin #0B1424, kart #17243C, OPAK — cam/doku
  KALKTI, geri gelmez) + açık **E2 «Derin mavi kâğıt»** (zemin #E3E9F2). Tema üçlüsü
  oto|açık|koyu (`pvq_tema`).
- Vitrin: beyaz yüz + «Gece sisi» bantlar; gren/benek SVG dili; gölge ölçeği `--vt-golge-*`
  yalnız yükselme anlamında (menü/pencere).
- Köşe ölçeği: vitrin `--vt-r-xs..l/tam`; yeni köşe değeri icat edilmez.
- Boşluk ritmi 4/8 px; süre `--vt-sure*` (120/200/320 ms), reduced-motion her animasyonu keser.

## Jeton-dışı değer yasağı

Bileşen kodunda ham hex/px (jeton karşılığı varken) inceleme kapısına takılır;
`betikler/tarama.mjs` computed-style taramasında set-dışı değerleri raporlar.
