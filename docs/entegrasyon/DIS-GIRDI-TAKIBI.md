# Dış girdi takibi — entegrasyon yol haritası kalanları (10.11.2026)

v2.563 ile Aşama 0–6'nın yerelde yapılabilen her parçası canlıya çıktı. Kalan her kalem bir **dış girdi** bekliyor: gerçek hesap,
gerçek cihaz, sahip izni, üretici onayı ya da hukuki görüş. Bu belge her kalem için **kim verir · nereye başvurulur · biz ne göndeririz ·
ne alırız · kod tarafı ne durumda · sıradaki adım** sorularını tek yerde tutar ve ilerledikçe güncellenir.

Kaynak: `~/Desktop/PVQuant_Inverter_Pazar_Arastirmasi` (A, [Kn]) ve `~/Desktop/PVQuant_Turkiye_Invertor_Entegrasyon_Arastirmasi` (B, [Sn]/[Tn]);
ikisinde de **hiçbir sağlayıcı için başvuru süresi, onay süresi ya da ticari onay formu belgelenmemiş** ve üreticilere hiçbir başvuru yapılmamıştır.
Aşağıdaki usuller araştırma notudur; ilk temasta üreticiyle teyit edilir. Gönderilecek metinler: `docs/entegrasyon/BASVURU-METINLERI.md`.

Durum sözlüğü: **bekliyor** (başvuru yapılmadı) · **başvuruldu** (tarih) · **alındı** (girdi elimizde, doğrulama sürüyor) · **kapandı** (doğrulandı, defterde kanıt).

## Önerilen sıra

Ölçüt: PVQuant'ın tek başına başlatabildikleri önce; müşteri/saha gerektirenler ilk müşteriyle; uzun süren hukuki süreç paralel.

| Sıra | Kalem | Kimi bekler | Neden bu sırada |
|---|---|---|---|
| 1 | KVKK md. 9 görüşü (D1) | hukuk danışmanı | Belge hazır; en uzun süren iş, paralel başlasın |
| 2 | Sungrow geliştirici kaydı + ticari onay (D4) | PVQuant kendi başvurur | Kayıt kendi başımıza; yönlendirme ucu için kod gerekir |
| 3 | SolarEdge geliştirici kaydı (D5) | PVQuant kendi başvurur | Kayıt kendi başımıza; filo onayı için bir kurulumcu gerekir |
| 4 | FusionSolar NBI hesabı (D2, P-FS) | Huawei kayıtlı bir kurulumcunun yöneticisi | Hedef segmentte en yaygın marka; bağlayıcı hazır; birim sorusu ancak gerçek yanıtla kapanır |
| 5 | Growatt belirteci (D6) | kurulumcu/distribütör OSS hesabı | Kurulumcu başvurur; sabit IP'miz var |
| 6 | Solis anahtarı (D7) | santral sahibi (bilet) | Yalnız son kullanıcı başvurabiliyor; müşteri gerekir |
| 7 | Pilotlar P-1xx / P-7xx / P-104 / P-SFTP (D8) | pilot sahası sahibi + O&M + OT | İlk müşteri görüşmesiyle (P-ENV soruları, izin metni hazır) |
| 8 | Ortaklık görüşmeleri Q6 (D9) | Inavitas / LOGGMA-Solarify / Mikrodev | Ticari; belgeli dış yol yok, görüşmeyle açılır |
| 9 | mTLS zorunluluğu + imzalı güncelleme (D10) | ilk çok sahalı müşteri | Araçlar hazır; karar eşiği (Q5) gelince |
| 10 | GoodWe / Deye / Sofar bağlayıcıları (D11) | müşteri talebi | Yapılmayacaklar listesi: talep olmadan bağlayıcı yazılmaz |

## Kalemler

