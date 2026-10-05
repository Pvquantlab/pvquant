# 2. Aşama — Sektör araştırması (yalnız kartlar)

## Yöntem — önce bunu okuyun

**2026-10-05 güncellemesi:** ağ erişimi açıldıktan sonra 13 sitenin **hepsi** tarayıcıyla
(Chromium, 1440 px) gezildi; canlı pvquant.com da açıldı. Her sitenin tam sayfa görüntüsü ve kart
ızgaralarının kırpımları `arastirma-ekran/` altında:

| Kod | Site | Dosyalar |
|---|---|---|
| 01 | pvquant.com (canlı) | `01-pvquant-canli-*.jpg` — yerelde incelenen v2.392 ile aynı |
| 10 | Datadog | `10-datadog-*.jpg` (ilk ziyarette görseller engelliydi; `10-datadog-tam.jpg` ve `10-datadog-urun-bolumu.jpg` görsellerle yeniden çekildi) |
| 11 | Stripe | `11-stripe-tam.jpg`, `11-stripe-kart-*.jpg` |
| 12 | Linear | `12-linear-tam.jpg`, `12-linear-bolum-*.jpg`, `12-linear-kart-*.jpg` |
| 13 | Vercel | `13-vercel-tam.jpg` (sayfanın alt yarısı geç yüklendiği için boş çizildi) |
| 14 | Databricks | `14-databricks-*.jpg` |
| 15 | Hex | `15-hex-*.jpg` |
| 16 | Modo Energy | `16-modo-*.jpg` |
| 17 | Kpler | `17-kpler-*.jpg` (çerez penceresi kartların ortasını örtüyor; onay verilmedi) |
| 18 | Solargis | `18-solargis-*.jpg` |
| 19 | Solcast | `19-solcast-*.jpg` |
| 20 | Amperon | `20-amperon-*.jpg` |
| 21 | Aurora Solar | `21-aurora-*.jpg` |
| 22 | Dexter Energy | `22-dexter-*.jpg` |

İşaretler: **[Z]** = bu oturumda ziyaret edilip görüntüsü alınan gözlem · **[A]** = web araması
sonucu (kaynak §2.4). Önceki sürümdeki «önceki bilgi» satırlarının (G) hepsinin yerini [Z] aldı.
Hiçbir sitede form gönderilmedi; çerez pencerelerinde onay verilmedi. Rakip alıntıları özgün dilinde.

## 2.1 Marka marka kart dersleri

### Enterprise SaaS

**Stripe** [Z] — Bölüm başlığı **iki tonlu**: koyu cümle + gri devam («Powering businesses of all
sizes. *Run your business on a reliable platform that adapts to your needs.*»). İçerik, sayfa boyunca
inen **ince dikey çizgilerle çerçeveli bir ızgarada** duruyor; kartlar çoğu yerde kutu değil, çizgiyle
ayrılmış alan. Ürün kartlarının görseli gerçek arayüz parçası (ödeme formu, fatura). Vaka satırında
etiket–değer dizisi: «160 countries · 11K+ locations globally · **Products used** Payments, Terminal,
Connect…». [A] «Accept and optimize payments globally…».
**Ders →** Çizgiyle bölünmüş ızgara ve «görsel = ürün parçası» seçtiğimiz C'yi doğruluyor.
*Kaçınılacak:* müşteri logo duvarı ve «50% of Fortune 100…» türü oran (anayasa 1–2).

**Linear** [Z] — Koyu zemin. «Purpose-built / Powered by agents / Designed for speed» üçlüsü
**kutusuz**: sütunlar ince dikey çizgiyle ayrılmış, her sütunun üstünde mono «FIG 0.1 / 0.2 / 0.3»
etiketi, tek renkli izometrik çizgi çizim, kısa ad, iki satır gövde (`12-linear-bolum-1.jpg`).
Bölümlerde başlık solda («Intake and integrations»), tek açıklama sağda, altında gerçek ürün arayüzü
ve sade bir «Features» listesi (`12-linear-bolum-2.jpg`). Bölüm başlığı yine iki tonlu.
**Ders →** C'nin üç kararı burada birebir var: 1 px ayraçlı hücre, mono küçük etiket, tek renkli
çizim. Linear'ın çizimleri soyut; bizimkiler veri taşıdığı için bir adım ileride.

