# 07 — Toplayıcı / DSG pilot protokolü (Faz 8, F8-E — 13.11.2026)

> **Durum: PİLOT YOK.** Bir toplayıcı ya da DSG portföyü (1 portföy) için giriş şartları, ölçütler ve **önceden yazılmış** kabul eşikleri. Eşikler **ÖNERİDİR**, pilot
> başlamadan kullanıcı onaylar (plan onay 5). Dayanak: Faz 3 portföy yöntemi (bottom-up P50; Schäfer–Strimmer büzülmüş korelasyonla σₚ² = Σ ρᵢⱼ σᵢ σⱼ; naif kantil toplamı
> hiçbir yerde portföy aralığı olarak sunulmaz; PICP80 / P(y<P10) / P(y>P90) / Winkler sınavı; DSG üç perspektif; etiket «Sözleşmeye dayalı dağılım» yalnız doğrulanmış üyelik +
> belgeyle, aksi «Varsayımsal maliyet dağılımı») — K-04, Faz 3 08 §4–§5. **Karar desteği ≠ otomatik piyasa emri:** PVQuant TPYS'ye bildirim yapmaz, GİP/GÖP emri vermez,
> DSG faturası kesmez; çıktılar öneri ve rapordur. **Teknik başarı ≠ ödeme istekliliği** (dönüşüm `10`).

## 1. Pilotun sorusu

| Sorulan | Sorulmayan |
|---|---|
| Gerçek bir toplayıcı/DSG portföyünde (≥ 3 GES) 60 günde: portföy P50 toplamı ve ρ-yöntemiyle P10/P90 bandı gerçeğe karşı kalibre mi (PICP80)? Üye bazında karne ve portföy katkı ayrışımı tutarlı mı? DSG üç perspektifi (bağımsız / DSG içi / netleşme farkı) müşterinin kendi hesabıyla mutabık mı? Üyelik ve sözleşme doğrulaması ne oranda «sözleşmeye dayalı» etiketi alıyor? | DSG içi paylaşımın TL sonucu (yalnız `08`, resmî bildirimle) · üye kazanımı/fiyat (`09`) · talimat/TELMT uzlaştırması (ürün yok — 03 §6) · otomatik piyasa işlemi |

## 2. Giriş şartları (zorunlu)

| # | Şart | Nasıl doğrulanır | Not |
|---|---|---|---|
| G1 | **Toplayıcı lisansı ya da DSG yöneticiliği** gerçek ve yürürlükte (EPDK toplayıcılık lisansı no / EPİAŞ DSG kaydı) | EPDK sorgusu (49 lisans listesi, K-40); müşteri beyanı | 03 segment C |
| G2 | **Portföy tanımı**: ≥ 3 GES (lisanslı ya da lisanssız — lisanssızda KGÜP toplayıcı UEVÇB'sinden, M5), her santral için teknik künye (06 G4) ve **üyelik tarihleri** (giriş/çıkış) | portföy + üyelik kayıtları (Faz 3 varlık modeli: aynı santral aynı tarihte iki DSG'de olamaz; toplayıcı ↔ DSG dışlaması DUY 20/4) | üyelik değişimi dönem içinde not düşer |
| G3 | **Sözleşme kalıbı** yazılı (paylaşım formülü / sabit fiyat / alt grup; bedel istenmez) ve **uzlaştırma sorumluluğu**: EDT'yi kim taşıyor (toplayıcı mı, üye mi), KÜPST üye bazında mı | sözleşme özeti (belge) → «Sözleşmeye dayalı dağılım» etiketi; yoksa tüm dağılım «Varsayımsal» | Faz 3 etiket kuralı; E §9 (kalıp türü yeterli) |
| G4 | **Veri yetkisi**: her üye santral için sahibin yazılı izni (üretim verisi + KGÜP + uzlaştırma bildirimi paylaşımı); toplayıcı adına tek yetki yetmez | veri işleme sözleşmesi + üye izin listesi | kişi adı yok |
| G5 | **Tarihsel veri**: üye başına ≥ 60 gün gün öncesi tahmin artığı için ölçüm (ρ tahmini: en az 14 ortak gün; yoksa ρ = 1 ihtiyatlı ve «yetersiz veri») | ölçüm yükleme | Faz 3 §4 |
| G6 | **Portföy KGÜP'ü ve uzlaştırma bildirimi**: toplayıcının portföy/UEVÇB bazında KGÜP arşivi ve EPİAŞ bildirimi (≥ 2 dönem) `08` için | belge | 08 girdi şartnamesi |
| G7 | **Tahmin yayın kayıtları** (06 G5) her üye için; portföy koşusu ortak yayın kuralıyla | koşu arşivi | — |
| G8 | **Sinyal basamağı ≥ 4**, karar verici erişimi; «karar desteği, emir değil» yazılı kabul | 05 kaydı; pilot sözleşmesi | — |
| G9 | Kapsam: 60 gün, 1 portföy, Standart/Kurumsal modül seti (portföy tahmini, DSG/paylaşım, üye karnesi, KÜPST, mutabakat; dış API isteğe bağlı); fiyat `09` | abonelik kaydı | Faz 6 |

