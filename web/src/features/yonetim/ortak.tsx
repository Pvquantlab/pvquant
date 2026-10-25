import { zamanTr } from "../../api/yonetim";
import { sayiTr } from "../sayfalar/parcalar";

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

/** 26.10 Faz 5 — kullanım/limit rozeti (UYARI kipi, zorlama yok): limit null → «sınırsız» soluk; ≥ %100 «aşıldı»; ≥ %80 uyarı; altı sakin. */
export function LimitRozet({ kullanim, limit }: { kullanim: number; limit: number | null | undefined }) {
  if (limit == null) return <span className="soluk" title="plan sınırsız">{sayiTr(kullanim)}</span>;
  const oran = limit === 0 ? (kullanim > 0 ? 2 : 0) : kullanim / limit;
  const sinif = oran >= 1 ? "rozet-uyari" : oran >= 0.8 ? "rozet-uyari plat-rozet-sari" : "rozet-notr";
  return <span className={`rozet rozet-kucuk ${sinif}`} title={oran >= 1 ? "plan limiti aşıldı (uyarı; kısıt yok)" : `plan limiti ${sayiTr(limit)}`}>{sayiTr(kullanim)} / {sayiTr(limit)}{oran >= 1 && " aşıldı"}</span>;
}
