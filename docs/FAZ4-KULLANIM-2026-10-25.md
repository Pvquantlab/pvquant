# Faz 4 — Kullanım sayaçları, paylaşımlı hız penceresi, `/yonetim` «Kullanım» sayfası (25.10.2026) — BİRİKİYOR (commit yok)
**Durum:** yerelde birikmiş; mühür kullanıcı «commitle» deyince (v2.486 önerilir; alembic `v2486_faz4_kullanim`).

Dayanak: `docs/YONETICI-PANELI-YOL-HARITASI-2026-10-24.md` §6 «Kullanım + sınırlayıcılar»; Faz 3 defteri «KALAN» ilk kalemi.
Tahmin/kalibrasyon/rapor/SCADA işleme servisleri, müşteri `/v1/*` sözleşmeleri ve ekranları, RLS politikaları, yetkiler DEĞİŞMEDİ.
Plan/limit (uyarı kipi) ve kimliğe bürünme Faz 5'e bırakıldı: bu faz yalnız ÖLÇÜM.

## NE
1. **Şema** `alembic/versions/v2486_faz4_kullanim.py`: `kullanim_sayac(tenant_id, gun, tur, adet)` günlük sayaç (UPSERT) ve
   `hiz_pencere(anahtar, pencere, adet)` 60 sn'lik paylaşımlı sayaç; RLS yok, `pvq_app`'e S/I/U/D.
2. **Servis** `src/pvquant/services/kullanim_service.py`: `say(tenant, tur, adet)` asla yükseltmez (günlüğe düşer); `pencere_say(anahtar)`
   sabit pencerede paylaşımlı artış, eski pencereleri aynı çağrıda siler, DB'ye ulaşılamazsa 0 döner; `ozet(aktör, ay)` kiracı başına seçili
   ay + önceki ay (dis_api, webhook, webhook_hata sayaçtan; **rapor = report_log, koşu = forecast_runs, SCADA saati = scada_hourly veri ayı
   flag='valid', yükleme = ingestion_batches sorguyla türetilir**) + etkin anahtar/webhook + son API kullanımı; `gunler(aktör, kiracı, ay)`
   günlük kırılım.
3. **Kancalar (yalnız iki):** `api_anahtar_service.dogrula` — üretim yolunda (`bul` enjekte değilken) `_paylasimli_izin`: `hiz_pencere`
   anahtar başına rpm'i tüm uvicorn işçilerinde birlikte sayar (eskiden süreç içi token bucket → 4 işçide fiilen 4×), izin verilen istek
   `dis_api` sayacına yazılır, reddedilen yazılmaz, pencere sayılamazsa süreç içi kovaya düşer (`_kova_izin`, v2.264 davranışı);
   `webhook_service.gonder` — teslim başına `webhook`, başarısızlar ayrıca `webhook_hata`. Giriş sınırlayıcısı (slowapi) dokunulmadı.
4. **API** `GET /v1/yonetim/kullanim?ay=YYYY-MM[&tenant_id]` — `platform_yetkisi()` (operatör de okur), salt okunur, denetim izine yazılmaz.
5. **İstemci** `web/src/api/yonetim.ts`: `KullanimToplam/KullanimKiraci/KullanimOzet/KullanimGunler`, `kullanim(ay)`, `kullanimGunler(id, ay)`.
6. **Sayfa** `features/yonetim/Kullanim.tsx` (menüde Müşteriler'den sonra «Kullanım»): ay seçici (son 6 ay), kiracı tablosu — Dış API,
   Webhook (+hata rozeti), Rapor, Tahmin koşusu, SCADA saat, Yükleme, Anahtar (+webhook), Son API kullanımı; her hücrede parantez içi önceki
   ay; Toplam satırı; satır → günlük kırılım (`KullanimDetay`); sıfır soluk «0» (— yalnız eksik değer). `KullanimKarti` müşteri detayında
   «Bu ay kullanım» (dl.kunye). Plan sınırı/rozeti yok.
7. **Testler/araçlar:** `tests/test_dis_api.py` fikstürü DB'siz kalsın diye `_paylasimli_izin` → kova; +1 test (pencere > rpm ret, izin
   verilen sayılır, 0 → kova yedeği, dogrula üretim yolu paylaşımlı izni çağırır); `tests/test_yonetim_api.py` +1 (ay/kiracı süzgeci,
   müşteri jetonu 403, başlıksız 422); `tests/test_platform_db.py` +1 (sayaç UPSERT, pencere iki çağrıda 1→2 ve yeni pencerede 1 + eski
   silinir, özet türetilmiş sayımlar rapor/koşu, günlük kırılım, bilinmeyen kiracı boş); `web/test/panel/yonetim.test.ts` +1;
   `betikler/sahte-api.mjs` `/v1/yonetim/kullanim`; kare betiği scratch (`kullanim-kare.mjs`).
8. **Yan düzeltme (Faz 3):** `sistem_service` nabız/tazelik yaşları negatife düşmez (`max(0, …)`): DB ile uygulama saati birkaç saniye
   kayarsa «−1 dk» yazmasın (yerel docker testinde görüldü).

## NEDEN
Kiracının ne kadar kullandığı bilinmiyordu (anahtarda yalnız `last_used_at`, webhook'ta yalnız son durum). Plan/limit işine girmeden
ölçüm gerekliydi. Hız sınırı süreç başına sayıyordu: anahtar başına 120/dk fiilen ~480/dk idi.

## KANIT
- Kapılar: tsc 0 · web test **89/89** · build 0 · oxlint **16** (= main; Kullanim.tsx yardımcıları dışa aktarılmadı) · Python: `test_dis_api`
  + `test_yonetim_api` 16/16; `test_platform_db` 3/3 (geçici timescale, alembic head `v2486_faz4_kullanim`; iki kez koşuldu, kararlı);
  tam takım (DB'li, geçici timescale) **703 passed**, 0 hata.
- Kareler (sahte API, Chrome kanalı) 1440 + 375: Kullanım listesi taşma 0, 11 sütun, 3 kiracı + Toplam; satır → günlük kırılım 25 satır;
  Müşteri detayında «Bu ay kullanım» kartı 6 satır; konsol 0.
- Canlı: henüz dağıtılmadı.

## DAĞITIM NOTLARI (mühürde)
`alembic upgrade head` (yeni api imajıyla `compose run --rm --no-deps api`) · **api + worker + web** imajları (webhook kancası worker'da
koşar) · `up -d --force-recreate api worker web`. Canlı doğrulama: `/v1/yonetim/kullanim` 422/401 kapıları; dış API anahtarı olan
kiracıda ilk istekten sonra `kullanim_sayac` ve `hiz_pencere` satırı; Kullanım sayfası gerçek hesapla kullanıcıda.

## KALAN (Faz 5+)
Planlar tablosu + `tenants.plan` FK + limit rozetleri (uyarı kipi), kimliğe bürünme (salt okunur, izli, 15 dk), platform kurtarma
kodları, askıdaki kiracıya müşteri panelinde anlamlı mesaj, Hakkında «meteo arşivi» kartının platforma taşınması.
