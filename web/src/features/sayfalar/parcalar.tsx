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
    ton?: "amber" | "uyari" }) {
  // v2.124: opsiyonel uyari tonu — negatif iyilesme gibi "dikkat" KPI'lari
  // icin; verilmezse davranis birebir eski hali (geriye uyumlu).
  // v2.264: "uyari" tonu — amber gerçekleşen mürekkebi olduğundan, açık alarm/gecikme gibi
  // dikkat KPI'ları kırmızı --uyari ailesini kullanır.
  const st = ton === "amber"
    ? { borderColor: "var(--amber)",
        background: "linear-gradient(180deg, var(--amber-zemin) 0%, var(--kart) 72%)" }
    : ton === "uyari"
    ? { borderColor: "var(--uyari)",
        background: "linear-gradient(180deg, var(--uyari-zemin) 0%, var(--kart) 72%)" }
    : undefined;
  return (
    <div className="kpi" style={st}>
      <div className="kpi-et">{etiket}</div>
      <div className="kpi-dg mono"
           style={ton === "amber" ? { color: "var(--amber-metin)" } : ton === "uyari" ? { color: "var(--uyari)" } : undefined}>{deger}{birim &&
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

/* v2.226 — ISI RAMPASI (F "Panel Cami", v2.215 duraklari): Santralim'in
 * parmak-izi matrisiyle Aylik'in yil×ay matrisi AYNI dili konussun diye
 * ortaklandi. Acikta gok→amber, koyuda gece laciverti→filiz→amber
 * (parlaklik degerle buyur). t: 0..1 normalize deger. */
export function isiTonu(t: number, koyu: boolean): string {
  const durak: [number, number, number][] = koyu
    ? [[16, 27, 44], [27, 58, 49], [76, 83, 27], [169, 119, 10], [232, 148, 10]]
    : [[237, 243, 250], [212, 231, 227], [232, 227, 194], [232, 148, 10], [178, 106, 8]];
  const k = Math.min(0.999, Math.max(0, t)) * (durak.length - 1);
  const i = Math.floor(k), f = k - i;
  return "rgb(" + durak[i].map((a, c) =>
    Math.round(a + (durak[i + 1][c] - a) * f)).join(",") + ")";
}

/** Parlak amber hucrelerde koyu metin (4.5:1); digerlerinde tema metni. */
export function isiMetni(t: number, koyu: boolean): string {
  return (koyu ? t > 0.55 : t > 0.62) ? "#14100A" : "var(--pi-metin)";
}
