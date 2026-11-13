# 06 — Lisanslı GES pilot protokolü (Faz 8, F8-E — 13.11.2026)

> **Durum: PİLOT YOK.** Bu belge 1–2 lisanslı GES pilotu için giriş şartlarını, ölçütleri ve **önceden yazılmış** kabul eşiklerini tanımlar. Eşik sayıları **ÖNERİDİR**
> (plan onay 5): Faz 1 Solentegre geriye dönük çalışması ve Faz 3 bant sınavından türetildi; **pilot başlamadan kullanıcı onaylar**, canlı 30 günlük bağımsız doğrulama
> sonuçları (Faz 1 §6, 11.11.2026'dan beri birikiyor) geldiğinde yeniden kalibre edilir. **Teknik başarı ≠ ödeme istekliliği:** bu protokol yalnız teknik kabulü ölçer;
> ticari dönüşüm `10`, fiyat `09`, finansal geriye dönük analiz `08`. Kod değişikliği yok; ölçütler PVQuant'ın **bugün hesapladığı** metriklerle sınırlıdır (bağımsız doğrulama
> motoru `bagimsiz_dogrulama_service`: kurallar program / gün öncesi / gün içi / ufuk; metrikler WMAPE, nMAE, nRMSE, nMBE, PICP80; referanslar persistans, CLIPER, naif; kapsama; gece davranışı).

## 1. Pilotun sorusu ve ne olmadığı

| Sorulan | Sorulmayan |
|---|---|
| Gerçek bir lisanslı GES'te, **yayımlandığı anda saklanmış** PVQuant tahmini (geriye bakış yok) ölçülen üretime karşı 60 günde ne kadar doğru? Referanslara (persistans, iklimsel) göre beceri var mı? Bant kalibre mi? Tahmin KGÜP kesiminden önce **kullanılabilir** miydi? | «Dengesizlik maliyeti ne kadar düştü?» (yalnız `08` yöntemiyle, ≥2 uzlaştırma dönemi ve müşterinin önceki programıyla; pilotun kabul ölçütü DEĞİL) · «Müşteri öder mi?» (`10`) · PVQuant'ın TPYS'ye bildirim yapması (yapmaz; KGÜP öneri + müşteri beyanı) |

## 2. Giriş şartları (hepsi zorunlu; eksikse pilot başlamaz)

