import { useEffect, useState, type ReactNode } from "react";

export const SAYFALAR = [
  { id: "santralim", ad: "Santralim" },
  { id: "veri", ad: "Veri yükleme" },
  { id: "kalibrasyon", ad: "Kalibrasyon" },
  { id: "tahminler", ad: "Tahminler" },
  { id: "dogruluk", ad: "Doğruluk" },
  { id: "raporlar", ad: "Raporlar" },
] as const;
export type SayfaId = (typeof SAYFALAR)[number]["id"];

export function Kabuk({ sayfa, setSayfa, santral, children }:
  { sayfa: SayfaId; setSayfa: (s: SayfaId) => void; santral: string; children: ReactNode }) {
  const [koyu, setKoyu] = useState(false);
  useEffect(() => { document.documentElement.dataset.tema = koyu ? "koyu" : "acik"; }, [koyu]);
  const bugun = new Date().toLocaleDateString("tr-TR",
    { day: "numeric", month: "short", year: "numeric", weekday: "short" });

  return (
    <div className="kabuk">
      <nav className="yan">
        <div className="logo"><span className="logo-kare">P</span>PVQuant</div>
        <div className="yan-etiket">Santral</div>
        <select className="yan-secim" defaultValue={santral}>
          <option>{santral}</option><option>Smoke GES</option>
        </select>
        {SAYFALAR.map((s) => (
          <button key={s.id} className="nav-btn" onClick={() => setSayfa(s.id)}
            aria-current={sayfa === s.id ? "page" : undefined}>{s.ad}</button>
        ))}
        <div className="yan-alt">
          <div style={{ fontSize: 12.5, color: "#fff", fontWeight: 500 }}>Meridyen Enerji</div>
          <div style={{ fontSize: 11.5, color: "var(--yan-metin)" }}>Admin</div>
        </div>
      </nav>
      <main>
        <header className="ust">
          <div style={{ fontSize: 13, color: "var(--ikincil)" }}>
            Santral <b style={{ color: "var(--metin)" }}>{santral}</b>
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
