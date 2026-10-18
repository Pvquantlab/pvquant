import { useSyncExternalStore } from "react";

/** Hero görseli hazır sinyali (16.10 hız turu 3).
 *  Ölçüm (canlı, soğuk önbellek): hero posteri (474 KB) aynı anda inen «Dört adım» levhaları (2×~440 KB)
 *  ve videoyla bant genişliğini paylaştığı için mobil 3G'de 11,0 sn, masaüstü 3G'de 13,7 sn'de iniyordu;
 *  bu sürede hero koyu zeminle duruyordu. Kural: hero bulunan sayfada levhalar ve video, poster inene
 *  (ya da en geç 5 sn) dek bekler. Hero olmayan sayfada (/yontem) beklenecek bir şey yoktur → hemen hazır;
 *  /yontem#para'da sahne levhası aynı rolü üstlenir (TurkiyePiyasasi.tsx, 16.10 hız turu 4).
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

/** K1 yavaş hat kararı (16.10 kullanıcı kuralı): posteri AĞDAN 2 sn'den uzun sürede indiren hatta video inmez,
 *  karar 7 gün hatırlanır. 18.10 (kök neden H13): kararı YALNIZ gövde baytları gerçekten aktarılmış ölçüm yazar —
 *  transferSize ≥ encodedBodySize > 0 (ağdan 200: gövde + başlık; ölçüldü Chromium/Firefox 485 432, WebKit 485 720 B;
 *  304'te transferSize yalnız başlıktır, ~300). Önbellek biçimleri kaydı yalnız OKUR: Firefox bellek önbelleği
 *  (RT girdisi yok), WebKit bellek önbelleği (0/0/0), Chromium bellek/disk (aktarım 0), 304; disk önbelleğinin
 *  Firefox/WebKit biçimi ölçülmedi — gövde aktarılmadığı sürece o da yalnız okur.
 *  Bayt alanı olmayan eski Safari'de yalnız «yavaş» sonucu yazılır: 2 sn süren önbellek isabeti olmaz, ama hızlı
 *  sonuç önbellekten de gelmiş olabilir. Ölçümü Hero.tsx posterYuklendi (onLoad) çağırır; işlev burada durur çünkü
 *  Hero.tsx video/görsel içe aktarır — node testi davranışı doğrudan sınar (test/vitrin/hiz.test.ts). */
const YAVAS_POSTER_MS = 2000;
const YAVAS_KAYIT = "pvq_yavas_hat";
const YAVAS_OMUR_MS = 7 * 24 * 3600 * 1000;
export function hatYavasKayitli(): boolean {
  try {
    const k = JSON.parse(localStorage.getItem(YAVAS_KAYIT) ?? "null") as { y?: boolean; t?: number } | null;
    return !!k && k.y === true && typeof k.t === "number" && Date.now() - k.t < YAVAS_OMUR_MS;
  } catch { return false; }
}
function kaydet(y: boolean): boolean {
  try { localStorage.setItem(YAVAS_KAYIT, JSON.stringify({ y, t: Date.now() })); } catch { /* depo yok */ }
  return y;
}
export function posterYavasMi(adres: string): boolean {
  let g: PerformanceResourceTiming[] = [];
  try { g = performance.getEntriesByName(adres, "resource") as PerformanceResourceTiming[]; } catch { /* RT yok */ }
  const e = g.find((x) => x.responseEnd > 0 && x.encodedBodySize > 0 && x.transferSize >= x.encodedBodySize);
  if (e) return kaydet(e.responseEnd - e.startTime > YAVAS_POSTER_MS);
  const eski = g.find((x) => x.responseEnd > 0 && typeof x.transferSize !== "number");
  if (eski && eski.responseEnd - eski.startTime > YAVAS_POSTER_MS) return kaydet(true);
  return hatYavasKayitli();
}
