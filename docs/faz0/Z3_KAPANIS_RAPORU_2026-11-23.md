# PVQuant Faz 0 — Z-1 / Z-2 / Z-3 Kapanış Değerlendirme Raporu
Doğrulama anı: **23.11.2026 15:04 TSİ** (sunucu ve DB saati 12:04 UTC, TimeZone UTC) · Salt okunur; kod/DB/servis/dal/mühür durumu değişmedi · Dil: Türkçe

## 1. Mevcut durum
- Canlı sürüm **v2.643** (`/opt/pvquant` HEAD `ef1581a`); api 22 s, worker 22 s, db 6 g, caddy 6 g ayakta; `healthz` 200 (0,13 s), `readyz` 200; vitrin HTTP/2 200.
- Faz 0: **KOŞULLU MÜHÜR** (22.11) — bu raporda değiştirilmedi.
- Kanıt kaynakları: canlı `jobs_log`, `piyasa_fiyat`, `scada_hourly`, `plants`, `forecast_runs/values` (SELECT, `default_transaction_read_only=on`; 14:47 ve 15:04 TSİ), `docker compose logs worker/api --since 23.11 00:00Z` (salt okunur), `apps/worker/main.py` zamanlayıcı planı (kod), UAT_2026-11-21.md §13–14.9, Z1_Z2_KONTROL_2026-11-23.md §1–8, kanit/g1_sentry/.
- Tarihsel taban (03:05 TSİ): Z-1 1/4, Z-2 0/4 BEKLİYOR; `piyasa_fiyat` 16.392 satır / son 14.11 20:00Z; epias üretim Karapınar 1.099 / Kıvanç 1.243 / son 13.11 15:00Z. 06:43 oturum kontrolü kayıt üretmedi (oturum kapalıydı); gece kanıtı 14:47'de okundu — zamanlama/veri kaybı yok.

## 2. Z-1 kabulü (K9-A, v2.643 worker)
| Kriter | Beklenen | Gözlenen | Kanıt | Sonuç |
|---|---|---|---|---|
| Gece cron'ları planlı saatte | 03:08 kural_sicili, 03:12 abonelik, 03:15 piyasa, 03:18 epias_uretim ×4, 03:20 hijyen, 03:30 skill, 03:33 ufuk_sigma, 03:35 konformal, 03:40 beklenti, 03:45 rapor_alanlari, 03:50 bağımsız doğrulama, 03:55 finansal etki, 04:00 meteo, 04:05 portföy, 04:15 yedek, 05:00 sabah_tahmin ×4 | hepsi saniye sapması 0 ile başladı ve `ok` bitti (süreler 0,0–8,4 s; meteo 8.729 s) | jobs_log 23.11 00:08–02:00Z | **PASS** |
| Gündüz cron'ları | 12:30 gün içi ×4, 14:35 PTF, 14:40 ptf_kontrol, 14:45 avans, saatlik iletişim/KGÜP kontrolleri | 12:30 (Format Lab 352 s, diğerleri 2–3 s), 14:35:00,005 → 14:35:00,55 ok; 14:40/14:45 ok | jobs_log | **PASS** |
| Hata / başarısız / yeniden deneme | 0 | 23.11 00:00 TSİ'den itibaren **163/163 ok**; worker günlüğü error/401/429/timeout/Traceback **0**; api 5xx **0** | jobs_log, compose logs | **PASS** |
| Worker nabzı ve sağlık | iş akışı sürüyor, servis ayakta | son iş 14:50 TSİ; worker 22 s ayakta; healthz/readyz 200 | compose ps, jobs_log, curl | **PASS** |
| Yedek 04:15 | ok | `gece_yedek` 04:15:00 ok, 20,8 s | jobs_log | **PASS** |
| Yeniden başlatma yakalaması | restart sonrası yakalama + yedek | `acilis_yakalama`/`acilis_yedek` 22.11 16:17:02 ve 17:16:03 ok (v2.643) | jobs_log | **PASS** |
| Beklenmeyen yazım / çift kayıt | yok | `piyasa_fiyat` çift ts **0** (tüm tablo); yeni epias üretim satırları gün×saat 24/24, tekil ts = satır; bugünkü tahmin koşuları beklenen 4+4 | SELECT | **PASS** |
| Atlanan işler | yalnız gerekçeli | `gece_epias_uretim` Format Lab/Golden 33 «şeffaflık numarası girilmedi» (test santrali, eşleme yok — doğru); bağımsız doğrulama/finansal etki test santrallerinde «ölçüm yok»; rapor_gonderimi «günü gelmedi». Hepsi `status=ok` → **Ü-1** (görünüm sorunu; iş gerçekten atlandı, veri işlemesi gereken bir iş atlanmadı) | jobs_log detail | **PASS (Ü-1 açık)** |
**Z-1: 8/8 PASS.** «ok ama iş yapılmadı» durumu yalnız beklenen atlamalarda; zorunlu veri işi (piyasa, üretim, PTF, yedek, tahmin) gerçekten yapıldı (§3–4).

