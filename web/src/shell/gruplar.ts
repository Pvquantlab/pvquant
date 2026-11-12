import type { SayfaId } from "./Kabuk";

/** v2.608 (Faz 5 F5-A) — yan menü İŞ AKIŞI GRUPLARI (brief §6 düzeni). Her sayfa kimliği tam bir grupta (bekçi: test/panel/nav.test.ts);
 *  sayfa kimlikleri, hash derin bağlantıları ve yetki kapıları değişmedi — yalnız kümelendi. Grup açık/kapalı durumu localStorage'da;
 *  aktif sayfanın grubu her zaman açık. */
export const GRUPLAR: { id: string; ad: string; sayfalar: SayfaId[] }[] = [
  { id: "genel", ad: "Genel bakış", sayfalar: ["genel", "portfoy"] },
  { id: "uretim", ad: "Üretim", sayfalar: ["santralim", "tahminler", "aylik", "dogruluk", "kalibrasyon"] },
  { id: "piyasa", ad: "Piyasa ve finans", sayfalar: ["kgup", "portfoyler", "mutabakat", "finans"] },
  { id: "operasyon", ad: "Operasyon", sayfalar: ["sayac", "veri", "olaylar", "takvim"] },
  { id: "yonetim", ad: "Yönetim", sayfalar: ["raporlar", "paylasim", "kurulus", "hakkinda"] },
];
/** Santral seçimi gerektirmeyen sayfalar: App bunları `SantralYok` kapısından muaf tutar (tek kaynak; nav.test bekçisi). */
export const SANTRALSIZ: SayfaId[] = ["portfoy", "portfoyler", "kurulus", "paylasim", "hakkinda"];
export const NAV_KAPALI_ANAHTAR = "pvq_nav_kapali";
export function kapaliGruplariOku(): string[] {
  try { const v = JSON.parse(localStorage.getItem(NAV_KAPALI_ANAHTAR) ?? "[]"); return Array.isArray(v) ? v.filter((x) => typeof x === "string") : []; } catch { return []; }
}
