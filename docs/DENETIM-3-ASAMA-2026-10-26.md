# Üç aşamalı denetim — yönetici paneli fazları 0–6 (26.10.2026) — YERELDE, commit yok
Kapsam: Faz 0 güvenlik tabanı, Faz 1 platform kimliği, Faz 2 `/yonetim` arayüzü, Faz 3 sistem izleme, Faz 4 kullanım, Faz 5 planlar + kimliğe
bürünme, Faz 6 Ayarlar/denetim izi/2FA politikası; ek: 13 canlı ekran görüntüsü. Yöntem: (1) kod denetimi + düzeltme, (2) uçtan uca yeniden
test (gerçek DB + tarayıcı, iki tema), (3) bağımsız ajanla üçüncü denetim + kritik testlerin yeniden koşulması. Müşteri verisi ve canlı sistem
dokunulmadı; hiçbir şey commit/push/dağıtılmadı.

## 1. Aşama — denetim ve düzeltmeler
Bulgular (önem sırası) ve kalıcı düzeltmeler:
1. **Orta — kimliğe bürünme GET'le yazabiliyordu.** `GET /v1/plants/{id}/report` rapor üretir: `report_log`'a yazar ve aylık rapor kullanımını
   sayar; temsil jetonu «salt okunur» denmesine rağmen bunu tetikleyebilirdi. `deps.TEMSIL_YASAK_GET_SONEKLERI = ("/report",)` → 403.
2. **Orta — yönetici kapısı temsil için yalnız role dayanıyordu.** `yonetici_yetkisi` artık `temsil` iddiasını açıkça reddeder (ileride rolü
   viewer olmayan bir temsil türü eklense de kapı kapalı kalır).
3. **Orta — kiracı denetim izi personel kimliğini sızdırıyordu.** `/v1/kurulus/denetim` platform satırlarında PVQuant personelinin e-postası, IP'si
   ve aktör kimliği müşteriye gidiyordu; artık `None` (arayüz «PVQuant» yazar). `kiraci_guncelle` ayrıntısındaki `notlar_degisti` gibi platforma
   özel alanlar süzülür; durum/plan değişimi kalır.
4. **Orta — bilinmeyen plan 500 veriyordu.** `tenants.plan` FK'sı (Faz 5) ile `kiraci_olustur` / `kiraci_guncelle` bilinmeyen plan adında
   IntegrityError → 500. `platform_service._plan_dogrula` → 422 «plan yok».
5. **Düşük — temsil işareti oturumdan uzun yaşıyordu.** 15 dk dolup 401 ile çıkış olunca `pvq_temsil` localStorage'da kalıyor, sonraki gerçek
   girişte kırmızı şerit yanlış çıkıyordu. `cikis()` işareti siler; `TemsilSeridi` jetonda `temsil` iddiası yoksa işareti siler ve çizmez.
