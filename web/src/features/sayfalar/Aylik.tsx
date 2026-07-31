import { useEffect, useMemo, useState } from "react";
import type { EChartsOption } from "echarts";
import { api } from "../../api/client";
import type { AylikBeklenti, SantralOzeti } from "../../api/types";
import { EChart } from "../../lib/EChart";
import { useTema } from "../../lib/useTema";
import { Cubuklar } from "../santralim/Cubuklar";
import { Kart, Kpi, Sayfa, sayiTr } from "./parcalar";

const AYLAR = ["Oca", "Şub", "Mar", "Nis", "May", "Haz",
               "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"];

/** v2.78-C — KUTU-2 sayfasi: uc kart (bu ayin P10/50/90) + 20 yil
 *  serpilisi + P10-P90 bandi + gerceklesen uretim cubugu (ozet'ten).
 *  NWP aya UZATILMAZ — beklenti iklimden gelir (sartname). */
export function Aylik({ plantId }: { plantId: string }) {
  const [b, setB] = useState<AylikBeklenti | null>(null);
  const [o, setO] = useState<SantralOzeti | null>(null);
  const [birikiyor, setBirikiyor] = useState(false);
  const { n, oku } = useTema();

  useEffect(() => {
    api.aylik(plantId).then(setB).catch(() => setBirikiyor(true));
    api.ozet(plantId).then(setO).catch(() => {});
  }, [plantId]);

  const option = useMemo<EChartsOption>(() => {
    const marka = oku("--marka"), acik = oku("--marka-acik");
    const izgara = oku("--izgara"), soluk = oku("--soluk");
    const kenar = oku("--kenar"), mono = "JetBrains Mono";
    const bek = b?.beklenti ?? [];
    const p10 = bek.map((r) => r.p10);
    const bant = bek.map((r) => (r.p90 !== null && r.p10 !== null)
      ? +(r.p90 - r.p10).toFixed(1) : null);
    return {
      grid: { left: 52, right: 12, top: 28, bottom: 28 }, animation: false,
      tooltip: { trigger: "axis", backgroundColor: oku("--kart"),
        borderColor: kenar, borderWidth: 0.5,
        textStyle: { color: oku("--metin"), fontSize: 12 } },
      xAxis: { type: "category", data: AYLAR, axisTick: { show: false },
        axisLine: { lineStyle: { color: kenar } },
        axisLabel: { color: soluk, fontFamily: mono, fontSize: 11 } },
      yAxis: { type: "value", name: "kWh/m²",
        nameTextStyle: { color: soluk, fontFamily: mono, fontSize: 10 },
        splitLine: { lineStyle: { color: izgara } }, axisLine: { show: false },
        axisLabel: { color: soluk, fontFamily: mono, fontSize: 11 } },
      series: [
        { name: "20 yıl", type: "scatter", symbolSize: 5, z: 1,
          itemStyle: { color: soluk, opacity: 0.45 },
          data: (b?.yillik ?? []).map((r) => [r.ay - 1, r.ghi_kwh_m2]) },
        { name: "P10", type: "line", stack: "bant", symbol: "none",
          lineStyle: { opacity: 0 }, data: p10, tooltip: { show: false } },
        { name: "P10–P90", type: "line", stack: "bant", symbol: "none",
          lineStyle: { opacity: 0 }, areaStyle: { color: acik, opacity: 0.7 },
          z: 2, data: bant },
        { name: "P50", type: "line", symbol: "circle", symbolSize: 5, z: 3,
          lineStyle: { color: marka, width: 2 },
          itemStyle: { color: marka },
          data: bek.map((r) => r.p50) },
      ],
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [b, n]);

  if (birikiyor) return (
    <Sayfa baslik="Aylık beklenti" alt="İklimden gelen ay bazlı üretim zarfı.">
      <Kart baslik="Beklenti birikiyor">
        <p style={{ fontSize: 13, color: "var(--ikincil)", margin: 0 }}>
          İklim beklentisi henüz hesaplanmadı — worker her ayın 1'inde
          20 yıllık arşivden tazeler. İlk hesap sonrası bu sayfa dolar.
        </p>
      </Kart>
    </Sayfa>);
  if (!b) return <div style={{ color: "var(--soluk)" }}>Yükleniyor…</div>;

  const buAy = new Date().getMonth() + 1;
  const k = b.beklenti.find((r) => r.ay === buAy);
  const hesap = new Date(b.hesap_zamani).toLocaleDateString("tr-TR",
    { day: "numeric", month: "short", year: "numeric" });

  return (
    <Sayfa baslik="Aylık beklenti"
      alt="İklimden gelen ay bazlı üretim zarfı — kısa ufuk tahmini değildir; NWP aya uzatılmaz."
      sag={<span className="cip">Kaynak: 20 yıl arşiv · hesap {hesap}</span>}>
      <div className="kpi-satir">
        <Kpi etiket={`${AYLAR[buAy - 1]} · P10`}
             deger={k?.p10 !== null && k ? sayiTr(k.p10) : "—"}
             birim="kWh/m²" alt="kötümser zarf (10/100 yıl altında)" />
        <Kpi etiket={`${AYLAR[buAy - 1]} · P50`}
             deger={k?.p50 !== null && k ? sayiTr(k.p50) : "—"}
             birim="kWh/m²" alt={`medyan · ${k?.yil_sayisi ?? "—"} yıl`} />
        <Kpi etiket={`${AYLAR[buAy - 1]} · P90`}
             deger={k?.p90 !== null && k ? sayiTr(k.p90) : "—"}
             birim="kWh/m²" alt="iyimser zarf (10/100 yıl üstünde)" />
      </div>
      <Kart baslik="Ay bazında GHI — 20 yıl serpilisi ve P10–P90 zarfı">
        <EChart option={option} height={320}
          ariaLabel="12 ay için 20 yıllık GHI serpilisi, P10-P90 bandı ve P50 çizgisi" />
      </Kart>
      {o && o.aylik.length > 0 && (
        <Kart baslik="Gerçekleşen üretim — son 12 ay (SCADA)">
          <Cubuklar etiketler={o.aylik.map((a) => a.ay)}
                    degerler={o.aylik.map((a) => a.mwh)}
                    birim="MWh" vurguIdx={o.aylik.length - 1} yukseklik={220} />
        </Kart>
      )}
    </Sayfa>
  );
}
