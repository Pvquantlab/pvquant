# Vitrin içeriği — Türkiye GES piyasasının diline uyarlama (21.10.2026)

Ortam: **bulut oturumu** (claude.ai/code uzak kapsayıcı; araştırma, kod incelemesi, metin düzenlemesi, testler, ekran
kontrolü ve bu rapor burada yapıldı). Yerel oturumda hiçbir işlem yapılmadı. Bulut kredi düşümü bu ortamdan okunamıyor —
**doğrulanamadı**; claude.ai kullanım sayfasından teyit edilmeli. Dal `main-bozzyl`, commit adfe316 (metinler) + bu rapor.

**Kapsam:** yalnız metin ve terminoloji. Renk, tipografi, görsel, animasyon, bölüm yapısı, responsive düzen, bileşen sayısı
ve çapalar değişmedi (derleme çıktısında yalnız metin düğümleri farklı). Yeni sayı, doğruluk oranı ya da ticari vaat
eklenmedi; vitrinin «görünür yüzeyde yöntem/kaynak adı yok» kuralı (`test/vitrin/gizlilik.test.ts`) ve eylem sözlüğü
(«Karnenizi başlatın», «Karnemi başlat») korundu.

## 1. Kimin için yazıldı, neyi düzeltiyor

Hedef okur: GES yatırımcısı, santral işletmecisi, enerji/ticaret yöneticisi. Eski metinler tahmin *yönteminin* diliyle
yazılmıştı (fizik modeli, öğrenen model, kantil, P10/P50/P90, ışınım, belirsizlik bütçesi, «dürüst aralık», «zincirin
çıkışı», webhook). Yeni metinler müşterinin *işi* ve piyasanın kendi terimleriyle yazıldı: üretim programı (KGÜP),
dengesizlik maliyeti, gün öncesi teklif, toplayıcı şablonu, kurulu güç (MW), emre amadelik, teslim saati, gün içi düzeltme.
Teknik kavram gerektiğinde kaldı, yanına tek cümlelik açıklama geldi (P50/P90 → «beklenen / güvenli üretim»).

## 2. Türkiye piyasası terminolojisi — araştırma özeti ve tercihler

