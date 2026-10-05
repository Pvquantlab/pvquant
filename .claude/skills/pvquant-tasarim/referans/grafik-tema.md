# Grafik tema sözleşmesi (ECharts birincil + uPlot uzman)

Karar (05.10.2026 araştırması): **ECharts 6 korunur ve ustalaşılır**; yalnız 10⁵+ noktalı
ham veri gezgini ekranları için **uPlot** (lazy-load). visx/D3 yeniden yazımı, Recharts,
Plotly, AG Charts, Vega-Lite, Lightweight Charts REDDEDİLDİ (gerekçeler:
`~/Desktop/ges-tasarim-zekasi/03-grafik-kutuphaneleri.md`).

## Sözleşme (Mühür B'de `web/src/lib/grafikTema.ts` olarak gerçekleşir)

1. **Tek kayıtlı tema:** koyu + açık iki tema `registerTheme` ile, değerler CSS
   `--chart-*` jetonlarından okunarak üretilir; geçiş dispose'suz `setTheme`.
2. **Option fabrikaları:** `eksenX()/eksenY()/izgara()/tooltipSablonu()/disLegend()` —
   her grafik option'ı BUNLARDAN kurulur. Grafik kodunda elle `axisLabel`, `splitLine`,
   `tooltip.backgroundColor`, seri rengi yazmak YASAK (bekçi: grep testi, Mühür B).
3. **Kapatılan varsayılanlar:** `toolbox` tamamen; varsayılan `color` paleti (bizim
   mavi/amber dilimiz); `animation` kapalı ya da ilk çizim ≤200 ms; varsayılan beyaz
   tooltip yerine tek şablon (Plex Mono, tabular, künye düzeni, boş «—»); legend grafiğin
   DIŞINDA React bileşeni (`legend.show:false` + `dispatchAction` vurgusu).
4. **İmza custom series:** anomali imi, bant kenar çizgisi, gece/gün-doğumu şeridi — bir
   kez yazılır, her grafikte aynı dil (v6 yeniden kullanılabilir custom series).
5. **Boyut:** `echarts/core` + yalnız kullanılan chart/bileşen importu; tam paket yüklenmez.
6. **Sarmalayıcı sözleşmesi** (`web/src/lib/EChart.tsx`): init bir kez (dpr≥2);
   güncelleme `setOption(option, {notMerge:false, lazyUpdate:true})`; resize
   ResizeObserver (border-box ölçer!); unmount dispose; senkron için `group` prop +
   `echarts.connect(group)`; tema adı context'ten.

## uPlot kuralları

Yalnız ham yüksek-frekans gezgini: `new uPlot` mount'ta, veri `u.setData` (re-init yok),
`uPlot.sync('ges')` paylaşımlı imleç, `bands` ile P10–P90, `hooks.draw` ile gece şeridi
ve anomali bantları; eksen/grid/stroke aynı jeton setinden; SSR yok → lazy import.

## Bant tekniği (ECharts)

P10–P90: stack hilesi (görünmez taban + dolgu) ya da custom series; dış bant soluk
(`--chart-band-*`), iç P25–P75 koyu (`--chart-band2-*`), P50 çizgisi ayrı; geçmiş/gelecek
ton ayrımı future/past jetonlarıyla; «şimdi» çizgisi `--chart-now`.
