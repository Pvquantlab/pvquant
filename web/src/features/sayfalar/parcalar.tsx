import type { ReactNode } from "react";

/** v2.85: Intl, sayinin kisa ondalik yazimindan yuvarlar (212.95 -> "213,0");
 *  Python/Streamlit ikili degerden yuvarlar (-> 212,9). Iki panel ayni sayiyi
 *  soylesin diye once toFixed ile ikili degerde yuvarlanir, sonra bicimlenir.
 *  (Serh: tam ikili dugumde — orn. 2.5 — JS yarim-yukari, Python cift-e; olculmus
 *  toplamlarda dogmaz.) */
export const sayiTr = (x: number, ondalik = 0): string =>
  new Intl.NumberFormat("tr-TR", { minimumFractionDigits: ondalik,
                                   maximumFractionDigits: ondalik })
    .format(Number(x.toFixed(ondalik)));

export function Kpi({ etiket, deger, birim, alt, ton }:
  { etiket: string; deger: string; birim?: string; alt?: ReactNode;
    ton?: "amber" }) {
  // v2.124: opsiyonel uyari tonu — negatif iyilesme gibi "dikkat" KPI'lari
  // icin; verilmezse davranis birebir eski hali (geriye uyumlu).
  const st = ton === "amber"
    ? { borderColor: "var(--amber)",
        background: "linear-gradient(180deg, var(--amber-zemin) 0%, var(--kart) 72%)" }
    : undefined;
  return (
    <div className="kpi" style={st}>
      <div className="kpi-et">{etiket}</div>
      <div className="kpi-dg mono"
           style={ton === "amber" ? { color: "var(--amber-metin)" } : undefined}>{deger}{birim &&
        <span style={{ fontSize: 13, color: "var(--soluk)", marginLeft: 5 }}>{birim}</span>}</div>
      {alt && <div className="kpi-br">{alt}</div>}
    </div>
  );
}

export function Kart({ baslik, no, sag, children, ...rest }:
  { baslik?: string; no?: string; sag?: ReactNode; children: ReactNode } & { style?: React.CSSProperties }) {
  // v2.196: opsiyonel "no" — D dilinin numarali bolum basligi ("2 · BUGÜN...")
  return (
    <section className="kart" {...rest}>
      {(baslik || sag) && <div className="kart-bas">
        <h3>{no && <span className="kart-no">{no}</span>}{baslik}</h3>{sag}</div>}
      {children}
    </section>
  );
}

export function Sayfa({ baslik, alt, sag, children }:
  { baslik: string; alt?: string; sag?: ReactNode; children: ReactNode }) {
  return (
    <>
      <div style={{ display: "flex", justifyContent: "space-between",
                    alignItems: "flex-start", gap: 20, marginBottom: 20 }}>
        <div>
          <h1 style={{ fontSize: 24 }}>{baslik}</h1>
          {alt && <p style={{ fontSize: 13, color: "var(--ikincil)", margin: "5px 0 0" }}>{alt}</p>}
        </div>
        {sag}
      </div>
      {children}
    </>
  );
}

export function Lejant({ ogeler }: { ogeler: { renk: string; ad: string; kesik?: boolean }[] }) {
  return (
    <div className="lejant">
      {ogeler.map((o) => (
        <span key={o.ad}>
          {o.kesik
            ? <span style={{ width: 14, borderTop: `2px dashed ${o.renk}` }} />
            : <span className="nokta" style={{ background: o.renk }} />}
          {o.ad}
        </span>
      ))}
    </div>
  );
}
