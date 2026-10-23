import type { ReactNode } from "react";

/** 23.10 yedinci tur — metaveri dizisi: birbirinden farklı kısa bilgiler (sayı, tarih, pencere, durum) orta
 *  noktayla DEĞİL ince dikey ayraçla ayrılır (.meta > span + span::before). Boş/false öğeler atlanır; her öğe
 *  kendi içinde kırılmaz, dizi dar ekranda öğe sınırından sarar. Çip, rozet, telemetri ve vitrin künyesi aynı
 *  bileşeni kullanır — ayırıcı kararı tek yerde. */
export function Meta({ items, className }:
  { items: (ReactNode | null | undefined | false | "")[]; className?: string }) {
  const dolu = items.filter((x) => x !== null && x !== undefined && x !== false && x !== "");
  return (
    <span className={`meta${className ? ` ${className}` : ""}`}>
      {dolu.map((x, i) => <span key={i}>{x}</span>)}
    </span>
  );
}
