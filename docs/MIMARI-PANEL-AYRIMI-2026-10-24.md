# PVQuant — Yönetici paneli / Müşteri paneli mimari analizi (24.10.2026)

Salt okunur inceleme; kod, şema ve işlev değiştirilmedi. Her bulgu dosya:satır ile dayanaklıdır (HEAD 46f5a69, v2.477).
Yöntem: `apps/api/main.py`, `apps/api/deps.py`, `src/pvquant/services/{auth,paylasim,basvuru,isler,api_anahtar}_service.py`,
`src/pvquant/db.py`, `alembic/versions/*`, `docker-compose.yml`, `Caddyfile*`, `web/src/{App,shell/Kabuk,api/client,features/**}`
doğrudan okundu; iki keşif ajanının raporu kaynakta çapraz doğrulandı.

## 0. Altı sorunun kısa cevabı

| Soru | Cevap |
|---|---|
| İki ayrı panel altyapımız var mı? | **Hayır.** Tek SPA (`web/`), tek API (`apps/api/main.py`), tek rol ekseni. Platform (PVQuant personeli) için ne rol, ne uç, ne ekran var. |
| Mevcut panel kime uygun? | **Müşteri kuruluşuna** (santral sahibi/işletmeci/trader): kiracıya bağlı 3 rol (viewer/editor/admin), santral odaklı 9 sayfa. Kiracı yöneticisi için ekip, API anahtarı, webhook, paylaşım, arşiv yönetimi içinde. |
| Yönetici (platform) panelinde ne olmalı? | Müşteriler/kiracılar (oluştur, askıya al, plan/durum), kullanıcılar (kiracılar arası arama, parola/2FA sıfırlama), santral envanteri (tüm kiracılar), sistem durumu (gece işleri, meteo arşivi, worker, DB, yedek), kullanım istatistikleri (tahmin koşusu, rapor, API anahtarı/istek, SCADA satırı), vitrin başvuruları, denetim izi, abonelik (plan/limit tanımları). §4.1. |
| Müşteri panelinde ne olmalı? | Bugünkü 9 sayfa korunur; üç «platform sızıntısı» (vitrin başvuruları, gece işleri ayrıntısı, meteo arşivi) çıkarılır; Portföy'ün altındaki yönetim bölümleri «Kuruluş ayarları» sayfasına toplanabilir. §4.2. |
| Hangi özellikler eksik? | Platform rolü ve kiracı CRUD'u; kiracı `plan`/`status` zorlaması; jeton iptali; genel denetim izi; rapor tablolarında RLS; güvenlik başlıkları; proxy arkasında IP; santral bazlı yetki (`plant_groups` boş); davet e-postası/ilk giriş parola değişimi. §3. |
| Ayrı uygulama mı, ortak altyapı + rol mu? | **Ortak altyapı üzerinde kapsam (scope) tabanlı ayrım**: aynı depo, aynı API süreci, aynı tasarım sistemi; ayrı JWT kapsamı (`kapsam: "platform"`), ayrı yol öneki (`/v1/yonetim/*`, SPA `/yonetim`), ayrı kabuk varyantı. Ayrı uygulama şu ölçekte (2 kiracı, 1 geliştirme hattı) ikiye katlanan maliyet ve iki tasarım dilidir; ayrı *süreç/alan adı* ileride isteğe bağlı eklenebilir. §4. |
| Mevcut sistemi bozmadan nasıl? | Yalnız EKLEME: yeni tablo/sütunlar, yeni `platform_yetkisi` bağımlılığı, yeni `/v1/yonetim/*` uçları, SPA'da yeni yol kapısı. Mevcut `/v1/*` sözleşmeleri değişmez; tek istisna vitrin başvurularının kiracı yöneticisinden platform rolüne taşınması (kodda zaten «taşınacak» notu var). Faz planı §5. |

## 1. Mevcut durum (kanıtlı)

