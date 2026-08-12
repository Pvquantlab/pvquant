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

  // Solargis Tablo 4.3/5.2 formati: sayi + isi-skalasi arka plan (v2.115)
  const matris = useMemo(() => {
    const yl = b?.yillik ?? [];
    const yillar = [...new Set(yl.map((r) => r.yil))].sort();
    const huc = new Map<string, number>();
    let lo = Infinity, hi = -Infinity;
    yl.forEach((r) => { if (r.ghi_kwh_m2 !== null) {
      huc.set(`${r.yil}-${r.ay}`, r.ghi_kwh_m2);
      lo = Math.min(lo, r.ghi_kwh_m2); hi = Math.max(hi, r.ghi_kwh_m2);
    } });
    const satirlar = yillar.map((y) => {
      const aylar = Array.from({ length: 12 }, (_, i) => huc.get(`${y}-${i + 1}`) ?? null);
      const tam = aylar.every((v) => v !== null);
      return { ad: String(y), aylar,
               yil: tam ? aylar.reduce((a, c) => a! + c!, 0) : null };
    });
    const ort = Array.from({ length: 12 }, (_, i) => {
      const v = satirlar.map((r) => r.aylar[i]).filter((x): x is number => x !== null);
      return v.length ? v.reduce((a, c) => a + c, 0) / v.length : null;
    });
    const tamYillar = satirlar.filter((r) => r.yil !== null).map((r) => r.yil as number);
    return { satirlar, ort,
             ortYil: tamYillar.length ? tamYillar.reduce((a, c) => a + c, 0) / tamYillar.length : null,
             lo, hi,
             yilLo: tamYillar.length ? Math.min(...tamYillar) : 0,
             yilHi: tamYillar.length ? Math.max(...tamYillar) : 1 };
  }, [b]);

  // Solargis paleti: acik yesil -> sari -> turuncu -> kizil (deger arka plani)
  const solargisTon = (t: number) => {
    const durak: [number, number, number][] = [
      [228, 239, 211], [247, 233, 160], [245, 193, 92], [232, 130, 60], [200, 64, 30]];
    const k = Math.min(0.999, Math.max(0, t)) * (durak.length - 1);
    const i = Math.floor(k), f = k - i;
    return "rgb(" + durak[i].map((a, c) =>
      Math.round(a + (durak[i + 1][c] - a) * f)).join(",") + ")";
  };

  const option = useMemo<EChartsOption>(() => {
    const izgara = oku("--izgara"), soluk = oku("--soluk");
    const kenar = oku("--kenar"), mono = oku("--mono");
    const bek = b?.beklenti ?? [];
    // Solargis Fig 4.1 dili: aylik toplam duz-renk sutun; ustune P10-P90
    // hata araligi (bankable "deger + belirsizlik" gelenegi).
    const marka = oku("--marka");
    return {
      grid: { left: 52, right: 12, top: 28, bottom: 28 }, animation: false,
      tooltip: { trigger: "axis", backgroundColor: oku("--kart"),
        borderColor: kenar, borderWidth: 0.5,
        textStyle: { color: oku("--metin"), fontSize: 12 },
        formatter: (ps: unknown) => {
          const arr = ps as { dataIndex: number }[];
          const r = bek[arr[0]?.dataIndex];
          if (!r) return "";
          const f = (v: number | null) => v === null ? "—" : sayiTr(v);
          return `${AYLAR[r.ay - 1]}<br/>P50: ${f(r.p50)} kWh/m²<br/>` +
                 `P10–P90: ${f(r.p10)} – ${f(r.p90)}`;
        } },
      xAxis: { type: "category", data: AYLAR, axisTick: { show: false },
        axisLine: { lineStyle: { color: kenar } },
        axisLabel: { color: soluk, fontFamily: mono, fontSize: 11 } },
      yAxis: { type: "value", name: "kWh/m²",
        nameTextStyle: { color: soluk, fontFamily: mono, fontSize: 10 },
        splitLine: { lineStyle: { color: izgara } }, axisLine: { show: false },
        axisLabel: { color: soluk, fontFamily: mono, fontSize: 11 } },
      series: [
        { name: "P50", type: "bar", barMaxWidth: 34, z: 1,
          itemStyle: { borderRadius: [2, 2, 0, 0], color: "#4E9B72" },
          label: { show: true, position: "top", distance: 16,
            color: oku("--metin"), fontFamily: mono, fontSize: 10.5,
            formatter: (pr: { value: number }) => `${Math.round(pr.value)}` },
          data: bek.map((r) => r.p50) },
        { name: "P10–P90", type: "custom", z: 2,
          renderItem: (_params: unknown, api0: unknown) => {
            const api = api0 as {
              value: (i: number) => number;
              coord: (v: [number, number]) => [number, number];
              style: (o: object) => object };
            const xi = api.value(0), lo = api.value(1), hi = api.value(2);
            if (!isFinite(lo) || !isFinite(hi)) return undefined as never;
            const [x, yLo] = api.coord([xi, lo]);
            const yHi = api.coord([xi, hi])[1];
            const w = 7;
            const cizgi = { stroke: "#26303A", lineWidth: 1.4 };
            return { type: "group", children: [
              { type: "line", shape: { x1: x, y1: yLo, x2: x, y2: yHi }, style: cizgi },
              { type: "line", shape: { x1: x - w, y1: yLo, x2: x + w, y2: yLo }, style: cizgi },
              { type: "line", shape: { x1: x - w, y1: yHi, x2: x + w, y2: yHi }, style: cizgi },
            ] } as never;
          },
          data: bek.map((r, i) => [i, r.p10 ?? NaN, r.p90 ?? NaN]),
          tooltip: { show: false } },
      ],
    };
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
      <Kart baslik="Aylık GHI — uzun dönem P50 ve P10–P90 aralığı">
        <EChart option={option} height={320}
          ariaLabel="12 ay için 20 yıllık GHI serpilisi, P10-P90 bandı ve P50 çizgisi" />
      </Kart>
      <Kart baslik="Yıl × ay GHI matrisi"
        sag={<span className="cip">kWh/m² · renk: değer skalası</span>}>
        <div style={{ overflowX: "auto" }}>
          <table style={{ borderCollapse: "collapse", width: "100%",
                          fontFamily: "var(--mono)", fontSize: 11.5 }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left", padding: "4px 6px",
                             color: "var(--soluk)", fontWeight: 500 }}></th>
                {AYLAR.map((a) => (
                  <th key={a} style={{ padding: "4px 2px", color: "var(--soluk)",
                                       fontWeight: 500 }}>{a}</th>))}
                <th style={{ padding: "4px 6px", color: "var(--soluk)",
                             fontWeight: 600 }}>Yıl</th>
              </tr>
            </thead>
            <tbody>
              {matris.satirlar.map((r) => (
                <tr key={r.ad}>
                  <td style={{ padding: "2.5px 6px", color: "var(--soluk)" }}>{r.ad}</td>
                  {r.aylar.map((v, i) => (
                    <td key={i} style={{ padding: "2.5px 2px", textAlign: "center",
                      border: "1px solid var(--kart)", color: "#26303A",
                      background: v === null ? "transparent"
                        : solargisTon((v - matris.lo) / (matris.hi - matris.lo)) }}>
                      {v === null ? <span style={{ color: "var(--soluk)" }}>–</span>
                        : Math.round(v)}
                    </td>))}
                  <td style={{ padding: "2.5px 6px", textAlign: "right", fontWeight: 600,
                    border: "1px solid var(--kart)", color: "#26303A",
                    background: r.yil === null ? "transparent"
                      : solargisTon((r.yil - matris.yilLo) /
                          Math.max(1, matris.yilHi - matris.yilLo)) }}>
                    {r.yil === null ? <span style={{ color: "var(--soluk)" }}>–</span>
                      : sayiTr(Math.round(r.yil))}
                  </td>
                </tr>))}
              <tr style={{ borderTop: "2px solid var(--marka)" }}>
                <td style={{ padding: "3px 6px", color: "var(--metin)",
                             fontWeight: 600 }}>Ort.</td>
                {matris.ort.map((v, i) => (
                  <td key={i} style={{ padding: "3px 2px", textAlign: "center",
                    fontWeight: 600, border: "1px solid var(--kart)", color: "#26303A",
                    background: v === null ? "transparent"
                      : solargisTon((v - matris.lo) / (matris.hi - matris.lo)) }}>
                    {v === null ? "–" : Math.round(v)}
                  </td>))}
                <td style={{ padding: "3px 6px", textAlign: "right", fontWeight: 700,
                  border: "1px solid var(--kart)", color: "#26303A",
                  background: matris.ortYil === null ? "transparent"
                    : solargisTon((matris.ortYil - matris.yilLo) /
                        Math.max(1, matris.yilHi - matris.yilLo)) }}>
                  {matris.ortYil === null ? "–" : sayiTr(Math.round(matris.ortYil))}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p style={{ fontSize: 12, color: "var(--soluk)", margin: "12px 0 0" }}>
          Aylık GHI toplamları (kWh/m²) — sıcak tonlar yüksek ışınımı gösterir.
          Yıl sütunu tam yılların toplamıdır; Ort. satırı uzun dönem ortalamasıdır.
        </p>
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
