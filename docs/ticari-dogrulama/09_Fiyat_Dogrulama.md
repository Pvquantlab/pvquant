# 09 — Fiyat ve ödeme istekliliği doğrulaması (Faz 8, F8-G — 13.11.2026)

> **Durum: ödeme istekliliği kanıtı SIFIR** (K-28: ücretli müşteri, imzalı sözleşme, kabul edilmiş teklif yok). Bu belgede **hiçbir TL/€ tutarı PVQuant fiyatı olarak yazılmaz**
> (plan onay 6; Faz 6 karar 10); fiyat **formüllüdür**, sayı görüşmelerden sonra kullanıcı kararıyla Faz 6 `04`'e yazılır. **Canlı faturalama ayarı yoktur** (ödeme altyapısı entegre
> değil; tahsilat panel dışında — Faz 6). Dayanak: Faz 6 `04_Fiyatlandirma_Senaryolari.md` (hibrit formül, dilimler, dış çapalar), `05_Maliyet_ve_Karlilik.md` (maliyet birimi
> santral konumu-gün), `06_Deger_Olcumu.md` (altı şart); `faz2/D` §4.5 (ödeme kanıtı yok); görüşme soruları `04` D5/D6, E rehberi S15/S16.

## 1. Ayrım merdiveni — ne «ödeme istekliliği» sayılır

| Basamak | Ad | Kanıt | Sayılır mı | 04 §5 sinyal merdiveni |
|---|---|---|---|---|
| 0 | **Varsayımsal isteklilik** («öderdik», «makul», «ilgileniriz») | sözlü | **hayır** (K1; gösterge) | 1 |
| 1 | **Bütçe** | bugün benzer bir hizmet/yazılım için fatura kalemi var (D5/S15) ya da bütçe sahibi ve kalem adı söyleniyor | «bütçe var» — ödeme değil | 3 |
| 2 | **Yazılı ilgi** | teklif isteyen e-posta / bütçe sahibiyle toplantı daveti | zayıf sinyal | 5 |
| 3 | **Kabul edilen teklif** | formüllü teklif mektubuna (sayılarıyla) yazılı «evet» | güçlü sinyal | 5–6 |
| 4 | **İmza / niyet mektubu** | niyet mektubu (E §4 merdiven 3) ya da sözleşme / sipariş | taahhüt | 6 |
| 5 | **Fiili ödeme** | fatura + ödeme kaydı (panel dışı) | **tek gerçek kanıt** | 6 |

Puan kartına (11) yalnız 3–5 «dönüşüm», 1–2 «sinyal» olarak girer; 0 hiçbir yere sayı olarak girmez.

## 2. Faz 6 formülüyle üç planın değerlendirmesi (sayı yok)

`P_abonelik(ay) = P_platform(plan) + P_portföy(S, M) + Σ P_modül(m) [+ tek seferlik kurulum]`; portföy bedeli dilimli (D1–D5: S santral sayısı maliyet tabanı, M AC MW değer
fiyatlaması); δ_f/δ_r sıfır (tek seçenek: saatlik veri, saatlik/15 gün tahmin); kullanım bedeli yalnız dış API ve işlem hacmi, kademeli, sürpriz faturasız.

