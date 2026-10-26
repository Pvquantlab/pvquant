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


/** 26.10 ortak sözlük — göreli yaş: «3 dk önce», «10 saat önce», «2 gün önce» (iki panel aynı eşikler: 60 dk, 48 saat). */
export function yasTr(s: string | null | undefined, simdi = Date.now()): string {
  if (!s) return "—";
  const dk = Math.max(0, Math.round((simdi - new Date(s).getTime()) / 60000));
  if (dk < 60) return `${dk} dk önce`;
  if (dk < 48 * 60) return `${Math.round(dk / 60)} saat önce`;
  return `${Math.round(dk / 1440)} gün önce`;
}

/** 26.10 ortak sözlük — kısa tarih-saat «26.10.2026 12:33» (tarayıcının yerel saati; iki panel de yerel saat gösterir). */
export function zamanTr(s: string | null | undefined): string {
  return s ? new Date(s).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "short" }) : "—";
}
