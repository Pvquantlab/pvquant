# Faz 6 — Müşteri paneli: «Kuruluş» sayfası, kiracı içi denetim izi, yönetici 2FA politikası (26.10.2026) — CANLI v2.493
**Durum:** v2.493 = 1551c3f (26.10), CI #595 yeşil. Sunucu: `git pull`, api + web imajları, yönetici rolüyle `alembic upgrade head` →
`v2493_faz6_kurulus (head)` (politika her iki kiracıda kapalı), `up -d --force-recreate api web`; worker değişmedi. Canlı index.html + **20/20
JS/CSS** (yeni Kuruluş parçası dahil) referansla birebir; `/` 200, `/v1/healthz` ok; `/v1/kurulus/ayarlar` 422, `/v1/kurulus/denetim` bozuk jeton
401; `/v1/auth/login` ve `/v1/yonetim/giris` yanlış parola 401; api log 0. Planlar rötuşu aynı mühürde. Gerçek hesapla Kuruluş sayfası, politika
kutusu ve denetim izi kullanıcıda.

Dayanak: `docs/YONETICI-PANELI-YOL-HARITASI-2026-10-24.md` §6 satır 5; denetim raporu O7. Tahmin/rapor/SCADA çekirdeği, RLS, mevcut uç
sözleşmeleri DEĞİŞMEDİ (ek uçlar + ek sütun). Müşteri panelinde navigasyon değişti: yönetim kartları Portföy'den «Kuruluş»a taşındı.

## NE
0. **Ad (26.10, kullanıcı kararı):** menü ve sayfa başlığı «Ayarlar» — Türkiye'deki SaaS alışkanlığı («Kuruluş» resmî duruyordu). İç kimlik
   `kurulus`, uçlar `/v1/kurulus/*` ve dosya adı aynen; yalnız görünen ad değişti (birikiyor, bir sonraki mühürle).
1. **Şema** `alembic/versions/v2493_faz6_kurulus.py`: `tenants.yonetici_2fa_zorunlu BOOLEAN NOT NULL DEFAULT false` — varsayılan kapalı, hiçbir
   kiracının davranışı değişmez.
2. **Kimlik yolu** `auth_service.oturum_durumu` / `oturum_yenile`: `iki_adim_kurulmali` = politika açık ∧ rol admin ∧ TOTP kapalı (60 sn önbellek;
   ayar değişince düşürülür). `deps.gecerli_kullanici`: bu durumda yalnız `MUSTERI_KURULUM_YOLLARI` (`/v1/iki-adim*`, `/v1/oturum/yenile`,
   `/v1/hakkinda`) açık, diğerleri 403 «iki adımlı doğrulama zorunlu; önce kurun». Editör/izleyici etkilenmez. Jeton değişmez.
3. **API** `apps/api/main.py`: `GET /v1/kurulus/denetim` (yönetici; kiracı jetondan — kendi ekibinin eylemleri VE platformun bu kiracıda
   yaptıkları, kapsam sütunuyla), `GET/PUT /v1/kurulus/ayarlar` (yönetici; denetim `kurulus_ayar`). `services/kurulus_service.py`.
4. **Müşteri arayüzü** `features/sayfalar/Kurulus.tsx` (yeni, tembel parça): Portföy'den AYNEN taşınan Dış erişim (yönetici), Kuruluşlar arası
   paylaşım, Hesap ve ekip (+ iki adım bölümü), Santral arşivi (yönetici) + yeni «Güvenlik politikası» (yönetici; onay kutusu, 2FA'sız yönetici
   sayısı) + «Denetim izi» (yönetici; ayrıntı çipleri `lib/AyrintiCipleri.tsx` — platformla ortak). Portföy yalnız analitik (3 kart). Menü:
   Raporlar'dan sonra «Kuruluş» (açık yüz, ikon). `shell/Kabuk.tsx` `IkiAdimKapisi`: `oturum/yenile` `iki_adim_kurulmali` dönerse içerik yerine
   kurulum ekranı («Kurdum, devam et» yeniden sorar). Yazma kontrolleri rolle gizli — kural aynen.
5. **Platform** Müşteri detayı başlık çipinde «yönetici 2FA zorunlu» (kiraci_detay yeni alan).
6. **Testler/araçlar:** `test_yonetim_api` +1 (kuruluş uçları yönetici-only, kiracı jetondan, PUT izli; politika açık → `/v1/iki-adim` 200,
   `/v1/plants` 403, kapanınca 200), `test_faz0_guvenlik` sahte satır/önbellek beklentisi yeni alanla, `test_platform_db` +1 (politika aç/kapa,
   oturum_durumu bayrağı, 2FA kurulunca kapı açılır, kiracı detayı alanı), web +1 (menü, App yolu, Portföy kartları çizmez, Kuruluş bileşenleri,
   Kabuk kapısı, platform rozeti); sahte-api `/v1/kurulus/*`; kare betiği scratch (`faz6-kare.mjs`, koyu + açık 1440, koyu 375).

## NEDEN
Portföy'ün altında dört yönetim kartı analitiği gömüyordu; kiracı kendi ekibinin ve platformun kendi hesabında ne yaptığını göremiyordu;
yönetici hesaplarında 2FA politikası yoktu (O7). Politika isteğe bağlı: zorlamayı kiracı yöneticisi kendisi açar.

## KANIT
- Kapılar: tsc 0 · web test **94/94** · `npm run build` 0 (tsc -b eksik import ve ikon haritasını yakaladı) · oxlint 16 · API testleri 30/30 ·
  DB testleri taze timescale'de (head `v2493_faz6_kurulus`) 10/10 + RLS; tam takım (DB'li) **715 passed**, 0 hata.
- Kareler (sahte API, Chrome, admin jetonu) koyu 1440 / açık 1440 / koyu 375: Portföy 3 kart (Santraller, günlük tahmin, DSG), Kuruluş 6 kart
  (Hesap ve ekip, Güvenlik politikası, Dış erişim, Kuruluşlar arası paylaşım, Santral arşivi, Denetim izi), politika kutusu, 3 denetim satırı
  (ekibiniz/platform), menüde «Kuruluş»; belge taşması 0. Konsol: yalnız sahte API'nin karşılamadığı santral uçlarının 404'leri (`/v1/plants/a1/*`,
  Santralim ilk sayfa) — sayfa istisnası yok; bu uçlar canlıda gerçek.
- Canlı: yukarıdaki Durum satırı.

## DAĞITIM NOTLARI (mühürde)
`alembic upgrade head` (yönetici rolüyle) · api + web imajları (worker değişmedi). Canlı kanıt: `/v1/kurulus/ayarlar` 422/401/403 kapıları; gerçek
hesapla Kuruluş sayfası, politika kutusu ve denetim izi kullanıcıda. Politika kapalı gelir.
