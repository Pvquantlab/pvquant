# PVQuant — Yönetici paneli stratejisi ve yol haritası (24.10.2026)

Dayanak: `docs/MIMARI-PANEL-AYRIMI-2026-10-24.md` (kod okuması, HEAD 46f5a69). Bu belge karar ve sıralama içindir; kod değişikliği yok.
Teyitler: canlı `.env`'de `PVQ_SMTP_*`, `PVQ_BILDIRIM_EPOSTA`, `PVQ_JWT_SECRET` anahtarları tanımlı (değerlere bakılmadı) → davet
e-postası için posta altyapısı mevcut (`posta_service.gonder`, `PVQ_SMTP_HOST` ile açılır). İki kiracı, tek sunucu, 4 API işçisi.

## 1. Önce güvenlik mi, yönetici paneli mi?

Soru ikili değil; doğru cevap **«güvenlikten yalnız yönetici panelinin ÜSTÜNE kurulacağı taban kadarını önce, gerisini panelle
birlikte»**. Üç seçenek karşılaştırıldı:

| Seçenek | Avantaj | Risk | Bağımlılık |
|---|---|---|---|
| A. Önce tam sertleştirme (10 madde), sonra panel | En temiz taban | 2–3 mühür boyunca görünür ürün yok; bazı maddeler (sır şifreleme, TOTP tekrar koruması, SSRF süzgeci) panelle ilgisiz, erteleyince de risk artmaz | Yok |
| B. Önce panel, güvenlik sonra | Hızlı görünür çıktı | Panel «platform» kimliğini mevcut zayıf jeton modeline (iptal yok, kiracı durumu yok, süper kullanıcı bağlantısı) bindirir; en yetkili kimlik en zayıf halkaya oturur; sonradan düzeltmek panelin kimlik akışını yeniden yazdırır | — |
| **C. Taban sertleştirme (5 madde) + panel kimliği aynı mühürde, kalan sertleştirme panel fazlarına dağıtılır** | Platform kimliği doğru tabana oturur; 1 mühür sonra ilk yönetici ekranı; geri kalan güvenlik işleri ait oldukları ekranla gelir (denetim izi ↔ Denetim sayfası) | Mühür büyür (şema + API + UI); disiplinle tutulur | Posta (var), ortam değişkeni (Caddy ağı) |

**Öneri: C.** Zorunlu taban (panelden önce, kapatılmadan panel açılmaz):
1. Vitrin başvurularını kiracı yöneticisinden çek (platform kapsamına taşınana dek geçici `PVQ_PLATFORM_TENANT_ID` kilidi). *Veri sızıntısı — tek acil madde.*
2. `report_stats`/`report_log` RLS politikaları (tek migration; mevcut kalıbın kopyası).
3. Jeton iptali: `users.oturum_surumu` + JWT `sv` + `gecerli_kullanici`'da kıyas (60 sn önbellek). *Platform rolü iptal edilemeyen jetonla var olamaz.*
4. Kiracı `status` girişte ve tazelemede (askıdaki kiracı 403). *Müşteri yönetimi ekranının «askıya al» düğmesi bunsuz yalandır.*
5. Proxy arkasında gerçek IP (`--proxy-headers --forwarded-allow-ips`) + Caddy güvenlik başlıkları (HSTS, nosniff, frame-ancestors, Referrer-Policy). *Yarım gün, panelden bağımsız, kalan tüm sınırlayıcıların ön koşulu.*

Panelle birlikte gelecekler: genel denetim izi (Faz 1, Denetim sayfası), uygulama DB kullanıcısının süper kullanıcıdan indirilmesi
(Faz 1, platform bağlamı tanımlanırken), paylaşımlı hız sınırı sayacı (Faz 3, kullanım sayaçlarıyla aynı tablo), davet e-postası +
ilk girişte parola değişimi (Faz 1, kiracı oluşturma ucu).
Sonraya bırakılabilir (risk düşük, panelle ilgisiz): TOTP/webhook sırlarının şifrelenmesi, TOTP tekrar koruması, webhook SSRF süzgeci,
`/v1/kullanicilar` daraltma, eski kimliksiz uygulamanın (`src/pvquant/api/main.py`) depodan silinmesi, JWT'nin localStorage'dan
httpOnly çereze taşınması (ayrı tasarım: CSRF gerekir; bugünkü tehdit modelinde XSS yüzeyi küçük, üçüncü taraf betik yok).

