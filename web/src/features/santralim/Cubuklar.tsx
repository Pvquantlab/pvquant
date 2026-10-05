/** Deger etiketli cubuk grafik — 7 gunluk gorunum ve aylik uretim icin.
 *  v2.196 (D karari): en dusuk donem NOTR koyulasir — amber artik yalniz
 *  "gerceklesen" grafik murekkebi (anayasa); eski K7 amber'i kaldirildi. */
import { useMemo } from "react";
import type { EChartsOption } from "echarts";
import { EChart } from "../../lib/EChart";
import { useTema } from "../../lib/useTema";
import { renkler, eksenYazi, eksenDeger, eksenKategori, tooltipEksen, TEMEL } from "../../lib/grafikTema";
import { Lejant, sayiTr } from "../sayfalar/parcalar";

export function Cubuklar({ etiketler, degerler, birim, vurguIdx, yukseklik = 260, ondalik = 1, kapsamPct, beklenti }:
  { etiketler: string[];
    /** v2.316 — null: takvimde var ama verisi yok; çubuk çizilmez, sıfır uydurulmaz. */
    degerler: (number | null)[]; birim: string;
    vurguIdx?: number; yukseklik?: number; ondalik?: number;
    kapsamPct?: number[];
    /** v2.203 (D bullet imleci): donem basina beklenti-P50; null = imlec yok */
    beklenti?: (number | null)[] }) {
  const { n, oku } = useTema();
  const option = useMemo<EChartsOption>(() => {
    // v2.148: mr/ar/grad kalıntısı söküldü; v2.397: jetonlar tek paketten.
    const r = renkler(oku);
    const nr = r.notrR || "100,116,139";
    // v2.118: kapsam <%50 aylar "eksik veri" sayilir — en-dusuk aramasina
    // girmez (Solargis: olculmemis donem, kotu donemle karistirilmaz)
    const tam = (i: number) => !kapsamPct || (kapsamPct[i] ?? 100) >= 50;
    const adaylar = degerler.map((v, i) => (tam(i) && v != null ? v : Infinity));
    const enDusuk = adaylar.indexOf(Math.min(...adaylar));
    return {
      ...TEMEL, grid: { left: 46, right: 10, top: 26, bottom: 26 },
      tooltip: tooltipEksen(r, {
        formatter: (ps: unknown) => {
          const a = ps as { dataIndex: number; value: number }[];
          const i = a[0]?.dataIndex ?? 0;
          if (degerler[i] == null) return `${etiketler[i]}: — veri yok`;
          let satir = `${etiketler[i]}: ${sayiTr(Number(a[0]?.value), ondalik)} ${birim}`;
          const b = beklenti?.[i];
          if (b !== null && b !== undefined)
            satir += `<br/>beklenti · P50: ${sayiTr(b, ondalik)} ${birim}`;
          return tam(i) ? satir
            : `${satir}<br/><span style="opacity:.75">kapsam %${sayiTr(kapsamPct![i], 1)} — eksik veri</span>`;
        } }),
      xAxis: eksenKategori(r, etiketler, {
        axisLine: { lineStyle: { color: r.kenar } },
        axisLabel: eksenYazi(r, 11) }),
      yAxis: eksenDeger(r, { axisLine: { show: false },
        axisLabel: eksenYazi(r, 11, { formatter: (v: number) => sayiTr(v) }) }),
      series: [{
        type: "bar", barMaxWidth: 34,
        data: degerler.map((v, i) => ({ value: v, itemStyle: {
          borderRadius: [2, 2, 0, 0],
          color: !tam(i) ? (r.eksik || `rgba(${nr},.18)`)
               : i === enDusuk ? (r.dusuk || "#A8A296")
               : i === vurguIdx ? r.vurgu
               : (r.cubuk || "#6FA98A"),
          borderType: !tam(i) ? "dashed" as const : "solid" as const,
          borderColor: !tam(i) ? `rgba(${nr},.5)` : "transparent",
          borderWidth: !tam(i) ? 1 : 0 },
          // v2.311: eksik-veri cubugunun degeri tam agirlikta basiliyordu —
          // hayalet cubugun rakami kendinden emin okunuyordu.
          label: tam(i) ? undefined : { color: r.soluk } })),
        label: { show: true, position: "top", color: r.ikincil,
                 fontFamily: r.mono, fontSize: 11,
                 formatter: (p: unknown) =>
                   sayiTr(Number((p as { value: number }).value), ondalik) },
      },
      // v2.203: beklenti-P50 imleci — cubugun ustune binen yatay cizgi
      // (D bullet dili); yalniz degeri olan donemlerde cizilir, uydurma yok.
      ...(beklenti && beklenti.some((b) => b !== null) ? [{
        type: "scatter" as const, silent: true, z: 5,
        symbol: "rect", symbolSize: [40, 2.4],
        itemStyle: { color: r.metin },
        tooltip: { show: false },
        data: beklenti.map((b, i) => (b === null ? null : [i, b])),
      }] : []),
      ],
    } as EChartsOption;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  // v2.311: kapsamPct/beklenti deps'te yoktu; Aylik ilk kez kapsamPct gecirmeye
  // basladigi icin veri tazelendiginde bayat option riski dogardi.
  }, [etiketler, degerler, kapsamPct, beklenti, vurguIdx, n]);

  // v2.315 (K4): grafikte dört ISTISNAI kodlama var ama bugüne dek yalnız tooltip
  // söylüyordu — fare kullanmayan icin bilgi yoktu. Lejant KOŞULLU: yalnız o örnekte
  // gerçekten görünen kodlamalar listelenir; olağan yeşil çubuk varsayılan olduğu
  // için ayrıca yazılmaz. Öncelik zinciri (eksik > en düşük > vurgu) korunur —
  // vurgu ayı aynı zamanda en düşükse "son ay" öğesi de basılmaz (renk görünmüyor).
  const tamMi = (i: number) => !kapsamPct || (kapsamPct[i] ?? 100) >= 50;
  const tamSayisi = degerler.filter((v, i) => v != null && tamMi(i)).length;
  const adaylar2 = degerler.map((v, i) => (tamMi(i) && v != null ? v : Infinity));
  const enDusukIdx = adaylar2.indexOf(Math.min(...adaylar2));
  const ogeler = [
    ...(vurguIdx != null && vurguIdx >= 0 && tamMi(vurguIdx) && vurguIdx !== enDusukIdx
      ? [{ renk: "var(--cubuk-vurgu)", ad: "son ay" }] : []),
    ...(tamSayisi >= 2 ? [{ renk: "var(--ch-dusuk)", ad: "en düşük ay" }] : []),
    ...(kapsamPct && degerler.some((v, i) => v != null && !tamMi(i))
      ? [{ renk: "var(--notr)", ad: "eksik veri · kapsam <%50", kesik: true }] : []),
    ...(beklenti && beklenti.some((b) => b != null)
      ? [{ renk: "var(--metin)", ad: "beklenti · P50", cizgi: true }] : []),
  ];
  return (
    <>
      <EChart option={option} height={yukseklik}
        ariaLabel={`${etiketler.length} sütunlu üretim grafiği, ${birim}`} />
      {ogeler.length > 0 && <div style={{ marginTop: 8 }}><Lejant ogeler={ogeler} /></div>}
    </>
  );
}
