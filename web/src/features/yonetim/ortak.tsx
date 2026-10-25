import { zamanTr } from "../../api/yonetim";

/** 25.10 denetim tablo turu (O1/O3) — platform tablolarının ortak hücre bileşenleri.
 *  Zaman: tek tipografi (mono, tabular; CSS .zaman). AyrintiCipleri: denetim ayrıntısı ham JSON yerine anahtar: değer çipleri. */
export function Zaman({ s, sar }: { s: string | null | undefined; sar?: boolean }) {
  return <span className={sar ? "zaman zaman--sar" : "zaman"}>{zamanTr(s)}</span>;   // sar: dar hücrede tarih/saat iki satıra kırılabilir
}

const kisalt = (v: unknown): string => {
  const t = typeof v === "string" ? v : JSON.stringify(v);
  return t.length > 48 ? t.slice(0, 45) + "…" : t;
};
const duz = (a: Record<string, unknown>, on = ""): [string, unknown][] =>
  Object.entries(a).flatMap(([k, v]) => v && typeof v === "object" && !Array.isArray(v)
    ? duz(v as Record<string, unknown>, on + k + ".")           // {eski:{status:…}} → eski.status (tek düzey yeter; derinler de açılır)
    : [[on + k, v] as [string, unknown]]);
export function AyrintiCipleri({ a }: { a: Record<string, unknown> }) {
  const g = duz(a);
  if (g.length === 0) return <span className="bos">—</span>;
  return (
    <span className="plat-ayrinti">
      {g.map(([k, v]) => { const tam = typeof v === "string" ? v : JSON.stringify(v); return (
        <span key={k} className="plat-ayrinti__cip" title={`${k}: ${tam}`}><b>{k}</b>{kisalt(v)}</span>); })}
    </span>
  );
}
