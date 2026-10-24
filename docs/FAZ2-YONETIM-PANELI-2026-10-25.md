# Faz 2 — Yönetici paneli arayüzü `/yonetim` (25.10.2026) — BİRİKTİ, commit bekliyor

Dayanak: `docs/YONETICI-PANELI-YOL-HARITASI-2026-10-24.md` Faz 2; Faz 1 API'si (v2.480) üstüne. Müşteri paneli, tahmin
sistemi ve `/v1/*` müşteri sözleşmeleri değişmedi; tek istisna yol haritasında kararlaştırılan temizlik: vitrin başvurularının
müşteri uçları ve Faz 0 geçici env kilidi kalktı.

## NE
1. **İstemci** `web/src/api/yonetim.ts`: `/v1/yonetim/*` için ayrı istemci; jeton anahtarı `pvq_platform_token` (müşteri
   `pvq_token`'ına dokunmaz, 401 yalnız platform oturumunu düşürür); tüm uçlar tiplenmiş; `zamanTr`.
2. **Giriş + zorunlu 2FA** `features/yonetim/PlatformGiris.tsx`: tek sütun, «Platform» rozeti, 2FA kod adımı; `IkiAdimKurulum`:
   jeton var ama TOTP kapalıysa kabuk AÇILMAZ — anahtar/otpauth adresi bir kez gösterilir, kod doğrulanınca panel.
3. **Kabuk** `features/yonetim/PlatformKabugu.tsx`: müşteri kabuğunun ızgarası ve sınıfları (`.kabuk/.yan/.ust/.nav-btn`, çekmece),
   santral seçici/alarm/telemetri YOK; yan menüde «PLATFORM · PVQuant personeli», üst çubukta «PLATFORM» rozeti; sayfa listesi
   `sayfaListesi.ts` (Operatörler yalnız sahip). Müşteri `Kabuk.tsx` dokunulmadı.
4. **Yüz** `Yonetim.tsx` kökte `data-tema=koyu` + `data-yuz=platform` (giriş ekranı dahil; ayrılırken eski değerler); `index.css`
   `:root[data-yuz="platform"]` vurgu jetonları nötr lacivert (#5B8DEF / #9DBBFF) — marka yeşili müşteriye kalır, yanlış pencere
   riski ilk bakışta ayırt edilir. Yeni sınıflar: `.plat-rozet`, `.plat-ust-rozet`, `.plat-yan-rozet`, `.plat-giris-marka`,
   `.plat-anahtar`, `.plat-tek-seferlik`, `.plat-cikis`, `textarea.girdi`; tablo içi `.cip-kod/.rozet` nowrap, `.dugme-sira` tek
   satır, `.grafik-kaydir > table` 620 px.
5. **Sayfalar** `features/yonetim/sayfalar.tsx`: Genel bakış (4 KPI + son 12 denetim kaydı), Müşteriler (tablo `table.veri.santral`,
   satır → detay; yeni kiracı formu `.form-izgara`, davet bağlantısı posta yoksa `TekSeferlik`), Müşteri detayı (askıya al/etkinleştir
   iki aşamalı onay, plan, notlar, kullanıcılar: parola bağlantısı / 2FA sıfırla / pasifleştir, santraller: son SCADA ve koşu),
   Kullanıcılar (kiracılar arası arama), Başvurular (okundu), Denetim izi (kapsam/eylem/kiracı süzgeci, «daha eski»), Operatörler
   (sahip: rol, pasifleştir, 2FA sıfırla, ekle → geçici parola bir kez), Hesabım (parola, 2FA durumu).
6. **Yol kapısı** `App.tsx`: `/yonetim` → tembel `Yonetim` parçası; müşteri paneli akışı aynı.
7. **Temizlik** `Portfoy.tsx` GelenTalepler kaldırıldı; `client.ts` başvuru uçları kaldırıldı; backend `apps/api/main.py`
   `/v1/vitrin/basvurular*` müşteri uçları ve `deps.platform_kiracisi` kaldırıldı, `docker-compose.yml` `PVQ_PLATFORM_TENANT_ID`
   kalktı, başvuru bildirim e-postası «pvquant.com/yonetim → Başvurular» der. Testler güncel.
8. **QA aracı** `betikler/sahte-api.mjs` `/v1/yonetim/*` sahte uçları (PLATFORM_2FA=1 → 2FA açık); kare betiği scratch.

## NEDEN
Faz 1 API'si vardı ama ekranı yoktu: ilk sahip 2FA'yı curl ile kurdu. Yönetim işleri (kiracı açma, askıya alma, parola/2FA
sıfırlama, başvurular, denetim) artık arayüzde; müşteri panelindeki platform sızıntısı (başvurular) ve geçici kilit kalktı.

## KANIT
- Kapılar: tsc 0 · web test **86/86** (yeni `test/panel/yonetim.test.ts`: yol kapısı, ayrı jeton anahtarı, GelenTalepler yok,
  koyu yüz + jeton, sahip-only, zorunlu 2FA pinleri) · build 0 · oxlint 16 (= main). Python: hedef testler 17/17
  (`test_faz0_guvenlik` başvuru testi 404'e, `test_api_vitrin_basvuru` liste testi 404'e güncellendi); tam takım (DB'siz, RLS + platform_db CI'da) **693 geçti**.
- Kareler (sahte API, Chrome kanalı, 1440 + 375 × 9 ekran): taşma 0, konsol/istisna 0. Yerleşik tarayıcıda giriş (koyu), genel
  bakış, müşteriler, detay, denetim, kullanıcılar gözle doğrulandı. Düzeltilenler: giriş ekranı açık temada geliyordu (yüz kökte
  uygulanır oldu), denetim tablosunda eylem çipi 1 % hücrede harf harf kırılıyordu (nowrap), işlem düğmeleri üst üste biniyordu.
- Canlı: henüz dağıtılmadı.

## DAĞITIM NOTLARI (mühürde)
web + api imajları; `docker compose up -d --force-recreate api web` (compose env satırı kalktı → api yeniden oluşur); Caddy
değişmedi. Canlı: `/yonetim` giriş (sahip@pvquant.com + 2FA), Müşteriler listesi gerçek iki kiracı, denetim izinde `giris`;
müşteri panelinde Portföy'de başvuru kartı yok; `/v1/vitrin/basvurular` 404.

## KALAN (Faz 3+)
Sistem durumu sayfası (işler, worker nabzı, meteo/piyasa tazeliği, yedek yaşı), kullanım sayaçları, plan/limit, kimliğe bürünme,
platform kurtarma kodları, askıdaki kiracıya müşteri panelinde anlamlı mesaj, Hakkında «meteo arşivi» tablosunun platforma taşınması.
