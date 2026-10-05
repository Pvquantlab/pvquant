# 2. Aşama — Sektör araştırması (yalnız kartlar)

## Yöntem ve sınır — önce bunu okuyun

Bu oturumun ağ politikası pvquant.com'u ve incelenecek rakip sitelerinin 13'ünden 12'sini
(stripe.com, linear.app, vercel.com, databricks.com, hex.tech, modoenergy.com, kpler.com,
solargis.com, solcast.com, amperon.co, aurorasolar.com, dexterenergy.ai) **engelledi**; web arşivi
(archive.org, archive.ph) de kapalı. 2026-10-05'te tarayıcıyla yeniden denendi: hepsi
`ERR_TUNNEL_CONNECTION_FAILED`. Bu nedenle:

- **Gerçekten gezilen tek rakip Datadog** (datadoghq.com açık). Ekran görüntüleri
  `arastirma-ekran/10-datadog-*.jpg`. Sayfanın görselleri gelmedi (görsel alan adı
  `corp.dd-static.net` engelli); düzen, metin ve tipografi görünüyor.
- Diğer 12 marka için kanıt iki kaynaktan: **[A]** bu oturumda yapılan web aramalarının döndürdüğü
  sayfa metinleri (aşağıda kaynak bağlantısıyla), **[G]** bu markaların sitelerine dair önceki
  gözlemim. [G] işaretli satırlar tarihli değildir ve sitelerin bugünkü hâlinden farklı olabilir.
  **[Z]** = bu oturumda tarayıcıyla ziyaret edilip görüntüsü alınan gözlem.
- Kalan siteleri gezmek için ortamın ağ erişiminin genişletilmesi gerekir (bkz. BENIOKU).
- Rakip alıntıları özgün dilinde bırakıldı.

## 2.1 Marka marka kart dersleri

### Enterprise SaaS

**Stripe** — *ad kalıbı:* ürün adı (Payments, Billing, Connect) küçük bir üst etiket, asıl başlık
fayda cümlesi. [G] *Görsel:* ikon değil, ürünün **gerçek arayüz parçası** (ödeme formu, fatura
satırı, grafik kesiti); kartın resmi ürünün kendisi. *Hiyerarşi:* etiket → fayda başlığı → tek
cümle → «Learn more». *Renk:* tek vurgu rengi yalnız eylem ve ürün etiketinde. [A] Arama:
«Their suite of optimized and composable UIs…», tasarım dili «generous white space, clear
typography hierarchy… purposeful blue color for primary actions».
**Ders →** Vinyet, ürünün panelde gerçekten ürettiği nesnenin (program tablosu, TL satırı,
şablon hücresi) çizimi olmalı. Kart 1'deki bayrak ve onaylı belge ikonu bu dersle çelişiyor.

**Linear** — *ad kalıbı:* tek kelimelik ürün nesnesi: «Issues», «Cycles», «Insights», «Triage».
[A] «Cycles – time-boxed periods…», «Insights provides real-time analytics…». *Görsel:* [G]
tek renkli, kısık tonlu arayüz kesitleri; dekoratif ikon yok. *Yeniden tasarım notu:* [A] «reduce
visual noise, maintain visual alignment, and increase the hierarchy and density».
**Ders →** Adı ürünün iç sözlüğünden alın; bir modül adı iki kelimeyi geçmesin. Görsel gürültüyü
azaltmak hiyerarşiyi artırır.

**Vercel** — *ad kalıbı:* ürün adı + tek satır sonuç: «Previews — A URL for every commit»,
«Observability», «Fluid compute». [A] *Yerleşim:* [G] kart kutusu yerine 1 px'lik çizgilerle
bölünmüş ızgara (hairline grid), mono etiketler, siyah-beyaz.
**Ders →** «Ad + tek satır somut sonuç» kalıbı. Kutusuz, çizgiyle bölünmüş ızgara, eşit kart
yığını görünümünü kırar.

