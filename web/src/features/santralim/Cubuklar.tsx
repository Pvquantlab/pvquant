/** Deger etiketli cubuk grafik — 7 gunluk gorunum ve aylik uretim icin.
 *  En dusuk gun amber, secili/son gun koyu (Streamlit'teki K7 kurali). */
import { useMemo } from "react";
import type { EChartsOption } from "echarts";
import { EChart } from "../../lib/EChart";
import { useTema } from "../../lib/useTema";
import { sayiTr } from "../sayfalar/parcalar";

export function Cubuklar({ etiketler, degerler, birim, vurguIdx, yukseklik = 260, ondalik = 1, kapsamPct }:
  { etiketler: string[]; degerler: number[]; birim: string;
    vurguIdx?: number; yukseklik?: number; ondalik?: number;
    kapsamPct?: number[] }) {
  const { n, oku } = useTema();
  const option = useMemo<EChartsOption>(() => {
    // v2.148: mr/ar/grad kalıntısı söküldü — üretim derlemesi (tsc -b)
    // ilk kez koşunca döküldü; dev-Vite tip denetimi yapmıyordu. nr kullanımda.
    const nr = oku("--notr-r") || "100,116,139";
    const izgara = oku("--izgara"), soluk = oku("--soluk"), kenar = oku("--kenar");
    const mono = oku("--mono");  // v2.92: sabit ad degil token
    // v2.118: kapsam <%50 aylar "eksik veri" sayilir — en-dusuk aramasina
    // girmez (Solargis: olculmemis donem, kotu donemle karistirilmaz)
    const tam = (i: number) => !kapsamPct || (kapsamPct[i] ?? 100) >= 50;
    const adaylar = degerler.map((v, i) => tam(i) ? v : Infinity);
    const enDusuk = adaylar.indexOf(Math.min(...adaylar));
    return {
      grid: { left: 46, right: 10, top: 26, bottom: 26 }, animation: false,
      tooltip: { trigger: "axis", backgroundColor: oku("--kart"), borderColor: kenar,
        borderWidth: 0.5, textStyle: { color: oku("--metin"), fontSize: 12 },
        formatter: (ps: unknown) => {
          const a = ps as { dataIndex: number; value: number }[];
          const i = a[0]?.dataIndex ?? 0;
          const satir = `${etiketler[i]}: ${sayiTr(Number(a[0]?.value), ondalik)} ${birim}`;
          return tam(i) ? satir
            : `${satir}<br/><span style="opacity:.75">kapsam %${sayiTr(kapsamPct![i], 1)} — eksik veri</span>`;
        } },
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
          color: !tam(i) ? `rgba(${nr},.18)`
               : i === enDusuk ? "#E8940A"
               : i === vurguIdx ? oku("--cubuk-vurgu")
               : "#4E9B72",
          borderType: !tam(i) ? "dashed" as const : "solid" as const,
          borderColor: !tam(i) ? `rgba(${nr},.5)` : "transparent",
          borderWidth: !tam(i) ? 1 : 0 } })),
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
