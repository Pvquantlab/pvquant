# Sahip onayı (OAuth) — platform uygulama kaydı ve işletim (v2.564, 10.11.2026)

Sungrow iSolarCloud ve SolarEdge (site sahibi) için santral sahibi kimlik bilgisini PVQuant'a yazmaz; sağlayıcının kendi sayfasında PVQuant uygulamasını
onaylar, belirteçler sunucuda zarf şifreli saklanır ve yenilenir. Bunun için PVQuant'ın her sağlayıcıda **bir kez** platform uygulaması kaydettirmesi gerekir
(dış girdi D4/D5). Kayıt yapılmadan yol kapalıdır: ekran «platform uygulaması tanımlı değil» der, sahte başarı yoktur.

## Akış (kod: `services/bulut_oauth_service.py`, uçlar `apps/api/main.py`)

1. Sahip Santralim › Veri kaynakları'nda sağlayıcıyı seçer, iki onayı işaretler («yalnızca veri okunmasını onaylıyorum», «şifreli saklama») → «Sahip onayına git».
2. `POST /v1/plants/{id}/bulut-kimlik/oauth/baslat` → tek kullanımlık rastgele `state` (tabloda yalnız SHA-256 özeti; santral, sağlayıcı, bölge, onaylar; 15 dk)
   ve sağlayıcının onay adresi. Tarayıcı o adrese gider.
3. Sahip onaylar → sağlayıcı `GET /v1/bulut/oauth/{saglayici}/geri-donus?code=…&state=…` (SolarEdge: `code`, `site_id`, `external_id`=state) adresine yönlendirir.
4. Sunucu state'i atomik olarak «kullanıldı» işaretler (yeniden oynatma kazanamaz), kodu belirteçle değiştirir (istemci gizli anahtarı yalnız ortamda), sağlayıcı
   santral listesini okur ve belirteçleri `bulut_kimlik`'e zarf şifreli yazar. Birden çok santral varsa kayıt santral kodu boş yazılır; sahip panelden seçer.
5. Tarayıcı panele döner: `/?bulut_oauth=<sağlayıcı>:<durum>#santralim/<santral>` — yalnız durum KODU taşınır; ekran koddan Türkçe üretir.
   Durum kodları: tamam · secim_bekliyor · durum_gecersiz · durum_yok · sahip_reddetti · saglayici_hatasi · kod_yok · uygulama_yok · belirtec_hatasi · kayit_hatasi.
6. Düzenli çekiş ve «birim doğrulandı» ayrı adımlar (v2.557 ile aynı). Belirteç yenileme: Sungrow `refreshToken` (−2 → yeniden onay), SolarEdge 401'de
   `/v2/oauth2/token` refresh (yeni çift atomik yazılır).

Yetkilendirme kodu, belirteçler ve gizli anahtarlar hiçbir günlük, denetim izi, yanıt ya da `bulut_oauth_durum.sonuc` özetine yazılmaz (testler: `tests/test_bulut_oauth_v2564.py`,
`tests/test_bulut_oauth_db_v2564.py`). Geri dönüş kökü ortamdan gelir (istekten alınmaz; açık yönlendirme yüzeyi yok).

## Kayıt adımları (siz)

**Geri dönüş adresi (her iki portalda «redirect URL / Allowed Redirect URI» alanına):**
`https://pvquant.com/v1/bulut/oauth/sungrow/geri-donus` ve `https://pvquant.com/v1/bulut/oauth/solaredge_oauth/geri-donus`.

| Sağlayıcı | Portal | Alınan değerler | Ortam değişkeni |
|---|---|---|---|
| Sungrow | iSolarCloud geliştirici portalı (A: `developer-api.isolarcloud.com`; B: `.com.hk`) → hesap → uygulama başvurusu (ad «PVQuant», simge, redirect URL) → onay | AppKey · Secret Key (`x-access-key`) · applicationId (onay adresindeki `applicationId`) | `PVQ_SUNGROW_APPKEY` · `PVQ_SUNGROW_ACCESS_KEY` · `PVQ_SUNGROW_APP_ID` |
| SolarEdge | developer.solaredge.com → uygulama (OAuth site erişimi; kapsam `SITE_DATA`, erişim türü sonradan değişmez; Allowed Redirect URI) | Client ID · Client Secret | `PVQ_SOLAREDGE_CLIENT_ID` · `PVQ_SOLAREDGE_CLIENT_SECRET` |
| Ortak | — | panel kökü | `PVQ_OAUTH_GERI_DONUS_KOK` (varsayılan `https://pvquant.com`) |

Sungrow ticari kullanım onayı (VIII(c)) kayıttan ayrı yazılı talep (BASVURU-METINLERI §3). Türkiye'nin Sungrow bölgesi (intl/eu) doğrulanmadı; sahip bölgeyi ekranda seçer.

## Sunucuda tanımlama (mühürde)

`.env`'e değerler eklenir (depoya girmez; `.env.example` alan adlarını listeler), `docker compose up -d api worker` (api: başlatma/geri dönüş; worker: belirteç yenileme).
Doğrulama: `GET /v1/plants/{id}/bulut-kimlik` → `oauth.uygulamalar.<sağlayıcı>.yapilandirildi: true`, `eksik: []` (değerler dönmez).
Secret döndürme: portalda yeni gizli → `.env` → compose yeniden; SolarEdge'de eski secret ile alınmış erişim belirteçleri ~2 saat çalışır, yenileme yalnız yeni secret ile.

## Doğrulanmamış varsayımlar (ilk gerçek kayıtla kapanır)

- Sungrow onay adresi kalıbı ve `cloudId` eşlemesi yalnız ikincil kaynakta [K366]; `x-access-key`'in portaldaki hangi alan olduğu birincil belgede yazmıyor.
- SolarEdge yetkilendirme adresinde `redirect_uri`/`state` parametresi belgede yok; `state` `external_id` ile taşınıyor — portal bunu geri dönüşte aynen vermezse akış «durum_yok» ile durur.
- Her iki sağlayıcıda da geri dönüşün tam sorgu biçimi gerçek hesapla görülmedi.
