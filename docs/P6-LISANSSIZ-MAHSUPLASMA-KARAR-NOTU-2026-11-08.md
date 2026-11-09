# P6 — Lisanssız mahsuplaşma ve ödeme katmanı: karar notu (08.11.2026)

Yol haritasının (31.10.2026) dalga 3'teki P6 kalemi bir ürün kararı istiyor: PVQuant tek tesisli lisanssız üreticiye (persona C) mahsuplaşma, limit ve
ödeme takibi sunacak mı? Bu not kararı sahibine bırakır; iki yolu, bugün yapılmış olanı, her yolun gerektirdiğini ve riskleri yan yana koyar.
Karar verilmeden kod yazılmaz.

## 1. Bugün ne var

| Konu | Durum | Nerede |
|---|---|---|
| Segment «Öz tüketim (saatlik mahsup)» ve lisanssız segmentler | var; mahsup hesabı yok | Santral ayarları › Piyasa segmenti |
| Toplayıcı/GTŞ portföyünde lisanssız KÜPST payı (IH-054) | var (UEVÇB bazında, Karar 14907 Md.1(3) brüt sapma) | Portföy › KÜPST (v2.511) |
| Lisanssız SCADA durumu ve Karar 14909 cezai şart göstergesi (IH-057) | var; (ç) askıda değil, uyarı tarihi | Sayaç sayfası (v2.523, v2.538) |
| 10 yıl bitişi, LÜY alım süresi, %90 kuralı tarihleri (IH-061) | var; Takvim Uyum satırları; 10.12.2026 sonrası fiyat rejimi belirsiz etiketli | Takvim (v2.524) |
| LÜY rejimi (m.25 / m.26; çağrı mektubu ölçütü 12.05.2019) | var | Takvim rozeti (v2.541) |
| GTŞ ödeme zinciri tarihleri (EPİAŞ → GTŞ → üretici) | var; Takvim dönem zinciri | Takvim (v2.518) |
| Tüketim verisi, üç sanal sayaç, bedelli limit, fatura mutabakatı, GTŞ ödeme kıyası | **yok** | — |