**Vercel** [Z] — «Build agents on infrastructure that thinks like them» bölümü: solda gerçek ürün
penceresi, sağda müşteri sonucu («Notion powers millions of agent conversations daily on Vercel») ve
altında yalın «Features» listesi (Durable Orchestration, Sandboxed Environments…). Tipografi siyah-beyaz,
süs yok. Sayfanın alt yarısı geç yüklendiği için görüntüde boş kaldı.
**Ders →** Teknik ayrıntı süslü cümle yerine düz liste/künye olarak. *Kaçınılacak:* «Agentic
Infrastructure» manşeti, logo şeridi.

**Datadog** [Z, 2026-10-05: ana sayfa ve `/product/`] — *ad kalıbı:* ana sayfadaki ürün
akordeonunda düz ürün adı + tek satır sonuç: «Infrastructure — From overview to deep details, fast»,
ardından «Learn more ›». `/product/` sayfasında ise bölüm başlıkları **fayda cümlesi**: «See across
systems, apps, and services», «Analyze and explore log data in context», «Get alerted on critical
issues»; ürün adı yalnız üstteki alt menüde. Her başlığın altında tek giriş cümlesi, sonra 4–5
maddelik somut özellik listesi, sonra «LEARN MORE»; görsel sağ/sol dönüşümlü. Etiketli kartlarda
hiyerarşi: büyük harfli küçük etiket («READ THE REPORT», «CAREERS») → başlık («State of Postgres»)
→ 3–4 satır gövde → «LEARN MORE ›». Tipografi sans; mono yok. Renk: mor yalnız eylemde ve bağlantıda.
*Görsel:* [Z] ürün akordeonunun yanında gerçek gösterge paneli görüntüsü; etkinlik ve e-kitap bantlarında yoğun mor gradyan ve sahne fotoğrafı (`10-datadog-urun-bolumu.jpg`, erişim açıldıktan sonra görsellerle yeniden çekildi).
**Ders →** (1) Başlık fayda, teknik ayrıntı altındaki listede: bizim «tek cümle + künye çipleri»
kalıbımızı doğruluyor. (2) Etiket → başlık → gövde → bağlantı dört katı burada da var.
*Kaçınılacak (bu ziyarette görüldü):* «AI-Powered Observability and Security» manşeti ve «empowers
organizations to decode runtime execution… with agentic speed» gibi süslü gövde; «Thousands of
customers love & trust Datadog» logo duvarı (anayasa madde 2); camgöbeğinden yeşile gradyan zeminli
kart («State of Postgres»); yoğun mor gradyan bantlar. PVQuant'ın sakin «Ufuk» diline uymaz.

### Data / Analytics

**Databricks** [Z] — Mono büyük harfli bölüm etiketi («FEATURED PRODUCTS», «PROVEN IMPACT»). Dört
koyu kart: renkli marka ikonu + ürün adı + sağ üstte ok + tek cümle («Lakebase — The first serverless
Postgres database integrated with the lakehouse, built for the AI era.»). Adlar uydurma alt markalar
(Lakebase, Genie, Unity Gateway). [A] Lakeflow, Unity Catalog.
**Ders (ters) →** Mono etiket iyi; alt marka çoğaltma ve «built for the AI era» dili beş kartlık bir
bölüm için yapay durur.

