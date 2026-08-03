/** P10-P90 fan chart. ECharts'ta yerlesik range serisi yok; stacked-area
 *  teknigi: gorunmez taban (P10) + FARK serileri. */
import { useMemo } from "react";
import type { EChartsOption } from "echarts";
import { EChart } from "../../lib/EChart";
import { useTema } from "../../lib/useTema";
import { sayiTr } from "../sayfalar/parcalar";
import type { TahminSerisi } from "../../api/types";

export function FanChart({ seri, yukseklik = 300 }:
  { seri: TahminSerisi; yukseklik?: number }) {
  const { n, oku } = useTema();
  const option = useMemo<EChartsOption>(() => {
    const marka = oku("--marka"), amber = oku("--amber");
    const mr = oku("--marka-r") || "11,122,91";
    const bant = { type: "linear", x: 0, y: 0, x2: 0, y2: 1, colorStops: [
      { offset: 0, color: `rgba(${mr},.26)` },
      { offset: 1, color: `rgba(${mr},.04)` }] };
    const izgara = oku("--izgara"), soluk = oku("--soluk"), kenar = oku("--kenar");
    const mono = oku("--mono");  // v2.92: sabit ad degil token
    const cokGun = seri.ufuk_saat > 48;
    // v2.93: bant verisi yoksa bant HIC cizilmez. ?? 0 gecmisi ayna
    // yaratiyordu: null p90 -> ust = -p50; ECharts samesign yigini
    // negatifi sifirdan ASAGI serer (gunes gece -3.500 kW "uretir"di).
    const varBant = seri.saatlik.some(
      (s) => s.p10_kw !== null && s.p90_kw !== null);
    const x = seri.saatlik.map((s) => {
      const d = new Date(s.ts);
      return cokGun ? d.toLocaleDateString("tr-TR", { day: "numeric", month: "short" })
                    : d.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" });
    });
    const p10 = seri.saatlik.map((s) => s.p10_kw ?? 0);
    const p50 = seri.saatlik.map((s) => s.p50_kw);
    const p90 = seri.saatlik.map((s) => s.p90_kw ?? 0);
    const gercek = seri.saatlik.map((s) => s.gercek_kw);
    const varGercek = gercek.some((v) => v !== null);

    const isaretler: Record<string, unknown>[] = [];
    if (seri.ac_tavani_kw)
      isaretler.push({ yAxis: seri.ac_tavani_kw, label: {
        formatter: `AC tavanı ${sayiTr(seri.ac_tavani_kw)} kW`, position: "insideStartTop",
        color: soluk, fontFamily: mono, fontSize: 11 } });
    if (seri.simdi_idx !== null)
      isaretler.push({ xAxis: seri.simdi_idx, label: {
        formatter: "şimdi", position: "insideEndTop",
        color: soluk, fontFamily: mono, fontSize: 11 } });

    return {
      grid: { left: 52, right: 16, top: 18, bottom: 30 }, animation: false,
      tooltip: { trigger: "axis", backgroundColor: oku("--kart"),
        borderColor: kenar, borderWidth: 0.5, textStyle: { color: oku("--metin"), fontSize: 12 },
        formatter: (p: unknown) => {
          const i = (p as { dataIndex: number }[])[0].dataIndex;
          return varBant
            ? `<b>${x[i]}</b><br/>P90 &nbsp;${sayiTr(p90[i])} kW<br/>` +
              `<b>P50 &nbsp;${sayiTr(p50[i])} kW</b><br/>P10 &nbsp;${sayiTr(p10[i])} kW`
            : `<b>${x[i]}</b><br/><b>P50 &nbsp;${sayiTr(p50[i])} kW</b>`;
        } },
      xAxis: { type: "category", data: x, boundaryGap: false,
        axisLine: { lineStyle: { color: kenar } }, axisTick: { show: false },
        axisLabel: { color: soluk, fontFamily: mono, fontSize: 11,
                     interval: Math.max(0, Math.ceil(x.length / 9) - 1) } },
      yAxis: { type: "value", name: "kW", nameGap: 14,
        nameTextStyle: { color: soluk, fontSize: 11, align: "right" },
        splitLine: { lineStyle: { color: izgara } }, axisLine: { show: false },
        axisLabel: { color: soluk, fontFamily: mono, fontSize: 11,
                     formatter: (v: number) => sayiTr(v) } },
      series: [
        ...(varBant ? [
          { name: "taban", type: "line" as const, stack: "band", data: p10,
            symbol: "none" as const, lineStyle: { opacity: 0 },
            areaStyle: { opacity: 0 }, silent: true },
          { name: "alt", type: "line" as const, stack: "band",
            symbol: "none" as const, silent: true,
            data: p50.map((v, i) => v - p10[i]), lineStyle: { opacity: 0 },
            areaStyle: { color: bant } },
          { name: "ust", type: "line" as const, stack: "band",
            symbol: "none" as const, silent: true,
            data: p90.map((v, i) => v - p50[i]), lineStyle: { opacity: 0 },
            areaStyle: { color: bant } },
        ] : []),
        { name: "P50", type: "line", data: p50, symbol: "none", smooth: 0.25, z: 3,
          lineStyle: { color: marka, width: 2.4 },
          markLine: isaretler.length ? { silent: true, symbol: "none",
            lineStyle: { color: soluk, type: "dashed", width: 1 },
            data: isaretler } : undefined },
        ...(varGercek ? [{ name: "Gerçekleşen", type: "line" as const, data: gercek,
          symbol: "none" as const, smooth: 0.25, z: 4, connectNulls: false,
          lineStyle: { color: amber, width: 2.4 } }] : []),
      ],
    } as EChartsOption;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seri, n]);

  return <EChart option={option} height={yukseklik}
    ariaLabel={`${seri.ufuk_saat} saatlik üretim tahmini, P10-P90 bandıyla`} />;
}
