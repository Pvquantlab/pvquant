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

/** 18.10 levha kuyruğu sinyali (perf/cross-browser): hero videosu, levha önden indirmesinin (useCanlandir; ana sayfada
 *  8 Storyset PNG, 2.525.490 B) bitişini bekler — ikisi aynı anda başlayınca bandı paylaşıyordu (20 Mbps'te kartların
 *  tamamlanması Firefox'ta 1,7 → 5,2 sn, mobilde üç motorda +1,4–2,7 sn; perf/analiz/ab). Her açılış yeni kuyruktur
 *  (levhaKuyruguBasladi; SPA dönüşünde eski «bitti» taşınmaz); kuyruk kurulmayan her çıkışta sinyal hemen verilir.
 *  Zaman aşımı Hero.tsx'te (LEVHA_BEKLEME_MS). */
let levhaBitti = false;
const levhaDinleyiciler = new Set<() => void>();
export function levhaKuyruguBasladi(): void { levhaBitti = false; }
export function levhalarBittiOldu(): void {
  if (levhaBitti) return;
  levhaBitti = true;
  for (const d of [...levhaDinleyiciler]) d();
  levhaDinleyiciler.clear();
}
export function levhalarBittiSoz(): Promise<void> {
  if (levhaBitti) return Promise.resolve();
  return new Promise<void>((coz) => { levhaDinleyiciler.add(() => coz()); });
}
/** Abonelik + bırakma (Hero sökülünce dinleyici kümede kalmasın). Sinyal zaten verildiyse hemen çağırır. */
export function levhalarBittiAbone(d: () => void): () => void {
  if (levhaBitti) { d(); return () => {}; }
  levhaDinleyiciler.add(d);
  return () => { levhaDinleyiciler.delete(d); };
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
/** 21.10 (canlı bulgu): «yavaş» kaydı poster önbellekten geldiği sürece (1 yıl, immutable) hiç yenilenmiyordu — DevTools
 *  kısıtlamasıyla yapılan tek bir ölçüm 7 gün boyunca videoyu kapatıyordu (kullanıcı: gizli pencerede oynuyor, normalde
 *  oynamıyor). Kural değişmedi (2 sn, 7 gün); kayıttan okunan «yavaş» karar artık günde en çok bir kez, posteri önbelleği
 *  atlayarak yeniden indirip (474 KB) sınanır — hatiYenidenOlc. Gerçek yavaş hatta sonuç yine «yavaş» (p damgası, 24 sa
 *  tekrar yok); hızlanmış/yanlış kayıt ilk ziyarette düzelir. Yalnız kayıttan okunan karar sınanır: bu açılışta ağdan
 *  ölçüldüyse (poster yeni ya da önbellek düşmüş) ölçüm kesindir, ikinci indirme yapılmaz. */
const YAVAS_YENIDEN_MS = 24 * 3600 * 1000;
type YavasKaydi = { y?: boolean; t?: number; p?: number };
let sonKararKayittan = false;
function kayitOku(): YavasKaydi | null {
  try { return JSON.parse(localStorage.getItem(YAVAS_KAYIT) ?? "null") as YavasKaydi | null; } catch { return null; }
}
export function hatYavasKayitli(): boolean {
  const k = kayitOku();
  return !!k && k.y === true && typeof k.t === "number" && Date.now() - k.t < YAVAS_OMUR_MS;
}
function kaydet(y: boolean, p?: number): boolean {
  try { localStorage.setItem(YAVAS_KAYIT, JSON.stringify(p === undefined ? { y, t: Date.now() } : { y, t: Date.now(), p })); } catch { /* depo yok */ }
  return y;
}
export function posterYavasMi(adres: string): boolean {
  sonKararKayittan = false;
  let g: PerformanceResourceTiming[] = [];
  try { g = performance.getEntriesByName(adres, "resource") as PerformanceResourceTiming[]; } catch { /* RT yok */ }
  const e = g.find((x) => x.responseEnd > 0 && x.encodedBodySize > 0 && x.transferSize >= x.encodedBodySize);
  if (e) return kaydet(e.responseEnd - e.startTime > YAVAS_POSTER_MS);
  const eski = g.find((x) => x.responseEnd > 0 && typeof x.transferSize !== "number");
  if (eski && eski.responseEnd - eski.startTime > YAVAS_POSTER_MS) return kaydet(true);
  sonKararKayittan = true;
  return hatYavasKayitli();
}
/** Son posterYavasMi kararı ağ ölçümünden değil, eski kayıttan mı geldi? (Hero: yalnız o zaman yeniden ölçülür.) */
export function yavasKararKayittan(): boolean { return sonKararKayittan; }
/** Kayıttaki «yavaş» kararını sınar: posteri önbelleksiz indirir, 2 sn kuralını uygular, kaydı (p damgasıyla) yeniler.
 *  Günde bir: p üzerinden 24 saat geçmediyse indirmeden «yavaş» döner. Ağ hatasında kayıt değişmez, «yavaş» döner. */
export async function hatiYenidenOlc(adres: string): Promise<boolean> {
  const k = kayitOku();
  if (k && typeof k.p === "number" && Date.now() - k.p < YAVAS_YENIDEN_MS) return true;
  const t0 = performance.now();
  try {
    const r = await fetch(adres, { cache: "reload", credentials: "omit" });
    if (!r.ok) return true;
    await r.arrayBuffer();
  } catch { return true; }
  return kaydet(performance.now() - t0 > YAVAS_POSTER_MS, Date.now());
}
