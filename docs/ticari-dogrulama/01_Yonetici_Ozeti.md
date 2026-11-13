# 01 — Yönetici özeti (Faz 8 ticari doğrulama programı) — NİHAİ, F8-I (13.11.2026)

> **Sonuç tek cümle:** program hazırlandı, uygulanmadı — 15 belge + 5 CSV masa başında tamamlandı (her paket öz incelemeden geçti, 3 kalite turu); görüşme 0, pilot 0, finansal
> doğrulama 0, teklif 0, ödeme 0; dış eylemlerin hepsi izin bekliyor (14). Karar sınıfı **BELİRSİZ** (11 §3). Ayrıntı ve 15 bölüm: `15_Nihai_Karar_Raporu.md`.

## 1. Amaç

Müşterinin gerçekten para ödemeye hazır olduğu, pahalı ve tekrarlayan problemi bulmak. Teknik ürün tamamlanması (Faz 0–6) ticari talebi kanıtlamaz.
Beş düzlem ayrı ölçülür: teknik yapılabilirlik · problem şiddeti · ödeme istekliliği · satın alma yapılabilirliği · fiili ödeme taahhüdü.

## 2. Başlangıç hedefleri (ekran görüntüsü §8; hedef ≠ sonuç)

| # | Çalışma | Başlangıç hedefi | Beklenen çıktı | Durum 13.11 | Hazır olan |
|---|---|---|---|---|---|
| 1 | Sektör görüşmeleri | 12–15 kuruluş | gerçek problem ve satın alma yetkilisi | **Henüz yapılmadı** (0 görüşme) — Engellendi (izin) | 03 havuz 40 / kısa liste 15 (K-49…K-59); 04 protokol D1–D7, Y1–Y8; 05 şablon + CSV (K-60); taslaklar gönderilmedi |
| 2 | Lisanslı GES pilotu | 1–2 santral/işletmeci | tahmin ve uzlaştırma doğrulaması | **Henüz yapılmadı** — Engellendi; eşikler Doğrulama gerekiyor | 06 protokol (G1–G9, Z/B/G eşikleri ÖNERİ; K-61); motor (K-01, K-03); canlı 30 gün sayıları okunmadı (14 D8) |
| 3 | Toplayıcı/DSG pilotu | 1 portföy | çoklu santral ve sözleşme modelinin testi | **Henüz yapılmadı** — Engellendi | 07 protokol (K-61); portföy/DSG katmanı (K-04); kısa liste C 6 kuruluş (Zeros 1.000+ MW beyanı, K-52) |
| 4 | Geriye dönük finansal analiz | ≥ 2 uygun uzlaştırma dönemi | hesaplama farklarının açıklanması | **Henüz yapılmadı** — Engellendi (resmî bildirim yok; en erken Ocak 2027) | 08 yöntem + G1–G10 + şablon CSV (K-62); FEM (K-05); Faz 2 C yalnız varsayımsal (K-07) |
| 5 | Ücretli dönüşüm denemesi | başarılı pilotlar arasından | fiyatlama ve sözleşme modelinin testi | **Henüz yapılmadı** (0 teklif, 0 sözleşme, 0 ödeme) — Engellendi | 09 ayrım merdiveni + E1–E9 + T1–T4 + sayısız teklif şablonu (K-63); 10 dönüşüm süreci (K-64); formül (K-21), abonelik (K-20) |

## 3. Pilota hazır yetenekler (yalnız «Mevcut» sınıfı — K-23)

| Yetenek | Pilotta vaat edilebilir | Vaat edilemez / şartlı |
|---|---|---|
| Üretim tahmini (saatlik, 15 gün) + doğruluk karnesi + yayın damgalı bağımsız doğrulama | evet | «%x doğruluk» (canlı 30 gün sonuç öncesi); 15 dk / başka ufuk |
| Veri yükleme (dosya) ve SCADA dışa aktarımı; alarm (13 kural); dönem raporu + zamanlanmış gönderim | evet | bulut inverter bağlantısı (müşteri hesabıyla pilot içinde doğrulanır, K-24) |
| KGÜP öneri sürümü + beyan dosyası yükleme | evet (öneri) | TPYS kabulü (doğrulanamaz; müşteri beyanı) |
| Finansal etki merkezi (EDT, KÜPST, satış geliri; nitelik etiketli) + mutabakat (EPİAŞ bildirimi esas) | evet | «tasarruf / kazanç» (K-06); resmî uzlaştırma sonucu |
| Portföy / DSG / KÜPST (korelasyonlu P10/P90, PICP sınavı; üç perspektif; «varsayımsal dağılım» etiketi) | evet | sözleşmeye dayalı dağılım (sözleşme verisi girilmeden); otomatik piyasa emri |
| Dış API (16 uç: 13 okuma + KGÜP gönderimi + üretim dosyası + santral ayarı; anahtar kapsamı, santral kapsamı) + webhook; kuruluşlar arası paylaşım | evet | — |
| Santral bazlı kullanıcı yetkisi · sözleşme kuralları · özel entegrasyon · Sanayi GES | — | geliştirmede / sınırlı / iş bazlı / yok |

