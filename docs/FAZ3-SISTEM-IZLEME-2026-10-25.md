# Faz 3 — Sistem izleme: `/yonetim` «Sistem» sayfası (25.10.2026) — CANLI v2.485
**Durum:** v2.485 = 856a88d (25.10), CI #580 yeşil (7 dk 11 s). Sunucu: `git pull`, api + worker + web imajları, yeni api imajıyla
`docker compose run --rm --no-deps api alembic upgrade head` → `v2485_faz3_sistem (head)`, `up -d --force-recreate api worker web`.
Canlı index.html + **19/19 JS/CSS** referans derlemeyle birebir; `/yonetim` 200; `/v1/yonetim/{sistem,isler,santraller}` başlıksız 422,
bozuk jeton 401; `/v1/healthz` ok; api ve worker loglarında hata 0. Worker açılış nabzı `sistem_nabiz`'e 24 sn içinde düştü
(`is_sayisi` 19, `aralik_dk` 5) ve 5 dk aralık işi tam zamanında tazeledi (13:34:54 → 13:39:54 UTC). Gerçek hesapla `/yonetim` → «Sistem» sayfasının gerçek veriyle görünümü kullanıcıda.

Dayanak: `docs/YONETICI-PANELI-YOL-HARITASI-2026-10-24.md` §6 «Sistem izleme» satırı; Faz 2 defteri «KALAN» ilk kalemi.
Tahmin/kalibrasyon/hesap servisleri, müşteri `/v1/*` sözleşmeleri (`/v1/isler`, `/v1/hakkinda` dahil), RLS politikaları ve
müşteri paneli ekranları DEĞİŞMEDİ; her şey ekleme. «Hakkında meteo arşivi kartını müşteriden platforma taşı» temizliği
bilerek bu fazda yapılmadı (ayrı rötuş).

## NE
1. **Şema** `alembic/versions/v2485_faz3_sistem.py`: `sistem_nabiz(bilesen PK, zaman, ayrinti jsonb)` — bileşen başına TEK satır,
   RLS yok, `pvq_app`'e SELECT/INSERT/UPDATE. jobs_log'a yazılmadı: o tablo müşterinin «gece işleri» listesine tenant'sız satırları
   da taşıyor, nabız orada görünürdü.
2. **Servis** `src/pvquant/services/sistem_service.py` (salt okunur; tek yazan `nabiz_yaz`):
   - `nabiz_yaz(bilesen, ayrinti)` — worker'dan UPSERT; hata yutulur ve günlüğe düşer (nabız asıl işleri düşürmez).
   - `ozet(aktör)` — nabız (`calisiyor` ≤15 dk / `sessiz` / `yok`), gece turu (ölçüt `isler_service.bayat_isler(30)` BİREBİR: müşteri ve
     platform aynı hükmü görür; üretici üç işin son başarılı koşusu), son 24 saat iş/hata sayısı, hava arşivi kaynak başına
     (`acik_nwp.arsiv_durumu`, 36 sa eşiği), piyasa fiyatı (son güncelleme, 36 sa), yedek (son başarılı `gece_yedek|acilis_yedek`,
     30 sa; son deneme ve ayrıntısı), veritabanı boyutu, etkin/arşivli santral. **Bayatlık hükümleri ve eşikler uçta**; arayüz eşik
     uydurmaz (web testi pinler).
   - `isler(aktör, saat, yalniz_hata, job, tenant_id, limit)` — kiracılar arası `jobs_log`, kiracı/santral adı birleşik, **hata
     ayrıntısı (`detail`) dahil**; iş adları `ISIM_TR` ile Türkçe; `is_turleri` süzgeç için.
   - `santraller(aktör, sorunlu)` — tüm kiracıların etkin santralleri: son geçerli SCADA, son koşu, son iş hatası; bayraklar
     `scada_yok/scada_bayat(48 sa)/kosu_yok/kosu_bayat(30 sa)/kiraci_askida`.
3. **Worker nabzı** `apps/worker/main.py`: açılışta ve her 5 dk `interval` işi `sistem_nabiz`'e yazar (`baslatma`, `is_sayisi`,
   `aralik_dk`); `--once` kipinde nabız yok. Nabız «zamanlayıcı ayakta» demektir; işler ayrı izlenir.
4. **API** `apps/api/yonetim.py`: `GET /v1/yonetim/sistem`, `GET /v1/yonetim/isler?saat&yalniz_hata&job&tenant_id&limit`,
   `GET /v1/yonetim/santraller?sorunlu` — `platform_yetkisi()` (operatör de okur), salt okunur → denetim izine yazılmaz.
5. **İstemci** `web/src/api/yonetim.ts`: `SistemOzet/IsKaydi/SantralEnvanter` tipleri, `sistem/isler/santraller`, `sorgu()` yardımcısı
   (denetim de onu kullanır), `yasTr` («3 dk önce / 8 saat önce / 2 gün önce»).