**Datadog** [Z, 2026-10-05: ana sayfa ve `/product/`] — *ad kalıbı:* ana sayfadaki ürün
akordeonunda düz ürün adı + tek satır sonuç: «Infrastructure — From overview to deep details, fast»,
ardından «Learn more ›». `/product/` sayfasında ise bölüm başlıkları **fayda cümlesi**: «See across
systems, apps, and services», «Analyze and explore log data in context», «Get alerted on critical
issues»; ürün adı yalnız üstteki alt menüde. Her başlığın altında tek giriş cümlesi, sonra 4–5
maddelik somut özellik listesi, sonra «LEARN MORE»; görsel sağ/sol dönüşümlü. Etiketli kartlarda
hiyerarşi: büyük harfli küçük etiket («READ THE REPORT», «CAREERS») → başlık («State of Postgres»)
→ 3–4 satır gövde → «LEARN MORE ›». Tipografi sans; mono yok. Renk: mor yalnız eylemde ve bağlantıda.
*Görsel:* [G] gerçek gösterge paneli görüntüleri (bu ziyarette görseller yüklenmedi).
**Ders →** (1) Başlık fayda, teknik ayrıntı altındaki listede: bizim «tek cümle + künye çipleri»
kalıbımızı doğruluyor. (2) Etiket → başlık → gövde → bağlantı dört katı burada da var.
*Kaçınılacak (bu ziyarette görüldü):* «AI-Powered Observability and Security» manşeti ve «empowers
organizations to decode runtime execution… with agentic speed» gibi süslü gövde; «Thousands of
customers love & trust Datadog» logo duvarı (anayasa madde 2); camgöbeğinden yeşile gradyan zeminli
kart («State of Postgres»); yoğun mor gradyan bantlar. PVQuant'ın sakin «Ufuk» diline uymaz.

### Data / Analytics

**Databricks** — *ad kalıbı:* icat edilmiş alt markalar («Lakeflow», «Unity Catalog»,
«Databricks SQL»). [A]
**Ders (ters) →** Beş kartlık küçük bir bölüm için alt marka uydurmak (ör. «PVQuant Flow»)
yapay durur. Kullanmayın.

**Hex** — *ad kalıbı:* ürün nesnesi («Threads», «Explore», «Notebooks»). [A] Metinlerde «agentic»,
«AI-powered» yoğun.
**Ders →** Nesne adı iyi; «AI/agentic» süs dili kaçınılacaklar listesinde.

**Modo Energy** — *ad kalıbı:* finans sözlüğünden nesneler: «Terminal», «Benchmarks», «Indices»,
«Forecasts». [A] Güven dili sayıdan çok **yöntemden** geliyor: «built on a published, fully
reconstructable methodology», «Transparent revenue forecasts… built for financing». [A]
**Ders →** Güveni «sonuç rakamı» değil «nasıl hesaplandığı belli» cümlesi kurar. PVQuant'ın
dürüstlük anayasasıyla birebir uyumlu: kart 2'nin künyesi «basit yönteme karşı, kendi verinizle»
diyebilir.

**Kpler** — teslim kanalı mantığı: [A] «access data through the Kpler Terminal…, use APIs to
embed insights into proprietary trading systems, or integrate via Snowflake».
**Ders →** Dışa verim kartı (kart 3), **kanalları** künye olarak sıralamalı: panel dosyası →
şablon (saatlik/15 dk) → API anahtarı. Kart görseli kanal diyagramı olabilir.

### EnergyTech

**Solargis** — *ad kalıbı:* yaşam döngüsünü izleyen tek kelimelik fiil-adlar: «Prospect»,
«Evaluate», «Monitor», «Forecast». [A] Her biri bir alt satırla: «solar power output forecast for
up to 14 days», «real-time PV output assessment». [A]
**Ders →** Beş adın tek dilbilgisi kalıbında, bir iş akışının adımları gibi okunması güçlü bir
marka sinyali. Teknik süre (14 gün) künyede.

**Solcast** — teknik özellik dili: [A] «5 minutes to 14 days ahead», «P10/P50/P90», «JSON or
CSV», «API uptime of >99.99%». Aynı sayfada «over 350 customers managing 300 GW».
**Ders →** Teknik değerler etiket–değer künyesine çok iyi oturuyor. *Kaçınılacak:* müşteri sayısı
ve GW iddiası, anayasa madde 1 gereği PVQuant'ta yasak.

