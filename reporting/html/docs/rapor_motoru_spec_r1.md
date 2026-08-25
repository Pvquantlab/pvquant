# PVQuant — Rapor Motoru Spesifikasyon Prompt'u — R1
## PVQuant — Report Engine Specification Prompt — R1

Bu belge iki dilde aynı prompt'u içerir. Bir yapay zekâ ajanına ya da geliştirici ekibe
verilecek şekilde yazılmıştır; kopyalanıp doğrudan kullanılabilir.

This document contains the same prompt in two languages. It is written to be handed to an
AI agent or a development team; it can be copied and used directly.

**R1 revizyonu (25 Ağustos 2026).** Ölçüm tabanı: `faz2-ui @ bfa0fa1` (v2.190); kayıt
makamı `reporting/html/denetim.py` + `tests/test_rapor_tutarlilik.py`. İşlenen kalemler:
**(1)** sayım düzeltmesi — ilk sürüm "22 denetim" diyordu, liste 21 maddeydi; sayım artık
kod envanterine bağlıdır (D1–D26, kanonik koşuda 37 geçen kayıt + render R-serisi).
**(2)** Madde 17 eşitlik→üst-sınır (D6, v2.132 anlam düzeltmesi). **(3)** D19–D26 ek
envanteri; 21 maddeye motor kodları köşeli parantezle işlendi. Bunlar dışında metin ilk
sürümle birebir aynıdır. Bu bir belge teslimidir, depo mührü değildir.

**R1 revision (25 August 2026).** Measured against `faz2-ui @ bfa0fa1` (v2.190); the
registry of record is `reporting/html/denetim.py` + `tests/test_rapor_tutarlilik.py`.
Items applied: **(1)** the count fix — the first edition said "22 checks" over a 21-item
list; the count is now tied to the code registry (D1–D26, 37 passing records in the
canonical run, plus the render R-series). **(2)** Item 17 equality → upper bound (D6, the
v2.132 semantic fix). **(3)** The D19–D26 supplementary inventory; engine codes are
annotated onto the 21 items in square brackets. Everything else is verbatim from the
first edition. This is a document delivery, not a repository seal.

---
---

# TÜRKÇE

## Rol ve amaç

Bir güneş santrali üretim tahmini SaaS ürününün **rapor motorunu** yazıyorsun. Motor, bir
tahmin koşusunun çıktısını (JSON) alır ve 16 sayfalık, müşteriye teslim edilebilir bir
"Üretim Tahmini ve Doğruluk Raporu" üretir: tek dosya HTML + PDF.

Bu bir belge biçimlendirme işi değil. **Raporun tek işi, üretilen sayıların doğru ve
birbiriyle tutarlı olduğunu okurun kendi denetleyebileceği biçimde göstermektir.** Güzel
görünen ama kendi içinde çelişen bir rapor, çirkin ama tutarlı bir rapordan daha zararlıdır:
müşteri bir çelişki bulduğunda tüm sayılara olan güvenini kaybeder.

## Mutlak kurallar

Bu dört kural hiçbir koşulda esnetilmez. Bunları ihlal eden bir çıktı **yayımlanmaz**.

1. **Hiçbir sayı elle yazılmaz.** Sayfada görünen her değer, gösterdiği veriden hesaplanır.
   Metin içindeki sayılar da buna dâhildir ("dönem toplamı 336,3 MWh" cümlesindeki sayı da
   toplamdan gelir). Şablon metninde sabit sayı bırakılamaz.
2. **Aynı büyüklük her sayfada aynı değeri gösterir.** İki sayfada görünen bir değer tek bir
   hesaptan türetilir, iki ayrı yerde hesaplanmaz.
3. **Veri yoksa sıfır yazılmaz, "—" yazılır.** Ölçülmemiş gün, gece saati, tamamlanmamış ay,
   künyede olmayan alan: hepsi "—". Sıfır bir ölçümdür, eksiklik değil.
4. **Bir sayı hesaplanamıyorsa onu kullanan cümle de basılmaz.** Eksik bir alan cümlenin
   ortasında "—" olarak görünemez.

## Girdi sözleşmesi

