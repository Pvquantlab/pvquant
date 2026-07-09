# PVQuant — UI Tasarım Sistemi ve Ekran Envanteri (v2 · Final)

**Bu belgenin rolü:** Görsel tasarım fazının (Claude Design, Tem 2026) sonunda ortaya çıkan sistemin bağlayıcı kaydı. Üç yerde kullanılır: (1) Claude Design projesindeki eski brief'in yerine referans belge, (2) Streamlit geliştirme fazında Claude Code'a verilecek devir paketinin çekirdeği, (3) ileride ekibe katılacak herkes için tasarım anayasası. v1 brief'in yerini alır.

**Konumlandırma:** "PVQuant, santralinizi tanıyan tahmin motorudur — SCADA verinizi yükleyin, model kendini santralinize kalibre etsin, sapma sıfıra insin."

---

## 1. Gizlilik Anayasası (her şeyin üstünde)

Yöntem ticari sırdır. Hiçbir kamuya açık yüzeyde — landing, uygulama ekranları, bekleme kartları, tooltip'ler, hata mesajları, API örnekleri dahil — şunlar görünmez: algoritma/model adları, fonksiyon adları, katsayı değerleri, veri kaynağı adları. Meteo kaynağı yalnızca "profesyonel meteoroloji verisi" olarak anılır.

Şeffaflık ilkesi yalnızca **müşterinin kendi sonuçlarına** uygulanır: önce/sonra sapması, bulunan parametreler (panel yönü/eğimi, sistem verimlilik katsayısı), veri kalitesi raporu. Bunlar ürünün güven hikayesidir ve tüm çıplaklığıyla gösterilir.

Denetim listesi (her tasarım/kod turunda taranır): Erbs · Perez · Faiman · Barhdadi · calibrate() · predict() · ModelSelector · eta_bos · bifacial · BG= · η= · Open-Meteo · "literatür katsayıları".

---

## 2. Kim İçin, Hangi His

Birincil kullanıcı: Python bilmeyen santral sahibi/işletmecisi veya enerji analisti; SCADA panellerine ve Excel'e alışkın. Hedef his: **dünya standardında kurumsal B2B SaaS** — referans ciddiyet seviyesi Stripe Dashboard, Linear, Grafana. Duygusal hedef: "Bu araç benim santralimi gerçekten anladı."

Sektör bağlamı (rakip araştırmasından kalan ilkeler):
- Enphase dersi: ekranın tek bir "kalp öğesi" olur — bizde bugünün amber/mavi saatlik eğrisi.
- iSolarCloud dersi: katmanlı yoğunluk — ilk bakışta en fazla 4 KPI + 1 grafik, detay tıklamayla.
- FusionSolar dersi (ters yönde): "her şeyi göster" değil "önemli olanı göster"; bir ekranda 8'den fazla kart olmaz.
- SolarEdge uyarısı: veri zenginliği sunum eskiyince ürünü kurtarmaz — yüzey dili disiplinli tutulur.
- Ayrışma tezi: izleme platformları geçmişi gösterir, PVQuant geleceği gösterir. Görsel ağırlık daima ileriye (bugün + 7 gün) bakar.

---

## 3. Tasarım Sistemi (Final)

### 3.1 Tipografi
| Rol | Yazı tipi | Kurallar |
| --- | --- | --- |
| Tüm arayüz | **Inter** | Başlıklar 600-700 kesim, sıkı aralık (-0.02em); gövde 400-500 |
| Sayılar/teknik | **IBM Plex Mono** | Tüm metrikler, tarihler, saatler, API adresleri, kısayollar |
| Mikro-etiket | Inter 600 | 11px, BÜYÜK HARF, +0.08em aralık, soluk gri — KPI kart başlıkları |

Space Grotesk sistemden çıkarılmıştır. Büyük sayı + küçük sakin etiket hiyerarşisi korunur.

