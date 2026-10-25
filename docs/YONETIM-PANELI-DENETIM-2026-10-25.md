# Yönetim paneli (`/yonetim`) denetim raporu — 25.10.2026, canlı v2.487
Kaynak: kullanıcının 13 canlı ekran görüntüsü (1920 px, yonetim@pvquant.com / sahip) + yerel kaynak kodu (apps/api/yonetim.py, deps.py,
platform_service, sistem_service, kullanim_service, web/src/features/yonetim/*) + sunucuda salt okunur kontroller. Kod değiştirilmedi.
Önem: **Y** = yüksek (güvenlik/veri), **O** = orta (işlev/UX), **D** = düşük (cila).

## Bulgular (önem sırasıyla)

### Y1 — Uygulama veritabanına süper kullanıcı olarak bağlanıyor
`PVQ_DB_URL` kullanıcısı `pvquant` → sunucuda `rolsuper = t`. RLS yalnız `tenant_baglami` içindeki `SET LOCAL ROLE pvq_app` ile devreye
giriyor; `sistem_baglami`/`platform_baglami` ile açılan her oturum tüm kiracı verisini RLS'siz görür. Bugün bu bilinçli (platform
okumaları), ama bir uç yanlışlıkla `sistem_baglami` kullanırsa izolasyon sessizce düşer. Yol haritasında Faz 1 kalemiydi («DB rolü
süper kullanıcıdan indirme»), yapılmadı. **Öneri:** uygulama için ayrı `pvq_api` rolü (NOSUPERUSER, BYPASSRLS yok); platform okumaları
için `SET LOCAL ROLE pvq_platform` + yalnız SELECT; göç `alembic`'te. Faz 5 öncesi en değerli güvenlik işi.

### Y2 — 2FA zorunluluğu yalnız arayüzde
`platform_service.giris`: TOTP kurulu değilse yine tam kapsamlı 4 saatlik jeton döner (`iki_adim_kurulmali: true`); arayüz kabuğu
açmaz ama jetonla `/v1/yonetim/*` uçları curl'den çağrılabilir. Yeni açılan operatör, 2FA kurmadan tüm kiracı verisine API'den ulaşır.
**Öneri:** TOTP kapalıyken jetona `kapsam: "platform-kurulum"` ver; `platform_yetkisi` bu kapsamla yalnız `/ben`, `/iki-adim/*`,
`/parola`'ya izin versin.

### O1 — Denetim izi ve Genel bakış tabloları 1920 px'te yatay kayıyor; «Ayrıntı» ham JSON
Ekran: her iki tabloda alt kaydırma çubuğu; Ayrıntı hücresi `{"eski":"sahip@…","yeni":"…","kaynak":"ssh cli"}` kesik ve «⇤» artığıyla
görünüyor. Kiracı sütunu `e190f269` gibi uuid öneki (ad yok), Nesne `platform_user 90985188`. Eylem çipi (`cip-kod`) satır metninden
aşağıda oturuyor (dikey hiza). **Öneri:** ayrıntıyı anahtar: değer çiftleri olarak satır içi çiplerle göster (uzun değer kısalt + hover);
`denetim_service.listele` kiracı adını birleştirsin; Kiracı süzgeci uuid girdisi yerine kiracı seçimi (Sistem sayfasındaki gibi).

### O2 — Geniş ekranda tablolar sola yığılı, ilk sütun dev boşluk
`table.veri.santral` ilk sütunu esnek, diğerleri 1 %: 1920 px'te İş kayıtları, Genel bakış ve Denetim tablolarında ilk sütun ile veri
sütunları arasında ~700 px boşluk (ekran 2, 10). Okunurluk düşüyor. **Öneri:** platform tablolarında içerik genişliği sınırı (ör. 1400 px)
ya da veri sütunlarının sola yaslanması (`th/td:not(:first-child){text-align:left}`) — müşteri paneli kuralına dokunmadan `.plat-*`
altında.

### O3 — Zaman gösterimi tutarsız (mono / orantılı)
Sistem'de zamanlar mono (`25.10.2026 18:40`), Genel bakış, Müşteriler, Kullanım, Kullanıcılar, Denetim'de orantılı. Aynı yüzde iki dil.
**Öneri:** platform tablolarında zaman hücreleri tek sınıf (`td.zaman` mono tabular) — `zamanTr` çağrılarının olduğu hücreler.

### O4 — Piyasa fiyatı verisi bir gün geride (doğrulanmalı)
Ekran: «veri 24.10.2026 23:00 saatine kadar», sunucu: `max(ts_utc)=24.10 20:00 UTC`, son güncelleme 25.10 00:15 UTC. EPİAŞ D+1 PTF'i
D günü ~14:00'te yayımlar; `gece_piyasa` 03:15'te koşuyor ve 25.10 fiyatlarını almamış görünüyor. İş «tamam» yazıyor, yani sessiz.
Tahmin/DSG hesabı çekirdek — bu rapor dokunmuyor; **öneri:** `epias` piyasa servisinin hangi günü çektiği teyit edilsin; Sistem KPI'ı
«son güncelleme» yerine «veri hangi güne kadar» ile bayatlık hükmü versin (36 sa ölçütü bunu yakalamıyor).

### O5 — Küresel işler santral başına kayıt düşüyor
`gece_meteo` ve `gece_piyasa` `_logla` (santral döngüsü) ile sarılı: her gece 5'er satır «Hava verisi indirme» (biri 130,7 dk, dördü
0,0 sn) ve 5 «Piyasa fiyatları» (0,0 sn). İş listesi şişiyor, süre anlamsız. Worker zamanlayıcı kodu platform altyapısı; **öneri:**
bu iki işi `_logla_tek` ile tek satır (worker/main.py zamanlayıcı bloğu; iş gövdelerine dokunmadan).

### O6 — Platformun kiracı verisi OKUMALARI denetim izine düşmüyor
11 yazan uç izli; `kiraci_detay`, `kullanicilar`, `isler`, `kullanim`, `santraller` okumaları izlenmiyor. Profesyonel SaaS'ta
«hangi personel hangi müşteriyi ne zaman görüntüledi» sorusu sözleşme/KVKK açısından gerekir. **Öneri:** kiracı-ayrıntı okumalarına
hafif `kiraci_goruntule` kaydı (gün başına tekilleştirilmiş), Denetim süzgecinde «görüntüleme» kapsamı.

### O7 — Kiracı yöneticisi 2FA'sız
Kullanıcılar: `m.serifucas+test@gmail.com` (Deneme Lab, Yönetici) 2FA kapalı. Platform bunu görüyor ama zorlayamıyor. **Öneri:** kiracı
yöneticisi için 2FA zorunluluğu (uyarı rozetiyle başla; Faz 5 «Kuruluş ayarları»nda politika).

### O8 — Platform oturumu tarayıcı açıkken sonsuz
Jeton 4 sa, her 30 dk `oturum/yenile` → sekme açık kaldıkça süresiz; boşta kalma zaman aşımı yok; jeton `localStorage`'da (httpOnly
çerez yol haritasında «sonraya»). **Öneri:** 30 dk hareketsizlikte yenilemeyi durdur; mutlak üst sınır (ör. 12 sa) sunucuda.

### D1 — Sayı/birim tutarsızlıkları
PVDAQ Golden 33 kurulu güç Sistem'de «2,4», Müşteri detayında «2» (farklı biçimleyici). Kullanım'da sıfırlar soluk «0», Müşteriler'de
«—» (Meridyen kurulu güç) — ikincisi doğru («—» = veri yok), ilki de doğru; ama Kullanım «Son API kullanımı —» ile «Anahtar 0» yan yana.

### D2 — Santral envanteri «Son hata» bağlamsız
1.10.2026 / 8.10.2026 tarihli hatalar bugünkü satırda rozetsiz; 24 gün önceki hata ile dünkü aynı görünüyor. **Öneri:** 7 günden
eskiyi soluk, tıklayınca İş kayıtları süzülmüş.

### D3 — Operatörler sayfasında kendi satırınızda rol seçimi etkin
Backend son sahibi düşürmeyi reddediyor (doğru), arayüzde seçim yine de deneniyor ve hata metni gelir. «siz» satırında rol/pasif
kontrolleri devre dışı olmalı. «İşlem» başlığı boş sütun.

### D4 — Sunucuda yardımcı betik kaldı
`/root/pvq_platform_parola.py` (parola sıfırlama, getpass ile) duruyor; konteyner kopyası recreate ile silindi. Kalıcı çözüm
`scripts/platform_sahip.py --parola-sifirla`; betik repoya alınıp /root'tan silinmeli.

### D5 — Genel bakış sistem sağlığını göstermiyor
İlk ekran «Son işlemler»i gösteriyor; zamanlayıcı/gece turu/yedek hükmü için Sistem'e geçmek gerekiyor. **Öneri:** Genel bakış'a tek
satır sağlık şeridi (Sistem özetinden 3 rozet).

### D6 — Denetim izi süresiz büyür
`denetim_izi` için saklama politikası yok (silme kodu yok). Başarısız giriş denemeleri (IP) dahil. **Öneri:** 24 ay saklama + aylık
arşiv (ürün kararı).

## Uygulananlar — CANLI v2.488 (2675f60, CI #585; testler CI'da pvq_api rolüyle)
Sunucu 25.10: `.env` API_DB_PASSWORD (48 hex) → api + worker imajları → alembic yönetici rolüyle (`v2488_db_rolu (head)`) → `ALTER ROLE
pvq_api PASSWORD` → `up -d --force-recreate api worker`. Kanıt: api konteynerinde sistem bağlamı `('pvq_api', rolsuper=False,
bypassrls=True)`, kiracı bağlamı `('pvq_app', bypassrls=False)`; `/v1/auth/login` ve `/v1/yonetim/giris` yanlış parola 401 (denetim
izine `giris_basarisiz` pvq_api ile yazıldı), `/v1/yonetim/sistem` ve `/v1/dis/santraller` bozuk kimlik 401, `/v1/healthz` ok,
`/yonetim` 200; worker nabzı 26 sn; gece yedeği yönetici URL'siyle elle koşuldu → 36,8 MB, 14 yedek; api/worker logunda
permission denied / traceback 0. Ders: `.env` `set -a; . ./.env` ile kaynak gösterilemez (`PVQ_SMTP_FROM=PVQuant <…>` tırnaksız) —
değerler `grep '^VAR=' | cut -d= -f2-` ile okunur.
- **Y2 (25.10):** `platform_service.oturum_durumu` artık `totp_aktif` taşır; `deps.platform_yetkisi` 2FA kurulu değilse yalnız
  `PLATFORM_KURULUM_YOLLARI` (`/ben`, `/iki-adim/baslat|dogrula`, `/parola`, `/oturum/yenile`) açar, diğer uçlar 403 «iki adımlı
  doğrulama kurulumu gerekli»; `iki_adim_dogrula` önbelleği düşürür (kurulum biter bitmez tam kapsam). Jeton biçimi değişmedi: açık
  oturumlar bozulmaz, 2FA sıfırlanan operatör de anında kurulum kapsamına iner. Test: `test_iki_adim_kurulmadan_kapsam_dar`.

- **Y1 (25.10):** alembic `v2488_db_rolu` — `pvq_api` (LOGIN, NOSUPERUSER/NOCREATEDB/NOCREATEROLE/NOREPLICATION, **BYPASSRLS**):
  tüm public tablolara S/I/U/D, dizilere USAGE/SELECT/UPDATE, hypertable'lara açık GRANT (Timescale chunk'lara taşır), `ALTER DEFAULT
  PRIVILEGES` (gelecek tablolar), `GRANT pvq_app TO pvq_api` (kiracı yolu `SET LOCAL ROLE pvq_app` → RLS devrede, pvq_app BYPASSRLS
  değil). BYPASSRLS bilinçli: sistem/platform bağlamlarının bugünkü davranışı aynen; yalnız süper kullanıcı yetkileri (COPY PROGRAM,
  dosya, rol/DB yönetimi) gider. RLS politikaları ve pvq_app değişmedi. `docker-compose.yml`: api + worker `PVQ_DB_URL` → pvq_api
  (`API_DB_PASSWORD`), worker'a yalnız gece pg_dump için `PVQ_DB_ADMIN_URL` (pvquant); api'de yönetici URL'si YOK. Worker `gece_yedek`
  yönetici URL'sini tercih eder. CI: alembic pvquant ile, `pytest` **pvq_api** ile koşar (ALTER ROLE adımı). Test `tests/test_db_rolu.py`
  (rol bayrakları, üyelik, tüm tablo/dizi yetkileri; pvq_api ile: current_user, COPY PROGRAM ve CREATE ROLE reddi, kiracı bağlamında
  pvq_app). Yerel: taze timescale'de head `v2488_db_rolu`, rol+RLS+platform+güvenlik testleri ve TAM TAKIM pvq_api ile geçti (**706 passed**, 0 hata).
  **Dağıtım (mühürde):** (1) `.env`'e `API_DB_PASSWORD=$(openssl rand -hex 24)`; (2) `git pull`; (3) alembic yönetici ile:
  `set -a; . ./.env; docker compose run --rm --no-deps -T -e PVQ_DB_URL=postgresql+psycopg://pvquant:$DB_PASSWORD@db:5432/pvquant api
  alembic upgrade head`; (4) `docker compose exec -T db psql -U pvquant -d pvquant -c "ALTER ROLE pvq_api PASSWORD '$API_DB_PASSWORD'"`;
  (5) `docker compose build -q api worker && docker compose up -d --force-recreate api worker`; (6) kanıt: api konteynerinde
  `SELECT current_user, rolsuper` → pvq_api/false; `/v1/healthz`, giriş, Sistem sayfası; worker nabzı; gece yedeği bir sonraki
  01:15 UTC'de (ya da `acilis_yedek` 24 sa kuralı) yönetici URL'siyle.

## Tablo turu O1+O2+O3 (+O5) — CANLI v2.489 (5785b94, CI #587)
Sunucu 25.10: pull → api + worker + web imajları → recreate (geçiş yok). Canlı index.html + 19/19 JS/CSS referans derlemeyle birebir;
`/yonetim` 200, `/v1/healthz` ok; worker nabzı 24 sn; `denetim_service.listele` canlı kayıtlarda kiracı adını döndürüyor (`giris` →
«Deneme Lab»); api/worker log 0 hata. Gerçek hesapla Denetim/Genel bakış görünümü kullanıcıda.
- **O1:** `denetim_service.listele` kiracı adını birleştirir (`kiraci_ad`, EK alan); Denetim/Genel bakış tablosunda Ayrıntı ham JSON yerine
  `anahtar: değer` çipleri (`AyrintiCipleri`, iç nesneler `eski.status` gibi düzleşir, uzun değer kısaltılır + başlıkta tamamı), Kiracı sütunu ad,
  Nesne «tür / id» iki satır, IP mono, Ayrıntı son sütun; Denetim süzgecinde kiracı SEÇİMİ (uuid girdisi kalktı); eylem çipi satır taban
  çizgisinde.
- **O2:** `:root[data-yuz="platform"]` kapsamlı CSS: platform tablolarında tüm sütunlar sola yaslı içerik genişliğinde, son sütun kalanı alır
  (ilk sütun artık boşluğu yutmuyor). Müşteri paneli tablo kuralları dokunulmadı (web testi pinler).
- **O3:** `features/yonetim/ortak.tsx` `Zaman` bileşeni (`.zaman` mono tabular nowrap; `sar` ile dar hücrede kırılır) — sayfalar/Sistem/Kullanım
  16 hücre tek tipografi; şablon dizelerindeki `${zamanTr}` metinler aynen.
- **O5:** worker zamanlayıcısı ve tam turda `gece_meteo` / `gece_piyasa` `_logla_tek` ile TEK satır (iş gövdeleri değişmedi; «bugün çekildi»
  bayrakları zaten vardı).
- Kanıt: tsc 0 · web test 90/90 · build 0 · oxlint 16 · API testleri 10/10 · DB testleri (kiracı adı) taze timescale'de 4/4. Kareler (sahte API,
  Chrome): **1920 ve 1440'ta beş sayfada belge taşması 0, hiçbir kaydırma alanında iç taşma yok** (önce Denetim/Genel bakış 91 px, meteo 21 px);
  375'te belge taşması 0, tablolar kart içinde kayar (tasarım kuralı); konsol 0. Ders: `{zamanTr(` regex'i şablon dizelerindeki `${zamanTr(`'i de
  yakaladı → iki yer elle geri alındı, test pini `[^$]\{zamanTr\(`.

## Sorunsuz bulunanlar
- **Kapsam ayrımı ve yetki:** platform jetonu müşteri uçlarında 403, müşteri jetonu `/v1/yonetim` uçlarında 403; başlıksız 422; bozuk
  jeton 401; oturum sürümü (sv) ve aktiflik 60 sn önbellekle her istekte; sahip-only uçlar; son etkin sahip düşürülemez.
- **Girdi güvenliği:** tüm sorgular parametreli (`kullanici_ara` ILIKE `:qq`), e-posta lowercase; sırlar (parola, davet jetonu, TOTP
  secret) denetim izine yazılmıyor; giriş hataları ayrıntısız (varlık sızdırmaz); 5/dk giriş sınırı; Caddy HSTS/nosniff/DENY/frame-ancestors.
- **Veri doğruluğu (ekranlarla çapraz):** Kiracı 2, etkin santral 5 (328.732 kWp), kullanıcı 2; Deneme Lab Ekim koşu 380, SCADA 1.694
  saat, yükleme 75 — kullanım özeti sunucudaki salt okunur sorguyla aynı; nabız 5 dk; gece turu taze; yedek 59 dk; iş kayıtları 145/0 hata.
- **Müşteri paneliyle bağ:** ayrı jeton anahtarı (`pvq_platform_token`), 401 işleyicileri birbirini düşürmüyor; müşteri `Isler` tipi hata
  ayrıntısı taşımıyor; müşteri istemcisi `/v1/yonetim` bilmiyor; koyu + lacivert yüz yanlış pencereyi ilk bakışta ayırt ettiriyor.
- **Hız:** Yonetim parçası 47,6 kB (gzip 11,9 kB) tembel; sayfalar 1–4 küçük GET; canlıda geçişler anlık (ekranlarda iskelet yok).
  Müşteri panelindeki bayat-önce önbelleği yok — bu kullanım için gerekmiyor.
- **Tipografi/ritim:** Inter Tight başlıklar, 15 px gövde, kart/KPI dili müşteri paneliyle bir; boş durumlar («Henüz başvuru yok.»)
  ve açıklama satırları dürüst («Plan sınırı yok, yalnız ölçüm»).

## Önerilen sıra
1. Y2 (küçük, bir dependency) → 2. Y1 (göç + rol; Faz 5 öncesi) → 3. O1+O2+O3 tek «platform tablo turu» (yalnız `.plat-*` CSS +
Denetim ayrıntı bileşeni + kiracı adı birleştirme) → 4. O5, O4 teyidi → 5. O6, O8 → 6. D'ler Faz 5 ile.
