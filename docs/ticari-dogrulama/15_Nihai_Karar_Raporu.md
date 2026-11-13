# 15 — Nihai karar raporu: Faz 8 ticari doğrulama programı (13.11.2026)

> **Tek cümle:** Program **hazırlandı, uygulanmadı** — 15 belge ve 5 CSV masa başında tamamlandı; görüşme 0, pilot 0, finansal doğrulama 0, teklif 0, ödeme 0. Dış eylemlerin hepsi
> kullanıcı izni bekliyor (14 §2). Tamamlanma sınıfları: **Tamamlandı · Kısmen · Doğrulama gerekiyor · Engellendi** — gerçekleşmemiş hedefe «tamamlandı» yazılmaz.
> Her sayı kanıt siciline (13, K-01…K-65) ya da belgeye bağlıdır; kişi adı yok; TL vaadi yok; «tasarruf/garanti/kazanç/ceza» yok.

## 1. Yönetici özeti ve karar

- **Teknik yapılabilirlik:** var (Faz 0–6 canlı v2.609; doğrulama motoru gerçek Türk GES verisiyle çalışır — K-01…K-05, K-23).
- **Problem şiddeti:** yalnız mevzuattan türetilen hipotez ve varsayımsal senaryo (K-07); **hiçbir müşteri problemi göstermedi** (görüşme yok). Mevzuat problemi büyüttü: KGÜP artık YEKDEM
  gelirinin şartı (02 M1), program sapması TEİAŞ izlemesinde (M2), lisanssız portföy yükü toplayıcı/GTŞ'de (M5), KÜPST yeni katsayılarla (M3).
- **Ödeme istekliliği:** sıfır kanıt (K-28); Türkiye'de GES tahmini için yayımlanmış fiyat yok (09 §5).
- **Satın alma yapılabilirliği:** bilinmiyor; kısa listedeki kuruluşların çoğu büyük grup (R1).
- **Karar (11 §3 ölçütleriyle): BELİRSİZ** — Ö1 = 0 < 8. GO / ITERATE / STOP için önce 14 §2 D1 (görüşme izni) gerekir. Önerilen ilk adım: D8 (canlı 30 gün SQL) + D11 (eşik ve pilot ücreti
  kararı) + D1 A segmenti 30.11 öncesi.

## 2. Başlangıç hedefleri — hedef / doğrulanmış ilerleme / kanıt / kalan iş / sonraki adım

| Hedef (brief) | Doğrulanmış ilerleme | Kanıt | Kalan iş | Sonraki adım | Sınıf |
|---|---|---|---|---|---|
| Sektör görüşmeleri 12–15 kuruluş | **0 görüşme.** Hazır: aday havuzu 40 / kısa liste 15 (03), protokol D1–D7 + Y1–Y8 (04), kayıt şablonu (05), e-posta/arama taslakları | K-19, K-49…K-60; 05 §4 tablo 0 | tüm görüşmeler | 14 D1–D3 (izin) | **Engellendi** (dış eylem izni yok) — hazır |
| Lisanslı GES pilotu 1–2 | **0 pilot.** Hazır: 06 (G1–G9, ölçütler, Z/B/G eşikleri ÖNERİ, kontrol listesi) | K-61 | eşik kalibrasyonu (canlı 30 gün), onay, aday, veri sözleşmesi, 60 gün | 14 D8 → D11 → D9 | **Engellendi** — hazır; eşikler **Doğrulama gerekiyor** |
| Toplayıcı/DSG pilotu 1 portföy | **0 pilot.** Hazır: 07 | K-61 | aday (Aksa/Zorlu/Zeros/Limak/Rönesans), üye izinleri, sözleşme kalıbı | 14 D1 (C) → D9 | **Engellendi** — hazır |
| Geriye dönük finansal analiz ≥ 2 dönem | **0 dönem.** Hazır: 08 yöntem + girdi şartnamesi + şablon CSV; resmî bildirim hiç görülmedi | K-62; Faz 2 08 | müşteri bildirimleri (G1–G3), mutabakat, karşı-olgu; ilk 2 dönem en erken Ocak 2027 | 14 D9 → 08 | **Engellendi** — hazır |
| Ücretli dönüşüm denemesi | **0 teklif, 0 ödeme.** Hazır: 09 (ayrım merdiveni, egzersizler, teklif şablonu sayısız), 10 (süreç, ret sınıfları, devir) | K-63, K-64 | fiyat seviyesi (≥5 kuruluş egzersiz), pilot kapanışı, teklif | 14 D10, D11 | **Engellendi** — hazır |