Kaynaklar (21.10.2026 web araştırması): EPDK 14907 sayılı Kurul kararı haberi (19.10.2026; üretim planı sapma toleransları:
güneş %8, rüzgâr %15, iletime bağlı lisanssız %20, dağıtıma bağlı lisanssız %25), Elektrik Piyasasında Toplayıcılık Faaliyeti
Yönetmeliği (RG 17.12.2024, yürürlük 1.1.2025; DSG'den toplayıcı portföyüne geçiş), Dengeleme ve Uzlaştırma Yönetmeliği
(dengesizlik tutarı, PTF/SMF ile değerleme), sektör rehberleri (GÖP 12:30 teklif / 14:00 PTF; GİP teslimden 60 dk öncesine dek).

| Kullanılan terim | Neden bu | Yerine geçtiği ifade |
|---|---|---|
| **Üretim programı (KGÜP)** | Santral işletmecisinin her gün teslim ettiği belgenin resmî adı; ilk geçişte açıldı | «program», «bildirim saati» |
| **Dengesizlik maliyeti** | Yönetmelik ve piyasa dili («dengesizlik tutarı/maliyeti»); «sapma maliyeti» ürün içi tanımdı | «sapmanın TL karşılığı», «sapma maliyeti», «tahmin hatasının maliyeti» |
| **Gün öncesi teklif / önerilen seviye** | GÖP teklifi gündelik iş; «kantil» istatistik terimi | «teklif kantili», «önerilen kantil» |
| **İyimser–kötümser aralık** (iyimser · beklenen · kötümser) | Zaten sitede vardı; P10/P50/P90 yalnız finans kartında ve açıklamalı | «P10/P50/P90», «dürüst aralık», «bant» |
| **Kurulu güç (MW)** | Fiyat ve form zaten MW soruyordu; birim açıkça yazıldı | «kurulu güç başına» (birimsiz) |
| **Toplayıcı şablonu** | 2025'ten beri lisanslı/lisanssız santraller toplayıcı portföyünde; şablon uyumu somut fayda | «TPYS'ye öneri CSV», «DSG şablonu» (menüde «Toplayıcı / DSG şablonları» kaldı) |
| **Teslim saati, gün içi düzeltme** | GÖP/GİP saatleri işletmecinin gündelik dili | «teslim penceresi», «revizyon kapısı/penceresi», «D‑1» |
| **Santralinizin yapısı / geçmiş üretiminiz** | Müşteri kendi santralini tanır; «fizik modeli / öğrenen model» yöntem adıydı | «Fizik modeli», «Öğrenen model», «geometri», «ışınım» |
| **Her gece sınav / doğruluk karnesi** | Markanın mevcut kanıt dili; korundu ve her yüzeyde aynı ad | «Gece karnesi», «kanıt birikir» |
| **Otomatik bildirim (webhook)** | Yazılım terimi parantezde, fayda önde | «sabah webhook'u», «REST API akışı» |
| **Emre amadelik** | Piyasa terimi; yerinde bırakıldı | — |

Bilinçli olarak **kullanılmayanlar:** tolerans yüzdeleri (EPDK kararıyla değişiyor; sayfa bayatlamasın), «şeffaf» ve kaynak
adları (test yasağı), «yapay zekâ/makine öğrenmesi» (yöntem adı; dürüstlük kuralı), rakip adı, doğruluk oranı vaadi.

## 3. Değişen metinler — eski → yeni

### Ana sayfa

| Yer | Eski | Yeni | Gerekçe |
|---|---|---|---|
| Hero giriş | «PVQuant, güneş santralinizin saatlik üretimini 15 güne kadar tahmin eder ve her tahmine bir güven aralığı ekler. Günlük üretim programınız bildirim saatinden önce hazır olur; tahmin ile gerçekleşen üretim arasındaki farkın size maliyeti panelde günlük olarak raporlanır. Her tahmin, ertesi gün gerçekleşen üretimle karşılaştırılır.» | «PVQuant, santralinizin saat saat ne üreteceğini 15 gün öncesinden söyler ve her saate bir iyimser–kötümser aralık ekler. Üretim programınız (KGÜP) teslim saatinden önce hazır olur; tahmin hatasının size kaç TL'ye mal olduğunu her gün panelde görürsünüz. Her tahmin, ertesi gün gerçekleşen üretimle karşılaştırılır; doğruluk karneniz gün gün birikir.» | «Ne işe yarıyor / hangi problemi çözüyor» ilk üç cümlede: program, TL, karne |
| Hero 2. düğme | «TL karşılığı nasıl hesaplanır» | «Dengesizlik maliyeti nasıl hesaplanır» | Piyasa terimi |
| Hero mikro satır | «başvuru · hesabınızı biz kurarız · veri yüklemeniz gerekmez · karneniz ilk gece sınavından itibaren birikir» | «başvuru · kurulumu biz yaparız · veri yüklemeniz gerekmez · doğruluk karneniz ilk günden birikmeye başlar» | Sadeleştirme |
| Dört adım başlığı | «Tahmin dört adımda doğar. Her adımı panelde görünür.» | «Dört adımlı, denetlenebilir tahmin süreci. Her adım panelde.» | Kullanıcı seçimi (21.10, 5 kurumsal seçenekten 3.) |
| Adım 1 | «Fizik modeli — Santralin geometrisinden yola çıkar — panel eğimi, tavan, kayıplar.» | «Santralinizin yapısı — Panel eğimi ve yönü, kurulu güç, inverter sınırı ve kayıplar: tahmin, santralinizin kendi özelliklerinden başlar.» | Yöntem adı → müşterinin tanıdığı özellikler («tavan» → «inverter sınırı») |
| Adım 2 | «Öğrenen model — Fiziğin gözden kaçırdığını santralin kendi geçmişinden öğrenir.» | «Geçmiş üretiminiz — Santralinizin geçmiş üretim verisiyle tahmin size özel ayarlanır; her yeni gün bu ayarı keskinleştirir.» | «Model» yerine fayda |
| Adım 3 | «Dürüst aralık — Tek sayı değil, gerçek hatayla ayarlanmış iyimser–kötümser bandı verir.» | «İyimser–kötümser aralık — Tek bir sayı değil, geçmiş hatalara göre ayarlanmış bir iyimser–kötümser aralık: programı hangi seviyeden vereceğinizi siz seçersiniz.» | Aralığın işletmeciye ne kazandırdığı |
| Adım 4 | «Gece karnesi — Her gece tahmin gerçekleşenle yüzleşir; kanıt birikir.» | «Her gece sınav — Günün tahmini gerçekleşen üretimle karşılaştırılır; doğruluk karneniz gün gün birikir.» | «Yüzleşir/kanıt» edebî; düz anlatım |
| Dört adım çıkış notu | «Zincirin çıkışı teslim kanallarıdır — TPYS'ye öneri CSV, toplayıcıya CSV/XLSX, REST API ve sabah webhook'u; masanıza göre ayrıntısı iş kartlarında.» | «Sonuç, kullandığınız kanala gider: üretim programı dosyası (CSV/XLSX, toplayıcı şablonuna uygun), doğrudan sisteminize API ile ve her sabah otomatik bildirimle; işinize göre ayrıntısı iş kartlarında.» | «Zincir/çıkış/webhook» jargonu kalktı |
| Ayna tablosu 1 | «Işınımı MWh'e kim çeviriyor?» / «Saatlik P10/P50/P90 üretim aralığı, 15 güne dek.» | «Hava tahminini üretime kim çeviriyor?» / «Her saat için iyimser, beklenen ve kötümser üretim; 15 gün ileriye.» | «Işınım», P-değerleri kalktı |
| Ayna tablosu 2 | «Tahmin tuttu mu, kim hesaplıyor?» / «Her gece gerçekleşenle karşılaştırılır; …» | «Tahmin tuttu mu, kim ölçüyor?» / «Her gece gerçekleşen üretimle karşılaştırılır; …» | Düz dil |
| Ayna tablosu 3 | «Sapmanın bedelini ne zaman görüyorsunuz?» / «Dengesizlik maliyetinin TL karşılığı panelde gün gün, teklif kantili önerisiyle.» | «Dengesizlik maliyetini ne zaman görüyorsunuz?» / «Panelde her gün TL olarak; gün öncesi teklifinizi hangi seviyeden vermeniz gerektiği önerisiyle.» | «Kantil» kalktı |
| Hangi iş için — giriş | «Aynı tahmin hattı dört masaya dört ayrı dille hizmet eder. Dördü de bugün panelde.» | «Aynı tahmin, santralinizdeki dört farklı işe hizmet eder. Dördü de bugün panelde.» | «Hat/masa/dil» iç jargonu |
| Program teslimi | «Programı teslim penceresi kapanmadan verin» / «Program dosyanız TPYS'ye öneri CSV, toplayıcıya CSV/XLSX olarak panelden iner; gün içi revizyon penceresi izlenir.» / Dosya: D‑1 öğleden sonra · Dilim: saatlik ya da 15 dk | «Üretim programınız (KGÜP) teslim saatinden önce hazır olsun» / «Yarının saatlik programı panelden dosya olarak iner (CSV/XLSX, toplayıcınızın şablonuna uygun); gün içi düzeltme fırsatları izlenir.» / Hazır: bir gün önce, öğleden sonra · Çözünürlük: saatlik ya da 15 dakika | KGÜP; «D‑1», «dilim», «TPYS» kalktı |
| Ticaret masası | «Teklifi önerilen kantille verin» / «Gün öncesi teklif için önerilen kantil panelde; sapmanın TL karşılığı gün gün.» / Teklif: önerilen kantil · Sapma: TL | «Gün öncesi teklifinizi doğru seviyeden verin» / «Gün öncesi piyasaya hangi miktarı teklif etmeniz gerektiği panelde önerilir; dengesizlik maliyetiniz her gün TL olarak görünür.» / Teklif: önerilen seviye · Dengesizlik: TL | «Kantil» → «seviye/miktar» |
| Operasyon nöbeti | «Nöbeti kurallar tutsun, sabah karne hazır olsun» / «Alarm kütüphanesi veri, teslim ve performans nöbetini tutar; gece karnesi her sabah hazırdır.» / Akış: REST API · sabah webhook'u | «Geceyi kurallar beklesin, sabah karne hazır olsun» / «Veri kesildi mi, program teslim edildi mi, üretim beklenenin altında mı: sekiz alarm kuralı sizin yerinize izler; sabah karne hazırdır.» / Bildirim: API · her sabah otomatik | Alarmın ne yakaladığı somutlaştı |
| Finansman dosyası | «Beklentiyi bileşenleriyle raporlayın» / «P50/P90 üretim beklentisi bileşenlerine ayrılmış belirsizlik bütçesiyle hesaplanır — dosya bağımsız doğrulamaya hazır biçimde.» | «Yatırımcıya ve bankaya üretim beklentisini raporlayın» / «Beklenen (P50) ve güvenli (P90) üretim, belirsizliğin nereden geldiği kalem kalem gösterilerek hesaplanır; dosya bağımsız denetime hazırdır.» | P50/P90 açıklamalı kaldı (finans okuru tanır); IEC/ASTM künyesi kaldı |
| Kanıt şeridi (karne yayına açılana dek görünen başlık) | «Her gece bir sınav, her sabah bir karne.» | «Tahmin doğruluğumuz her gün ölçülür ve kayda geçer.» | Kullanıcı seçimi (21.10, 5 kurumsal seçenekten 1.): mecaz yerine kurumsal, ölçülebilir ifade; çipler ve metrik adları aynı |
| Açık karne giriş | «Sistem her gece tahminini gerçekleşen üretimle karşılaştırır. Sonuç saklanmaz, süslenmez — panelde gün gün birikir.» | «Her gece günün tahmini gerçekleşen üretimle karşılaştırılır. Sonuç gizlenmez, düzeltilmez; panelde gün gün birikir.» | Düz dil |
| Açık karne «Sıkı referans» alt etiketi | «iklim + akıllı süreklilik» | «iklim beklentisi + süreklilik» | «Akıllı» boş sıfat |
| Rakamlar başlığı | «Disiplin, tarihli rakamla.» | «Vaat değil, tarihli rakam.» | Dürüstlük konumu düz söylendi |
| Rakamlar — 8 alarm kuralı | «veri, teslim ve performans nöbetini kurallar tutar» | «veri akışı, program teslimi ve üretim performansı izlenir» | Somut |
| SSS — güven sorusu | «Tahmin zinciri açıktır: fizik modeli santralin geometrisinden kurar, öğrenen düzeltme santralin kendi geçmişinden gelir, dürüst aralık gerçek hatayla ayarlanır, gece karşılaştırması da sonucu ölçer.» | «Tahminin nasıl oluştuğu açıktır: santralinizin yapısından başlar, geçmiş üretiminizle size özel ayarlanır, iyimser–kötümser aralık geçmiş hatalara göre kurulur ve her gece sonuç ölçülür.» | Dört adımla aynı adlar |
| SSS — fiyat | «Fiyatlandırma, kurulu güç başına aylık abonelik modeline dayanır…» | «Fiyat, kurulu güç (MW) başına aylık aboneliktir…» | Birim |
| Başvuru giriş | «E-postanızı bırakın; hesabınızı kuralım, ilk gece sınavından itibaren karneniz birikmeye başlasın. Fiyatlandırma kurulu güç başına aylık aboneliktir, santral sayısına göre şekillenir — teklif başvuruyla gelir.» | «E-postanızı bırakın; hesabınızı biz kuralım, doğruluk karneniz ilk günden birikmeye başlasın. Fiyat, kurulu güç (MW) başına aylık aboneliktir ve santral sayısına göre belirlenir; teklif başvurunuza e-postayla gelir.» | Birim, kanal |
| Altbilgi alt satır | «Güneş santralleri için. Fizikten başlar, geçmişinizden öğrenir.» | «Güneş santralleri için. Santralinizin yapısından başlar, geçmiş üretiminizden öğrenir.» | Adımlarla aynı dil |
| Mega menü — Kalibrasyon | «Üretim verinizle santralinize özgü model; kayıp ağacı ve güç matrisi» | «Üretim verinizle tahmin santralinize özel ayarlanır; kayıp kalemleri ve güç tablosu» | «Ağaç/matris» yazılım dili (sayfa adı «Kalibrasyon» panelle aynı kaldı) |
| Mega menü — Alarmlar | «Veri gelmedi, isabet düştü, KGÜP penceresi kaçtı… sekiz kural» | «Veri gelmedi, doğruluk düştü, KGÜP teslim saati kaçtı… sekiz kural» | «İsabet/pencere» |
| Mega menü — KGÜP / Dengesizlik | «teslim penceresi ve revizyon kapısı izlenir» / «gün gün TL karşılığı» | «teslim saati ve gün içi düzeltme fırsatı izlenir» / «her gün TL karşılığı» | Düz dil |
| `<title>` / açıklama / OG | «PVQuant — Kanıtla konuşan üretim tahmini» / «…iyimser–kötümser bant, KGÜP programı, sapmanın TL karşılığı… Pembe vaat değil, ölçülmüş dürüstlük.» | «PVQuant — Güneş santralleri için üretim tahmini ve doğruluk karnesi» / «Güneş santralleri (GES) için saatlik üretim tahmini, hazır üretim programı (KGÜP), dengesizlik maliyetinin günlük TL karşılığı ve her gece ölçülen doğruluk karnesi.» | Arama ve paylaşım kartında ürünün ne olduğu ilk kelimelerde |

### /yontem — Türkiye piyasası bölümü

| Yer | Eski | Yeni |
|---|---|---|
| Başlık | «Tahmin hatasının maliyetini TL olarak görün.» | «Dengesizlik maliyetinizi her gün TL olarak görün.» |
| Giriş | «Elektrik piyasasında her santral, ertesi gün ne üreteceğini önceden bildirmekle yükümlüdür; gerçekleşen üretim bu programdan saptığında aradaki fark santrale fatura edilir. PVQuant üretim programınızı hazırlar, gün içi güncelleme fırsatlarını izler ve sapmanın size maliyetini her gün TL olarak raporlar.» | «Elektrik piyasasında her santral, ertesi gün saat saat ne üreteceğini önceden bildirir: üretim programı (KGÜP). Gerçekleşen üretim bu programdan saptığında aradaki fark dengesizlik maliyeti olarak santrale yansır. PVQuant programınızı hazırlar, gün içi düzeltme fırsatlarını izler ve dengesizliğin size maliyetini her gün TL olarak raporlar.» |
| Kart adları | Sapma maliyeti · Şablonlu dışa verim · Alarm kütüphanesi · Gün içi aralık | Dengesizlik maliyeti · Hazır şablonla dışa aktarım · Alarm kuralları · Gün içi güncelleme |
| Gün içi kartı | «İyimser–kötümser bant gün içinde güncellendikçe önceki hâlleri izde kalır; sabah koşusu bitince webhook sisteminize haber verir.» / künye «gün içi revizyon», «sabah webhook'u» | «İyimser–kötümser aralık gün içinde güncellendikçe önceki hâlleri kayıtta kalır; sabah hesabı bitince sisteminize otomatik bildirim gider.» / «gün içi güncelleme», «sabah bildirimi (webhook)» |

**Değişmeyenler (bilinçli):** h1 (satır kırılımı ve vurgu tasarımın parçası; anlaşılır), bölüm çubuğu adları, metrik adları ve
tanımları (`yontem-metni.ts` hesapla eşlenmiş tek kaynak; `mantik.test` pinleri), kilitli karne metni, ilkeler, SSS'nin ilk
beş sorusu (zaten düz dil), /yontem'in yöntem bölümleri (teknik okur için yazılmış, amaç o), masa adları (test pini).

## 4. Yapılmayanlar ve öneriler

- **Blok başına 5 seçenek sunma kuralı** (`emsaller.md` v2.392): bu turda her blok için tek öneri uygulandı; §3 tablosu
  eski/yeni karşılaştırması olarak yerine geçer. Beğenilmeyen satır için alternatif üretilip tek commit'le değiştirilebilir.
- Lisanssız santraller ve toplayıcı kapsamı: sitede «lisanslı/lisanssız» ayrımı yapılmadı — ürün gerçeği (hangi santral
  türlerine hizmet verildiği) bu depoda yazılı değil; doğrulanmadan vaat yazılmadı.
- Tolerans oranları (%8 güneş) metne alınmadı; EPDK kararıyla değişiyor.
- /yontem'in yöntem/metrik bölümleri teknik kaldı; hedef okuru o.

## 5. Kontroller (hepsi bulut oturumunda çalıştırıldı)

| Kontrol | Sonuç |
|---|---|
| `npm test` (71 test; gizlilik/yapı/mantık/tıklama pinleri dahil) | **71/71** — her metin commit'inden sonra tekrar koştu (adfe316, 9005517, 111780a) |
| `npx tsc --noEmit`, `npm run build`, `npx oxlint src/features` | 0 / 0 / 0 (oxlint'teki 2 uyarı önceden var, dokunulmayan dosyada) |
| Yasak terim taraması (`gizlilik.test`: yöntem ve kaynak adları, «şeffaf») | geçti; yeni metinlerde yöntem/kütüphane/kaynak adı yok |
| CDP taraması (`pvquant-tasarim/betikler/tarama.mjs`; «/» ve «/yontem», 320/375/390/768/1081/1440/1920 px) | **taşma 0, çift id 0, isimsiz etkileşimli 0, alt'sız görsel 0**; küçük dokunma hedefi (<44 px) sayıları önceki derlemeyle birebir aynı (ana 7/8/8, /yontem 1 — önceden var, bu turun konusu değil); son derleme 111780a'da tekrar: temiz |
| Ekran görüntüleri — önce (2cb5fbf) ↔ sonra (adfe316): Chromium 156, Firefox 157, WebKit 27.2 × 390/768/1440/1920 × «/», «/yontem», giriş (2 × 60 görüntü, hareket azaltma kipinde) | Kırpılan/üst üste binen metin yok; kart ızgaraları eşit yükseklikte; üç motorda sayfa yüksekliği ±2 px aynı (aşağıdaki tablo) |
| Son derleme (111780a) Chromium 390/1440 görüntüleri + gözle kontrol (hero, Dört adım, Hangi iş için, /yontem Türkiye piyasası, altbilgi) | Düzgün; iş kartı başlıkları 1440'ta dörtte de 3 satır; hero girişi 390'da 7 satır, 1440'ta 6 satır |

**Sayfa yüksekliği önce → sonra (CSS px; metin uzadıkça sayfa uzar — düzen değişmedi):**

| Motor | Görünüm | «/» | «/yontem» |
|---|---|---:|---:|
| Chromium | 390×844 | 12 539 → 12 887 (son 111780a: 12 860) | 8 853 → 8 853 |
| Chromium | 768×1024 | 10 225 → 10 487 | 6 955 → 7 050 |
| Chromium | 1440×900 | 7 611 → 7 723 (son: 7 718) | 5 188 → 5 188 |
| Chromium | 1920×1080 | 7 701 → 7 813 | 5 218 → 5 231 |
| Firefox | 390 / 768 / 1440 / 1920 | 12 540 → 12 888 · 10 226 → 10 489 · 7 612 → 7 724 · 7 702 → 7 814 | 8 853 → 8 853 · 6 955 → 7 051 · 5 188 → 5 188 · 5 218 → 5 231 |
| WebKit | 390 / 768 / 1440 / 1920 | 12 542 → 12 890 · 10 227 → 10 512 · 7 613 → 7 725 · 7 702 → 7 814 | 8 853 → 8 853 · 6 955 → 7 073 · 5 188 → 5 188 · 5 218 → 5 231 |

Artış kaynağı: hero girişi (+1 satır dar ekranda; sonra 1 cümle kısaltıldı), Dört adım ve iş kartlarının açıklama cümleleri (+1–2 satır),
ayna tablosu cevapları. Hiçbir bileşen eklenmedi/çıkarılmadı; CSS değişmedi.

**Bu turda yapılmayan kontroller:** gerçek Safari/iOS ve Android cihaz (Linux WebKit/Chromium kullanıldı), panel içi metinler
(kapsam dışı), canlıya alma (ssh bulutta yok; `git pull && docker compose build web && docker compose up -d` yerel oturumdan).
Ham veri: `perf/analiz/fable5-icerik/` (depo dışı; görüntüler 2 × 60 + 2 × 10, tarama JSON'ları).

## 6. Ortam ve teslim

Bu turun bütün adımları (araştırma, kod incelemesi, metin düzenlemesi, testler, derleme, ekran görüntüleri, rapor) bulut
oturumunda yapıldı; yerel oturum kullanılmadı. Bulut kredi tüketimi bu ortamdan okunamıyor (**doğrulanamadı**). Commit'ler:
adfe316 (metinler), 9005517 (başlık kısaltma + «dengesizlik» tutarlılığı), 111780a (hero girişi kısaltma), rapor commit'i. PR #9.
