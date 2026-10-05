# 3. Aşama — İsim turu ⛔ DUR

## 3.0 Önce bir kapsam önerisi: her kart tek bir yeti grubunu anlatsın

Bugün aynı yetiler kartlar arasında tekrar ediyor («TL gün gün» üç yerde, «API» ve «emre amadelik»
ikişer yerde), iki geniş kart ise «Hangi iş için?» bölümündeki rollerle çakışıyor (analiz §1.2/5–6).
İsimlerden önce §0 yeti listesini beş karta **tekrarsız** dağıtmayı öneriyorum. Kart sırası ve
yerleri aynı kalır:

| Yer | Bugünkü ad | Anlatacağı yeti grubu (yalnız §0'dan) |
|---|---|---|
| K1 | Program hazır | saatlik üretim programı + emre amadelik bildirimi; teslim penceresi gecikince çalan alarm |
| K2 | Sapmanın TL kartı | tahmin hatasının aylık TL karşılığı + basit yönteme göre fark + teminat etkisi |
| K3 | Toplayıcıya tek tık | tahmin aralığının toplayıcı/DSG şablonlarında (saatlik ya da 15 dk) CSV/XLSX dışa verimi + API anahtarıyla sistemden sisteme akış |
| K4 | Operatör masası | 8 kurallık alarm kütüphanesi (veri / teslim / performans) + gece karnesi |
| K5 | Ticaret masası | iyimser–kötümser bant + gün içi revizyon izi + sabah koşusu webhook'u |

Düşenler: «aylık bakım penceresine iklim beklentisi» (§0 listesinde yok). «Sapmanın gün gün TL
karşılığı» K5'ten, «API» K5'ten çıkar; ikisi zaten K2 ve K3'te var.
Roller («operatör», «ticaret») ad olmaktan çıkar: kitle listesi tek yerde, «Hangi iş için?»
bölümünde kalır.

## 3.1 Beş isim dili, her kart için beş alternatif (25 isim)

Kural: görev dosyası «tek marka dili» istiyor. Bu yüzden alternatifleri **beş tutarlı küme**
olarak verdim. Her küme beş kartı aynı dilbilgisi kalıbıyla adlandırır. Böylece her kartın beş
alternatifi var ve hangi kümeyi seçerseniz seçin karışık dil oluşmuyor. Jargon (D‑1, DSG, KGÜP,
P10/P90) hiçbir adda yok, künyeye kalıyor.

### Özet tablo

| Kart | A · Ürün nesnesi | B · Tek kelime modül | C · Sonuç durumu | D · Kısa emir | E · Panelin sözlüğü |
|---|---|---|---|---|---|
| K1 | **Teslim programı** | **Teslim** | **Zamanında program** | **Vaktinde gönderin** | **Program ve teslim** |
| K2 | **Sapma maliyeti** | **Sapma** | **TL cinsinden sapma** | **Sapmayı fiyatlayın** | **Dengesizlik maliyeti** |
| K3 | **Şablonlu dışa verim** | **Aktarım** | **Şablona hazır tahmin** | **Şablona aktarın** | **Dış erişim** |
| K4 | **Alarm kütüphanesi** | **Nöbet** | **Kurallı nöbet** | **Nöbeti devredin** | **Açık alarmlar** |
| K5 | **Gün içi aralık** | **Revizyon** | **Güncel aralık** | **Aralığı izleyin** | **Bant ve revizyonlar** |

### A · Ürün nesnesi (isim tamlaması, en çok iki kelime)
Kaynak ders: Stripe/Linear/Vercel ürün adları, Solargis «Forecast/Monitor» (arastirma §2.2/1).

| Kart | Ad | Gerekçe |
|---|---|---|
| K1 | Teslim programı | Panelin ürettiği dosyanın kendisi. «Hazır» gibi durum bildirimi yerine somut nesne. |
| K2 | Sapma maliyeti | Panel dizgesi «dengesizlik maliyeti»nin jargonsuz hâli. «TL kartı»ndaki arayüz kelimesi («kart») kalkar. |
| K3 | Şablonlu dışa verim | «Tek tık» abartısı yerine yetinin adı. «Şablonlu», toplayıcı/DSG biçimini jargonsuz taşır (Kpler kanal dersi). |
| K4 | Alarm kütüphanesi | §0'daki gerçek adı. «8 kural» künyede ölçülebilir değer olur. |
| K5 | Gün içi aralık | Bant + revizyon izini tek nesnede toplar. «Belirsizlik» kelimesinin olumsuz tınısından kaçar. |

### B · Tek kelime modül adı
Kaynak ders: Linear «Cycles / Triage», Solargis «Prospect / Evaluate / Monitor / Forecast».

| Kart | Ad | Gerekçe |
|---|---|---|
| K1 | Teslim | Günün ilk işi. Beş ad birlikte bir iş akışı gibi okunur: Teslim → Sapma → Aktarım → Nöbet → Revizyon. |
| K2 | Sapma | Bölüm başlığı zaten «maliyetini TL olarak görün» diyor; kart adı yalın kalabilir. «Maliyet» seçilmedi: ürünün fiyatı gibi okunabilir. |
| K3 | Aktarım | Dosya ve API'yi tek kelimede birleştirir. |
| K4 | Nöbet | «Operasyon nöbeti» masasıyla aynı kök. Kitle değil, iş anlatır. |
| K5 | Revizyon | Gün içi revizyon izi ürünün ayırt edici yetisi; bant künyeye iner. |
Risk: tek kelime tek başına az şey söyler, etiket ve künyenin yükü artar (tasarım turunda ele alınır).

### C · Sonuç durumu (iş sonucu, isim öbeği)
Kaynak ders: Aurora fayda kalıbı, Dexter'in «piyasa anına bağlanan sonuç» dili.

| Kart | Ad | Gerekçe |
|---|---|---|
| K1 | Zamanında program | Okurun aldığı sonuç: geç kalmamak. Alarm künyede. |
| K2 | TL cinsinden sapma | Bölüm vaadinin kart düzeyindeki karşılığı. |
| K3 | Şablona hazır tahmin | Dönüştürme işinin ortadan kalktığını söyler; «tek tık» abartısı yok. |
| K4 | Kurallı nöbet | Nöbetin kişiye değil kurallara bağlı olduğunu söyler. |
| K5 | Güncel aralık | Gün içinde revize edilen bandın sonucu. |
Risk: «Hangi iş için?» başlıkları da iş sonucu dilinde. İki bölüm benzer sesle konuşur.

### D · Kısa emir (iki kelime, ikinci çoğul kişi)
Kaynak ders: Stripe fayda başlıkları («Accept and optimize payments…»).

| Kart | Ad | Gerekçe |
|---|---|---|
| K1 | Vaktinde gönderin | Doğrudan eylem; «gecikirse alarm» künyede. |
| K2 | Sapmayı fiyatlayın | TL karşılığını eylem olarak koyar. |
| K3 | Şablona aktarın | Dışa verimi okurun işi olarak söyler. |
| K4 | Nöbeti devredin | Alarm kütüphanesinin işi üstlendiğini söyler. |
| K5 | Aralığı izleyin | Gün içi revizyonu eylem olarak söyler. |
Risk: «Hangi iş için?» h3'leri de emir kipinde («…verin», «…raporlayın»). Aynı sayfada en çok
tekrar hissi verecek küme bu.

### E · Panelin kendi sözlüğü
Kaynak ders: Modo/Kpler «Terminal» gerçekliği. Vitrin ile panel aynı adı kullanır, giriş yapan
müşteri aynı kelimeyi panelde bulur.

| Kart | Ad | Panelde karşılığı |
|---|---|---|
| K1 | Program ve teslim | panelde teslim penceresi ve emre amade kapasite ayarları |
| K2 | Dengesizlik maliyeti | «Tahmin hatasının TL karşılığı — dengesizlik maliyeti» (birebir) |
| K3 | Dış erişim | «Dış erişim» bölüm başlığı (birebir) |
| K4 | Açık alarmlar | «Açık alarm · veri gecikmiş» etiketi |
| K5 | Bant ve revizyonlar | birebir karşılığı yok (kümedeki tek zayıf halka) |
Risk: «Dengesizlik» ve «Dış erişim» ilk kez gelen ziyaretçi için en az anlaşılır adlar.

## 3.2 Önerim

**A · Ürün nesnesi.** Gerekçe: (1) Bir alttaki «Hangi iş için?» bölümü zaten *iş sonucu* dilinde.
TL bölümünün *panelde ne bulacağınızı* adlandırması iki bölümü birbirinden ayırır ve tekrarı
önler. (2) Liderlerin ortak kalıbı (Stripe, Linear, Vercel, Solargis) bu. (3) Her ad doğrudan bir
§0 yetisine karşılık geliyor, dürüstlük testi kolay. İkinci tercih: B (daha cesur ve markalı, ama
etiket ile künyeye daha çok yük biniyor).

## Seçim (kullanıcı dolduracak)

- Kapsam önerisi 3.0: kabul (çalışma varsayımı olarak tüm aşamalarda uygulandı; kullanıcı itiraz etmedi)
- İsim kümesi: **A · Ürün nesnesi** (kullanıcı, 2026-10-05: «A ile devam et») — Teslim programı · Sapma maliyeti · Şablonlu dışa verim · Alarm kütüphanesi · Gün içi aralık
- Tek tek değişiklik: yok