| # | Şart | Nasıl doğrulanır | Kaynak / not |
|---|---|---|---|
| G1 | **Gerçek, işletmedeki lisanslı GES** (EPDK üretim lisansı; YEKDEM içi/dışı fark etmez), AC ≥ 1 MW | lisans no (EPDK sorgusu; müşteri beyanı) | 03 aday; 02 §4 A |
| G2 | **Yetkili veri erişimi**: santral sahibinin yazılı izniyle saatlik üretim (SCADA / inverter bulutu / OSOS sayaç) — kaynak ve **ölçüm sınırı** (brüt AC / net veriş) yazılı | veri işleme sözleşmesi; ölçüm uygunluğu kontrolü (motor) | Faz 1 §2 dersi: `scada_hourly`'de sınır kolonu yok → protokolde yazılı tutulur |
| G3 | **Tarihsel üretim ≥ 90 gün** pilot öncesi (persistans ve bant için yeter); CLIPER referansı dönem öncesi geçmişte **aynı ayın ≥ 20 gününü** ve 7 gün eğitim ister → pratikte ≥ 12 ay tarihsel; yoksa CLIPER «hesaplanamadı», B katmanında yalnız persistans | geçmiş ölçüm yükleme | motor `cliper` koşulu |
| G4 | **Teknik künye**: DC kWp, AC kW (inverter/bağlantı sınırı), konum (enlem/boylam ±0,01°), eğim/azimut ya da izleyici, saat dilimi, devreye giriş yılı | santral kaydı; müşteri teyidi | Karapınar dersi: konum 1,15 km dışında bulunmuştu (katalog) |
| G5 | **Tahmin yayın kayıtları**: pilot boyunca her koşu yayın damgasıyla saklanır (koşu künyesi), geriye bakış yok; «program» kuralı için D-1 KGÜP kesimi (15:30) öncesi son koşu | koşu arşivi (mevcut) | Faz 1 §6 (1) |
| G6 | **Ölçülebilir üretim**: gündüz saatlerinde geçerli ölçüm kapsaması ≥ %95; bayrak sözlüğü (geçerli / kısıntı / gece üretimi / eksik); **olay kaydı** (arıza, bakım, kısıntı, YAT talimatı) müşteri tarafından girilir, aksi hâlde «tahmin hatası» sayılır (Faz 1 §6 (2) imzası) | ölçüm uygunluğu raporu; olay defteri | — |
| G7 | **Piyasa bağlamı**: UEVÇB, DSG/toplayıcı üyeliği (varsa), KGÜP'ü kimin verdiği, uzlaştırma bildiriminin kimde olduğu — yazılı; pilot süresince müşterinin **kendi** KGÜP'ü değişmez (PVQuant yalnız öneri üretir; `08` için «karar anındaki tahmin» arşivlenir) | pilot sözleşmesi eki | «mevcut süreç ↔ PVQuant destekli» karşılaştırması `08`'de |
| G8 | **Sinyal basamağı ≥ 4** (04 §5: veri paylaşımı + gizlilik + başlangıç tarihi) ve karar vericiye erişim | 05 kaydı | pilot ≠ demo |
| G9 | **Kapsam ve süre yazılı**: 60 gün (Faz 6 Pilot planı), 1–3 santral, Pilot modül seti (tohum v2609: tahmin, doğruluk — karne + bağımsız doğrulama, veri — 1 bağlantı, temel alarm, KGÜP öneri — revizyon yok; **dönem raporu ve mutabakat Standart'ta**, pilot için ayrıca açılması gerekir — Faz 6 modül istisnası kararı); fiyat/ücret `09`'a göre — bu belgede sayı yok | abonelik kaydı (Pilot, pilot_bitis) | Faz 6 |

## 3. Ölçütler (motorun hesapladığı; 60 gün, «program» kuralı esas, «gün öncesi» yanında)

Değerlendirme kümesi: gündüz saatleri (ölçüm VEYA tahmin > kapasitenin %2'si), geçerli ölçüm, olay saatleri dışlanmış; en az **30 değerlendirilebilir gün** (motor `EN_AZ_GUN`); kapasite normalizasyonu motorda **kWp (DC, santral kaydı)**; AC sınırı künyede yazılı tutulur ve raporda belirtilir (Faz 1 dersi: DC/AC ayrımı belirsizdi, nMBE'nin bir bölümü buradan).

| Ölçüt | Tanım (motor) | Ne söyler | Birincil / ikincil |
|---|---|---|---|
| **Tahmin kullanılabilirliği** | teslim günlerinin yüzde kaçında «program» kesiminden (15:30 D-1) önce yayımlanmış koşu vardı; en geç yayın saati; eksik günler | ürün KGÜP sürecine yetişiyor mu | birincil |
| **Ölçüm kapsaması / eksik veri oranı** | geçerli gündüz saati / toplam gündüz saati; bayrak dağılımı; `kapsama_dk` | veri hattı güvenilir mi | birincil |
| **WMAPE** (saatlik toplam, gündüz) | Σ\|P50−y\| / Σ y | ağırlıklı hata; **mutlak eşik yok** (bkz. §4) | ikincil (gösterge) |
| **nMAE, nRMSE** (kWp'ye) | MAE / kapasite; RMSE / kapasite | kapasiteye göre hata; büyük sapmalar | ikincil |
| **nMBE** | ortalama (P50−y) / kapasite | sistematik yön (fazla/az tahmin) | **birincil** |
| **Beceri (referansa göre)** | 1 − WMAPE / WMAPE_ref; ref = persistans (bilgi kümesi tutarlı) ve CLIPER (iklimsel + persistans) | tahmin referanstan ne kadar iyi | **birincil** |
| **PICP80, P(y<P10), P(y>P90), Winkler** | P10–P90 bandı gerçeği hangi oranda kapsıyor | bant kalibre mi | birincil |
| **Kesitler** | mevsim, üretim düzeyi (yüksek/orta/düşük gün), saat, ufuk | zayıf koşullar nerede | ikincil (rapor) |
| Gece davranışı | gece saatlerinde tahmin ≈ 0 mı | hijyen | kontrol |
| Tahmin ufku | 47–72 saat (koşu künyesi) | KGÜP için yeterli ufuk | kontrol |

## 4. Kabul eşikleri — ÖNERİ (pilot başlamadan onaylanır; canlı 30 gün sonuçlarıyla kalibre edilir)

**Referans çapaları (kanıt, taahhüt değil):** Faz 1 Solentegre 2025 geriye dönük **simülasyonu** (kalibrasyonsuz fizik modeli, ERA5 **analiz** meteosu → NWP hatası yok,
gerçek işletmede hata bundan büyük): WMAPE %25,9 (yaz %12,5, kış %49,5, düşük üretim günleri %89,8), nMAE %9,8, nRMSE %15,7, **nMBE +%6,5** (sistematik fazla tahmin;
bir bölümü ölçüm sınırı/kapasite tanımından), kapsama %99,7 (K-02). Faz 3 bant sınavı: PICP80 ∈ [70, 90] ve ≥ 30 gün → «doğrulandı» (K-04). Canlı: iki etkin santralde
40 gün çakışma, gece işi 11.11'den beri `dogrulama_sonuc` yazıyor — **canlı WMAPE/beceri sayıları bu belge yazılırken okunmadı** (F8-E sonrası ayrı okuma; 08 teslim).

| Katman | Ölçüt | Eşik (ÖNERİ) | Gerekçe | Karşılanmazsa |
|---|---|---|---|---|
| **Z — zorunlu (veri ve süreç)** | değerlendirilebilir gün | ≥ 30 / 60 | motor asgarisi; cılız örneklem yayımlanmaz | pilot uzatılır, sonuç «yetersiz veri» |
| Z | ölçüm kapsaması (gündüz) | ≥ %95 | Solentegre %99,7; canlı %94–99 | veri hattı düzeltilir; kabul ertelenir |
| Z | tahmin kullanılabilirliği («program» kesimi öncesi koşu) | ≥ %95 teslim günü | ürün vaadi: KGÜP'e yetişen tahmin | işletme hatası → kök neden, yeniden sayım |
| Z | yayın damgası bütünlüğü | %100 (geriye bakış 0) | dürüstlük anayasası | sonuç geçersiz |
| **B — birincil (doğruluk)** | beceri, persistans referansına göre | ≥ %20 | «tahmin, bugünkü değeri taşımaktan iyi» asgari anlamı; sayı Faz 1 referans tanımından türetilmiş ÖNERİ, literatür/canlıyla kalibre edilecek | «referansı geçmiyor» → pilot teknik olarak başarısız |
| B | beceri, CLIPER referansına göre | ≥ %10 (hesaplanabildiyse) | iklimsel+persistans daha zor referans | gösterge olarak raporlanır |
| B | \|nMBE\| | ≤ %5 (kWp) | Solentegre +%6,5 «sistematik» bulundu; kalibrasyon hedefi bunun altı | yön hatası → kalibrasyon talebi (çekirdek değişmez; kalibrasyon çalışması ayrı karar) |
| B | PICP80 | ∈ [70, 90] (≥ 30 gün) | Faz 3 kuralı aynen | «doğrulanmadı» etiketi; bant kullanılmaz |
| B | P(y<P10) ve P(y>P90) | her biri ∈ [5, 15] | simetri; PICP tek başına yetmez | tek yönlü sapma raporlanır |
| **G — gösterge (eşik yok, raporlanır)** | WMAPE, nMAE, nRMSE | — (Solentegre %25,9 / %9,8 / %15,7 **analiz meteosuyla**; canlı NWP ile daha yüksek beklenir) | mutlak sayı santrale, mevsime ve ölçüm sınırına bağlı; pilot başında taahhüt edilmez | kesitlerle açıklanır (kış, düşük üretim günleri) |
| G | kesit zayıflıkları | — | kış %49,5, düşük günler %89,8 Solentegre'de | müşteriye açık yazılır |

**Kabul kararı:** Z'nin tamamı + B'nin tamamı → «teknik olarak kabul»; Z tamam, B'de 1 eksik → «şartlı; eksik ölçüt ve plan yazılır»; Z eksik → «değerlendirilemedi» (başarısız değil,
yetersiz). Kabul ödeme istekliliği anlamına gelmez; dönüşüm `10`.

## 5. Kabul kontrol listesi (pilot sonunda imzalanır; iki taraf)

- [ ] G1–G9 giriş şartları başlangıçta yazılı ve karşılanmış (tarihleriyle)
- [ ] Değerlendirme dönemi, kural (program / gün öncesi), kapasite normalizasyonu ve ölçüm sınırı raporda yazılı
- [ ] Bağımsız doğrulama raporu (JSON/Excel) yayın damgalı koşulardan üretildi; tahmin kümesi ve saat kümesi özetleri (hash) kayıtlı; yeniden üretilebilir
- [ ] Z katmanı: gün sayısı, kapsama, kullanılabilirlik, bütünlük — değerleriyle
- [ ] B katmanı: beceri (persistans, CLIPER), nMBE, PICP80, P10/P90 kuyrukları — değerleriyle ve eşik karşılaştırmasıyla
- [ ] G katmanı: WMAPE/nMAE/nRMSE ve kesitler — açıklamalarıyla; en zayıf 5 gün olay kaydıyla eşlendi
- [ ] Olay kaydı eksikleri ve bunların metriklere etkisi yazılı
- [ ] Müşterinin kendi KGÜP'ü ve karar anındaki PVQuant tahmini `08` için arşivlendi (finansal analiz **bu belgede yapılmaz**)
- [ ] Vaat dili kontrolü: raporda «tasarruf / garanti / kazanç / ceza» yok; TL yok
- [ ] Kabul sınıfı: teknik kabul / şartlı / değerlendirilemedi — gerekçe; ticari sonraki adım `10`'a devir

## 6. Dış bağımlılıklar ve riskler

| Bağımlılık | Risk | Azaltım |
|---|---|---|
| NWP kaynağı (Open-Meteo üzerinden GEFS/ICON vb.; santral konumu başına indirme, gece işi) | kaynak kesintisi → koşu yok → kullanılabilirlik düşer | kullanılabilirlik ölçütü bunu yakalar; kesinti günleri raporda ayrı |
| Müşteri veri hattı (SCADA/bulut/OSOS) | eksik saat, yanlış sınır etiketi, saat dilimi | G2/G6; ölçüm uygunluğu kontrolü; kapsama eşiği |
| Olay kaydı disiplini | kısıntı/bakım tahmin hatası sayılır | G6; haftalık hatırlatma; en zayıf günler elle incelenir |
| Kalibrasyon | kalibrasyonsuz modelde sistematik sapma (Solentegre +%6,5) | nMBE eşiği; kalibrasyon ayrı karar (çekirdek değişmez) |
| Kış / düşük üretim | mutlak hata yüksek | eşikler göreli (beceri) ve yönsel (nMBE); WMAPE gösterge |
| Mevzuat takvimi | KGÜP kesimi 15:30, 15 dk uzlaştırma tarihi belirsiz | «program» kuralı 15:30'a bağlı; 15 dk pilot kapsamı dışı |
| Tek pilot | tek santralden genelleme | 1–2 pilot; sonuç «bu santralde» diye yazılır |