## 4. Vaat ve dil kuralları (CLAUDE.md anayasası, Faz 6 06)

Sayı uydurulmaz; «tasarruf / kazanç / kurtarılan / garanti» yazılmaz; «ceza» yalnız 6446 md.16; EPİAŞ bildirimi esastır; TPYS kabulü ve uzlaştırma
sonucu «doğrulanamadı»; dengesizlik etkisi «tahmini fayda» ya da «varsayımsal senaryo» etiketiyle; fiyat teklifle, panelden satın alma yok.

## 5. Kanıt durumu özeti (13 sicil, 65 satır)

Teknik yapılabilirlik: var. Tahmin doğruluğu: canlı 30 gün sayıları okunmadı (SQL hazır, 14 D8). Problem şiddeti: mevzuattan türeyen hipotez + varsayımsal senaryo; hiçbir
müşteri göstermedi. Ödeme istekliliği: sıfır kanıt; Türkiye'de GES tahmini fiyatı yok. Satın alma yapılabilirliği: bilinmiyor. Dört adlı aday: Inavitas (ortak + toplayıcı), Aksa
Dengeleme (kısa liste), Akenerji (segment D, «dengesizlikten kaynaklı maliyet» beyanı — K-46), Birleşim Grup Enerji (13 GES + 1 RES, 146 MW, YEKDEM — doğrulandı, K-50).

## 6. Pazar — ne değişti (02)
19.10.2026 paketi: KGÜP artık YEKDEM gelirinin şartı (YEK 23/6), program sapması TEİAŞ izlemesinde, KÜPST yeni katsayılar (14907, Kasım 2026), V 150 → 100 (maliyeti düşürür), lisanssız
portföy yükü toplayıcı/GTŞ'de (uzaktan kontrol, talimat/TELMT, 18.12 revize). 15 dk tarihi belirsiz. TBMM 2/4042 Komisyonda. Güneş 28,2 GW; lisanslı 3,12 GW; 148 üretim lisansı; 49 toplayıcı.

## 7. Adaylar (03)
Havuz 40, kısa liste 15 (A 5 · B 2 · C 6 · D 2). Yeni doğrulananlar: Birleşim Grup Enerji, Zeros («1.000+ MW, 150+ katılımcı»), İş Enerji (700 MW GES + toplayıcı), Kıvanç Toptan (toplayıcı), Rönesans Reflex.

## 8. Program araçları (04–10)
Görüşme: D1–D7 + Y1–Y8, sinyal merdiveni 6 basamak, şiddet puanı (eşik 12 ÖNERİ). Pilot: 06/07, eşikler Z/B/G ÖNERİ. Finansal: 08 «varsayımsal fark», mutabakat önce. Fiyat: 09 sayısız,
ayrım merdiveni 0–5. Dönüşüm: 10, 8 ret sınıfı.

## 9. Puan kartı (11) ve riskler (12)
13 ölçü, gerçek hepsi 0; karar sınıfı BELİRSİZ. 13 risk; en yüksek R1 erişim ve R9 toplayıcı değer önermesi; R5/R6 pilot öncesi ölçüm ister.

## 10. Sonraki adım (14)
İzin bekleyen dış eylemler D1–D11. Önerilen sıra: D8 canlı SQL → D11 eşik + pilot ücreti kararı → D4/D5/D6 okuma → D1 A segmenti **30.11 öncesi** → görüşmeler → pilot → Ocak 2027 ilk 08 raporu.
Tek «Rapor:» commit'i kullanıcı kararıyla.
