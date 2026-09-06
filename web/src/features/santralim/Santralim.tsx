import { useEffect, useMemo, useState } from "react";
import type { PrKarti, Saglik, AlarmKurallari, FizikTerimleri, FizikOnizleme } from "../../api/types";
import { SEGMENTLER } from "../../api/types";
import type { EChartsOption } from "echarts";
import { api } from "../../api/client";
import type { SantralOzeti, TahminSerisi, GunesYolu, SaatAyMatrisi } from "../../api/types";
import { EChart } from "../../lib/EChart";
import { useTema } from "../../lib/useTema";
import { Kart, Sayfa, sayiTr, isiTonu, isiMetni } from "../sayfalar/parcalar";
import ProductionForecastChart from "../sayfalar/ProductionForecastChart";
import { t0Hesapla, simdiDegeri, dilimle } from "../sayfalar/tahminPencere";
import { Cubuklar } from "./Cubuklar";

/** v2.200 (D imzasi): 7 gunluk gorunum — cubuk yerine profilli tablo.
 *  Gun-ici profil 16 gunluk saatlik P50'den turetilir (dilimleme istemcide,
 *  Tahminler kalibi); toplam MWh API'nin kendi gunluk degeridir. Tum gunler
 *  AYNI olcekle cizilir — profiller karsilastirilabilir kalsin. */
function gunAnahtari(ms: number, tz: string): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: tz, year: "numeric", month: "2-digit", day: "2-digit",
  }).format(new Date(ms));
}