## 3. Ölçütler (Faz 3'te var olanlar)

| Ölçüt | Tanım | Birincil / ikincil |
|---|---|---|
| **Portföy P50 doğruluğu** | portföy toplamı WMAPE / nMAE (Σ kapasite); yanında «üye P50'lerin toplamı» ile aynı (bottom-up) olduğu kontrolü | gösterge (eşik yok) |
| **Bant kalibrasyonu** | PICP80, P(y<P10), P(y>P90), Winkler — portföy toplamı, son 30+ gün; naif (ρ=1) ve bağımsız (ρ=0) sınırlar yanında | **birincil** |
| **Korelasyon güvenilirliği** | korelasyon durumu (hesaplandı / «yetersiz veri» → ρ = 1 varsayımı; portföy düzeyinde, motor), ortak gün sayısı; ρ örneklem içi uyarısı | birincil (veri) |
| **Üye karnesi tutarlılığı** | üye bazında WMAPE/nMBE/PICP (06 ölçütleri) ve portföy katkı ayrışımı (hangi üye ne kadar katkı) toplamı portföy sapmasına eşit | birincil |
| **Net sapma (DSG)** | Σ bağımsız dengesizlik − DSG içi dengesizlik = netleşme farkı; %5 üye eşiği uygulaması; aylık | **birincil (DSG pilotunda)** |
| **Risk göstergesi** | portföy belirsizliği (P90−P10)/Σ kapasite; yüksek belirsizlik saatleri; revizyon önerisi sayısı | ikincil |
| **Finansal dağılım güvenilirliği** | «Sözleşmeye dayalı dağılım» etiketli dönem/üye oranı vs «Varsayımsal»; resmî EPİAŞ bildirimiyle mutabakat farkı (nitelik: resmî › hesaplanan) | **birincil** |
| **Kullanılabilirlik** | portföy koşusu teslim günü KGÜP kesimi öncesi hazır mı; eksik üye/saat listesi (0 sayılmaz) | birincil |
| Veri bütünlüğü | üye ölçüm kapsaması, eksik saat, olay kaydı | zorunlu |

## 4. Kabul eşikleri — ÖNERİ (onay sonrası geçerli)

