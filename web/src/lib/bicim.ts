/** 24.10 performans turu — Intl biçimleyici önbelleği. `new Intl.DateTimeFormat/NumberFormat` kurmak pahalıdır
 *  (yüzlerce µs); saat serisi döngülerinde nokta başına yeniden kuruluyordu (Santralim gün gruplaması 384 nokta × 2:
 *  4× CPU'da 145 ms tek işlev). Aynı yerel ayar + seçenek için tek nesne; biçim sonucu birebir aynı. */
const tarihler = new Map<string, Intl.DateTimeFormat>();
const sayilar = new Map<string, Intl.NumberFormat>();
export function tarihBicimi(yerel: string, secenek: Intl.DateTimeFormatOptions): Intl.DateTimeFormat {
  const k = yerel + JSON.stringify(secenek);
  let b = tarihler.get(k);
  if (!b) { b = new Intl.DateTimeFormat(yerel, secenek); tarihler.set(k, b); }
  return b;
}
export function sayiBicimi(yerel: string, secenek: Intl.NumberFormatOptions): Intl.NumberFormat {
  const k = yerel + JSON.stringify(secenek);
  let b = sayilar.get(k);
  if (!b) { b = new Intl.NumberFormat(yerel, secenek); sayilar.set(k, b); }
  return b;
}
