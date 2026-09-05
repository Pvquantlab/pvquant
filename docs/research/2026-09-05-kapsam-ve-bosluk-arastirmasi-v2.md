# PVQuant Kapsam ve Boşluk Araştırması — Eylül 2026

> **Amaç:** `pvquant_ult` referans klasörü (NREL hakem seti + üç sektör belgesi), dış kaynaklar (rakip SaaS'lar, iklim veri setleri, standartlar, tahmin bilimi literatürü) ve deponun kendisi üzerinden PVQuant'ın **nerede sektör standardında, nerede ileride, nerede eksik** olduğunu saptamak; profesyonel seviye için önceliklendirilmiş bir yol haritası çıkarmak.
> **Yöntem:** Yerel dosyalar okundu ve ölçüldü (NREL setinde 7 eyalet / 1.468 santral-tahmin çifti üzerinde kıyas hesabı), depo koddan envanterlendi, üç paralel araştırma hattı (rakipler · veri/standartlar · tahmin bilimi) yürütüldü; kritik iş bulguları (lisans) birincil kaynaktan teyit edildi.
> **Kırmızı çizgi korunur:** Bu belge yalnız araştırma ve öneridir; model çekirdeğine (`models_v2/hybrid_residual.py`) dokunulmadı, her öneri ayrı onayla uygulanır.

---

## 0. Yönetici özeti — beş cümle

1. **Çekirdek doğru sınıfta:** fizik-öncelikli hibrit (Barhdadi-Bennis + LightGBM rezidüel) 2023–2025 literatürünün "gray-box" konsensüsüyle örtüşüyor; bifacial'ı açıkça modelleyen ve **60 günlük gece sınavıyla kendini ölçen** bir ürün ticari araçların çoğundan ileride.
2. **En acil iş bir özellik değil, bir lisans:** ürün tüm meteorolojiyi Open-Meteo'nun **ücretsiz (ticari kullanım dışı)** katmanından çekiyor; 20 yıllık iklim arşivi de "Historical API" — ticari plan gerektiren uç nokta. Bir SaaS için bu, profesyonelleşmenin birinci maddesi.
3. **Manşet çıktımız denetimsiz:** P10/P50/P90 üretiyoruz ama **kalibrasyonunu ölçmüyoruz** (reliability, pinball, CRPS yok) ve belirsizliğin ana kaynağı olan NWP tek deterministik kaynaktan geliyor — ensemble/harman yok.
4. **Türkiye'de ticari değerin adı dengesizlik:** KGÜP/DUY mekanizmasında saatlik tahmin hatası doğrudan paradır; ürün bunu henüz TL cinsinden göstermiyor — en güçlü satış argümanı ve en büyük farklılaşma fırsatı burada.
5. **Referans hakem seti elimizde:** NREL setinde gün-öncesi tahmin hatası eyaletlere göre WMAPE %19–30 (nMAE %8,5–12,4); canlı karnemiz (0–24s %5,4) güçlü bir banda düşüyor — ama elma-elma kıyas için metrikleri Solar Forecast Arbiter standardına oturtmamız şart.

---

## 1. Referans klasörünün envanteri ve okunuşu

### 1.1 `büyükveri` — NREL "Solar Power Data for Integration Studies" (2006)
- 52 zip, ~2,3 GB; her eyalet için sentetik PV santralleri (**DPV** dağıtık ~120 / **UPV** şebeke ölçeği ~46 örnekte; kapasite 7–100 MW, medyan 38 MW).
- Her santral üçlü: **Actual** (5 dk gerçekleşen), **DA** (gün-öncesi saatlik tahmin), **HA4** (4 saat öncesi saatlik tahmin).
- Değeri: bağımsız, herkese açık, tahmin+gerçekleşen bir arada → **karne motorumuzun dış doğrulaması** ve **referans tahmin kalibrasyonu** için hazır hakem.
- Sınırı: 2006 yılı, 2006 dönemi NWP kalitesi, ABD iklimi; mutlak sayılar bugünün Türkiye santrallerine taşınmaz, **metrik disiplini** taşınır.

**Ölçtüğümüz kıyas çubuğu** (gündüz saatleri: gerçekleşen ya da tahmin > %1 kapasite; saatlik ortalama):

| Eyalet | Ufuk | Santral | WMAPE % | nMAE % | nRMSE % | nMBE % |
|---|---|---|---|---|---|---|
| Arizona | DA | 171 | 19,4 | 8,8 | 14,0 | +1,6 |
| Arizona | HA4 | 171 | 15,0 | 6,8 | 10,2 | −0,5 |
| California | DA | 405 | 24,5 | 9,9 | 15,1 | +2,6 |
| California | HA4 | 405 | 17,0 | 7,0 | 10,1 | −0,3 |
| Colorado | DA | 88 | 29,8 | 12,4 | 18,6 | +2,8 |
| Colorado | HA4 | 88 | 21,0 | 8,7 | 12,7 | +0,3 |
| Connecticut | DA | 29 | 27,8 | 8,8 | 12,8 | +0,2 |
| Connecticut | HA4 | 29 | 26,4 | 8,4 | 12,8 | +0,8 |
| Florida | DA | 593 | 22,9 | 8,5 | 12,3 | +0,4 |
| Florida | HA4 | 593 | 21,6 | 8,1 | 12,2 | +1,6 |
| New York | DA | 129 | 30,4 | 9,3 | 12,9 | 0,0 |
| New York | HA4 | 129 | 28,7 | 8,9 | 13,3 | +0,5 |
| Texas | DA | 53 | 22,3 | 9,0 | 13,6 | +0,5 |
| Texas | HA4 | 55 | 23,3 | 9,6 | 14,5 | −0,9 |

Okunuşu: (a) kuru/açık iklimde (AZ) hata düşük, bulutlu/kıtasal iklimde (CO, NY) yüksek — coğrafya hatayı yönetir; (b) 4 saat öncesi tahmin gün-öncesinden tutarlı biçimde iyi — **kısa ufuk (nowcasting) katmanının değeri** burada nicel; (c) kapasiteye normalize nMAE/nRMSE, WMAPE'den çok daha kararlı bir kıyas dili — bizim karnenin ikinci dili olmalı.

### 1.2 Solar Forecast Arbiter (AMS 2021 posteri)
DOE'nin açık kaynak, **tarafsız** tahmin değerlendirme çerçevesi. Öğrettiği ilkeler: metadata-önce kayıt (site/gözlem/tahmin nesneleri), **referans tahminler** (persistence + NWP), veri doğrulama/filtreleme raporu, **standart metrik raporu** (HTML/PDF, CSV/JSON dışa aktarım), utility↔vendor arasında **rol-tabanlı veri paylaşımı**, anonim operasyonel tahmin yarışmaları. PVQuant'ın "karne" fikri aynı kültürden; eksik olan, metrik setinin ve rapor biçiminin bu standarda **birebir** oturması.

### 1.3 meteocontrol VCOM kullanıcı kılavuzu
Portföy seviyesi (kontrol odası) ↔ santral seviyesi (kokpit) ayrımı; **5 dakikada bir otomatik tazeleme**; taşınabilir portletler; turuncu/kırmızı alarm şiddeti ve kokpite inme; Excel "Solar Index" dışa aktarımı; **tarife/gelir yapılandırması** (sabit ya da zaman-bağımlı); mobil uygulama. → İzleme SaaS'larının "hijyen" seviyesi.

### 1.4 AlsoEnergy PowerTrack broşürü
Tek uygulamada izleme + **kontrol** (PPC yapılandırma, uzaktan kumanda, **BESS**), portföy toplama, CMMS/BI entegrasyonu, **12+ şablon rapor** (finansal, kapasite testi, beklenen-gerçekleşen, kayıp uyarıları, fatura), cihaz sağlığı/iletişim teşhisi, API ile veri alma-verme. → Pazarın "her şey dahil" ucu; PVQuant'ın kapsamı değil ama entegrasyon ve rapor çeşitliliği dersleri var.

---

## 2. PVQuant bugün ne? — kod-temelli envanter

| Katman | Durum (depo, v2.241) |
|---|---|
| Fizik zinciri | Erbs → Perez → Faiman/SAPM/NOCT → Barhdadi-Bennis (bifacial revize) → DC → AC; PVWatts, SAPM, De Soto, Skoplaki, view-factor bifacial katalogda (`PVQuant_Matematiksel_Modeller.docx`) |
| Hibrit | LightGBM rezidüel (saat/mevsim/POA/T_cell/kt), Mod A/B/C, holdout kapısı, zaman-bazlı split |
| Model seçimi | Karar matrisi: bifacial→BB, mono <300 kWp→PVWatts, ≥300→SAPM; 3+ ay SCADA→kalibre |
| Meteo | **Tek kaynak: Open-Meteo** (forecast + archive uç noktaları) |
| Ufuk / çıktı | 15 gün saatlik, P10/P50/P90; günlük toplamlar; aylık iklim beklentisi (20 yıl GHI → yıl-ay P10/50/90) |
| Doğruluk | skill_daily: WMAPE, RMSE, **naif referans = dün-aynı-saat × gök açıklığı (akıllı persistans)**, skill; saat×gün hata matrisi; günlük sapma dağılımı (P10/P50/P90, μ, σ) |
| Veri alımı | Akıllı SCADA parser (Türkiye formatları, 30 santral testi), bayraklama (silme yok), kalibrasyon ızgarası |
| Worker | Sabah tahmin, gece skill, günlük beklenti, rapor alanları, alarm (2 kural: veri_gelmedi 48s, skill_dustu) |
| Raporlama | 16 sayfa PDF (26 tutarlılık denetimi), Excel, JSON (şema 1.1.0) |
| Platform | FastAPI + JWT + **RLS çok kiracılı** (3 rol: viewer/editor/admin), React SPA (F kimliği, mobil, ⌘K, zil), Docker/Caddy, CI |
| Doğrulama geçmişi | NREL PVDAQ 2107 (Arbuckle CA, 893 kWp) 15 dk gerçek veriyle Faz 1.7–1.9; frekans-agnostik kalibrasyon Faz 1.6 |
| Satış tezi (deck) | "Model sizin santralınız olur" + "60 gün karne, fiyat karneye göre" |

**Bizi ayıran (GitHub'dan okunan):** (1) saha-kalibre fizik + rezidüel — çoğu SaaS ya saf istatistik ya saf simülasyon; (2) **gece sınavı kültürü** — her gece kendini ölçen, naif referansla dürüst kıyaslanan karne; (3) bifacial'ın açık modellenmesi; (4) Türkçe SCADA formatlarına özel parser; (5) veri silmeyen bayraklama ve "tire ilkesi" — dürüstlük ürünün diline işlemiş; (6) RLS ile gerçek çok kiracılılık; (7) 16 sayfalık bankable-üslup rapor.

---

## 3. Boşluk analizi — sektör standardı vs PVQuant

Ölçek: **Var** · **Kısmi** · **Yok**. Etki: ürünün ticari/bilimsel değerine katkı. Zorluk: mühendislik eforu (çekirdeğe dokunanlar ★ ile işaretli, onay ister).

### 3.1 Meteoroloji ve veri kaynakları
| Yetenek | Durum | Etki | Zorluk | Not |
|---|---|---|---|---|
| Ticari kullanıma uygun meteo lisansı | **Yok** | Kritik | Kolay | Open-Meteo ücretsiz katman "ticari ❌"; Historical/Ensemble/Satellite → Professional plan |
| Çoklu NWP harmanı (ECMWF+GFS+ICON) | Yok | Yüksek | Orta | Open-Meteo `models=` ve Ensemble API zaten var — aynı bağımlılık |
| Uydu türevli ışınım (CAMS / PVGIS-SARAH) | Yok | Yüksek | Orta | Türkiye Meteosat görüş alanında; ölçüm-kalibreli GHI/DNI/DHI |
| Uydu nowcasting (0–6 s, bulut hareketi) | Yok | Orta (gün-içi ürünse Yüksek) | Zor | NREL setinde HA4'ün DA'ya üstünlüğü bu değerin kanıtı |
| Uzun homojen iklim arşivi (ERA5) | Kısmi | Orta | Kolay | Mevcut 20 yıl arşiv Open-Meteo Historical'dan; ERA5 doğrudan + belirsizlik bütçesi |
| Bankable TMY/P90 (Solargis/Meteonorm) | Yok | Orta (finans segmenti) | Kolay (ücretli) | Premium katman farklılaştırıcısı |
| EPİAŞ Şeffaflık gerçekleşen üretim | Yok | Yüksek | Orta | Ücretsiz API; SCADA yüklenmeyen santrallerde ground-truth |
| Kaynak atfı (attribution) | Yok | Kritik (lisans şartı) | Kolay | README/rapor/UI'da "profesyonel meteoroloji verisi" — atıf yükümlülüğü ayrıca yerine getirilmeli |

### 3.2 Tahmin bilimi (çekirdek — ★ onaylı)
| Yetenek | Durum | Etki | Zorluk |
|---|---|---|---|
| Olasılıksal kalibrasyon **doğrulaması** (reliability/PIT, pinball, CRPS, PICP) | Yok | Yüksek | Kolay-Orta |
| Conformal / quantile-regression ile P10–P90 kalibrasyonu ★ | Yok | Yüksek | Orta |
| Ensemble spread → ufukla büyüyen belirsizlik ★ | Yok | Yüksek | Orta |
| Curtailment/clipping tespiti ve kalibrasyon maskesi ★ | Yok | Yüksek | Orta |
| Rolling-origin backtest + train/serve-skew denetimi ★ | Kısmi | Yüksek | Kolay |
| İklimsel referans + akıllı persistansla optimal konveks birleşim (Yang 2019) | Kısmi | Orta | Kolay |
| Clear-sky McClear + IAM + spektral terimler ★ | Kısmi | Orta | Kolay (pvlib) |
| Soiling / kar modeli ★ | Yok | Orta (saha-bağımlı) | Orta |
| Degradasyon (%/yıl) + PR trendi | Yok | Orta (sağlık) | Kolay-Orta |
| Alt-saatlik (15 dk) tahmin | Kısmi (kalibrasyon frekans-agnostik, tahmin saatlik) | Orta | Orta |
| Portföy / hiyerarşik uzlaştırma | Yok | Stratejik | Orta-Zor |

### 3.3 Standartlar ve metrik dili
| Yetenek | Durum | Etki | Zorluk |
|---|---|---|---|
| IEC 61724-1 Performance Ratio (PR, sıcaklık-düzeltmeli PR', Yr/Yf) | Yok | Yüksek | Kolay |
| Kapasiteye normalize nMAE/nRMSE/nMBE + skill (SFA sözlüğü) | Kısmi | Yüksek | Kolay |
| P50/P90/P99 belirsizlik bütçesi (yıllar-arası + kaynak + model σ) | Kısmi | Yüksek (bankability) | Orta |
| PVsyst kayıp ağacı (transpozisyon→IAM→soiling→gölge→sıcaklık→…→availability) | Yok | Yüksek (rapor dili) | Orta |
| IEC 61853 güç matrisi ile modül davranışı | Yok | Orta | Orta |
| Availability (kullanılabilirlik) metriği | Yok | Orta | Kolay |

### 3.4 Türkiye pazarı
| Yetenek | Durum | Etki | Zorluk |
|---|---|---|---|
| KGÜP/DUY dengesizlik maliyeti simülasyonu (PTF/SMF, ±%3) | **Yok** | **Kritik (satış tezi)** | Orta |
| YEKDEM içi / serbest piyasa segmentasyonu | Yok | Yüksek | Kolay |
| EPİAŞ Şeffaflık entegrasyonu (gerçekleşen, PTF/SMF) | Yok | Yüksek | Orta |
| KGÜP bildirim dosyası üretimi (saatlik program) | Yok | Yüksek | Kolay |

### 3.5 Ürün / platform (izleme SaaS hijyeni)
| Yetenek | Durum | Etki | Zorluk |
|---|---|---|---|
| Portföy (çok santral) görünümü ve toplama | Yok (tek santral) | Yüksek | Orta |
| Otomatik tazeleme / canlı veri | Yok (yenileme elle) | Orta | Kolay |
| Alarm kural çeşitliliği + şiddet + okundu yönetimi | Kısmi (2 kural) | Orta | Kolay-Orta |
| Şablon rapor çeşitliliği (kapasite testi, beklenen-gerçekleşen, fatura) | Kısmi (16 sayfa + 3 format) | Orta | Orta |
| Dışa dönük API + API anahtarları (tablo var, kapı yok) | Kısmi | Yüksek (entegrasyon) | Kolay |
| Rol tabanlı veri paylaşımı (utility↔vendor, SFA kalıbı) | Kısmi (3 rol) | Orta | Orta |
| Tarife/gelir yapılandırması | Yok | Orta | Kolay |
| BESS / kontrol | Yok | Kapsam dışı (bilinçli) | — |

---

## 4. Rakip kapsam matrisi

On bir ürün üç kümeye ayrılıyor: **tahmin/veri sağlayıcılar** (Solargis, Solcast), **tasarım/simülasyon** (PVsyst, pvlib/PVPMC), **izleme/O&M platformları** (meteocontrol VCOM, AlsoEnergy PowerTrack [artık GE Vernova], Power Factors Unity [+GreenPowerMonitor aynı grup], QOS Qantum, Raptor Maps) ve **tarafsız değerlendirme** (Solar Forecast Arbiter — kamu paneli 2022'de emekli, metrik kütüphanesi açık kaynak).

| Yetenek | Solargis | Solcast | PVsyst | SFA | VCOM | PowerTrack | Power Factors | QOS | Raptor | pvlib | **PVQuant** |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Olasılıksal tahmin P10/50/90 | Yok (deterministik sunuluyor) | **Var** (doğrulanmış) | Yıllık P50/P90 | Tanımlar | Yok | Yok | Yok | Yok | Yok | — | **Var** |
| Uydu nowcasting 0–3 s | Var | Var | — | — | Yok | Yok | Yok | Yok | Yok | — | Yok |
| NWP çoklu-model / ensemble | Var (consensus) | Var | — | — | Yok | Yok | Yok | Yok | Yok | — | Yok (tek kaynak) |
| 14–15 gün saatlik ufuk | Var | Var | — | — | Yok | Yok | Yok | Yok | Yok | — | **Var** |
| Uzun dönem iklim / TMY / bankable P90 | Var (30+ yıl) | Var (2007→) | Girdi | — | Yok | Yok | Yok | Yok | Yok | — | Kısmi (20 yıl, tek kaynak) |
| Resmi doğrulama / skill çerçevesi | Yayımlıyor | Yayımlıyor (EPRI) | — | **Standart** | Yok | Yok | Yok | Yok | Yok | — | Var (WMAPE/skill) — SFA dışı sözlük |
| Gerçek zamanlı izleme / SCADA | Monitor | Yok | — | — | Var | Var | Var | Var | Yok | — | Kısmi (kalibrasyon için) |
| Alarm + CMMS / iş emri | Yok | Yok | — | — | Var | Var | Var | Var | Var | — | Kısmi (2 kural) |
| Kayıp ağacı / RCA | Yok | Yok | **Var** | — | Kısmi | Var | Var | Kısmi | Var | Zincir | Yok |
| BESS / dispatch | Var | Kısmi | Var | — | Var | Var | Var | Yok | Yok | — | Kapsam dışı |
| Curtailment kotalama + finans / fatura | Yok | Yok | Ekonomi | — | Var | Var | Var | Var | Yok | — | Yok |
| Portföy + üretim sınıfı API | Var | **Var** (26M/gün) | — | Var | Var | Var | Var | Var | Var | — | Yok (tek santral, PDF-öncelikli) |
| Soiling modeli | Var | Var (PM2.5/10) | Var | — | Kısmi | Kısmi | Kısmi | Kısmi | Var (termal) | Var | Yok |

**Okunuş:** PVQuant, olasılıksal + 15 günlük ufukta Solcast ile aynı sınıfta ve Solargis'in *reklam ettiği* çıktının üstünde; buna karşılık (i) NWP çeşitliliği ve uydu katmanında tahmincilerin gerisinde, (ii) izleme hijyeninde (portföy, API, alarm çeşitliliği, kayıp ağacı) izleyicilerin gerisinde. **Boş kesişim:** tahminciler arıza atfı yapmaz, izleyiciler olasılıksal tahmin yapmaz — "az üretim hava mı arıza mı?" sorusunu tek üründe yanıtlayan yok. Türkiye'ye ayarlı (EPİAŞ/KGÜP/dengesizlik) küresel oyuncu da yok.

**Farklılaşma fırsatları (rakip ajanı + kendi okumam):**
1. Türkiye piyasasına gömülü olasılıksal tahmin — dengesizlik maliyetini minimize eden teklif katmanı.
2. Tasarım-zamanı (20 yıl P50/P90) + operasyon-zamanı (15 gün P10/P90) **aynı saha-kalibreli modelden**; rakipler bu ikisini ayırır.
3. SFA-hizalı, kamuya açık **skill karnesi** — rakipler doğruluğu övgüyle geçiştirir, biz ölçüyle hesap veririz.
4. Kreditör-formatında otomatik 16 sayfa rapor — Solcast/Solargis ham API verir.
5. **Tahmin↔arıza mutabakatı:** SCADA kalibrasyonunun üstüne hafif PR/availability + kayıp atfı.

---

## 5. Öncelikli yol haritası — "kesinlikle eklenmeli"

Sıralama etki × aciliyet × zorluk'a göre; her madde ayrı mühür(ler) ve çekirdeğe dokunanlar açık onay ister.

### Dalga 0 — Lisans ve atıf (bu hafta)
1. **Open-Meteo ticari plan** (Professional: forecast + historical + ensemble + satellite tek pakette) **ya da** PVGIS/CAMS'e geçiş; ne seçilirse seçilsin **atıf** README + rapor künyesi + UI "veri kaynağı" satırına.
   *Gerekçe:* SaaS gelirine dokunan tek yasal risk. *Yan kazanç:* Ensemble API aynı planla açılır → Dalga 2'nin veri ihtiyacı çözülür.

### Dalga 1 — Ölçüm dilini standarda oturt (çekirdeğe dokunmaz)
2. **Karneye SFA metrik seti:** nMAE / nRMSE / nMBE (kapasiteye normalize) + skill; mevcut WMAPE kalır.
3. **Olasılıksal doğrulama paneli:** reliability diyagramı, PICP ("P10–P90 bandı gerçekten günlerin %80'ini tutuyor mu?"), pinball, CRPS — Doğruluk sayfasına yeni kart, gece skill işine yeni kolonlar.
4. **IEC 61724-1 PR kartı:** Yr/Yf/PR/PR′ — Santralım'a; kayıp ağacının tepesi.
5. **NREL hakem seti ile CI regresyonu:** `büyükveri`den 3–5 santralı test fikstürüne al; karne motoru her mühürde bilinen DA/HA4 hatasını yeniden üretmeli (sayıların bağımsız kanıtı).

### Dalga 2 — Belirsizlik gerçek olsun (★ onay)
6. **Çoklu-model NWP + ensemble üyeleri** → üye başına fizik koşusu → ampirik kantiller; MOS/kantil-harman.
7. **Conformal (CQR/ACI) ile P10–P90 kalibrasyonu**, reliability ile kapatılan döngü.
8. **Rolling-origin backtest + train/serve-skew denetimi** (rezidüel özellikleri tahmin-türevli mi ölçüm-türevli mi?).

### Dalga 3 — Veri hijyeni ve fizik terimleri (★ onay)
9. **Curtailment/clipping maskesi** (pvanalytics/RdTools) — kalibrasyon ve metrikler sessizce sapmasın; "kısıtlama olmasaydı" senaryosu.
10. **McClear clear-sky + IAM + spektral** (pvlib, mevcut bağımlılık) — kt'yi yeniden tanımla, rezidüele temiz hedef.
11. **Soiling/kar + degradasyon/PR trendi** — saha profiline göre açılır.

### Dalga 4 — Türkiye'de para diline çevir
12. **Dengesizlik maliyeti simülatörü:** KGÜP = P50, gerçekleşen = SCADA/EPİAŞ; PTF/SMF ile ±%3 kuralı; "bu ay tahmin hatası size X TL'ye mal oldu / PVQuant Y TL kurtardı" — karnenin TL dili.
13. **KGÜP bildirim çıktısı** (saatlik program dosyası) + **YEKDEM/serbest** segment bayrağı santral kartında.
14. **EPİAŞ Şeffaflık** entegrasyonu (gerçekleşen üretim + fiyatlar).

### Dalga 5 — Platform genişlemesi
15. **Portföy görünümü** (santral listesi, toplam güç, alarm özeti; ileride hiyerarşik uzlaştırma).
16. **Dışa dönük API anahtarları** (tablo hazır) + OpenAPI belgesi + webhook — SFA/CMMS kalıbında entegrasyon.
17. **Otomatik tazeleme**, alarm kural kütüphanesi (PR düşüşü, clipping oranı, iletişim kesintisi), okundu/atama.
18. **Uydu nowcasting** (0–6 s) — gün-içi/dengeleme ürünü olarak ayrı SKU.

---

## 6. Bilinçli kapsam dışı
- Uzaktan kontrol / PPC / BESS (PowerTrack sınıfı) — PVQuant tahmin ve kanıt ürünü; donanım kontrolü ayrı bir sorumluluk alanı.
- MGM verisi — açık API yok, ücretli; EPİAŞ + uydu kaynakları yeterli.
- Alarm kural sayısını şişirmek — "iki kural, fazlası yasak" ilkesi (El Kitabı P4 §3) korunur; yeni kurallar ancak dengesizlik/PR gibi ölçülebilir zararla gelir.

---

## 7. Kaynaklar
- NREL Solar Power Data for Integration Studies: https://www.nrel.gov/grid/solar-power-data.html
- Solar Forecast Arbiter: https://solarforecastarbiter.org · https://github.com/SolarArbiter · https://solarforecastarbiter-core.readthedocs.io/
- pvlib-python: https://pvlib-python.readthedocs.io/ · pvanalytics: https://github.com/pvlib/pvanalytics · RdTools: https://github.com/NREL/rdtools
- Open-Meteo lisans/planlar: https://open-meteo.com/en/pricing (teyit: ücretsiz katman ticari kullanım dışı; Historical/Climate/Ensemble/Satellite → Professional)
- PVGIS: https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis_en · CAMS Radiation: https://ads.atmosphere.copernicus.eu/datasets/cams-solar-radiation-timeseries · ERA5: https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels · NSRDB PSM3: https://developer.nrel.gov/docs/solar/nsrdb/
- Solargis: https://solargis.com · Meteonorm: https://meteonorm.com · SolarAnywhere: https://www.solaranywhere.com
- EPİAŞ Şeffaflık: https://seffaflik.epias.com.tr · MGM ürünler: https://www.mgm.gov.tr/site/urunler.aspx
- IEC 61724-1, IEC 61853-1..4: https://webstore.iec.ch · PVsyst kayıp ağacı: https://www.pvsyst.com/help/
- Literatür: Yang 2019 (referans tahminler, Solar Energy); Lauret-David-Pinson 2019 (olasılıksal doğrulama); Gneiting-Raftery 2007 (CRPS); Romano-Patterson-Candès 2019 (CQR); Gibbs-Candès 2021 (ACI); Coello-Boyle 2019 (HSU soiling); Deceglie 2018 / Jordan 2018 (degradasyon); Wickramasuriya-Athanasopoulos-Hyndman 2019 (MinT); Ineichen-Perez 2002, Lefèvre 2013 (McClear).

---

# İKİNCİ TUR — Ek bölümler (5 Eylül 2026, akşam)

> İlk raporun 04 (rakipler) ve 07 (kaynaklar) bölümlerini genişleten ikinci araştırma turu: dört hat (tahminci ikinci halkası · Türkiye oyuncuları ve düzenleme · literatür/veri seti/açık NWP · meteo tedarik lisans-fiyat). Sonunda yol haritası yeniden değerlendirilir. Teyit edilemeyen her madde açıkça işaretlidir.

## 0-b. İkinci turun beş bulgusu

1. **Lisans sorunu bir günde, €1.099/yıla kapanıyor.** Open-Meteo Professional ticari lisansı verir, kod değişikliği gerektirmez ve ürünün ihtiyaç duyduğu üç şeyi aynı sözdizimiyle açar: ERA5 arşivi, IFS ensemble (51 üye, 15 gün) ve SARAH-3 uydu ışınımı. 500 santralde bile kotanın %5'i kullanılır. Ham NWP'yi kendimiz çekmek (ECMWF Open Data + ICON + GFS, hepsi CC BY 4.0 / kamu malı) hukuken mümkün ama yılda €15–30k insan maliyetiyle savunulamaz; yalnız acil-durum yedeği olarak 1–2 haftalık minimal çekici anlamlı.
2. **Türkiye'de olasılıksal GES tahmini satan yerli oyuncu yok.** Yerli izleme SaaS'ları (Solarify, Solar8, SolarTools, Enoptimal…) deterministik; tek "güven bandı" UrClimate'te. 2025'ten beri lisans alan 38–47 toplayıcı ve büyük DSG'ler (Enerjisa Üretim, Limak, Zeros) doğal B2B kanal. Dağıtım bağlı lisanssız GES'in doğrudan dengesizlik sorumluluğu yok — dengesizlik GTŞ/toplayıcı portföyünde taşınır; değer önerisi orada kurulmalı.
3. **Piyasa takvimi ürün ritmini belirler.** KGÜP her gün 14:00–15:30 arası TEİAŞ TPYS'ye (DUY'da 'PYS'), TEİAŞ teyidi 17:00; saatlik (≥200 MWh sıçramada 15 dk); gün içi güncelleme teslimattan 30 dk önceye kadar. KGÜP'ten sapma için ayrı KÜPST tutarı var. 15 dakikalık uzlaştırma 1/1/2027 hedefli — Faz 2'nin takvimi budur. EPİAŞ Şeffaflık API'si (301 uç nokta, PTF/SMF/KGÜP/gerçek zamanlı üretim/dengesizlik) kayıtla ücretsiz; `eptr2` Python paketi hazır.
4. **Sektör pratikleri:** kantil vektörü standartlaşıyor (Steadysun 11 kantil, Dexter P5–P95, OCF API'de `plevel_10/90`); trend/bias düzeltme katmanı API parametresi; büyük ensemble = kalibrasyon iddiası; kantilin piyasa ürününe bağlanması sayısal vakayla anlatılıyor (Dexter aFRR P10); fiyat site-kademeli. Karnemiz pazarda nadir bir şeffaflık; eksiğimiz gün içi ufuk ve bağımsız doğrulama yayını.
5. **Metrik sözlüğü netleşti:** Yang ve diğ. 2020 (33 yazarlı konsensüs) deterministik doğrulama, Doubleday-Hodge 2020 olasılıksal referans tahmin, Mayer & Yang 2022 kalibre model-zinciri ensemble'ı, IEA Wind RP 2. baskı (tahmin çözümü seçimi/değerlendirme). Türkiye'de BSRN istasyonu yok → CAMS/SARAH-3 "sanal piranometre" rolü. Foundation modellerin hiçbirinde yüzey ışınımı çıktısı teyit edilemedi — pratik yol ECMWF AIFS (ssrd, CC BY 4.0).

## 08. Tahmin sağlayıcılarının ikinci halkası

| Oyuncu | Küme | Ufuk / adım | Olasılıksal | Öne çıkan |
|---|---|---|---|---|
| Steadysun (FR) | Nowcast uzmanı | dakikalar–15 g, 5 dk güncelleme, 1 dk adım | **11 kantil P00–P100** | Site/ay kademeli fiyat (D+2/D+7/D+16), portalda MAE/MBE/RMSE |
| Reuniwatt (FR) | Nowcast uzmanı | 10 g / 6 s / 30 dk (kamera) | Teyit edilemedi | Kızılötesi gök kamerası + 5 uydu, MODBUS'a bağlı InstaCast |
| Meteomatics (CH) | Hava-API | gün içi/gün öncesi, 15 dk | Ensemble üyeleri/kantil (100 üye) | EURO1k 1 km; Avrupa portföyü nRMSE %4; "~%20 dengesizlik azalması" |
| DNV Forecaster | Kurumsal | 15 g, saatlik→5 dk | Var (format belirsiz) | Eski Vaisala/3TIER; 7/24 |
| UL Solutions | Kurumsal | dakikalar–haftalar, 5 dk | POE + güven bantları | K. Amerika şebeke güneşinin %65'i, 145 GW |
| ENFOR SolarFor (DK) | Kurumsal | dakikalar–haftalar | Kantil bantları | On-prem/hosted; trading için |
| Meteologica (ES) | Kurumsal | 14 g saatlik, 4×/gün | Piyasa düzeyinde ensemble | 260 GW güneş, 400+ trader |
| emsys Suncast (DE) | Kurumsal | 5 dk–15 g | Durum-bağımlı belirsizlik | Hava durumuna göre NWP ağırlıklandırma; gerçek besleme vs teknik potansiyel |
| Whiffle (NL) | Nowcast/LES | 7 g, <100 m | Var | LES; "%30 düşük RMSE" (kendi iddiası) |
| Amperon (US) | Trader-odaklı | 15 g, alt-saatlik | Dağılım eğrisi (2026) | 4 satıcıdan 40k hava noktası; ERCOT teklif senaryoları |
| Open Climate Fix – Quartz (UK) | Açık kaynak | 0–48 s, 5 dk güncelleme | `plevel_10/90` | PVNet (MIT): SEVIRI 11 kanal + ICON-EU/ECMWF/GFS + canlı PV; `trend_adjuster` |
| Dexter Energy (NL) | Trader-odaklı | kısa vade | **P5…P95**, conformal, CRPS | aFRR vakası: P10 tabanı €65.552 ile sabit haircut'ları geçti |
| Rebase Energy (SE) | Trader-odaklı | tam ufuk, 15 dk | Ensemble | Ücretsiz 3 site, sonra €800/ay |
| Sunairio (US) | Foundation-model | 18 s / 15 g / 12 ay / 15 yıl | 1.000 üye "kalibre" | Kendi reanalizi 1950→ |
| Sprixin 国能日新 (CN) | Kurumsal/TSO | 4 s / 72 s / 240 s | Teyit edilemedi | 2.000+ müşteri; TSO sapma cezası düşürme hedefi |
| REConnect (IN) | Kurumsal/TSO | — | — | Sapma sorumluluğunu üstlenen sabit ücret (QCA modeli) |

Diğerleri: Volue Insight, meteoblue, Tomorrow.io, Vaisala Xweather (ışınım doğrulaması 66 istasyon, MBE %0,86), Overspeed (%100 erişilebilirlik 10 yıl), AleaSoft, WindBorne (128 üye), Jua, Silurian (post-training), Brightband; Nnergix (5 g, 10 sisteme kadar ücretsiz), DTN (güneşe özel ürün bulunamadı), Solar Analytics (tahmin yok).

**Yeni öğrenilen pratikler:** (1) kantil vektörü ≥7 nokta; (2) kamera/uydu/NWP üç katmanlı ufuk (30 dk / 6 s / 15 g); (3) foundation-model "post-training" ve saha üretimiyle ML — "saha-kalibreli" artık AI oyuncularının da dili; (4) büyük ensemble + "underdispersion" düzeltmesi satış argümanı; (5) kantilin piyasa ürününe bağlanması sayısal vakayla; (6) portföy/ülke tahmini ayrı ürün hattı; (7) gerçek besleme vs teknik potansiyel (kısıntı) ayrımı; (8) fiyat: site/ay kademe, ücretsiz 3 site, sapma sorumluluğu üstlenen sabit ücret; (9) doğrulama şeffaflığı ışınımda güçlü, güçte kendi iddiası; (10) trend/bias düzeltme katmanı API parametresi; (11) 7/24 nöbet = SLA.

**PVQuant'ın konumu (ikinci tur):** çekirdek DNV/UL/Meteomatics'in ufuk ve olasılık düzeyiyle örtüşüyor; onlar 5 dk adım ve gün içi uydu nowcast da veriyor. 60 günlük karne pazarda nadir; hiçbir oyuncu periyodik öz-değerlendirmeyi ürünün parçası yapmıyor. Türkiye'de 100 kWp–50 MW segmentinde fiyat MW başına değil site-kademesine göre kurulmalı. En ucuz kısa vadeli kazanç: trend/bias düzeltme katmanı ve (Dalga 2'de) ensemble; kamera/LES'e girmeden.

## 09. Türkiye: yerli oyuncular ve piyasa mekaniği

### 9.1 Yerli oyuncular
| Oyuncu | Ne yapar | Tahmin / olasılık |
|---|---|---|
| Solarify (Loggma) | YZ izleme, iş emri, 12 alarm tipi, OSOS/EDAŞ/TEİAŞ uyumu, PPC; 300 kWp+; MAXIMA 370+ MW | Performans/kayıp; olasılıksal yok |
| Solar8, MapperX, Retgen, SolarRelax, Ranaliz | İzleme / termografi / tracker / çatı | Basit veya yok |
| SolarTools | IoT + LSTM/RF/GBM üretim tahmini, V-I arıza | Deterministik ("%95+") |
| Enoptimal | İzleme + canlı PTF + saatlik mahsuplaşma + BESS; 3.000+ tesis | — |
| GESmetrik (Paff) | Lisanssız GES gelir takibi, 1 Mayıs 2026 saatlik mahsuplaşma; 100 $/sayaç/ay | Gün-öncesi PTF |
| UrClimate (Alkazar) | RES+GES gün-öncesi, WRF + çok modelli YZ; 243 RES / 56 GES | **Güven bantları** (tek örnek) |
| APLUS Enerji | 14 gün saatlik tahmin, MAPE/MAE raporu | Deterministik |
| VTC Enerji | V-Forecast, V-Plant Manager (KGÜP/EAK otomasyonu), V-Market; enercast + Sirocco partner | 15 dk; olasılıksal belirtilmiyor |
| Corius, Buluttan | LSTM/XGBoost ensemble; hiper-yerel hava | Deterministik |
| smartPulse (Volue, Ekim 2025) | GÖP/GİP algoritmik ticaret, 600+ santral, 20+ tahmin sağlayıcı entegrasyonu | Kendi tahmini yok → **entegrasyon hedefi** |
| Enerjisa Üretim, Limak, Zeros, Zorlu Dengeleme, Enerjisa MÇ, Minas, Energy Pool | DSG / toplayıcılık (2025'ten beri 38–47 lisans) | Portföy optimizasyonu, tahmin satın alır |
| TEİAŞ + TÜBİTAK "Güneş Üretim Tahmin Sistemi" (Tem 2026) | 40.000+ GES / ~26,7 GW, 6 s–3 gün, hibrit YZ, YTBS'ye entegre | TSO düzeyi; santral düzeyi ürün değil |

Bulgu: **P10/P90 olasılıksal GES tahminini pazarlayan yerli firma bulunamadı** (yalnız akademik çalışmalar). TÜBİTAK RİTM yalnız rüzgar (≥10 MWe RES'e bağlantı zorunlu, RG 6/2/2026); GES için benzeri zorunluluk yok. MGM ışınım verisi ücretli (MEVBİS), açık API yok; GEPA aktif ama güncelleme tarihi belirsiz.

### 9.2 Piyasa mekaniği (DUY, RG 29/12/2025 sürümü)
- **KGÜP:** tüm üretim UEVÇB'leri; toplayıcılar portföyleri için; MW eşiği yok. DGP 14:00'te başlar, **15:30'a kadar** KGÜP + YAL/YAT (TEİAŞ TPYS — EPİAŞ DGP süreci sayfası; DUY metninde 'PYS'), **17:00'a kadar** TEİAŞ teyidi. Saatlik; ardışık iki saat farkı ≥200 MWh ise 15 dk. Gün içi güncelleme GİP kapı kapanışı (teslimattan 1 s önce) + 30 dk'ya kadar. Emre amade kapasite de 15:30'a kadar; gerçeğe aykırı bildirim Kanun md. 16 (2026 cezaları 10,3–16,5 milyon TL).
- **Dengesizlik:** pozitif = min(PTF, SMF)×(1−l), negatif = max(PTF, SMF)×(1+k); k, l Kurul kararıyla 0–1. k ve l = **0,03** — EPİAŞ SMF hesaplama sayfası: "01 Mayıs 2015 tarihinden itibaren 0,03 olarak belirlenmiştir" (https://www.epias.com.tr/smf-hesaplanmasi/); değiştiren bir karar/duyuru bulunamadı. 29/12/2025 değişikliği azami fiyat limiti ve 15 dk SMF_N/SMF_P'yi formüle ekledi. **KÜPST**: KGÜP bildirmekle yükümlü birimler için ayrı sapma tutarı (katsayı n + tolerans, Kurul kararı).
- **YEKDEM içi dengesizlik:** DUY'da ayrı havuz hükmü yok; YEKDEM Yönetmeliği metni çekilemedi — teyit edilemedi.
- **Lisanssız:** LÜY'de "dengesizlik" hiç geçmiyor; ihtiyaç fazlasını GTŞ **veya toplayıcı** alır (RG 02.04.2026/33212; 10 yıl YEKDEM kapsamında, saatlik mahsuplaşma) → dağıtım bağlı lisanssız üreticinin doğrudan dengesizlik sorumluluğu yok. İstisna: iletim bağlı lisanssız KGÜP bildirir; toplayıcı portföyünde KÜPST işler.
- **15 dk:** DGP uzlaştırma dönemi 15 dk yazıldı ama Geçici md. 40 → altyapı en geç 1/1/2027; 2025–2026'da geçilmedi.
- **Fiyatlar (EPDK aylık sektör raporları, birincil):** 2025 yıllık ağırlıklı PTF **2.651,81 TL/MWh** (2024: 2.273,73, +%16,6), SMF **2.524,09** (+%15,9); aylık PTF 2.207 (Mart) – 3.005 (Aralık). SMF 2.565 saat tavanda (3.400 TL/MWh), 369 saat sıfırda — dengesizlik riskinin kaynağı SMF'nin uçlara PTF'den çok daha sık gitmesi. 2025 YEKDEM ortalama fiyatı 3.684 TL/MWh.
- **Pazar büyüklüğü (EPDK Aralık 2025):** kurulu güneş **25.109 MW** (toplamın %20,5), bunun **22.569 MW'ı lisanssız (≈%90)**; 2025 güneş üretimi 36,97 TWh (%10,3). Ember 2026: rüzgar+güneş payı %22.
- **Örnek hesap (10 MW GES, 16.000 MWh/yıl, 2025 PTF/SMF):** üretimin %10'u kadar hata → yıllık dengesizlik maliyeti **≈127 bin TL** (SMF=PTF, yalnız %3) ile **≈550 bin TL** (PTF–SMF sapması %20 varsayımı) arası; kurulu gücün %10'u kadar saatlik hata tanımıyla 348 bin – 1,5 milyon TL. Gelirin (≈42 milyon TL) %0,3–3,6'sı. Simülatör hata tanımını ve PTF–SMF sapma dağılımını kullanıcıya seçtirmeli.
- **Dengesizlik teminatı:** son 3 ayın en yüksek negatif dengesizliği × 12 aylık SMF ortalaması × risk katsayısı (EPİAŞ teminat esasları) — tahmin kalitesi teminat tutarını da düşürür.

### 9.3 EPİAŞ Şeffaflık API
Swagger v1.15.15, 301 uç nokta, `basePath /electricity-service`; POST + tarih aralığı. Kullanacaklarımız: `/v1/markets/dam/data/mcp` (PTF), `/v1/markets/bpm/data/system-marginal-price` (SMF), `/v1/markets/bpm/data/system-direction`, `/v1/generation/data/dpp` ve `dpp-first-version` (KGÜP), `/v1/generation/data/realtime-generation`, `/v1/markets/imbalance/data/imbalance-quantity|imbalance-amount`, `/v1/markets/idm/data/weighted-average-price`, `/v1/renewables/data/imbalance-cost`, `/v1/renewables/data/res-generation-and-forecast`. Kimlik: kayıt + TGT (`giris.epias.com.tr/cas/v1/tickets`, 11 Kas 2025'ten beri kimlik body'de); CAS limiti TGT 100/dk, ST 1.500/dk. Python: `eptr2` (Tideseed; 24 Ağu 2026, 213+ servis).

### 9.4 Türkiye'ye özgü ürün gereksinimleri
1. **KGÜP dosyası ve teslim saati:** TEİAŞ TPYS CSV şablonu (EAK/KGÜP) üretici + manuel yükleme akışı; D+1 için saatlik program 15:30'dan önce hazır (sabah koşusu zaten uygun; 12 UTC koşusu ~15:00'te gelir — ikinci koşu "KGÜP öncesi güncelleme" olarak düşünülmeli); ≥200 MWh sıçramada 15 dk kural bayrağı.
2. **Gün içi güncelleme akışı:** GİP kapı kapanışı+30 dk'ya kadar KGÜP revizyonu → gün içi tahmin katmanı (uydu/nowcast) Türkiye'de doğrudan paraya çevrilir.
3. **Dengesizlik simülatörü girdileri:** PTF, SMF, sistem yönü, k/l = 0,03 (parametre), KÜPST katsayı/tolerans (parametre), gerçekleşen (SCADA veya EPİAŞ realtime-generation), KGÜP (dpp-first-version vs güncel), DSG içi netleştirme, dengesizlik teminatı etkisi; çıktı: aylık TL + gelir yüzdesi (10 MW örneği: 127 bin – 1,5 milyon TL/yıl).
4. **Segment bayrağı:** lisanslı / iletim-bağlı lisanssız / dağıtım-bağlı lisanssız (toplayıcı portföyü) / YEKDEM — dengesizlik kimin cebinden çıkıyor?
5. **Toplayıcı/DSG portföy görünümü:** 38–47 toplayıcı için çok santral toplama, portföy netleşme etkisi, KÜPST topluluk/münferit seçeneği.
6. **smartPulse/Volue entegrasyonu:** 20+ tahmin sağlayıcı entegre ediyor — PVQuant çıktısını standart biçimde sunmak (API anahtarı + KGÜP formatı) doğrudan kanal.
7. **Emre amade kapasite (EAK) alanı:** 69/A uyarınca 15:30 bildirimi; santral kartında EAK ve bakım takvimi.
8. **1 Mayıs 2026 saatlik mahsuplaşma:** lisanssız öz-tüketimde saatlik tahmin değeri arttı — GESmetrik'in yakaladığı segment.
9. **15 dk hazırlığı (2027):** Faz 2 alt-saatlik tahmin takvimi mevzuata bağlanmalı.
10. **Yasal metin kütüphanesi:** DUY madde referanslarıyla (69, 69/A, 110, 111) ürün içi açıklamalar; %3 ve KÜPST katsayıları "Kurul kararı" notuyla, sabit kodlanmadan.

## 10. Meteo tedarik kararı (Dalga 0)

| Yol | Yıllık maliyet (50 / 500 santral) | Mühendislik | Hukuki risk | Ensemble / uydu / arşiv |
|---|---|---|---|---|
| **A. Open-Meteo Professional** | €1.099 / €1.099 (kotanın <%5'i) | ~0 (yalnız alan adı + anahtar) | Düşük; CC BY 4.0 atıf zorunlu; sözleşmesel SLA yalnız Enterprise | IFS ENS 51 · SARAH-3/MTG · ERA5/CERRA — hepsi dâhil |
| B. Ham NWP (ECMWF Open Data + ICON-EU + GFS/GEFS) | 1. yıl ≈ €30k, sonra ≈ €15,5k (insan maliyeti) | 2–3 kişi-ay kurulum + 0,2 FTE bakım; GRIB2, harmanlama, saatlik ayrıştırma | Düşük; CC BY 4.0 / kamu malı | Tam ham erişim; uydu için ayrıca CAMS/SARAH; ilk sürüm kalitesi düşük |
| C. Ticari (Solcast / Meteomatics) | Teklif; düşük–orta beş haneli € beklenir | Düşük–orta | En düşük; sözleşmeli SLA | 5–15 dk uydu nowcast, GTI, P10/P90 hazır |

Diğer adaylar: Visual Crossing Corporate $150/ay (ticari ✔, ensemble ✗), OpenWeather Solar Irradiance 0,1 GBP/çağrı (ölçekte pahalı), Weatherbit Free ticari ✗, Meteostat ışınım ✗, Pirate Weather 7 gün yalnız GHI, Météo-France AROME Türkiye dışı. Ücretsiz kamu arşivleri: PVGIS-SARAH3 2005–2023 (Konya için sınandı), CAMS ışınım serisi 2004→ (CC-BY), NASA POWER 2001→ saatlik (kaba).

**Karar önerisi:** (1) Open-Meteo Professional, yıllık ödeme; (2) atıf — README, rapor künyesi ve panelde "Hakkında / Veri kaynakları" satırı: "Weather data by Open-Meteo.com (CC BY 4.0)"; **not:** Gizlilik Anayasası görünür UI'da "Open-Meteo" adını yasaklıyor, CC BY ise atıf istiyor — anayasaya "lisans atfı istisnası" (yalnız Hakkında/künye) maddesi gerekir, kullanıcı kararı; (3) ECMWF Open Data'dan minimal yedek çekici (ssrd/2t/10u/10v/tcc, 1–2 hafta) acil durum planı; (4) PVGIS/CAMS arşivleri kalibrasyon referansı ve "bankable uydu" hikâyesi; (5) Yol C'yi 500 santral / gün içi taahhüt eşiğinde değerlendir.

## 11. Yeniden değerlendirme — ne değişti?

| İlk tur | İkinci tur sonrası |
|---|---|
| Dalga 0 "lisans" — belirsiz bütçe, PVGIS/CAMS'e geçiş seçeneği | **Somut ve ucuz:** Professional €1.099/yıl, kod değişikliği yok; geçiş gereksiz |
| Dalga 2 ensemble için veri kaynağı sorusu | Aynı planla çözülür → **Dalga 2 öne çekilebilir** (veri hazır, iş yalnız model+doğrulama) |
| Türkiye "beyaz alan" varsayımı | **Teyit edildi:** olasılıksal yerli rakip yok; TEİAŞ'ın kendi sistemi TSO düzeyi |
| Satış kanalı: santral sahibi | **Toplayıcı/DSG kanalı** (38–47 lisans) + smartPulse/Volue entegrasyonu eklendi; lisanssız GES'te dengesizlik sahibi GTŞ/toplayıcı |
| KGÜP "dosya üretimi" (Dalga 4) | Takvim netleşti (15:30 / 17:00 / GİP+30 dk) ve **KÜPST** ayrı maliyet kalemi → simülatör iki bileşenli; KGÜP çıktısı **Dalga 1'e** alınabilir (ucuz, yüksek değer) |
| Faz 2 alt-saatlik "ertelendi" | Mevzuat tarihi: **1/1/2027** → Faz 2 için dış takvim |
| Metrik seti "SFA sözlüğü" | Yang 2020 konsensüsü + Doubleday 2020 olasılıksal referans + IEA Wind RP 2. baskı — karnenin akademik dayanağı |
| Uydu/nowcasting "Dalga 5, zor" | OCF/PVNet açık kaynak (MIT) + SEVIRI/SARAH-3 CC BY → **orta zorluk**; gün içi güncelleme Türkiye'de doğrudan paraya çevriliyor |
| Post-processing | OCF `trend_adjuster` kalıbı: son 7 gün bias düzeltme — çekirdeğe dokunmadan bir "son katman" adayı (★ onay) |

### Revize yol haritası
- **Dalga 0 (bu hafta):** Open-Meteo Professional + atıf (anayasa istisnası kararıyla) + ECMWF yedek çekici planı.
- **Dalga 1 (çekirdeğe dokunmaz):** SFA/Yang-2020 metrik seti · olasılıksal doğrulama paneli (reliability/PICP/pinball/CRPS, Doubleday referansıyla) · IEC 61724-1 PR kartı · NREL hakem seti CI regresyonu · **+ KGÜP saatlik program çıktısı (15:30 kuralı, ≥200 MWh bayrağı)**.
- **Dalga 2 (★):** Open-Meteo Ensemble API ile üye başına fizik koşusu → ampirik kantiller (Mayer & Yang 2022 kalıbı) · conformal kalibrasyon · rolling-origin backtest · **+ trend/bias düzeltme katmanı**.
- **Dalga 3 (★):** curtailment/clipping maskesi · McClear/IAM/spektral · soiling/degradasyon.
- **Dalga 4 (Türkiye):** dengesizlik + KÜPST simülatörü (EPİAŞ `eptr2`: PTF/SMF/yön/KGÜP/gerçekleşen) · segment bayrağı · EAK alanı · smartPulse/Volue çıktı biçimi.
- **Dalga 5 (platform):** toplayıcı/DSG portföy görünümü · API anahtarları · otomatik tazeleme · uydu nowcast (OCF kalıbı) → 2027 15 dk'ya hazırlık.

### Kullanıcı kararı bekleyen üç soru
1. Open-Meteo Professional'a yıllık abonelik (€1.099) — onay?
2. Gizlilik Anayasası'na "lisans atfı yalnız Hakkında/künyede" istisnası — onay?
3. Hangi dalgayla başlıyoruz: Dalga 1 (+KGÜP çıktısı) mı, Dalga 2 (ensemble, ★) mi?

## 07-b. İkinci tur kaynakları (ek)
- Kılavuz: IEA PVPS Task 16 (Regional Solar Power Forecasting 2020; Best Practices Handbook 4. baskı 2024) · IEA PVPS Task 13 (2025–2026 raporları) · IEA Wind Task 51 RP 2. baskı (Möhrlen-Zack-Giebel 2022, açık erişim) · ASTM E2848-13(2023) · PVPMC blind modeling 2021/2023 · WMO JWGFVR verification FAQ · ECMWF Forecast User Guide.
- Makale: Yang ve diğ. 2020 (10.1016/j.solener.2020.04.019) · Yang ve diğ. 2022 (10.1016/j.rser.2022.112348) · Yang & van der Meer 2021 (10.1016/j.rser.2021.110735) · van der Meer 2018 (10.1016/j.rser.2017.05.212) · Doubleday-Hodge 2020 (10.1016/j.solener.2020.05.051) · Mayer 2022 (10.1016/j.rser.2022.112772) · Mayer & Yang 2022 (10.1016/j.rser.2022.112821) · Mayer & Yang 2023 (10.1016/j.ijforecast.2022.03.008) · Hong ve diğ. 2016 GEFCom2014 · Fulton ve diğ. 2024 PVNet (ICLR CCAI) · Le Gal La Salle-David-Lauret 2025 EVC/OEV.
- Veri: Sheffield PV_Live (CC BY 4.0) · OCF HuggingFace (uk_pv, dwd-icon-eu) · NREL PVDAQ OEDI (CC BY 4.0) · Energy-Charts API (CC BY 4.0) · SARAH-3 (CC BY 4.0, DOI 10.5676/EUM_SAF_CM/SARAH/V003) · CAMS gridded/time-series (CC-BY) · PVGIS v5.3 · NASA POWER · Renewables.ninja (CC BY-NC — ticari ✗) · DKASC (şartlı) · BSRN: Türkiye'de istasyon yok.
- Açık NWP: ECMWF Open Data (CC BY 4.0; IFS/AIFS; ssrd) · DWD ICON-EU (CC BY 4.0; aswdir_s/aswdifd_s; Türkiye kapsamda) · NOAA GFS/GEFS (kamu malı) · Météo-France (Licence Ouverte 2.0; AROME Türkiye dışı).
- Tedarik: Open-Meteo pricing · Meteomatics · meteoblue · Solcast · Solargis · Tomorrow.io · Visual Crossing · OpenWeatherMap · Weatherbit · Pirate Weather · Xweather · Meteostat.
- Oyuncular: Steadysun · Reuniwatt · DNV Forecaster · UL Solutions · ENFOR · Meteologica · emsys · Whiffle · Amperon · OCF Quartz (api.quartz.solar/openapi.json) · Dexter · Rebase · Sunairio · WindBorne · Jua · Silurian · Sprixin · REConnect · Overspeed · Xweather · Volue.
- Türkiye: DUY (mevzuat.gov.tr 7.5.12985, RG 29/12/2025) · EPDK Elektrik Piyasası Aylık Sektör Raporları 2025 + 2025 Piyasa Gelişim Raporu (epdk.gov.tr) · EPİAŞ SMF hesaplanması (k,l=0,03) · EPİAŞ DGP süreci (TPYS) · EPİAŞ dengesizlik teminatı esasları · RG 02.04.2026/33212 (LÜY toplayıcı) · Global Solar Atlas PVOUT (Konya 1.635 kWh/kWp) · Ember Türkiye Electricity Review 2026 · EPİAŞ KGÜP sayfası · EPİAŞ Şeffaflık teknik doküman + swagger · CAS limit duyurusu (23 Tem 2025) · eptr2 (github.com/Tideseed/eptr2) · GİP genel esaslar · RİTM Yönetmeliği RG 6/2/2026 · MGM MEVBİS · GEPA · EPDK lisans sorgu · Solarify · Solar8 · SolarTools · Enoptimal · GESmetrik · UrClimate · APLUS · VTC · Corius · smartPulse · Limak · Zeros · Enerjisa Üretim · TEİAŞ Güneş Üretim Tahmin Sistemi haberi (Tem 2026).
