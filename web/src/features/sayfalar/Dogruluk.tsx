import { useEffect, useMemo, useState } from "react";
import type { EChartsOption } from "echarts";
import { api } from "../../api/client";
import type { Karne, HataMatrisi } from "../../api/types";
import { EChart } from "../../lib/EChart";
import { useTema } from "../../lib/useTema";
import { Kpi, Kart, Sayfa, Lejant, sayiTr } from "./parcalar";

const AY = ["Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
            "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"];
const donem = (a: string | null, b: string | null) => {
  if (!a || !b) return "—";
  const x = new Date(a), y = new Date(b);
  return x.getMonth() === y.getMonth()
    ? `${x.getDate()} – ${y.getDate()} ${AY[y.getMonth()]} ${y.getFullYear()}`
    : `${x.getDate()} ${AY[x.getMonth()]} – ${y.getDate()} ${AY[y.getMonth()]} ${y.getFullYear()}`;
};

export function Dogruluk({ plantId }: { plantId: string }) {
  const [k, setK] = useState<Karne | null>(null);
  const [hm, setHm] = useState<HataMatrisi | null>(null);
  const { n, oku } = useTema();
  useEffect(() => { api.karne(plantId).then(setK); }, [plantId]);
  useEffect(() => { api.hataMatrisi(plantId).then(setHm); }, [plantId]);

  const option = useMemo<EChartsOption>(() => {
    const marka = oku("--marka"), acik = oku("--marka-acik");
    const izgara = oku("--izgara"), soluk = oku("--soluk"), kenar = oku("--kenar");
    const gri = oku("--notr-acik"), mono = oku("--mono");  // v2.92: sabit ad degil token
    const g = k?.gunluk ?? [];
    // v2.76: iki kova ayni gunde birlesir — eksen benzersiz sirali tarih,
    // seriler tarih+kova aramasiyla hizalanir (satir-basina-kategori kalkti).
    const tarihler = [...new Set(g.map((r) => r.tarih))].sort();
    const bul = (t: string, kova: string) =>
      g.find((r) => r.tarih === t && r.kova === kova);
    const seri = (kova: string) =>
      tarihler.map((t) => bul(t, kova)?.wmape ?? null);
    const naifSeri = tarihler.map((t) =>
      bul(t, "0-24")?.naif_wmape ?? bul(t, "24-72")?.naif_wmape ?? null);
    return {
      grid: { left: 46, right: 12, top: 24, bottom: 28 }, animation: false,
      tooltip: { trigger: "axis", backgroundColor: oku("--kart"), borderColor: kenar,
        borderWidth: 0.5, textStyle: { color: oku("--metin"), fontSize: 12 },
        valueFormatter: (v: unknown) => (v === null ? "—" : `%${sayiTr(Number(v), 1)}`) },
      xAxis: { type: "category", data: tarihler, axisTick: { show: false },
        axisLine: { lineStyle: { color: kenar } },
        axisLabel: { color: soluk, fontFamily: mono, fontSize: 11 } },
      yAxis: { type: "value", splitLine: { lineStyle: { color: izgara } },
        axisLine: { show: false },
        axisLabel: { color: soluk, fontFamily: mono, fontSize: 11,
                     formatter: (v: number) => `%${v}` } },
      series: [
        { name: "Naif referans", type: "bar", barMaxWidth: 26,
          data: naifSeri, itemStyle: { color: gri, borderRadius: [2,2,0,0] } },
        { name: "PVQuant 0-24s", type: "bar", barMaxWidth: 26,
          data: seri("0-24"), itemStyle: { color: marka, borderRadius: [2,2,0,0] } },
        { name: "PVQuant 24-72s", type: "bar", barMaxWidth: 26,
          data: seri("24-72"), itemStyle: { color: acik, borderRadius: [2,2,0,0] } },
      ],
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [k, n]);

  const matrisOption = useMemo<EChartsOption>(() => {
    const kenar = oku("--kenar"), soluk = oku("--soluk"), mono = oku("--mono");
    const orta = oku("--kart");
    const gunler = hm?.gunler ?? [], saatler = hm?.saatler ?? [];
    const veri: [number, number, number][] = [];
    let tepe = 0;
    const mutlak: number[] = [];
    (hm?.hucreler ?? []).forEach((satir, si) => satir.forEach((v, gi) => {
      if (v !== null) { veri.push([gi, si, v]); mutlak.push(Math.abs(v)); }
    }));
    // skala siniri P95: tek uc deger govdeyi soldurmasin (uc, renk tavaninda kirpilir)
    mutlak.sort((a, b) => a - b);
    tepe = mutlak.length ? mutlak[Math.floor(0.85 * (mutlak.length - 1))] : 0;
    return {
      grid: { left: 56, right: 12, top: 8, bottom: 64 }, animation: false,
      tooltip: { backgroundColor: oku("--kart"), borderColor: kenar,
        borderWidth: 0.5, textStyle: { color: oku("--metin"), fontSize: 12 },
        formatter: (p0: unknown) => {
          const p1 = p0 as { value: [number, number, number] };
          const [gi, si, v] = p1.value;
          const yon = v >= 0 ? "fazla tahmin" : "eksik tahmin";
          return `${gunler[gi]} · ${saatler[si]}<br/>${v >= 0 ? "+" : ""}${sayiTr(v, 1)} kW (${yon})`;
        } },
      xAxis: { type: "category", data: gunler, axisTick: { show: false },
        axisLine: { lineStyle: { color: kenar } },
        axisLabel: { color: soluk, fontFamily: mono, fontSize: 10,
          formatter: (t: string) => t.slice(8) } },
      yAxis: { type: "category", data: saatler, axisTick: { show: false },
        axisLine: { show: false },
        axisLabel: { color: soluk, fontFamily: mono, fontSize: 10 } },
      visualMap: { min: -tepe || -1, max: tepe || 1, calculable: false,
        orient: "horizontal", left: "center", bottom: 0, itemWidth: 10, itemHeight: 90,
        text: ["fazla tahmin (kW)", "eksik tahmin"], textStyle: { color: soluk, fontSize: 11 },
        inRange: { color: ["#0D3A6E", "#2166AC", "#67A9CF", "#D1E5F0",
                           orta, "#FDDBC7", "#EF8A62", "#B2182B", "#7F0A1E"] } },
      series: [{ type: "heatmap", data: veri,
        itemStyle: { borderColor: oku("--izgara"), borderWidth: 1 },
        emphasis: { itemStyle: { borderColor: soluk } } }],
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hm, n]);

  if (!k) return <div style={{ color: "var(--soluk)" }}>Yükleniyor…</div>;

  // v2.76: karne gunu + kapsanan donem TUM kovalardan (Streamlit tanimi:
  // sk["date"].nunique() ve sk min/max — kova filtresiz).
  const tumTarihler = [...new Set(k.gunluk.map((r) => r.tarih))].sort();
  const donemIlk = tumTarihler[0] ?? k.ilk_tarih;
  const donemSon = tumTarihler[tumTarihler.length - 1] ?? k.son_tarih;

  return (
    <Sayfa baslik="Doğruluk karnesi"
      alt="Tahminlerimiz gerçekleşenle her gece karşılaştırılır — kanıt burada birikir."
      sag={<span className="cip">Kapsanan dönem: {donem(donemIlk, donemSon)}</span>}>
      <div className="ızgara satir-3" style={{ marginBottom: 14 }}>
        <Kpi etiket={`WMAPE · 0-24s · ${k.gun_sayisi} gün ort.`}
             deger={`%${sayiTr(k.wmape_ort ?? 0, 1)}`} alt="gündüz saatleri, valid veriyle" />
        <Kpi etiket="Naife göre üstünlük" deger={`%${sayiTr(k.naife_ustunluk_pct ?? 0)}`}
             alt="referans: dün-aynı-saat, gök açıklığıyla ölçekli" />
        <Kpi etiket="Karne günü" deger={sayiTr(new Set(k.gunluk.map((g) => g.tarih)).size)}
             birim="gün" alt="kesintisiz kanıt geçmişi" />
      </div>
      <Kart baslik="Günlük WMAPE — naif referansla karşılaştırma"
        sag={<Lejant ogeler={[{ renk: "var(--yuzey2)", ad: "Naif referans" },
                              { renk: "var(--marka)", ad: "PVQuant 0-24s" },
                              { renk: "var(--marka-acik)", ad: "PVQuant 24-72s" }]} />}>
        <EChart option={option} height={300}
          ariaLabel="Günlük WMAPE sütunları, naif referansla karşılaştırmalı" />
        <p style={{ fontSize: 12, color: "var(--soluk)", margin: "12px 0 0" }}>
          Yeşil sütunların gri sütunların altında kalması, modelin naif tahminden
          ne kadar iyi olduğunu gösterir.
        </p>
      </Kart>
      <Kart baslik="Saat × gün hata ısı haritası"
        sag={<span className="cip">son 30 gün · 0-24s · {hm?.tz ?? "—"}</span>}>
        {hm && hm.gunler.length > 0 ? (
          <>
            <EChart option={matrisOption} height={360}
              ariaLabel="Saat ve gün kırılımında işaretli tahmin hatası ısı haritası" />
            <p style={{ fontSize: 12, color: "var(--soluk)", margin: "12px 0 0" }}>
              Kızıl hücreler fazla, mavi hücreler eksik tahmini gösterir (p50 − gerçek).
              Aynı saatte üst üste aynı renk, sistematik sapmanın adresidir.
            </p>
          </>
        ) : (
          <p style={{ fontSize: 13, color: "var(--soluk)", margin: 0 }}>
            Matris için henüz eşleşmiş tahmin-gerçek çifti birikmedi — SCADA
            yüklemeleri sürdükçe burası kendiliğinden dolar.
          </p>
        )}
      </Kart>
    </Sayfa>
  );
}
