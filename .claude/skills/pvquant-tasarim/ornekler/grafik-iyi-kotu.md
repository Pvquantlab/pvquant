# Örnek: aynı grafiğin elle ↔ fabrikalı hâli (Mühür B gerçek diff'i, v2.396)

Kaynak: `web/src/features/sayfalar/Dogruluk.tsx` PIT histogramı. Görsel çıktı BİREBİR aynı;
fark, görünümün tek kaynağa inmesi ve bir daha elle yazılamaması (bekçi:
`web/test/grafik-tema.test.ts`).

## Önce (elle — her grafikte tekrar, jeton okumaları dağınık)

```tsx
const soluk = oku("--soluk"), mono = oku("--mono");
return {
  animation: false, grid: { left: 40, right: 12, top: 18, bottom: 30 },
  tooltip: { trigger: "axis", backgroundColor: oku("--kart"), borderColor: oku("--kenar"),
    borderWidth: 0.5, textStyle: { color: oku("--metin"), fontSize: 12 },
    valueFormatter: (v) => `%${sayiTr(Number(v) * 100, 0)}` },
  xAxis: { type: "category", data: kutular, axisLabel: { color: soluk,
    fontFamily: mono, fontSize: 9, interval: 1 }, axisTick: { show: false } },
  yAxis: { type: "value", min: 0, axisLabel: { color: soluk, fontFamily: mono,
    fontSize: 10, formatter: (v) => `%${Math.round(v * 100)}` },
    splitLine: { lineStyle: { color: oku("--izgara") } } },
  ...
};
```

## Sonra (fabrikalı — karar grafiğin, görünüm temanın)

```tsx
const r = renkler(oku);
return {
  ...TEMEL, grid: { left: 40, right: 12, top: 18, bottom: 30 },
  tooltip: tooltipEksen(r, { valueFormatter: (v) => `%${sayiTr(Number(v) * 100, 0)}` }),
  xAxis: eksenKategori(r, kutular, { axisLabel: eksenYazi(r, 9, { interval: 1 }) }),
  yAxis: eksenDeger(r, { min: 0,
    axisLabel: eksenYazi(r, 10, { formatter: (v) => `%${Math.round(v * 100)}` }) }),
  ...
};
```

## Dersler

- Fabrikalar BİLEREK minimal: axisLine/axisTick grafikten grafiğe farklıydı — pixel-parite
  için zorla standartlaştırılmadı, `ek` ile veriliyor (gerçek standartlaştırma ayrı karardır).
- `registerTheme` bilinçli YOK: tema = jeton okuyan fabrika katmanı + useTema().n yeniden
  kurulumu; kayıtlı tema çifte kaynak olurdu (bekçi `registerTheme(` çağrısını yasaklar).
- Kök `animation:false` varken bileşen içi (markLine) `animation:false` gereksizdi — kalktı.
- Kanıt kareleri: scratchpad mB/dogruluk-{ust,alt,koyu}.png (açık+koyu iki temada doğrulandı).