## 3. Z-2 kabulü (K9-B, gerçek EPİAŞ akışı)
| Veri kaynağı | Santral / tarih | Son kayıt | Yeni satır | İş sonucu | Kabul |
|---|---|---|---|---|---|
| EPİAŞ üretim (`gece_epias_uretim` 03:18:00) | **Karapınar RT-2579**, 15–22.11 TSİ | 22.11 20:00Z (önce 13.11 15:00Z) | **192** (çekilen 192 = yazılan 192; 8 gün × 24, eksik 0, çift 0); toplam 1.099 → 1.291 | `ok`, 1,0 s; alınma 00:18:01Z | **PASS** |
| EPİAŞ üretim (`gece_epias_uretim` 03:18:01) | **Kıvanç 2 GES**, 15–22.11 TSİ | 22.11 20:00Z (önce 13.11 15:00Z) | **192** (192/192; eksik 0, çift 0); toplam 1.243 → 1.435 | `ok`, 0,9 s; alınma 00:18:02Z | **PASS** |
| Üretim kimlik/doğruluk | plant_id ↔ ad; değer ≤ AC | plant_id eşlemesi doğru (yalnız eşlemeli iki santral yazıldı); maks 158.970 kW ≤ 200.000 AC, 34.390 ≤ 35.000; AC üstü ölçüm 0 | SELECT | **PASS** |
| Piyasa fiyatı (`gece_piyasa` 03:15:00) | 20, 21, 22.11 TSİ | 22.11 20:00Z | **72** (24+24+24, kaynak `epias`, ptf NULL 0, tekil ts 24/24; PTF aralığı 310–4.499) ; güncelleme 00:15:01Z | `ok`, 0,9 s | **PASS** |
| Gün-öncesi PTF (`gun_oncesi_ptf` 14:35) | 23.11 + **24.11** TSİ | 24.11 20:00Z | **48** (23.11 24 + 24.11 24, kaynak `epias_gop`, ptf NULL 0; 24.11 aralık 1.700–4.500) | «ok; yazılan 48; yarın 24 saat» | **PASS** |
| Kimlik doğrulama / hata | CAS başarılı; 401/429/zaman aşımı 0 | worker günlüğünde eşleşme 0; jobs_log'da «kimlik_yok» yok (22.11'de vardı, kimlik öncesi) | compose logs, jobs_log | **PASS** |
| B4 boşluğu (14.11 tabanı) | gerçek akışın dönmesi | **Döndü**: üretim 15–22.11 tamamen geldi; piyasa 20–24.11 geldi. **Kalan**: piyasa 15–18.11 (19.11 var) ve üretim 14.11 TSİ günü yok → backfill ayrı onay | SELECT | **PASS (akış döndü; boşluk Ü dışı açık iş)** |
**Z-2: 4/4 zorunlu alt kontrol PASS** (piyasa artışı, üretim artışı + plant_id, hata 0, 14:35 «yazılan 24» → 24.11 için 24 saat). Kimlik doğrulama, çekim ve DB yazımı üçü de ayrı ayrı kanıtlı (çekilen = yazılan).

