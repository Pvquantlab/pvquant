# 08 — Geriye dönük finansal doğrulama yöntemi (Faz 8, F8-F — 13.11.2026)

> **Durum: HİÇ FİNANSAL DOĞRULAMA YAPILMADI.** Resmî bir uzlaştırma bildirimi bugüne kadar PVQuant'ta görülmedi (Faz 2 08: «resmî uzlaştırma verisi yok; gerçek EPYS dosya
> başlıkları doğrulanmadı»). Bu belge, bir pilot müşterinin **en az iki uzlaştırma dönemi** için yapılacak geriye dönük analizin yöntemini, girdi şartnamesini ve rapor şablonunu
> önceden yazar. Çıktı hiçbir zaman «tasarruf» değildir; **varsayımsal fark**tır (K-06: altı şartın üçü eksik — müşterinin önceki tahmini, karşılaştırılabilir sözleşme şartı,
> bağımsız ticari doğrulama). Faz 2 C geri testi (K-07) **sentetik hata serisiyle varsayımsal senaryodur** ve bu yöntemin yerine geçmez. Formüller `ext/turkiye/kurallar.py` ve Faz 2
> `05_Mevzuat_Kunyesi.md`'deki kural kümesidir; bu belge formül yazmaz, yeniden türetmez (çekirdek değişmez).

## 1. Soru ve karşılaştırma

| | Mevcut süreç (gerçekleşen) | PVQuant destekli (karşı-olgu) |
|---|---|---|
| Program | müşterinin TPYS'ye bildirdiği **gerçek KGÜP** (UEVÇB × saat; D-1 kesimi öncesi son sürüm) | aynı saatler için PVQuant'ın **karar anında** (D-1 15:30 kesimi öncesi) yayımlanmış «program» koşusu P50 → KGÜP′ |
| Üretim | uzlaştırmaya esas veriş (UEVM) — aynı | aynı |
| Fiyat / yön | PTF, SMF, sistem yönü — aynı | aynı |
| Kural | dönemde yürürlükteki DUY 110/111 kural kümesi — aynı | aynı |
| Sonuç | **resmî** EDT + KÜPST (bildirim) ↔ PVQuant yeniden hesabı (mutabakat) | **varsayımsal** EDT′ + KÜPST′ |
| Fark | — | (EDT + KÜPST) − (EDT′ + KÜPST′); artı = santral lehine; etiket **«varsayımsal fark»** |

Sorulmayan: «ne kadar tasarruf etti» (etmedi; KGÜP′ hiç bildirilmedi), gelecek dönem tahmini, fiyat/ödeme (`09`), teknik kabul (`06/07`).

## 2. Kavram ayrımı (her kalem ayrı satır, ayrı nitelik)

