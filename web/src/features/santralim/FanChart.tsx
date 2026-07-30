/** P10-P90 fan chart — rehberin imza ogesi.
 *  ECharts'ta yerlesik range serisi yok; stacked-area teknigi kullanilir:
 *  gorunmez taban (P10) + FARK serileri. Ust serilerin data'si gercek
 *  degeri degil FARKI tasir — yoksa band iki katina cikar. */
import { useMemo } from "react";
import type { EChartsOption } from "echarts";
import { EChart } from "../../lib/EChart";
import { yazi, sayiTr } from "../../theme/tokens";
import { useTema } from "../../lib/useTema";
import type { TahminSerisi } from "../../api/types";

export function FanChart({ seri }: { seri: TahminSerisi }) {
  const { n, oku } = useTema();
  const option = useMemo<EChartsOption>(() => {
    const marka = oku("--marka"), markaAcik = oku("--marka-acik");
    const izgara = oku("--izgara"), soluk = oku("--soluk");
    const x = seri.saatlik.map((s) =>
      new Date(s.ts).toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" }));
    const p10 = seri.saatlik.map((s) => s.p10_kw ?? 0);
    const p50 = seri.saatlik.map((s) => s.p50_kw);
    const p90 = seri.saatlik.map((s) => s.p90_kw ?? 0);

    return {
      grid: { left: 48, right: 12, top: 12, bottom: 28 },
      animation: false,
      tooltip: {
        trigger: "axis",
        formatter: (p: unknown) => {
          const d = p as { dataIndex: number }[];
          const i = d[0].dataIndex;
          return `${x[i]}<br/>P90 ${sayiTr(p90[i])} kW<br/>` +
                 `<b>P50 ${sayiTr(p50[i])} kW</b><br/>P10 ${sayiTr(p10[i])} kW`;
        },
      },
      xAxis: {
        type: "category", data: x, boundaryGap: false,
        axisLine: { lineStyle: { color: izgara } },
        axisTick: { show: false },
        axisLabel: { color: soluk, fontFamily: yazi.mono, fontSize: 11, interval: Math.ceil(x.length / 8) },
      },
      yAxis: {
        type: "value", name: "kW", nameTextStyle: { color: soluk, fontSize: 11 },
        splitLine: { lineStyle: { color: izgara } },
        axisLabel: { color: soluk, fontFamily: yazi.mono, fontSize: 11,
                     formatter: (v: number) => sayiTr(v) },
      },
      series: [
        { name: "taban", type: "line", stack: "band", data: p10, symbol: "none",
          lineStyle: { opacity: 0 }, areaStyle: { opacity: 0 }, silent: true },
        { name: "P10-P50", type: "line", stack: "band", symbol: "none",
          data: p50.map((v, i) => v - p10[i]),
          lineStyle: { opacity: 0 },
          areaStyle: { color: markaAcik, opacity: 0.45 }, silent: true },
        { name: "P50-P90", type: "line", stack: "band", symbol: "none",
          data: p90.map((v, i) => v - p50[i]),
          lineStyle: { opacity: 0 },
          areaStyle: { color: markaAcik, opacity: 0.45 }, silent: true },
        { name: "Tahmin P50", type: "line", data: p50, symbol: "none", smooth: 0.3,
          lineStyle: { color: marka, width: 2 }, z: 3 },
      ],
    };
      // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seri, n]);

  return <EChart option={option} height={280}
    ariaLabel={`${seri.ufuk_saat} saatlik üretim tahmini, P10-P90 belirsizlik bandıyla`} />;
}