6. **Sayfa** `web/src/features/yonetim/Sistem.tsx` (menüde Genel bakış'tan sonra «Sistem», ikon nabız çizgisi): 6 KPI
   (Zamanlayıcı, Gece turu, İşler [hata sayısı], Hava verisi [bayat kaynak adıyla], Piyasa fiyatı, Yedek; uyarı tonu yalnız uçtan
   gelen hükümle), «İş kayıtları» (pencere 24/48/72/168 sa, yalnız başarısız, iş, kiracı seçimi; tablo esnek sütun İş, zaman mono,
   ayrıntı sola yaslı %38), «Santral envanteri» (yalnız sorunlu anahtarı; sorun rozetleri), «Üretici işler» (3 satır, taze/bayat),
   «Meteoroloji arşivi» (yarım kartta 440 px tabanlı tablo, kapsam yalnız tarih). Başlık sağında veritabanı boyutu + santral sayıları,
   «Yenile».
7. **Testler/araçlar:** `tests/test_yonetim_api.py` +1 (operatör 200, süzgeç geçişi, ayrıntı görünür, müşteri jetonu 403, başlıksız
   422); `tests/test_platform_db.py` +1 (nabız UPSERT tek satır, özet alanları, hatalı iş kaydı kiracı/santral/ayrıntıyla, envanter
   bayrakları); `web/test/panel/yonetim.test.ts` +2 (sayfa/yol/istemci pinleri, hükümler uçtan, müşteri `Isler` tipi ve gece işleri
   kartı ayrıntı taşımaz); `betikler/sahte-api.mjs` üç sahte uç (`NABIZ_SESSIZ=1` → sessiz/bayat kipi); kare betiği scratch
   (`sistem-kare.mjs`: Chrome kanalı, 1440 tam sayfa + 375, iki süzgeç etkileşimi, taşma/konsol ölçümü).

## NEDEN
«Dün gece ne oldu» sorusu yalnız müşterinin kendi kiracısı için ve ayrıntısız yanıtlanıyordu; zamanlayıcının ayakta olduğunun
tek kanıtı iş kayıtlarıydı (31 Ağu / 10 Eyl / 18 Eyl bayatlık vakaları). Artık personel tek ekranda zamanlayıcı nabzı, gece turu,
veri tazeliği, yedek yaşı, hangi iş hangi kiracıda neden düştü ve hangi santral veri almıyor sorularını görür.

## KANIT
- Kapılar: tsc 0 · web test **88/88** · build 0 · oxlint **16** (= main) · Python tam takım (geçici timescale DB, alembic head
  `v2485_faz3_sistem`) **700 geçti** (`test_yonetim_api` 8/8, `test_platform_db` 2/2).
- Kareler (sahte API, Chrome kanalı): 1440 ve 375 → yatay taşma 0, konsol/istisna 0, 6 KPI, 4 kart; «yalnız başarısız» 5→1 satır,
  «yalnız sorunlu» 4→3 satır; uyarı tonu normal kipte 2 (İşler 1 hata, Hava verisi GEFS bayat), sessiz kipte 4 (zamanlayıcı sessiz,
  gece turu bayat). Düzeltilenler: iş tablosunda esnek sütun «Zaman» olmuştu (İş/Kiracı sıkışıyordu) → esnek sütun İş; meteo
  «Kapsam» saatli tarihle yarım kartı 121 px aşıyordu → yalnız tarih + 440 px taban (1440'ta 0 taşma, 375'te kart içi kaydırma);
  «Hava verisi» KPI alt metni bayat kaynağı adıyla; süre hücresi tek satır.
- Canlı: yukarıdaki Durum satırı (sha 19/19, uç kapıları, log 0 hata, açılış nabzı).

## DAĞITIM NOTLARI (mühürde)
`alembic upgrade head` (sistem_nabiz) · **api + worker + web** imajları (worker nabız için yeniden derlenmeli: `docker compose build
api worker web`), `up -d --force-recreate api worker web`; Caddy değişmedi. Canlı doğrulama: worker logunda açılış nabzı,
`/v1/yonetim/sistem` nabız `calisiyor` (yaş ≤ 5 dk), iş kayıtlarında gerçek kiracı adları, envanterde Deneme Lab santrallerinin
SCADA bayraklarının gerçek verisi; müşteri paneli Hakkında/gece işleri kartı aynen.

## KALAN (Faz 4+)
Kullanım sayaçları (`api_kullanim`), plan/limit (uyarı kipi), kimliğe bürünme (salt okunur, izli), platform kurtarma kodları, askıdaki
kiracıya müşteri panelinde anlamlı mesaj, Hakkında «meteo arşivi» kartının platforma taşınması.