Motor tek bir JSON nesnesi alır. Zorunlu alanlar eksikse motor **hata verip durur**; kısmi
rapor üretmez.

```
plant           ad, koordinat, yükseklik, kurulu_dc_mwp, sebeke_ac_mwe, egim, azimut,
                izleyici, panel_modeli, inverter_modeli, saat_dilimi
                (R1 — D26: koordinat aralığı ile saat_dilimi/model boş-değilliği denetlenir)
forecast        horizon_start, horizon_end, daily[], hourly[]
                daily[]  : tarih, p10, p50, p90   (MWh/gün)
                hourly[] : zaman_damgasi, p10, p50, p90   (kW)
accuracy        report_card[] : tarih, wmape_0_24, wmape_24_72, naif_wmape, skill,
                                olculdu (bool)
                uninterrupted_days
                kapsama[] : karneyle hizalı gün-içi kapsama yüzdesi       (R1 — D19)
                esik : kapsama_pct, kucuk_orneklem_gun                    (R1 — D19/D20)
calibration     physics_mape, train_mape, holdout_mape, holdout_split,
                steps[] : ad, delta_puan
                coefficients : eta_bos, bifacial_kazanc, kullanilan_saat, tarih
scada           quality_flags[] : bayrak, saat, aksiyon
                monthly_coverage[] : ay, gecerli_saat, toplam_saat, bayrak_kirilimi
                arsiv_baslangic, arsiv_bitis
climate         monthly_history{yil: [12 aylık MWh]}, last12[]
error_dist      matrix : saat × gün |p50 − gerçek| — ölçümsüz hücre boş   (R1 — v2.2, D25)
run             mode (A|B|C), model, zaman_damgasi, rapor_kimligi, musteri, iletisim,
                meteo_source (biçimce serbest)                            (R1 — v2.2, D26)
```

**Kısmi veri davranışı:** Bir bölümün gerektirdiği alanlar yoksa o bölüm basılmaz; yerine tek
satır "veri eksik (gereken: …)" konur. Bölüm yarım basılmaz.

## Hesaplama kuralları

Aşağıdaki tanımlar bağlayıcıdır. Farklı bir tanım kullanılamaz.

| Büyüklük | Tanım |
|---|---|
| Dönem toplamı P50 | `Σ daily[].p50` |
| Dönem toplamı P10/P90 | Kantillerin toplamı **değildir**. Günler kısmen bağımsız olduğundan dönem bandı ayrı hesaplanır; hangi yöntemin kullanıldığı raporda yazılır. |
| Kapasite faktörü | `toplam_uretim / (plant.sebeke_ac_mwe × takvim_saati)` — **MWp değil, MWe.** `sebeke_ac_mwe` yoksa bu gösterge basılmaz. *(bekçi: D10)* |
| WMAPE | `Σ|tahmin − gerçekleşen| / Σ gerçekleşen` |
| Kazanç (skill) | `1 − (wmape_tahmin / wmape_naif)` |
| Naif referans | Güneş açısına göre ölçeklenmiş süreklilik. Ham süreklilik kullanılmaz. |
| Kesintisiz doğrulama | Bugünden geriye doğru, ilk ölçülmemiş güne kadar olan gün sayısı. **Tek bir yerde hesaplanır.** |
| Kapsama | `kalite_süzgecini_geçen_saat / toplam_saat` |
| Uzun dönem ortalaması | Yalnızca **tam** yılların ortalaması. Kısmi yıl hiçbir ortalamaya girmez. |
| Değişkenlik katsayısı | `standart_sapma / ortalama`, tam yıllar üzerinden |
| Pxx (yıllık) | `P50 − z × σ`, z: P75→0,6745 · P90→1,2816. Normal varsayımı **yalnızca yıllık eğride** kullanılır; günlük/saatlik bantlar kantil yöntemiyle üretilir. |
| Kalibrasyon iyileşmesi | `(physics_mape − holdout_mape) / physics_mape` |

## Zorunlu tutarlılık denetimleri

