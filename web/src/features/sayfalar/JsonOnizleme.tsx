import { useState } from "react";
import type { RaporJson } from "../../api/types";
import { sayiTr } from "./parcalar";

/** v2.351: JSON raporunun panel içi OKUNUR önizlemesi (kullanıcı kararı,
 *  22 Eyl). İndirme ham JSON kalır — bu görünüm dosyanın kendisini değil,
 *  içeriğini insan gözüyle anlatır. Yazı tipi Arial (Solargis raporuyla
 *  hizalı); ham veri kutusu bilerek eş aralıklı kalır (kod, kod gibi görünür).
 *  GİZLİLİK: model/kaynak makine adları görünür ada çevrilir; ham JSON kutusu
 *  kullanıcının kendi indirdiği dosyanın birebir metnidir. */

const ARIAL = 'Arial, "Liberation Sans", Arimo, Helvetica, sans-serif';
const MODEL_AD: Record<string, string> = {
  hybrid_residual: "Hibrit", barhdadi_bennis: "Fizik", backtest: "Geriye dönük",
};
// Kaynak adı görünür dile çevrilir; tanınmayan kod "hava kaynağı" der (anayasa:
// sağlayıcı adları görünür metne girmez, anahtar listesi de yalnız iç kod adı taşır)
const KAYNAK_AD: Record<string, string> = { "acik-nwp": "Açık NWP birleşimi" };

function tr(iso: string, saat = true) {
  const d = new Date(iso);
  const iki = (x: number) => String(x).padStart(2, "0");
  const g = `${iki(d.getDate())}.${iki(d.getMonth() + 1)}.${d.getFullYear()}`;
  return saat ? `${g} ${iki(d.getHours())}:${iki(d.getMinutes())}` : g;
}
const pct = (v: number | null | undefined, n = 1) => (v == null ? "—" : `%${sayiTr(v, n)}`);
const num = (v: number | null | undefined, n = 1) => (v == null ? "—" : sayiTr(v, n));