### 3.2 Renk
| İsim | Hex | Kullanım |
| --- | --- | --- |
| Birincil mavi | `#1F5288` | Butonlar, linkler, aktif durumlar, seçili pill'ler |
| Koyu hover | `#173F6E` | Birincil etkileşim hover'ı |
| Gece laciverti | `#0E1D30` | Sol menü zemini, tooltip zemini, koyu marka bandı degrade başlangıcı |
| Metin | `#0F1B28` | Ana metin (neredeyse-siyah) |
| İkincil metin | `#57616D` / `#7C8794` | Açıklamalar, nötr değerler |
| Kenarlık | `#E2E6EA` | Tüm kart/giriş kenarlıkları (1px) |
| Zemin | `#F7F8F9` | Sayfa zemini; kartlar beyaz |
| **Amber** | `#E8940A` | **YALNIZCA grafiklerde "gerçekleşen üretim" veri mürekkebi.** Arayüzde (buton, rozet, vurgu) asla. |
| Model mavisi | `#2D6FB5` | Grafiklerde "tahmin" çizgisi (kesikli) |
| Başarı yeşili | `#1E9E6A` | Kalibre rozeti, sapma %0.00, pozitif deltalar — küçük dozda |
| Uyarı bakırı | `#C9502E` | Yalnızca gerçek uyarılar. Hava kaynaklı doğal üretim düşüşleri BAKIR DEĞİL, nötr gridir. |

Bir ekranda görünür renk sayısı 4'ü geçmez. Yeni renk eklenmez.