Motor, rapor yayımlanmadan önce aşağıdaki denetimleri **otomatik koşturur**. Herhangi biri
başarısız olursa rapor üretilmez; hangi denetimin neden düştüğü rapor edilir.
*(R1: köşeli parantezdeki kodlar motorun kayıt makamındaki karşılıklardır — ölçüm
`denetim.py @ bfa0fa1`. "render-…" kodları sayfa üretiminden SONRA koşan render
denetimine aittir.)*

**Toplam ve türev denetimleri**
1. Günlük P50 toplamı = dönem toplamı P50 (yuvarlama toleransı 0,1) `[D1]`
2. Saat × gün matrisinin sütun toplamları = günlük P50 değerleri `[D3]`
3. İklim matrisinin son satırı = iklim zarfının orta çizgisi `[D11]`
4. Her karne satırında `skill = 1 − wmape/naif` (tolerans 0,5 puan) `[D4]`
5. Yıllık Pxx değerleri, açıklanan σ ve z ile yeniden hesaplanabilir `[D17]`
6. Şelale: `başlangıç + Σ adımlar = bitiş` (tolerans 0,1 puan). **Tutmuyorsa şelale
   basılmaz** — eksik bir adım vardır. `[D2]`
7. Şelalede yazan iyileşme yüzdesi, başlangıç ve bitişten yeniden hesaplanabilir `[D12]`

**Sayfalar arası denetimler**
8. Aynı büyüklüğün tüm sayfalardaki değerleri özdeş (kesintisiz doğrulama gün sayısı,
   kapsama oranı, ortalama kazanç, CV, arşiv dönemi, kurulu güç, panel/inverter modeli)
   `[mimari: tek-kaynak token — aynı büyüklük tek hesaptan türetilir; künye display
   örneği D23]`
9. Şekil açıklamalarında geçen her sayı, şeklin verisinden türetilmiş `[ilke: D21 ailesi
   — metin gerçeğe vurulur; uygulamalar D20 · D22 · D25(iii)]`