| Katman | Ölçüt | Eşik (ÖNERİ) | Gerekçe |
|---|---|---|---|
| **Z — zorunlu** | değerlendirilebilir gün | ≥ 30 / 60 | Faz 3 «≥ 30 gün» |
| Z | üye ölçüm kapsaması | her üyede ≥ %95; eksik üye günleri listeli | 06 Z |
| Z | portföy koşusu kullanılabilirliği | ≥ %95 teslim günü | 06 Z |
| Z | üyelik doğrulaması | tüm üyeler tarihli; «Varsayımsal» etiket oranı raporlanır | Faz 3 etiket kuralı |
| **B — birincil** | PICP80 (portföy, ρ yöntemi) | ∈ [70, 90] | Faz 3 kuralı (sentetikte %72–88) |
| B | P(y<P10), P(y>P90) | her biri ∈ [5, 15] | simetri |
| B | bant naif toplamdan dar, bağımsızdan geniş | evet (ρ ∈ (0,1) ise) | yöntem tutarlılığı; ihlal = veri/ρ sorunu |
| B | korelasyon durumu | 30. günden sonra «yetersiz veri» değil (ortak gün ≥ 14, ρ hesaplandı) | G5 sağlanıyorsa; durum portföy düzeyinde |
| B | üye katkı ayrışımı toplamı = portföy sapması | fark ≤ %1 | muhasebe tutarlılığı |
| B | DSG netleşme farkı mutabakatı (DSG pilotu) | müşterinin kendi aylık hesabıyla üye bazında fark ≤ %5 ya da fark açıklanmış | «resmî › hesaplanan» niteliği |
| B | üye başına beceri (persistans) | ≥ %20 üyelerin ≥ 2/3'ünde | 06 B |
| **G — gösterge** | portföy WMAPE/nMAE, risk göstergesi, revizyon önerisi isabeti | — | raporlanır; eşik yok |

Kabul kararı 06 §4 ile aynı (Z tam + B tam → teknik kabul; B'de 1 eksik → şartlı; Z eksik → değerlendirilemedi). DSG pilotunda «net sapma mutabakatı» eksikse teknik kabul verilmez
(ürünün DSG vaadi budur).

## 5. Kabul kontrol listesi

- [ ] G1–G9 başlangıçta yazılı; üyelik tarihleri ve sözleşme kalıbı kayıtlı; «Sözleşmeye dayalı» etiket oranı başlangıçta hesaplandı
- [ ] Portföy ve üye koşuları yayın damgalı; ortak yayın kuralı; eksik üye/saat listesi raporda (0 sayılmadı)
- [ ] Z katmanı değerleriyle
- [ ] B katmanı: PICP80 + kuyruklar + naif/bağımsız sınırlar + ρ güvenilirliği + ayrışım tutarlılığı + (DSG) net sapma mutabakatı + üye beceri — değerleriyle
- [ ] Üye bazlı karne üyelerle paylaşıldı mı (toplayıcının kararı; PVQuant paylaşım formülü yalnız sözleşme kalıbıyla)
- [ ] «Karar desteği ≠ emir» ihlali yok (hiçbir TPYS/GİP işlemi PVQuant'tan)
- [ ] Vaat dili kontrolü (tasarruf/garanti/kazanç/ceza/TL yok); talimat/TELMT kapsam dışı yazıldı
- [ ] `08` girdileri arşivlendi (portföy KGÜP, bildirimler, karar anındaki tahminler)
- [ ] Kabul sınıfı + gerekçe; dönüşüm `10`

## 6. Dış bağımlılıklar

| Bağımlılık | Risk | Azaltım |
|---|---|---|
| Üye izinleri (G4) | bir üye izin vermezse portföy eksik | portföy eksik üyeyle «kısmi» raporlanır; 0 sayılmaz |
| EPİAŞ Şeffaflık/EPYS erişimi (üyelik; M18) | resmî bildirim ve veri çekimi müşteri hesabına bağlı | müşteri dışa aktarır; API anahtarı yöntemi teknik risk (12) |
| DSG faturası biçimi bilinmiyor (Faz 3 sınır) | mutabakat elle | kalem eşleme tablosu pilotta çıkarılır (08'e girdi) |
| Lisanssız üyeler: KGÜP toplayıcı UEVÇB'sinde, KÜPST m 0,25 / n 0,01, talimat/TELMT (M5) | PVQuant talimat uzlaştırmasını hesaplamaz | kapsam dışı yazılı; 15 §14 ürün boşluğu |
| ρ örneklem içi; GEFS üye bazlı senaryo yok | bant iyimser olabilir | PICP sınavı; meta uyarısı raporda |
| NWP / veri hattı | 06 §6 ile aynı | — |
| Rakip platform (smartPulse vb.) yan yana | karşılaştırma isteği | yalnız müşterinin kendi verisiyle; rakip adı raporda yok |