**Hex** [Z] — İki sütunlu büyük kartlar: üstte **noktalı (benekli) zeminde** görsel — gerçek ürün
parçası («Suggestions» paneli), entegrasyon logoları ya da izometrik çizim; altta **mono, renkli
çerçeveli etiket** («Self-learning», «Easy to set up»), sorunla açılan başlık («Setting up context is
one thing, but managing changes can be a headache»), gövde, düğme (`15-hex-kart-1.jpg`).
**Ders →** Benekli zemin + gerçek ürün parçası, bizim gren/benek dilimizle aynı aile. *Kaçınılacak:*
her kartta ayrı renkli etiket (renk anlam taşımıyor), «AI-powered self-serve» dili, G2 puanı ve
müşteri alıntıları (anayasa 2).

**Modo Energy** [Z] — Bölümün en güçlü örneği (`16-modo-kart-1.jpg`): üç kartın üst yarısı **gerçek
ürün parçası** — yıllara göre tahmin çubuk grafiği, eksenli; endeks satırları (birim «GBP/MW», ad «ME
BESS GB», küçük çizgi grafik, değer ve değişim); analist notu metni. Altında ürün adı + «↗» + tek
cümle: «**Bankable Forecasts** — Nodal forecasts for solar, wind, data centers, and batteries, built
for financing.» Gövde serif, sakin; renk yalnız değişim okunda. [A] «fully reconstructable methodology».
**Ders →** «Görsel = ürünün ürettiği veri» kararımızın en net doğrulaması. Ad ürün nesnesi (bizim
isim kümesi A ile aynı kalıp). *Kaçınılacak:* «cited by Bloomberg, the FT…» türü atıf (bizde yok).

**Kpler** [Z] — Bölüm başlığı iki tonlu («Track *with confidence* through uncertainty.»). Üç koyu
kart, zeminde veri görüntüsü (gemi rotası noktaları, gösterge paneli); kartın altında **fiil
etiketi** «Monitor / Understand / Act» + fayda başlığı («Observe real time seaborne trade flows»).
Haber kartlarında tarih + kategori etiketi. [A] Terminal · API · Snowflake teslim kanalları.
**Ders →** Kartları bir iş akışının adımları gibi etiketlemek (bizde zaman etiketleri). Teslim
kanallarının açık sayılması K3'ü destekliyor.

### EnergyTech

**Solargis** [Z] — Altı **eşit** beyaz kart, her birinde marka kırmızısı **süs çizgi ikon** (konum
iğnesi, monitör, gösterge), fayda başlığı («Find the right solar project location», «Discover true
output»), üç satır gövde, «Explore →» (`18-solargis-kart-3.jpg`). Bir başka ızgarada «1500+ locations»,
«20 years» türü sayılar.
**Ders →** Başlıkların iş sonucu dili iyi; ama kart kalıbı, analizde «AI üretti» dediğimiz kalıbın ta
kendisi: eşit kutular + anlam taşımayan ikonlar. Bilinçli olarak bundan uzak durduk.

**Solcast** [Z] — Üç kart: üstte **stok fotoğraf** (bulut uydu görüntüsü, rüzgâr türbinleri, güneş
tarlası), altında **ortalanmış** başlık ve gövde, gölgeli kutu (`19-solcast-kart-1.jpg`). [A] «5 minutes
to 14 days ahead», «P10/P50/P90», «JSON or CSV» gibi teknik değerler başka sayfalarda.
**Ders →** Teknik değerler künye için iyi kaynak. *Kaçınılacak:* stok fotoğraf, ortalanmış gövde,
gölge, «350 customers / 300 GW» türü iddia.