10. İçindekilerdeki sayfa numaraları gerçek sayfalarla eşleşiyor `[render-R1/render-R3]`
11. EK-A'daki "Nerede" sütunu var olan sayfalara işaret ediyor `[render denetimi —
    "Nerede" referansları 1–16 içinde]`

**Fiziksel makullük denetimleri**
12. Saatlik profil gün içinde tek tepeli ve sürekli: ardışık saatler arasında fiziksel
    olmayan sıçrama yok `[D8 tek-tepe + D14 süreklilik]`
13. Tepe güç ≤ kurulu DC güç `[D13]`
14. Bifacial kazanç %0–12 aralığında (dışındaysa "şüpheli kalibrasyon" işareti **konur**)
    `[D7 — bifacial bacağı]`
15. Sistem verimi 0,80–0,98 aralığında `[D7 — η_BoS bacağı]`
16. Kalibrasyonda kullanılan gündüz saati ≤ pencere_günü × 14 `[D5]`
17. Arşivdeki toplam saat ≤ dönem_günü × 24 (tolerans +%1). Kapasiteyi **aşmak** aritmetik
    olarak imkânsızdır ve hatadır; arşiv içindeki boşluk normaldir ve kapsama bölümünde
    zaten dürüstçe raporlanır. *(R1 — v2.132 anlam düzeltmesi: ilk sürümdeki eşitlik±%1
    kuralı kusursuz arşiv varsayıyordu.)* `[D6]`
18. Holdout MAPE hedefin üstündeyse gösterge kartı **kırmızı** basılır; eşik ile değer
    arasındaki yön tutarlı olmalı `[D16]`

**Zaman denetimleri**
19. Saatlik profil panellerinde gösterilen günler tahmin ufkunun içinde `[D9]`
20. Tahmin evrimi grafiğindeki hedef gün tahmin ufkunun içinde `[D9 — hedef gün aynı
    denetimde]`
21. Karne penceresi ile SCADA arşiv dönemi çakışıyor `[D15]`

**Ek envanter — motorda doğan denetimler (R1)**

Aşağıdaki kodlar bu belgenin ilk sürümünden sonra motorun kendisinde doğdu. D10 ve D18
yukarıdaki kuralların bekçileridir: D10 kapasite faktörünün MWe koşulunu (alan yoksa
gösterge ve tüketen cümleler basılmaz), D18 karne bütünlüğünü (30 takvim satırı,
ölçülmemiş gün boş kalır, kesintisiz-doğrulama kartı karne kuyruğuyla çapraz denetlenir)
tutar.

- **D19** — gün içi kapsaması eşik altındaki gün karnede skorlanamaz: kapsama < eşik iken
  `olculdu=true` hatadır.
- **D20** — küçük örneklem uyarısı ↔ geçerli gün sayısı tutarlı; uyarı metni geçerli gün
  sayısını taşır. Uyarı veriden türetilir, elle ezilemez.
- **D21** — kapak dönemi ↔ günlük seri: uçlar birebir, tarihler ardışık takvim günleri,
  gün sayısı tutarlı. Ailenin ilke cümlesi buradan çıkar: anlatı/display DENETLENENDİR —
  metin gerçeğe vurulur, gerçek metinden türetilmez.
- **D22** *(3 kayıt)* — kalibrasyon anlatısı ↔ katsayı alanları. Çıpa başına üç durum:
  anlatı söz etmiyorsa iddia yok, kayıt yok; söz edip alan boşsa kanıtsız iddia (hata);
  ikisi de varsa değer alandan doğrulanır.
- **D23** *(2 kayıt)* — saha künyesi display'i ↔ plant alanları (MWp ve MWe bacakları).
  Display serbest sunum metnidir ve alandan bağımsız bayatlayabilir; hüküm makamı alandır.
- **D24** *(3 kayıt)* — olasılık bandı tutarlılığı: (i) girdi bütünlüğü — bant yarım
  olamaz, günlük yarı-genişlikler ya tam ya boş ve toplam uçlarıyla birlikte yaşar;
  (ii) bantlıysa aritmetik — P10 < P50 < P90; (iii) blok aynası — bant varken bantsızlık
  açıklaması basılamaz, bant yokken açıklama bloğu dolu olmalı ve toplam iddiası taşıyamaz.
- **D25** *(3 kayıt)* — saat × gün hata matrisi: (i) boyutlar tutarlı, değerler ≥ 0,
  ölçümsüz hücre boştur; (ii) saat marjinali hata eğrisiyle ±0,02 tutar — matris ve eğri
  aynı fotoğraftan gelir, ayrışmaları bayat/uydurma işaretidir; (iii) başlık ve iddia
  metni matrisin gerçek kapsamını taşır.
- **D26** — künye alanları: koordinatlar aralıkta, saat dilimi ve model adı boş değil.
  Alanlar toptan yoksa iddia yok sayılır ve geçer; var olan alan yanlışsa hata. Meteo
  kaynağı biçimce serbesttir — sağlayıcı adları sözlükle kapılanmaz.

Kayıt makamı sayımı: 26 kod (D1–D26), kanonik koşuda **37 geçen kayıt** — bazı kodlar
birden çok kayıt üretir (D7 iki bacak; D22 üç çıpa; D23 iki, D24 üç, D25 üç bacak).
Render denetimi (R serisi) bu sayımın dışındadır ve sayfa üretiminden sonra koşar.

## Metin kuralları

- **Şablon metninde sabit sayı bırakılmaz.** Her sayı ya veriden gelir ya da cümle kurulmaz.
  Örnek: "en geniş bant 21 Ağustos'tadır (±4,0 MWh)" cümlesi veriden üretilir; "±%15'e kadar
  genişler" gibi genel ifadeler ancak veriyle doğrulanabiliyorsa yazılır.
- **İç terimler müşteri diline çevrilir:** "run" → "tahmin", "holdout MAPE" → "bağımsız testte
  hata", `yanlis_yil` → "hatalı yıl bloğu". Kısaltmalar birim olarak kalabilir (WMAPE, MAPE).
- **Kötü sonuç gizlenmez.** Zayıf gün karnede kalır, bedel ödeten kalibrasyon adımı şelalede
  görünür, bilinen sınırlar ayrı bölümde yazılır. Bu bölüm ürünün borç listesiyle aynı dili
  konuşur: bir borç kapanınca rapordaki madde de kalkar.
- **Anlatı, veriyle çelişemez.** "Kalibrasyon karşılaştırması raporlanmıyor" cümlesi, aynı
  raporda kalibrasyon şelalesi varken basılamaz. Anlatı cümleleri, kullandıkları alanların
  varlığına göre koşullu üretilir.

## Çizim kuralları

- **Eksenler veriye göre ölçeklenir.** Tepe gücü 2,8 MW olan bir santralin saçılım grafiği
  0–10 MW ekseninde çizilmez. Eksen üst sınırı verinin azamisine göre belirlenir.
- **Sıfırdan başlamayan eksen kullanılıyorsa şekil açıklamasında yazılır.**
- **Her şekil kendi lejantını taşır**; okur sayfayı yukarı taramak zorunda kalmaz.
- **Her grafik bir iddia taşır ve o iddianın sayısı grafiğin içindedir.** Örnek: "±%10
  koridorunda gün-öncesi %59 · 24–72 s %40".
- **Renk anlamı sabittir:** marka rengi = veri ve yapı; kum tonu = belirsizlik ve büyüklük;
  amber ve kırmızı = **yalnızca** durum. Büyüklük göstermek için uyarı rengi kullanılmaz.
- **Isı çizelgelerinde tek renk tonlaması** kullanılır ve sayı her hücrede koyu kalır.
- **Etiketler çakışmaz.** Eğri üzerine düşen etiket, eğrinin boş tarafına alınır.
- **Değişimler yüzde puanıysa etiket "puan" yazar** ("−1,8 puan"), yüzde yazmaz.

## Yerleşim kuralları

- Her sayfa **tam tek A4**. Taşma sessiz bir bozulmadır: içerik kırpılır, genellikle altbilgi
  ve son çizelge kaybolur.
- Motor her sayfa için sayfa sayısını ölçer; 1'den fazlaysa **hata verir ve taşan sayfayı
  bildirir**. Bu denetim CI adımı olarak koşar.
- Metin bir kutunun dışına taşamaz. Taşıyorsa metin kısaltılır, kutu büyütülmez.
- Şekil açıklamaları cümle ortasında kesilemez.

## Kabul ölçütü

Rapor şu koşullarda yayına hazırdır:

- [ ] Denetim envanterinin tamamı geçti — kod bazlı sayım: D1–D26 (kanonik koşuda 37
  kayıt) + render R-serisi temiz *(R1: ilk sürümdeki "22" sayımı 21 maddelik listeyle
  çelişiyordu; sayım kod envanterine bağlandı)*
- [ ] 16 sayfanın her biri tek A4'e sığdı
- [ ] Hiçbir sayfada "—" dışında eksik veri işareti yok, sıfırla doldurulmuş alan yok
- [ ] Şablon metninde veriden gelmeyen tek bir sayı kalmadı
- [ ] Aynı büyüklük tüm sayfalarda aynı değeri gösteriyor
- [ ] Eksenler veriye göre ölçeklenmiş
- [ ] Anlatı cümleleri gösterdikleri veriyle çelişmiyor
- [ ] Bilinen sınırlar bölümü ürünün güncel borç listesiyle örtüşüyor

## Çıktılar

1. `rapor.html` — tek dosya, yazı tipleri gömülü, dış bağımlılık yok
2. `rapor.pdf` — aynı içerikten üretilmiş, 16 sayfa
3. `denetim.json` — koşan tüm denetimlerin sonucu, geçen/kalan ayrımıyla *(R1 notu: bir
   kod birden çok kayıt üretebilir — kanonik koşuda 26 kod, 37 geçen kayıt)*
4. Çıkış kodu: denetimlerden biri düştüyse sıfırdan farklı

---
---

# ENGLISH

## Role and goal

You are building the **report engine** for a solar production forecasting SaaS. The engine
takes the output of a forecast run (JSON) and produces a 16-page, client-deliverable
"Production Forecast and Accuracy Report": a single-file HTML plus a PDF.

This is not a document formatting task. **The report's only job is to let the reader verify
for themselves that the numbers are correct and mutually consistent.** A beautiful report
that contradicts itself is worse than a plain one that does not: the moment a client finds
one contradiction, they stop trusting every number in the document.

## Absolute rules

These four rules are never relaxed. Output that violates them is **not published**.

1. **No number is written by hand.** Every value on the page is computed from the data it
   depicts — including numbers inside sentences. No literal number may survive in template
   prose.
2. **The same quantity shows the same value on every page.** A value appearing twice is
   derived once, not computed in two places.
3. **Missing data is printed as "—", never as zero.** Unmeasured days, night hours,
   incomplete months, absent nameplate fields: all "—". Zero is a measurement, not an absence.
4. **If a number cannot be computed, the sentence that uses it is not printed either.** A
   missing field must never appear as "—" in the middle of a sentence.

## Input contract

The engine takes a single JSON object. If required fields are missing it **fails loudly**;
it never emits a partial report.

```
plant           name, coordinates, elevation, dc_capacity_mwp, ac_grid_mwe, tilt, azimuth,
                tracker, module_model, inverter_model, timezone
                (R1 — D26: coordinate range and timezone/model non-emptiness are checked)
