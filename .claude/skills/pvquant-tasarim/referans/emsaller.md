# Emsaller dizini — «yeni kalıp icat etmeden önce buraya bak»

Her satır: kalıp → dosya → kritik kural. Yeni mühürde yeni kalıp çıkarsa buraya satır eklenir.

## Vitrin

| Kalıp | Dosya | Kritik kural |
|---|---|---|
| Panel kesiti (kart yerine tek-yüzey hücreler) | `vitrin/TurkiyePiyasasi.tsx` + `.vt-kesit` | 1 px gap=çizgi; hücreler eylemsiz (R21); etiket durum noktası; künye tabana yaslı |
| Kart veri diyagramları (anlam taşıyan mini-SVG) | `vitrin/KartCizimleri.tsx` | amber YALNIZ sapma+alarm (test pini); kılavuz+eksen tiki dili; sembol ikon yasak |
| Hero eylem sütunu + TL bağı | `vitrin/Hero.tsx` | dar ekranda çift-DOM tek görünür; mikro metin düğme altında |
| Canlı gök + crosshair'li referans eğrisi | `vitrin/ReferansEgri.tsx`, `gunesSaati.ts` | NOAA hesabı TRT gün sırası düzeltmeli; crosshair getComputedTextLength kıstırma; touch kalıcı |
| Disiplin bandı + dürüst dipnot | `vitrin/DisiplinBandi.tsx` | «iki test takımının toplamı, aşağı yuvarlanmış» — otomasyon İDDİA EDİLMEZ; sup aria-hidden + .vt-srgizli |
| Bölüm çubuğu (şerit-içi scroll) | `vitrin/BolumCubugu.tsx` + `bolumler.ts` | sayfa zıplatmaz (yalnız şerit scrollLeft, scroll-margin:0); IO küme + belge sırası sonuncu |
| Dört adım zinciri + ayna tablosu | `vitrin/DortAdim.tsx` | ok'lar GRID HÜCRESİ (::after kart overflow'una kırpılır!); ayna role=table, ✓ alt-metinsiz |
| İş ızgarası (4 masa, fayda kalıbı) | `vitrin/IsIzgarasi.tsx` | rakamlı vaat/müşteri iması yasak (test); künye dl/dt/dd |
| Scroll-reveal (R25) | `.vt [data-canlan]` + Ö10 dersi | gizleme YALNIZ keyframe `from` + fill:backwards; sınıf ilk render'da; print animation:none |
| Benekli/grenli SVG dili | `vitrin/varlik/`, feTurbulence tarifi | rasterşiz; bellek: svg-benek-dither-tekniği |

## Panel

| Kalıp | Dosya | Kritik kural |
|---|---|---|
| Hero tahmin grafiği (utility-grade) | `sayfalar/ProductionForecastChart.tsx` | D2 tek-kaynak pencere; D3 now-noktası; V1 dar bant (sıfıra demirli dağ YASAK); V2 AC limiti düz kesik |
| İmza bant motifi | `lib/BandImza.tsx` + `pdf.py _imza_bandi` | AYNI kontrol noktaları iki ortamda; renkler var(--chart-*) |
| İnce EChart sarmalayıcı | `lib/EChart.tsx` | sözleşme grafik-tema.md'de; lazyUpdate + grup/connect |
| Grafik tema fabrikaları | `lib/grafikTema.ts` | TÜM ECharts dosyaları geçti (v2.396-397); bekçi web/test/grafik-tema.test.ts; yeni grafik fabrikasız yazılamaz |
| KPI/çip dili | `santralim/*`, Kpi bileşeni | uyari tonu amber DEĞİL; değer nowrap; tire disiplini (`?? 0` yasak) |
| Ayar/form dili | `index.css .ayar/.girdi` | etikette uppercase yok (birim bozulur) |
| Tablo oluğu | `table.veri` | `th+th/td+td{padding-left}` — oluk ilk sütun dolgusuyla OLMAZ (v2.309) |
| Üç kipli tema | `Kabuk` temaKipi oto\|acik\|koyu | pvq_tema localStorage; oto varsayılan |
| Palet/modal kalıbı | Kabuk ⌘K + YeniSantral | kart örtünün ÇOCUĞU + stopPropagation (v2.308 dersi: kardeş çizim örtü altında kalır) |

| Görsel baseline + değişmezler | `web/tests/visual/` + `playwright.config.ts` | `npm run gorsel`; dondur.ts (sabit saat 12:00 TRT + dogrulama stub); baseline azdır (6 PNG); güncelleme `--update-snapshots` + GÖZLE onay + commit'te «görsel baseline güncellendi: <sebep>»; eşik gevşetme yasak |

## Süreç emsalleri

- Metin seçimi: blok başına 5 kurumsal-anlaşılır seçenek sun, kullanıcı seçer (v2.392).
- Tasarım adımı: 3 aday + gerçek içerikli önizleme → kullanıcı seçer → uygula (v2.304-307).
- Bulut teslimi devralma: DEVIR.md + temiz patch kalıbı (v2.393).

## Split hattı ve kart subgrid (ölçü sistemi, v2.410+)

