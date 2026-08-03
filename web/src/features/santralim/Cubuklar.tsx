/** Deger etiketli cubuk grafik — 7 gunluk gorunum ve aylik uretim icin.
 *  En dusuk gun amber, secili/son gun koyu (Streamlit'teki K7 kurali). */
import { useMemo } from "react";
import type { EChartsOption } from "echarts";
import { EChart } from "../../lib/EChart";
import { useTema } from "../../lib/useTema";
import { sayiTr } from "../sayfalar/parcalar";

export function Cubuklar({ etiketler, degerler, birim, vurguIdx, yukseklik = 260, ondalik = 1 }:
  { etiketler: string[]; degerler: number[]; birim: string;
    vurguIdx?: number; yukseklik?: number; ondalik?: number }) {
  const { n, oku } = useTema();
  const option = useMemo<EChartsOption>(() => {
    const mr = oku("--marka-r") || "14,124,90", ar = oku("--amber-r") || "232,148,10";
    const nr = oku("--notr-r") || "100,116,139";
    const grad = (r: string, ust: number, alt: number) => ({ type: "linear",
      x: 0, y: 0, x2: 0, y2: 1, colorStops: [
        { offset: 0, color: `rgba(${r},${ust})` },
        { offset: 1, color: `rgba(${r},${alt})` }] });
    const izgara = oku("--izgara"), soluk = oku("--soluk"), kenar = oku("--kenar");
    const mono = oku("--mono");  // v2.92: sabit ad degil token
    const enDusuk = degerler.indexOf(Math.min(...degerler));
    return {
      grid: { left: 46, right: 10, top: 26, bottom: 26 }, animation: false,
      tooltip: { trigger: "axis", backgroundColor: oku("--kart"), borderColor: kenar,
        borderWidth: 0.5, textStyle: { color: oku("--metin"), fontSize: 12 },
        valueFormatter: (v: unknown) => `${sayiTr(Number(v), ondalik)} ${birim}` },
      xAxis: { type: "category", data: etiketler, axisTick: { show: false },
        axisLine: { lineStyle: { color: kenar } },
        axisLabel: { color: soluk, fontFamily: mono, fontSize: 11 } },
      yAxis: { type: "value", splitLine: { lineStyle: { color: izgara } },
        axisLine: { show: false },
        axisLabel: { color: soluk, fontFamily: mono, fontSize: 11,
                     formatter: (v: number) => sayiTr(v) } },
      series: [{
        type: "bar", barMaxWidth: 34,
        data: degerler.map((v, i) => ({ value: v, itemStyle: {
          borderRadius: [2, 2, 0, 0],
          color: i === enDusuk ? grad(ar, .95, .70)
               : i === vurguIdx ? grad(mr, 1, .74)
               : grad(nr, .42, .18) } })),
        label: { show: true, position: "top", color: oku("--ikincil"),
                 fontFamily: mono, fontSize: 11,
                 formatter: (p: unknown) =>
                   sayiTr(Number((p as { value: number }).value), ondalik) },
      }],
    } as EChartsOption;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [etiketler, degerler, vurguIdx, n]);

  return <EChart option={option} height={yukseklik}
    ariaLabel={`${etiketler.length} sütunlu üretim grafiği, ${birim}`} />;
}