forecast        horizon_start, horizon_end, daily[], hourly[]
                daily[]  : date, p10, p50, p90   (MWh/day)
                hourly[] : timestamp, p10, p50, p90   (kW)
accuracy        report_card[] : date, wmape_0_24, wmape_24_72, naive_wmape, skill, measured
                uninterrupted_days
                coverage[] : intra-day coverage %, aligned with the report card (R1 — D19)
                thresholds : coverage_pct, small_sample_days                  (R1 — D19/D20)
calibration     physics_mape, train_mape, holdout_mape, holdout_split,
                steps[] : name, delta_points
                coefficients : eta_bos, bifacial_gain, hours_used, date
scada           quality_flags[] : flag, hours, action
                monthly_coverage[] : month, valid_hours, total_hours, flag_breakdown
                archive_start, archive_end
climate         monthly_history{year: [12 monthly MWh]}, last12[]
error_dist      matrix : hour × day |p50 − actual| — unmeasured cells empty  (R1 — v2.2, D25)
run             mode (A|B|C), model, timestamp, report_id, customer, contact,
                meteo_source (free-form)                                     (R1 — v2.2, D26)
```

**Partial-data behaviour:** if a section's required fields are absent, the section is not
printed; a single line "data missing (required: …)" takes its place. Sections are never
printed half-full.

## Computation rules

The following definitions are binding. No alternative definition may be substituted.

| Quantity | Definition |
|---|---|
| Period total P50 | `Σ daily[].p50` |
| Period total P10/P90 | **Not** the sum of the daily quantiles. Days are partially independent, so the period band is computed separately; the method used is stated in the report. |
| Capacity factor | `total_production / (plant.ac_grid_mwe × calendar_hours)` — **MWe, not MWp.** If `ac_grid_mwe` is absent, the indicator is not printed. *(guard: D10)* |
| WMAPE | `Σ\|forecast − actual\| / Σ actual` |
| Skill | `1 − (wmape_forecast / wmape_naive)` |
| Naive reference | Solar-angle-scaled persistence. Raw persistence is not used. |
| Uninterrupted verification | Days back from today until the first unmeasured day. **Computed in exactly one place.** |
| Coverage | `hours_passing_quality_filter / total_hours` |
| Long-term average | Average of **complete** years only. A partial year enters no average. |
| Coefficient of variation | `stdev / mean`, over complete years |
| Pxx (annual) | `P50 − z × σ`, z: P75→0.6745 · P90→1.2816. The normal assumption applies **only to the annual curve**; daily and hourly bands come from quantile methods. |
| Calibration improvement | `(physics_mape − holdout_mape) / physics_mape` |

## Mandatory consistency checks

The engine **runs these automatically** before publishing. If any check fails, no report is
produced and the failing check is reported with its reason.
*(R1: bracketed codes are the counterparts in the engine's registry of record — measured
against `denetim.py @ bfa0fa1`. "render-…" codes belong to the render audit that runs
AFTER page generation.)*

**Totals and derivations**
1. Sum of daily P50 = period total P50 (rounding tolerance 0.1) `[D1]`
2. Column sums of the hour × day matrix = the daily P50 values `[D3]`
3. Bottom row of the climate matrix = the mid-line of the climate envelope `[D11]`
4. For every report-card row, `skill = 1 − wmape/naive` (tolerance 0.5 points) `[D4]`
5. Annual Pxx values are reproducible from the stated σ and z `[D17]`
6. Waterfall: `start + Σ steps = end` (tolerance 0.1 points). **If it does not close, the
   waterfall is not printed** — a step is missing. `[D2]`
7. The improvement percentage shown is reproducible from start and end `[D12]`

**Cross-page checks**
8. The same quantity is identical on every page it appears (uninterrupted days, coverage,
   average skill, CV, archive period, installed capacity, module/inverter model)
   `[architecture: single-source tokens — each quantity is derived once; nameplate display
   instance: D23]`
9. Every number inside a figure caption is derived from that figure's data `[principle:
   the D21 family — text is checked against the data; instances D20 · D22 · D25(iii)]`
10. Page numbers in the table of contents match the actual pages `[render-R1/render-R3]`
11. The "Where" column in Appendix A points to pages that exist `[render audit — "Where"
    references within 1–16]`

**Physical plausibility**
12. The hourly profile is single-peaked and continuous: no non-physical jumps between
    consecutive hours `[D8 single-peak + D14 continuity]`
13. Peak power ≤ installed DC capacity `[D13]`
14. Bifacial gain within 0–12% (outside this range, the "suspect calibration" flag **is
    set**) `[D7 — bifacial leg]`
15. System efficiency within 0.80–0.98 `[D7 — η_BoS leg]`
16. Daylight hours used in calibration ≤ window_days × 14 `[D5]`
17. Total archive hours ≤ period_days × 24 (tolerance +1%). **Exceeding** the capacity is
    arithmetically impossible and fails the check; gaps inside the archive are normal and
    are already reported honestly in the coverage section. *(R1 — the v2.132 semantic fix:
    the first edition's equality±1% rule assumed a gapless archive.)* `[D6]`
18. If holdout MAPE exceeds its target, the indicator card prints **red**; the direction of
    the threshold and the value must agree `[D16]`

**Time checks**
19. Days shown in the hourly profile panels fall inside the forecast horizon `[D9]`
20. The target day of the forecast-evolution chart falls inside the forecast horizon
    `[D9 — the target day is covered by the same check]`
21. The report-card window overlaps the SCADA archive period `[D15]`

**Supplementary inventory — checks born in the engine (R1)**

The codes below were born in the engine itself after this document's first edition. D10
and D18 guard rules stated above: D10 enforces the capacity factor's MWe condition (no
field → no indicator and no consuming sentences), D18 enforces report-card integrity
(30 calendar rows, unmeasured days stay empty, the uninterrupted-verification card is
cross-checked against the card's tail).

- **D19** — a day whose intra-day coverage falls below the threshold cannot be scored in
  the report card: coverage < threshold with `measured=true` is an error.
- **D20** — the small-sample warning agrees with the valid-day count, and the warning text
  carries that count. The warning is derived from data and cannot be hand-set.
- **D21** — cover period ↔ daily series: endpoints match exactly, dates are consecutive
  calendar days, the day count agrees. The family's principle comes from here: narrative
  and display are THE AUDITED, not the source — text is checked against the data, never
  the data derived from text.
- **D22** *(3 records)* — calibration narrative ↔ coefficient fields. Three states per
  anchor: no mention → no claim, no record; mention with an empty field → an unbacked
  claim (error); both present → the value is verified from the field.
- **D23** *(2 records)* — the site nameplate display ↔ plant fields (MWp and MWe legs).
  The display is free-form presentation text and can go stale independently of the
  fields; the fields are the authority.
- **D24** *(3 records)* — probability-band consistency: (i) input integrity — no
  half-band: daily half-widths are either complete or entirely empty, and live together
  with the period endpoints; (ii) if banded, arithmetic — P10 < P50 < P90; (iii) block
  mirror — the no-band explanation cannot print while a band exists, and with no band the
  explanation block must be present and may not claim totals.
- **D25** *(3 records)* — hour × day error matrix: (i) dimensions consistent, values ≥ 0,
  unmeasured cells empty; (ii) the hourly marginal agrees with the error curve within
  ±0.02 — matrix and curve come from the same photograph, and divergence marks stale or
  invented data; (iii) the title and claim text carry the matrix's true extent.
- **D26** — nameplate fields: coordinates in range, timezone and model name non-empty.
  If the fields are absent altogether, there is no claim and the check passes; a present
  but wrong field is an error. The meteo source is free-form — provider names are not
  gated by a dictionary.

Registry count: 26 codes (D1–D26), **37 passing records** in the canonical run — some
codes emit more than one record (D7 two legs; D22 three anchors; D23 two, D24 three,
D25 three legs). The render audit (R series) is outside this count and runs after page
generation.

## Copy rules

- **No literal numbers survive in template prose.** Either a number comes from the data or
  the sentence is not written. "The widest band falls on 21 August (±4.0 MWh)" is generated;
  a generic "widens to ±15%" is written only if the data supports it.
- **Internal terms are translated into client language:** "run" → "forecast", "holdout MAPE"
  → "error on unseen data". Abbreviations may remain as units (WMAPE, MAPE).
- **Bad results are not hidden.** The weakest day stays in the report card, the calibration
  step that costs accuracy stays in the waterfall, known limitations get their own section.
  That section speaks the same language as the product's debt list: when a debt closes, the
  item disappears from the report.
- **Narrative may never contradict the data.** A sentence saying "no calibration comparison
  is reported for this run" cannot appear in a report that contains a calibration waterfall.
  Narrative sentences are generated conditionally on the presence of the fields they use.

## Charting rules

- **Axes scale to the data.** A plant peaking at 2.8 MW does not get a scatter plot on a
  0–10 MW axis. The axis maximum follows the data maximum.
- **If an axis does not start at zero, the figure caption says so.**
- **Every figure carries its own legend**; the reader never scans up the page for it.
- **Every chart makes a claim, and the number behind that claim sits inside the chart.**
  Example: "within the ±10% corridor: day-ahead 59% · 24–72 h 40%".
- **Colour meaning is fixed:** brand colour = data and structure; sand = uncertainty and
  magnitude; amber and red = **status only**. Warning colours never encode magnitude.
- **Heat tables use a single-hue ramp** and numerals stay dark in every cell.
- **Labels never collide.** A label falling on a curve moves to the curve's empty side.
- **If a change is in percentage points, the label says "points"** ("−1.8 points"), not "%".

## Layout rules

- Every page is **exactly one A4 sheet**. Overflow is a silent corruption: content is clipped,
  usually the footer and the last table.
- The engine measures the page count of each page; if greater than one it **fails and names
  the overflowing page**. This check runs as a CI step.
- Text may not escape its container. If it does, shorten the text; do not enlarge the box.
- Figure captions may never be cut mid-sentence.

## Acceptance criteria

The report is ready to publish when:

- [ ] The full check inventory passes — counted by code: D1–D26 (37 records in the
  canonical run) plus a clean render R-series *(R1: the first edition's "22" contradicted
  the 21-item list; the count is now tied to the code registry)*
- [ ] Each of the 16 pages fits one A4 sheet
- [ ] No missing-data marker other than "—"; no field filled with zero
- [ ] No number in template prose that does not come from the data
- [ ] The same quantity shows the same value on every page
- [ ] Axes are scaled to the data
- [ ] No narrative sentence contradicts the data it accompanies
- [ ] The known-limitations section matches the product's current debt list

## Outputs

1. `report.html` — single file, fonts embedded, no external dependencies
2. `report.pdf` — produced from the same source, 16 pages
3. `checks.json` — result of every check that ran, pass/fail per check *(R1 note: one code
   may emit several records — 26 codes, 37 passing records in the canonical run)*
4. Exit code: non-zero if any check failed
