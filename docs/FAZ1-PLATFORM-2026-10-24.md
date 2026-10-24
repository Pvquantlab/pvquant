# Faz 1 — Platform kimliği ve müşteri yönetimi API'si (24.10.2026) — CANLI v2.480
**Durum:** v2.480 = 3860f0c (24.10), CI #571 yeşil. Sunucu: git pull, api + worker imajları, `alembic upgrade head` →
`v2480_faz1_platform (head)`, api ve worker yeniden oluşturuldu (worker v2.477'den beri eski imajdaydı; artık güncel).
Canlı: `POST /v1/yonetim/giris` yanlış parola → 401 ve `denetim_izi`'ne `platform/giris_basarisiz` satırı gerçek istemci IP'siyle;
sahte jeton `/v1/yonetim/ben` 401; müşteri ucu aynı; api/worker logunda hata 0. **İlk platform sahibi henüz açılmadı** (kullanıcı:
`docker compose exec -it api python scripts/platform_sahip.py <eposta>`, sonra `/v1/yonetim/giris` → `iki-adim/baslat` + `dogrula`).

Dayanak: `docs/YONETICI-PANELI-YOL-HARITASI-2026-10-24.md` §3–§6 (Faz 1, «önce API + şema»). UI yok (Faz 2). Yalnız EKLEME:
mevcut `/v1/*` sözleşmeleri, hesap servisleri, tahmin/kalibrasyon, mevcut RLS politikaları ve kiracı rol kümesi değişmedi.

## NE
1. **Şema** `alembic/versions/v2480_faz1_platform.py`: `platform_kullanicilar` (kiracıya bağlı değil; rol sahip|operator,
   TOTP, oturum_surumu, last_login), `denetim_izi` (kapsam platform|musteri, aktör, kiracı, eylem, nesne, ayrıntı jsonb, ip;
   zaman/kiracı indeksleri; RLS yok — sistem tablosu), `tenants.notlar`, `tenants.updated_at`. downgrade var.
2. **DB bağlamı** `src/pvquant/db.py` `platform_baglami(aktor_id)`: RLS dışı ama aktör ZORUNLU (`app.platform_aktor`) ve her uç
   denetim izine yazar; yalnız platform_service/yonetim kullanır.
3. **Servisler** `src/pvquant/services/platform_service.py`: giriş (bcrypt, TOTP açıksa kod şart; kapalıysa `iki_adim_kurulmali`),
   jeton `{sub, kapsam:"platform", rol, sv, exp 4 sa}`, `oturum_durumu` (60 sn önbellek) + sürüm artırma, oturum yenile, ben,
   parola (≥12), 2FA baslat/dogrula, operatör listele/ekle/güncelle (son etkin sahip korunur, 2FA sıfırlama), kiracı listesi
   (santral/kWp/kullanıcı/son giriş sayımları), kiracı detayı (kullanıcılar + santraller son SCADA/koşu), kiracı oluşturma
   (tenant + ilk admin rastgele parola + 72 sa davet bağlantısı; posta yoksa bağlantı bir kez yanıtta), kiracı güncelleme
   (ad/plan/durum/notlar; askıya alma kiracının tüm `oturum_surumu`'nu artırır → ≤60 sn'de tüm jetonlar düşer), kiracı
   kullanıcısı arama, 24 sa parola belirleme bağlantısı (destek). `denetim_service.py`: `kaydet` (kendi işleminde, asla ana
   işi düşürmez, sır yazmaz) ve `listele` (kiracı/eylem/kapsam/limit/once_id).
4. **Bağımlılıklar** `apps/api/deps.py`: `gecerli_kullanici` platform jetonunu 403 ile reddeder; `platform_yetkisi(rol=None)`
   yalnız `kapsam: platform` + DB aktiflik/sürüm (+ sahip zorunluluğu). `apps/api/hiz.py`: limiter paylaşımı.
5. **Uçlar** `apps/api/yonetim.py` (`/v1/yonetim`, 20 uç): `giris` (5/dk), `oturum/yenile`, `ben`, `parola`, `iki-adim/{baslat,
   dogrula}`, `operatorler` (GET/POST/PUT — sahip), `kiracilar` (GET/POST), `kiracilar/{id}` (GET/PUT), `kullanicilar?q=`,
   `kullanicilar/{id}` (PUT aktif/rol — kiracı kuralıyla), `kullanicilar/{id}/parola-sifirlama`, `kullanicilar/{id}/iki-adim-sifirla`,
   `basvurular` (GET), `basvurular/{id}/okundu`, `denetim`. Her yazan uç `denetim_izi`'ne düşer.
6. **Müşteri eylemlerine denetim izi** `apps/api/main.py`: giriş (başarılı), takım ekle/güncelle/2FA sıfırla, parola değişimi,
   API anahtarı üret/iptal, webhook ekle/sil, santral arşivle/geri al, SCADA sil. Sırlar (geçici parola, düz anahtar, webhook
   secret) YAZILMAZ.
7. **Kurulum** `scripts/platform_sahip.py`: ilk sahip (gizli girdi, denetim izine `kaynak: cli`).

## NEDEN
Platform (PVQuant personeli) kimliği yoktu; kiracı açma/parola/2FA sıfırlama sunucuda elle Python'du; vitrin başvuruları müşteri
yöneticisine açıktı (Faz 0 env kilidi geçiciydi). Ayrı tablo + ayrı kapsam: `users.tenant_id NULL` ile süper admin RLS kalıbını ve
«her kullanıcı bir kiracının» varsayımını bozardı; iki yüz aynı jetonu paylaşmaz. Askıya alma ancak jeton iptaliyle (Faz 0) anlamlı.

## KANIT
- `tests/test_yonetim_api.py` (7, DB'siz, GERÇEK jeton akışı): kapsamlar karışmaz (platform jetonu `/v1/plants` 403, müşteri jetonu
  `/v1/yonetim/ben` 403), sürüm/pasif 401, sahip-only 403, kiracı oluştur/askıya al, denetim izine davet bağlantısı yazılmaz,
  başvurular platformda, giriş ucu + müşteri girişi denetim izi.
- `tests/test_platform_db.py` (DB'li, CI'da koşar): ilk sahip → giriş → jeton kapsamı → TOTP kur → kodsuz giriş reddi → kiracı
  oluştur (posta kapalı: bağlantı) → listede/detayda → aynı ad reddi → davet bağlantısıyla parola → müşteri girişi → askıya alma
  → `KiraciAskida` + sv artışı → yeniden açma → kullanıcı arama → destek bağlantısı → denetim yaz/oku → operatör ekle/pasifleştir,
  son sahip korunur. Temizlik etiketle.
- Yerel timescale (CI imajı) + `alembic upgrade head` → `v2480_faz1_platform (head)`; 17/17 hedef test; tam takım **698 geçti** (CI ile aynı imaj, DB'li; 5 dk 24 sn).
- Import: `/v1/yonetim/*` 20 uç; `gecerli_kullanici`/`yonetici_yetkisi` sözleşmeleri aynı (eski testler yeşil).

## DAĞITIM NOTLARI (mühürde)
`alembic upgrade head` (iki tablo + iki sütun) → api yeniden oluştur → `docker compose exec -it api python scripts/platform_sahip.py
<eposta>` ile ilk sahip → `/v1/yonetim/giris` → `iki-adim/baslat` + `dogrula` (TOTP zorunlu hâle gelir). Faz 0 env kilidi
(`PVQ_PLATFORM_TENANT_ID`) Faz 2'de müşteri uçlarıyla birlikte kaldırılır (bugün ikisi de çalışır).

## KALAN (Faz 2+)
`/yonetim` SPA (PlatformKabugu; Giriş bileşeni platform ucuyla), müşteri panelinden GelenTalepler'in çıkarılması, kurtarma
kodları (platform), askıdaki kiracıya panelde mesaj, süper kullanıcı DB bağlantısının indirilmesi (platform_baglami hazır;
`pvquant_app` giriş rolü ayrı iş), kimliğe bürünme (Faz 4), kullanım sayaçları (Faz 3).
