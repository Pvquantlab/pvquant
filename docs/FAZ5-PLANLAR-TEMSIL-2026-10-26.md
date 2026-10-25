# Faz 5 — Planlar (uyarı kipi) + kimliğe bürünme (26.10.2026) — CANLI v2.492
**Durum:** v2.492 = ec6ec3e (26.10), CI #593 yeşil. Sunucu: `git pull`, api + web imajları, yönetici rolüyle `alembic upgrade head` →
`v2492_faz5_planlar (head)` (planlar tohumu pilot 3/3/60/50/5000 [2 kiracı], standart, kurumsal sınırsız; `tenants_plan_fkey` var),
`up -d --force-recreate api web`; worker değişmedi. Canlı index.html + **19/19 JS/CSS** birebir; `/yonetim` 200; `/v1/yonetim/planlar` 422/401;
`/kiracilar/{tid}/temsil` bozuk jeton 401; müşteri `/v1/plants` 422, `/v1/auth/login` yanlış parola 401 (yeni `gecerli_kullanici` imzası canlıda);
api log 0 hata. Gerçek hesapla Planlar sayfası, rozetler ve «Müşteri gözüyle aç» (yeni sekme + şerit) kullanıcıda; denetim izinde `kiraci_temsil`.

Dayanak: `docs/YONETICI-PANELI-YOL-HARITASI-2026-10-24.md` §6 satır 4 ve §7 karar 2/5; denetim raporu O7 dışındaki tüm kalemler kapanmıştı.
Tahmin/rapor/SCADA çekirdeği, RLS politikaları, müşteri uç sözleşmeleri DEĞİŞMEDİ; müşteri kabuğuna yalnız işaretle görünen bir şerit eklendi.

## NE
1. **Şema** `alembic/versions/v2492_faz5_planlar.py`: `planlar` (ad PK, başlık, `santral_limit`, `kullanici_limit`, `api_rpm_limit`, `aylik_rapor_limit`,
   `aylik_dis_api_limit` — NULL = sınırsız, notlar, sıra); tohum pilot 3/3/60/50/5.000, standart 25/10/120/500/50.000, kurumsal sınırsız; tenants.plan'da
   olup tohumda olmayan ad varsa eklenir; `tenants.plan → planlar(ad)` FK (ON UPDATE CASCADE). **Zorlama yok.**
2. **Servis** `platform_service`: `plan_listesi` (kiracı sayısıyla), `plan_guncelle` (negatif ret, None = sınırsız), `temsil_jetonu` (sahip → `kapsam`
   müşteri, `role: viewer`, `temsil: <platform id>`, `sv` platformun, 15 dk; askıdaki kiracıya açılmaz), `kiraci_durumu`.
3. **Kapı** `deps.gecerli_kullanici(request, …)`: `temsil` jetonu yalnız **GET**'te geçer (POST/PUT/DELETE 403 «görüntüleme oturumu salt okunur»), aktiflik/sürüm
   platform tablosundan, kiracı askıya alınırsa 403; `yazma_yetkisi` ayrıca reddeder, `yonetici_yetkisi` rol viewer olduğundan zaten 403. Platform uçları
   kapsam yokluğundan 403.
4. **API** `apps/api/yonetim.py`: `GET /planlar` (herkes okur), `PUT /planlar/{ad}` (sahip; `sinirsiz: [alan]` ile NULL), `POST /kiracilar/{tid}/temsil`
   (sahip; jeton yanıtta, denetim izine `kiraci_temsil` — jeton YAZILMAZ; `plan_guncelle` izli).
5. **Platform arayüzü**: «Planlar» sayfası (sahip; alan başına sayı, boş = sınırsız, Kaydet); `ortak.tsx` `LimitRozet` (null → soluk sayı, ≥ %80 uyarı tonu,
   ≥ %100 «aşıldı»); Müşteriler tablosunda santral/kullanıcı, Kullanım'da dış API/rapor rozetleri; Müşteri detayında «Müşteri gözüyle aç» (yalnız sahip,
   askıdaysa yok) → `features/yonetim/temsil.ts` müşteri jetonu + `pvq_temsil` işareti, yeni sekme. Platform istemcisi `api/yonetim.ts` müşteri jetonuna
   dokunmaz (Faz 2 bekçisi korundu; temsil ayrı modül).
6. **Müşteri kabuğu** `shell/Kabuk.tsx` `TemsilSeridi`: yalnız `pvq_temsil` işareti varsa kırmızı şerit «Platform görüntülemesi · kiracı · salt okunur · N dk
   kaldı · Kapat»; Kapat işareti ve jetonu siler, vitrine döner. Olağan müşteri oturumunda hiç render edilmez. Oturum yenileme (POST) temsilde 403 → istemci
   «mevcut jetonla devam» (null) — tasarım gereği; 15 dk sonra 401 → çıkış.
7. **Testler/araçlar:** `test_yonetim_api` +2 (planlar operatör okur / sahip yazar / sinirsiz; temsil: sahip-only, GET 200, POST 403, yönetici ucu 403, platform
   ucu 403, kiracı askıya alınınca 403, denetim izinde jeton yok), `test_faz0_guvenlik` doğrudan çağrılar `request` ile, `test_platform_db` +1 (tohum, FK reddi,
   plan_guncelle, temsil jetonu iddiaları, askıda ret), web +1 (sahip-only sayfa, rozetler, temsil düğmesi, Kabuk şeridi işaretle, müşteri istemcisi bilmez);
   sahte-api planlar/temsil; kare betiği scratch (`faz5-kare.mjs`).

## NEDEN
İki bekleyen karar (§7): plan adları/eşikleri ve kimliğe bürünme. Limitler önce yalnız rozet (müşteri davranışı kırılmaz), destek ekibi müşterinin gördüğünü
görebilsin ama hiçbir şeyi değiştiremesin (salt okunur, kısa, izli).

## KANIT
- Kapılar: tsc 0 · web test **93/93** · build 0 · oxlint 16 · API testleri 29/29 · DB testleri taze timescale'de (head `v2492_faz5_planlar`) 10/10 + RLS;
  tam takım (DB'li) **713 passed**, 0 hata.
- Kareler (sahte API, Chrome) 1440 + 375: Planlar 3 kart × 5 girdi, taşma 0; Müşteriler rozetleri «1 / 3», «5 / 3 aşıldı», «2 / 25»; Kullanım «1.184 / 5.000»,
  «3 / 50»; «Müşteri gözüyle aç» → yeni sekmede müşteri paneli, şerit «Platform görüntülemesi · Deneme Lab · salt okunur · 15 dk kaldı», Kapat → işaret ve
  jeton silindi; konsol 0.
- Canlı: yukarıdaki Durum satırı.

## DAĞITIM NOTLARI (mühürde)
`alembic upgrade head` (yönetici rolüyle; planlar + FK) · api + web imajları (worker değişmedi) · canlı kanıt: `/v1/yonetim/planlar` 422/401 kapıları,
gerçek hesapla Planlar sayfası ve «Müşteri gözüyle aç» kullanıcıda; denetim izinde `kiraci_temsil`.

## KALAN (Faz 6)
Müşteri «Kuruluş ayarları» düzeni + kiracı yöneticisi 2FA politikası (O7); limit zorlaması ve ödeme (ürün kararı sonrası).
