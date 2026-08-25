# PVQuant JSON Şeması v2.2 — Delta Belgesi

**Durum:** K-B kararının (v2.0-R1) yazılı hâli. v2.1 şemasının yerine geçmez; onun üzerine eklenen alanları, reddedilenleri ve sürümleme kuralını tanımlar. Taban şemanın özeti v2.0-R1 §5R'de; tam yapı `reporting/html/ornek_girdi_v21.json`.
**Ölçüm tabanı:** `faz2-ui` @ `2fbcfa1` (v2.188), 24 Ağustos 2026. Her iddia dosya:satır kanıtlı; ölçülmeyen ne varsa öyle işaretli.
**Süreç notu:** Bu bir belge teslimidir, depo mührü değildir. §6'daki uygulama planı dahil hiçbir şey kendiliğinden uygulanmaz; motor/worker dokunuşu çekirdek-dokunulmazlığı gereği ayrı onaya tabidir.

---

## 1. Sürümleme kararı (K-B1, bu oturum)

**v2.2 = v2.1 + üç alan grubu:** `error_dist.matrix` (gemide), `plant.lat/lon/tz` (taahhüt), `run.model` + `run.meteo_source` (taahhüt).

`schema_version` **"2.1" → "2.2"** geçişi, taahhütlü alanları getiren uygulama mühüründe yapılır — daha önce değil. `matrix` v2.185'te "2.1" etiketi altında, bump'sız çıktı; bu belge onu geriye dönük v2.2 kapsamına alır ve bu tutarsızlığı kayda düşer: 24 Ağustos itibarıyla sahadaki "2.1" etiketli JSON'lar matrix içerebilir. Bunun pratik zararı yok, çünkü:

**Uyumluluk kuralı:** v2.2 yalnız-ekleme (additive-only) bir deltadır. Yeni alanların hepsi opsiyonel-tolere: motor yokluğa dayanıklıdır ve yokluk "denetlenemedi" uyarısı değil iddia-yok/geçti'dir (emsal: D25'in matrissiz dalı — `denetim.py:1040`). v2.1 okuyan bir tüketici v2.2 belgeyi bilinmeyen alanları yok sayarak okuyabilir; sürüm alanı bilgilendiricidir, eşitlik kapısı değildir (motor bugün de şemayı sürümle kapılamıyor — `reporting/html/*.py` içinde `schema_version` okuyan kod yok, ölçüldü).

## 2. Alan: `error_dist.matrix` — GEMİDE (v2.185)

Fiilen çıkmış ilk delta alanı; sözleşmesi burada arşivlenir.

| Özellik | Değer | Kanıt |
|---|---|---|
| Biçim | `{days: [30 × "YYYY-AA-GG"], hours: [6..19], mae_mw: [14 satır × 30 kolon]}` | `ornek_girdi_v21.json`, ölçüldü |
| Anlam | saat×gün, gün-öncesi \|p50 − gerçek\| MW, 2 ondalık (K3 kararı) | `apps/worker/main.py:149` |
| Üretici | worker'ın saf `error_matrix_hesapla` fonksiyonu, B5 fotoğrafına `error_matrix` alanı; rapor yalnız okur | `apps/worker/main.py:149,279-281` |
| Yokluk | eşleşmesiz hücre `null` (uydurma 0 yok); tüm hücreler boşsa alan **hiç yazılmaz** | `main.py` "eşleşmesiz hücre None" |
| Tüketici | s08 Şekil 8.3, koşullu — matris yoksa şekil basılmaz | `reporting/html/veri.py:342` |
| Bekçi | D25 üç bacak: boyut/negatiflik · saat-marjinali↔MAE24 ±0,02 · `olculdu=false` günün kolonu boş | `denetim.py:1029-1048` |
| Canlı davranış | alan, mühür-sonrası ilk gece koşusunda dolar; o zamana dek raporlar dürüstçe 8.3'süz | v2.185 kayıt notu |

## 3. Alan: `plant.lat`, `plant.lon`, `plant.tz` — TAAHHÜT (K-B2)