## 2. Yönetici paneli için önceden hazır olması gerekenler

| Altyapı | Durum | Gerek |
|---|---|---|
| Platform kimliği (ayrı kullanıcı tablosu, 2FA zorunlu, kısa ömürlü jeton, `kapsam` iddiası) | Yok | Zorunlu, Faz 1 |
| Jeton iptali (`oturum_surumu`) | Yok | Zorunlu, taban |
| Kiracı durumu zorlaması | Yok | Zorunlu, taban |
| Denetim izi tablosu + yazım noktaları | Yalnız paylaşım | Zorunlu, Faz 1 (platform her eylemi iz bırakır) |
| Kiracı verisine platform erişim kapısı (`platform_baglami`: adlı, denetimli; okuma yine `tenant_baglami` ile) | `sistem_baglami` her yerde, denetimsiz | Zorunlu, Faz 1 |
| Uygulama DB rolü süper kullanıcı değil | Süper kullanıcı | Faz 1 ile (platform kapısı tanımlanırken) |
| Posta (davet, parola sıfırlama) | Var, canlıda tanımlı | Hazır |
| Kabuk iskeletinin santraldan ayrılması (`KabukIskeleti` + müşteri/platform varyantı) | Sıkı bağlı | Faz 2 (UI), müşteri yüzü piksel-birebir korunarak |
| İş sağlığı sinyali (worker nabzı `jobs_log`'a) | Yalnız iş kayıtları | Faz 3 |
| Kullanım sayaçları (`api_kullanim`) | Yalnız `last_used_at` | Faz 3 |
| Plan/limit şeması | `tenants.plan` metin, okunmuyor | Faz 4 |

## 3. Roller nasıl ayrılmalı

İki **kapsam**, kapsam içinde roller; kapsamlar jeton düzeyinde ayrı ve birbirini reddeder:

- **Platform kapsamı** (`platform_kullanicilar`, kiracıya bağlı değil): `sahip` (her şey + kimliğe bürünme + plan tanımı) ve
  `operator` (müşteri/kullanıcı/sistem izleme, kimliğe bürünme yok ya da yalnız salt okunur). 2FA zorunlu, jeton ≤ 4 saat,
  ayrı giriş ucu, IP/oturum kaydı. Kiracı verisini yalnız kiracı kimliği belirtilmiş `tenant_baglami` ile okur → RLS devrede.
- **Müşteri kapsamı** (`users`, mevcut): `admin` (kuruluş yöneticisi: ekip, anahtar, webhook, paylaşım, arşiv, ayarlar),
  `editor` (santral ayarları, veri, koşu), `viewer` (okuma). Rol kümesi ve API sözleşmesi değişmez; UI yalnız rolün yapabileceğini çizer.
- Kimliğe bürünme: platform `sahip` → 15 dk, `kapsam:musteri`, `role:viewer`, `temsil:{platform_sub}`; yazma uçları `temsil`'i reddeder;
  denetim izine yazılır; panelde kalıcı şerit. Müşteri sözleşmesine madde eklenmeli.
- İleride (Faz 5 sonrası): kiracı içinde santral bazlı yetki (`plant_groups`/`user_groups` zaten şemada) — büyük portföy müşterileri isteyince.

Reddedilen alternatifler: `users.tenant_id NULL` ile «süper admin» (RLS kalıbı ve «her kullanıcı bir kiracının» varsayımı bozulur,
tek tabloda iki tehdit modeli); müşteri `admin`'ine platform yetkisi vermek (bugünkü vitrin sızıntısının genelleşmesi).

## 4. Geliştirme sırası (bağımlılıklara göre)

1. **Güvenlik tabanı** (§1'deki 5 madde) — her şeyin önü.
2. **Müşteri yönetimi** — platform kimliği + kiracı/kullanıcı CRUD + başvurular + denetim izi. Komut satırı işlerini bitirir; en çok zaman kazandıran.
3. **Sistem izleme** — işler, worker nabzı, meteo/piyasa tazeliği, yedek yaşı, santral envanteri sorun süzgeci. Veri zaten var (`jobs_log`, `meteo_arsiv`, dosyalar); çoğunlukla okuma ucu + ekran.
4. **Kullanım limitleri (uyarı kipi)** — sayaçlar + plan tablosu, önce yalnız rozet; müşteri davranışını kırmaz.
5. **Abonelik** — plan zorlaması ve ödeme entegrasyonu. En son: ödeme sağlayıcısı (iyzico/Stripe) seçimi ve sözleşme süreci ürün kararı; teknik olarak Faz 4 tablosuna webhook yazar.

Neden abonelik sonda: iki kiracıyla ödeme otomasyonunun getirisi yok; yanlış kurgulanmış limit müşteri paneli için en görünür regresyon riski.

## 5. Tek uygulamada rol bazlı mı, ayrı yönetici uygulaması mı?

| | Tek uygulama, kapsam tabanlı (`/yonetim`) | Ayrı yönetici uygulaması (ayrı SPA + ayrı API süreci) |
|---|---|---|
| Güvenlik | Kapsamlar jeton düzeyinde ayrı; aynı süreç ama ayrı bağımlılık (`platform_yetkisi`); saldırı yüzeyi API'de zaten var | Süreç/ağ ayrımı daha güçlü; ama kiracı verisine erişim yine aynı DB'den, aynı RLS/`sistem_baglami` sorunlarıyla |
| Maliyet | Tasarım sistemi, istemci, giriş/2FA, RLS, CI/dağıtım yeniden kullanılır; 1 geliştirme hattı | İkinci derleme, dağıtım, imaj, Caddy bloğu, test takımı; tasarım dili ikiye ayrılma eğilimi |
| Risk müşteri paneline | Kabuk refactor'u ortak kodu etkiler (piksel-birebir bekçiyle yönetilir) | Sıfır UI riski; ama API tarafı yine ortak |
| Ölçek | 2 kiracı, tek sunucu için fazlasıyla yeterli | Çok operatörlü ekip, ayrı güvenlik bölgesi istendiğinde |

**Karar: tek uygulama, kapsam tabanlı.** Ayrı süreç kazanımının büyük kısmı (jeton ayrımı, ayrı giriş, 2FA zorunluluğu,
denetim) tek uygulamada da alınır. İleride ayrı alan adı (`yonetim.pvquant.com`) Caddy'de ikinci blok + SPA'da host kontrolüyle
eklenir; ayrı süreç yalnız ekip ve tehdit modeli büyürse. Geri dönülmez karar değildir: `/v1/yonetim/*` uçları ve platform
tabloları tek modülde tutulursa sonradan ayrı servise taşınabilir.

## 6. En düşük riskli yol haritası

Kurallar: her faz yalnız EKLER (yeni tablo/sütun/uç/yol); mevcut `/v1/*` yanıt şekilleri, `/v1/dis/*`, tahmin/kalibrasyon/hesap
servisleri, SCADA işleme, mevcut RLS politikaları ve kiracı rol kümesi değişmez. Her faz kendi mührü: pytest + RLS izolasyon
testi (+ «platform jetonu kiracı ucunu açamaz» eklenir) + web kapıları (tsc/test/build/oxlint) + örnek kip üç motor karesi +
canlı sha ve canlı doğrulama. Müşteri yüzü değişen fazlarda kare.mjs/pngfark ile piksel-birebir bekçi.

| Faz | İçerik | Zorunlu mu | Bağımlılık | Müşteri paneline etki |
|---|---|---|---|---|
| **0 Taban** | Başvuru kilidi (env), report_* RLS, `oturum_surumu` + `sv`, kiracı status, proxy IP + güvenlik başlıkları, `healthz` DB, `PVQ_JWT_SECRET` yoksa başlamama | **Zorunlu** | Yok | Yalnız başvuru kartı platform kiracısı dışında kaybolur |
| **1 Platform kimliği + müşteri yönetimi** | `platform_kullanicilar`, `denetim_izi`, `platform_baglami`, DB rolü süper kullanıcıdan indirme, `/v1/yonetim/{giris,oturum,kiracilar,kullanicilar,basvurular,denetim}`, kiracı oluşturma + davet e-postası + ilk giriş parola değişimi, vitrin başvurularının platforma taşınması; SPA `/yonetim` ilk 4 sayfa (Genel bakış, Müşteriler, Kullanıcılar, Başvurular) ve `PlatformKabugu` | **Zorunlu** | Faz 0 | Kabuk iskeleti ayrılır; müşteri yüzü piksel-birebir bekçiyle |
| **2 Sistem izleme** | `jobs_log` kiracılar arası + hata ayrıntısı, worker nabzı, meteo/piyasa tazeliği, yedek yaşı, santral envanteri + sorun süzgeci; Hakkında arşiv tablosu ve gece işleri ayrıntısı müşteriden platforma | Zorunlu (işletme için) | Faz 1 | Hakkında/Veri yükleme iki kart sadeleşir |
| **3 Kullanım + sınırlayıcılar** | `api_kullanim` sayaçları (anahtar, webhook, rapor, koşu, SCADA satırı), paylaşımlı hız sınırı sayacı, Kullanım sayfası | Önerilir | Faz 1 | Yok |
| **4 Planlar (uyarı kipi) + kimliğe bürünme** | `planlar` tablosu, `tenants.plan` FK, limit rozetleri (zorlamasız), salt okunur görüntüleme (izli, 15 dk) | Ertelenebilir | Faz 3 | Rozet; yazma yok |
| **5 Müşteri paneli düzeni** | «Kuruluş ayarları» sayfası, Portföy sade analitik, viewer'dan yazma kontrolleri gizlenir, kiracı içi denetim izi | Ertelenebilir | Faz 1 | Portföy ve kabuk navigasyonu değişir (tasarım turu) |
| **6 Abonelik zorlaması + ödeme** | Limit zorlaması, ödeme sağlayıcı webhook'u | Ürün kararı sonrası | Faz 4 | Limit aşımında kısıt |
| Sonraya | Sır şifreleme, TOTP tekrar koruması, SSRF süzgeci, httpOnly çerez, eski uygulamanın silinmesi, `plant_groups` yetkisi | Ertelenebilir | — | — |

Kritik yol: **Faz 0 → Faz 1** (ilk yönetici ekranı). Faz 0 tek mühür; Faz 1 iki mühür (API+şema, sonra SPA) önerilir ki kimlik
katmanı UI'dan bağımsız test edilsin.

## 7. Karar bekleyenler
1. Yönetici girişi `/yonetim` mi, `yonetim.pvquant.com` mi (teknik fark: Caddy bloğu + SPA host kontrolü; öneri: `/yonetim` ile başla).
2. Kimliğe bürünme olsun mu (öneri: Faz 4'te, salt okunur, izli, sözleşmede açık).
3. Faz 0 başvuru kilidi için «platform kiracısı» hangisi (Meridyen Enerji?).
4. Platform kullanıcıları başlangıçta kaç kişi, rolleri (`sahip`/`operator`).
5. Plan adları ve ilk uyarı eşikleri (santral, kullanıcı, API rpm, aylık rapor).

Durum: belge commit edilmedi (biriktirme kuralı); kod değişikliği yok.