**Amperon** [Z] — Rol sekmeleri (Utility · Financial trader · Retailer · IPP · C&I) altında dört kart:
stok fotoğraf → ad («Power markets trading») → gövde → **ince çizgili etiket–değer satırları**
(«Grids across NA, Europe and AU · 26», «Capacity payments avoided annually · $50M+») → «Learn more»
(`20-amperon-kart-1.jpg`). Sayfada ödül duvarı, logo şeridi, sayfa içi form.
**Ders →** Künye kalıbımızın kaynağı doğrulandı (etiket–değer, ince ayraç). *Kaçınılacak:* değerlerin
kaynaksız iddia olması — bizim künyede yalnız ürün özellikleri (saatlik, CSV · XLSX, 8 kural) var.
Rol sekmeleri bizde «Hangi iş için?» bölümünde zaten karşılanıyor.

**Aurora Solar** [Z] — Koyu, noktalı zemin; üç sütun: kare çerçeveli küçük çizgi ikon, fayda başlığı
(«Accuracy, not approximations», «Automation across the whole job»), somut gövde («design, pricing,
contracting, and permitting») (`21-aurora-kart-1.jpg`). [A] «models the roof, places panels, runs
shading analysis…».
**Ders →** Gövdede somut iş adımları sıralamak. «X, not Y» başlık kalıbı akılda kalıcı ama yapay
zekâ metinlerinde de sık; kullanmadık.

**Dexter Energy** [Z] — «Why work with us?» yanında **kademeli dizilmiş, çok yuvarlatılmış** (≈32 px)
açık camgöbeği kartlar; ince çizgi ikon (biri kesik çizgili tahmin eğrisi), serif başlık («High-accuracy
forecasting», «Scalable API»), gövdede «Our advanced AI stack interprets massive data streams…»
(`22-dexter-kart-2.jpg`). Vaka kartları «Learn more →». [A] gün öncesi → gün içi → dengeleme
zaman çizelgesi dili.
**Ders →** Tahmin eğrisini ikon yapmak doğru yönde ama süs düzeyinde kalıyor; bizde eğri gerçek
diyagram. *Kaçınılacak:* aşırı yuvarlak köşe, kademeli yerleşim, «advanced AI stack» dili.

## 2.2 Sentez — beş ders (ziyaretlerle güncellendi)

1. **Ad = ürünün nesnesi ya da yaptığı iş; slogan değil.** Modo («Bankable Forecasts»), Databricks,
   Datadog ürün adı; Solargis, Kpler, Aurora iş sonucu başlığı kullanıyor. «Tek tık», «hazır» gibi
   durum ya da slogan adı hiçbirinde yok.
2. **Görsel = ürünün gerçek parçası ya da verisi.** Modo (tahmin grafiği, endeks satırları), Stripe,
   Linear, Hex (arayüz kesiti) bunu yapıyor. Süs ikonu kullananlar (Solargis, Databricks, Dexter) ve
   stok fotoğraf kullananlar (Solcast, Amperon) en jenerik görünenler.
3. **Kutusuz, çizgiyle bölünmüş ızgara üst segmentin dili.** Linear ve Stripe kartları kutu yerine
   1 px ayraçla ayırıyor; mono küçük etiket (Linear «FIG 0.1», Databricks, Hex) bu dilin parçası.
   Tasarım C bu kalıbı izliyor.
4. **Hiyerarşi dört katlı:** etiket → başlık → tek cümle → künye ya da liste. Amperon'un etiket–değer
   satırları, Datadog ve Vercel'in özellik listeleri teknik ayrıntıyı gövdeden ayırıyor.
5. **Güven yöntemden gelir, rakamdan değil.** En güçlü örnek (Modo) iddiayı yöntemle kuruyor
   («built for financing», «reconstructable methodology»); en zayıflar kaynaksız sayıyla («$50M+»,
   «3x more accurate», «350 customers»).

**Kararlara etkisi:** ziyaretler seçilen yönü **değiştirmiyor, güçlendiriyor**. C'nin 1 px ayraçlı
hücreleri (Linear, Stripe), mono etiketi (Linear, Databricks), veri diyagramı (Modo) ve künyesi
(Amperon kalıbı, rakamsız) sektörün en iyi örnekleriyle örtüşüyor. Kart koduna ve yamaya değişiklik
gerekmedi. Kapsam dışı bir gözlem: Stripe, Linear ve Kpler'in **iki tonlu bölüm başlığı** (koyu cümle
+ gri devam) bölüm başlıkları için ayrı bir işte değerlendirilebilir.