| Kalem | Tanım | Birim | Nitelik (FEM sözlüğü: resmî › hesaplanan › sözleşme tahmini › senaryo › eksik) | Nereden |
|---|---|---|---|---|
| Üretim sapması | UEVM − KGÜP (saat; dönem toplamı ve mutlak toplam) | MWh | hesaplanan (UEVM ve KGÜP resmî) | sayaç + TPYS |
| Dengesizlik tutarı (EDT) | EDTA/EDTB kuralıyla alacak/borç; k/l yön bazlı; V/B/AFL dalları | TL | **resmî** (bildirim) · hesaplanan (yeniden hesap) · **varsayımsal** (KGÜP′) | EPYS bildirimi / FEM |
| KÜPST | KÜPSM × max(750; PTF; SMF) × n; KÜPSM = max(0, \|UEVM − BUDÜP\| − m·BUDÜP); BUDÜP = KGÜP ± talimatlar (YAL/YAT) + SRDM/SFHM (02 M3) | TL | resmî · hesaplanan · varsayımsal; **talimatlı saat varsa BUDÜP bilinmiyorsa «hesaplanamaz»** | bildirim / FEM |
| DSG etkisi | grup netleşmesi; üye eşiği (%5); bağımsız ↔ DSG içi ↔ netleşme farkı | TL | «Sözleşmeye dayalı dağılım» yalnız belgeyle; aksi **varsayımsal**; diğer üyelerin pozisyonu yoksa **hesaplanamaz** | Faz 3 üç perspektif |
| Satış geliri | UEVM × tarife (YEKDEM / İA / PTF); karşı-olguda değişmez (üretim aynı) — **toplama girmez**, bağlam | TL | resmî (YEKDEM bildirimi) · sözleşme tahmini · senaryo (PTF) | FEM `satis_geliri` |
| Olası kayıp | YEK 23/6: düşük/negatif fiyat ya da yük atma saatlerinde KGÜP üstü üretim YEKDEM dışı (Kasım 2026'dan); talimata uyulmayan kısım (lisanssız, TELMT) | TL / MWh | **gösterge, resmî değil, toplama girmez**; KGÜP′ ile değişebilir — ayrı satır | 02 M1, M5 |
| Varsayımsal fark | (EDT + KÜPST) − (EDT′ + KÜPST′), kalem kalem | TL | **varsayımsal** — rapor başlığında ve her sayıda etiket | §4 |

Toplam kuralı (FEM): en zayıf nitelik kazanır; senaryo fiyatlı ya da yön varsayılan saat varsa dönem toplamı «senaryo»; eksik ölçüm saati 0 sayılmaz (NaN) → o saat her iki tarafta da dışlanır.

## 3. Girdi şartnamesi (her girdi: kaynak, biçim, nitelik, zorunlu/isteğe bağlı, kontrol)

| # | Girdi | Kaynak (kim verir) | Biçim | Nitelik | Z/İ | Kontrol |
|---|---|---|---|---|---|---|
| G1 | **Resmî uzlaştırma bildirimi** (ön ve/veya **faturaya esas nihai**): dönem, UEVÇB, EDT alacak/borç, KÜPST, (YEKDEM) kalemleri; sürüm/tarih | müşteri, EPYS dışa aktarımı | EPYS Excel/CSV (gerçek başlıklar **doğrulanmamış** — ilk bildirimde kalem eşleme tablosu çıkarılır) | resmî | **Z** | takvim: ay M → ön ≈ M+1'in 11'i, itiraz 12'si 17:30, nihai ≈ 15'i (M19); nihai yoksa «ön bildirim» etiketi |
| G2 | **Orijinal üretim programı (KGÜP)**: UEVÇB × saat, bildirilen son sürüm + revizyon zaman damgaları | müşteri (TPYS dışa aktarımı / arşiv) | saat, UEVÇB, KGÜP_MWh, bildirim_zamanı | resmî | **Z** | D-1 15:30 kesimi öncesi sürüm esas; sonraki GİP revizyonları ayrı sütun; eksik saat → o saat dışlanır |
| G3 | **Uzlaştırmaya esas üretim (UEVM)**: saatlik veriş | müşteri (bildirim eki / sayaç) | saat, MWh | resmî | **Z** | PVQuant ölçümüyle (SCADA/sayaç) karşılaştırma: fark > %2 ise ölçüm sınırı/kayıp açıklanır; UEVM esastır |
| G4 | **Karar anındaki PVQuant tahmini**: «program» kuralı koşusu (D-1 kesimi öncesi son yayın), P50 (P10/P90 bilgi), yayın damgası, koşu künyesi | PVQuant koşu arşivi | saat, p50_kw, run_at, run_id, model, meteo_source | hesaplanan | **Z** | **geriye bakış 0**: run_at ≤ kesim; `model='backtest'` / arşiv meteolu koşular DIŞLANIR (motor zaten dışlar); dönem içinde koşu yoksa o gün **hesaplanamaz** — analiz meteosuyla doldurulmaz; UEVÇB birden çok santral içeriyorsa santral P50'leri toplanır, biri eksikse o saat hesaplanamaz; **KGÜP′ = P50 varsayımı** (müşterinin elle düzeltmesi yok — varsayım listesinde) |
| G5 | **EPİAŞ fiyat ve yön**: PTF, SMF, sistem yönü (saatlik) | Şeffaflık (müşteri hesabı) ya da günlük bülten PDF; PVQuant `piyasa_service` | saat, PTF, SMF, yön | resmî (EPİAŞ) | **Z** | bildirimdeki fiyatla tutarlılık; eksik saat → senaryo etiketi (toplam «senaryo») |
| G6 | **Geçerli kural ve dönemi** | PVQuant kural tablosu (Faz 2 05 künyesi) | kural kümesi sürümü | — | **Z** | dönem ↔ kural eşlemesi (§3.1); dönem içinde kural değişirse saat bazında |
| G7 | **Sözleşme / portföy şartı**: YEKDEM mi (yıl), İA/PPA mı; DSG üyeliği (tarih, paylaşım kalıbı), toplayıcı portföyü | müşteri (belge özeti) | metin + belge | sözleşme tahmini / resmî | **Z** (etiket için) | belge yoksa DSG dağılımı «varsayımsal» (Faz 3 kuralı); satış geliri niteliği |
| G8 | **Olay kaydı**: kısıntı, arıza, bakım, **YAL/YAT talimatı**, acil durum | müşteri | saat aralığı, tür | — | İ (yoksa uyarı) | talimat saatlerinde BUDÜP ≠ KGÜP → KÜPST «hesaplanamaz» o saatlerde; kısıntı saatleri tahmin hatasına yazılmaz, ayrı listelenir |
| G9 | Müşterinin **kendi** hesabı (varsa; Excel) | müşteri | serbest | hesaplanan (müşteri) | İ | mutabakat üçgeni: resmî ↔ müşteri ↔ PVQuant |
| G10 | Gün içi işlemler (GİP) ve ikili anlaşma pozisyonu | müşteri | saat, MWh, fiyat | resmî | İ | karşı-olguda GİP davranışı **sabit** varsayılır; belirtilir; pozisyon yoksa saf satıcı |

### 3.1 Dönem ↔ kural eşlemesi (Faz 2 C sabitler sayfası; birincil atıflar orada ve 02 §1)

| Dönem | EDT formülü | k / l | V / B | AFL | KÜPST m / n (güneş, lisanslı) | Not |
|---|---|---|---|---|---|---|
| 1.1.2026 – 31.10.2026 | DUY 110 (RG 29.12.2025) | yön bazlı (Karar 14030): açık 0,06/0,03 · fazla 0,03/0,06 · dengede 0,03/0,03 | 150 / 100 | 3.400 → **4.500 (4.4.2026'dan)** | 0,08 / 0,05 (14029; YEK aylık arıza ≥30: 0,08) | 15 dk yok (60 dk) |
| **1.11.2026 –** (Kasım dönemi; ilk bildirim ≈ 11–15.12.2026) | DUY 110 (RG 19.10.2026 değişikliği; saatlik birim fiyat yapısı aynı, aylık toplama satırları değişti — C-315) | aynı (14030) | **100** / 100 (Karar 14911) | 4.500 | **14907**: güneş 0,08 / 0,05 (≥30 arıza 0,08); dağıtım-lisanssız 0,25 / 0,01; iletim-lisanssız 0,20 / 0,02 | YEK 23/6 KGÜP-YEKDEM şartı (olası kayıp satırı) |
| **1.1.2027 –** | **hukuken BELİRSİZ**: RG 21.1.2025-32789 Md.13 + Md.20(b) m.110(1)-(4)'ü 1.1.2027'de değiştiriyor (tek EDT_f; V/B/AFL ve EDTA/EDTB yok; tek k/l; KÜPST 15 dk «ç»), ama 33122/33405 aynı fıkraları yeniden yazdı ve tek k/l ile «ç» bazlı KÜPSM kararları yok → kural tablosu 2026 rejimini sürdürür, **her 2027 sonucu «belirsiz» bayrağı taşır** (`BELIRSIZ_2027_GEREKCE`) | ? | ? | 4.500 | ? | 2027 DSG oranı kararı en geç 1.12.2026; Ocak 2027 dönemi raporu bu bayrakla yazılır (02 M6 ile uyumlu: 15 dk tarihi YORUM GEREKTİRİR) |
| 2025 (yalnız bağlam) | 2025 kuralı k = l = 0,03 | — | — | 3.000 → 3.400 (5.4.2025) | 0,10 / 0,03 (13025) | PVQuant koşusu yok → karşı-olgu **yapılamaz** |

Kural değerleri bu belgeye kopyalanırken yanlışlanabilir: **esas kaynak kural tablosu ve künye**; rapor kural sürümünü ve hash'ini yazar.

## 4. Yöntem adımları

1. **Girdi tamlığı** (G1–G7 zorunlu): eksikse analiz **başlamaz**; «değerlendirilemedi — eksik: …» raporu yazılır (fark uydurulmaz).
2. **Mutabakat (önce):** PVQuant, müşteri KGÜP + UEVM + fiyat/yön + kural kümesiyle EDT ve KÜPST'ü yeniden hesaplar (FEM `uzlastirma_bilesenleri`); resmî bildirimle kalem kalem
   karşılaştırır. Kalem farkı ≤ %1 (ya da ≤ ölçüm toleransı) → «mutabık»; aksi hâlde neden aranır (fiyat sürümü, saat dilimi, kural dönemi, talimat/BUDÜP, YEKDEM kalemi). **Mutabakat
   sağlanmayan dönemde karşı-olgu hesaplanmaz** (aynı motor yanlışsa fark da yanlıştır).
3. **Karşı-olgu:** KGÜP′ = PVQuant «program» koşusu P50 (saat bazında; birim dönüşümü kW → MWh; UEVÇB'ye göre). Aynı UEVM, aynı fiyat/yön, aynı kural; EDT′, KÜPST′ hesaplanır.
   Koşu olmayan gün/saat her iki tarafta da dışlanır ve sayılır («karşılaştırılabilir saat oranı»).
4. **Fark ve ayrışım:** varsayımsal fark = (EDT + KÜPST) − (EDT′ + KÜPST′); kalem kalem (EDT, KÜPST), yön ve saat kesitleri (öğle fazlası / sabah-akşam / düşük fiyat saatleri),
   gün bazında dağılım (medyan, en iyi/en kötü 5 gün). İşaret: artı santral lehine (FEM sözleşmesi). **Üretim sapması** MWh olarak yanında (mutlak toplam müşteri KGÜP ↔ KGÜP′).
5. **DSG/portföy:** üye ise ve diğer üyelerin pozisyonu + sözleşme kalıbı verilmişse Faz 3 üç perspektifle; değilse yalnız bağımsız perspektif ve «DSG etkisi hesaplanamadı».
6. **Olası kayıp (gösterge):** Kasım 2026 ve sonrası dönemlerde YEK 23/6 saatleri (PTF/SMF < V ya da yük atma) için KGÜP üstü üretim MWh ve KGÜP′ ile farkı — toplama girmez.
7. **Güven ve sınırlama değerlendirmesi** (§6) raporun başında; dil kontrolü (§7).
8. **İkinci kişi doğrulaması:** girdi hash'leri (tahmin kümesi, saat kümesi, fiyat kümesi), kural sürümü, bildirim sürümü; yeniden üretilebilirlik.

## 5. Gelecek-veri sızıntısı kontrolleri (hepsi zorunlu)

| Kontrol | Kural | Nasıl kanıtlanır |
|---|---|---|
| Yayın damgası | her saat için kullanılan koşunun `run_at` ≤ D-1 15:30 TSİ (program kesimi); gün içi koşular karşı-olguda kullanılmaz (ayrı «gün içi» senaryosu yalnız etiketle) | koşu künyesi listesi raporda; `karne_kurali.program_kovasi` |
| Meteo kaynağı | yalnız NWP koşuları; `model='backtest'` / arşiv-analiz meteolu koşular dışlanır | `meteo_source` dağılımı raporda |
| Kalibrasyon | koşu anında geçerli kalibrasyon/konformal (künyede `konformal_hesap_zamani` ≤ run_at); dönem sonrası yeniden kalibrasyon kullanılmaz | künye alanları |
| Fiyat | fiyatlar gerçekleşen (resmî) — karşı-olgu KGÜP′ fiyatı etkilemez varsayımı (santral fiyat alıcı) yazılır | varsayım listesi |
| Ölçüm | UEVM resmî; PVQuant ölçümü yalnız çapraz kontrol | G3 |
| KGÜP′ tanımı | KGÜP′ = «program» P50 aynen (elle düzeltme, güvenlik payı, GİP revizyonu yok); gerçek kullanıcı farklı davranabilir → varsayım listesinde ilk madde | varsayım listesi |
| Seçim yanlılığı | dönemler önceden sabitlenir (müşteriyle yazılı: hangi iki ay); «iyi çıkan ay» sonradan seçilmez | protokol eki |

## 6. Güven ve sınırlama değerlendirmesi (rapor başında)

| Boyut | Ölçü | Sınıf |
|---|---|---|
| Nitelik | dönem toplamının niteliği (resmî / hesaplanan / senaryo); karşı-olgu her zaman «varsayımsal» | FEM sözlüğü |
| Tamlık | karşılaştırılabilir saat oranı (koşu + UEVM + fiyat + KGÜP var) / dönem saati; FEM hesap durumu (tam / kısmi / senaryo / hesaplanamadı) | ≥ %95 tam · %80–95 kısmi · < %80 raporlanmaz |
| Mutabakat | resmî ↔ yeniden hesap kalem farkı | ≤ %1 mutabık · aksi açıklamalı |
| Dönem sayısı | ≥ 2 dönem = iki nokta, eğilim değil; mevsim etkisi (kış/yaz) açıkça yazılır | — |
| Dışlanan saatler | talimat, kısıntı, eksik koşu — sayısı ve payı | — |
| Genelleme | sonuç «bu santral, bu dönem, bu kural»; başka santrale/yıla taşınmaz; teklif metninde kullanılmaz (`09`: fiyat formüllü, sayı görüşme sonrası) | — |

## 7. Rapor şablonu (`finansal_dogrulama_sablonu.csv` + metin)

Başlık: santral kodu (ad yok), dönem(ler), kural kümesi sürümü + hash, bildirim sürümü (ön/nihai, tarih), kaynak hash'leri (tahmin, saat, fiyat), hesap zamanı, doğrulayan (kısaltma).
Tablo (CSV): `donem, santral_kodu, kalem, nitelik, resmi_tl, yeniden_hesap_tl, mutabakat_fark_pct, karsi_olgu_tl, varsayimsal_fark_tl, karsilastirilabilir_saat_pct, kural_kumesi, kaynak, not`
— kalem ∈ {EDT_alacak, EDT_borc, EDT_net, KUPST, DSG_etkisi, satis_geliri(bağlam), olasi_kayip(gösterge), uretim_sapmasi_MWh, toplam(EDT+KUPST)}.
Metin: §6 tablosu → kalem tablosu → kesitler → dışlananlar → varsayımlar → «bu rapor ne söyler / ne söylemez».
**Dil kuralı:** «tasarruf / kazanç / garanti / ceza» yok; her TL'nin yanında nitelik; «varsayımsal fark» başlıkta; müşteri adı yok.

## 8. Bugün PVQuant'ta ne var, ne yok (uygulama notu; kod değişikliği bu fazda yok)

| Var (Faz 2/3) | Yok (ürün boşluğu → 15 §14) |
|---|---|
| FEM: EDT (EDTA/EDTB), KÜPST, segment kapısı, DSG dönem hesabı, nitelik sözlüğü, yeniden üretim metası; program serisi = bildirilen KGÜP (yoksa öneri, `program_tamamlanan` işareti); Mutabakat sayfası (bildirim yükleme; **gerçek EPYS başlıkları doğrulanmamış**); koşu arşivi + künye; `karne_kurali.program_kovasi` | tek tıkla **karşı-olgu KGÜP′ ile ikinci hesap** (bugün: koşu arşivinden dışa aktarım + elle/CSV); talimat/BUDÜP ve TELMT; YEK 23/6 «olası kayıp» hesabı; 15 dk uzlaştırma |

## 9. Takvim ve ilk uygulanabilir dönemler

- Kasım 2026 dönemi (ilk 14907 + V = 100 dönemi): ön bildirim ≈ 11.12, nihai ≈ 15.12.2026; Aralık dönemi nihai ≈ 15.01.2027 → **ilk «iki dönem» raporu en erken Ocak 2027 ortası**.
- Daha erken yalnız şu şartla: santral için PVQuant'ta **yayın damgalı NWP koşuları dönem boyunca zaten varsa** (canlıdaki etkin santraller 01.10.2026'dan beri; Faz 1 §6) ve müşteri Ekim/Kasım
  bildirimlerini verirse → Ekim + Kasım 2026 mümkün. Ekim dönemi 14029 kuralındadır (karışık kural dönemi yazılır).
- Pilot sonrası başlayan müşteride geriye dönük karşı-olgu **yapılamaz** (koşu yok); yöntem ileriye dönük uygulanır (pilotun 2 uzlaştırma dönemi).
