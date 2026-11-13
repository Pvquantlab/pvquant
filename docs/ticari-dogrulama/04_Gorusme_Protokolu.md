# 04 — Görüşme protokolü (Faz 8, F8-D — 13.11.2026)

> **Durum: HİÇ GÖRÜŞME YAPILMADI.** Bu belge programı hazır hâle getirir; hiçbir kuruluşla iletişim kurulmadı. §9'daki taslaklar **incelemeye hazırdır, gönderilmez**
> (dış eylem yalnız açık izinle; izin listesi `14_Eylem_Plani.md`).
> Dayanak: `faz2/E_Gorusme_Rehberi.md` (28.10.2026) — 20 soru (S1–S20), 20 hipotez (H1–H20), 60 dk akış, 12 yanlı-soru tuzağı, kayıt şablonu, veri koruma **aynen geçerlidir
> ve burada tekrarlanmaz**. Bu belge ekler: brief'in yedi davranış sorusu (D1–D7), 19.10.2026 mevzuat paketinden türeyen sorular (Y1–Y8; `02` M1–M21), segment akışları,
> altı basamaklı sinyal merdiveni, problem şiddeti puanı, pilot nitelik matrisi, sentez şablonu ve iletişim taslakları. Kayıt: `05_Gorusme_Kayit_Sablonu.md` + `gorusme_kayit_sablonu.csv`.
> Dil: «tasarruf / garanti / kazanç / ceza» ve **hiçbir rakam** söylenmez (E §7 #2–#4); rakip adı sorulmaz; ürün tanıtımı yalnız ayrı ikinci görüşmede.

## 1. Hedef ve örneklem

| Ölçü | Hedef | Kaynak |
|---|---|---|
| Görüşme sayısı | **12–15 kuruluş** (brief); E §5 asgari 15 / önerilen 24 görüşme (kişi) — bir kuruluşta 1–2 kişi (karar verici + uygulayıcı, ayrı ayrı; E §7 #10) | brief; E §5 |
| Kuruluş kaynağı | `03` kısa liste 15 (öncelik 1) + yedekler (öncelik 2) | 03 §2 |
| Segment dağılımı | A 5 · B 2 (+Akfen/Eksim çok segmentli) · C 6 (1 GTŞ) · D 2 | 03 §1 |
| Persona asgari (E §5) | LS 3 ✓(5) · TC 3 (2 + yedek İş Enerji/SOCAR) · DSG 2 ✓(Limak, Enerjisa Üretim) · TP 2 ✓ · GTŞ 1 ✓(CK) · İŞ 1 (LS/B görüşmelerinde ikinci kişi) · EPC 1 (yedek Halk Enerji/Naturel) · LL 2 (kısa liste dışı: 1 kamu + 1 OSB, bilgi edinme/OSB kanalı — H15 ve D' teyidi) | E §5; 03 §2 |
| Yanlılık kuralları | «PVQuant'ı hiç duymamış» ≥1 / persona; rakip platform kullanan ≥2 (Aksa + Pure Energy/Borusan); mevcut temas ≤ 1/3 (bilinen müşteri ilişkisi yok — K-28) | E §5 |
| Süre | 6–8 hafta; haftada 2 kuruluş (3–4 kişi görüşmesi); her görüşme 60 dk + 24 saat içinde sentez | E §6, §8.3 |
| Zaman penceresi | **30.11.2026** 2027 YEKDEM başvuru son günü (M16) → A görüşmeleri bundan önce ya da hemen sonra; **~11–15.12.2026** Kasım dönemi (14907 + V=100) ilk ön/nihai uzlaştırma bildirimi (M19) → Y4 bu tarihten sonra sorulur; **≈18.12.2026** lisanssız bağlantı anlaşması revizesi (M5) → C/GTŞ'de Y5 | 02 §1 |

## 2. Brief'in davranış soruları (D1–D7) — her görüşmede, segmentten bağımsız

Kural (E §3): geçmiş davranış sorulur, gelecek niyeti sorulmaz; her yanıttan sonra «bana bir örnek gösterebilir misiniz?»; kanıt düzeyi K1/K2/K3 (E §4).

| # | Soru (görüşmecinin metni) | Neyi ölçer | E bağlantısı | Kanıt (K3 için) | Tuzak |
|---|---|---|---|---|---|
| D1 | «Santral/portföyle ilgili **en son** canınızı sıkan somut olay neydi? Ne zaman oldu, o gün ne yaptınız?» | problem var mı, hangi sıklıkta | S1, S10 | olayın tarihi + ilgili belge | yönlendirme yok; «dengesizlik» kelimesini biz söylemeyiz |
| D2 | «Bunu **nasıl fark ettiniz**: hangi rapor, ekran ya da kişi size söyledi? Kaç gün sonra?» | fark etme gecikmesi (uzlaştırma bildirimi mi, SCADA mı, DSG raporu mu) | S2, S9, S11 | raporun adı/ekranı | «fatura geldiğinde» cevabı = gecikme kanıtı |
| D3 | «**Nasıl çözdünüz** ya da çözmeye çalıştınız? Kim, hangi araçla, ne kadar sürede?» | mevcut çözüm ve yetersizliği | S4, S5, S7 | Excel/araç ekranı | çözüm önerme yok |
| D4 | «Bu olayın size **maliyeti** neydi — zaman, para, ya da başka bir şey? Kendi kelimelerinizle.» | maliyet algısı (TL varsa müşterinin sayısı; **görüşmeci rakam söylemez**) | S3, S10 | müşterinin kendi hesabı | rakamla çapalama yasak (E §7 #3) |
| D5 | «Bugün bu iş için **hangi yazılıma, hizmete ya da kişiye** ödeme yapıyorsunuz? Fatura kaleminin adı ne, neye göre hesaplanıyor?» | mevcut harcama (sinyal basamağı 3) | S15, S16 | fatura kalemi adı (tutar istenmez) | birim seçeneği önerilmez |
| D6 | «Böyle bir hizmeti **kim onaylar**? En son benzer bir alımda süreç nasıl işledi, ne kadar sürdü?» | karar verici ve satın alma süreci | S16 | süreç adımları | — |
| D7 | «Böyle bir hizmetin işe yaradığına **hangi kanıt** sizi ikna eder? En son bir tedarikçiyi hangi ölçütle değerlendirdiniz?» | pilot kabul ölçütü müşterinin ağzından (F8-E girdisi) | S8, S17 | değerlendirme raporu/metrik adı | metrik adı (MAE/WMAPE) biz önermeyiz |

## 3. 19.10.2026 paketinden türeyen sorular (Y1–Y8) — `02` §1'e bağlı

| # | Soru (Y numarası aynı zamanda hipotez kimliğidir; 05 «hipotez» sütununa Y1…Y8 yazılır) | Segment | Dayanak (02) | Destek / çürütme | Not |
|---|---|---|---|---|---|
| Y1 | «Ekim ortasından bu yana KGÜP sürecinizde bir şey değişti mi? En son ne zaman KGÜP vermediğiniz ya da sıfır verdiğiniz bir gün oldu, ne oldu?» | A (YEKDEM'de), C | M1 (YEK 23/6: KGÜP yoksa KGÜP = 0 → YEKDEM dışı) | D: değişiklik biliniyor, süreç değişti (K2) / Ç: haberi yok ya da etkilemiyor | görüşmeci hükmü anlatmaz (E §7 #8) |
| Y2 | «KGÜP'ü 15:30 sonrası GİP kapanışına kadar hiç güncellediniz mi? En son hangi gün, neden?» | A, C, D | M2 (DUY 69: +30 dk güncelleme) | D: kullanılıyor, somut gün / Ç: hiç | S5/S6 ile birleşir |
| Y3 | «TEİAŞ'tan (ya da başka bir kurumdan) program sapması ya da KGÜP üstü üretimle ilgili bir uyarı/yazı aldınız mı? Ne zaman, ne yaptınız?» | A, C | M2 (DUY 73/9: KGÜP üstü üretim uyarı → Kuruma rapor) | D: uyarı alınmış (K3: yazı) / Ç: yok | yeni yükümlülük; «yaptırım» kelimesi kullanılmaz |
| Y4 | «Kasım ayı uzlaştırma bildiriminiz geldiğinde (Aralık ortası) hangi kalemleri önceki aylarla karşılaştıracaksınız / karşılaştırdınız? Bir fark gördünüz mü?» | A, C, D | M3, M4 (14907 katsayıları, V 150 → 100; Kasım döneminden) | D: KÜPST/V değişimi fark edildi, hesaplandı (K2/K3) / Ç: fark edilmedi | **11–15.12.2026'dan önce sorulmaz**; katsayılar söylenmez |
| Y5 | «Lisanssız portföyünüzdeki santraller için uzaktan kontrol kurulumu ve bağlantı anlaşması revizesi (60 gün) nerede? Talimata uyulmayan miktarı nasıl hesaplıyor ve üreticiye nasıl yansıtıyorsunuz?» | C (toplayıcı/GTŞ) | M5 (DUY 75/4, 104/107, LÜY Ek 4, Geçici 14; 14909) | D: süreç kuruluyor, hesap yöntemi var / Ç: haberi yok ya da dağıtım şirketine bırakıyor | TELMT/KGÜP ilişkisi: ürün boşluğu notu (15 §14) |
| Y6 | «2027 YEKDEM başvurusu (30 Kasım) için kararı kim, hangi hesapla verdi/veriyor? Çıkmayı düşündüğünüz bir tesis var mı; o hesapta dengesizlik ne kadar yer tuttu?» | A | M16 | D: hesap yapılmış, dengesizlik kalemi var / Ç: otomatik devam | 30.11 öncesi/sonrası ifade uyarlanır |
| Y7 | «10 yılını dolduran lisanssız tesisler için Meclis'teki teklifle ilgili ne yaptınız — bir değerlendirme, bir hesap, bir toplantı?» | A (grup içinde lisanssız olanlar), C | M15 (TBMM 2/4042, Komisyonda) | D: değerlendirme yapılmış / Ç: izlenmiyor | «kanunlaşırsa» varsayımsalı sorulmaz (E §7 #1) |
| Y8 | «EPİAŞ Şeffaflık ya da EPYS verisini bugün hangi hesapla, kim çekiyor? En son ne zaman bir veri setine erişemediniz?» | tüm | M18 (Şeffaflık üyelik), S14 | D: kurumsal hesap + süreç / Ç: elle, kişisel hesap | PVQuant veri erişim riskinin saha teyidi |

## 4. Segment akışları (60 dk; E §6 iskeleti korunur)

| Dakika | Bölüm | **A — Lisanslı GES sahibi (LS/İŞ)** | **B — Portföy/O&M (İŞ/EPC)** | **C — Toplayıcı/DSG/GTŞ (TP/DSG/GTŞ)** | **D — Ticaret (TC/DSG)** |
|---|---|---|---|---|---|
| 0–5 | Açılış, izin, anonimleştirme | ortak (E §6) | ortak | ortak | ortak |
| 5–10 | Rol ve bağlam | santral sayısı/MW aralığı, YEKDEM yılı, DSG/toplayıcı üyeliği, kurum içi masa var mı | portföy büyüklüğü aralığı, sözleşme türü (O&M/varlık yönetimi), müşteri sayısı aralığı | lisans tarihi, üye tipi (lisanslı ≤100 MW / 10 yılı dolan lisanssız / tüketici), GTŞ bölgesi | portföy tipi (kendi/üçüncü taraf), DSG rolü |
| 10–25 | Günlük iş akışı | S1, S4, S5, Y2, S18 | S1, S14, S18; yedek İŞ sorusu (arıza kaydı/ay) | S1, S4 (üyelerden program nasıl geliyor), Y2, Y5 | S1, S6, Y2, S7 |
| 25–40 | Problem ve uzlaştırma | **D1–D4**, S2, S3, S9, S10, Y1, Y3, (Y4) | **D1–D4**, S2 (müşteri adına kontrol), S17 (müşteri raporu) | **D1–D4**, S11, S12, S13, Y1, Y3, (Y4) | **D1–D4**, S3, S9, S11, (Y4) |
| 40–50 | Araçlar, sağlayıcılar, ödeme | S7, S8, S14, **D5, D6**, S16 | S8, S14, **D5, D6** | S7, S8, **D5, D6**, S15 | S7, S8, **D5, D6**, S15 |
| 50–55 | Gelecek ve karar | Y6, Y7, S20, **D7** | **D7**; S19 (kamu ihalesi kazanmış EPC'de); yedek EPC sorusu (performans garantisi raporu) | Y7, S20, **D7** | S20, **D7** |
| 55–60 | Kapanış, bağlılık | «başka kiminle konuşmalıyız»; uzlaştırma verisi paylaşımı (anonim karşılaştırma) | O&M müşterisine yönlendirme | üye santral verisi paylaşımı (üye izniyle) | portföy verisi paylaşımı |
| Yapılmayacak | | mevzuat saatlerini/hükümlerini anlatmak; «ceza»; rakam | ürün karşılaştırması | katsayı söylemek; sözleşme bedeli sormak | fiyat önermek |

Görüşülen kişi: A'da enerji/ticaret-finans yöneticisi + (ikinci) santral işletme; B'de işletme müdürü/performans mühendisi; C'de dengeleme-uzlaştırma ekibi + portföy yöneticisi;
D'de ticaret masası/portföy riski (02 §4 «Kim»). Kişi adı hiçbir dosyaya yazılmaz (E §8.4).

## 5. Sinyal merdiveni (altı basamak) — ödeme isteği sözle değil davranışla

| Basamak | Sinyal | Nasıl kanıtlanır | Kanıt düzeyi | E §4 merdiveni | Puan kartına (11) |
|---|---|---|---|---|---|
| 1 | **Beyan edilen ilgi** («güzel olur», «kullanırız») | sözlü | K1 | 0 | sayılmaz (gösterge) |
| 2 | **Gösterilen problem** | D1–D4'te tarihli somut olay (K2) ya da belge/ekran (K3) | K2/K3 | — | «problem gösterildi» sayısı |
| 3 | **Mevcut harcama** | D5/S15: tahmin/izleme/uzlaştırma için bugün ödenen fatura kalemi (ad; tutar istenmez) ya da kişi-gün emeği | K2/K3 | — | «ödeyen» sayısı |
| 4 | **Pilot taahhüdü** | kendi EPYS/SCADA verisini paylaşma, gizlilik sözleşmesi, pilot başlangıç tarihi | K3 (imzalı/yazılı) | 1 | pilot aday sayısı |
| 5 | **Satın alma sürecine katılım** | bütçe sahibiyle ikinci görüşme ayarlandı; satın alma/BT soruları geldi; teklif istendi | K3 | 2 | teklif istenen sayısı |
| 6 | **Gerçek taahhüt** | niyet mektubu, imzalı sözleşme, fiili ödeme | K3 | 3–4 | ücretli dönüşüm (10) |

Kural: basamak ≥2 olmadan 3+ aranmaz; her görüşme kaydında basamak sayısı tek sayı olarak yazılır; iltifat kanıt sayılmaz (E §7 #11).

## 6. Problem şiddeti puanı — yalnız K2/K3 kanıtıyla

**Puan = Sıklık (1–3) × Maliyet (1–3) × Mevcut çözümün yetersizliği (1–3)** → 1–27. K1 (yalnız söz) ile puanlanmaz, «gösterge» yazılır.

| Boyut | 1 | 2 | 3 | Soru |
|---|---|---|---|---|
| Sıklık | yılda bir–iki | ayda bir (uzlaştırma döngüsü) | haftada bir ve daha sık (günlük KGÜP) | D1, S2, S5 |
| Maliyet (müşterinin kendi ölçüsüyle) | «önemsiz»; kimse zaman ayırmıyor | her ay kişi-gün harcanıyor ya da müşteri bir TL tutarı **kendisi** söylüyor | yönetim/finansa raporlanan kalem; gelir kaybı ya da idari sonuç riski (TEİAŞ uyarısı, YEKDEM dışı kalma) | D4, S3, Y3, Y1 |
| Mevcut çözümün yetersizliği | çözülmüş (araç var, memnun) | elle/Excel; geç fark ediliyor | çözüm yok ya da dış hizmetle de çözülmüyor; itiraz/kayıp yaşandı | D2, D3, S7, S9 |

Eşikler (**öneri; görüşmelerden sonra kalibre edilir, kanıt değil**): ≥ 12 → pilot adayı (nitelik matrisine); 6–11 → izle, ikinci görüşme; < 6 → bu segmentte problem zayıf → hipotez çürütme kanıtı olarak yazılır.
Her puan `05` CSV'de üç ayrı sütunda + gerekçe satırıyla tutulur; iki kodlayıcı (E §7 #12) farkı 2'den büyükse üçüncü okuma.

## 7. Pilot nitelik matrisi (F8-E'ye devir)

| Ölçüt | Zorunlu / tercih | Nasıl doğrulanır | Kaynak |
|---|---|---|---|
| Yasal yük: santral/portföy düzeyinde EDT + KÜPST taşıyor (A) ya da üye KGÜP'ü/KÜPST'ü yönetiyor (C) | zorunlu | lisans/toplayıcı durumu (EPDK), S3/S11 | 02 §4 |
| Problem puanı ≥ 12 ve sinyal basamağı ≥ 2 | zorunlu | §5–§6 | — |
| Veri erişimi: saatlik üretim (SCADA/inverter bulutu/OSOS) + EPYS uzlaştırma bildirimi + tarihsel KGÜP (≥ 2 uzlaştırma dönemi) | zorunlu (F8-F girdi şartnamesi) | S14, Y8; yetkili kişi | 08 |
| Karar vericiye erişim (D6) | zorunlu | ikinci görüşme ayarlandı | §5 basamak 5 |
| Zaman penceresi: YEKDEM çıkışı 2026–2028 ya da yeni yükümlülük (M1/M5) | tercih | YEK listesi (K-49) | 03 |
| Segment kotası: lisanslı GES 1–2, toplayıcı/DSG 1 | kota | 03 kısa liste | brief |
| Rakip platform kullanıyor | tercih (karşılaştırma değeri) | S7 | E §5 |
| «Teknik başarı ≠ ödeme istekliliği» kabulü yazılı | zorunlu | pilot protokolü (06/07) | F8-E |

Sonuç: **nitelikli / izle / değil** + gerekçe satırı (05 §3).

## 8. Sentez şablonu

1. **Görüşme sonrası 24 saat** (E §8.3): saat saat akış; araçlar; H1–H20 + Y1–Y8 durumu (DESTEK/ÇÜRÜTME/NÖTR/SORULMADI); D1–D7 özeti; sinyal basamağı; şiddet puanı (3 boyut + gerekçe); nitelik sonucu; yeni hipotez; açık soru bağlantısı (E §9).
2. **Haftalık segment sentezi:** segment başına «gösterilen problem» listesi (anonim), ortak kalıplar (≥2 görüşmede), çürütmeler, kelime sözlüğü (müşterinin kendi terimleri — ürün dili için).
3. **Program sonu (15 §4–§6 girdisi):** hipotez tablosu (E §4 eşikleri: DESTEK ≥%60 K2/K3 + ≥3 K3; ÇÜRÜTME ≥%50); segment × problem şiddeti dağılımı; sinyal merdiveni dağılımı; pilot adayları (nitelik); F8-F için veri sağlayan kuruluş sayısı; F8-G için mevcut harcama kalıpları (adlar, birimler — tutar yoksa yok yazılır).
4. **Dürüstlük kuralı:** görüşme sayısı persona başına 3'ün altındaysa sonuç «gösterge»; hiç görüşme yoksa 15'te «Henüz yapılmadı — hazır: 04/05».

## 9. Dış iletişim taslakları — İNCELEMEYE HAZIR, GÖNDERİLMEZ

Kanal: kurumsal iletişim sayfası / kurumsal e-posta (03'teki iletişim kanalı sütunu) ya da yatırımcı ilişkileri; kişi adı yok. Gönderim yalnız kullanıcı onayıyla, kuruluş kuruluş (14).

**E-posta taslağı (A/C/D; 120 kelime):**
> Konu: Güneş santrali üretim programı ve uzlaştırma süreçleri üzerine 45 dakikalık görüşme talebi
>
> Merhaba,
> PVQuant, lisanslı güneş santralleri ve toplayıcı portföyleri için üretim tahmini ve uzlaştırma takibi üzerine çalışan bir Türk yazılım ekibidir. Ekim 2026 mevzuat
> değişikliklerinden sonra santral sahiplerinin ve toplayıcıların günlük KGÜP ve aylık uzlaştırma işlerini **nasıl yürüttüğünü** anlamak için sektörden 12–15 kuruluşla
> görüşmeyi planlıyoruz. Bu bir satış görüşmesi değildir; ürün tanıtımı yapmayacağız. 45–60 dakikalık bir görüşmede, bu işleri yürüten ekibinizden bir kişiyle çalışma biçiminizi
> öğrenmek istiyoruz. Görüşme notları anonimleştirilir; söyledikleriniz raporlarda kuruluşunuzun adıyla eşlenmez; kayıt yalnız izninizle alınır.
> Uygun bir zaman ve kişiyi yönlendirebilirseniz seviniriz.
> Saygılarımızla, PVQuant ekibi · pvquant.com

**B (O&M/portföy) varyantı:** «üretim tahmini ve uzlaştırma» → «çok santralli portföylerde performans takibi ve müşteri raporlaması».
**Arama senaryosu (90 sn):** kimlik + amaç (öğrenme, satış değil) + süre + anonimlik + «bu işi kim yürütüyor, kime yönlendirirsiniz?» — rakam, vaat, ürün özelliği yok.
**Kamu/OSB (LL):** bilgi edinme ya da resmî yazı gerektirebilir (E §5) → ayrı taslak 14'te, izinle.
**Yasak:** kişisel e-posta/LinkedIn mesajı kişi adıyla; «tasarruf», «ceza», «garanti»; herhangi bir TL/%; rakip adı; «pilot ücretsiz» vaadi (fiyat kararı 09/Faz 6).

## 10. Risk ve sınırlar

- Görüşme ≠ talep kanıtı: yalnız basamak ≥ 4 ve puan ≥ 12 pilot adaylığı doğurur; sonuçlar 11 puan kartında «gösterge/destek» ayrımıyla yazılır.
- Erişim riski: kurumsal gruplar (Kalyon, Enerjisa, Limak, İş) için soğuk e-posta dönüş oranı bilinmiyor → yedek liste ve ikinci dalga (03 §2) hazır.
- Takvim riski: 30.11 ve Aralık uzlaştırma pencereleri kaçırılırsa Y4/Y6 bir sonraki döneme kayar.
- Teyit yanlılığı: iki kodlayıcı; her hipotez için zorunlu «çürütme kanıtı» alanı (05).