### D1 — KVKK md. 9 hukuki görüşü
- **Kim:** hukuk danışmanı (KVKK/veri koruma alanında).
- **Biz ne göndeririz:** `docs/guvenlik/KVKK-BULUT-KIMLIK-DEGERLENDIRME.md` (olgular, veri akışı, 6 soru) + `docs/guvenlik/KEK-ANAHTARI.md`; isterse hizmet sözleşmesi taslağı.
- **Ne alırız:** 6 soruya yazılı görüş; sözleşmeye eklenecek hükümler; veri sorumlusu/işleyen rol dağılımı.
- **Kod tarafı:** görüşe göre onay metinleri (`bulut_kimlik_service.ONAY_METNI`) ve saklama/imha süreleri değişebilir; bugün kimlik silinince anında siliniyor, ham sağlayıcı verisi süresiz.
- **Durum:** bekliyor. **Sıradaki adım (siz):** danışman seçimi, iki belgeyi iletmek.

### D2 — FusionSolar Northbound (NBI) hesabı (P-FS)
- **Kim:** Huawei «Installer Registration» ile kayıtlı bir kurulumcu şirketin **yöneticisi**; santral sahibi başvuramaz («Owners cannot apply for northbound accounts»); şirket başına en çok 5 NBI hesabı [K81] (A 02:78,134). Yönetici ayrı bir Northbound kullanıcısı açıp izinli santralleri ve arayüzleri atar; normal portal hesabı bunun yerine geçmez [S29].
- **Menü yolu / süre / ücret:** belgede yok (ikincil iz: System Management → OpenAPI Management).
- **Biz ne göndeririz:** BASVURU-METINLERI §1 (kurulumcuya istek): hangi santraller, hangi arayüzler (`/thirdData/login`, `/thirdData/stations` ya da `getStationList`, `getKpiStationHour`), yalnızca okuma, kimliğin güvenli kanaldan iletilmesi.
- **Ne alırız:** `userName` + `systemCode`; XSRF-TOKEN 30 dk; 10 dk'da ≤5 oturum; 5 hatalı parola → 30 dk kilit [K81]. Türk santrallerinin hangi bölge sunucusuna düştüğü bilinmiyor (intl/eu5/… listesi kodda).
- **Kod tarafı:** bağlayıcı, sınama, şifreli kayıt ve saatlik çekiş canlı; «birim doğrulandı» işareti elle. **Doğrulama protokolü:** (1) sınama → santral listesi, `capacity` birimi (kWp/MW) portal ile kıyas; (2) 1 gün çekiş → `bulut_saatlik_ham`; (3) `inverter_power`'ın kWh mi kW mi olduğu portal «saatlik enerji» dışa aktarımıyla kıyas — **araç hazır (v2.565, yerelde):** Santralim kayıt satırında CSV yükleme, beş yorumla kıyas, «birim doğrulandı» yalnız belge yorumu uyumluysa işaretlenebilir; (4) 407/403/429/20618 davranışı günlüğe; (5) sonuç defterde, `birim_dogrulandi` işaretlenir, G07 kapanır.
- **Durum:** bekliyor. **Sıradaki adım (siz):** FusionSolar kullanan bir kurulumcu/EPC teması; §1 metnini iletmek.

### D3 — Pilot kapıları için yazılı izin (G02/G03/G04)
- **Kim:** tesis/veri sahibi + O&M + OT birlikte imzalar; imzalar tamamlanmadan P0 kapanmaz [T01] (B 17/09:20–23, 09a:14,37).
- **Araştırmada hazır metin yok;** kapsam kalemleri var: cihaz listesi, amaç, okuma kapsamı (FC03/04 + unit + adres süzgeci), test penceresi, saklama, kesinti ve geri alma yetkisi, tolerans/saat belirsizliği/kapsama eşikleri. Taslak: BASVURU-METINLERI §2.
- **Kod tarafı:** Santralim › Pilot kartında saha kapıları «sahibin tarihli beyanıyla» kapanır (`pilot_service.KAPILAR`); imzalı belge dosya olarak saklanmaz (ileride ek).
- **Durum:** taslak hazır, pilot sahası yok.