## 4. 14:35 PTF sonucu
- Başlangıç **14:35:00,005 TSİ** (11:35:00,005Z), bitiş 14:35:00,55; status `ok`; detail «ok; yazılan 48; yarın 24 saat».
- Kimlik doğrulama: başarılı (yazım gerçekleşti; günlükte 401/429 yok). Hedef piyasa günü: **24.11.2026 TSİ** (ts 23.11 21:00Z → 24.11 20:00Z, 24 saat) + bugünün 23.11 GÖP değerleri (24 saat) yenilendi.
- Çekilen/yazılan: 24 + 24 = 48 satır, `kaynak=epias_gop`, güncelleme 11:35:01Z; ptf NULL 0; çift ts 0; değer aralığı 24.11 1.700–4.500 (TL/MWh; tabloda para birimi sütunu yok — EPİAŞ PTF TL/MWh, uygulama sözleşmesi).
- Hata/eksik: yok. `ptf_kontrol` 14:40 ×4 ok.

## 5. K9 değerlendirmesi
- **K9-A Altyapı/zamanlayıcı: PASS** — §2 (23.11 gerçek koşu kanıtı, v2.643).
- **K9-B EPİAŞ veri bağlantısı: PASS** — §3–4 (kimlik doğrulama ✓, çekim ✓, DB yazımı ✓, bütünlük ✓, plant_id ✓).
- **K9-C Gerçek müşteri santrali doğruluğu: UYGULANAMAZ** — bağlı gerçek müşteri santrali yok. Kamu referans karnesi (23.11 03:50 bağımsız doğrulama: Karapınar gun_oncesi n=266 WMAPE %26,0; Kıvanç n=287 %24,2) **teknik** doğrulamadır, ticari müşteri doğruluğu iddiası değildir. Bu bir **kabul istisnasıdır**; mühürde açıkça yazılır ve onayla kabul edilir.
- Hata sınıflandırması: kimlik eksikliğinden kaynaklı atlama **yok** (22.11'deki «kimlik_yok» B3 ile kapandı); dış veri eksikliği **yok** (çekilen = yazılan); uygulama kusuru olarak yalnız **Ü-1** (görünüm) ve Faz 1 bulguları (mühür dışı).

## 6. Açık riskler
| ID | Önem | Kanıt | Etki | Mührü engeller? | Gereken eylem |
|---|---|---|---|---|---|
| R-1 Ü-1 atlanan iş «ok» | Orta (görünüm) | bugün 10 kayıt `status=ok` + «atlandı» | hizmet sağlığı yanıltıcı yeşil | **Hayır** (iş gerçekten gerekçeli atlandı) | G1 4bec272 dağıtımı (v2.644) — AÇIK |
| R-2 Ü-2 santral türü etiketi boş | Orta (görünüm) | `plants.params_json.santral_turu` 5/5 boş | sınıf rozeti yok; test/kamu ayrımı yüzeyde yok | Hayır | G1 dağıtımı + operatör ayarı — AÇIK |
| R-3 Kamu referans verisi SCADA gibi sunulma | Orta | `kaynak='epias'`, `sinir=settlement_gross`; G1 «kamuya açık resmî üretim ölçümü» metni dağıtılmadı | yanıltıcı etiket | Hayır | G1 dağıtımı — AÇIK |
| R-4 Golden 33 / Format Lab test santrali sınıfı | Bilgi | epias eşlemesi yok, atlanıyor; türü boş | karışıklık riski | Hayır | Ü-2 ile — AÇIK |
| R-5 G1 dağıtılmadı | Orta | 4bec272 yerel | R-1…R-3 sürer | Hayır | mühür sonrası v2.644 — AÇIK |
| R-6 G2-A1 dağıtılmadı — AC üstü P50 **canlıda yeniden** | Orta–Yüksek (ürün) | 23.11 koşuları: sapma aktif (Kıvanç oran 1,23); Kıvanç P50 1,022×AC (05:00, 4 saat), 1,115×AC (12:35, 3 saat); Karapınar 0,84 | Tahminler sayfası fiziken imkânsız P50; KGÜP EAK=AC ile kırpık | Hayır (Faz 1 kapsamı; Faz 0 kriteri değil) | d7d34d2 dağıtımı — AÇIK |
| R-7 Sentry DSN boş | Orta (gözlem) | `.env` DSN boş → Sentry etkin değil; geçmiş olay planı yazılı | hata görünürlüğü yok | Hayır (ayrı karar) | DSN kararı + inceleme planı — AÇIK |
| R-8 Tarihsel veri boşluğu (B4) | Düşük–Orta | piyasa 15–18.11 yok; üretim 14.11 yok | geçmiş karne/finans o günlerde eksik | Hayır | backfill ayrı onay — AÇIK |
| R-9 Yedek at-rest şifreleme yok | Orta (güvenlik) | A3 kaydı | sunucu ele geçirilirse yedek açık | Hayır (kabul edilen istisna, kayıtlı) | ayrı paket — KABUL EDİLEN İSTİSNA |
| R-10 Gerçek müşteri doğrulaması yok | — | müşteri santrali yok | ticari iddia yapılamaz | Hayır (K9-C UYGULANAMAZ) | pilot santral bağlanınca — UYGULANAMAZ |
| R-11 D-19 tatbikat template0, kilitsiz sürümler, Meridyen sona_erdi | Düşük | önceki kayıtlar | operasyon/ticari | Hayır | SONRAYA — AÇIK |
| R-12 06:43 oturum kontrolü kayıt üretmedi | Bilgi | cron ateşlendi mi bilinmiyor; oturum kapalıydı | yok (kanıt 14:47'de okundu) | Hayır | — ÇÖZÜLDÜ |
Hiçbir madde veri bütünlüğü ya da güvenlik **arızası** değildir; R-6 ürün kusuru olup Faz 1'de düzeltilmiş, dağıtım bekliyor.

## 7. Z-3 kararı
**KOŞULLU GO.** Zorunlu Faz 0 kapanış koşulları (Z-1 8/8, Z-2 4/4, K9-A PASS, K9-B PASS) **gerçek jobs_log ve DB kanıtıyla** doğrulandı; FAIL ve BEKLİYOR yok. «Koşullu» olmasının tek nedeni: **K9-C UYGULANAMAZ** bir kabul istisnasıdır ve nihai mühürde açıkça onaylanmalıdır; ayrıca R-1…R-11 engellemeyen açık işler olarak kayda girer. Teknik doğrulama ile istisna onayı ayrı tutulmuştur; bu tur mühür durumunu değiştirmez.

## 8. Nihai mühür hazırlığı
- **Tamamlanan:** K1–K8 (22.11), K9-A, K9-B; v2.643 canlı ve değişmemiş; yedek 04:15 ok; EPİAŞ akışı canlı; kapanış belgeleri (UAT §13–14.9, Z1_Z2_KONTROL, bu rapor, Z-3 defter metni taslağı UAT §14.9).
- **Kalan (onaya bağlı):** K9-C istisnasının kabulü; Z-3 defter kaydının yazılması ve raporların commit/push'u (yalnız belge; main checkout'ta `main` dalına geçiş; CI). Bunlar canlı uygulama kodunu ve verisini değiştirmez.
- **Kalan riskler:** §6 (hepsi engellemeyen; R-6 en yüksek ürün önceliği).

## 9. Nihai öneri
**A.** Evet — Faz 0 teknik olarak nihai mühre hazır: zorunlu kriterlerin hepsi gerçek koşu ve DB kanıtıyla PASS.
**B.** Evet — Z-1 ve Z-2 gerçekten doğrulandı (zaman damgaları, satır sayıları, çekilen = yazılan, bütünlük ve plant_id kontrolleri; «ok ama iş yapılmadı» durumu yalnız gerekçeli atlamalarda).
**C.** Evet — 14:35 PTF işi 14:35:00 TSİ'de koştu, 24.11 piyasa günü için 24 saatlik PTF çekti ve yazdı (ayrıca 23.11 için 24 saat yeniledi; toplam 48 satır, çift 0, NULL 0, kaynak epias_gop).
**D.** Kapanışı engelleyen madde **yok**. Onay gereken tek şey K9-C UYGULANAMAZ istisnasının mühürde kabulü; R-1…R-11 mühür sonrası açık işlerdir.
**E.** Evet — nihai mühür yalnız belge işlemidir (defter kaydı + rapor commit/push); canlı uygulama kodu, DB, servis ve EPİAŞ yapılandırması değişmez.
