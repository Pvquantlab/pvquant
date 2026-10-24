# Faz 0 — Güvenlik tabanı (24.10.2026) — CANLI v2.479
**Durum:** v2.479 = 4944f2a + düzeltme 1c67542 (24.10; v2.478 numarası PR #12 «açık tema panel geçişleri» ile dolu olduğundan
yeniden numaralandı, migration `v2479_faz0_guvenlik`). CI #568 kırmızı (yeni RLS testinde `pytest.raises` bağlam içindeydi +
`'{"v":1}'` literal'i text() bağ parametresi sanıldı) → düzeltme CI #569 yeşil; yerelde CI ile aynı timescale imajıyla 690/690.
Dağıtım: `.env` PVQ_PLATFORM_TENANT_ID (Meridyen Enerji), api+web imajı, `alembic upgrade head` → `v2479_faz0_guvenlik (head)`,
api yeni komutla (`--proxy-headers --forwarded-allow-ips *`; loglarda gerçek istemci IP'si görünüyor), web yeniden oluşturuldu,
Caddy **yeniden oluşturuldu** (reload «config is unchanged» dedi: tek dosya bind-mount, `git pull` yeni inode yazınca konteyner
eski dosyayı görüyordu — ders emsaller.md'de). Canlı: index.html + 18/18 JS/CSS referansla birebir; başlıklar `/`'da HSTS,
nosniff, X-Frame-Options DENY, CSP frame-ancestors, Referrer-Policy, Permissions-Policy, `Server` yok; `/v1/*`'da da aynı;
www → apex 301; sahte jeton 401, jetonsuz başvurular 401, yanlış parola 401; api logunda hata 0. Worker konteyneri eski imajda
(Faz 0 kodu worker'a dokunmaz; bir sonraki gece işi/dağıtımda yenilenir). Panelden gerçek hesapla pasifleştirme ≤60 sn düşme
denemesi kullanıcıda.

Dayanak: `docs/YONETICI-PANELI-YOL-HARITASI-2026-10-24.md` §1 (seçenek C). Kapsam kullanıcı talimatı: başvuru kilidi,
report_* RLS, oturum_surumu jeton iptali, kiracı status, proxy IP + güvenlik başlıkları. Yalnız EKLEME: mevcut uç
sözleşmeleri, hesap servisleri, tahmin/kalibrasyon ve mevcut RLS politikaları değişmedi.

## NE
1. **Vitrin başvuru kilidi** — `apps/api/deps.py` `platform_kiracisi()`: `yonetici_yetkisi` üstüne `claims.tenant_id ==
   PVQ_PLATFORM_TENANT_ID`; değişken boşsa KİMSE. `GET /v1/vitrin/basvurular` ve `POST …/{id}/okundu` bu kapıya alındı
   (`apps/api/main.py`). `docker-compose.yml` api ortamına `PVQ_PLATFORM_TENANT_ID: ${PVQ_PLATFORM_TENANT_ID:-}`.
   Panel: `GelenTalepler` 403'te boş liste → kart çizilmez (mevcut `catch`), UI değişikliği gerekmedi.
2. **report_stats / report_log RLS** — `alembic/versions/v2479_faz0_guvenlik.py`: ENABLE + FORCE + `p_<tablo>`
   USING/WITH CHECK `tenant_id = app.tenant_id` (v2.264 kalıbı). Yazanlar zaten `tenant_baglami` (worker `report_stats`,
   `report_service.rapor_id_uret` `report_log`); GRANT'lar v2.103'te vardı → davranış aynı, sızıntı kapısı kapandı.
3. **Jeton iptali** — aynı migration `users.oturum_surumu INTEGER NOT NULL DEFAULT 0`. `auth_service`: JWT'ye `sv`;
   `oturum_durumu(user_id)` (sürüm + aktif + kiracı durumu, süreç içi 60 sn önbellek), `oturum_surumu_artir(s, uid)`
   (rol/durum değişimi `kullanici_guncelle`, `parola_degistir`, `parola_sifirla`), `iki_adim_service.yonetici_sifirla`
   da artırır. `deps.gecerli_kullanici`: imza + süreden sonra DB kıyası — sürüm uyuşmazlığı 401 «oturum geçersiz;
   yeniden giriş yapın», pasif 401, askıdaki kiracı 403. `sv` iddiası olmayan eski jeton 0 sayılır → sürümü hiç
   artmamış kullanıcıda geçerli (dağıtımda kimse düşmez).
4. **Kiracı status** — `giris` ve `oturum_yenile` `tenants.status` okur; `active` değilse `KiraciAskida` → uç 403
   «hesap askıda» (parola yanlışsa yine 401 «hatali»: hesap varlığı sızdırılmaz). Her istekte de `gecerli_kullanici`
   üzerinden 403.
5. **Proxy IP + başlıklar** — `docker-compose.yml` api: `--proxy-headers --forwarded-allow-ips *` (api'ye yalnız Caddy ve
   sunucu loopback'i ulaşır: port 127.0.0.1:8000). `Caddyfile` site bloğu: HSTS 1 yıl + includeSubDomains, nosniff,
   X-Frame-Options DENY, CSP `frame-ancestors 'none'` (script-src için satır içi tema betiği nonce/hash ister — ayrı iş),
   Referrer-Policy strict-origin-when-cross-origin, Permissions-Policy (kamera/mikrofon/konum kapalı), `-Server`.

## NEDEN
Yönetici paneli (platform kimliği) bu beş eksiğin üstüne kurulamazdı: satış adayları her kiracıya açıktı; iki rapor
tablosu politikasızdı; pasifleştirme/rol/parola değişimi 12 saate kadar jetonu düşürmüyordu; askıdaki kiracı giriyordu;
giriş hız sınırı Caddy IP'sine kilitliydi ve tarayıcı güvenlik başlıkları yoktu (analiz: `docs/MIMARI-PANEL-AYRIMI-2026-10-24.md`).

## KANIT
- Yeni test `tests/test_faz0_guvenlik.py` (5 test, DB'siz): başvuru kapısı (değişken yok → 403, başka kiracı → 403,
  platform kiracısı admin → 200, editor → 403); `gecerli_kullanici` sürüm/pasif/askı/kullanıcı yok dalları; önbellek
  tek sorgu + düşürme; askıda giriş/tazeleme 403; migration metni ve artırma noktaları.
- `tests/test_rls_izolasyon.py::test_rapor_tablolari_rls` (DB'li, CI'da koşar): A'nın `report_stats` satırı B'de görünmez,
  B bağlamından A adına yazılamaz.
- `tests/test_iki_adim.py` sahte satırlarına iki yeni sütun eklendi (giriş sorgusu değişti).
- Yerel: pytest **686 geçti**, 4 RLS testi DB yokken (yerel docker kapalı) atlandı → CI'da `alembic upgrade head` +
  timescale servisiyle koşar. `docker-compose.yml` `yaml.safe_load` OK. Caddyfile sunucuda `caddy:2.11.7 caddy validate`
  → «Valid configuration» (uygulanmadı). `alembic heads` tek baş: `v2479_faz0_guvenlik`.
- Web: değişiklik yok (tsc/test/build önceki mühürden).

## DAĞITIM NOTLARI (mühürde)
1. `.env`'e `PVQ_PLATFORM_TENANT_ID=19bf0a66-39dc-42e5-a9bb-269466de3f7a` — **karar 24.10: platform kiracısı Meridyen
   Enerji** (Deneme Lab yöneticisi artık başvuruları görmez). Boş bırakılsaydı kimseye görünmezdi; e-posta bildirimi
   `PVQ_BILDIRIM_EPOSTA` ile sürer.
2. `docker compose exec api python -m alembic upgrade head` (yeni sütun + iki politika; geri alma `downgrade` var).
3. `docker compose up -d` (api komutu değişti → yeniden oluşur) + `docker compose exec caddy caddy reload --config
   /etc/caddy/Caddyfile` ya da caddy'yi yeniden başlat (Caddyfile bağlı birim).
4. Canlı doğrulama: `curl -I https://pvquant.com/` başlıklar; yanlış `sv` ile 401; panelde pasifleştirilen üyenin
   ≤60 sn içinde girişe düşmesi; başvuru kartı yalnız platform kiracısında.

## KALAN (Faz 0 dışı, yol haritasında)
`healthz` DB kontrolü ve `PVQ_JWT_SECRET` yokken başlamama (küçük, istenirse eklenir); askıdaki kiracı için panelde
anlamlı mesaj (bugün 403 → sayfa hatası, Faz 1 UI); CSP script-src; süper kullanıcı DB bağlantısı (Faz 1).