### D4 — Sungrow iSolarCloud geliştirici erişimi + ticari onay (VIII(c))
- **Kim:** PVQuant kendi adına geliştirici portalına kaydolur (A'da `developer-api.isolarcloud.com`, B'de `.com.hk`); portal hesabı onaylanır, sonra **uygulama başvurusu**: uygulama adı, simge, **redirect URL** [K87] (A 08:677–685). Onay sonrası AppKey + Secret Key + Authorize URL.
- **Ticari onay:** Developer Service Agreement VIII(c) onaysız ticari kullanımı askıya alma nedeni sayar; III(c) üçüncü taraflara dağıtım yasağı; II(a) ek ticari bilgi isteyebilir; X ÇHC hukuku, ilk temas `data-protection@sungrowpower.com` [K88]. **Onayın nasıl alındığı (form/süre) belgelenmemiş** → BASVURU-METINLERI §3 ile yazılı talep.
- **Sahip onayı (OAuth):** sahip iSolarCloud giriş sayfasında uygulamayı onaylar; URL kalıbı yalnız ikincil kaynakta (`…#/authorized-app?cloudId=…&applicationId=…&redirectUrl=…`, `state` `#`'ten önce); `POST /openapi/apiManage/token` ile code → access (~48 sa) + refresh; −2 → yeniden onay [K87] (A 08:687–722). Türkiye'nin bölgesi (intl/eu) DOĞRULANMADI.
- **Kod tarafı (v2.564, yerelde):** bağlayıcı, belirteç yenileme (zarf şifreli) canlı; sahip yönlendirme ucu YAZILDI — `POST …/bulut-kimlik/oauth/baslat` + `GET /v1/bulut/oauth/sungrow/geri-donus` (tek kullanımlık state, sunucuda belirteç değişimi, kasaya yazım, çok santralda ertelenmiş seçim); ortam değişkenleri ve kayıt adımları `docs/entegrasyon/OAUTH-UYGULAMA-KAYDI.md`. Geri dönüş adresi: `https://pvquant.com/v1/bulut/oauth/sungrow/geri-donus`. Kota: Basic 2.000/sa, 100.000/ay; dakika geçmişi ≤3 sa × ≤50 santral.
- **Durum:** kod canlıda (v2.565, 10.11); kayıt bekliyor. **Sıradaki adım (siz):** geliştirici kaydı (redirect URL yukarıda), §3 e-postası; değerler `.env`'e.

### D5 — SolarEdge V2 geliştirici kaydı + filo erişimi
- **Kim:** PVQuant `developer.solaredge.com`'da geliştirici hesabı ve uygulama açar (Free: 2.000 kredi/ay, 10 CPM, 1 uygulama; Starter 100 $/20.000; sandbox yok) [K77]. Üç erişim yolu:
  - **External Fleet:** uygulama `Pending` açılır; onay bağlantısı `…/fleet-authorize/{token}` 14 gün, tek kullanım; **filo sahibi** (kurulumcu) SSO ile girer, süre seçer (3/6/12 ay ya da ≤24 ay); sonra «Generate Key». Uygulama başına tek filo (A 08:59–90).
  - **Associated Accounts:** siteleri tutan hesap Monitoring › Account Details › Associated Accounts › Add → PVQuant yönetici e-postası, «Read only», «Per site»; **PVQuant'ın installer hesabı olması şart** (A 08:84–89).
  - **OAuth site erişimi:** `connect.solaredge.com/authorize?client_id=…`, Allowed Redirect URI uygulamada; her onay tek site; access 2 sa, refresh 14 gün kullanılmazsa düşer; PKCE yok (A 08:92–109).
- **Kod tarafı (v2.564, yerelde):** V2 filo anahtarı bağlayıcısı canlı (X-API-Key, `/v2/sites`, `/energy?resolution=HOUR`, 429 ayrımı); site sahibi OAuth yolu YAZILDI — ayrı sağlayıcı kaydı `solaredge_oauth` (Bearer; `/sites/{id}` + `/energy`; 401'de yenileme; `state` `external_id` ile taşınır, `site_id` geri dönüşten). Geri dönüş adresi: `https://pvquant.com/v1/bulut/oauth/solaredge_oauth/geri-donus`. Geliştirici kullanım şartları (ticari kullanım, yeniden dağıtım) DOĞRULANMADI [K79].
- **Durum:** kod canlıda (v2.565, 10.11); kayıt bekliyor. **Sıradaki adım (siz):** geliştirici kaydı (Client ID/Secret → `.env`); filo onayı için SolarEdge'li bir kurulumcu teması (BASVURU-METINLERI §4).

### D6 — Growatt OpenAPI belirteci
- **Kim:** OSS hesabı olan **kurulumcu** (Growatt ile doğrudan sözleşmesi varsa distribütör): OSS › System Settings › System Management › **Add API** → onay → belirteç e-postayla [K90]; son kullanıcı kurulumcusuna başvurur (A 04_api_grup_B:16–23). Türkiye hattı: +90 312 394 71 00, servis@growatt-tr.com / turkey@growatt.com (Form Elektrik ile aynı numara [K305]); rolü belgede yok.
- **Ne alırız:** 32 karakter sabit `token` («Permanent (tentative)»); **IP beyaz listesi** önerilir, sabit olmayan IP'den çağrı belirteci kapattırabilir [K90]. PVQuant sabit IP: 178.18.206.130. Beyaz listenin nereye girildiği belgede yok.
- **Kod tarafı:** v1 bağlayıcı (yalnız güç serisi) canlı; limitler 5 dk/çağrı, `/plant/energy` günde 10, ≤7 gün aralık.
- **Durum:** bekliyor. **Sıradaki adım (siz):** Growatt kullanan kurulumcu teması; BASVURU-METINLERI §5.

### D7 — SolisCloud API anahtarı
- **Kim:** **santral sahibi** (eski SSS: kurulumcuya kapalı [K94]; yeni portal developer.soliscloud.com owner/installer HMAC + üçüncü taraf OAuth2 ayrımı yapıyor, ticari inceleme istiyor [S36][S37] — çelişki, ilk hesapla teyit).
- **Adımlar (sahip):** Service Centre › ticket «API Access Request» (SolisCloud e-postası) → onay e-postası → çıkış/giriş → Service › API Management › «activate now» → CAPTCHA + e-posta kodu → **Key ID + Key Secret** [K367] (A 08:928–936). Aynı anahtar yazma uçlarını da açar; PVQuant kodunda yazma uçları yasak.
- **Sözleşme:** kullanım şartları (2025-01-01) verinin üçüncü tarafa yeniden satışını yasaklar; «müşteri adına analiz» ile «ham veri satışı» ayrımı yazılı netleşmeli (U09) → BASVURU-METINLERI §6.
- **Kod tarafı:** HMAC bağlayıcı canlı; www/v3 hangisi kanonik DOĞRULANMADI (ilk anahtarla ikisi denenir).
- **Durum:** bekliyor; Solis'li müşteri gerekir.

### D8 — Pilotlar (P-1xx, P-7xx, P-104, P-SFTP, P-ENV)
- **Ortak:** ilk görüşmede P-ENV soruları (BASVURU-METINLERI §7) → B 17/09a parametre formu (29 parametre) → D3 izin → kapılar.
- **P-1xx (SMA CORE1 / Fronius DM2):** SMA: FW ≥3.14, yalnız TCP 502, unit **126** (genel varsayılan 1 değil); Modbus varsayılan kapalı, açılınca **parolasız yazma da açılır** → OT süzgeci (FC03 + unit + adres) kanıtlanmadan sahaya çıkılmaz [T01]; CORE1 artık satılmıyor. Fronius: port 502, DM başına ≤6 inverter, «rtu» seçilirse TCP kapanır; inverter no 00 → unit 100; ≥10 s timeout (B 11a:44).
- **P-7xx (ennexOS / Huawei M-serisi):** ennexOS yalnız 1, 123, 701–714; Huawei M-serisi sertifikası 1, 701, 702, 714; amaç `TotWhInj` sahada var mı. VPN'i saha başlatır, 502'ye yalnız tüneldeki okuyucu; SmartLogger ≤5 istemci.
- **P-104 (GE FLEXINVERTER YEKA / Inavitas):** istenecek paket: logger IP/port; CA ve CA/IOA/COT boyları; k/w/t; nokta tablosu (IOA→tip→anlam→birim); PVQuant IP beyaz listesi; **ayrı yedeklilik grubu/kanal**; zaman kaynağı [K387][K137][K140]. SmartLogger ≤5 IEC104 IP, 4G üzerinden kurulamaz, «IEC104-N IP» alanı; Logger1000 port 2404 + «Generate Point Table». EDAŞ RTU'suna asla; YEDAŞ bildirim, OEDAŞ/Enerjisa yazılı teyit [K214][K326][K327]. STARTDT yalnız yazılı onay + ayrı yuva.
- **P-SFTP (Solarify/LOGGMA/Mikrodev):** Solarify «periodic FTP Push» yalnız SSS'de, şema yok; LOGGMA «API ve FTP» vaadi, şema yok; Mikrodev FTP push yok (CSV/XLSX dışa aktarım, MQTT, Web API). Ortak şema önerisi (santral, zaman+ofset, güç, enerji, kalite) bizde; müşteriye PVQuant tarafında SFTP hesabı (işletim).
- **Kod tarafı:** hepsi hazır ve «gerçek cihazda doğrulanmadı» etiketli; pilot kartı + referans kıyası canlı.
- **Durum:** bekliyor; pilot sahası yok. Aday temaslar (Q7): Kalyon/GE/Inogen sahası, SMA CORE1 ya da Fronius DM2 sahibi, Huawei M-serisi sahası.

### D9 — Ortaklık görüşmeleri (Q6)
- Inavitas: belgeli dış yol yok, IEC 104 slave rolü doğrulanmadı [K334][K337]. LOGGMA/Solarify: API+FTP vaadi, uç/şema yok; mahsuplaşmada rakip. Mikrodev: Web API, CSV/XLSX, MQTT, OPC UA Server belgeli; GES referansı yok. Üçü için iletişim kişisi belgede yok.
- **Konu:** ikinci IEC 104 master + FTP push şeması. **Durum:** bekliyor (ticari).

### D10 — Edge mTLS zorunluluğu, sertifika döndürme, imzalı güncelleme
- Araçlar hazır (`scripts/edge_ca.sh`, Caddy bloğu, TOPLAYICI.md). Zorunluluk ve prosedür ilk çok sahalı müşteriyle (Q5 eşiği). İmzalı güncelleme (wheel/git etiketi) yok.
- **Durum:** karar bekliyor; dış girdi değil, eşik.

### D11 — GoodWe / Deye / Sofar bağlayıcıları
- Yol haritası «yapılmayacaklar»: talep olmadan bağlayıcı yazılmaz. GoodWe için G08 (RTA lisansı/history, yerel yön/harita) açık.
- **Durum:** talep bekliyor.

## Güncelleme günlüğü
- 10.11.2026 — belge açıldı; tüm kalemler «bekliyor»; başvuru metinleri taslağı yazıldı.
- 10.11.2026 — D4/D5 kod tarafı: sahip OAuth yönlendirme ucu, ertelenmiş santral seçimi, SolarEdge site sahibi bağlayıcısı (v2.564, yerelde).
- 10.11.2026 — D2 adım 3 aracı: portal dışa aktarımıyla birim kıyası, «birim doğrulandı» kanıta bağlandı (v2.565, yerelde).
