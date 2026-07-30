import type { ReactNode } from "react";

export function Kpi({ etiket, deger, birim }: { etiket: string; deger: string; birim?: string }) {
  return (
    <div className="kpi">
      <div className="kpi-et">{etiket}</div>
      <div className="kpi-dg mono">{deger}</div>
      {birim && <div className="kpi-br">{birim}</div>}
    </div>
  );
}

export function Bolum({ baslik, sag, children }:
  { baslik: string; sag?: ReactNode; children: ReactNode }) {
  return (
    <section className="kart">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div className="eyebrow">{baslik}</div>{sag}
      </div>
      {children}
    </section>
  );
}

export function BosDurum({ baslik, metin }: { baslik: string; metin: string }) {
  return (
    <div style={{ textAlign: "center", padding: "48px 20px", color: "var(--ikincil)" }}>
      <div style={{ fontSize: 15, fontWeight: 500, color: "var(--metin)", marginBottom: 6 }}>{baslik}</div>
      <div style={{ fontSize: 13, maxWidth: 380, margin: "0 auto" }}>{metin}</div>
    </div>
  );
}