Yol haritasındaki (i) yolu («C'yi yalnız toplayıcı portföyündeki lisanssız olarak kapsa») bu tabloyla fiilen tamamlanmıştır; eksik yalnız
(ii) yolunun kalemleridir.

## 2. Mevzuat zemini (birincil kaynaklardan, 31.10.2026 teyitli)

- **Saatlik mahsuplaşma:** LÜY m.26(1) — 12.05.2019 ve sonrası çağrı mektubu alan YEK tesisleri ile (ç), (d) bentlerindeki tesislerin mahsuplaşmasını
  EPİAŞ saatlik yapar; meskenle ilişkili tesislerde aylık (m.26(20)). Değişiklik RG 02.04.2026-33212, yürürlük 1.5.2026. Ödeme: EPİAŞ → GTŞ (dönem
  sonunu izleyen ayın 25'i civarı) → üretici (izleyen ayın 5. iş günü) — bulgular 02-16.
- **Karar 14531 (RG 05.05.2026):** üretim üç sanal sayaca ayrılır (bedelli / sistem kullanım bedeli ödemeli / bedelsiz); tüketim tesisi başına bedelli
  üretim limiti; aynı kişi/VKN'li tesisler tek grup; mevcut grupların limit bildirimi 01.06.2026'ya kadar LÜM'e; veri LÜM ve PYS üzerinden; itiraz 5 iş
  günü. Birincil metin arşivde (`kaynaklar/Karar-14531-LUM-mahsuplasma-UE-OCR-metni.txt`), madde düzeyinde karşılaştırma yapılmadı — bulgular 07-12.
- **AYM E.2024/133 K.2025/233 (RG 10.03.2026-33192):** 5346 md.6(2)'nin 1. ve 2. cümleleri (10 yılı dolan lisanssızın lisans alma bedeli ve katkı
  bedeliyle lisanslıya geçişi) iptal; yürürlük 10.12.2026. 3. cümle (ihtiyaç fazlası için PTF'yi geçmeyen fiyat, CK'ya bırakılmış) korundu. 10 yılı
  dolan tesise 10.12.2026 sonrası uygulanacak rejim BELİRSİZ — bulgular 08-14; CK 11415 (RG 13.06.2026-33279) on yılı dolan lisanssızda fiyat.
- **Kullanıcı sesi:** mahsuplaşma/fatura 8 kaynak, fiyat < maliyet saatleri 7, garanti/sigorta 6, ödeme 5 — en güçlü dört tema lisanssız tarafta
  (bulgular 07). GENSED 21.05.2026: EPİAŞ LÜM saatlik mahsup ekranları simülasyonda.
- **Rakip tabanı:** LOGGMA Finans ve Mahsuplaşma Modülü (OSOS 21 EDAŞ + EPYS); Enerjisa Lisanssız Üretici Portali («Müşteri TL / EPİAŞ TL») —
  bulgular 06-49.

## 3. İki yol

### (i) Bugünkü kitle: A/B/D + toplayıcı portföyündeki lisanssız — KÜÇÜK, fiilen tamam

- Kapsam: yukarıdaki tabloda «var» olan satırlar. Yeni kod yok.
- Yapılacak tek şey: Vitrin «Kimin için» bölümünde tek tesisli lisanssızı açıkça kapsam dışı bırakmak ya da «toplayıcı üzerinden» diye
  nitelendirmek (K-02). Karar: metin değişikliği, ayrı mühür.
- Risk: lisanssız sahibinden gelen talepler yanıtsız kalır; rakipler bu dilimde büyür.

### (ii) Tam C dilimi: saatlik mahsup, limit sayacı, GTŞ ödeme takibi, fatura mutabakatı — BÜYÜK

Gerektirdikleri (her biri kendi girdisini ister; hiçbiri bugün elde değil):

| Kalem | Girdi | Kaynak sistem | Zorluk |
|---|---|---|---|
| Saatlik mahsup hesabı (veriş − çekiş, saat saat) | tüketim tesisinin saatlik çekişi | OSOS / MASS dışa aktarımı ya da EDAŞ portalı; tüketim sayacı eşlemesi | orta — PVQuant'ta tüketim veri modeli yok |
| Üç sanal sayaç (bedelli / sistem kullanım bedeli ödemeli / bedelsiz) ve bedelli limit | Karar 14531 limit, grup tanımı (aynı VKN), LÜM bildirimi | LÜM (EPİAŞ), müşteri beyanı | yüksek — Karar metni madde düzeyinde doğrulanmalı; LÜM erişimi yok |
| Beklenen GTŞ ödemesi ve kıyas (IH-051) | PTF, bedelli MWh, GTŞ ödeme belgesi | EPİAŞ fiyatı (var), GTŞ belgesi (müşteri yükler) | orta |
| Fatura dökümü ve belge mutabakatı (IH-050/052) | GTŞ/EDAŞ fatura ve döküm dosyaları | müşteri yükler; biçimler GTŞ'ye göre değişir | yüksek — biçim çeşitliliği |
| İç tüketim ve tasarruf girdileri (IH-063/066) | tüketim profili, tarife | müşteri beyanı | orta; «tasarruf» dili anayasaya aykırı → «mahsup edilen» diye adlandırılmalı |
| 10 yıl sonrası rejim (IH-061) | 10.12.2026 sonrası CK/EPDK düzenlemesi | RG izleme | belirsiz; mevzuat çıkmadan hesap yapılamaz |

- Satış kanalı: tek tesisli lisanssız sahibi (çatı/C&I) farklı bir müşteri; EDAŞ/GTŞ portal entegrasyonu ve fatura doğrulama ayrı destek yükü.
- Kapsam/effor: yol haritası T 5 (yeni dilim) · M 5 · Y 2; ilk pilot için en az bir lisanssız müşteri, bir GTŞ'nin fatura/döküm örneği ve OSOS dışa
  aktarımı gerekir.

## 4. Karar soruları (sahibine)

1. PVQuant 2027 ilk yarısında tek tesisli lisanssız (persona C) dilimine giriyor mu? — Evet ise (ii) için pilot müşteri ve belge örnekleri;
   hayır ise (i) tamam, vitrin metni netleşir.
2. (ii) seçilirse ilk adım hangisi: saatlik mahsup hesabı (tüketim verisiyle) mi, GTŞ ödeme kıyası (belge yüklemeyle) mi?
3. Karar 14531 birincil metninin madde düzeyinde karşılaştırması (OCR arşivde) yapılsın mı? — (ii) için ön koşul.
4. 10.12.2026 AYM yürürlüğü sonrası rejim için RG izleme devam ediyor (haftalık tarama); hesap, düzenleme çıkınca.

## 5. Öneri

Bugünkü kitle ve kaynaklarla **(i)**: C dilimi toplayıcı üzerinden kapsanır, vitrin metni buna göre netleştirilir; (ii) en az bir lisanssız müşteriyle
görüşülüp OSOS dışa aktarımı ve GTŞ fatura örneği alınmadan açılmaz. Bu not karar verilince 04 raporundaki P6 satırına işlenir.

## 6. Karar (09.11.2026)

Sahip **(i)** yolunu seçti: PVQuant 2027 ilk yarısında tek tesisli lisanssız (persona C) dilimine girmez; lisanssız santraller yalnız toplayıcı /
görevli tedarik portföyü üzerinden kapsanır (bugünkü KÜPST payı, Karar 14909 göstergesi, Takvim satırları ve LÜY rejimi rozeti korunur). Uygulanan
tek değişiklik (K-02): vitrin «Kimin için» künyesine «lisanssız santraller toplayıcı portföyü üzerinden» maddesi eklendi (v2.547). (ii) yolunun
kalemleri (tüketim veri modeli, üç sanal sayaç, GTŞ ödeme kıyası, fatura mutabakatı, Karar 14531 madde karşılaştırması) yol haritasında kapalı
kalır; yeniden açılması için en az bir lisanssız pilot müşteri, OSOS dışa aktarımı ve bir GTŞ fatura örneği gerekir. 10.12.2026 AYM yürürlüğü sonrası
rejim için haftalık RG taraması sürer.
