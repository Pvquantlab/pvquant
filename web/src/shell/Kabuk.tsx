import { useEffect, useState, type ReactNode } from "react";
import { api } from "../api/client";
import { sayiTr } from "../features/sayfalar/parcalar";

export const SAYFALAR = [
  { id: "santralim", ad: "Santralim" },
  { id: "veri", ad: "Veri yükleme" },
  { id: "kalibrasyon", ad: "Kalibrasyon" },
  { id: "tahminler", ad: "Tahminler" },
  { id: "dogruluk", ad: "Doğruluk" },
  { id: "aylik", ad: "Aylık beklenti" },
  { id: "raporlar", ad: "Raporlar" },
] as const;
export type SayfaId = (typeof SAYFALAR)[number]["id"];

/* v2.196 — D "Rapor Odasi": 1.5px cizgi SVG ikonlar (emoji yasak). */
const IKON_ORTAK = { width: 15, height: 15, viewBox: "0 0 20 20", fill: "none",
  stroke: "currentColor", strokeWidth: 1.5, strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const, "aria-hidden": true as const };
const IKONLAR: Record<SayfaId, ReactNode> = {
  santralim: <svg {...IKON_ORTAK}><rect x="3" y="3" width="6" height="6" rx="1"/><rect x="11" y="3" width="6" height="6" rx="1"/><rect x="3" y="11" width="6" height="6" rx="1"/><rect x="11" y="11" width="6" height="6" rx="1"/></svg>,
  veri: <svg {...IKON_ORTAK}><path d="M10 3v9M6.5 8.5 10 12l3.5-3.5"/><path d="M4 14v2.5h12V14"/></svg>,
  kalibrasyon: <svg {...IKON_ORTAK}><circle cx="10" cy="10" r="6.5"/><path d="M10 6.5V10l2.5 1.5"/></svg>,
  tahminler: <svg {...IKON_ORTAK}><path d="M3 15l4-5 3 3 4-6 3 4"/></svg>,
  dogruluk: <svg {...IKON_ORTAK}><path d="M4 3h12v14H4z"/><path d="M7.5 10l1.8 1.8 3.2-3.6"/></svg>,
  aylik: <svg {...IKON_ORTAK}><rect x="3" y="4" width="14" height="13" rx="1.5"/><path d="M3 8h14M7 4V2.5M13 4V2.5"/></svg>,
  raporlar: <svg {...IKON_ORTAK}><path d="M5 2.5h7L16 6v11.5H5z"/><path d="M12 2.5V6h4"/></svg>,
};

/** Marka isareti: 1.5px stroke gunes (Vitrin'dekiyle ayni dil). */
function GunesLogo() {
  return (
    <svg width="22" height="22" viewBox="0 0 20 20" aria-hidden="true">
      <circle cx="10" cy="10" r="3.4" fill="none" stroke="var(--marka)" strokeWidth="1.5" />
      <g stroke="var(--marka)" strokeWidth="1.5" strokeLinecap="round">
        {[0, 45, 90, 135, 180, 225, 270, 315].map((a) => {
          const k = (a * Math.PI) / 180;
          return <line key={a}
            x1={10 + 5.8 * Math.cos(k)} y1={10 + 5.8 * Math.sin(k)}
            x2={10 + 7.8 * Math.cos(k)} y2={10 + 7.8 * Math.sin(k)} />;
        })}
      </g>
    </svg>
  );
}

export function Kabuk({ sayfa, setSayfa, santral, plantId, onCikis, children }:
  { sayfa: SayfaId; setSayfa: (s: SayfaId) => void; santral: string;
    plantId?: string; onCikis?: () => void; children: ReactNode }) {
  const [koyu, setKoyu] = useState(false);
  // v2.196: yan-ozet kutulari — kurulu guc gercek veriden; gelene dek "—"
  const [kwp, setKwp] = useState<number | null>(null);
  useEffect(() => { document.documentElement.dataset.tema = koyu ? "koyu" : "acik"; }, [koyu]);
  useEffect(() => {
    if (plantId) api.ozet(plantId).then((o) => setKwp(o.kapasite_kwp)).catch(() => {});
  }, [plantId]);
  const bugun = new Date().toLocaleDateString("tr-TR",
    { day: "numeric", month: "short", year: "numeric", weekday: "short" });

  return (
    <div className="kabuk">
      <nav className="yan">
        <div className="logo"><GunesLogo />PVQuant</div>
        <div className="yan-etiket">Santral</div>
        <select className="yan-secim" defaultValue={santral}>
          <option>{santral}</option><option>Smoke GES</option>
        </select>
        <div className="yan-ozet">
          <div><div className="et">Santral</div><div className="dg">1</div></div>
          <div><div className="et">Kurulu güç</div>
            <div className="dg">{kwp === null ? "—" : `${sayiTr(kwp)} kWp`}</div></div>
        </div>
        {SAYFALAR.map((s) => (
          <button key={s.id} className="nav-btn" onClick={() => setSayfa(s.id)}
            aria-current={sayfa === s.id ? "page" : undefined}>
            {IKONLAR[s.id]}{s.ad}
          </button>
        ))}
        <div className="yan-alt">
          <div style={{ fontSize: 12.5, color: "var(--metin)", fontWeight: 600 }}>Meridyen Enerji</div>
          <div style={{ fontSize: 11.5, color: "var(--yan-metin)" }}>Admin</div>
          {onCikis && (
            <button onClick={onCikis}
              style={{ marginTop: 8, background: "none", border: "none", padding: 0,
                       fontSize: 11.5, color: "var(--yan-metin)", cursor: "pointer",
                       textDecoration: "underline" }}>
              Çıkış yap
            </button>
          )}
        </div>
      </nav>
      <main>
        <header className="ust">
          <div style={{ fontSize: 13, color: "var(--ikincil)" }}>
            Panel <b style={{ color: "var(--metin)" }}>· {santral}</b>
            <span className="mono" style={{ color: "var(--soluk)", marginLeft: 14 }}>{bugun}</span>
          </div>
          <button className="dugme" onClick={() => setKoyu(!koyu)}>
            {koyu ? "Açık tema" : "Koyu tema"}
          </button>
        </header>
        <div className="icerik">{children}</div>
      </main>
    </div>
  );
}
