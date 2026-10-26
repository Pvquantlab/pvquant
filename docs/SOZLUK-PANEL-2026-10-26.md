# İki panel ortak sözlüğü ve eşzamanlama (26.10.2026) — v2.496 CANLI (cdfdb9a, CI #600)
Kapsam: platform paneli (/yonetim) ↔ müşteri/santral paneli. Kaynak dil müşteri panelinin «piyasa dili» (v2.462); platform buna uyar.
API alan adları ve uçlar SÖZLEŞMEDİR, değişmedi (`bayat`, `taze`, `tamam`, `kosu`, `/v1/yonetim/kiracilar`, jobs_log eylem kodları).

## 1. Sözlük (kullanıcıya görünen karşılıklar) — `web/src/lib/sozluk.ts`
| Kavram (teknik) | Eski platform | Eski müşteri | ORTAK |
|---|---|---|---|
| tenant | kiracı (v2.495'te müşteri) | — | **müşteri**, hesap («Müşteri hesapları», «Hesabı aç») |
| jobs_log.status = ok / değil | tamam / başarısız | tamam / başarısız | **tamam / başarısız** (`isDurumu`) |
| tazelik hükmü (uçtan `bayat`/`taze`) | taze / bayat | «N gün eski», «eskimeye başlar» | **güncel / eski** (`tazelik`) |
| son SCADA ölçümü (scada_hourly max ts) | Son SCADA | son veri | **son veri** (SCADA birim notu) |
| son tahmin koşusu (forecast_runs max run_at) | Son koşu | son tahmin | **son tahmin**; sayım «Tahmin koşusu» (Kullanım) |
| damga yoklama zamanı | — | son kontrol | **son kontrol** |
| gece_meteo kaynağı | Hava verisi | Hava / «profesyonel meteoroloji verisi» | **Hava verisi** (iş adı «Hava verisi indirme») |
| gece_piyasa (PTF/SMF) | Piyasa fiyatı | — | **Piyasa fiyatları (PTF/SMF)** |
| gece işleri grubu | Gece turu | Otomatik gece işlemleri | **Gece işlemleri** |
| envanter sorun kodları | SCADA yok / SCADA eski / koşu yok / koşu eski | — | **veri yok / veri eski / tahmin yok / tahmin eski / müşteri askıda** |
| hesap durumu | etkin / askıda | — | **etkin / askıda** (`hesapDurumu`) |
| iş adları (tek kaynak) | sunucu `isler_service.ISIM_TR` | aynı | aynı; **`denetim_temizlik` etiketsizdi → «Denetim izi temizliği»** |
| göreli yaş / kısa zaman | `api/yonetim.ts` yasTr/zamanTr | yok | **`lib/bicim.ts` yasTr/zamanTr** (yonetim.ts yeniden dışa aktarır); iki panel yerel saat |
Bilerek BİRLEŞTİRİLMEYENLER (farklı teknik anlam): «koşu» (tahmin koşusu, forecast_runs) ≠ «iş» (jobs_log kaydı); «son veri» (ölçüm) ≠ «son tahmin»;
«nabız» (worker sistem_nabiz, yalnız platform); «kalibrasyon bekliyor» (model durumu) ≠ «eski» (tazelik).

## 2. Eşzamanlama bulguları ve düzeltmeler
- **Zaman kaynağı:** iki panel de jobs_log.started / forecast_runs.run_at / scada_hourly.ts_utc'yi okur; tazelik eşiği tek (`sistem_service.BAYAT_SAAT
  = isler_service.bayat_isler(saat=30)`); platform «eski işler» listesi = müşteri gece işleri «eski» listesi (DB testi).
- **Damga (değişim damgası) kapsamı genişledi** — `damga_service._ortak_damga`: son_piyasa (piyasa_fiyat.guncelleme), son_is (jobs_log, kiracı+küresel),
  son_meteo (meteo_arsiv, santral noktası ±0,05°), santral_ozu (plants satırı md5). Eskiden yalnız SCADA/koşu/alarm/skill/kalibrasyon: fiyat
  güncellemesi, iş sonucu ve santral ayarı değişince müşteri paneli tazelenmiyordu.
- **İstemci önbelleği damgaya bağlandı** — `client.bellekEskit()`: damga değişince kayıtlar silinmez, yaşı sıfırlanır (bayat-önce okuyucu çalışır, getir
  ağa çıkar). Eski kusur: damga değişimi 60 sn içinde gelirse yeniden çekim bellekten dönüyor, panel yeni koşuyu bir sonraki değişime dek göremiyordu.
- **Sayfalar damgaya abone** — `shell/damgaOlay.ts` (`damgaYay`/`useDamgaSurumu`): Santralim (11 efekt), Tahminler, Doğruluk, Aylık, Kalibrasyon,
  Raporlar, gece işleri kartı. Eskiden yalnız Kabuk şeridi tazeleniyordu; açık sayfa eski tahminle kalıyordu.
- Sunucu tarafı: oturum önbelleği 60 sn (belgeli), rapor/portföy uçları her istekte DB'den; worker yazar, API okur — süreç içi paylaşım yok (damga da DB'den).

## 3. Test paketi (üç tur üst üste; `tur.sh`)
tests/test_senkron.py (sözlük kapsamı + eşik parite, iş kayıtları iki panelde aynı + izolasyon, damga 4 kaynak + sabitlik + izolasyon), hedef API/DB/RLS
takımları, worker içe aktarma, tam Python takımı, web build/test(senkron.test.ts)/oxlint, gerçek tarayıcı önbellek testi (sahte API damga kontrolü),
50 ölçümlük sayfa turu. Sonuçlar aşağıda birebir.

## 4. Tur sonuçları (birebir terminal çıktısı)
```
=== TUR 1  13:36:29 UTC ===
--- [DB+API] eşzamanlama + hedef takımlar
================= 54 passed, 1 skipped, 83 warnings in 21.27s ==================
--- [WORKER] içe aktarma + iş etiketleri
worker içe aktarıldı; zamanlanan iş 20 | etiketsiz []
--- [PYTHON TAM TAKIM]
=========== 728 passed, 1 skipped, 154 warnings in 342.69s (0:05:42) ===========
--- [WEB] build
✓ built in 1.13s
--- [WEB] test
ℹ tests 98 ℹ pass 98 ℹ fail 0 
--- [WEB] oxlint uyarı/hata: 16/0
--- [TARAYICI] sahte paket derleme + sunucular
✓ built in 1.05s
--- [CACHE] gerçek tarayıcı: damga değişince yeniden çekim
{"once":"69.761","sonra":"69.762","degisti":true,"sure_sn":60,"summary_istek":[1,2],"damga_istek":[1,3],"hatalar":[]}
--- [TARAYICI] 50 ölçüm (platform + müşteri koyu/açık, 1440/375)
ölçüm 50 | belge taşması [] | iç taşma 1440 [] | iskelet [] | boş [] | hatalar [] | geçiş ms medyan 77 p90 175 max 309
=== TUR 1 bitti 13:45:14 UTC ===
```
```
=== TUR 2  13:45:35 UTC ===
--- [DB+API] eşzamanlama + hedef takımlar
================= 54 passed, 1 skipped, 83 warnings in 18.68s ==================
--- [WORKER] içe aktarma + iş etiketleri
worker içe aktarıldı; zamanlanan iş 20 | etiketsiz []
--- [PYTHON TAM TAKIM]
=========== 728 passed, 1 skipped, 154 warnings in 292.08s (0:04:52) ===========
--- [WEB] build
✓ built in 1.11s
--- [WEB] test
ℹ tests 98 ℹ pass 98 ℹ fail 0 
--- [WEB] oxlint uyarı/hata: 16/0
--- [TARAYICI] sahte paket derleme + sunucular
✓ built in 1.05s
--- [CACHE] gerçek tarayıcı: damga değişince yeniden çekim
{"once":"69.761","sonra":"69.762","degisti":true,"sure_sn":60,"summary_istek":[1,2],"damga_istek":[1,3],"hatalar":[]}
--- [TARAYICI] 50 ölçüm (platform + müşteri koyu/açık, 1440/375)
ölçüm 50 | belge taşması [] | iç taşma 1440 [] | iskelet [] | boş [] | hatalar [] | geçiş ms medyan 79 p90 168 max 311
=== TUR 2 bitti 13:53:23 UTC ===
```
```
=== TUR 3  13:53:45 UTC ===
--- [DB+API] eşzamanlama + hedef takımlar
================= 54 passed, 1 skipped, 83 warnings in 19.19s ==================
--- [WORKER] içe aktarma + iş etiketleri
worker içe aktarıldı; zamanlanan iş 20 | etiketsiz []
--- [PYTHON TAM TAKIM]
=========== 728 passed, 1 skipped, 154 warnings in 270.14s (0:04:30) ===========
--- [WEB] build
✓ built in 1.09s
--- [WEB] test
ℹ tests 98 ℹ pass 98 ℹ fail 0 
--- [WEB] oxlint uyarı/hata: 16/0
--- [TARAYICI] sahte paket derleme + sunucular
✓ built in 1.01s
--- [CACHE] gerçek tarayıcı: damga değişince yeniden çekim
{"once":"69.761","sonra":"69.762","degisti":true,"sure_sn":60,"summary_istek":[1,2],"damga_istek":[1,3],"hatalar":[]}
--- [TARAYICI] 50 ölçüm (platform + müşteri koyu/açık, 1440/375)
ölçüm 50 | belge taşması [] | iç taşma 1440 [] | iskelet [] | boş [] | hatalar [] | geçiş ms medyan 80 p90 185 max 308
=== TUR 3 bitti 14:01:11 UTC ===
```

**Tur 1–3 sonrası bulgu (tarayıcı karesinden):** Sistem «Yedek» notu «eskisi bayat / son deneme düştü», Genel bakış sağlık şeridi «gece turu: taze/bayat»,
müşteri detayı santral tablosu «Son SCADA / Son koşu» eski sözcükleri taşıyordu; bekçi yalnız köşeli bağlamı tarıyordu. Düzeltildi (sözlük üzerinden);
bekçi artık platform dosyalarının tüm dizge/şablon değerlerini kelime sınırıyla tarar (`${…}` kod ifadeleri hariç). Son kod üzerinde üç ardışık tur
(4–6) yeniden koşuldu — sonuçlar aşağıda.

### Son kod üzerinde üç ardışık tur (4–6) — birebir
```
=== TUR 4  14:02:42 UTC ===
--- [DB+API] eşzamanlama + hedef takımlar
================= 54 passed, 1 skipped, 83 warnings in 19.22s ==================
--- [WORKER] içe aktarma + iş etiketleri
worker içe aktarıldı; zamanlanan iş 20 | etiketsiz []
--- [PYTHON TAM TAKIM]
=========== 728 passed, 1 skipped, 154 warnings in 301.76s (0:05:01) ===========
--- [WEB] build
✓ built in 1.07s
--- [WEB] test
ℹ tests 98 ℹ pass 98 ℹ fail 0 
--- [WEB] oxlint uyarı/hata: 16/0
--- [TARAYICI] sahte paket derleme + sunucular
✓ built in 1.08s
--- [CACHE] gerçek tarayıcı: damga değişince yeniden çekim
{"once":"69.761","sonra":"69.762","degisti":true,"sure_sn":60,"summary_istek":[1,2],"damga_istek":[1,3],"hatalar":[]}
--- [TARAYICI] 50 ölçüm (platform + müşteri koyu/açık, 1440/375)
ölçüm 50 | belge taşması [] | iç taşma 1440 [] | iskelet [] | boş [] | hatalar [] | geçiş ms medyan 80 p90 173 max 307
=== TUR 4 bitti 14:10:41 UTC ===
```
```
=== TUR 5  14:10:41 UTC ===
--- [DB+API] eşzamanlama + hedef takımlar
================= 54 passed, 1 skipped, 83 warnings in 17.44s ==================
--- [WORKER] içe aktarma + iş etiketleri
worker içe aktarıldı; zamanlanan iş 20 | etiketsiz []
--- [PYTHON TAM TAKIM]
=========== 728 passed, 1 skipped, 154 warnings in 321.05s (0:05:21) ===========
--- [WEB] build
✓ built in 1.84s
--- [WEB] test
ℹ tests 98 ℹ pass 98 ℹ fail 0 
--- [WEB] oxlint uyarı/hata: 16/0
--- [TARAYICI] sahte paket derleme + sunucular
✓ built in 1.68s
--- [CACHE] gerçek tarayıcı: damga değişince yeniden çekim
{"once":"69.761","sonra":"69.762","degisti":true,"sure_sn":60,"summary_istek":[1,2],"damga_istek":[1,3],"hatalar":[]}
--- [TARAYICI] 50 ölçüm (platform + müşteri koyu/açık, 1440/375)
ölçüm 50 | belge taşması [] | iç taşma 1440 [] | iskelet [] | boş [] | hatalar [] | geçiş ms medyan 80 p90 177 max 302
=== TUR 5 bitti 14:19:03 UTC ===
```
```
=== TUR 6  14:19:03 UTC ===
--- [DB+API] eşzamanlama + hedef takımlar
================= 54 passed, 1 skipped, 83 warnings in 18.89s ==================
--- [WORKER] içe aktarma + iş etiketleri
worker içe aktarıldı; zamanlanan iş 20 | etiketsiz []
--- [PYTHON TAM TAKIM]
=========== 728 passed, 1 skipped, 154 warnings in 307.80s (0:05:07) ===========
--- [WEB] build
✓ built in 1.98s
--- [WEB] test
ℹ tests 98 ℹ pass 98 ℹ fail 0 
--- [WEB] oxlint uyarı/hata: 16/0
--- [TARAYICI] sahte paket derleme + sunucular
✓ built in 1.46s
--- [CACHE] gerçek tarayıcı: damga değişince yeniden çekim
{"once":"69.761","sonra":"69.762","degisti":true,"sure_sn":60,"summary_istek":[1,2],"damga_istek":[1,3],"hatalar":[]}
--- [TARAYICI] 50 ölçüm (platform + müşteri koyu/açık, 1440/375)
ölçüm 50 | belge taşması [] | iç taşma 1440 [] | iskelet [] | boş [] | hatalar [] | geçiş ms medyan 80 p90 173 max 317
=== TUR 6 bitti 14:27:19 UTC ===
```

## 5. Kabul kriteri ve kalanlar
- Üç ardışık turda (4, 5, 6) sıfır başarısızlık: DB+API 54/54 (+1 atlanan: yerel süper kullanıcı testi), tam Python takımı 728/728, worker 20 iş etiketli,
  web build 0 hata, test 98/98, oxlint 16 uyarı 0 hata, gerçek tarayıcı önbellek testi (damga değişti → 60 sn içinde /summary yeniden çekildi, yeni değer
  çizildi), 50 ölçüm taşma/iskelet/hata 0, geçiş medyan 80 ms.
- Veri izolasyonu: test_senkron (müşteri yalnız kendi + küresel iş kayıtları; başka kiracının santral damgası/SCADA'sı boş) + test_rls_izolasyon.
- KANITLANAMAYAN / KAPSAM DIŞI: canlı sistemde gerçek worker tetiklemesiyle uçtan uca tazeleme (sahte API ile ölçüldü; canlı doğrulama dağıtım sonrası);
  Firefox/WebKit koşulmadı (Chrome); müşteri paneli metinleri (piyasa dili) bilerek değiştirilmedi, platform ona uydu.
- Dağıtım gerekirse: api + web imajları (damga_service, isler_service etiketi; web); alembic ve .env değişikliği YOK. Commit/push/dağıtım ONAY BEKLİYOR.

## 6. Mühür ve canlı kanıt (26.10)
v2.496 = cdfdb9a, CI #600 yeşil, ssh dağıtım api + web (alembic/.env yok). Sunucu HEAD cdfdb9a; index.html + **22/22 JS/CSS** referansla sha256 birebir;
sözlük metinleri canlı `sozluk-*.js` parçasında («bayat» kalıntısı 0); api konteynerinde `damga_service.hesapla` gerçek santralda 9 alan döndü
(son_piyasa 26.10 00:15, son_is 09:33, son_meteo 03:00, santral_ozu) ve ETag iki çağrıda sabit; api log 0 traceback, 4 işçi açıldı.
