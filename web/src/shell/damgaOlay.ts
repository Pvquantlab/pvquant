/** 26.10 eşzamanlama — damga (değişim damgası) olay kanalı: Kabuk'taki useDamga «değişti» deyince yayar; sayfalar
 *  useDamgaSurumu ile abone olur ve veri efektlerini yeniden koşar. Modül düzeyi, bağlam gerekmez; test edilebilir. */
import { useEffect, useState } from "react";

type Dinleyici = () => void;
const dinleyiciler = new Set<Dinleyici>();
let surum = 0;

export function damgaYay(): void { surum += 1; for (const d of dinleyiciler) d(); }
export function damgaSurumu(): number { return surum; }
export function damgaDinle(d: Dinleyici): () => void { dinleyiciler.add(d); return () => { dinleyiciler.delete(d); }; }

/** Sayfa kancası: damga her değiştiğinde artan sayı; efekt bağımlılığına eklenir. */
export function useDamgaSurumu(): number {
  const [s, setS] = useState(surum);
  useEffect(() => damgaDinle(() => setS(damgaSurumu())), []);
  return s;
}
