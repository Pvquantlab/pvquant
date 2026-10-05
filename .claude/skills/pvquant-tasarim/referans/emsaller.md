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

## Süreç emsalleri

- Metin seçimi: blok başına 5 kurumsal-anlaşılır seçenek sun, kullanıcı seçer (v2.392).
- Tasarım adımı: 3 aday + gerçek içerikli önizleme → kullanıcı seçer → uygula (v2.304-307).
- Bulut teslimi devralma: DEVIR.md + temiz patch kalıbı (v2.393).