function GunProfili({ noktalar, tepe, vurgu }:
  { noktalar: number[]; tepe: number; vurgu?: boolean }) {
  if (noktalar.length < 2 || tepe <= 0)
    return <span style={{ color: "var(--soluk)" }}>—</span>;
  const d = noktalar.map((v, i) =>
    `${(2 + (i / (noktalar.length - 1)) * 96).toFixed(1)},${(23 - (v / tepe) * 19).toFixed(1)}`)
    .join(" ");
  return (
    <svg viewBox="0 0 100 26" aria-hidden="true"
      style={{ width: 100, height: 26, display: "block" }}>
      <polyline points={d} fill="none"
        stroke={vurgu ? "var(--cubuk-vurgu)" : "var(--ch-cubuk)"}
        strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function Santralim({ plantId }: { plantId: string }) {
  const [o, setO] = useState<SantralOzeti | null>(null);
  const [pr, setPr] = useState<PrKarti | null>(null);   // v2.249
  const [seri, setSeri] = useState<TahminSerisi | null>(null);
  const [gy, setGy] = useState<GunesYolu | null>(null);
  const [sam, setSam] = useState<SaatAyMatrisi | null>(null);
  const { n, oku } = useTema();
  useEffect(() => { api.ozet(plantId).then(setO); }, [plantId]);
  useEffect(() => { api.tahmin(plantId, "16d").then(setSeri); }, [plantId]); // v2.166: D1 — tam seri cek, istemcide "24h" dilimle (Tahminler kalibi)
  useEffect(() => { api.gunesYolu(plantId).then(setGy).catch(() => {}); }, [plantId]);
  useEffect(() => { api.saatAyMatrisi(plantId).then(setSam).catch(() => {}); }, [plantId]);
  useEffect(() => { api.pr(plantId).then(setPr).catch(() => {}); }, [plantId]);   // v2.249
  const [sg, setSg] = useState<Saglik | null>(null);   // v2.256
  const [seg, setSeg] = useState<{ segment: string | null; dengesizlik_sahibi: string | null } | null>(null);   // v2.260
  useEffect(() => { api.dengesizlik(plantId, 14).then((d) => d && setSeg({ segment: d.segment.segment, dengesizlik_sahibi: d.segment.dengesizlik_sahibi })).catch(() => {}); }, [plantId]);
  useEffect(() => { api.saglik(plantId).then(setSg).catch(() => {}); }, [plantId]);
  // v2.274 (Dalga 3 tamamlayıcısı): fizik terimleri — santral bazında aç/kapa + "açsam ne değişir?" önizlemesi
  const [ft, setFt] = useState<FizikTerimleri | null>(null);
  const [ftOn, setFtOn] = useState<FizikOnizleme | null>(null);
  const [ftMesaj, setFtMesaj] = useState<string | null>(null);
  useEffect(() => { api.fizikTerimleri(plantId).then(setFt).catch(() => {}); }, [plantId]);
  const [ftSon, setFtSon] = useState<Record<string, string>>({});
  const ftDegistir = (k: string, v: string) => {
    setFtMesaj(null); setFtOn(null); setFtSon({ [k]: v });
    api.fizikOnizle(plantId, { [k]: v }).then(setFtOn).catch((e) => setFtMesaj(String((e as Error).message ?? e)));
  };
  const ftUygula = (k: string, v: string) => {
    api.fizikAyarla(plantId, { [k]: v }).then((r) => { setFt(r); setFtOn(null); setFtSon({}); setFtMesaj("Kaydedildi — bir sonraki koşudan itibaren geçerli."); })
      .catch((e) => setFtMesaj(String((e as Error).message ?? e)));
  };
  const [ak, setAk] = useState<AlarmKurallari | null>(null);   // v2.265: ek alarm kuralları (opt-in)
  useEffect(() => { api.alarmKurallari(plantId).then(setAk).catch(() => {}); }, [plantId]);
  const akDegistir = (kural: string, acik: boolean) => {
    if (!ak) return;
    const k = acik ? [...ak.secili, kural] : ak.secili.filter((x) => x !== kural);
    api.alarmKurallariAyarla(plantId, k, ak.esik).then(setAk).catch(() => {});
  };
  const t0 = useMemo(() => t0Hesapla(Date.now()), []);
  const nowVal = useMemo(
    () => (seri ? simdiDegeri(seri.saatlik, t0) : null), [seri, t0]);
  const dilim = useMemo(
    () => (seri ? dilimle(seri.saatlik, t0, "24h") : null), [seri, t0]);
  // v2.200: gun-ici P50 profilleri — gunAnahtari(t0+i gun) ile gruplanir
  const gunProfilleri = useMemo(() => {
    if (!seri || !o) return null;
    const grup = new Map<string, number[]>();
    for (const x of seri.saatlik) {
      const k = gunAnahtari(new Date(x.ts).getTime(), o.tz);
      if (!grup.has(k)) grup.set(k, []);
      grup.get(k)!.push(x.p50_kw ?? 0);
    }
    const gunler = o.gunler.map((_, i) =>
      grup.get(gunAnahtari(t0 + i * 86_400_000, o.tz)) ?? []);
    const tepe = Math.max(1, ...gunler.flat());
    return { gunler, tepe };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seri, o, t0]);
  const AYLAR_K = ["Oca","Şub","Mar","Nis","May","Haz","Tem","Ağu","Eyl","Eki","Kas","Ara"];
  const samAralik = useMemo(() => {
    const v = (sam?.hucreler ?? []).flat().filter((x): x is number => x !== null);
    return v.length ? { lo: Math.min(...v), hi: Math.max(...v) } : { lo: 0, hi: 1 };
  }, [sam]);
  // v2.215 (F "Panel Cami"): iki temali rampa — acikta gok->yesil->amber,
  // koyuda gece laciverti->filiz->amber (parlaklik degerle buyur).
  const koyuTema = typeof document !== "undefined" &&
    document.documentElement.dataset.tema === "koyu";
  // v2.226: duraklar parcalar.tsx'e ortaklandi (Aylik ayni dili konusur)
  const solargisTon = (t: number) => isiTonu(t, koyuTema);
  const piMetin = (t: number) => isiMetni(t, koyuTema);

  const gyOption = useMemo(() => {
    const soluk = oku("--soluk"), kenar = oku("--kenar"), mono = oku("--mono");
    const izgara = oku("--izgara");
    const renk: Record<string, string> = {  // v2.196: sabit hex -> D tokenlari
      yaz: oku("--ch-gy-yaz") || oku("--marka"),
      ekinoks: oku("--ch-gy-eki") || "#6B7570",
      kis: oku("--ch-gy-kis") || "#8A8478" };
    const ad: Record<string, string> = {
      yaz: "Yaz gündönümü", ekinoks: "Ekinoks", kis: "Kış gündönümü" };
    // v2.201: D cizim dili — yay karakterleri ayrisir (yaz duz, ekinoks
    // kesikli, kis noktali); ayni saati mevsimler arasinda izleyen soluk
    // dikmeler; tepe noktasina mevsim etiketi (veriden: en yuksek el.)
    const cizgiTip: Record<string, "solid" | "dashed" | "dotted"> = {
      yaz: "solid", ekinoks: "dashed", kis: "dotted" };
    const egriler = gy?.egriler ?? [];
    const saatDikmeleri: object[] = [];
    const saatler = [...new Set(egriler.flatMap((e) => e.saat.map((p) => p[2])))];
    for (const h of saatler) {
      const pts = egriler
        .map((e) => e.saat.find((p) => p[2] === h))
        .filter((p): p is [number, number, number] => !!p)
        .map((p) => [p[0], p[1]]);
      if (pts.length >= 2)
        saatDikmeleri.push({ type: "line" as const, silent: true, symbol: "none",
          z: 1, tooltip: { show: false },
          lineStyle: { color: izgara, width: 1, type: [2, 3] }, data: pts });
    }
    const tepeEtiketleri = egriler.map((e) => {
      const apex = e.nokta.reduce((a, b) => (b[1] > a[1] ? b : a), e.nokta[0]);
      return { type: "scatter" as const, silent: true, symbolSize: 0.1, z: 5,
        tooltip: { show: false }, itemStyle: { color: "transparent" },
        label: { show: true, position: "bottom" as const, distance: 10,
          color: renk[e.ad], fontFamily: mono, fontSize: 11,
          formatter: `${(ad[e.ad] ?? e.ad).toLowerCase()} · ${Math.round(apex[1])}°` },
        data: [apex] };
    });
    const seriler = [
      ...saatDikmeleri,
      ...egriler.flatMap((e) => [
        { name: ad[e.ad] ?? e.ad, type: "line" as const, symbol: "none",
          smooth: true, z: 3,
          lineStyle: { color: renk[e.ad], width: e.ad === "yaz" ? 2.2 : 2,
            type: cizgiTip[e.ad] ?? "solid" },
          itemStyle: { color: renk[e.ad] }, data: e.nokta },
        { name: ad[e.ad] ?? e.ad, type: "scatter" as const,
          symbolSize: e.ad === "yaz" ? 5 : 4, z: 4,
          itemStyle: { color: e.ad === "yaz" ? oku("--amber") : renk[e.ad] },
          tooltip: { show: true },
          label: { show: e.ad === "yaz", position: "top" as const,
            color: soluk, fontSize: 9.5, fontFamily: mono,
            formatter: (pr: { value: [number, number, number] }) =>
              `${pr.value[2]}:00` },
          data: e.saat },
      ]),
      ...tepeEtiketleri,
    ];
    return {
      grid: { left: 60, right: 16, top: 26, bottom: 46 }, animation: false,
      tooltip: { backgroundColor: oku("--kart"), borderColor: kenar,
        borderWidth: 0.5, textStyle: { color: oku("--metin"), fontSize: 12 },
        formatter: (p0: unknown) => {
          const p1 = p0 as { seriesName: string; value: number[] };
          const saat = p1.value.length > 2 ? ` · ${p1.value[2]}:00` : "";
          return `${p1.seriesName}${saat}<br/>azimut ${Math.round(p1.value[0])}° · yükseklik ${Math.round(p1.value[1])}°`;
        } },
      xAxis: { type: "value", min: 45, max: 315, name: "[panel yönü — azimuth]",
        nameLocation: "middle", nameGap: 30,
        // v2.202: tikler 45'lik adimla — 90/180/270 tam duser, ana yonler okunur
        interval: 45,
        nameTextStyle: { color: soluk, fontFamily: mono, fontSize: 10.5 },
        axisLabel: { color: soluk, fontFamily: mono, fontSize: 10.5,
          formatter: (v: number) =>
            ({ 90: "Doğu · 90°", 180: "Güney · 180°", 270: "Batı · 270°"
             } as Record<number, string>)[v] ?? `${v}°` },
        splitLine: { show: false },
        axisLine: { lineStyle: { color: kenar } } },
      yAxis: { type: "value", min: 0, max: 90, name: "Güneş yüksekliği [°]",
        interval: 30,
        nameLocation: "middle", nameGap: 36, nameRotate: 90,
        nameTextStyle: { color: soluk, fontFamily: mono, fontSize: 10.5 },
        axisLabel: { color: soluk, fontFamily: mono, fontSize: 10.5 },
        splitLine: { lineStyle: { color: izgara } }, axisLine: { show: false } },
      series: seriler,
    } as EChartsOption;  // v2.148: üretim derlemesi literal daraltması
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gy, n]);

  if (!o) return <div style={{ color: "var(--soluk)" }}>Yükleniyor…</div>;

  const s = o.saglik;
  // v2.198 (D ozet seridi): anlik guc = simdiDegeri; gece/veri yokken "—".
  const tavan = seri?.ac_tavani_kw ?? o.ac_tavani_kw ?? null;
  const anlikPay = nowVal !== null && tavan ? Math.max(0, Math.min(1, nowVal / tavan)) : null;
  return (
    <Sayfa baslik={o.ad}
      alt={o.anlati}
      sag={<div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <span className="rozet rozet-ok">{o.model_adi} · Mod {o.mod}</span>
        <span className="mono" style={{ fontSize: 12.5, color: "var(--soluk)" }}>
          {sayiTr(o.kapasite_kwp)} kWp · {o.lat}, {o.lon}
        </span>
      </div>}>

      {/* v2.198 — D "Rapor Odasi" yerlesimi: 1 Ozet seridi (kartsiz), 2 hero
          tam genislik, hava+kunye/saglik cifti, 3 parmak izi, 4 gunes yolu,
          5 yedi gun + 6 aylik. */}
      <div className="ozet-bas"><span className="no">1</span> Özet
        <span className="sag">tümü P50 · gece sınavıyla ayarlı</span></div>
      <div className="ozet">
        <div className="anlik">
          <svg viewBox="0 0 160 112" role="img" style={{ width: "100%", maxWidth: 118 }}
            aria-label={nowVal === null ? "Anlık güç verisi yok"
              : `Anlık güç ${sayiTr(nowVal)} kilovat`}>
            <path d="M18,88 A62,62 0 0 1 142,88" fill="none"
              stroke="var(--izgara)" strokeWidth="10" strokeLinecap="round" />
            {/* pay ~0 iken cizme: round linecap sifirda bile nokta basiyordu */}
            {anlikPay !== null && anlikPay > 0.005 && (
              <path d="M18,88 A62,62 0 0 1 142,88" fill="none"
                stroke="var(--amber)" strokeWidth="10" strokeLinecap="round"
                strokeDasharray={`${(Math.PI * 62 * anlikPay).toFixed(1)} ${(Math.PI * 62).toFixed(1)}`} />
            )}
            <text x="80" y="66" textAnchor="middle" className="ch-gauge-deger">
              {nowVal === null ? "—" : sayiTr(nowVal)}</text>
            <text x="80" y="82" textAnchor="middle" className="ch-t">
              {nowVal === null ? "veri yok" :
                anlikPay === null ? "kW" : `kW · %${sayiTr(anlikPay * 100)}`}</text>
          </svg>
          <div>
            <div className="et">Anlık güç</div>
            <div className="alt">{tavan ? `AC tavanı ${sayiTr(tavan)} kW` : "AC tavanı —"}</div>
            <div className="alt">{nowVal === null
              ? "şimdiyi kapsayan koşu yok" : "son tahmin koşusundan"}</div>
          </div>
        </div>
        <div>
          <div className="et">Bugün — beklenen</div>
          <div className="dg">{sayiTr(o.bugun_kwh ?? 0)} <small>kWh</small></div>
          <div className="alt">gün sonu itibarıyla</div>
        </div>
        <div>
          <div className="et">Yarın</div>
          <div className="dg">{sayiTr(o.yarin_kwh ?? 0)} <small>kWh</small></div>
          <div className="alt">{o.hava[1]
            ? `${sayiTr(o.hava[1].isinim, 1)} kWh/m² ışınım` : "—"}</div>
        </div>
        <div>
          <div className="et">Önümüzdeki 7 gün</div>
          <div className="dg">{sayiTr(o.hafta_mwh ?? 0, 1)} <small>MWh</small></div>
          <div className="alt">döküm §5'te</div>
        </div>
        <div>
          <div className="et">Model durumu</div>
          <div className="md-dizi">
            <div><span className="e">Durum</span>
              <span className="rozet rozet-ok">{o.model_adi} · Mod {o.mod}</span></div>
            <div><span className="e">Yıllık sapma</span>
              <span className="d">%{sayiTr(o.sapma_pct ?? 0, 2)}</span></div>
            <div><span className="e">Son kalibrasyon</span>
              <span className="d">{o.son_kalibrasyon}</span></div>
          </div>
        </div>
      </div>

      <Kart no="2" baslik="Bugün — saatlik üretim"
        sag={<span className="cip">saatlik çözünürlük</span>}
        style={{ marginBottom: 14 }}>
        {seri && dilim && (
          <ProductionForecastChart
            forecast={dilim.saatlik.map((x) => ({
              ts: x.ts, p10: x.p10_kw, p50: x.p50_kw, p90: x.p90_kw,
              p25: x.p25_kw, p75: x.p75_kw }))}
            actual={dilim.saatlik
              .filter((x) => x.gercek_kw !== null)
              .map((x) => ({ ts: x.ts, kw: x.gercek_kw as number }))}
            nowMs={t0}
            nowValue={nowVal}
            gunes={seri.gunes}
            mode="hourly"
            plant={{ acCapacityKw: seri.ac_tavani_kw ?? o.ac_tavani_kw,
                     lat: o.lat, lon: o.lon, timezone: o.tz }}
            features={{ exportButtons: true }}  // v2.215: PNG/CSV — SaaS eylemi
            height={340}
          />
        )}
        <p style={{ fontSize: 12, color: "var(--soluk)", margin: "10px 0 0" }}>
          Gerçekleşen üretimi görmek için bugünün SCADA verisini yükleyin.
        </p>
      </Kart>

      <div className="ızgara" style={{ gridTemplateColumns: "minmax(0,1fr) minmax(0,1fr)",
                                       marginBottom: 14, alignItems: "start" }}>
        <Kart baslik="Hava — önümüzdeki günler"
          sag={<span className="cip">profesyonel meteoroloji verisi</span>}>
          {o.hava.length === 0 && (
            /* v2.90: bos kart sessiz kalmasin — neden bos, soyle */
            <p style={{ fontSize: 12.5, color: "var(--soluk)", margin: 0,
                        lineHeight: 1.65 }}>
              Hava özeti son tahmin koşusundan gelir — bugünü kapsayan
              koşu yok. Yeni koşuyla bu kart kendiliğinden dolar.
            </p>
          )}
          <div className="hava">
            {o.hava.map((h) => (
              <div key={h.etiket} className="hava-kart">
                <div className="hava-gun">{h.etiket}</div>
                <div className="hava-sic mono">{sayiTr(h.sicaklik, 1)}°</div>
                <div className="hava-isin mono">{sayiTr(h.isinim, 1)} kWh/m²</div>
              </div>
            ))}
          </div>
        </Kart>
        <Kart baslik="Künye & veri sağlığı">
          <table className="veri">
            <tbody className="mono">
              <tr><td>DC gücü</td><td>{sayiTr(o.kapasite_kwp)} kWp</td></tr>
              <tr><td>AC tavanı</td><td>{sayiTr(o.ac_tavani_kw ?? 0)} kW</td></tr>
              <tr><td>Eğim / azimut</td><td>{o.egim_azimut}</td></tr>
              <tr><td>Saat dilimi</td><td>{o.tz}</td></tr>
              <tr><td>Son veri yüklemesi</td>
                <td style={{ color: "var(--uyari)" }}>{s.son_scada} · {s.kesinti_gun} gündür yeni veri yok</td></tr>
              <tr><td>İşlenen veri</td><td>{sayiTr(s.islenen_saat)} saatlik ölçüm</td></tr>
              <tr><td>Anomali tespiti</td><td>{sayiTr(s.anomali)} işaretlendi — tek satır silinmedi</td></tr>
              {/* v2.249 (Dalga 1.4): IEC 61724-1 performans orani — olcumden, POA yoksa tire + neden */}
              <tr><td>Performans oranı (30 g)</td>
                <td>{pr?.durum === "ok" && pr.PR != null
                  ? <>%{sayiTr(pr.PR * 100, 1)}{pr.PR_sicaklik != null && ` · sıcaklık düzeltmeli %${sayiTr(pr.PR_sicaklik * 100, 1)}`}
                      <span style={{ color: "var(--soluk)" }}> · {sayiTr(pr.gun)} gün{pr.son_olcum ? `, son ölçüm ${pr.son_olcum}` : ""}</span></>
                  : pr?.durum === "poa_yok"
                    ? <span style={{ color: "var(--soluk)" }}>— düzlem ışınımı (POA) ölçümü {pr.poa_orani != null ? `saatlerin %${sayiTr(pr.poa_orani * 100, 0)}'inde` : "yok"}; PR için en az %95 gerekir</span>
                    : <span style={{ color: "var(--soluk)" }}>— ölçüm birikmedi</span>}</td></tr>
              {/* v2.260 (Dalga 4.13): piyasa segmenti — dengesizliği kim taşır; editor değiştirebilir */}
              <tr><td>Piyasa segmenti</td>
                <td><select className="mono" value={seg?.segment ?? ""} style={{ fontSize: 12.5 }}
                    onChange={(e) => api.segmentAyarla(plantId, e.target.value).then((r) => setSeg({ segment: r.segment, dengesizlik_sahibi: r.dengesizlik_sahibi })).catch(() => {})}>
                    <option value="" disabled>belirtilmedi</option>
                    {SEGMENTLER.map((x) => <option key={x.deger} value={x.deger}>{x.etiket}</option>)}
                  </select>
                  {seg?.dengesizlik_sahibi && <span style={{ color: "var(--soluk)" }}> · dengesizlik: {seg.dengesizlik_sahibi}</span>}</td></tr>
              {/* v2.256 (Dalga 3.11): bozunma ve eğilim — POA yoksa model-normalize verimle; yetersizse neden */}
              <tr><td>Bozunma eğilimi</td>
                <td>{sg?.bozunma_yuzde_yil != null
                  ? <>%{sayiTr(sg.bozunma_yuzde_yil, 2)}/yıl{sg.bozunma_ga && ` (±${sayiTr(Math.abs(sg.bozunma_ga[1] - sg.bozunma_ga[0]) / 2, 2)})`}
                      <span style={{ color: "var(--soluk)" }}> · {sayiTr(sg.ay)} ay</span></>
                  : sg?.egim_yuzde_yil != null
                    ? <>eğilim %{sayiTr(sg.egim_yuzde_yil, 1)}/yıl<span style={{ color: "var(--soluk)" }}> · {sayiTr(sg.gun)} gün · {sg.not || "bozunma için ≥13 ay"}</span></>
                    : <span style={{ color: "var(--soluk)" }}>— {sg?.not || "ölçüm birikmedi"}</span>}</td></tr>
              {/* v2.274 (Dalga 3): fizik terimleri — seçim önce önizlenir (salt fizik, arşiv meteosu), sonra uygulanır */}
              <tr><td>Fizik terimleri</td>
                <td>{ft ? <>
                  {(["iam_model", "spectral_model", "soiling_model", "kar_model"] as const).map((k) => (
                    <label key={k} style={{ display: "inline-flex", gap: 4, alignItems: "center", marginRight: 12, fontSize: 12.5 }} title={ft.not[k] ?? ""}>
                      {ft.etiket[k]}
                      <select className="mono" value={ftSon[k] ?? ft[k]} style={{ fontSize: 12 }} onChange={(e) => ftDegistir(k, e.target.value)}>
                        {ft.secenekler[k].map((s) => <option key={s} value={s}>{s === "none" ? "kapalı" : "açık" + (ft.secenekler[k].length > 2 ? ` (${s.replace("_", " ")})` : "")}</option>)}
                      </select>
                    </label>))}
                  {ftOn && <div style={{ marginTop: 6, fontSize: 12.5 }}>
                    <span className="cip">önizleme · 7 gün salt fizik · {ftOn.toplam_fark_pct == null ? "—" : `%${sayiTr(ftOn.toplam_fark_pct, 2)}`} enerji farkı ({sayiTr(ftOn.toplam_mevcut_kwh / 1000, 1)} → {sayiTr(ftOn.toplam_aday_kwh / 1000, 1)} MWh)</span>
                    {!ftOn.nem_var && <span className="cip" style={{ marginLeft: 6 }}>nem verisi yok → spektral etkisiz</span>}
                    {!ftOn.kar_var && <span className="cip" style={{ marginLeft: 6 }}>kar verisi yok → kar örtüsü etkisiz</span>}
                    <button className="dugme" style={{ marginLeft: 8, fontSize: 11.5 }} onClick={() => { const [k, v] = Object.entries(ftSon)[0] ?? []; if (k) ftUygula(k, String(v)); }}>Uygula</button>
                  </div>}
                  {ftMesaj && <div className="soluk" style={{ marginTop: 4, fontSize: 12.5 }}>{ftMesaj}</div>}
                  </> : <span style={{ color: "var(--soluk)" }}>—</span>}</td></tr>
              {/* v2.265 (Dalga 5.17): ek alarm kuralları — varsayılan iki kural sabit; üçü santral bazında açılır */}
              <tr><td>Alarm kuralları</td>
                <td>{ak ? <>
                  <span style={{ color: "var(--soluk)" }}>veri gelmedi · isabet düştü (sabit)</span>
                  {ak.secilebilir.map((k) => (
                    <label key={k} style={{ display: "inline-flex", gap: 4, alignItems: "center", marginLeft: 10, fontSize: 12.5 }}>
                      <input type="checkbox" checked={ak.secili.includes(k)} onChange={(e) => akDegistir(k, e.target.checked)} />
                      {ak.etiket[k] ?? k}
                      <span style={{ color: "var(--soluk)" }} className="mono">
                        {k === "pr_dustu" ? `<${sayiTr(ak.esik.pr_esik, 2)}` : k === "clipping_orani_yuksek" ? `>%${sayiTr(ak.esik.clipping_esik * 100, 0)}` : `>${sayiTr(ak.esik.iletisim_esik_saat, 0)} s`}
                      </span>
                    </label>))}
                  </> : <span style={{ color: "var(--soluk)" }}>—</span>}</td></tr>
            </tbody>
          </table>
          <p style={{ fontSize: 12.5, color: "var(--ikincil)", margin: "12px 0 0",
                      lineHeight: 1.55 }}>
            Model, en taze verinizle en güçlü hâlindedir. Yeni SCADA dosyanızı
            yükleyin — tahmin o gece kendini yeniden sınar, karneniz büyür.
          </p>
        </Kart>
      </div>

      {sam && sam.saatler.length > 0 && (
        <Kart no="3" baslik="Üretim parmak izi — saat × ay"
          sag={<span className="cip">tüm geçerli SCADA · kW · {sam.tz}</span>}>
          <div style={{ overflowX: "auto" }}>
            <table style={{ borderCollapse: "collapse", width: "100%",
                            fontFamily: "var(--mono)", fontSize: 11.5 }}>
              <thead><tr>
                <th style={{ textAlign: "left", padding: "4px 6px",
                             color: "var(--soluk)", fontWeight: 500 }}></th>
                {AYLAR_K.map((a) => (
                  <th key={a} style={{ padding: "4px 2px", color: "var(--soluk)",
                                       fontWeight: 500 }}>{a}</th>))}
              </tr></thead>
              <tbody>
                {sam.saatler.map((st, si) => (
                  <tr key={st}>
                    <td style={{ padding: "2px 6px", color: "var(--soluk)" }}>{st}</td>
                    {sam.hucreler[si].map((v, mi) => (
                      <td key={mi} style={{ padding: "2px 2px", textAlign: "center",
                        border: "1px solid var(--kart)",
                        color: v === null ? "var(--pi-metin)"
                          : piMetin((v - samAralik.lo) / (samAralik.hi - samAralik.lo)),
                        background: v === null ? "transparent"
                          : solargisTon((v - samAralik.lo) / (samAralik.hi - samAralik.lo)) }}>
                        {v === null ? <span style={{ color: "var(--soluk)" }}>–</span> : v}
                      </td>))}
                  </tr>))}
                <tr style={{ borderTop: "2px solid var(--marka)" }}>
                  <td style={{ padding: "3px 6px", fontWeight: 600,
                               color: "var(--metin)" }}>Tipik gün</td>
                  {sam.toplam.map((v, mi) => (
                    <td key={mi} style={{ padding: "3px 2px", textAlign: "center",
                      fontWeight: 600, color: "var(--metin)" }}>
                      {v === null ? "–" : `${sayiTr(Math.round(v / 100) / 10, 1)}`}
                    </td>))}
                </tr>
              </tbody>
            </table>
          </div>
          <p style={{ fontSize: 12, color: "var(--soluk)", margin: "12px 0 0" }}>
            Hücreler saat×ay çok-yıllı ortalama güç (kW); Tipik gün satırı, o ayın
            karakteristik günlük üretimidir (MWh).
          </p>
        </Kart>
      )}

      {gy && gy.egriler.length > 0 && (
        <Kart no="4" baslik="Güneş yolu — yaz / ekinoks / kış"
          sag={<span className="cip">{gy.lat}°K · {gy.tz}</span>}>
          <EChart option={gyOption} height={300}
            ariaLabel="Azimut ve yükseklik düzleminde yaz gündönümü, ekinoks ve kış gündönümü güneş yolları, saat işaretleriyle" />
          <p style={{ fontSize: 12, color: "var(--soluk)", margin: "12px 0 0" }}>
            Eğriler güneşin gökyüzündeki günlük yolunu gösterir; noktalar saat başlarıdır.
            Panel eğim/azimut kararları ve gölgelenme analizi bu geometriden beslenir.
          </p>
        </Kart>
      )}

      <div className="ızgara" style={{ gridTemplateColumns: "minmax(0,1fr) minmax(0,1fr)",
                                       marginBottom: 14, alignItems: "start" }}>
        <Kart no="5" baslik="7 günlük görünüm" sag={<span className="cip mono">
          {sayiTr(o.hafta_mwh ?? 0, 1)} MWh toplam</span>}>
          {/* v2.200 (D imzasi): profilli tablo — profil gun-ici P50 egrisi,
              tum gunler ayni olcekte; tepe = gunun en yuksek P50 saati */}
          <table className="veri">
            <thead><tr>
              <th>Gün</th><th style={{ textAlign: "left" }}>Profil</th>
              <th>Tepe kW · P50</th><th>Toplam MWh · P50</th>
            </tr></thead>
            <tbody className="mono">
              {o.gunler.map((g, i) => {
                const nk = gunProfilleri?.gunler[i] ?? [];
                const gunTepe = nk.length ? Math.max(...nk) : null;
                return (
                  <tr key={g.etiket}>
                    <td style={{ color: "var(--ikincil)" }}>
                      {i === 0 ? `Bugün · ${g.etiket}` : g.etiket}</td>
                    <td style={{ textAlign: "left" }}>
                      <GunProfili noktalar={nk}
                        tepe={gunProfilleri?.tepe ?? 1} vurgu={i === 0} /></td>
                    <td>{gunTepe === null ? "—" : sayiTr(gunTepe)}</td>
                    <td>{sayiTr(g.mwh, 1)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <p style={{ fontSize: 12, color: "var(--soluk)", margin: "10px 0 0" }}>
            Profiller aynı ölçekte çizilir — kısa görünen gün, düşük beklenen gündür.
          </p>
        </Kart>
        <Kart no="6" baslik="Aylık üretim — gerçekleşen"
          sag={<span className="cip">son 12 ay</span>}>
          {/* v2.205: beklenti-P50 imleci (D bullet dili) — yalniz TAM
              kapsanmis aylarda; imlecin hakemi gun-oncesi arsiv */}
          <Cubuklar etiketler={o.aylik.map((a) => a.ay)} degerler={o.aylik.map((a) => a.mwh)}
            kapsamPct={o.aylik.map((a) => a.kapsam_pct)}
            beklenti={o.aylik.map((a) => a.beklenti_mwh)}
            birim="MWh" vurguIdx={o.aylik.length - 1} yukseklik={230} />
          <table className="veri" style={{ marginTop: 14 }}>
            <thead><tr><th>Ay</th><th>Üretim MWh</th><th>Beklenti MWh</th><th>Sapma</th><th>Kapsam %</th></tr></thead>
            <tbody className="mono">
              {[...o.aylik].reverse().slice(0, 6).map((a) => (
                <tr key={a.ay}>
                  <td>{a.ay}</td><td>{sayiTr(a.mwh, 1)}</td>
                  <td>{a.beklenti_mwh === null ? "—" : sayiTr(a.beklenti_mwh, 1)}</td>
                  <td>{a.beklenti_mwh === null || a.beklenti_mwh === 0 ? "—"
                    : `${a.mwh >= a.beklenti_mwh ? "+" : "−"}%${sayiTr(
                        Math.abs((a.mwh - a.beklenti_mwh) / a.beklenti_mwh) * 100, 1)}`}</td>
                  <td style={{ color: "var(--ikincil)" }}>{sayiTr(a.kapsam_pct, 1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p style={{ fontSize: 12, color: "var(--soluk)", margin: "8px 0 0" }}>
            Beklenti, her gün için gün başlamadan verilmiş en taze tahminin
            toplamıdır; ay tam kapsanmadan gösterilmez.
          </p>
        </Kart>
      </div>
    </Sayfa>
  );
}