| Boyut | Pilot | Standart | Kurumsal | Doğrulanacak soru (görüşme) |
|---|---|---|---|---|
| Süre | 60 gün (Faz 6 varsayımı; `pilot_bitis`) | aylık/yıllık — **karar yok** | sözleşmeyle | E7: aylık mı yıllık mı; pilot → yıllık geçiş beklentisi |
| Kapsam (tohum v2609) | 5 modül: tahmin, doğruluk (karne + bağımsız doğrulama), veri (1 bağlantı), temel alarm, KGÜP öneri (revizyon yok); portföy 0 | 11 modül (+ finansal etki, mutabakat, gelişmiş rapor, paylaşım, portföy/DSG 1, dış API oku) | 15 modül (tam) | E4: hangi modül «olmazsa olmaz», hangisi «hiç kullanmam» |
| Veri erişimi | dosya yükleme; 1 bağlantı | dosya + bulut bağlayıcı (gerçek hesapla doğrulanmadı — K-23) + dış API (oku) | dış API tam | S14/Y8: bugünkü veri hattı; API'ye kim bağlanır |
| Kurulum emeği (tek seferlik) | santral künyesi, veri hattı, KGÜP arşivi yükleme, kullanıcılar — **saat ölçülmedi** | + portföy/üyelik/sözleşme kaydı, bildirim yükleme | + entegrasyon (SCADA/API), veri göçü | E6: kurulum ücretine bakış; «kim yapacak» |
| Deneme (bizim) maliyeti | 05: değişken maliyet santral **konumu-gün**; hava indirme ≈ 1,4 saat/konum/gün, tek işçi ≈ 17 konumda dolar → 3 santrallik pilot ölçülebilir, 120 santral bugünkü mimariyle değil | — | — | F8-H kapasite riski (12) |
| Pilot ücreti | **karar açık** (04 §5 öneri: ücretsiz, 3 santral/3 kullanıcı, API yok) | — | — | ücretsiz pilot ödeme sinyali üretmez → pilot sonunda **teklif şart** (10) |

Çıkarım (kanıtsız, hipotez): segment A (1–3 santral) Standart D1; B (4–15) Standart D2 + finansal etki/rapor; C (16–150) Kurumsal D3–D4 + portföy/DSG/mutabakat/dış API (Faz 6 04 §3 senaryoları A/B/C).

## 3. Görüşme egzersizleri (fiyat bölümü; 40–50. dakika — `04` §4; görüşmeci rakam söylemez)

