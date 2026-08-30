import { useEffect, useMemo, useState } from "react";
import type { EChartsOption } from "echarts";
import { api } from "../../api/client";
import type { Karne, HataMatrisi, HataDagilimi } from "../../api/types";
import { EChart } from "../../lib/EChart";
import { useTema } from "../../lib/useTema";
import { Kpi, Kart, Sayfa, sayiTr } from "./parcalar";

const AY = ["Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
            "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"];
const donemYaz = (a: string | null, b: string | null) => {
  if (!a || !b) return "—";
  const x = new Date(a), y = new Date(b);
  return x.getMonth() === y.getMonth()
    ? `${x.getDate()} – ${y.getDate()} ${AY[y.getMonth()]} ${y.getFullYear()}`
    : `${x.getDate()} ${AY[x.getMonth()]} – ${y.getDate()} ${AY[y.getMonth()]} ${y.getFullYear()}`;
};

export function Dogruluk({ plantId }: { plantId: string }) {
  const [k, setK] = useState<Karne | null>(null);
  const [hm, setHm] = useState<HataMatrisi | null>(null);
  const [hd, setHd] = useState<HataDagilimi | null>(null);
  // v2.230: donem segmenti (mockup H'den; API gun'u zaten destekliyordu).
  // Yalniz KARNEYI (KPI'lar + WMAPE panelleri) surer — matris/dagilim kendi
  // pencerelerini ciplerinde soyler. Gecis sirasinda eski veri tutulur
  // (k null'a dusmez), sayfa titremez.
  const [donem, setDonem] = useState<30 | 60 | 90>(60);
  const { n, oku } = useTema();
  useEffect(() => { api.karne(plantId, donem).then(setK); }, [plantId, donem]);
  useEffect(() => { api.hataMatrisi(plantId).then(setHm); }, [plantId]);
  useEffect(() => { api.hataDagilimi(plantId).then(setHd); }, [plantId]);

  // v2.225 (H "Rapor Dili"): Solargis grameri — gunluk degerler NOKTA,
  // 7 gun egilimi TEK kalin cizgi, naif INCE gri cizgi (alan degil).
  // Hiyerarsi: nokta < gri cizgi < egilim; ic ice cizgi karmasasi biter.
  const wmapePanel = useMemo(() => {
    const izgara = oku("--izgara"), soluk = oku("--soluk");
    const kenar = oku("--kenar"), mono = oku("--mono");
    const marka = oku("--marka"), dusuk = oku("--ch-dusuk");
    const markaKoyu = oku("--marka-koyu");
    const g = k?.gunluk ?? [];
    const tarihler = [...new Set(g.map((r) => r.tarih))].sort();
    const bul = (t: string, kova: string) =>
      g.find((r) => r.tarih === t && r.kova === kova);
    // 7 gun hareketli ortalama — pencerede en az 3 gercek deger yoksa "—"
    const ho7 = (xs: (number | null)[]) => xs.map((_, i) => {
      const p = xs.slice(Math.max(0, i - 6), i + 1)
        .filter((x): x is number => typeof x === "number");
      return p.length >= 3 ? p.reduce((a, b) => a + b, 0) / p.length : null;
    });
    return (kova: string): EChartsOption => {
      const gunluk = tarihler.map((t) => bul(t, kova)?.wmape ?? null);
      const naif = tarihler.map((t) => bul(t, kova)?.naif_wmape ?? null);
      const egilim = ho7(gunluk);
      const tepe = Math.max(10,
        ...gunluk.filter((v): v is number => v !== null),
        ...naif.filter((v): v is number => v !== null));
      const ymax = Math.min(100, Math.ceil((tepe * 1.12) / 10) * 10);
      let si = -1;
      egilim.forEach((v, i) => { if (v !== null) si = i; });
      return {
        grid: { left: 40, right: 14, top: 18, bottom: 26 }, animation: false,
        tooltip: { trigger: "axis", backgroundColor: oku("--kart"), borderColor: kenar,
          borderWidth: 0.5, textStyle: { color: oku("--metin"), fontSize: 12 },
          valueFormatter: (v: unknown) => (v == null ? "—" : `%${sayiTr(Number(v), 1)}`) },
        xAxis: { type: "category", data: tarihler, axisTick: { show: false },
          axisLine: { lineStyle: { color: kenar } },
          // v2.231: sabit 13 araligi 30g penceresinde tek etiket birakiyordu —
          // hedef ~4 etiket, pencereye gore olceklenir
          axisLabel: { color: soluk, fontFamily: mono, fontSize: 10,
            interval: Math.max(1, Math.ceil(tarihler.length / 4) - 1) } },
        yAxis: { type: "value", max: ymax, splitLine: { lineStyle: { color: izgara } },
          axisLine: { show: false },
          axisLabel: { color: soluk, fontFamily: mono, fontSize: 10,
                       formatter: (v: number) => `%${v}` } },
        series: [
          { name: "Naif referans", type: "line", symbol: "none", z: 1,
            lineStyle: { color: dusuk, width: 1.4 },
            data: naif, connectNulls: true },
          { name: "Günlük", type: "scatter", z: 2, symbolSize: 4.5,
            itemStyle: { color: marka, opacity: 0.42 }, data: gunluk },
          {
            name: "7 gün eğilimi", type: "line", symbol: "none", z: 3,
            lineStyle: { color: marka, width: 2.6, cap: "round", join: "round" },
            data: egilim, connectNulls: true,
            ...(si >= 0 ? { markPoint: {
              silent: true, symbol: "circle", symbolSize: 7,
              itemStyle: { color: marka, borderColor: oku("--kart"), borderWidth: 1.5 },
              label: { show: true, position: "top", distance: 6, color: markaKoyu,
                fontFamily: "monospace", fontSize: 10, fontWeight: "bold",
                formatter: () => `%${sayiTr(egilim[si] as number, 1)}` },
              data: [{ coord: [tarihler[si], egilim[si]] }],
            } } : {}),
          } as unknown as NonNullable<EChartsOption["series"]>,
        ] as EChartsOption["series"],
      };
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [k, n]);

  const matrisOption = useMemo<EChartsOption>(() => {
    const kenar = oku("--kenar"), soluk = oku("--soluk"), mono = oku("--mono");
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
    // v2.225 (H): sag marj — saat basina ortalama |hata| profili; matrisin
    // saat imzasini tek bakista ozetler (Solargis kucuk-marj dili).
    const profil = saatler.map((_, si) => {
      const xs = (hm?.hucreler?.[si] ?? [])
        .filter((v): v is number => v !== null).map(Math.abs);
      return xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0;
    });
    return {
      grid: [
        { left: 56, right: 168, top: 26, bottom: 64 },
        { right: 12, width: 128, top: 26, bottom: 64 },
      ],
      animation: false,
      tooltip: { backgroundColor: oku("--kart"), borderColor: kenar,
        borderWidth: 0.5, textStyle: { color: oku("--metin"), fontSize: 12 },
        formatter: (p0: unknown) => {
          const p1 = p0 as { seriesType: string; value: unknown; name: string };
          if (p1.seriesType === "bar") {
            return `${p1.name} · ort. |hata| ${sayiTr(Number(p1.value), 0)} kW`;
          }
          const [gi, si, v] = p1.value as [number, number, number];
          const yon = v >= 0 ? "fazla tahmin" : "eksik tahmin";
          return `${gunler[gi]} · ${saatler[si]}<br/>${v >= 0 ? "+" : ""}${sayiTr(v, 1)} kW (${yon})`;
        } },
      xAxis: [
        { type: "category", data: gunler, gridIndex: 0, axisTick: { show: false },
          axisLine: { lineStyle: { color: kenar } },
          axisLabel: { color: soluk, fontFamily: mono, fontSize: 10,
            formatter: (t: string) => t.slice(8) } },
        { type: "value", gridIndex: 1, splitLine: { show: false },
          axisLine: { show: false }, axisTick: { show: false },
          axisLabel: { show: false },
          name: "ort. |hata| (kW)", nameLocation: "end" as const, nameGap: 6,
          nameTextStyle: { color: soluk, fontFamily: mono, fontSize: 10,
                           align: "right" as const, verticalAlign: "bottom" as const,
                           padding: [0, 0, -34, 0] } },
      ],
      yAxis: [
        { type: "category", data: saatler, gridIndex: 0, axisTick: { show: false },
          axisLine: { show: false },
          axisLabel: { color: soluk, fontFamily: mono, fontSize: 10 } },
        { type: "category", data: saatler, gridIndex: 1, show: false },
      ],
      // v2.225 (H): rampa "alacakaranlik" — celik mavi ↔ sicak altin,
      // dusuk kroma (goz yormaz); sektor teamulu korunur (mavi=eksik,
      // sicak=fazla), sifir civari zemin gibi sessiz. Koyu temada uclar
      // parlak, sifir civari koyu (algi tersinmesin). Lejant SAYISAL:
      // uc degerler metinde (grafik kurali — renk tek basina konusmasin).
      visualMap: { min: -tepe || -1, max: tepe || 1, calculable: false,
        orient: "horizontal", left: "center", bottom: 0, itemWidth: 10, itemHeight: 90,
        seriesIndex: 0,
        text: [`fazla · +${sayiTr(tepe, 0)} kW`, `eksik · −${sayiTr(tepe, 0)} kW`],
        textStyle: { color: soluk, fontSize: 11 },
        inRange: { color: document.documentElement.dataset.tema === "koyu"
          ? ["#7FB0DE", "#5A87B4", "#3D608A", "#263D5C",
             "#14213A", "#4A3418", "#755324", "#A47334", "#D49A4C"]
          : ["#2F4F76", "#587DA6", "#92AECB", "#CBDAE8",
             "#FBFCFE", "#F0DDBE", "#D3A15D", "#A06E33", "#6E4A1E"] } },
      series: [
        { type: "heatmap", data: veri, xAxisIndex: 0, yAxisIndex: 0,
          itemStyle: { borderColor: oku("--izgara"), borderWidth: 1 },
          emphasis: { itemStyle: { borderColor: soluk } } },
        { type: "bar", data: profil, xAxisIndex: 1, yAxisIndex: 1,
          barWidth: "62%", itemStyle: { color: oku("--ch-dusuk") },
          emphasis: { itemStyle: { color: soluk } } },
      ],
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hm, n]);

  // v2.225 (H): cubuklar TAHMIN MAVISI (sapma tahminin urunudur; amber
  // yalniz gerceklesene ayrili), yesil egri kumulatif pay (sag eksen),
  // P10-P90 acik bant + duz medyan cizgisi (Solargis Fig 7.5 dili).
  // API p25/p75 vermez \u2014 ic bant cizilmez (tire ilkesinin alan hali).
  const dagOption = useMemo<EChartsOption>(() => {
    const kenar = oku("--kenar"), soluk = oku("--soluk"), mono = oku("--mono");
    const marka = oku("--marka"), markaKoyu = oku("--marka-koyu");
    const mavi = oku("--chart-p50-future");
    const kutular = hd?.kutular ?? [];
    // v2.232: TR sayi bicimi + bosluklu ayrac — "-1.5-–1" yigilmasi biter
    const ond = kutular.some((x) => !Number.isInteger(x.lo) || !Number.isInteger(x.hi)) ? 1 : 0;
    const etiket = kutular.map((x) => `${sayiTr(x.lo, ond)} \u2013 ${sayiTr(x.hi, ond)}`);
    const kutuGen = kutular.length ? kutular[0].hi - kutular[0].lo : 1;
    const xi = (v: number) => (v - (kutular[0]?.lo ?? 0)) / kutuGen - 0.5;
    const toplam = kutular.reduce((a, b) => a + b.adet, 0);
    let birikim = 0;
    const kdf = kutular.map((b) => {
      birikim += b.adet;
      return toplam ? Math.round((1000 * birikim) / toplam) / 10 : 0;
    });
    const bant = hd?.p10 != null && hd?.p90 != null
      ? [[{ xAxis: xi(hd.p10), name: "P10\u2013P90",
            itemStyle: { color: soluk, opacity: 0.12 },
            label: { show: true, position: "insideTopLeft" as const, distance: 6,
                     color: soluk, fontSize: 10, fontFamily: mono } },
          { xAxis: xi(hd.p90) }]]
      : [];
    return {
      grid: { left: 46, right: 46, top: 24, bottom: 44 }, animation: false,
      tooltip: { trigger: "axis", backgroundColor: oku("--kart"), borderColor: kenar,
        borderWidth: 0.5, textStyle: { color: oku("--metin"), fontSize: 12 },
        valueFormatter: (v: unknown) => `${v}` },
      xAxis: [
        { type: "category", data: etiket, name: "MWh/g\u00fcn (tahmin \u2212 ger\u00e7ekle\u015fen)",
          nameLocation: "middle", nameGap: 26,
          nameTextStyle: { color: soluk, fontSize: 11 },
          axisTick: { show: false }, axisLine: { lineStyle: { color: kenar } },
          axisLabel: { color: soluk, fontFamily: mono, fontSize: 11 } },
        // v2.232: KDF icin gizli deger ekseni — kutu KENARLARI (kumulatif pay
        // kutunun SONUNDA birikir; Solargis Fig 7.5 egriyi kenardan gecirir)
        { type: "value", min: -0.5, max: Math.max(0.5, kutular.length - 0.5),
          show: false },
      ],
      yAxis: [
        { type: "value", name: "g\u00fcn", nameGap: 10,
          nameTextStyle: { color: soluk, fontFamily: mono, fontSize: 10 },
          splitLine: { lineStyle: { color: oku("--izgara") } },
          axisLine: { show: false },
          axisLabel: { color: soluk, fontFamily: mono, fontSize: 11 } },
        { type: "value", min: 0, max: 100, splitLine: { show: false },
          axisLine: { show: false }, axisTick: { show: false },
          axisLabel: { color: markaKoyu, fontFamily: mono, fontSize: 11,
                       formatter: (v: number) => `%${v}` } },
      ],
      series: [
        { name: "G\u00fcn say\u0131s\u0131", type: "bar", barMaxWidth: 40,
          data: kutular.map((b) => b.adet),
          itemStyle: { color: mavi, opacity: 0.88, borderRadius: [2, 2, 0, 0] },
          z: 2,
          markArea: bant.length
            ? { silent: true, data: bant as never }
            : undefined,
          markLine: { symbol: "none", animation: false, silent: true,
            data: [
              // v2.232: sifir cizgisi vurgusu (mockup H'de vardi, canliya gelmemisti)
              ...(kutular.length && kutular[0].lo <= 0 &&
                  kutular[kutular.length - 1].hi >= 0
                ? [{ xAxis: xi(0),
                     lineStyle: { color: oku("--chart-baseline") || kenar,
                                  type: "solid" as const, width: 1.2 },
                     label: { show: false } }]
                : []),
              // v2.232: medyan etiketi dikeyken cubugun icinde kayboluyordu —
              // yatay, cizginin tepesinde (rotate 0, position end)
              ...(hd?.p50 != null
                ? [{ name: "medyan", xAxis: xi(hd.p50),
                     lineStyle: { color: soluk, type: "solid" as const, width: 1.4 },
                     label: { color: soluk, fontSize: 10, fontFamily: mono,
                       position: "end" as const, distance: 6, rotate: 0,
                       formatter: () => `medyan ${sayiTr(hd.p50 as number, 2)}` } }]
                : []),
            ] as never } },
        { name: "K\u00fcm\u00fclatif pay", type: "line", xAxisIndex: 1, yAxisIndex: 1, z: 3,
          symbol: "none",
          data: [[-0.5, 0], ...kdf.map((v, i) => [i + 0.5, v])],
          lineStyle: { color: marka, width: 2.2 } },
      ],
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hd, n]);

  // v2.225 (H): WMAPE delta cipi — API'de donem kiyasi yok; DURUST yol:
  // gunluk karneden son 30 gun vs onceki 30 gun ortalamasi TURETILIR.
  // Iki pencere de yeterince dolu degilse cip hic gorunmez (uydurma yok).
  const delta = useMemo(() => {
    const g = (k?.gunluk ?? []).filter(
      (r) => r.kova === "0-24" && typeof r.wmape === "number");
    const tarihler = [...new Set(g.map((r) => r.tarih))].sort();
    if (tarihler.length < 28) return null;
    const ort = (ts: string[]) => {
      const v = ts
        .map((t) => g.find((r) => r.tarih === t)?.wmape)
        .filter((x): x is number => typeof x === "number");
      return v.length >= 14 ? v.reduce((a, b) => a + b, 0) / v.length : null;
    };
    const son = ort(tarihler.slice(-30));
    const once = ort(tarihler.slice(-60, -30));
    if (son === null || once === null) return null;
    return son - once;
  }, [k]);

  if (!k) return <div style={{ color: "var(--soluk)" }}>Yükleniyor…</div>;

  const OK = ({ yukari }: { yukari: boolean }) => (
    <svg width="9" height="9" viewBox="0 0 10 10" aria-hidden="true">
      <path d={yukari ? "M5 8V2M2.4 4.6 5 2l2.6 2.6" : "M5 2v6M2.4 5.4 5 8l2.6-2.6"}
        fill="none" stroke="currentColor" strokeWidth="1.5"
        strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
  const deltaCip = delta === null ? "gündüz saatleri, valid veriyle"
    : Math.abs(delta) < 0.05 ? (
      <span className="kpi-delta notr" role="status">
        değişim yok · önceki 30 güne göre
      </span>
    ) : (
      <span className={`kpi-delta ${delta < 0 ? "iyi" : "notr"}`} role="status">
        <OK yukari={delta > 0} />
        {sayiTr(Math.abs(delta), 1)} puan · önceki 30 güne göre
      </span>
    );

  // v2.76: karne gunu + kapsanan donem TUM kovalardan (Streamlit tanimi:
  // sk["date"].nunique() ve sk min/max — kova filtresiz).
  const tumTarihler = [...new Set(k.gunluk.map((r) => r.tarih))].sort();
  const donemIlk = tumTarihler[0] ?? k.ilk_tarih;
  const donemSon = tumTarihler[tumTarihler.length - 1] ?? k.son_tarih;

  return (
    <Sayfa baslik="Doğruluk karnesi"
      alt="Tahminlerimiz gerçekleşenle her gece karşılaştırılır — kanıt burada birikir."
      sag={<>
        <span className="seg" role="group" aria-label="Karne dönemi">
          {([30, 60, 90] as const).map((g) => (
            <button key={g} aria-pressed={donem === g}
              onClick={() => setDonem(g)}>{g}g</button>
          ))}
        </span>
        <span className="cip">Kapsanan dönem: {donemYaz(donemIlk, donemSon)}</span>
      </>}>
      <div className="ızgara satir-4" style={{ marginBottom: 14 }}>
        <Kpi etiket={`WMAPE · 0-24s · ${k.gun_sayisi} gün ort.`}
             deger={`%${sayiTr(k.wmape_ort ?? 0, 1)}`} alt={deltaCip} />
        <Kpi etiket="Naife göre üstünlük" deger={`%${sayiTr(k.naife_ustunluk_pct ?? 0)}`}
             alt="referans: dün-aynı-saat, gök açıklığıyla ölçekli" />
        <Kpi etiket="Karne günü" deger={sayiTr(new Set(k.gunluk.map((g) => g.tarih)).size)}
             birim="gün" alt="kesintisiz kanıt geçmişi" />
        <Kpi etiket="Günlük sapma μ · σ"
             deger={hd?.mu != null && hd?.sd != null
               ? `${sayiTr(hd.mu, 2)} · ${sayiTr(hd.sd, 2)}` : "—"}
             birim={hd?.mu != null ? "MWh" : undefined}
             alt={hd?.mu != null
               ? "sıfır merkezli dar dağılım hedef"
               : "yeterli eşleşmiş gün birikmedi"} />
      </div>
      <Kart baslik="Günlük WMAPE — naif referansla karşılaştırma"
        sag={<span className="cip">nokta: günlük · kalın: 7 gün eğilimi · ince gri: naif</span>}>
        <div className="ızgara" style={{ gridTemplateColumns: "minmax(0,1fr) minmax(0,1fr)" }}>
          <div>
            <p style={{ fontSize: 12.5, fontWeight: 600, color: "var(--metin)",
                        margin: "0 0 4px" }}>0–24 saat ufku</p>
            <EChart option={wmapePanel("0-24")} height={240}
              ariaLabel="0-24 saat ufku günlük WMAPE, naif referans zeminiyle" />
          </div>
          <div>
            <p style={{ fontSize: 12.5, fontWeight: 600, color: "var(--metin)",
                        margin: "0 0 4px" }}>24–72 saat ufku</p>
            <EChart option={wmapePanel("24-72")} height={240}
              ariaLabel="24-72 saat ufku günlük WMAPE, naif referans zeminiyle" />
          </div>
        </div>
        <p style={{ fontSize: 12, color: "var(--soluk)", margin: "12px 0 0" }}>
          <b style={{ color: "var(--ikincil)" }}>Bu paneller günlük tahmin hatasını ölçer (WMAPE, %):</b>{" "}
          her nokta bir günün hatası, kalın yeşil çizgi 7 günlük eğilimdir; ince gri
          çizgi "naif" referanstır — dünü kopyalayan akılsız tahmin.{" "}
          <b style={{ color: "var(--ikincil)" }}>Nasıl okunur:</b> yeşil eğilim gri
          çizginin ne kadar altındaysa modelin kattığı değer o kadar büyüktür;
          sağ panelde hatanın bir miktar yüksek olması doğaldır — 3 güne kadar bakan
          tahmin daha fazla belirsizlik taşır, önemli olan aradaki farkın kontrollü kalmasıdır.
        </p>
      </Kart>
      <Kart baslik="Saat × gün hata ısı haritası"
        sag={<span className="cip">son 30 gün · 0-24s · {hm?.tz ?? "—"}</span>}>
        {hm && hm.gunler.length > 0 ? (
          <>
            <EChart option={matrisOption} height={360}
              ariaLabel="Saat ve gün kırılımında işaretli tahmin hatası ısı haritası" />
            <p style={{ fontSize: 12, color: "var(--soluk)", margin: "12px 0 0" }}>
              <b style={{ color: "var(--ikincil)" }}>Her hücre bir gün × saat kutusudur</b>{" "}
              ve o saatteki işaretli hatayı gösterir: altın tonlar fazla tahmin
              (tahmin &gt; gerçekleşen), mavi tonlar eksik tahmin; renk koyulaştıkça
              hata büyür, sıfıra yakın hücreler zemin gibi sessiz kalır.{" "}
              <b style={{ color: "var(--ikincil)" }}>Neye bakmalı:</b> dikey tek renkli
              bir sütun, bulutun beklenenden erken/geç geldiği tekil bir gündür; aynı
              saat satırında gün gün tekrar eden renk ise sistematik sapmanın adresidir —
              kalibrasyonun bir sonraki hedefi o satırdır. Sağdaki profil aynı imzanın
              saat özetidir.
            </p>
          </>
        ) : (
          <p style={{ fontSize: 13, color: "var(--soluk)", margin: 0 }}>
            Matris için henüz eşleşmiş tahmin-gerçek çifti birikmedi — SCADA
            yüklemeleri sürdükçe burası kendiliğinden dolar.
          </p>
        )}
      </Kart>
      <Kart baslik="Günlük sapma dağılımı (tahmin − gerçekleşen)"
        sag={<span className="cip">
          {hd?.ndays ?? 0} geçerli gün · μ {hd?.mu ?? "—"} · σ {hd?.sd ?? "—"} MWh
        </span>}>
        {hd && hd.kutular.length > 0 ? (
          <>
            <EChart option={dagOption} height={280}
              ariaLabel="Günlük tahmin sapması histogramı, yüzdelik çizgileriyle" />
            <p style={{ fontSize: 12, color: "var(--soluk)", margin: "12px 0 0" }}>
              <b style={{ color: "var(--ikincil)" }}>Bu grafik günlük enerji sapmasının dağılımıdır:</b>{" "}
              her mavi çubuk, günlük toplam sapması (tahmin − gerçekleşen, MWh) o aralığa
              düşen gün sayısını verir; sıfırın solu eksik, sağı fazla tahmindir. Gri bant
              günlerin %80'inin düştüğü P10–P90 aralığı, düz çizgi medyan, yeşil eğri
              kümülatif paydır (sağ eksen).{" "}
              <b style={{ color: "var(--ikincil)" }}>Neye bakmalı:</b> gövde sıfır
              çevresinde ne kadar dar toplanırsa model o kadar güvenilirdir; gövdenin
              sola/sağa kayması sistematik eksik/fazla tahminin işaretidir.
            </p>
          </>
        ) : (
          <p style={{ fontSize: 13, color: "var(--soluk)", margin: 0 }}>
            Dağılım için henüz yeterli eşleşmiş gün birikmedi.
          </p>
        )}
      </Kart>
    </Sayfa>
  );
}
