import { useSyncExternalStore } from "react";

/** Hero görseli hazır sinyali (16.10 hız turu 3).
 *  Ölçüm (canlı, soğuk önbellek): hero posteri (474 KB) aynı anda inen «Dört adım» levhaları (2×~440 KB)
 *  ve videoyla bant genişliğini paylaştığı için mobil 3G'de 11,0 sn, masaüstü 3G'de 13,7 sn'de iniyordu;
 *  bu sürede hero koyu zeminle duruyordu. Kural: hero bulunan sayfada levhalar ve video, poster inene
 *  (ya da en geç 5 sn) dek bekler. Hero olmayan sayfada (/yontem) beklenecek bir şey yoktur → hemen hazır.
 *  Hero, render sırasında `heroBekle()` çağırır; kardeş bileşenler (DortAdim, IsIzgarasi) aynı geçişte
 *  sonra render olduğundan bekleme durumunu doğru okur. */
let bekleniyor = false;
let hazir = false;
const dinleyiciler = new Set<() => void>();

export function heroBekle(): void { if (!hazir) bekleniyor = true; }
export function heroHazirOldu(): void {
  if (hazir) return;
  hazir = true;
  for (const d of [...dinleyiciler]) d();
}
export function heroHazirMi(): boolean { return hazir || !bekleniyor; }
function abone(d: () => void): () => void { dinleyiciler.add(d); return () => { dinleyiciler.delete(d); }; }
export function heroHazirSoz(): Promise<void> {
  if (heroHazirMi()) return Promise.resolve();
  return new Promise((coz) => { const birak = abone(() => { birak(); coz(); }); });
}
export function useHeroHazir(): boolean {
  return useSyncExternalStore(abone, heroHazirMi, () => true);
}