## 3. Pazar bulguları (02; K-29…K-48) — ne değişti

1. **19.10.2026 paketi (RG 33405):** YEK Yön. 23/6 — düşük/negatif fiyat ve yük atma dönemlerinde KGÜP üstü üretim YEKDEM dışı, KGÜP yoksa KGÜP = 0 (M1); DUY 68/69/71A/73 — KGÜP 15:30,
   GİP +30 dk, KGÜP üstü üretim TEİAŞ uyarısı → Kuruma rapor (M2); Karar 14907 KÜPST katsayıları (güneş 0,08/0,05; dağıtım-lisanssız 0,25/0,01; Kasım 2026'dan) (M3); Karar 14911
   V 150 → 100 TL/MWh (M4; maliyeti −%1 mertebesinde **düşürür**, artırmaz — K-32); lisanssız portföy paketi: GTŞ/toplayıcı UEVÇB'si, uzaktan kontrol, talimat/TELMT, 18.12 anlaşma revizesi, 14909 SCADA cezai şartı 30.04.2027'ye kadar askıda (M5).
2. **15 dk uzlaştırma:** hukuki altyapı var, fiilî tarih yok — YORUM GEREKTİRİR (M6); 2027 m.110 yapısı kural tablosunda «belirsiz» (08 §3.1).
3. **TBMM teklifi 2/4042 (12.11.2026, Komisyonda):** ≥750 kW, 10 yılı dolan lisanssız → lisanslıya isteğe bağlı geçiş; KGÜP/dengesizlik yükümlülüğü metinde yok (M15).
4. **Pazar sayıları (EPDK Eylül 2026):** güneş 28.221,78 MW; lisanslı 3.124,46 MW; güneş üretim lisansı 148 adet / 6.089,52 MWe; lisanssız ödeme 9,997 milyar TL/ay; toplayıcı lisansı
   49 yürürlükte; Şeffaflık YEKDEM güneş lisanslı 1.468,81 / lisanssız 24.209,90 MW (K-41, K-40, K-48).
5. **Şirket sinyalleri:** Akenerji «dengesizlikten kaynaklı maliyet azaltılması» (segment D, K-46); Aksa «portföyü ilk dolduran»; Zorlu «üretim tahminleme»; Enerjisa MÇ 146,4 MWp; Zeros «1.000+ MW
   portföy, 150+ katılımcı» (K-52); toplayıcı sitelerinde «toplayıcılık» ve «tahmin/KGÜP» dili nadir (K-58); lisanslı GES sahiplerinin sitelerinde «KGÜP/dengesizlik» hiç yok (K-57).
6. **Segment × problem hipotezi (02 §4):** A ve C'de mevzuata bağlı ve büyüdü; B sözleşme/rapor emeği; D ticaret kararı; D′ (lisanssız sahibi) müşteri değil. **Hiçbiri görüşmeyle doğrulanmadı.**

## 4. Aday havuzu ve kısa liste (03; K-49…K-59)

Havuz 40 (A 18 · B 8 · C 10 · D 4; doğrulanmış aday 24, ek araştırma 15, ortak 1). Kısa liste 15: **A** Birleşim Grup Enerji (13 GES + 1 RES, 146 MW, YEKDEM — doğrulandı, K-50),
Kalyon (≈2.000 MW, ticaret birimi sitede yok, K-51), Kıvanç/Ilgaz (35 MWe + toplayıcı lisanslı toptan satış şirketi, K-54), Margün (118 MWp, BIST), Akfen (GES 121,4 MW + Gökada
toplayıcı + KAP'ta «dengesizlik maliyetlerini düşürme», K-55); **B** Enerjisa Müşteri Çözümleri, Eksim (Viranşehir GES 191,6 MW + toplayıcı); **C** Aksa, Zorlu, Zeros, Limak, Rönesans
Reflex (tahmin dili, K-56), CK Enerji (GTŞ); **D** Akenerji, Enerjisa Üretim. Yedekler ve havuz dışı (rakip/ortak/erişilemeyen) 03 §2/§4. YEKDEM dışı ≈97 lisans sahibi adıyla yok (14 D4).

## 5. Görüşme programı (04, 05) — hazır, uygulanmadı

E rehberi (S1–S20, H1–H20) + D1–D7 davranış soruları + Y1–Y8 Ekim 2026 soruları; segment akışları; **sinyal merdiveni 6 basamak**; **şiddet puanı** sıklık × maliyet × yetersizlik (yalnız
K2/K3; eşik 12 ÖNERİ); pilot nitelik matrisi; sentez şablonu; iletişim taslakları **gönderilmedi**. Takvim: A segmenti 30.11 öncesi; Y4 11–15.12 sonrası. Persona asgarileri: TC 1 eksik (yedekten).

## 6. Pilot protokolleri (06, 07) — eşikler önceden yazıldı, ÖNERİ

Lisanslı: G1–G9; ölçütler motorun hesapladıklarıyla (kWp normalizasyonu); Z: ≥30 gün, kapsama ≥%95, kullanılabilirlik ≥%95, bütünlük %100; B: beceri persistans ≥%20, CLIPER ≥%10
(≥12 ay geçmiş yoksa hesaplanamaz), |nMBE| ≤%5, PICP80 ∈[70,90], kuyruklar [5,15]; G: WMAPE eşiksiz (Solentegre %25,9 analiz meteosuyla; canlı daha yüksek beklenir). Toplayıcı/DSG:
üyelik/sözleşme/veri yetkisi; ρ-yöntemi PICP80; DSG net sapma mutabakatı ≤%5; karar desteği ≠ emir. **Canlı 30 gün sayıları okunmadı** → kalibrasyon şart (14 D8).

## 7. Finansal doğrulama yöntemi (08) — hazır, uygulanmadı

Gerçek KGÜP ↔ karar anındaki «program» koşusu KGÜP′; aynı UEVM/fiyat/kural; çıktı **«varsayımsal fark»**; 7 kalem FEM nitelik etiketiyle; G1–G10 girdi; **mutabakat ≤%1 önce**; sızıntı
kontrolleri; dönem ↔ kural tablosu (2026 / Kasım 2026 / 2027 belirsiz); ilk 2 dönem raporu en erken **Ocak 2027**. Karşı-olgu ürün içinde tek tıkla yok (§14).

## 8. Fiyat ve ödeme istekliliği (09) — sayısız

Ayrım merdiveni 0–5 (yalnız kabul edilen teklif / imza / fiili ödeme dönüşüm); Faz 6 formülü `P_platform + P_portföy(S, M) + Σ P_modül`; egzersizler E1–E9 (geçmiş davranış); deneyler T1–T4;
teklif mektubu şablonu (sayı alanları boş). Pilot ücreti **karar açık**. Dış çapalar yalnız iç referans (RİTM yalnız RES; Türkiye GES fiyatı yok).

## 9. Dönüşüm süreci (10)

10 adım; ret gerekçesi 8 sınıf (ürün itirazı ↔ engel ayrı); kapanış 22 alan; devir belgesi («vaat edilmeyenler» dâhil); abonelik pilot → aktif panelden, ödeme panel dışı.

## 10. Puan kartı (11; `puan_karti.csv`)

| Ölçü | Hedef | Gerçek 13.11.2026 |
|---|---|---|
| Görüşülen kuruluş | 12–15 | 0 |
| Problem gösterildi (sinyal ≥2) | ≥%50 | 0 |
| Şiddet ≥12 kuruluş | ≥5 (ÖNERİ) | 0 |
| Pilot taahhüdü (sinyal ≥4) | ≥3 | 0 |
| Lisanslı pilot / toplayıcı pilot | 1–2 / 1 | 0 / 0 |
| Teknik kabul | ≥%50 | 0 |
| Finansal dönem | ≥2 | 0 |
| Teklif / kabul / ödeme | ≥3 / ≥1 / ≥1 | 0 / 0 / 0 |

GO / ITERATE / STOP ölçütleri 11 §3'te, görüşmelerden önce yazıldı (ÖNERİ). Bugünkü sınıf: **BELİRSİZ**.

## 11. Riskler (12)

13 risk; en yüksek birleşik: **R1 erişim** (soğuk kurumsal e-posta dönüşü bilinmiyor) ve **R9 toplayıcı değer önermesi** («dengesizliği biz üstleniyoruz» → üreticide argüman kayar). Pilot
öncesi ölçüm isteyen teknik riskler: R5 canlı doğruluk (kalibrasyonsuz, kış), R6 tek işçi kapasitesi (≈17 konum). R12: ücretsiz pilot ödeme sinyali üretmez. R7: RG rutini etkin (pazartesi 09:00 TSİ).

## 12. Belgeler ve kanıt sicili (13)

`docs/ticari-dogrulama/01…15` + `aday_havuzu.csv` (40×17), `gorusme_kayit_sablonu.csv` (20 sütun, boş), `finansal_dogrulama_sablonu.csv` (13, boş), `puan_karti.csv` (13 ölçü),
`kanit_sicili.csv` (**65 satır**: DO çoğunluk; KÇ/ÇH/DM işaretli). Kanıt dosyaları `~/Desktop/PVQuant_Faz8_Ticari_Dogrulama/kanit/` (F8-B/C ajan raporları, tarayıcı bulguları, YEK 37 CSV,
toplayıcı 49 CSV, canlı okuma SQL). Her paket öz incelemeden geçti (A 4/4, B 9/9, C 5/5, D 6/6, E 5/5, F 4/4, G 3/3, H 4/4, I 2/2); üç kalite turu `kanit/F8-I_kalite_turlari_2026-11-13.md`.

## 13. Tamamlanma sınıfları ve müşteri dili

| İş | Sınıf | Neden |
|---|---|---|
| Kanıt sicili, protokoller (04–10), puan kartı, risk sicili, eylem planı | **Tamamlandı** | masa başı; öz inceleme geçti |
| Pazar araştırması (02) | **Kısmen** | YEKDEM dışı lisans sahipleri adıyla yok (reCAPTCHA); Şeffaflık santral listesi okunamadı; 12 küçük toplayıcı doğrulanamadı |
| Aday havuzu (03) | **Kısmen** | 15 satır «ek araştırma»; grup bağları KAP'tan teyit bekliyor |
| Pilot eşikleri (06/07 §4) | **Doğrulama gerekiyor** | canlı 30 gün sayılarıyla kalibrasyon + kullanıcı onayı |
| Görüşmeler, pilotlar, finansal doğrulama, teklif, ödeme | **Engellendi** | dış eylem izni yok; müşteri yok; resmî bildirim yok; takvim (Ocak 2027) |
| **Müşteri dili sözlüğü** (görüşmelerden; 05 «musteri_kelimesi_aynen») | boş | görüşme yok — ürün dili için ileride |

## 14. Ürün sonuçları ve boşluklar (kod değişikliği Faz 8'de yok; ayrı karar)

| Boşluk | Kaynak | Etkilenen segment |
|---|---|---|
| KGÜP = YEKDEM şartı (YEK 23/6) uyarısı / «olası kayıp» göstergesi | 02 M1; 08 §2 | A (YEKDEM'de) |
| KGÜP üstü üretim / program sapması izleme (DUY 73/9 TEİAŞ uyarısı) | 02 M2 | A, C |
| Talimat/TELMT uzlaştırması; BUDÜP ≠ KGÜP saatleri | 02 M5; 08 §2 | C (GTŞ/toplayıcı) |
| Karşı-olgu KGÜP′ ile ikinci hesap tek tıkla (08 yöntemi) | 08 §8 | tümü |
| Depolamalı GES muhasebesi (YEK 8/7; KÜPST m 0,05) | 03 §6 | A (depolamalı) |
| Hibrit tesis kaydı (yardımcı kaynak güneş, 182 tesis) | 03 §6 | B |
| Kurumsal Şeffaflık/EPYS erişim yöntemi (API anahtarı) | 02 M18; 12 R4 | PVQuant |
| 15 dk uzlaştırma çözünürlüğü | 02 M6 | tümü (tarih belirsiz) |
| TPYS bildirimi (yok; öneri + beyan) | 06 §1 | A, C |
| Kurulum emeği ölçümü; tek işçi kapasitesi | 09 §2; 12 R6 | PVQuant |

## 15. Dış eylemler ve karar

- **İzin bekleyen dış eylemler (14 §2):** D1 görüşme e-postaları (15 kuruluş; A segmenti 30.11 öncesi), D2 arama, D3 kamu/OSB, D4 EPDK lisans sorgusu (reCAPTCHA), D5 Şeffaflık listeleri,
  D6 KAP, D7 şirket siteleri (tarayıcı), D8 canlı SQL (kullanıcı çalıştırır), D9 pilot sözleşmeleri, D10 teklif gönderimi, D11 eşik + pilot ücreti kararı. **Hiçbiri yapılmadı.**
- **Karar (11 §3):** **BELİRSİZ** — ticari doğrulama başlamadı; GO/ITERATE/STOP verilemez. İlk 5 görüşme R1 ve R9'un ilk kanıtını verir; ilk pilot kabulü ve ilk 08 raporu (Ocak 2027) GO için
  asgari koşulların ikisidir; fiili ödeme olmadan GO yok.
- **Bu rapor ne söyler:** program eksiksiz hazır, dürüstlük kuralları her belgede, her sayı kaynaklı. **Ne söylemez:** müşteri problemi, ödeme istekliliği, fiyat seviyesi, pilot başarısı — bunların hiçbiri henüz bilinmiyor.