### 3.3 Yüzey Dili
- Gölge yok; ayrım 1px `#E2E6EA` kenarlıkla. (Tek istisna: ⌘K palet overlay'i — kenarlık + %40 `#0E1D30` karartma.)
- Köşe yarıçapı: kartlar 8px, butonlar 6px, palet 12px.
- 8px grid: tüm boşluklar 8'in katı.
- Emoji yasak. Tüm ikonlar tek ince-çizgi SVG seti (Lucide stili, 1.5px stroke). →/✓ gibi tipografik semboller de zamanla ikonlaşır.
- Tablolar: başlıklar mikro-etiket stilinde + sıralama okları, rakamlar sağa hizalı mono, 40px satır, ince ayraçlar, hover'da `#F7F8F9` zemin (0.15s geçiş).

### 3.4 Grafik Dili
- **Anlam kuralı (değişmez):** amber dolu çizgi = gerçekleşen; mavi kesikli = tahmin. Her grafikte aynı; lejant her grafikte görünür.
- Bugün grafiğinde ince dikey "şimdi" çizgisi + mono saat etiketi.
- Izgara çok soluk; eksen yazıları mono; birim notu grafik altında mono ("saatlik güç (kW) · MW ölçeği solda").
- Sapma histogramında sıfır çizgisi yeşil ve kalın.
- Zaman aralığı pill'leri grafik sağ üstünde: [Bugün] [7g] [30g] — seçili dolgu mavi; 30g "Yakında" rozetli (yol haritası sinyali).
- İleride P50/P90: mavi çizgi etrafına %15 opak bant — görsel dil buna hazır.

---

## 4. Uygulama Kabuğu Envanteri

Landing hariç tüm ekranlar bu kabuğun içinde yaşar:

**Sol menü** (koyu `#0E1D30`→lacivert): üstte PVQuant logosu + gün eğrisi motifi; öğeler: Santralim · Veri Yükleme · Kalibrasyon · Tahminler · Raporlar (aktif öğe vurgulu); altta gizlilik cümlesi ("Veriniz yalnızca bu oturumda kullanılır; oturum kapanınca silinir."); en altta kuruluş bloğu: baş harf karesi + şirket adı + "Kurumsal plan" + ayarlar dişlisi.

**Üst bar:** arama kutusu ("Ara veya komut yaz..." + mono ⌘K rozeti) · sihirbaz adım göstergesi (akış ekranlarında: "1 · Santral bilgisi ✓ · 2 · Veri yolu · 3 · Sonuç") · santral seçici ("Santral: Konya GES" — çoklu santral hazırlığı) · görünüm anahtarı ("Görünüm: Kalibre | Hızlı" — sonuç ekranlarında; tek mod göstergesi ilkesi: rozet VE anahtar aynı anda olmaz) · canlılık: yeşil nabız noktası + "Veri akışı aktif" · tarih · bildirim zili (örnek bildirimli panel) · avatar + ad + şirket.

**Sayfa başlığı disiplini:** her ekran başlık (22px, 700) + tek satır gri açıklama + sağda eylemler (Dışa Aktar / Yenile) + mono "Son güncelleme 14:32" damgası ile açılır.

**Footer:** "PVQuant v1.4.2" (mono) · "● Sistem durumu: Normal" · "© 2026 PVQuant".

**⌘K Komut Paleti:** 560px, üç grup (Git / Eylemler / Santral), satırlarda ikon + ad + mono kısayol ipucu, canlı filtreleme, "↑↓ gezin · ↵ seç · esc kapat" altbilgisi. Git komutları gerçekten gezinir.

---

## 5. Ekran Envanteri (Final Durum)

**0 · Landing (kabuksuz, pazarlama):** Hero: "Santralinizi tanıyan tahmin" + canlı önce/sonra mini-demo (gerçek değerlerle). "Nasıl çalışır?" = yalnızca 3 kullanıcı adımı (tanıtın → yükleyin → tahmininizi alın), yöntem detayı sıfır. Kanıt şeridi + CTA. Landing de final tasarım sistemiyle konuşur.

**1 · Santral formu:** haritalı (stilize placeholder), "Bilmiyorum — PVQuant bulsun" onay kutuları, tilt+azimuth ikisi birden işaretlenince sakin XOR açıklaması.

**2 · Veri yolu ayrımı:** iki kart — "Hızlı tahmin · veri yüklemeden · %5-10 beklenen sapma" vs "Kalibre tahmin · SCADA verinizle · %1-3 beklenen sapma" (ÖNERİLEN rozetli, yeşil çerçeve). Alt not: 3 aydan az veri engellenmez, hızlı tahminle başlatılıp yükseltme önerilir.

**3 · SCADA yükleme:** sürükle-bırak (gün eğrisi silüetli boş durum), sütun eşleşme önizlemesi (kullanıcı onaylar/düzeltir), en-az-3-ay doğrulaması (önerilen 12 ay), otomatik temizlik anahtarı.

**4 · Kalibrasyon bekleme:** gün eğrisi biçimli progress, üç aşama etiketi, iptal her an görünür, bilgi kartları yalnızca fayda dili ("Kalibre santrallerde sapma %1-3'e iner").

**5 · Sonuç (Tahminler):** KPI şeridi (Sapma %0.00 yeşil ⓘ · Ortalama tahmin hatası %20.3 ⓘ · Süre 42 sn · Veri 15.538 saat) → Önce/Sonra kartı (yeşil ibre, -%52 → %0.00, "Tekrar oynat") → Bulduklarımız (üstü çizili eski değer → yeni değer: 180° → 159°; kilit = sizin girdiğiniz, kalkan = modelin bulduğu) + Veri Kaliteniz (67 anomali, en uzun kesinti 2 sa 5 dk, 15.538 saat) → Gerçek vs Tahmin grafiği (Hafta 1/2/3 + aralık pill'leri) → günlük sapma dağılımı (açılır). Mod A varyantı: KPI şeridi yerine bilgi bandı + yükseltme çağrısı; önce/sonra ve Bulduklarımız yalnızca Mod B'de.

**6 · 7 günlük tahmin:** ana grafik + grafik altı indirme kutusu ([CSV][Excel][JSON] + kopyalanabilir API adresi: https://api.pvquant.io/v1/santral/{id}/tahmin) + 7 günlük tablo (Gün · Beklenen üretim · Pik saat · Pik güç · Bugüne göre %; negatifler nötr gri, pozitifler yeşil).

**7 · Raporlar:** üç kart (PDF yönetici özeti / Excel tam veri / JSON API formatı), her kartta 3 maddelik içerik önizlemesi.

**8 · Santralim (genel bakış — kalibrasyon sonrası ana ekran):** Koyu marka bandı (lacivert→mavi degrade): santral adı ("Konya GES", 700) + mono teknik ID rozeti + meta satırı (2.5 MW · Konya, Türkiye · Devreye alma 2023) + iki pill rozet ([● Kalibre — sapma %0.00] ve [Bugünün tahmini hazır →]) + sağda 3 günlük hava/ışınım sütunları (bugün vurgulu) + alt şeritte üretim etkisi cümlesi ("Yarın parçalı bulutlu — beklenen üretim bugünden %9, cuma %18 düşük", yüzdeler mono açık mavi). Altında 4 KPI (Bugünkü tahmini üretim · Yarın beklenen · Bu haftaki toplam · Model durumu/sağlık rozeti). Kalp öğesi: "Bugün — saatlik üretim" (amber gerçekleşen + mavi kalan saatler + şimdi çizgisi). Yanında "7 günlük görünüm" mini bar (→ Tahminler). Altta "Veri sağlığı" (→ Veri Yükleme). Boş durum: soluk gün eğrisi + "İlk tahmininizi alın".

---

## 6. UX Yazım Dili

- Terim sözlüğü: MAPE → "Ortalama tahmin hatası (MAPE)" · bias → "Sapma" · eta_bos → "Sistem verimlilik katsayısı" · azimuth → "Panel yönü (azimuth)" · tilt → "Panel eğimi (tilt)".
- KPI tooltip'leri tek cümle tanım (koyu lacivert zemin, beyaz yazı): Sapma → "Yıllık toplam tahmin ile gerçekleşen üretim arasındaki fark." MAPE → "Ortalama mutlak yüzde hata — günlük tahmin isabetinin ölçüsü."
- Butonlar eylemi söyler ("Kalibre tahmine geç", "CSV"), asla "Tamam/Gönder".
- Hatalar yol gösterir, suçlamaz; az veri engellemez, yönlendirir.
- Durum bilgisi düz cümle değil rozettir (● nokta + pill).
- Hava kaynaklı üretim düşüşü uyarı dili almaz (nötr); bakır yalnızca gerçek sorunlara.

---

## 7. Streamlit Devir Notları (Faz 2 kod tarafı için)

- Kaynak paket: Claude Design'dan yeniden paketlenmiş tam HTML (tek dosya, komut paleti dahil) + support.js + bu belge.
- Bileşen eşlemesi: kabuk/sol menü → çok sayfalı Streamlit + özel CSS; KPI kartları → st.metric üstüne stil; grafikler → Plotly (renk/lejant kuralları §3.4'ten); tablo → styled dataframe (mono, sağa hizalı, hover); ⌘K paleti → MVP'de opsiyonel (streamlit-searchbox benzeri veya Faz 2.5'e ertelenebilir); önce/sonra ibre animasyonu → MVP'de statik iki değer + ibre SVG kabul edilebilir.
- Backend arayüzü değişmedi: calibrate_from_scada · forecast_7day · OpenMeteoClient · load_csv (bu adlar yalnızca kodda yaşar, UI metinlerinde asla).
- Font yükleme: Inter + IBM Plex Mono (Google Fonts); Streamlit'te özel CSS ile gömülür.
- Kod tarafında da gizlilik denetim listesi (§1) her PR'da taranır — UI string'lerinde yasaklı kelime kontrolü CI'a eklenebilir.

---

## 8. Sürüm Notu

v1 → v2 değişiklikleri: Space Grotesk çıktı (Inter geldi) · amber marka renginden veri mürekkebine indirildi · koyu mavi kimlik (#1F5288/#0E1D30) · gölgeden 1px kenarlık diline geçildi · uygulama kabuğu envanteri eklendi (üst bar donanımı, ⌘K, kuruluş bloğu, footer) · "Santralim" genel bakış ekranı eklendi · landing'deki mimari teşhiri kaldırıldı, gizlilik anayasası yazıldı · tablo/tooltip/pill/rozet standartları tanımlandı · Streamlit devir notları eklendi.