**Amperon** — *ad kalıbı:* ürün + kullanım bağlamı («Solar Forecasting» → «trading/risk
management, asset optimization, operations/reliability»). [A] Ana mesaj: «AI energy forecasting
software… up to 3x more accurate». [A] Önceki rakip turunda alınan **etiket–değer biçimi**
(`IsIzgarasi.tsx` yorumu) buradan.
**Ders →** Etiket–değer biçimi al, «3x more accurate» türü kaynaksız oranı alma.

**Aurora Solar** — *ad kalıbı:* «Sales Mode», «Design Mode». Gövde somut fiil zinciri: [A]
«Aurora models the roof, places panels, runs shading analysis, and generates a code-compliant
layout in one session». Önceki turda alınan fayda kalıbının kaynağı.
**Ders →** Gövdede sıfat değil, ürünün yaptığı somut işler sıralanır. Ancak liste değil, cümle.

**Dexter Energy** — kartı **piyasa zaman çizelgesine** bağlar: [A] «forecasts feed into the
decision-making layer…, helping traders determine day-ahead bids, adjust intraday positions, and
make balancing stage decisions». Ürün adları: «Power Forecasting», «Solar Nowcasting».
**Ders →** PVQuant'ın beş kartı da bir günün sırasına oturuyor: gün öncesi program teslimi →
gün içi revizyon → dengesizlik maliyeti → dışa verim → gece nöbeti/karnesi. Bu sıra, kart
şablonunda **zaman etiketi** olarak kullanılabilir (4. aşamada değerlendirilecek).

## 2.2 Sentez — beş ders

1. **Ad = ürünün nesnesi ya da yaptığı iş; slogan değil.** Liderlerin hepsi kart adını ürünün iç
   sözlüğünden alıyor (Payments, Cycles, Previews, Forecast). «Tek tık», «hazır» gibi durum ya da
   slogan adları yok.
2. **Görsel = ürünün gerçek parçası ya da veri; sembol değil.** Stripe ve Linear arayüz kesiti,
   Modo ve Solcast gerçek grafik çiziyor. Jeton, zil ya da `</>` gibi kavram ikonları kimsede yok.
3. **Hiyerarşi dört katlı:** etiket (mono, küçük) → başlık → tek cümle fayda → künye (etiket–değer,
   teknik değer). PVQuant'ın «Hangi iş için?» bölümü bunu zaten kurmuş; TL kartları da bu dile
   geçmeli.
4. **Renk disiplini:** tek vurgu rengi yalnız eylemde. Veri renkleri yalnız veriyi kodluyor. Zemin
   tonu kartı «öne çıkarmak» için değişmiyor.
5. **Güven yöntemden gelir, rakamdan değil:** «nasıl hesaplandığı belli» (Modo) ve «kendi
   verinizle» cümlesi, uydurma oran ya da müşteri sayısından güçlüdür.

## 2.3 Kaçınılacaklar listesi

- Gradyan zemini kartı «özel» göstermek için kullanmak (bugünkü şeftali zeminli iki kart).
- Aşırı yuvarlatılmış köşeler (≥20 px) ve kart başına gölge/kalkma (R21 zaten yasaklıyor).
- Kavram ikonu: ₺ jetonu, zil, `</>`, imleç, bayrak, onay rozeti, kalkan, roket, şimşek.
- Dekoratif stok ya da yapay zekâ üretimi görsel, izometrik 3B nesneler, parıltı (glow).
- «AI-powered», «akıllı», «yapay zekâ destekli», «agentic», «sorunsuz», «tek tık», «devrim» dili.
- Kaynaksız oran ve sayı («3x daha doğru», «%30 tasarruf», «350 müşteri»).
- Eşit ağırlıklı, aynı kalıp cümleyle başlayan kartlar («X ile Y'yi Z'leyin» ×5).
- Uydurma alt marka adları (Databricks dersi).
- Aynı yetinin birden çok kartta tekrarı (bugün «TL gün gün» üç yerde geçiyor).

## 2.4 Kaynaklar

Ziyaret edilen [Z]: https://www.datadoghq.com/ · https://www.datadoghq.com/product/ (2026-10-05, ekran görüntüleri `arastirma-ekran/10-datadog-*.jpg`).

Arama sonuçları [A]:

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
