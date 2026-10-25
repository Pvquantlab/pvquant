/** 25.10 denetim O1 / 26.10 Faz 6 — denetim ayrıntısı ham JSON yerine «anahtar: değer» çipleri; iç nesneler düzleşir (eski.status),
 *  uzun değer kısaltılır, tamamı başlıkta. Platform (yonetim/ortak) ve müşteri (Kuruluş) aynı bileşeni kullanır. */
const kisalt = (v: unknown): string => {
  const t = typeof v === "string" ? v : JSON.stringify(v);
  return t.length > 48 ? t.slice(0, 45) + "…" : t;
};
const duz = (a: Record<string, unknown>, on = ""): [string, unknown][] =>
  Object.entries(a).flatMap(([k, v]) => v && typeof v === "object" && !Array.isArray(v)
    ? duz(v as Record<string, unknown>, on + k + ".")
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
