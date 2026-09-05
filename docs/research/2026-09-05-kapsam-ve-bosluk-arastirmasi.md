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