6. **Düşük — Planlar sayı girdisi** `step=1` (ondalık limit girilemez; API zaten int'e çevirir).
Sorunsuz bulunanlar: platform/müşteri kapsam ayrımı; sv ve aktiflik; sahip-only uçlar; parametreli sorgular; sırların izinde olmaması; pvq_api
rolü (BYPASSRLS, süper kullanıcı değil); `tenant_baglami` RLS; `hiz_pencere` hizalama (v2.487); `kullanim_sayac` UPSERT; `planlar` FK;
`denetim_temizlik` yalnız giriş/görüntüleme satırları ve ayar 0 → silmez; React kaçışı (dangerouslySetInnerHTML yok).
Testler eklendi: temsil rapor GET 403, personel maskeleme, bilinmeyen plan 422 (API); FK ValueError (DB).

## 2. Aşama — uçtan uca yeniden test
- Python: hedef takımlar API 32/32, DB 11/11 + RLS; **yeni gerçek-DB uçtan uca test** `test_faz5_temsil_uctan_uca_get_ler` (gerçek kapı +
  gerçek jeton): 12 müşteri GET ucu 500 vermez, yönetici uçları 403, `oturum/yenile` 403, rapor 403, platform ucu 403, kiracı askıya alınınca
  403. **Tam takım (gerçek DB, tüm Faz 1 düzeltmeleriyle): 718 passed, 1 skipped, 0 failed (8 dk 13 sn).**
- Web: build 0 (tsc -b), test 94/94, oxlint 16.
- Tarayıcı (sahte API, Chrome): **platform 10 sayfa × 1440/375 + müşteri 10 sayfa × koyu/açık 1440 + koyu 375 = 50 ölçüm.** 1440'ta belge/iç
  taşma 0, sayfa istisnası 0 (iki tema). 375'te tablolar kart içinde kayar (tasarım kuralı); tek belge taşması **Tahminler 375: 132 px** —
  başlık sağ yuvasında «güncellenemedi» çipi + 4 ufuk sekmesi sarmıyordu → `Sayfa` başlığına `.sayfa-bas`, ≤560'ta `flex-wrap`. Yeniden
  ölçüm: Tahminler/Portföy/Ayarlar/Doğruluk/Raporlar 375 → 0.
- Ekran görüntüsü karşılaştırması (13 canlı ekran ↔ kod): başlık/alt metin/çip dili, tablo sola yaslı düzeni, zaman tipografisi, rozetler, Planlar
  alanları, Ayarlar kartları kodla birebir; açık temada Ayarlar ve Portföy kontrast/hiza doğru.

## 3. Aşama — bağımsız son kontrol
(ajan raporu ve sonuç aşağıya eklenecek)
Bağımsız ajan (salt okunur, gerçek DB sondalı): Yüksek yok. Orta 3, Düşük 9. Doğrulanıp DÜZELTİLENLER (yerelde, commit yok):
- **Orta 1** posta gitmezse parola/davet bağlantısı operatöre de dönüyordu (tam yetkili müşteri hesabı yolu) → `platform_service._baglanti_yaniti`:
  yalnız sahibe; denetim ayrıntısına `baglanti_gosterildi`; `parola_sifirlama_gonder` satırına `tenant_id` (Düşük 5).
- **Orta 2** sahip kendi 2FA'sını sıfırlayabiliyordu → `PUT /operatorler/{kendi}` `iki_adim_sifirla` 403.
- **Orta 3** slowapi süreç başına (4 işçi → ~20/dk) → `hiz.paylasimli_sinir` hiz_pencere tablosunda işçiler arası 5/dk/IP; `/v1/auth/login` ve
  `/v1/yonetim/giris`; slowapi DB kesintisinde yedek. `--forwarded-allow-ips *` + 127.0.0.1:8000: yalnız sunucu-yerel (root) süreç; KABUL, belgelendi.
- **Düşük 4** biçimsiz UUID / INTEGER taşması 500 → `yonetim._uuid` 422 (kiracı/kullanıcı/operatör/tenant_id/plant_id), `LIMIT_UST` 1e9, boş başlık 422.
- **Düşük 6** denetim temizliği yalnız `kapsam='platform'` (müşteri Ayarlar izi silinmez). **Düşük 7** kiracı adı benzersizliği güncellemede de.
- **Düşük 8** `/scada/disa` temsil jetonuna kapalı (ham dışa aktarım görüntüleme değil). **Düşük 10** giriş zamanlama dengesi: hesap yokken de bcrypt (kukla hash).
KABUL/ERTELENEN: temsil jti iptali, TOTP tekrar koruması, localStorage jeton, 60 sn önbellek, users/tenants RLS'siz (fazlar öncesi tasarım) → sonraya listesi.
DEVAM (26.10, ikinci oturum): 6 API testi UUID fikstürüyle (T1/T9/PL1 sabitleri) düzeltildi — geçici çözüm değil, uç doğru davranıyor.
Yeni testler: `test_d3_kendi_iki_adimini_sifirlayamaz`, `test_d3_parola_baglantisi_yalniz_sahibe` (+ `_baglanti_yaniti` birim),
`test_d3_giris_paylasimli_pencere_429` (iki giriş ucu; pencere_say 0 → kapı açık), `test_d3_bicimsiz_uuid_422` (11 uç, servis hiç çağrılmaz;
büyük harf/küme ayracı kanonik biçime iner), `test_d3_plan_sinirlari_ve_baslik`; DB: temizlik kapsamı (müşteri satırı kalır), ad benzersizliği
güncellemede, operatöre bağlantı yok (kiraci_olustur + davet_gonder), kukla hash yolu; temsil testine `/scada/disa` 403.
Web: `yonetim/sayfalar.tsx` operatöre bağlantı dönmezse dürüst mesaj (eskiden boş «tek seferlik» kutusu / yanıltıcı «hazırlandı»);
`api/yonetim.ts` tip `not?`. **Yeni bulgu (tarayıcı turu): Santralim** — `/summary` alınamazsa yakalanmamış ret, iskelet sonsuza dek kalıyordu
(Doğruluk aynı durumda dürüst satır gösteriyor) → `Santralim.tsx` `oHata` + «Santral özeti alınamadı; sayfayı yenileyin.» (müşteri paneli,
ön yüz; algoritma/veri yoluna dokunulmadı).

### 3. Aşama test sonuçları
- Hedef Python takımları (gerçek DB 5433): **49 passed, 1 skipped** (yonetim_api 23 = 18 + 5 yeni; platform_db; faz0; dis_api; rls; db_rolu;
  atlanan: test_db_rolu süper kullanıcı testi yerelde).
- Web: build (tsc -b) 0 hata; test **94/94**; oxlint **16 uyarı, 0 hata** (taban).
- Tarayıcı (sahte API, Chrome; platform 10 sayfa × 1440/375 + müşteri 10 sayfa × koyu/açık 1440 + koyu 375 = **50 ölçüm**): belge taşması 0,
  iç taşma (1440) 0, iskelette kalan 0, boş içerik 0, sayfa istisnası/konsol hatası 0 (sahte API'nin 404'leri hariç). Sayfa geçişi (tıklama →
  içerik; ilk sayfa hariç): **medyan 78 ms, p90 163 ms, en yüksek 193 ms (Sistem, 1440)**.
- Tam Python takımı (gerçek DB 5433), iki koşu: **1.** 1 failed, 722 passed, 1 skipped (6 dk 20 sn) — kalan `tests/test_modb_rapor.py::
  test_matrissiz_girdi_kosullu` (rapor üretici, denetim dosyalarıyla ilgisiz; tek başına DB'li 9/9 ve DB'siz 1/1 geçti) → sıra bağımlı/kararsız,
  GİZLENMEDİ, kapsam dışı risk olarak kaydedildi; **2.** **723 passed, 1 skipped, 0 failed (6 dk 6 sn)**.
- Gerçek tıklama (Kullanıcılar → «Parola bağlantısı», sahte API): sahip kipi → tek seferlik bağlantı kutusu + «E-posta gönderilemedi; bağlantıyı
  elden iletin.»; operatör kipi (`OPERATOR=1`) → kutu yok, sunucu notu hata satırında. İlk denemede sahip kipinde «e-postalandı» yazıyordu (benim
  değişikliğimin yan etkisi) → mesaj `gonderildi`'ye bağlandı; `islem` fn'in döndürdüğü metni mesaj olarak alır.

### Bağımsız son kontrol (ikinci ajan, salt okunur, gerçek DB sondalı, Caddy XFF deneyi)
Yüksek yok. 7 düzeltmeden 5'i sağlam bulundu (bağlantı yalnız sahibe — rol DB'den, sahte `rol` iddialı jeton atlatamıyor; paylaşımlı 429;
UUID 422; temizlik kapsamı; web). Bulgular ve DÜZELTMELER:
- **Orta 1.1 — «kendi 2FA'sını sıfırlayamaz» atlatılıyordu:** çalınmış sahip JETONU ile ikinci bir sahip hesabı açılıp onunla kurbanın 2FA'sı
  sıfırlanabiliyordu (sondayla kanıtlı). → `platform_service.yeniden_dogrula(pid, sifre, kod)` (parola + TOTP; 2FA'sız False) ve `yonetim.
  _yeniden_dogrula`: **sahip hesabı açma, sahip yapma, başkasının 2FA'sını sıfırlama** artık aktörün parolası + kodunu ister (403 «yeniden
  doğrulama gerekli»); çalınmış jeton tek başına bu zinciri kuramaz. Parola/kod denetim izine yazılmaz (`model_dump(exclude)`). Web: Operatörler
  sayfasında «Yeniden doğrulama» kartı (parola + kod, Onayla/Vazgeç); sahip rolüyle ekleme de aynı kart; gerçek tıklama 1440/375 doğrulandı.
- **Düşük 1.2** `POST /basvurular/{bid}/okundu` UUID doğrulamasız (500) → `_uuid`. **Düşük 1.3** kiracı adı güncellemede kırpma/uzunluk yoktu
  (« Firma», «» geçiyordu) → strip + ≥2. **Düşük 1.4** pasif hesapta bcrypt kısa devre (6 ms ↔ 280 ms) → bcrypt her dalda koşar (platform +
  müşteri girişi). **Gözlem 3** operatörün parola bağlantısı çağrısı göremeyeceği jeton üretip müşterinin bekleyen bağlantısını bozuyordu →
  posta yapılandırılmamışsa operatör için jeton ÜRETİLMEZ, gönderim arızasında üretilen silinir (DB testi: bekleyen jeton değişmez).
  **Gözlem** `hiz_pencere` küresel temizliği yoktu → `kullanim_service.pencere_temizle` (1 saatten eski), worker `denetim_temizlik` işinde.
KABUL (belgelendi): `--forwarded-allow-ips *` — Caddy deneyinde dış XFF soyuluyor, yalnız sunucu-yerel süreç istisna; yerel compose api
konteyneri bayat (kod bulgusu değil).
Testler (son durum): hedef Python takımları **51 passed, 1 skipped** (yeni: `test_d3_hassas_islemler_yeniden_dogrulama`,
`test_d3_basvuru_kimligi_422`; DB: `yeniden_dogrula` 5 dal, yetim jeton, ad kırpma); web build 0 / test **94/94** / oxlint 16 uyarı 0 hata;
tarayıcı 50 ölçüm: taşma 0, iskelet 0, hata 0, geçiş medyan 80 ms / p90 165 ms / en yüksek 232 ms; gerçek tıklama: Parola bağlantısı (sahip/
operatör kipi), 2FA sıfırla → yeniden doğrulama kartı → PUT gövdesi sifre+kod → başarı mesajı.
Tam Python takımı (son koşu, gerçek DB 5433, tüm düzeltmelerle): **725 passed, 1 skipped, 0 failed (7 dk 3 sn)**.

## Commit planı (ONAY BEKLİYOR — commit/push/dağıtım yapılmadı)
Tek mühür önerisi **v2.494 = ÜÇ AŞAMALI DENETİM + «Ayarlar»**: 24 dosya. Dağıtım gerekirse: api + worker + web imajları; alembic değişikliği YOK;
.env değişikliği YOK. Canlıda smoke: `/v1/yonetim/giris` 6 ardışık → 429; `PUT /operatorler/{kendi} iki_adim_sifirla` 403; `/kiracilar/abc` 422.

## Kalan riskler (sonraya listesi, bu turda bilerek yapılmadı)
- Temsil jetonu tekil iptal (jti) ve görüntülenen verinin izlenmesi; TOTP tekrar koruması (platform + müşteri); jetonların localStorage'da
  olması (httpOnly çerez); 60 sn oturum önbelleği (askıya alma ≤60 sn gecikir, belgeli); `users`/`tenants` RLS'siz (fazlar öncesi tasarım,
  kod süzgeçli); `datetime.utcnow()` DeprecationWarning (Python 3.14); `tests/test_modb_rapor.py::test_matrissiz_girdi_kosullu` tam takımda
  bir kez kaldı, yeniden koşuda geçti (sıra bağımlı; rapor üretici, kapsam dışı).
