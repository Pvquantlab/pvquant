import { useEffect, useState, type ReactNode } from "react";

export const SAYFALAR = [
  { id: "santralim", ad: "Santralim" },
  { id: "veri", ad: "Veri Yükleme" },
  { id: "kalibrasyon", ad: "Kalibrasyon" },
  { id: "tahminler", ad: "Tahminler" },
  { id: "dogruluk", ad: "Doğruluk" },
  { id: "raporlar", ad: "Raporlar" },
] as const;
export type SayfaId = (typeof SAYFALAR)[number]["id"];

export function Kabuk({ sayfa, setSayfa, santral, children }:
  { sayfa: SayfaId; setSayfa: (s: SayfaId) => void; santral: string; children: ReactNode }) {
  const [koyu, setKoyu] = useState(false);
  useEffect(() => {
    document.documentElement.dataset.tema = koyu ? "koyu" : "acik";
  }, [koyu]);

  const bugun = new Date().toLocaleDateString("tr-TR",
    { day: "numeric", month: "short", year: "numeric", weekday: "short" });

  return (
    <div className="kabuk">
      <nav className="yan">
        <div className="marka-satir">
          <span style={{ width: 22, height: 22, borderRadius: 6, background: "var(--marka)",
            display: "grid", placeItems: "center", fontSize: 13 }}>P</span>
          PVQuant
        </div>
        <div style={{ padding: "0 10px 14px" }}>
          <div style={{ fontSize: 11, color: "var(--yan-metin)", marginBottom: 5 }}>Santral</div>
          <select defaultValue={santral} style={{ width: "100%", padding: "7px 9px",
            borderRadius: 8, background: "var(--yan-aktif)", color: "#fff",
            border: "0.5px solid rgba(255,255,255,.12)", fontSize: 13,
            fontFamily: "var(--font)" }}>
            <option>{santral}</option>
            <option>Smoke GES</option>
          </select>
        </div>
        {SAYFALAR.map((s) => (
          <button key={s.id} className="nav-btn" onClick={() => setSayfa(s.id)}
            aria-current={sayfa === s.id ? "page" : undefined}>{s.ad}</button>
        ))}
        <div style={{ marginTop: "auto", padding: "16px 10px 0", borderTop: "0.5px solid rgba(255,255,255,.08)" }}>
          <div style={{ fontSize: 12, color: "#fff", fontWeight: 500 }}>Meridyen Enerji</div>
          <div style={{ fontSize: 11, color: "var(--yan-metin)" }}>Admin</div>
        </div>
      </nav>

      <main>
        <header className="ust">
          <div style={{ fontSize: 13, color: "var(--ikincil)" }}>
            Santral <b style={{ color: "var(--metin)" }}>{santral}</b>
            <span className="mono" style={{ color: "var(--soluk)", marginLeft: 14 }}>{bugun}</span>
          </div>
          <button className="tema-btn" onClick={() => setKoyu(!koyu)}>
            {koyu ? "Açık tema" : "Koyu tema"}
          </button>
        </header>
        <div className="icerik">{children}</div>
      </main>
    </div>
  );
}