### 1.1 Kimlik ve roller
- Giriş: `POST /v1/auth/login` (5/dk) → `auth_service.giris` (`auth_service.py:57-82`): e-posta küresel benzersiz, bcrypt, pasif hesap «hatalı» der, TOTP açıksa `iki_adim_gerekli` ile ikinci adım. JWT HS256, ömür `JWT_SAAT = 12` (`:9`), iddialar yalnız `sub, tenant_id, role, exp`.
- Kayan oturum: `POST /v1/oturum/yenile` rol/aktiflik ve firma adını DB'den taze okur (`:161-177`). İptal listesi yok.
- Bağımlılıklar (`apps/api/deps.py`): `gecerli_kullanici` (yalnız imza + süre, DB'ye bakmaz), `yazma_yetkisi` (editor|admin), `yonetici_yetkisi` (admin), `api_anahtari(kapsam)` (X-API-Key). Başka rol denetimi yok.
- Rol kümesi: `users.role CHECK IN ('viewer','editor','admin')` (`alembic/versions/d688ccc7983c_ilk_sema.py:28`), `ROLLER` (`auth_service.py:93`). **Platform/superadmin rolü, kiracı CRUD ucu, kimliğe bürünme yok.** Kiracı yalnız `tenant_ve_admin_olustur` (`auth_service.py:26-35`) ile, konteynerde elle Python çağrısıyla açılır (`docs/sunucu-kurulum.md:196-206`); tek kod çağıranı `scripts/smoke.py:84`.
- Rol kapıları (API): admin → santral arşivle/geri al, `/v1/takim*`, `/v1/vitrin/basvurular*`, API anahtarı, webhook, paylaşım yaz, SCADA sil. editor|admin → santral ekle, alarm ata/kural, fizik, segment, EPİAŞ, EAK, tarife, kayıp/güç/bankable hesapla, SCADA yükle, tahmin koş (13 uç). Diğer tüm okumalar her role açık (`/v1/kullanicilar` dahil: kiracının tüm e-postaları viewer'a görünür).
- Rol kapıları (UI): `rolum()` JWT'den okur (`web/src/api/client.ts`, yalnız görünürlük); admin → Portföy'de GelenTalepler/DisErisim/SantralArsivi, Ekip tablosu, SCADA sil; admin|editor → «Yeni santral bağla», alarm atama. **Santral ayarları (segment, tarife, EAK, fizik, alarm kuralları), SCADA yükleme, tahmin koşusu ve hesapla düğmeleri viewer'a da çizilir**; yalnız sunucu 403 der.

### 1.2 Kiracı izolasyonu
- `tenant_baglami` (`src/pvquant/db.py:17-30`): `SET LOCAL ROLE pvq_app` (NOLOGIN rol, `ilk_sema.py:121`) + `app.tenant_id`; iş tablolarında FORCE RLS `tenant_id = current_setting('app.tenant_id')` (plants, scada_hourly, forecast_*, skill_daily, alerts, api_keys, webhooks, konformal_ayar, iklim_*, forecast_daily, paylasimlar [kaynak VEYA hedef okur, kaynak yazar], paylasim_denetim).
- `sistem_baglami` (`db.py:34`): rol değişimi yok; uygulama DB kullanıcısı `pvquant` = Postgres imajında süper kullanıcı (`docker-compose.yml:6`) → RLS'yi tümüyle atlar. Docstring «başka yerde YASAK» dese de auth, 2FA, API anahtarı arama, paylaşım okumaları, işler, başvurular, piyasa/meteo, worker ve betikler kullanıyor; güvenlik oralarda WHERE koşuluna dayanır.
- RLS'siz tablolar: `tenants, users, user_groups, jobs_log, piyasa_fiyat, meteo_*, vitrin_basvurulari, parola_sifirlama, kurtarma_kodlari` ve **`report_stats`, `report_log`** (tenant_id var, politika yazılmamış; migration kendi notuyla: `v2103_report_tables.py:5-6`).
- `tenants(plan DEFAULT 'pilot', status DEFAULT 'active')`: `plan` hiçbir yerde okunmuyor; `status` yalnız worker ve HTML rapor provasında süzgeç. **Girişte kiracı durumu denetlenmiyor** (askıya alınmış kiracı oturum açar).
- `plant_groups`/`user_groups` şemada var, kodda kullanılmıyor → kiracı içinde santral bazlı yetki yok.
- Kuruluşlar arası paylaşım (`paylasim_service.py`): hedef e-postadan kiracı bulunur, izinler `tahmin:oku|karne:oku|gerceklesen:oku`, bitiş/iptal/takma ad, her karar `paylasim_denetim`'e yazılır; yalnız toplulaştırılmış veri döner. Tek gerçek kiracılar-arası köprü budur ve temizdir.

### 1.3 Sayfalar ve kabuk (web/src)
- 9 sayfa, URL'siz durum yönlendirmesi (`App.tsx`), yol kapıları `/yontem`, `/parola-yenile`, `?vitrin`. Santral seçimi kabukta; Portföy ve Hakkında dışındakiler `plantId` ister.
- Analitik: Portföy (KPI, tablo, portföy tahmini, DSG), Santralim (özet, grafik, hava, künye, matris, güneş yolu, 7 gün, aylık), Tahminler, Doğruluk, Kalibrasyon, Aylık beklenti, Raporlar, Hakkında.
- Kuruluş yönetimi (müşteri-admin): Portföy'ün alt yarısı (Dış erişim, Santral arşivi, Paylaşım, Hesap ve ekip), Santralim kart 3 (segment, tarife, EAK, fizik, alarm kuralları), Veri yükleme (EPİAŞ kimliği, SCADA yükle/dışa/sil), santral ekleme (kabuk).
- **Platform işlevi olup müşteri paneline sızanlar:** (a) `GelenTalepler` — vitrin başvuruları (`vitrin_basvurulari` kiracı sütunsuz; `basvuru_service.listele` sistem bağlamında; uç `yonetici_yetkisi`) → **her kiracının yöneticisi PVQuant'ın tüm satış adaylarını (e-posta, santral, güç) görür ve «okundu» işaretler**; kod notu: «gerçek çok kiracılılıkta platform-sahibi rolüne taşınacak» (`main.py:658-659`). Bugün canlıda iki kiracı var (Meridyen Enerji, Deneme Lab) — ikisi de görüyor. (b) `GeceIsleriKarti` (`/v1/isler`): kiracının + küresel işlerin durumu (ayrıntı gizli) — müşteri için «tahminim gece koştu mu» sorusu meşru, ama worker sağlığı platformun işi. (c) Hakkında «Meteoroloji arşivi» — küresel indirme istatistiği.
- Ortak yapı taşları (yeniden kullanılabilir): `index.css` jeton/sınıfları (iki tema), `parcalar.tsx` (Kart, Kpi, Sayfa, SayfaIskeleti, biçimleyiciler), `lib/{Meta,EChart,useTema,bicim}`, `api/client.ts` (getir/gonder, 60 sn bellek, 401 → giriş, `bellektenOku`), `Giris.tsx` (2FA dahil), `GunesLogo`. **Kabuk santrala sıkı bağlı** (santral seçici, plantId alarmları, telemetri, sabit `SAYFALAR/IKONLAR`); ikinci panel için nav listesi ve yan menü gövdesi prop olmalı ya da palet/tema/çekmece parçaları ayrılmalı.

### 1.4 Güvenlik mekanizmaları (özet)
Var: bcrypt, TOTP + 10 kurtarma kodu (bcrypt), tek kullanımlık 30 dk parola sıfırlama (SHA-256 saklı), slowapi (giriş 5/dk, vitrin, sıfırlama), CORS beyaz liste, API anahtarı SHA-256 + sabit zamanlı kıyas + kapsam + rpm, webhook HMAC-SHA256 zaman damgalı imza, son etkin yönetici korunur, pasif kullanıcı tazeleyemez, paylaşım denetim izi, DB/API portları 127.0.0.1.
Yok/eksik: güvenlik başlıkları (Caddyfile'da yalnız Cache-Control), JWT iptali (pasifleştirme/rol değişimi 12 saate kadar geçerli jetonu düşürmez — `gecerli_kullanici` DB'ye bakmaz), kiracı `status` zorlaması, genel denetim izi (giriş, rol, anahtar üretimi, SCADA silme, arşivleme kayıtsız), proxy arkasında gerçek IP (uvicorn `--forwarded-allow-ips` yok; `reverse_proxy api:8000` → hız sınırı büyük olasılıkla Caddy IP'sine kilitli; çıkarım, canlıda sınanmadı), hız sınırı ve API rpm süreç başına (4 işçi), TOTP ve webhook sırları düz metin, davet e-postası ve ilk girişte zorunlu parola değişimi yok, JWT localStorage'da, `PVQ_JWT_SECRET` yoksa dev varsayılanına sessiz düşüş, `/v1/healthz` DB'ye bakmaz, metrik yok, depoda kimliksiz eski uygulama (`src/pvquant/api/main.py`, dağıtılmıyor).

## 2. Değerlendirme: üç kullanıcı türü

| Tür | Bugün | Olması gereken |
|---|---|---|
| Platform yöneticisi (PVQuant personeli) | Rol yok; iş sunucuda Python/CLI ile (`tenant_ve_admin_olustur`, `sifre_sifirla.py`, docker logları) | Ayrı kapsamlı kimlik, kiracı/kullanıcı/sistem/kullanım/başvuru/denetim ekranları, kimliğe bürünme (izli, süreli) |
| Müşteri kuruluş yöneticisi (admin) | Ekip, anahtar, webhook, paylaşım, arşiv, SCADA sil, santral ayarları | Aynı + kuruluş profili, denetim izi kendi kiracısı için, santral bazlı yetki (ileride) |
| Standart müşteri kullanıcısı (editor/viewer) | editor yazar, viewer okur; UI yazma kontrollerini viewer'dan gizlemez | Rolün göremeyeceği eylem çizilmez; `/v1/kullanicilar` yalnız alarm atamada gerekir → editor|admin |

## 3. Boşluklar (öncelik sırası)

Güvenlik (panel ayrımından ÖNCE kapatılmalı — yönetici paneli bunların üstüne kurulmamalı):
1. Vitrin başvuruları her kiracı yöneticisine açık (veri sızıntısı). Platform kapsamına taşı; geçici çözüm: `PVQ_PLATFORM_TENANT_ID` ile tek kiracıya kilitle.
2. `report_stats`/`report_log` RLS'siz (tenant_id var; politika bir migration).
3. Uygulama süper kullanıcıyla bağlanıyor; `sistem_baglami` RLS'yi atlıyor ve yaygın. En az: uygulama için `pvquant_app` giriş rolü (NOSUPERUSER) + `pvq_app` devralımı; `sistem_baglami` çağrılarını listele ve gerekçelendir.
4. Jeton iptali: `users.oturum_surumu` (int) sütunu, JWT'ye `sv` iddiası, `gecerli_kullanici`'da hafif kıyas (bellekte 60 sn önbellekli sorgu) — pasifleştirme/rol değişimi/parola değişimi sürümü artırır.
5. Kiracı `status` girişte ve tazelemede denetlensin (`suspended` → 403 «hesap askıda»).
6. uvicorn `--proxy-headers --forwarded-allow-ips=<caddy ağı>`; hız sınırı/rpm için paylaşımlı sayaç (Postgres tablo yeter; Redis şart değil).
7. Caddy güvenlik başlıkları (HSTS, nosniff, frame-ancestors/CSP, Referrer-Policy).
8. Genel denetim izi tablosu `denetim_izi(tenant_id NULL=platform, aktor, eylem, nesne, ayrıntı jsonb, ip, zaman)`; yazanlar: giriş/çıkış, takım, anahtar, webhook, arşiv, SCADA sil, ayar değişiklikleri, platform eylemleri.
9. TOTP/webhook sırları için uygulama düzeyi şifreleme (Fernet, anahtar env'de); TOTP son kullanılan sayaç.
10. Davet e-postası + `parola_degistir_zorunlu` bayrağı.

Ürün/mimari:
11. Platform kimliği ve kiracı CRUD'u yok (bugün sunucuda elle).
12. `plan` tanımsız; limit/kota kavramı yok (santral sayısı, kullanıcı sayısı, API rpm toplamı, rapor sayısı).
13. Kullanım istatistiği yok (API anahtarı `last_used_at` dışında).
14. Sistem durumu kiracılar arası görünmüyor (gece işleri yalnız kiracı penceresinden).
15. Santral bazlı yetki (`plant_groups`) uygulanmamış — büyük kuruluşlarda gerekecek.
16. UI'da rol dışı eylemler çizili (viewer).

## 4. Önerilen mimari: ortak altyapı, kapsam tabanlı iki yüz

**Karar:** tek depo, tek API süreci, tek tasarım sistemi; iki **kapsam** (`musteri`, `platform`), iki **yol öneki**, iki **kabuk varyantı**. Gerekçe: (a) mevcut RLS + JWT + tasarım yatırımı yeniden kullanılır; (b) kiracı verisine platform erişimi zaten `sistem_baglami` ile var, onu *disiplinli* bir kapıya almak ayrı uygulama kurmaktan güvenlidir; (c) 2 kiracı/1 geliştirme hattı ölçeğinde iki uygulama = iki dağıtım, iki tasarım dili, iki kimlik akışı. Ayrı alan adı (`yonetim.pvquant.com`) istenirse Caddy'de aynı SPA'ya ikinci site bloğu yeter; süreç ayrımı gerekmez.

### 4.0 Kimlik modeli
- Yeni tablo `platform_kullanicilar(id, email UNIQUE, pw_hash, totp_*, aktif, rol IN ('operator','sahip'), oturum_surumu, created_at)` — kiracı tablosuna bağlı değil. (Alternatif `users.tenant_id NULL` reddedildi: NOT NULL kısıtı, RLS kalıbı ve «her kullanıcı bir kiracının» varsayımı bozulur.)
- Ayrı giriş ucu `POST /v1/yonetim/giris` (2FA ZORUNLU), JWT iddiaları `{sub, kapsam:"platform", rol, exp(≤4 sa), sv}`. Müşteri JWT'sine `kapsam:"musteri"` eklenir (eksikse musteri sayılır → geriye uyumlu).
- Bağımlılıklar: `gecerli_kullanici` platform jetonunu **reddeder** (kapsam uyuşmazlığı 403), yeni `platform_yetkisi(rol)` yalnız platform jetonunu kabul eder. İki yüz asla aynı jetonla açılmaz.
- Kimliğe bürünme: `POST /v1/yonetim/kiracilar/{id}/goruntule` → 15 dk'lık, `role:"viewer"`, `kapsam:"musteri"`, `temsil:{platform_sub}` iddialı jeton; denetim izine yazılır; panelde kırmızı şerit «Platform görüntülemesi — salt okunur». Yazma uçları `temsil` iddiasını reddeder.
- DB erişimi: platform uçları için `platform_baglami()` = `sistem_baglami`'nin ADLI ve denetimli sürümü (her çağrı denetim izine); kiracı verisini okurken yine `tenant_baglami(id)` tercih edilir (RLS devrede kalır, yalnız kiracı kimliği platformdan gelir).

### 4.1 Yönetici paneli sayfaları (`/yonetim`)
1. **Genel bakış** — kiracı sayısı, aktif santral/kWp, son gece işleri özeti, açık başvurular, son 24 sa hata sayısı, yedek yaşı.
2. **Müşteriler (kiracılar)** — liste (ad, plan, durum, santral/kullanıcı sayısı, son giriş, oluşturma); oluştur (firma + ilk yönetici, davet e-postası), askıya al / yeniden aç, plan ata, notlar; kiracı detayı: kullanıcılar, santraller, kullanım, denetim, «görüntüle».
3. **Kullanıcılar** — kiracılar arası arama, pasifleştir, parola sıfırlama bağlantısı gönder, 2FA sıfırla (bugün `sifre_sifirla.py`).
4. **Santraller** — tüm kiracıların santralleri: kapasite, son SCADA, son koşu, kalibrasyon durumu, WMAPE; sorunlu santral filtresi (veri gecikmiş, koşu düşmüş).
5. **Sistem durumu** — `jobs_log` kiracılar arası (hata ayrıntısıyla), worker son nabız, meteo arşivi (bugün Hakkında'daki tablo), piyasa fiyatı tazeliği, DB boyutu/hypertable parçaları, yedek dosyaları (`yedekler/`), API sağlık (DB'li healthz), sürüm.
6. **Kullanım** — kiracı × ay: tahmin koşusu, SCADA satırı, rapor indirme (`report_log`), API anahtarı istekleri (yeni `api_kullanim` sayaç tablosu), webhook teslimleri; plan limitleriyle kıyas.
7. **Başvurular** — bugünkü GelenTalepler buraya taşınır; durum (yeni/görüşüldü/teklif/kapandı), not, kiracıya dönüştür.
8. **Denetim izi** — `denetim_izi` filtreli görünüm (kiracı, aktör, eylem, tarih).
9. **Abonelik/planlar** — plan tanımları (ad, santral/kullanıcı/rpm/rapor limitleri, özellik bayrakları); faturalama entegrasyonu kapsam dışı (ileride iyzico/Stripe webhook'u bu tabloya yazar).

### 4.2 Müşteri paneli
- 9 sayfa aynen; çıkarılanlar: GelenTalepler (→ platform), Hakkında «Meteoroloji arşivi» (→ platform; müşteriye yalnız «veri kaynağı ve son güncelleme» satırı), Gece işleri kartı sadeleşir («bu santral için son tahmin/kalibrasyon ne zaman koştu» — zaten Santralim künyesinde var; worker sağlığı platforma).
- Yeni sayfa **Kuruluş ayarları** (`ayarlar`): Portföy'ün alt yarısı (Hesap ve ekip, Dış erişim, Paylaşım, Santral arşivi) buraya; Portföy saf analitik kalır. Kabuk'ta ayrı bir «Kuruluş» grubu; URL'siz yönlendirme korunur (ileride `history` ile gerçek yol önerilir ama bu turun konusu değil).
- Rol farkındalığı: viewer'a yazma kontrolleri çizilmez (`rolum()` kapıları Santralim kart 3, Veri yükleme, hesapla düğmeleri); editor santral ayarlarını görür.
- Kiracı içi denetim izi (kendi kuruluşu): Kuruluş ayarları'nda salt okunur liste.

### 4.3 Tasarım dili ve ortak bileşenler
- Aynı jetonlar, `Kart/Kpi/Sayfa/Meta/EChart`, aynı tipografi; platform yüzü **koyu sabit** ve üst çubukta ayırt edici «PLATFORM» rozeti + farklı vurgu rengi (müşteri markası #0E7C5A yerine nötr lacivert) — yanlış pencerede işlem riskine karşı.
- Kabuk yeniden kullanımı için refactor: `Kabuk` → `KabukIskeleti({nav, yanGovde, ustSag, children})` + `MusteriKabugu` (santral seçici, alarm zili, telemetri) + `PlatformKabugu` (kiracı arama, ortam rozeti). Palet, tema, çekmece ortak parçaya alınır. Mevcut `Kabuk` davranışı birebir korunur (test: `test/vitrin/hiz.test.ts` bekçileri).
- Tablo/çip/form kalıpları `bilesen-dili.md` ile aynı; yönetici tabloları için `table.veri.santral` kalıbı yeterli.

## 5. Uygulama adımları (mevcut sistemi bozmadan)

Kural: her faz yalnız EKLER; mevcut uçların yanıt şekli, RLS politikaları ve hesap servisleri değişmez; her faz kendi mührüyle (pytest + RLS testi + web kapıları + canlı doğrulama) gider.

- **Faz 0 — Sertleştirme (ön koşul, ~1 mühür):** §3 madde 1 (geçici kilit), 2, 5, 6, 7; `PVQ_JWT_SECRET` yoksa üretimde başlamama; `healthz` DB kontrolü. Şema: yalnız `report_*` politikaları.
- **Faz 1 — Platform kimliği (şema + API):** `platform_kullanicilar`, `denetim_izi`, `users.oturum_surumu`; `kapsam` iddiası; `platform_yetkisi`; `/v1/yonetim/{giris,oturum,kiracilar,kullanicilar,basvurular,denetim}`; kiracı oluşturma ucu (`tenant_ve_admin_olustur` + davet e-postası); vitrin başvuruları platforma taşınır (müşteri ucu 410/kaldırılır — UI aynı mühürde). RLS izolasyon testine «platform jetonu kiracı ucunu açamaz / kiracı jetonu yönetim ucunu açamaz» eklenir.
- **Faz 2 — Yönetici SPA (`/yonetim`):** `App.tsx` yol kapısı; `PlatformKabugu`; sayfalar Genel bakış, Müşteriler, Kullanıcılar, Başvurular, Denetim. Giriş ekranı aynı `Giris` bileşeni, platform ucu ile. Kabuk refactor'u bu fazda, müşteri tarafı piksel-birebir doğrulanarak (kare.mjs/pngfark).
- **Faz 3 — Sistem durumu ve kullanım:** `jobs_log` kiracılar arası uç, worker nabzı (`jobs_log`'a «heartbeat»), meteo/piyasa tazeliği, yedek yaşı, `api_kullanim` sayaç tablosu (webhook/anahtar/rapor), Kullanım sayfası; müşteri tarafından Hakkında arşivi ve gece işleri ayrıntısı çekilir.
- **Faz 4 — Planlar ve limitler:** `planlar` tablosu + `tenants.plan` FK; limitler yalnız **uyarı** olarak başlar (panelde rozet), sonra zorlayıcı; kimliğe bürünme (salt okunur, izli).
- **Faz 5 — Müşteri paneli yeniden düzeni:** «Kuruluş ayarları» sayfası, Portföy sadeleşir, viewer'dan yazma kontrolleri gizlenir, kiracı içi denetim izi; `plant_groups` ile santral bazlı yetki tasarımı (ayrı karar).

Sınırlar: tahmin/kalibrasyon/hesap servisleri, SCADA işleme, API sözleşmeleri (`/v1/dis/*` dahil), mevcut RLS politikaları ve kiracı rol kümesi değişmez. Gerekli şema işleri yalnız yeni tablo/sütun ve iki eksik politika.

## 6. Açık kararlar (kullanıcıya)
1. Platform girişi için alan adı: aynı adres `/yonetim` mi, `yonetim.pvquant.com` mi (Caddy'de ikinci blok; SPA aynı).
2. Kimliğe bürünme istenir mi (destek için çok değerli; kurumsal müşteri sözleşmesinde açıkça yazılmalı).
3. Davet e-postası altyapısı (`posta_service` var; SMTP ayarı canlıda açık mı doğrulanmadı).
4. Faz 0'daki vitrin başvurusu kilidi: hangi kiracı «platform sahibi» (Meridyen Enerji?) — env ile verilecek.
5. Plan/limit tanımları: ilk sürümde hangi sayaçlar zorlayıcı olacak.

Durum: analiz dosyası commit edilmedi (biriktirme kuralı); kod değişikliği yok.
