# Veri kalitesi sözlüğü (Faz 4 F4-C, v2.598)

Tarih: 12 Kasım 2026. Kod: `src/pvquant/services/kalite_sozlugu.py` (saf, tek yer). Göç: `alembic/versions/v2598_kalite.py`.
Testler: `tests/test_kalite_sozlugu_v2598.py`. API: `GET /v1/sozluk/kalite`. Arşiv tarafı: `docs/TAHMIN-ARSIVI.md`.

## Neden

Altı ayrı «kalite» sözlüğü vardı: `scada_hourly.flag` (CHECK'siz, 10+ değer), `kaynak_saatlik.tamlik`, sayaç `nitelik`,
ölçüm uygunluk `neden`, veri yolu durumu, rapor/web etiketleri. `flag='valid'` süzgeci 31 dosyada 64 satırda elle yazılıydı.
Bir saatin «hesaba girer mi» kararı tek yerde durmalı; kaynaklar değişince (sayaç, bulut, EPİAŞ) sözlük büyür, süzgeçler değil.

## Nitelik (tek küme)

| Kod | Etiket | Hesaba girer | Anlam |
|---|---|---|---|
| `dogrulanmis` | doğrulanmış | evet | bağımsız kaynakla (sayaç/EPİAŞ) çapraz doğrulanmış ölçüm (henüz üretilmez; yer ayrıldı) |
| `olculmus` | ölçülmüş | evet | sahadan gelen, kontrolleri geçen saatlik ölçüm |
| `kismi` | kısmi saat | hayır | saatin 45 dakikasından azı ölçülü |
| `tahmini` | tahmini | hayır | kaynak «tahmini» demiş (sayaç portalı Estimated) |
| `doldurulmus` | doldurulmuş | hayır | kaynak eksik değeri sonradan doldurmuş |
| `elle` | elle girilmiş | hayır | ölçüm cihazından değil |
| `supheli` | şüpheli | hayır | ölçüm var ama fiziksel/istatistiksel şüphe |
| `gecikmis` | gecikmiş | — | saat geçti, veri henüz gelmedi (tazelik) |
| `eksik` | eksik | — | kaynakta o saat için satır yok |
| `gecersiz` | geçersiz | hayır | okunamayan, tekrarlanan, saatlik olmayan |

## `scada_hourly.flag` → Nitelik (CHECK kısıtı = bu küme)

| flag | Nitelik | Not |
|---|---|---|
| `valid` | olculmus | |
| `kisinti` | olculmus | ölçüm geçerli; kısıntı boyutu ayrı — karne/kalibrasyon dışı, kayıp analizi içi (hijyen yazar) |
| `partial_hour` | kismi | kapsama < 45 dk |
| `anomali` | supheli | EPİAŞ gerçek zamanlı üretim anomali işareti |
| `sifir_gunduz` | supheli | **yeni (v2.598):** güneş > 10°, ışınım > 200 W/m², güç 0 — yalnız ışınım kolonu varsa |
| `negative_power`, `night_production`, `over_capacity`, `frozen_value`, `dst_ambiguous` | supheli | |
| `eksik` | eksik | **yeni (v2.598):** kaynakta satır yok (eskiden `unparseable` yazılıyordu) |
| `unparseable`, `duplicate_time`, `gunluk_ozet` | gecersiz | günlük özet aylık toplamlara ayrı yoldan girer |
| `frozen`, `yanlis_yil`, `yanlis_yil_2006` | supheli / gecersiz | eski yazımlar; yeni satırda yazılmaz, raporlar tanır |

Göç kısıtı NOT VALID ekler, sonra doğrulamayı dener: mevcut veri sözlük içindeyse kısıt doğrulanır (test DB: doğrulandı); dışında
değer varsa kısıt NOT VALID kalır (yeni satırlar denetlenir) ve göç NOTICE ile değerleri söyler. Veri sessizce değiştirilmez.

## Amaç → kabul edilen küme (eski süzgeçlerle birebir)

| Amaç | flag kümesi | Eski yazım | Kullananlar |
|---|---|---|---|
| `karne`, `kalibrasyon`, `uzlastirma`, `rapor`, `tazelik` | `valid` | `flag='valid'` | doğruluk karnesi, konformal/ufuk/sapma öğrenme, program sapması, finansal etki, raporlar, son ölçüm zamanı |
| `kayip`, `kullanilabilirlik`, `hijyen` | `valid`, `kisinti` | `flag IN ('valid','kisinti')` | kayıp ayrışımı, hijyen, kullanılabilirlik, fizik beklentisi karşılaştırmaları |

`kalite_sozlugu.sql_kosulu(amac, alias)` SQL parçasını, `pandas_maskesi` aynı kararı pandas tarafında verir. 64 süzgeç (31 dosya,
`src/pvquant/services/*`, `apps/api/main.py`, `apps/worker/main.py`) buna bağlandı; bekçi testi kodda (docstring dışında) ham
`flag='valid'` literal'i kalmadığını doğrular. Yazım yolları (`ingest`, `epias_uretim`, `canli_ornekleme`, hijyen) flag değerini
yazar; süzgeç kullanmaz.

## Diğer sözlüklerin eşlemesi

- `kaynak_saatlik.tamlik`: `measured_complete` → olculmus, `measured_partial` → kismi, `estimated` → tahmini.
- Sayaç `nitelik`: olculmus/tahmini/doldurulmus/elle → aynı adlı Nitelik; `yok` → eksik.
- Ölçüm uygunluk `neden`: `olculdu` → olculmus; `eksik` → eksik; `kismi_saat` → kismi; `bayrak:<flag>` → bayrağın niteliği;
  `sayac:<nitelik>` → sayaç niteliği; `olay:<tur>` → supheli (ölçüm var, olay saati; amaç için dışlanır).
- Tazelik: son geçerli ölçümden 48 saat geçtiyse `gecikmis` (Portföy satırının «2 gün» eşiğiyle aynı); `kalite_sozlugu.tazelik_durumu`.

## Ölçüm satırı künyesi (`scada_hourly` yeni sütunlar)

| Sütun | Anlam | Kim yazar |
|---|---|---|
| `alinma_zamani` | satırın sisteme geliş zamanı (geri doldurma: parti oluşturma zamanı) | ingest, EPİAŞ, canlı |
| `aralik_dk` | kaynak adımı (dk) | ingest (dönüşüm künyesinden), EPİAŞ 60, canlı 60 |
| `kaynak_damga_tipi` | `aralik_basi` / `aralik_sonu` / `anlik`; bilinmiyorsa NULL | EPİAŞ, canlı (`aralik_basi`); dosyada NULL (F4-D zaman sözleşmesi) |
| `kaynak` | `scada_dosya` / `epias` / `canli` / `bulut` / `elle` | hepsi; geri doldurma yalnız partinin açık etiketi varsa |
| `sinir` | ölçüm sınırı (`inverter_ac`, `plant_gross_ac`, `pcc_net`, `settlement`) | EPİAŞ `settlement`; diğerleri NULL (bilinmiyor) |

## Kaynak önceliği (yazımda)

SCADA dosyası birincil kaynaktır: EPİAŞ/canlı satırının üstüne yazar. Ancak hijyenin koyduğu `kisinti` bayrağı ve `kirpma`
işareti yeni `valid` satırla silinmez (bir sonraki hijyen koşusu yeniden değerlendirir). EPİAŞ ve canlı örnekleme `DO NOTHING`
ile yalnız boş saate yazar (değişmedi).

## Düzeltmeler (v2.598)

- **M4 — DST:** `transform.parse_timestamps` yaz saati geçişindeki satırı artık düşürmez. Yok saat (ileri alınan) ileri kaydırılır,
  çift saat sırayla çözülür (çözülemezse standart saat varsayımı); satır `dst_ambiguous` bayrağıyla seriye girmez. Varsayım
  bayrakla görünür, sessiz değil.
- **Boş saat:** saatlik ızgarada kaynak satırı olmayan saat `eksik`; satır var ama sayı okunamıyorsa `unparseable`
  (`n_kaynak_satir` dönüşümden gelir).
- **Beklenmeyen sıfır üretim:** gündüz, ışınım ölçülürken güç 0 → `sifir_gunduz` (şüpheli); karne uyarısı yazar.
- **Rapor çizelgesi:** `frozen_value` ve diğer bütün bayraklar `BAYRAK_AKSIYON`'da karşılık bulur (eskiden yalnız `frozen` vardı).
- **İş sonucu:** `jobs_log.sonuc_json` — iş sözlük dönerse yapılı yazılır; veri yolu durumu regex yerine bunu okur
  (eski satırlarda metin ayrıştırması kalır). «İş başarılı ≠ veri taze» kararı bu alandan verilir.

## Arayüz

Portföy satırı `veri_durumu` {kod, nitelik, etiket, yas_saat} taşır (ortak sözlük). Web rozetlerinin bu alana ve
`GET /v1/sozluk/kalite` etiketlerine bağlanması F4-K (arayüz entegrasyonu) kapsamındadır; bu pakette arayüz değişmedi.
