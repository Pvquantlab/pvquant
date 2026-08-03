import { useEffect, useMemo, useState } from "react";
import type { EChartsOption } from "echarts";
import { api } from "../../api/client";
import type { Karne } from "../../api/types";
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
  const { n, oku } = useTema();
  useEffect(() => { api.karne(plantId).then(setK); }, [plantId]);

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
    </Sayfa>
  );
}
