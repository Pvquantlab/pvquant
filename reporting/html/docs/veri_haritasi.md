# Veri Haritası

**Dalga E.2 güncellemesi:** sabit veriler tek modülde: `veri.py`. Build betikleri veriyi
oradan alır (`from veri import …`). **JSON adaptörü çalışır durumda:** `PVQ_VERI_JSON`
ortam değişkeni bir JSON v2.0/v2.1 dosyası gösterirse `veri.py` içindeki `_json_yukle`
varsayılanları o dosyadan gelen değerlerle değiştirir; türetilen alanlar (LTA, gün
etiketleri, dönem metni, cephe aralığı, karne tarihleri) otomatik yeniden hesaplanır.
Kanonik örnek: `ornek_girdi_v21.json` — bu girdiyle üretim, varsayılanlarla **bayt-birebir**
aynı çıktıyı verir (md5 `8764…c001`). Kullanım:
`PVQ_VERI_JSON=ornek_girdi_v21.json python3 uret.py`

**Önce okuyun:** birden fazla sayfada görünen değerler tek bir kaynaktan türetilmelidir.
Örneğin günlük beklenti dizisi hem sayfa 4'ün çizelgesini hem sayfa 6'nın toplam satırını
besler; iki ayrı yerde tanımlanırsa er ya da geç birbirinden ayrışır.

---

## Ortak veri (`pvq.py`)

| Değişken | Ne | Beslediği sayfa | JSON kaynağı |
|---|---|---|---|
| `IKLIM` | 2007–2026 aylık üretim, MWh | 11, 12 | `climate.monthly_history[]` |
| `TAM_YILLAR` | Ortalamaya giren tam yıllar | 11, 12 | türetilir (eksiksiz yıllar) |
| `LTA_AY`, `LTA_YIL` | Uzun dönem ortalaması | 11, 12 | türetilir (`IKLIM`) |
| `HEAD` | Üstbilgi: santral adı ve dönem | tümü | `plant.name`, `forecast.horizon` |
| `foot(n)` | Altbilgi: mod rozeti | tümü | `run.mode` |

---

## Sayfa 1 — Kapak (`build_s01.py`)

| Değişken / metin | Ne | JSON kaynağı |
|---|---|---|
| `p50`, `hw` | 16 günün beklentisi ve bant yarı genişliği | `daily[].p50_kw`, `p10_kw`, `p90_kw` |
| `days` | Gün etiketleri | `daily[].date` |
| “Konya GES” | Santral adı | `plant.name` |
| “Anadolu Enerji A.Ş.” | Müşteri | `report.customer` |
| “1.036,4 MWh” | Dönem toplamı | `totals.p50_mwh` |
| “1.005–1.068 MWh” | Dönem bandı | `totals.p10_mwh`, `p90_mwh` |
| Künye alanları | Rapor kimliği, hazırlanma, ufuk, karne penceresi | `report.*`, `run.*` |
| “87 gündür kesintisiz” | Kesintisiz doğrulama | `accuracy.uninterrupted_days` |

---

## Sayfa 2 — İçindekiler (`build_s02.py`)

Veri içermez. `TOC` listesi sayfa planı değişirse elle güncellenir.

---

## Sayfa 3 — Yönetici özeti (`build_s03.py`)

| Değişken | Ne | JSON kaynağı |
|---|---|---|
| `KPI` listesi | 8 gösterge (değer, birim, not, durum) | aşağıdaki satırlar |
| — toplam beklenti | `totals.p50_mwh` |
| — olasılık bandı | `totals.p10_mwh` / `p90_mwh` |
| — kapasite faktörü | `totals.capacity_factor` |
| — gün-öncesi hata | `accuracy.wmape_0_24` |
| — basit referansa üstünlük | `accuracy.skill` |
| — bağımsız testte hata | `calibration.holdout_mape` |
| — kesintisiz doğrulama | `accuracy.uninterrupted_days` |
| — santral verisi kapsaması | `scada.coverage_pct` |
| Durum rengi (`ok` / `watch`) | Eşik karşılaştırması | eşikler `pvq.py` yerine adaptörde tanımlanmalı |
| Değerlendirme paragrafları | Anlatı | elle yazılır ya da şablonlanır |

---

## Sayfa 4 — Günlük üretim (`build_s04.py`)

| Değişken | Ne | JSON kaynağı |
|---|---|---|
| `p50`, `hw`, `days` | Günlük beklenti, bant, tarihler | `daily[]` |
| “1.036,4 / 1.005 / 1.068” | Dönem toplamı satırı | `totals.*` |
| Cephe vurgusu `highlight=(6, 8)` | Dikkat çekilen gün aralığı | `daily[].flag` ya da elle |

---

## Sayfa 5 — Saatlik profiller (`build_s05.py`)

| Değişken | Ne | JSON kaynağı |
|---|---|---|
| `BASE` | Tipik gün saatlik profili, MW | `hourly[].p50_kw` (tipik gün) |
| `DAILY` | İlk 8 günün toplamı | `daily[].p50_kw` |
| “tepe 8,9 MW” | Tepe değer açıklaması | türetilir (`BASE` en yüksek) |

---

## Sayfa 6 — Saat × gün matrisi (`build_s06.py`)

| Değişken | Ne | JSON kaynağı |
|---|---|---|
| `BASE_KW` | Saatlik güç taban eğrisi | `hourly[].p50_kw` |
| `DAILY` | Günlük ölçek | `daily[].p50_kw` |
| `PEAK` | Renk ölçeğinin üst sınırı | türetilir (en yüksek hücre) |

