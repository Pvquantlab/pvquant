# Panel mimarisi — Faz 5 (v2.608)

Tarih: 12 Kasım 2026 (gece). Kapsam: müşteri paneli bilgi mimarisi (iş akışı grupları, Genel bakış açılış sayfası, KGÜP ve Paylaşım sayfaları, aşamalı
açılım) ve yönetim panelinde «teknik sistem sağlığı» ile «müşteri hizmet sağlığı» ayrımı. Tahmin çekirdeği, uzlaştırma formülleri, kalibrasyon ve
şema DEĞİŞMEDİ (göç yok). Plan ve kanıtlar: `~/Desktop/PVQuant_Faz5_Panel_Mimarisi/` (00 plan, 07 test turları, 08 teslim raporu, kanit/).

## 1. Yan menü grupları (F5-A)

Tek kaynak `web/src/shell/gruplar.ts` (`GRUPLAR`); sayfa kimlikleri, hash derin bağlantıları ve yetki kapıları değişmedi, yalnız kümelendi.
Bekçi: `web/test/panel/nav.test.ts` (her kimlik tam bir grupta; App her kimliği çizer; santralsız sayfalar `SANTRALSIZ` tek kaynaktan).

| Grup | Sayfalar |
|---|---|
| Genel bakış | `genel` (açılış), `portfoy` |
| Üretim | `santralim`, `tahminler`, `aylik`, `dogruluk`, `kalibrasyon` |
| Piyasa ve finans | `kgup` (Tahminler'den taşınan program kartları), `portfoyler` («DSG ve portföyler»), `mutabakat`, `finans` |
| Operasyon | `sayac`, `veri`, `olaylar`, `takvim` |
| Yönetim | `raporlar`, `paylasim` (Kuruluş'tan ayrılan paylaşımlar), `kurulus`, `hakkinda` |

Grup açık/kapalı durumu `localStorage.pvq_nav_kapali`; aktif sayfanın grubu her zaman açık; grup başlığı `aria-expanded` + `hidden` kapsayıcı;
yan menü `overflow-y: auto`. Açılış `#genel` (`hashBaglanti().sayfa ?? "genel"`); eski `#santralim` yer imleri çalışır. Arka uçtaki KGÜP eylem
metinleri ve sayfa kodları (`finansal_etki_service`, `mutabakat_service`, `alarm_service`, `genel_bakis_service.BAGLANTI`) «KGÜP sayfası» / `kgup`.

## 2. Durum sözlüğü (F5-C) — `src/pvquant/services/durum_sozlugu.py` (saf)

Altı durum, kötüden iyiye `SIRA`: **kritik › dikkat › doğrulanamadı › veri bekleniyor › sağlıklı › uygulanmıyor**. Birleşim `en_kotu`:
«uygulanmıyor» yalnız hepsi öyleyse; boş liste → doğrulanamadı (sinyali olmayan şey yeşil yazılmaz). Sözlük ucu `GET /v1/sozluk/durum`
(sürüm `SOZLUK_SURUMU`, etiketler, eşikler). Eşikler (`ESIK`, yalnız yanıtta; UI'da sabit yok): ölçüm dikkat 48 sa / kritik 168 sa; tahmin
dikkat 30 sa / kritik 72 sa; tahmin–ölçüm yaşı 48 sa; bağımsız doğrulama 7 gün; iş hatası 48 sa; alarm penceresi 7 gün. Kural «>»: tam eşik
değerinde durum düşmez.

Boyut kuralları: `veri_durumu` (en yeni GEÇERLİ ölçüm damgası ile son alım ayrı; hüküm damgadan), `tahmin_durumu` (üretim / güvenilirlik /
doğruluk ayrı alt sonuçlar; iş başarısı hiç okunmaz), `kgup_durumu` (adımlar tahmin / hazırlık / bildirim / kabul; **kabul her zaman
doğrulanamadı** ve hükme girmez, `dogrulanmayan=["kabul"]`; «bildirildi» müşteri beyanıdır), `mutabakat_durumu` (dönem takvimi ön/nihai
tarihleri; `resmi_durum` daima `dogrulanmadi`), `alarm_durumu`, `santral_hukmu` (eylem gereken = kritik/dikkat boyutlar).

## 3. Hizmet sağlığı (F5-C) — `hizmet_sagligi_service.py`

Beş boyut (veri, tahmin, KGÜP, mutabakat, alarm) × santral; küme tabanlı tek SQL / sinyal (DISTINCT ON yayımlanmış koşu + kapsama; kesim
öncesi koşu `kurallar.kgup_kesim` + `yayin_kosu_sql`; `kgup_surum` kaynak başına; son kapanmış ay bildirimi; `finansal_etki_sonuc`;
`alerts`/`olay`/`jobs_log`; `portfoy_uyelik`). Toplama santral → kuruluş → portföy → platform. Uçlar: `GET /v1/hizmet-sagligi` (kiracı
jetonundan; RLS), `GET /v1/yonetim/hizmet-sagligi?tenant_id=&yalniz_sorunlu=` (platform; özet süzgeçsiz, yalnız satırlar süzülür; izsiz —
`/sistem` kuralı). Yük (test DB, 25 santral × 168 sa ölçüm + 48 sa tahmin): `ozet` 50–64 ms, `platform_ozet` 40–51 ms → `plant_ids` süzgeci
ya da önbellek bu hacimde gerekmedi (F5-C incelemesi kararı; 500 ms'yi aşarsa yeniden değerlendirilir).

## 4. Genel bakış (F5-B) — `genel_bakis_service.py`, `GET /v1/plants/{id}/genel-bakis`

Dört kart: **bugün** (beklenen = yayımlanmış koşunun yerel gün toplamı; gerçekleşen yalnız bugünün geçerli ölçümü; sapma ≥ 6 ortak saat),
**yarın** (KGÜP boyutu; eylem metni adımdan), **riskler** (yalnız eylem gerektirenler; kiracı sayımı), **finans** (son kayıtlı FEM sonucu +
EPİAŞ bildirimi + maruziyet p25/p50/p75; `hesaplanamiyor` metni). Bağlantılar `BAGLANTI` (santralim / kgup / veri / finans). Web
`features/genel/GenelBakis.tsx` (`bellekten.genelBakis`, `onYukle` ön yükleme), rozet `parcalar.HizmetDurumu` + `lib/durum.ts HIZMET_DURUMU`;
jeton `.rozet-kritik` (uyarı ailesinin dolgulu türevi; yeni renk yok).

## 5. Yönetim: sistem sağlığı ↔ müşteri hizmet sağlığı (F5-D)

`sistem_service.sinifla` (saf) + `sistem_sagligi(aktor_id)`: altı bileşen — zamanlayıcı (nabız), gece işleri, hava (iş ≠ koşu: ayrı alanlar),
EPİAŞ (son bağlantı / son veri alımı / en yeni kayıt / yön), veritabanı (bağlantı, yedek; yedek doğrulaması `dogrulanamadi`), sunucu (API,
hata günlüğü `dogrulanamadi`, iş hataları). Uç `GET /v1/yonetim/sistem-sagligi` (izsiz). `Sistem.tsx` iki bölüm (sistem / müşteri hizmet
sağlığı; `sessionStorage pvq_platform_sistem_bolum`); yönetim Genel bakış iki şerit + «Dikkat gereken santraller» (kritik önce; eylem metni
ilk neden + «+n boyut»). Ağ hatası Türkçe (`api/yonetim.ts istek`).

## 6. Aşamalı açılım (F5-E) — `parcalar.Katla`

Yerleşik `details`/`summary`; kart başlığı + çip her zaman görünür, yalnız gövde/gelişmiş alanlar katlanır; `acik` yalnız dış sinyalle
(vadesi geçen sensör, hava verisinde KAYMA) AÇAR, kullanıcının kapattığını geri açmaz, sinyal sönünce kapatmaz; boş/yükleniyor durumu
katlanmaz. Santralim «Santral ayarları»: işletme «Gelişmiş alanlar» (dengeleme birimi + LÜY istisnası, veri güncelliği, risk ve arıza
kayıtları; aynı Kaydet), alarm «Eşikleri düzenle», kart düzeyi «Gelişmiş ayarlar» (fiziksel model terimleri), sensör kartı gövdesi.
Kalibrasyon: kayıp ayrışımı ve hava verisi tutarlılığı gövdeleri. Hiçbir alan silinmedi; yazma yetkisi aynı. Bekçi `test/panel/acilim.test.ts`.
Jetonlar `.katla`, `.ayar-gelismis` (skill `referans/jetonlar.md` «Katlama», `emsaller.md` «Aşamalı açılım»).

## 7. Dürüstlük kuralları (testle zorlanır)

Sayı uydurulmaz (veri yoksa null/tire); «bildirildi» = müşteri beyanı; TPYS kabulü ve EPİAŞ uzlaştırma durumu hiçbir kaynaktan doğrulanmaz
(`dogrulanamadi` / `dogrulanmadi`); iş başarısı hizmet hükmüne girmez; müşteri yüzeyinde iç terim yok (`web/test/panel/dil.test.ts`).

## 8. Testler

Python: `test_hizmet_sagligi_v2608` (9), `test_genel_bakis_v2608` (5), `test_sistem_sagligi_v2608` (4), `test_faz5_tur1_v2608` (5, eşik sınırları
ve kart durumları), `test_faz5_tur3_v2608` (3, kiracı izolasyonu / viewer / platform kapsamı / boş santral), `test_faz5_performans_v2608` (1).
Web: `nav.test.ts`, `acilim.test.ts`, `dil.test.ts`, `gecis.test.ts`, `yonetim.test.ts` güncel (toplam 112).