- **Split kalıbı:** iki sütunlu bölümlerde (hero, TL üstü, SSS, başvuru, ayna) metin
  1–5. kolonlarda (+1 oluk iç pay), medya/cevap 6–12. kolonlarda → bütün sağ sütunlar
  1440'ta **x=630** tek hattında. Yeni iki sütunlu bölüm bu kalıbı kullanır; üçüncü
  çocuk eklenecekse grid-column kuralları güncellenir (vitrin.css P3b).
- 4'lü kart ızgaraları tek oluk (24); dört adım zinciri istisnası: 264 kart + 48 ok şeridi.
- **Subgrid kart hizası (v2.412):** iş kartları 5 satır (rozet/h3/metin/künye/bağ), dört
  adım zinciri 2 satır subgrid — künye ve bağ satırları kartlar arasında hizalı; desteklemeyen
  motorda zarif bozulma (bugünkü akış). Kesit çizim kutusu 16:7 sabit en-boy.
- **Köşe istisnaları (belgeli):** rozet = boyutun ≈%30'u (44→13, 32→10, 24→7); lejant renk
  örneği kutusu 2px (mini yüzey — jeton ölçeği 10×10 kutuya oransız kalır).

## Yaşayan kart dili (v2.413 — Referans kartı emsali)

- **Görünümün tek kaynağı uygulama durumu** (seçili gün + katman görünürlükleri); CSS asla
  durum kaynağı değildir. Katmanlar koşullu render edilir — gizleme CSS'le yapılmaz.
- **SVG/HTML ayrımı:** eksen/ızgara/seri SVG'de; tooltip balonu, bulgu ve AC etiketi,
  kontroller GERÇEK DOM nesneleri (`.vt-nesne` dili: beyaz .96 zemin + 1px mürekkep-alfa
  kenar + yumuşak gölge; cam/blur yok).
- **Katman kontrolü** = `button aria-pressed` + onay kutusu + renk anahtarı; hover ≤1px
  kalkma. Takvim açılırı araç düğmesinin SAĞINA hizalanır (kart overflow:hidden kırpar;
  ≤600'de düğme solda olduğundan sola). Tarih değişiminde çizim `key={gun}` ile sıfırlanır
  — açık balon eski günün değerini taşımaz.
- **Dürüstlük:** takvimde yalnız koşusu olan günler etkin; bulgu rozeti VERİDEN türetilir
  (gercek < p10 − 0,005, ≥3 saat blok); pazarlama kartında gün-üstü kip yok (seyrek veri
  ürünü zayıf gösterir — toplulaştırma referansVeri'de panel için durur).

## Referans dizini (masaüstü araştırma klasörleri — «gerçek SaaS referansı» sorusunun adresi)

| Klasör | Ne için bakılır |
|---|---|
| `~/Desktop/vitrin-rakip-analizi/markalar` | Rakip vitrin ekran kanıtları; Ö1–Ö15 uyarlanabilir öneriler (açık: Ö4 TL vakası, Ö5, Ö12, Ö15) |
| `~/Desktop/vitrin-tasarim-arastirmasi/referans_tokens.json` | Gerçek sitelerden ölçülmüş token kümeleri; YON_ONERILERI yön belgeleri |
| `~/Desktop/vitrin-olcu-sistemi/` | Ölçü sistemi denetimi + Opus teslim CSS'i (v2.408–412'nin kaynağı); 01-denetim/betikler/cdp.mjs test yardımcıları |
| `~/Desktop/ges-tasarim-zekasi/` | Yığının kuruluş gerekçeleri (skill retleri, grafik kütüphane kararı, QA döngüsü) |
| `~/Desktop/rakip-excel-raporlari/` | Solargis/Vaisala/DNV/SolarEdge/Raptor/NREL rapor BİÇİMLERİ — panel Raporlar/dışa verim tasarımında kıyas |
| `~/Desktop/scada-markalari/` | 23 SCADA markasının ekran dili + gerçek üretim arşivleri — panel entegrasyon/izleme ekranlarında kıyas |
| `~/Desktop/kart-tasarim/` · `vitrin-cila-kesif/` · `vitrin-gorsel-kesif/` | Geçmiş tur arşivleri (panel kesiti, Ufuk cilası, palet varyantları) — tekrar keşfetme |

## Vaka dili (v2.416 — Ö4, TL bölümü emsali)

- Pazarlama bölümü bir yetiyi MAKETLE değil, hero'daki araştırma koşusunun GERÇEK
  çıktısıyla anlatır; her sahnede mono künye: «GG.AA araştırma koşusu · … · teslim edilmedi».
- Türetilmiş çıktılar depodaki gerçek fonksiyonla üretilir (15 dk: ext.alt_saatlik),
  kapasiteye ORANLA gösterilir (mutlak MW santral ölçeğini sızdırır) ve tutarlılığı test
  tarar (her saatin dilim ortalaması saatlik değere eşit).
- Depoda hesaplanmamış değer (TL) GÖSTERİLMEZ; tek-gün performans kıyası yapılmaz —
  köprü cümle çok-günlük açık karneye. Çalıştırılmamış yeti açıkça söylenir (Ö4-c).
- Bağ dili: kenardan taşan .vt-nesne saat kartı + kesik MÜREKKEP çizgisi (eylem rengi değil).