| # | Egzersiz | Soru metni | Kayıt alanı | Tuzak / kural |
|---|---|---|---|---|
| E1 | **Mevcut yazılım/hizmet harcaması** | «Bugün tahmin, izleme ya da uzlaştırma için ödeme yaptığınız yazılım/hizmet var mı? Fatura kaleminin adı ne, neye göre hesaplanıyor?» (= D5/S15) | `harcama_kalemi` (ad), `harcama_birimi` (müşterinin kelimesi), tutar yalnız müşteri söylerse | birim seçeneği önerilmez; tutar istenmez |
| E2 | **Bütçe sahibi** | «Böyle bir hizmetin bütçesi hangi birimde durur; kim imzalar?» (= D6) | `butce_sahibi_rolu` (unvan düzeyi; ad yok) | — |
| E3 | **Onay süreci** | «En son bir yazılım/veri hizmeti alımında adımlar neydi, ne kadar sürdü, pilot yapıldı mı?» (= S16) | `onay_adimlari`, `onay_suresi_hafta`, `pilot_yapildi` | — |
| E4 | **Kabul edilebilir yapı** (açık uçlu, sonra kart) | önce: «Böyle bir hizmetin bedeli sizce neye göre hesaplanmalı?» — yanıt alındıktan sonra **sayısız** üç yapı kartı gösterilir: (a) santral başına aylık, (b) yönetilen MW başına aylık, (c) sabit platform + santral/MW dilimi + modül (PVQuant formülü). «Hangisi sizin işinize uyar, neden?» | `tercih_yapi` (a/b/c/başka), `gerekce_aynen` | kartlar rakam içermez; formül ilk önce söylenmez (çözümü soruya koymamak, E §7 #7) |
| E5 | **Santral ↔ MW** | «2 MW çatı ile 100 MW arazi santralini aynı hizmette nasıl fiyatlamak adil olur?» | `santral_mw_tercihi` + gerekçe | «MW başına» tek başına kullanılmaz (Faz 6 00 §4) — müşteri derse not |
| E6 | **Kurulum ücreti** | «Kurulum/entegrasyon için tek seferlik bir bedel ödediğiniz hizmet oldu mu? Kim yaptı işi?» | `kurulum_ucreti_kabul` (geçmiş davranış), `kurulum_kim` | hipotetik «öder misiniz» sorulmaz |
| E7 | **Sözleşme süresi** | «Yazılım hizmetlerinde aylık mı, yıllık mı sözleşme yapıyorsunuz? Son örnek?» | `sure_tercihi` | — |
| E8 | **Satın alma engelleri** | «Dış bir yazılımı kullanmanızı en son ne engelledi ya da geciktirdi?» (BT güvenlik, veri paylaşımı, KVKK, yabancı para birimi, referans isteği, grup merkezi onayı, kurum içi geliştirme) | `engel_turu` (çoklu), `engel_aynen` | seçenekler yalnız müşteri tıkanırsa okunur |
| E9 | **Rakip/ikame ödeme** (yalnız müşteri açarsa) | «Bu işi bugün yapan hizmet için ne tür bir bedel ödeniyor — gömülü mü, ayrı mı?» | `ikame_bedel_turu` (gömülü/ayrı/yok) | rakip adı sorulmaz (E §7 #9); H16 |

Hepsi geçmiş davranış ya da yapı tercihi sorar; **«ayda X öder misiniz?» yok** (E §7 #2). Kayıt alanları `05` CSV'ye `not` sütunu yerine ayrı satırlar (soru_no E1–E9) olarak girer.

## 4. Teklif doğrulama deneyleri (yalnız kullanıcı onayıyla; gönderilmez)

| # | Deney | Nasıl | Ölçülen | Sonuç nereye |
|---|---|---|---|---|
| T1 | **Formüllü teklif mektubu** | §6 şablonu: bileşenler, dilim, modül listesi, süre, kabul ölçütleri (06/07), 08 raporu, veri/gizlilik; **sayılar görüşme sonrası kullanıcı tarafından doldurulur** | teklif istendi mi (basamak 2), yanıt süresi, kabul/ret, ret gerekçesi (fiyat / yapı / değer / zamanlama / yetki) | 10 dönüşüm, 11 puan kartı |
| T2 | **İki yapı, bir kuruluş** | aynı kuruluşa (a) santral-dilim ağırlıklı ve (c) hibrit yapı iki ayrı formül özetiyle (sayısız) sunulur; hangisini anladığı ve tercih ettiği kaydedilir | anlaşılırlık, tercih, soru sayısı | 04 dilim/yapı kararı |
| T3 | **Pilot → ücretli teklif** | pilot kabul kontrol listesi (06/07) imzalandıktan sonra 14 gün içinde (ÖNERİ) T1 teklifi | kabul oranı (hedef yazılmaz; gözlenir), itiraz türü | 10 |
| T4 | **İtiraz sınıflaması** | her ret/ erteleme: ürün itirazı ↔ bütçe/satın alma/veri/entegrasyon engeli (10'daki ayrım) | dağılım | 12 risk sicili |

Deneylerde «indirim» ya da «ilk müşteri fiyatı» önerilmez (dürüstlük: fiyat seviyesi kanıtsızken indirim anlamsız); teklif tek sürüm.

## 5. Dış çapalar (yalnız iç referans; görüşmede SÖYLENMEZ — E §7 #3)

| Çapa | Değer (kaynaklı) | Ne gösterir | Ne göstermez |
|---|---|---|---|
| TEİAŞ RİTM merkezi tahmin bedeli 2027 | 50.000 TL + KDV / santral / yıl, **yalnız RES** | kamu «santral başına yıllık» kalıbı | GES; özel sektör fiyatı |
| Nnergix Sentinel | €540/yıl (20 sistem), €2.800/yıl (100 sistem) «başlayan» [ŞB] | sistem sayısı dilimi; tahminin hangi planda olduğu belirsiz | Türkiye |
| Steadysun SteadyWeb | «€12/ay tek site'tan başlayan» (05.12.2024) [ŞB] | site başına abonelik kalıbı | Türkiye uzlaştırma bilgisi |
| Solar-Log doğrudan pazarlama arayüzü | kWp dilimli tek seferlik lisans [ŞB] | kWp dilimi kalıbı | abonelik |
| Türkiye'de GES tahmini için yayımlanmış fiyat | **BULUNAMADI** (D §4.5, 06-rakip-urunler) | — | — |
| Aksa / Zorlu / Enerjisa / Zeros toplayıcı bedeli | yayımlanmıyor (D §4.5; K-52) | — | — |

Okuma: piyasadaki üç kalıp (site/santral dilimi · kWp/MW dilimi · hacim indirimi) Faz 6 formülüyle örtüşür; **seviye** yalnız görüşmeyle bulunur.

## 6. Teklif mektubu şablonu (formüllü; sayı alanları boş; gönderilmez)

```
Konu: PVQuant — [plan] aboneliği teklifi ([kuruluş kodu]; [tarih])
1. Kapsam: [S] santral / [M] MW (dilim [Dx]); modüller: [liste]; veri sıklığı saatlik; tahmin saatlik, 15 gün ufuk.
2. Bedel (aylık): platform [plan] = [__]; portföy dilimi [Dx] = [__] (santral) + [__] (MW); modüller = [__]; toplam = [__]. Tek seferlik kurulum/entegrasyon = [__].
   Kullanım: dış API [kademe] = [__]/ay; aşımda bildirim, ek kademe yalnız onayınızla. KDV hariç. Para birimi: [TL].
3. Süre ve şartlar: [aylık/yıllık]; başlangıç [tarih]; fesih [__ gün] bildirimle; pilotta doğrulanan kabul ölçütleri (06/07 raporu [kimlik]) ekte.
4. Ne vaat edilir / edilmez: yayın damgalı tahmin, bağımsız doğrulama raporu, KGÜP önerisi ve beyan izi, mutabakat; **tasarruf, kazanç ya da sonuç garantisi yok**;
   geriye dönük analiz (08) «varsayımsal fark» niteliğindedir.
5. Veri ve gizlilik: veri işleme sözleşmesi; müşteri verisi müşteriye ait; kişi adı raporlarda yok.
6. Geçerlilik: [__ gün]. İmza alanı.
```
Sayı alanları «[__]» görüşmeler ve kullanıcı kararıyla doldurulur; dolduruluncaya kadar mektup **taslak** etiketlidir.

## 7. Kayıt ve puan kartı alanları (kuruluş başına; 11'e)

`harcama_kalemi, harcama_birimi, butce_sahibi_rolu, onay_adimlari, onay_suresi_hafta, pilot_yapildi, tercih_yapi, santral_mw_tercihi, kurulum_ucreti_kabul, sure_tercihi,
engel_turu, ikame_bedel_turu, teklif_istendi, teklif_tarihi, teklif_sonucu (kabul/ret/erteleme), ret_gerekcesi_sinifi, odeme_basamagi (0–5)`.

## 8. Karar kuralları ve sınırlar

- Fiyat seviyesi: en az 5 kuruluşta (ÖNERİ; E §4 «3 görüşme» asgarisinin üstü) E1–E8 tamamlanmadan sayı yazılmaz; sayı Faz 6 `04`'e kullanıcı kararıyla girer; bu belge güncellenir («görüşme sonrası» bölümü eklenir).
- Yapı kararı (dilim sınırları D1–D5, modül bedel oranları, API kademesi): T2 ve E4/E5 sonuçlarıyla; maliyet tabanı 05 ölçümleriyle (santral konumu-gün) çapraz kontrol.
- Pilot ücreti kararı (ücretsiz/ücretli) 10 ile birlikte; ücretsizse pilot sonunda T3 zorunlu.
- Sınırlar: görüşme örneklemi küçük (persona başına < 3 → gösterge); beyan edilen yapı tercihi davranış değildir; dış çapalar Türkiye GES'i için yok; grup içi geliştirme alternatifi (E-428) her büyük grupta sorulur.
- Dil: «tasarruf / garanti / kazanç / ceza» yok; indirim yok; rakip adı yok; TL yalnız müşteri söylerse ve «müşteri beyanı» etiketiyle.
