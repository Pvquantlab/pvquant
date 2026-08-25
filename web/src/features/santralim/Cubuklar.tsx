/** Deger etiketli cubuk grafik — 7 gunluk gorunum ve aylik uretim icin.
 *  v2.196 (D karari): en dusuk donem NOTR koyulasir — amber artik yalniz
 *  "gerceklesen" grafik murekkebi (anayasa); eski K7 amber'i kaldirildi. */
import { useMemo } from "react";
import type { EChartsOption } from "echarts";
import { EChart } from "../../lib/EChart";
import { useTema } from "../../lib/useTema";
import { sayiTr } from "../sayfalar/parcalar";

export function Cubuklar({ etiketler, degerler, birim, vurguIdx, yukseklik = 260, ondalik = 1, kapsamPct, beklenti }:
  { etiketler: string[]; degerler: number[]; birim: string;
    vurguIdx?: number; yukseklik?: number; ondalik?: number;
    kapsamPct?: number[];
    /** v2.203 (D bullet imleci): donem basina beklenti-P50; null = imlec yok */
    beklenti?: (number | null)[] }) {
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
          let satir = `${etiketler[i]}: ${sayiTr(Number(a[0]?.value), ondalik)} ${birim}`;
          const b = beklenti?.[i];
          if (b !== null && b !== undefined)
            satir += `<br/>beklenti · P50: ${sayiTr(b, ondalik)} ${birim}`;
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
               : i === enDusuk ? (oku("--ch-dusuk") || "#A8A296")
               : i === vurguIdx ? oku("--cubuk-vurgu")
               : (oku("--ch-cubuk") || "#6FA98A"),
          borderType: !tam(i) ? "dashed" as const : "solid" as const,
          borderColor: !tam(i) ? `rgba(${nr},.5)` : "transparent",
          borderWidth: !tam(i) ? 1 : 0 } })),
        label: { show: true, position: "top", color: oku("--ikincil"),
                 fontFamily: mono, fontSize: 11,
                 formatter: (p: unknown) =>
                   sayiTr(Number((p as { value: number }).value), ondalik) },
      },
      // v2.203: beklenti-P50 imleci — cubugun ustune binen yatay cizgi
      // (D bullet dili); yalniz degeri olan donemlerde cizilir, uydurma yok.
      ...(beklenti && beklenti.some((b) => b !== null) ? [{
        type: "scatter" as const, silent: true, z: 5,
        symbol: "rect", symbolSize: [40, 2.4],
        itemStyle: { color: oku("--metin") },
        tooltip: { show: false },
        data: beklenti.map((b, i) => (b === null ? null : [i, b])),
      }] : []),
      ],
    } as EChartsOption;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [etiketler, degerler, vurguIdx, n]);

  return <EChart option={option} height={yukseklik}
    ariaLabel={`${etiketler.length} sütunlu üretim grafiği, ${birim}`} />;
}
