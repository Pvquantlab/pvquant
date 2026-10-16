// 16.10 hız turu 4 — ECharts yalnız kullanılan parçalarla (src/lib/echarts.ts). Tam paketten değer içe aktarması
// geri gelirse panel parçası 1,1 MB'a döner; listede olmayan seri/bileşen ise üretimde sessizce çizilmez.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const kok = fileURLToPath(new URL("../src/", import.meta.url));
const dosyalar: string[] = [];
const gez = (d: string) => { for (const a of readdirSync(d)) { const y = join(d, a); if (statSync(y).isDirectory()) gez(y); else if (/\.tsx?$/.test(a)) dosyalar.push(y); } };
gez(kok);

test("tam 'echarts' paketinden değer içe/dışa aktarması yok (yalnız import type)", () => {
  for (const y of dosyalar) {
    const metin = readFileSync(y, "utf8");
    // ifade önceki bir `from "…"` yan tümcesini aşamaz (noktalı virgülsüz dosyada type-only satır yanlış alarm vermesin)
    const m = /^\s*(import|export)\s+(?!type\b)(?:(?!\bfrom\s*["'])[^;])*\bfrom\s*["']echarts["']/m.exec(metin);
    assert.equal(m, null, `${y}: ${m?.[0]}`);
    const d = /\bimport\s*\(\s*["']echarts["']\s*\)|^\s*import\s*["']echarts["']/m.exec(metin);   // dinamik ya da yan etki içe aktarması
    assert.equal(d, null, `${y}: ${d?.[0]}`);
  }
});

test("kaynakta kullanılan seri türleri ve bileşenler kayıtlı", () => {
  const kayit = readFileSync(join(kok, "lib/echarts.ts"), "utf8");
  const metin = dosyalar.filter((y) => !y.endsWith("lib/echarts.ts")).map((y) => readFileSync(y, "utf8")).join("\n");
  const SERI: Record<string, string> = { line: "LineChart", bar: "BarChart", scatter: "ScatterChart", heatmap: "HeatmapChart", custom: "CustomChart", pie: "PieChart", candlestick: "CandlestickChart", boxplot: "BoxplotChart", radar: "RadarChart", gauge: "GaugeChart", effectScatter: "EffectScatterChart", lines: "LinesChart", graph: "GraphChart", tree: "TreeChart", treemap: "TreemapChart", sunburst: "SunburstChart", sankey: "SankeyChart", funnel: "FunnelChart", parallel: "ParallelChart", themeRiver: "ThemeRiverChart", pictorialBar: "PictorialBarChart", map: "MapChart" };
  for (const [tur, ad] of Object.entries(SERI)) {
    if (new RegExp(`type: ?["']${tur}["']`).test(metin)) assert.ok(kayit.includes(ad), `${tur} serisi kullanılıyor ama ${ad} kayıtlı değil`);
  }
  const BILESEN: Record<string, string> = { tooltip: "TooltipComponent", legend: "LegendComponent", dataZoom: "DataZoomComponent", visualMap: "VisualMapComponent", markLine: "MarkLineComponent", markArea: "MarkAreaComponent", markPoint: "MarkPointComponent", graphic: "GraphicComponent", axisPointer: "AxisPointerComponent", title: "TitleComponent", toolbox: "ToolboxComponent", dataset: "DatasetComponent", polar: "PolarComponent", calendar: "CalendarComponent", brush: "BrushComponent", aria: "AriaComponent", timeline: "TimelineComponent", geo: "GeoComponent", singleAxis: "SingleAxisComponent", containLabel: "LegacyGridContainLabel", universalTransition: "UniversalTransition" };
  for (const [anahtar, ad] of Object.entries(BILESEN)) {
    if (new RegExp(`\\b${anahtar}\\s*:`).test(metin)) assert.ok(kayit.includes(ad), `${anahtar} kullanılıyor ama ${ad} kayıtlı değil`);
  }
  if (/renderer:\s*["']svg["']/.test(metin)) assert.ok(kayit.includes("SVGRenderer"), "svg çizici kullanılıyor ama SVGRenderer kayıtlı değil");
});