> Bu sayfa şu anda saatlik değerleri taban eğri × günlük ölçek olarak türetiyor.
> Gerçek veride doğrudan `hourly[]` pivotu kullanılmalıdır.

---

## Sayfa 7 — Doğruluk karnesi (`build_s07.py`)

| Değişken | Ne | JSON kaynağı |
|---|---|---|
| `wm` | Son 30 günün gün-öncesi hatası | `accuracy.report_card[].wmape_0_24` |
| `h72` | 24–72 saatlik hata | `accuracy.report_card[].wmape_24_72` |
| `sk` | Kazanç puanı | `accuracy.report_card[].skill` |
| `naif` | Naif referans hatası | türetilir: `wm / (1 − sk)` |
| `TARIH` | Gün etiketleri | `accuracy.report_card[].date` |
| `ORT_SKILL` | Ortalama kazanç | türetilir |

---

## Sayfa 8 — Hata dağılımı (`build_s08.py`)

| Değişken | Ne | JSON kaynağı |
|---|---|---|
| `pairs24`, `pairs72` | Saatlik tahmin–gerçekleşen çiftleri | `hourly[]` × SCADA gerçekleşen |
| `mae24`, `mae72` | Saat bazında ortalama mutlak hata | türetilir |
| `MU`, `SD`, `NDAYS` | Günlük sapma dağılımının parametreleri | `daily[]` × gerçekleşen |
| `BINS`, `P10/P50/P90` | Histogram ve yüzdelikler | **türetilir — elle yazılmaz** |
| `ORAN24`, `ORAN72` | ±%10 koridorunda kalan saat oranı | türetilir |

---

## Sayfa 9 — Kalibrasyon (`build_s09.py`)

| Değişken | Ne | JSON kaynağı |
|---|---|---|
| `BAS`, `BIT` | Ham fizik ve hibrit MAPE | `calibration.physics_mape`, `holdout_mape` |
| `ADIM` | Şelale adımları ve puan değişimleri | `calibration.steps[]` |
| `KATSAYI` | η_BoS, bifacial kazanç, saat sayısı, tarih | `calibration.*` |

---

## Sayfa 10 — Bağımsız test ve veri kalitesi (`build_s10.py`)

| Değişken | Ne | JSON kaynağı |
|---|---|---|
| Holdout şeridi (%80/%20, tarihler) | Bölme | `calibration.holdout_split` |
| `GECERLI`, `HATALI`, `DIGER` | Aylık geçerli saat payı ve bayrak kırılımı | `scada.quality_flags` (aylık) |
| `AYLAR` | Ay etiketleri | türetilir |
| `BAYRAK` | Bayrak adı, saat, pay, aksiyon | `scada.quality_flags[]` |
| “%6,8 / %8,9” | Eğitim ve test hatası | `calibration.train_mape`, `holdout_mape` |

---

## Sayfa 11 — İklim zarfı (`build_s11.py`)

| Değişken | Ne | JSON kaynağı |
|---|---|---|
| `P10`, `P90` | Aylık zarf sınırları | türetilir (`IKLIM`) |
| `SON12` | Son 12 ayın gerçekleşeni | `climate.last12[]` |
| `ORT`, `SD`, `CV` | Yıllık ortalama, standart sapma, değişkenlik | türetilir |
| `p_yil(50/75/90)` | Aşılma olasılığı değerleri | türetilir |
| Nisan işareti | Düşük kapsamalı ay | `scada.coverage_pct` (aylık) |

---

## Sayfa 12 — Yıl × ay matrisi (`build_s12.py`)

Tümü `pvq.IKLIM`'den türetilir. Ayrı veri girişi yoktur.

---

## Sayfa 13 — Model zinciri ve künye (`build_s13.py`)

| Değişken | Ne | JSON kaynağı |
|---|---|---|
| `HALKA` | Zincir halkaları ve açıklamaları | sabit metin; aktif halka `run.mode` |
| `SAHA` | Koordinat, yükseklik, güç, eğim, izleyici, panel/inverter | `plant.*` |
| `KUNYE` | Veri kaynakları, çözünürlük, dönem, zaman damgası | `sources.*` |

---

## Sayfa 14 — Standartlar ve sınırlar (`build_s14.py`)

| Değişken | Ne | JSON kaynağı |
|---|---|---|
| `STANDART` | Çerçeveler | sabit metin |
| `SINIR` | Bilinen sınırlar | **kod borç listesiyle eşleşmelidir** |
| `EVRIM` | Aynı hedef gün için ardışık tahminler | run arşivi (append-only) |

> `SINIR` listesi geliştirme borç listesiyle aynı dili konuşmalıdır. Bir borç kapandığında
> rapordaki madde de kalkmalıdır; aksi hâlde rapor gerçeği yanlış anlatır.

---

## Sayfa 15–16 — Ekler (`build_s15.py`, `build_s16.py`)

Veri içermez. `METRIK`, `BUTCE`, `KISALTMA`, `SOZLUK`, `REFERANS` listeleri sabittir ve
yalnızca rapor yapısı değişince güncellenir. `METRIK` tablosundaki "Nerede" sütunu sayfa
numaralarına atıf yapar; sayfa planı değişirse birlikte güncellenmelidir.

---

## Yer tutucular

Aşağıdaki değerler gerçek değil, yer tutucudur ve entegrasyonda değiştirilmelidir:

| Yer tutucu | Nerede |
|---|---|
| `PVQ-2026-08-04-C-0417` | Sayfa 1, 16 |
| `rapor@pvquant.example` | Sayfa 1, 16 |
| `Anadolu Enerji A.Ş.` | Sayfa 1 |
| `MonoPERC-540B · INV-3125K` | Sayfa 1, 13 |
