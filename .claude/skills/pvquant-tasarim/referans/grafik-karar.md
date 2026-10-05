# Grafik karar çerçevesi (veri türü → görselleştirme)

Ortak kurallar (her satır için geçerli): renkler YALNIZ `--chart-*` jetonlarından
(mavi=tahmin, amber=YALNIZ gerçekleşen, gri aile=bağlam); eksen/künye Plex Mono
tabular-nums; tooltip tek şablondan; birim eksende BİR kez; animasyon ≤200 ms ya da yok;
legend grafiğin dışında React bileşeni; «ne YAPMA» ihlali inceleme kapısına takılır.

| # | Veri | Birincil | İkincil | Kritik kurallar | Ne YAPMA |
|---|---|---|---|---|---|
| 1 | Zaman içinde üretim (saatlik) | Çizgi/alan, gece şeridi arka planda | — | Gün sınırı `--chart-daybreak`; x ekseni yerel saat | Alanı sıfıra demirleyip «dağ» yapma (dar bant kuralı V1) |
| 2 | Tahmin vs gerçekleşen | İki seri: mavi kesikli tahmin + amber düz gerçekleşen, tek eksen | Ayna/fark grafiği | Lejant «gerçekleşen · her gece karşılaştırılır» dili; crosshair ikisini birden okur | İki ayrı grafik; üçüncü renk; dolgu savaşı |
| 3 | Tahmin belirsizliği (P10–P90) | Bant (dış P10–P90 soluk, iç P25–P75 koyu) + P50 çizgisi | Kantil yelpazesi | Bant jetonları `--chart-band*`; geçmiş/gelecek ton farkı; «şimdi» çizgisi | Bandı ayrı seri gibi lejantlama; P50'yi bantla aynı kalınlıkta boğma |
| 4 | Işınım ↔ üretim | Scatter (+6.0 jitter), yoğunlukta progressive | Binned heatmap | Nokta rengi TEK (mavi), boyut sabit; eğilim çizgisi gri | Gökkuşağı yoğunluk paleti; trend çizgisini amber yapma |
| 5 | Sıcaklık/meteo bindirmesi | Çift y-eksen çizgi; meteo serisi gri, İNCE | — | Sağ eksen yalnız meteo; axisPointer link | Meteo serisine veri renklerini verme |
| 6 | Saatlik üretim profili (tipik gün) | Saat×ay ısı haritası ya da kova ortalaması çizgi ailesi | Küçük katlar | visualMap tek-ton mavi rampa | Çok renkli rampa; 3B |
| 7 | Günlük/aylık üretim | Çubuk (günlük), çubuk+önceki dönem hayalet (aylık) | Takvim heatmap | Hayalet çubuk %30 opak gri | Yan yana 4+ çubuk grubu |
| 8 | Santral karşılaştırma | Küçük katlar + `echarts.connect()` senkron imleç | Normalize endeks çizgisi | Her kat AYNI y ölçeği ya da açıkça «ayrı ölçek» rozeti | Tek grafikte 6 renkli spagetti |
| 9 | Tahmin hatası (zaman içinde) | Çubuk ± (işaretli sapma), sıfır çizgisi vurgulu | Hata bandı | Pozitif/negatif AYNI mavi ton çifti, kırmızı/yeşil DEĞİL (finans çağrışımı yasak) | Kırmızı-yeşil ikiliği; mutlak hata ile işaretli hatayı karıştırma |
| 10 | MAPE/MAE/RMSE karnesi | Tablo + satır içi mini-sparkline | KPI satırı (değer+çapa+pencere) | Metrik tanımı tooltip'te değil künyede; «aşağı yuvarlanmış» dili | Her metriğe ayrı dev KPI kartı; gauge |
| 11 | Anomali tespiti | Ana seri + `markArea` vurgusu + markPoint etiketi | Anomali şerit-zaman çizelgesi | Vurgu `--uyari` ailesi (AMBER DEĞİL — amber=gerçekleşen) | Anomaliyi amberle işaretlemek; yanıp sönen animasyon |
| 12 | Performans oranı (PR) | Çizgi + hedef bandı (markLine) | Aylık çubuk | POA yoksa dürüst tire («poa_yok» emsali) | GHI ile uydurma PR; %100 çizgisini gizleme |
| 13 | Özgül verim (kWh/kWp) | Aylık çubuk + yıllık küm. çizgi ikincil eksende | — | Birim başlıkta bir kez | Donut/pasta |
| 14 | Kullanılabilirlik | Zaman şeridi (uptime bantları) + tek KPI | Aylık çubuk | Kesinti gri-koyu, kısıntı ayrı desen (tarama) | Yeşil/kırmızı trafik ışığı duvarı |
| 15 | İnverter/dizi performansı | Isı haritası (dizi×zaman, sapma rengi tek-ton) | Sıralı çubuk (en kötü N) | Satır sırası sapmaya göre, alfabetik değil | 20 inverter = 20 çizgi spagetti |
| 16 | Üretim ısı haritası (saat×gün) | ECharts heatmap, mavi rampa, gece satırları soluk | Takvim görünümü | Hücre kenarı 0; eksende hafta sonu imi | Kırmızı-yeşil diverging rampa |
| 17 | Ham veri gezgini (10⁵+ nokta) | **uPlot**: çok panel, `cursor.sync`, `bands` | — | LTTB ön-örnekleme sunucuda; zoom senkron | Bu ekranı ECharts'a zorlamak; SVG'ye dökmek |
| 18 | Yoğunlaştırılmış KPI şeridi | Satır içi değer + Δ çapa + mini sparkline, TEK yüzeyde | — | «panel kesiti» emsali: kart değil hücre | 5+ eş boyutlu KPI kartı dizisi (slop imzası) |

## Anotasyon stratejisi (ortak)

- Olay imleri (teslim penceresi, koşu anı, webhook): markLine + mono etiket, eğik DEĞİL.
- «şimdi» çizgisi: `--chart-now`, üstünde etiket; gelecek bölge tonu ayrışır (future jetonları).
- Açıklama balonu yerine kenarda sabit künye; grafik içinde cümle yazılmaz.

## Tooltip sözleşmesi (tek şablon)

Başlık: zaman (mono) · satırlar: renk imi + seri adı + değer (tabular, birimli) ·
sıra: tahmin → gerçekleşen → bağlam · boş değer «—». Varsayılan beyaz kutu asla.