export function JsonOnizleme({ veri, onKapat }: { veri: RaporJson; onKapat: () => void }) {
  const [saatlikAcik, setSaatlikAcik] = useState(false);
  const [hamAcik, setHamAcik] = useState(false);
  const a = veri.accuracy;
  const q = veri.quality;
  const kpi: [string, string, string][] = [
    ["Dönem toplamı (P50)", `${num(veri.totals.p50_mwh)} MWh`,
      veri.totals.p10_mwh != null ? `aralık ${num(veri.totals.p10_mwh)}–${num(veri.totals.p90_mwh)} MWh` : "bant yok"],
    ["Kapasite faktörü", pct(veri.totals.capacity_factor_pct), "dönem boyunca"],
    ["Özgül verim", `${num(veri.totals.specific_yield_kwh_kwp)} kWh/kWp`, "kurulu güç başına"],
    ["Kalibrasyon MAPE", pct(q.mape_pct), q.hybrid ? `bağımsız test ${pct(q.hybrid.holdout_mape_pct)}` : "—"],
  ];
  const etiket: React.CSSProperties = { fontSize: 11, letterSpacing: "0.06em", textTransform: "uppercase",
    color: "var(--ikincil)", marginBottom: 4 };
  const kutu: React.CSSProperties = { padding: "12px 14px", border: "1px solid var(--cizgi)",
    borderRadius: 10, background: "var(--yuzey)" };

  return (
    <div style={{ fontFamily: ARIAL, fontVariantNumeric: "tabular-nums", lineHeight: 1.5 }}>
      {/* künye şeridi */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline",
        gap: 12, flexWrap: "wrap", marginBottom: 12 }}>
        <div>
          <div style={{ fontSize: 17, fontWeight: 700 }}>{veri.plant.name} — JSON raporu</div>
          <div style={{ fontSize: 12.5, color: "var(--ikincil)" }}>
            {veri.report_id ?? "kimlik yok"} · şema {veri.schema_version} · üretildi {tr(veri.generated_at)}
            {" · "}{MODEL_AD[veri.run.model] ?? "Model"} · Mod {veri.run.mode}
            {" · "}{KAYNAK_AD[veri.run.meteo_source] ?? "hava kaynağı"}
          </div>
        </div>
        <button className="dugme" onClick={onKapat} style={{ fontFamily: ARIAL }}>Kapat</button>
      </div>

      {/* sözleşme — makine-okunur bloğun insan dili */}
      <div style={{ fontSize: 12.5, color: "var(--ikincil)", marginBottom: 14 }}>
        Damga: aralığın {veri.conventions.timestamp === "interval_start" ? "başı" : veri.conventions.timestamp}
        {" · "}adım {veri.conventions.period === "PT1H" ? "1 saat" : veri.conventions.period}
        {" · "}{veri.conventions.timezone}
        {" · "}eksik değer: {veri.conventions.missing === "null" ? "null (uydurulmaz)" : veri.conventions.missing}
        {" · "}{veri.hourly.length} saatlik · {veri.daily.length} günlük satır
      </div>

      {/* KPI'lar */}
      <div style={{ display: "grid", gap: 10, gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
        marginBottom: 14 }}>
        {kpi.map(([et, deger, alt]) => (
          <div key={et} style={kutu}>
            <div style={etiket}>{et}</div>
            <div style={{ fontSize: 22, fontWeight: 700 }}>{deger}</div>
            <div style={{ fontSize: 12, color: "var(--ikincil)" }}>{alt}</div>
          </div>
        ))}
      </div>

      {/* doğruluk */}
      <div style={{ ...kutu, marginBottom: 14 }}>
        <div style={etiket}>Doğruluk karnesi</div>
        {a ? (
          <>
            <div style={{ fontSize: 13, marginBottom: 6 }}>
              Son {a.window_days} gün · son ölçüm {tr(a.last_measured_date + "T12:00:00", false)}
            </div>
            <div style={{ display: "flex", gap: 22, flexWrap: "wrap", fontSize: 13 }}>
              <span><b>{pct(a.wmape_pct)}</b> WMAPE</span>
              <span><b>{pct(a.nmae_pct)}</b> kapasiteye normalize</span>
              <span><b>{pct(a.skill_vs_naive_pct, 0)}</b> naife üstünlük</span>
              <span><b>{pct(a.band_coverage_pct)}</b> bant kapsaması · hedef {pct(a.band_target_pct, 0)}</span>
              <span><b>{a.daily.filter((d) => d.measured).length}</b>/{a.daily.length} gün ölçülü</span>
            </div>
          </>
        ) : (
          <div style={{ fontSize: 13, color: "var(--ikincil)" }}>
            Ölçüm özeti yok — doğruluk bloğu null, uydurulmadı.
          </div>
        )}
      </div>

      {/* günlük tablo */}
      <div style={etiket}>Günlük üretim beklentisi (kWh)</div>
      <table className="veri" style={{ fontFamily: ARIAL, marginBottom: 12 }}>
        <thead><tr><th>Tarih</th><th>P10</th><th>P50</th><th>P90</th></tr></thead>
        <tbody>
          {veri.daily.map((g) => (
            <tr key={g.date}>
              <td>{tr(g.date + "T12:00:00", false)}</td>
              <td>{num(g.p10_kwh, 0)}</td>
              <td><b>{num(g.p50_kwh, 0)}</b></td>
              <td>{num(g.p90_kwh, 0)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* saatlik — katlanır */}
      <button className="dugme" onClick={() => setSaatlikAcik(!saatlikAcik)}
        style={{ fontFamily: ARIAL, marginRight: 8 }}>
        {saatlikAcik ? "Saatlik seriyi gizle" : `Saatlik seriyi göster (${veri.hourly.length} satır)`}
      </button>
      <button className="dugme" onClick={() => setHamAcik(!hamAcik)} style={{ fontFamily: ARIAL }}>
        {hamAcik ? "Ham JSON'u gizle" : "Ham JSON'u göster"}
      </button>
      {saatlikAcik && (
        <div style={{ maxHeight: 340, overflow: "auto", marginTop: 10, border: "1px solid var(--cizgi)",
          borderRadius: 8 }}>
          <table className="veri" style={{ fontFamily: ARIAL, margin: 0 }}>
            <thead><tr><th>Zaman (UTC)</th><th>P10 kW</th><th>P50 kW</th><th>P90 kW</th></tr></thead>
            <tbody>
              {veri.hourly.map((h) => (
                <tr key={h.ts}>
                  <td>{h.ts.replace("T", " ").replace(":00Z", "")}</td>
                  <td>{num(h.p10_kw, 0)}</td>
                  <td><b>{num(h.p50_kw, 0)}</b></td>
                  <td>{num(h.p90_kw, 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {hamAcik && (
        <pre style={{ maxHeight: 340, overflow: "auto", marginTop: 10, padding: 12, fontSize: 11.5,
          border: "1px solid var(--cizgi)", borderRadius: 8, background: "var(--yuzey)" }}>
          {JSON.stringify(veri, null, 2)}
        </pre>
      )}
    </div>
  );
}
