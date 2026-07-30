import { useMemo } from "react";
import type { EChartsOption } from "echarts";
import { EChart } from "../../lib/EChart";
import { useTema } from "../../lib/useTema";
import { yazi } from "../../theme/tokens";
import { Kpi, Bolum } from "./parcalar";

const GUN = ["15 Nis", "16 Nis", "17 Nis", "18 Nis"];
const BIZ0 = [83, 39, null, null];
const BIZ1 = [null, 38, 47, 53];
const NAIF = [99, 46, 56, 63];

export function Dogruluk() {
  const { n, oku } = useTema();
  const option = useMemo<EChartsOption>(() => {
    const marka = oku("--marka"), acik = oku("--marka-acik");
    const izgara = oku("--izgara"), soluk = oku("--soluk"), gri = oku("--kenar");
    return {
      grid: { left: 44, right: 10, top: 16, bottom: 28 }, animation: false,
      tooltip: { trigger: "axis", valueFormatter: (v: unknown) => `%${v}` },
      xAxis: { type: "category", data: GUN, axisTick: { show: false },
        axisLine: { lineStyle: { color: izgara } },
        axisLabel: { color: soluk, fontFamily: yazi.mono, fontSize: 11 } },
      yAxis: { type: "value", splitLine: { lineStyle: { color: izgara } },
        axisLabel: { color: soluk, fontFamily: yazi.mono, fontSize: 11,
                     formatter: (v: number) => `%${v}` } },
      series: [
        { name: "Naif referans", type: "bar", data: NAIF, itemStyle: { color: gri, borderRadius: [4, 4, 0, 0] }, barMaxWidth: 22 },
        { name: "PVQuant 0-24s", type: "bar", data: BIZ0, itemStyle: { color: marka, borderRadius: [4, 4, 0, 0] }, barMaxWidth: 22 },
        { name: "PVQuant 24-72s", type: "bar", data: BIZ1, itemStyle: { color: acik, borderRadius: [4, 4, 0, 0] }, barMaxWidth: 22 },
      ],
    };
  }, [n, oku]);

  return (
    <>
      <h1 style={{ fontSize: 21, fontWeight: 600, margin: "0 0 4px", letterSpacing: "-0.02em" }}>Doğruluk karnesi</h1>
      <p style={{ fontSize: 13, color: "var(--ikincil)", margin: "0 0 18px" }}>
        Tahminlerimiz gerçekleşenle her gece karşılaştırılır — kanıt burada birikir.
      </p>
      <div style={{ display: "grid", gap: 12, marginBottom: 8,
                    gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))" }}>
        <Kpi etiket="WMAPE · 0-24s · 2 gün ort." deger="%60,6" />
        <Kpi etiket="Naife göre üstünlük" deger="%16" />
        <Kpi etiket="Karne günü" deger="4" birim="gün" />
      </div>
      <p style={{ fontSize: 12, color: "var(--soluk)", margin: "0 0 18px" }}>
        Kapsanan dönem: 15 – 18 Nisan 2026
      </p>
      <Bolum baslik="Günlük WMAPE — naif referansla karşılaştırma">
        <div style={{ display: "flex", gap: 16, fontSize: 12, color: "var(--ikincil)", marginBottom: 6 }}>
          <span>■ Naif referans</span>
          <span style={{ color: "var(--marka)" }}>■ PVQuant 0-24s</span>
          <span style={{ color: "var(--marka-acik)" }}>■ PVQuant 24-72s</span>
        </div>
        <EChart option={option} height={280} ariaLabel="Günlük WMAPE sütunları, naif referansla karşılaştırmalı" />
      </Bolum>
    </>
  );
}
