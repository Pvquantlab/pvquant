import { useEffect, useMemo, useState } from "react";
import type { EChartsOption } from "echarts";
import { api } from "../../api/client";
import type { SantralOzeti, TahminSerisi, GunesYolu, SaatAyMatrisi } from "../../api/types";
import { EChart } from "../../lib/EChart";
import { useTema } from "../../lib/useTema";
import { Kpi, Kart, Sayfa, sayiTr } from "../sayfalar/parcalar";
import ProductionForecastChart from "../sayfalar/ProductionForecastChart";
import { t0Hesapla, simdiDegeri, dilimle } from "../sayfalar/tahminPencere";
import { Cubuklar } from "./Cubuklar";

export function Santralim({ plantId }: { plantId: string }) {
  const [o, setO] = useState<SantralOzeti | null>(null);
  const [seri, setSeri] = useState<TahminSerisi | null>(null);
  const [gy, setGy] = useState<GunesYolu | null>(null);
  const [sam, setSam] = useState<SaatAyMatrisi | null>(null);
  const { n, oku } = useTema();
  useEffect(() => { api.ozet(plantId).then(setO); }, [plantId]);
  useEffect(() => { api.tahmin(plantId, "16d").then(setSeri); }, [plantId]); // v2.166: D1 — tam seri cek, istemcide "24h" dilimle (Tahminler kalibi)
  useEffect(() => { api.gunesYolu(plantId).then(setGy).catch(() => {}); }, [plantId]);
  useEffect(() => { api.saatAyMatrisi(plantId).then(setSam).catch(() => {}); }, [plantId]);
  const t0 = useMemo(() => t0Hesapla(Date.now()), []);
  const nowVal = useMemo(
    () => (seri ? simdiDegeri(seri.saatlik, t0) : null), [seri, t0]);
  const dilim = useMemo(
    () => (seri ? dilimle(seri.saatlik, t0, "24h") : null), [seri, t0]);
  const AYLAR_K = ["Oca","Şub","Mar","Nis","May","Haz","Tem","Ağu","Eyl","Eki","Kas","Ara"];
  const samAralik = useMemo(() => {
    const v = (sam?.hucreler ?? []).flat().filter((x): x is number => x !== null);
    return v.length ? { lo: Math.min(...v), hi: Math.max(...v) } : { lo: 0, hi: 1 };
  }, [sam]);
  // v2.196 (D): iki temali rampa — acikta kagit->yesil->amber, koyuda
  // murekkep->filiz->amber (parlaklik degerle buyur; Murekkep-Bakir dersi).
  const koyuTema = typeof document !== "undefined" &&
    document.documentElement.dataset.tema === "koyu";
  const solargisTon = (t: number) => {
    const durak: [number, number, number][] = koyuTema
      ? [[23, 28, 22], [31, 44, 35], [59, 61, 30], [131, 96, 14], [232, 148, 10]]
      : [[233, 244, 238], [199, 227, 212], [240, 226, 189], [232, 148, 10], [178, 106, 8]];
    const k = Math.min(0.999, Math.max(0, t)) * (durak.length - 1);
    const i = Math.floor(k), f = k - i;
    return "rgb(" + durak[i].map((a, c) =>
      Math.round(a + (durak[i + 1][c] - a) * f)).join(",") + ")";
  };
  // parlak amber hucrelerde koyu metin (4.5:1); digerlerinde tema metni
  const piMetin = (t: number) =>
    (koyuTema ? t > 0.55 : t > 0.62) ? "#14100A" : "var(--pi-metin)";

  const gyOption = useMemo(() => {
    const soluk = oku("--soluk"), kenar = oku("--kenar"), mono = oku("--mono");
    const izgara = oku("--izgara");
    const renk: Record<string, string> = {  // v2.196: sabit hex -> D tokenlari
      yaz: oku("--ch-gy-yaz") || oku("--marka"),
      ekinoks: oku("--ch-gy-eki") || "#6B7570",
      kis: oku("--ch-gy-kis") || "#8A8478" };
    const ad: Record<string, string> = {
      yaz: "Yaz gündönümü", ekinoks: "Ekinoks", kis: "Kış gündönümü" };
    const seriler = (gy?.egriler ?? []).flatMap((e) => [
      { name: ad[e.ad] ?? e.ad, type: "line" as const, symbol: "none",
        smooth: true, lineStyle: { color: renk[e.ad], width: 2 },
        itemStyle: { color: renk[e.ad] }, data: e.nokta },
      { name: ad[e.ad] ?? e.ad, type: "scatter" as const, symbolSize: 5,
        itemStyle: { color: renk[e.ad] }, tooltip: { show: true },
        label: { show: e.ad === "yaz", position: "top" as const,
          color: soluk, fontSize: 9, fontFamily: mono,
          formatter: (pr: { value: [number, number, number] }) =>
            `${pr.value[2]}:00` },
        data: e.saat },
    ]);
    return {
      grid: { left: 44, right: 12, top: 30, bottom: 30 }, animation: false,
      legend: { top: 0, right: 0, textStyle: { color: soluk, fontSize: 11 },
        itemWidth: 14, data: Object.values(ad) },
      tooltip: { backgroundColor: oku("--kart"), borderColor: kenar,
        borderWidth: 0.5, textStyle: { color: oku("--metin"), fontSize: 12 },
        formatter: (p0: unknown) => {
          const p1 = p0 as { seriesName: string; value: number[] };
          const saat = p1.value.length > 2 ? ` · ${p1.value[2]}:00` : "";
          return `${p1.seriesName}${saat}<br/>azimut ${Math.round(p1.value[0])}° · yükseklik ${Math.round(p1.value[1])}°`;
        } },
      xAxis: { type: "value", min: 45, max: 315, name: "azimut °",
        nameLocation: "middle", nameGap: 22,
        nameTextStyle: { color: soluk, fontSize: 10 },
        axisLabel: { color: soluk, fontFamily: mono, fontSize: 10,
          formatter: (v: number) =>
            ({ 90: "D", 180: "G", 270: "B" } as Record<number, string>)[v] ?? `${v}°` },
        splitLine: { lineStyle: { color: izgara } },
        axisLine: { lineStyle: { color: kenar } } },
      yAxis: { type: "value", min: 0, max: 90, name: "yükseklik °",
        nameTextStyle: { color: soluk, fontSize: 10 },
        axisLabel: { color: soluk, fontFamily: mono, fontSize: 10 },
        splitLine: { lineStyle: { color: izgara } }, axisLine: { show: false } },
      series: seriler,
    } as EChartsOption;  // v2.148: üretim derlemesi literal daraltması
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gy, n]);

  if (!o) return <div style={{ color: "var(--soluk)" }}>Yükleniyor…</div>;

  const s = o.saglik;
  return (
    <Sayfa baslik={o.ad}
      alt={o.anlati}
      sag={<div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <span className="rozet rozet-ok">{o.model_adi} · Mod {o.mod}</span>
        <span className="mono" style={{ fontSize: 12.5, color: "var(--soluk)" }}>
          {sayiTr(o.kapasite_kwp)} kWp · {o.lat}, {o.lon}
        </span>
      </div>}>

      <div className="ızgara satir-4" style={{ marginBottom: 14 }}>
        <Kpi etiket="Bugün · P50" deger={sayiTr(o.bugun_kwh ?? 0)} birim="kWh"
             alt="gün sonu itibarıyla" />
        <Kpi etiket="Yarın · P50" deger={sayiTr(o.yarin_kwh ?? 0)} birim="kWh"
             alt={o.hava[1]
               ? `${sayiTr(o.hava[1].isinim, 1)} kWh/m² ışınım`
               : "—"} />  {/* v2.90: veri yokken 0,0 uydurma — tire ilkesi */}
        <Kpi etiket="7 gün · P50" deger={sayiTr(o.hafta_mwh ?? 0, 1)} birim="MWh"
             alt="kayan 7 gün" />
        <Kpi etiket="Model durumu" deger={o.model_adi}
             alt={`yıllık sapma %${sayiTr(o.sapma_pct ?? 0, 2)} · son kalibrasyon ${o.son_kalibrasyon}`} />
      </div>

      <div className="ızgara" style={{ gridTemplateColumns: "minmax(0,2.1fr) minmax(0,1fr)",
                                       marginBottom: 14 }}>
        <Kart baslik="Bugün — saatlik üretim">
          {seri && dilim && (
            <ProductionForecastChart
              forecast={dilim.saatlik.map((x) => ({
                ts: x.ts, p10: x.p10_kw, p50: x.p50_kw, p90: x.p90_kw }))}
              actual={dilim.saatlik
                .filter((x) => x.gercek_kw !== null)
                .map((x) => ({ ts: x.ts, kw: x.gercek_kw as number }))}
              nowMs={t0}
              nowValue={nowVal}
              mode="hourly"
              plant={{ acCapacityKw: seri.ac_tavani_kw ?? o.ac_tavani_kw,
                       lat: o.lat, lon: o.lon, timezone: o.tz }}
              height={300}
            />
          )}
          <p style={{ fontSize: 12, color: "var(--soluk)", margin: "10px 0 0" }}>
            Gerçekleşen üretimi görmek için bugünün SCADA verisini yükleyin.
          </p>
        </Kart>

        <div style={{ display: "grid", gap: 14, alignContent: "start" }}>
          <Kart baslik="Hava">
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
          <Kart baslik="Santral künyesi">
            <table className="veri">
              <tbody className="mono">
                <tr><td>DC gücü</td><td>{sayiTr(o.kapasite_kwp)} kWp</td></tr>
                <tr><td>AC tavanı</td><td>{sayiTr(o.ac_tavani_kw ?? 0)} kW</td></tr>
                <tr><td>Eğim / azimut</td><td>{o.egim_azimut}</td></tr>
                <tr><td>Saat dilimi</td><td>{o.tz}</td></tr>
              </tbody>
            </table>
          </Kart>
        </div>
      </div>

      {sam && sam.saatler.length > 0 && (
        <Kart baslik="Üretim parmak izi — saat × ay"
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
        <Kart baslik="Güneş yolu — yaz / ekinoks / kış"
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
                                       marginBottom: 14 }}>
        <Kart baslik="7 günlük görünüm" sag={<span className="cip mono">
          {sayiTr(o.hafta_mwh ?? 0, 1)} MWh toplam</span>}>
          <Cubuklar etiketler={o.gunler.map((g) => g.etiket)}
            degerler={o.gunler.map((g) => g.mwh)} birim="MWh" vurguIdx={0} yukseklik={230} />
        </Kart>
        <Kart baslik="Veri sağlığı">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 16 }}>
            <div>
              <div className="kpi-et">Son veri yüklemesi</div>
              <div className="mono" style={{ fontSize: 17, color: "var(--uyari)" }}>{s.son_scada}</div>
              <div style={{ fontSize: 12, color: "var(--uyari)", marginTop: 3, fontWeight: 500 }}>
                {s.kesinti_gun} gündür yeni veri yok</div>
            </div>
            <div>
              <div className="kpi-et">İşlenen veri</div>
              <div className="mono" style={{ fontSize: 17 }}>{sayiTr(s.islenen_saat)}</div>
              <div style={{ fontSize: 12, color: "var(--soluk)", marginTop: 3 }}>
                saatlik ölçüm, temiz ve hazır</div>
            </div>
            <div>
              <div className="kpi-et">Anomali tespiti</div>
              <div className="mono" style={{ fontSize: 17 }}>{sayiTr(s.anomali)}</div>
              <div style={{ fontSize: 12, color: "var(--soluk)", marginTop: 3 }}>
                işaretlendi — tek satır silinmedi</div>
            </div>
          </div>
          <p style={{ fontSize: 13, color: "var(--ikincil)", margin: "16px 0 0",
                      lineHeight: 1.55 }}>
            Model, en taze verinizle en güçlü hâlindedir. Yeni SCADA dosyanızı
            yükleyin — tahmin o gece kendini yeniden sınar, karneniz büyür.
          </p>
        </Kart>
      </div>

      <Kart baslik="Aylık üretim — gerçekleşen"
        sag={<span className="cip">son 12 ay</span>}>
        <Cubuklar etiketler={o.aylik.map((a) => a.ay)} degerler={o.aylik.map((a) => a.mwh)}
          kapsamPct={o.aylik.map((a) => a.kapsam_pct)}
          birim="MWh" vurguIdx={o.aylik.length - 1} yukseklik={250} />
        <table className="veri" style={{ marginTop: 18 }}>
          <thead><tr><th>Ay</th><th>Üretim MWh</th><th>Sağlam saat</th><th>Kapsam %</th></tr></thead>
          <tbody className="mono">
            {[...o.aylik].reverse().slice(0, 6).map((a) => (
              <tr key={a.ay}>
                <td>{a.ay}</td><td>{sayiTr(a.mwh, 1)}</td>
                <td>{sayiTr(a.saglam_saat)}</td>
                <td style={{ color: "var(--ikincil)" }}>{sayiTr(a.kapsam_pct, 1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Kart>
    </Sayfa>
  );
}