| Özellik | Değer | Kanıt |
|---|---|---|
| Kaynak | `plants` tablosu: `lat DOUBLE PRECISION NOT NULL, lon DOUBLE PRECISION NOT NULL, tz TEXT NOT NULL` — ilk şemadan beri var, taşıma migration gerektirmez | `alembic/versions/d688ccc7983c_ilk_sema.py:44-45` |
| JSON konumu | `plant` bloğuna üç alan (mevcut: name, capacity_kwp, sebeke_ac_mwe, display[]) | üretici: `report_html_service.py` plant bloğu |
| Tip/birim | lat/lon: ondalık derece (WGS84 varsayımı — DB'de CRS alanı yok, ölçüldü); tz: IANA adı (ör. "Europe/Istanbul") | şema tanımı |
| Gerekçe | JSON dış sözleşmedir; konum/saat-dilimi künyesi denetçi-bankability senaryosunun asgarisi. PDF/Excel kendi ctx'inden zaten basıyor (`excel.py` Metadata "Konum" satırı) — JSON'da eksik kalması asimetriydi | v2.0-R1 §5R adayı |
| Tüketici | ilk mühürde YOK (alan künyeseldir). Rapora basma kararı (ör. s13 künye) ayrı iştir ve **pin değişimi** getirir — bilinçli olarak bu deltanın dışında | §6 |

## 4. Alan: `run.model`, `run.meteo_source` — TAAHHÜT (K-B2)

| Özellik | Değer | Kanıt |
|---|---|---|
| Kaynak | `forecast_runs` tablosu: `model`, `meteo_source` kolonları | `forecast_service.py:96-98,177` |
| JSON konumu | `run` bloğuna iki alan (mevcut: mode, pages, prepared) | üretici: `report_html_service.py` run bloğu |
| **Adlandırma ayrımı** | `run.model` = **güç/üretim modeli** (ör. "barhdadi_bennis"); `run.meteo_source` = hava verisi **sağlayıcısı** (ör. "open-meteo"); mevcut `sources.weather.model` = **hava modelinin** adı/sürümü. Üçü farklı şeydir; bu belge ayrımı sabitler | `ornek_girdi_v21.json` sources bloğu |
| Bilinen pürüz | insert `meteo_source`'u `'open-meteo'` SABİTİYLE yazıyor — kolon var ama parametre geçmiyor. Alan JSON'a taşınmadan önce bu sabitin gerçek kaynağa bağlanması gerekir (küçük servis işi, uygulama mührünün parçası) | `forecast_service.py:98` |
| Tüketici | ilk mühürde yok; künyesel. Not: `narrative`/s13 model adını bugün ctx'ten alıyor, JSON'dan değil — çift kaynak riski uygulamada gözetilecek | §6 |

## 5. Reddedilenler kaydı

- **`hourly[]` — RED (K-D):** saatlik tahmin serisi persist edilmiyor; JSON'a koymak ya uydurma ya da yeni persist yükü olurdu. `hourly_typical` (temsilî gün) yeterli sözleşme. Yeniden açılma şartı: saatlik persist kararı ayrıca verilirse.
- **`climate` GHI zarfına dönüşüm — RED (K-E):** `monthly_history` üretim (MWh) tarihçesi olarak KALIR; GHI beklentisi ayrı tabloda (`iklim_beklenti`) yaşar ve s11 GHI zarfı park kalemidir. v2.0'ın `monthly_envelope` önerisi geçersiz.

## 6. Uygulama planı (tek mühür taslağı — ONAYA TABİ)

1. `report_html_service.py:80` → `"schema_version": "2.2"`; plant bloğuna lat/lon/tz, run bloğuna model/meteo_source (hepsi `rapor_baglami`nın zaten okuduğu satırlardan; meteo_source sabiti §4'teki düzeltmeyle birlikte).
2. `ornek_girdi_v21.json` güncellenir: sürüm + beş alan. **Dosya adı KALIR** (tarihî ad; ci.yml/KONUSLANDIRMA referansları kırılmaz — yeniden adlandırma ayrı ve gereksiz churn).
3. **Pin beklentisi:** HTML `schema_version`'ı ve yeni alanları basmadığından kanonik çıktı bayt-birebir kalmalı → **md5 8a405d0d korunur**. Bu bir varsayım değil mühür kapısıdır: stash'li referansla sayfa-sayfa md5 kıyası koşulur; pin oynarsa mühür durur, kullanıcıya dönülür.
4. Bekçi önerisi (**D26, onaya tabi**): lat∈[−90,90], lon∈[−180,180], tz boş değil; run.model boş değil; alanlar yoksa iddia-yok/geçti (D25 emsali).
5. Excel/PDF etkilenmez. **Karar (bu oturum):** `contracts.SCHEMA_VERSION` gerçekte "1.1.0" ve AYRI bir şema soyudur (`ForecastReport` — lat/lon/tz ve run.model/meteo_source'u zaten taşır, tam hourly[] ile). "2.2" etiketi ona sahip olmadığı biçimi iddia ettirirdi; kendi çizgisinde DOKUNULMADAN kaldı.

## 7. Açık noktalar

- ~~D26 kapsamı ve `contracts.SCHEMA_VERSION`~~ — ikisi de karara bağlandı (D26 dahil edildi; 1.1.0 dokunulmadı). §6 planı v2.189'da uygulandı, pin kapısı GEÇTİ (md5 8a405d0d korundu, denetim 37/0).
- "Rapor Motoru Spesifikasyonu" (D maddelerinin asıl belgesi) hâlâ kullanıcıda; geldiğinde bu belgenin D25/D26 satırları oraya işlenir.