## 2.3 Kaçınılacaklar listesi (ziyaretlerde görülen örneklerle)

- Gradyan zeminli kart (Datadog «State of Postgres»; bizde eski şeftali zeminli iki kart).
- Aşırı yuvarlatılmış ve kademeli kartlar (Dexter), kart başına gölge (Solcast).
- Süs ikonu: Solargis'in kırmızı çizgi ikonları, Databricks'in renkli marka ikonları; bizde eski ₺
  jetonu, zil, `</>`, imleç, bayrak, onay rozeti.
- Stok fotoğraf (Solcast, Amperon), ortalanmış gövde metni (Solcast).
- «AI-Powered» (Datadog), «Agentic Infrastructure» (Vercel), «built for the AI era» (Databricks),
  «advanced AI stack» (Dexter) dili; bizde «akıllı», «tek tık», «sorunsuz».
- Kaynaksız sayı ve oran (Amperon «$50M+», Stripe «50% of Fortune 100», Solargis «1500+»).
- Logo duvarı, ödül duvarı, G2 puanı, müşteri alıntısı (Datadog, Stripe, Hex, Amperon).
- Her karta ayrı, anlamsız renk (Hex etiketleri).
- Uydurma alt marka adları (Databricks).
- Eşit ağırlıklı, aynı kalıp kartlar (Solargis altılı ızgara).
- Aynı yetinin birden çok kartta tekrarı (eski TL bölümünde «TL gün gün» üç yerde).

## 2.4 Kaynaklar

**Ziyaret edilen [Z]** (2026-10-05, Chromium 1440 px): https://pvquant.com/ · https://www.datadoghq.com/ ·
https://www.datadoghq.com/product/ · https://stripe.com/ · https://linear.app/ · https://vercel.com/ ·
https://www.databricks.com/ · https://hex.tech/ · https://modoenergy.com/ · https://www.kpler.com/ ·
https://solargis.com/ · https://solcast.com/ · https://www.amperon.co/ · https://aurorasolar.com/ ·
https://dexterenergy.ai/

**Arama sonuçları [A]:**

- Stripe: https://stripe.com/payments · https://stripe.com/payments/elements
- Linear: https://linear.app/features · https://linear.app/docs/insights · https://linear.app/now/how-we-redesigned-the-linear-ui
- Vercel: https://vercel.com/platform · https://vercel.com/docs/glossary
- Datadog: https://www.datadoghq.com/product/ · https://www.datadoghq.com/product/apm/
- Databricks: https://www.databricks.com/blog/introducing-databricks-lakeflow · https://docs.databricks.com/aws/en/lakehouse-architecture/scope
- Hex: https://hex.tech/ · https://learn.hex.tech/docs/explore-data/threads
- Modo Energy: https://modoenergy.com/product/benchmarks · https://modoenergy.com/research/en/terminal-product-launch-battery-energy-storage-bankable-forecast-benchmark-indices-data-explorer-portfolio-november-2024
- Kpler: https://www.kpler.com/solution/trader-tools
- Solargis: https://solargis.com/products/forecast · https://solargis.com/products/prospect
- Solcast: https://solcast.com/forecast-solar-irradiance-data · https://solcastglobal.com/solar-data-api/api/utility-scale-solar/
- Amperon: https://www.amperon.co/ · https://www.amperon.co/solutions/asset-management-optimization
- Aurora Solar: https://aurorasolar.com/design-mode/ · https://aurorasolar.com/sales-mode/
- Dexter Energy: https://dexterenergy.ai/solutions/ · https://dexterenergy.ai/news/forecasting-wind-and-solar-for-short-term-power-trading/
