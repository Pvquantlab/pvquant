/** Referans santral — DÖRT GÜNLÜK gerçek araştırma koşusu verisi (v2.413).
 *  Kaynak: tur7/gun4_01_10 geri-izleme koşusu (yama 01+04+07+08); kapasiteye oran = MW ÷ 200.
 *  Reçete numuneGun ile AYNI: p50 = kontrol üyesi, p10/p90 = üye bandı, gercek = kamuya açık
 *  üretim kaydı — 01.10 serisi numuneGun ile 4 ondalıkta bayt-aynıdır (mantik.test tarar).
 *  Sayılar elle değiştirilmez; canlı panel çıktısı DEĞİLDİR ve künyede böyle söylenir. */
import type { EgriNoktasi } from "./numuneGun";

export type AralikKipi = "gun" | "hafta" | "ay" | "yil";

export interface KatmanDurumu { tahmin: boolean; bant: boolean; gercek: boolean; tavan: boolean }

export const VARSAYILAN_KATMANLAR: KatmanDurumu = { tahmin: true, bant: true, gercek: true, tavan: true };

/** Koşusu olan günler (ISO, artan). Takvimde yalnız bunlar seçilebilir — veri uydurulmaz. */
export const KOSU_GUNLERI = ["2026-09-28", "2026-09-29", "2026-09-30", "2026-10-01"] as const;
export type KosuGunu = (typeof KOSU_GUNLERI)[number];
export const VARSAYILAN_GUN: KosuGunu = "2026-10-01";

const GUNLER: Record<KosuGunu, readonly EgriNoktasi[]> = {
  "2026-09-28": [
    { saat: 5, p10: 0.0, p50: 0.0, p90: 0.0, gercek: 0.0 },
    { saat: 6, p10: 0.0, p50: 0.0, p90: 0.0, gercek: 0.0007 },
    { saat: 7, p10: 0.0479, p50: 0.1429, p90: 0.1705, gercek: 0.0528 },
    { saat: 8, p10: 0.1606, p50: 0.6001, p90: 0.7441, gercek: 0.4707 },
    { saat: 9, p10: 0.6347, p50: 0.8636, p90: 0.976, gercek: 0.4987 },
    { saat: 10, p10: 0.6886, p50: 0.893, p90: 0.9747, gercek: 0.5957 },
    { saat: 11, p10: 0.6965, p50: 0.8643, p90: 0.9405, gercek: 0.6697 },
    { saat: 12, p10: 0.6965, p50: 0.8492, p90: 0.9098, gercek: 0.7399 },
    { saat: 13, p10: 0.701, p50: 0.8679, p90: 0.9279, gercek: 0.8147 },
    { saat: 14, p10: 0.693, p50: 0.897, p90: 0.9618, gercek: 0.1545 },
    { saat: 15, p10: 0.1825, p50: 0.2412, p90: 0.5626, gercek: 0.2961 },
    { saat: 16, p10: 0.1141, p50: 0.1573, p90: 0.4488, gercek: 0.3518 },
    { saat: 17, p10: 0.0498, p50: 0.0662, p90: 0.1509, gercek: 0.2884 },
    { saat: 18, p10: 0.0, p50: 0.0, p90: 0.0, gercek: 0.0078 },
    { saat: 19, p10: 0.0, p50: 0.0, p90: 0.0, gercek: 0.0 },
  ],
  "2026-09-29": [
    { saat: 5, p10: 0.0, p50: 0.0, p90: 0.0, gercek: 0.0 },
    { saat: 6, p10: 0.0, p50: 0.0, p90: 0.0, gercek: 0.0 },
    { saat: 7, p10: 0.0098, p50: 0.0097, p90: 0.0427, gercek: 0.0664 },
    { saat: 8, p10: 0.0302, p50: 0.0297, p90: 0.1443, gercek: 0.1201 },
    { saat: 9, p10: 0.1823, p50: 0.1684, p90: 0.5428, gercek: 0.1769 },
    { saat: 10, p10: 0.2524, p50: 0.2351, p90: 0.6287, gercek: 0.165 },
    { saat: 11, p10: 0.305, p50: 0.2853, p90: 0.6472, gercek: 0.5201 },
    { saat: 12, p10: 0.7458, p50: 0.8446, p90: 0.9005, gercek: 0.3973 },
    { saat: 13, p10: 0.7572, p50: 0.8633, p90: 0.916, gercek: 0.2275 },
    { saat: 14, p10: 0.7658, p50: 0.8931, p90: 0.9433, gercek: 0.1348 },
    { saat: 15, p10: 0.3651, p50: 0.6714, p90: 0.9693, gercek: 0.178 },
    { saat: 16, p10: 0.2612, p50: 0.5531, p90: 0.8796, gercek: 0.1343 },
    { saat: 17, p10: 0.0892, p50: 0.179, p90: 0.2804, gercek: 0.0562 },
    { saat: 18, p10: 0.0, p50: 0.0, p90: 0.0, gercek: 0.0098 },
    { saat: 19, p10: 0.0, p50: 0.0, p90: 0.0, gercek: 0.0 },
  ],
  "2026-09-30": [
    { saat: 5, p10: 0.0, p50: 0.0, p90: 0.0, gercek: 0.0 },
    { saat: 6, p10: 0.0, p50: 0.0, p90: 0.0, gercek: 0.0 },
    { saat: 7, p10: 0.1797, p50: 0.1837, p90: 0.1859, gercek: 0.0583 },
    { saat: 8, p10: 0.785, p50: 0.8101, p90: 0.8199, gercek: 0.1633 },
    { saat: 9, p10: 0.977, p50: 0.9916, p90: 0.9972, gercek: 0.2928 },
    { saat: 10, p10: 0.973, p50: 0.983, p90: 0.9878, gercek: 0.4766 },
    { saat: 11, p10: 0.9372, p50: 0.943, p90: 0.9471, gercek: 0.7157 },
    { saat: 12, p10: 0.9083, p50: 0.9176, p90: 0.9209, gercek: 0.8394 },
    { saat: 13, p10: 0.9298, p50: 0.9391, p90: 0.9446, gercek: 0.8451 },
    { saat: 14, p10: 0.9681, p50: 0.9783, p90: 0.9858, gercek: 0.9466 },
    { saat: 15, p10: 0.913, p50: 1.0, p90: 1.0, gercek: 0.9992 },
    { saat: 16, p10: 0.79, p50: 0.909, p90: 0.915, gercek: 0.8967 },
    { saat: 17, p10: 0.2406, p50: 0.2768, p90: 0.2779, gercek: 0.2708 },
    { saat: 18, p10: 0.0, p50: 0.0, p90: 0.0, gercek: 0.0084 },
    { saat: 19, p10: 0.0, p50: 0.0, p90: 0.0, gercek: 0.0 },
  ],
  "2026-10-01": [
    { saat: 5, p10: 0.0, p50: 0.0, p90: 0.0, gercek: 0.0 },
    { saat: 6, p10: 0.0, p50: 0.0, p90: 0.0, gercek: 0.0 },
    { saat: 7, p10: 0.0651, p50: 0.1391, p90: 0.1427, gercek: 0.065 },
    { saat: 8, p10: 0.2787, p50: 0.6519, p90: 0.6717, gercek: 0.1469 },
    { saat: 9, p10: 0.5316, p50: 0.9335, p90: 0.9335, gercek: 0.4576 },
    { saat: 10, p10: 0.6021, p50: 0.9444, p90: 0.9444, gercek: 0.546 },
    { saat: 11, p10: 0.6387, p50: 0.9067, p90: 0.9067, gercek: 0.5045 },
    { saat: 12, p10: 0.206, p50: 0.7244, p90: 0.8582, gercek: 0.7349 },
    { saat: 13, p10: 0.1924, p50: 0.7354, p90: 0.8797, gercek: 0.695 },
    { saat: 14, p10: 0.1577, p50: 0.723, p90: 0.9114, gercek: 0.666 },
    { saat: 15, p10: 0.0278, p50: 0.4525, p90: 0.6738, gercek: 0.2653 },
    { saat: 16, p10: 0.0157, p50: 0.3133, p90: 0.5457, gercek: 0.125 },
    { saat: 17, p10: 0.0068, p50: 0.1037, p90: 0.1621, gercek: 0.0244 },
    { saat: 18, p10: 0.0, p50: 0.0, p90: 0.0, gercek: 0.0 },
    { saat: 19, p10: 0.0, p50: 0.0, p90: 0.0, gercek: 0.0 },
  ],
};

export function gunSerisi(gun: KosuGunu): readonly EgriNoktasi[] {
  return GUNLER[gun];
}

export function trTarih(iso: string): string {
  const [y, a, g] = iso.split("-");
  return `${g}.${a}.${y}`;
}

const AY_ADLARI = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"];
const GUN_ADLARI = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"];

/** Günlük kapasite faktörü (%): saatlik oranların 24 saate ortalaması. Enerji anlamı:
 *  CF × 24 = eşdeğer tam-güç saati. Saatlik P10/P90 kantillerinin toplamı GÜNLÜK kantil
 *  olmadığı için gün-üstü kiplerde bant hesaplanmaz (kontrol bu yüzden devre dışı kalır). */
export function gunlukCF(gun: KosuGunu): { cf50: number; cfGercek: number } {
  const seri = GUNLER[gun];
  const t = (alan: "p50" | "gercek") => seri.reduce((a, n) => a + (n[alan] ?? 0), 0) / 24;
  return { cf50: t("p50"), cfGercek: t("gercek") };
}

export interface CFNoktasi { etiket: string; iso?: KosuGunu; cf50: number | null; cfGercek: number | null }

function isoGun(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
function kosuMu(iso: string): KosuGunu | null {
  return (KOSU_GUNLERI as readonly string[]).includes(iso) ? (iso as KosuGunu) : null;
}

/** Seçili günü içeren haftanın (Pzt–Paz) günlük CF serisi; koşusu olmayan gün null (çizilmez). */
export function haftaSerisi(gun: KosuGunu): CFNoktasi[] {
  const d = new Date(gun + "T12:00:00");
  const pzt = new Date(d);
  pzt.setDate(d.getDate() - ((d.getDay() + 6) % 7));
  return Array.from({ length: 7 }, (_, i) => {
    const g = new Date(pzt);
    g.setDate(pzt.getDate() + i);
    const iso = kosuMu(isoGun(g));
    const cf = iso ? gunlukCF(iso) : null;
    return { etiket: GUN_ADLARI[i], iso: iso ?? undefined, cf50: cf ? cf.cf50 : null, cfGercek: cf ? cf.cfGercek : null };
  });
}

/** Seçili günün ayı: ayın her günü bir yuva; koşusu olmayan gün null. */
export function aySerisi(gun: KosuGunu): CFNoktasi[] {
  const d = new Date(gun + "T12:00:00");
  const son = new Date(d.getFullYear(), d.getMonth() + 1, 0).getDate();
  return Array.from({ length: son }, (_, i) => {
    const iso = kosuMu(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(i + 1).padStart(2, "0")}`);
    const cf = iso ? gunlukCF(iso) : null;
    return { etiket: String(i + 1), iso: iso ?? undefined, cf50: cf ? cf.cf50 : null, cfGercek: cf ? cf.cfGercek : null };
  });
}

/** Seçili günün yılı: 12 ay; ay değeri = o aydaki koşu günlerinin CF ortalaması, kapsam etiketli. */
export function yilSerisi(gun: KosuGunu): { seri: CFNoktasi[]; kapsam: string } {
  const yil = gun.slice(0, 4);
  let kosulu = 0;
  const seri = AY_ADLARI.map((etiket, ay) => {
    const aydakiler = KOSU_GUNLERI.filter((g) => g.startsWith(`${yil}-${String(ay + 1).padStart(2, "0")}`));
    if (!aydakiler.length) return { etiket, cf50: null, cfGercek: null };
    kosulu += aydakiler.length;
    const cfler = aydakiler.map(gunlukCF);
    const ort = (a: "cf50" | "cfGercek") => cfler.reduce((t, c) => t + c[a], 0) / cfler.length;
    return { etiket, cf50: ort("cf50"), cfGercek: ort("cfGercek") };
  });
  return { seri, kapsam: `${yil} · ${kosulu} koşu günü` };
}

/** VERİDEN türetilmiş bulgu: gündüz penceresinde gerçekleşenin bandın (P10) altında kaldığı
 *  en uzun ardışık blok (≥3 saat; yarım puanlık gürültü eşiğiyle). Yoksa null — rozet
 *  çizilmez, uydurulmaz. 01.10 için sonuç araştırma vurgusuyla birebir: «08:00–12:00». */
export function bulgu(gun: KosuGunu, ustSaat?: number): { bas: number; son: number; metin: string } | null {
  const seri = ustSaat === undefined ? GUNLER[gun] : GUNLER[gun].filter((n) => n.saat + 0.5 <= ustSaat);
  let enIyi: { bas: number; son: number } | null = null;
  let bas: number | null = null;
  for (const n of seri) {
    const altinda = n.gercek !== null && n.p10 > 0 && n.gercek < n.p10 - 0.005;
    if (altinda && bas === null) bas = n.saat;
    if (!altinda && bas !== null) {
      if (n.saat - bas >= 3 && (!enIyi || n.saat - bas > enIyi.son - enIyi.bas)) enIyi = { bas, son: n.saat };
      bas = null;
    }
  }
  if (bas !== null && 20 - bas >= 3 && (!enIyi || 20 - bas > enIyi.son - enIyi.bas)) enIyi = { bas, son: 20 };
  if (!enIyi) return null;
  const ss = (s: number) => `${String(s).padStart(2, "0")}:00`;
  return { ...enIyi, metin: `${ss(enIyi.bas)}–${ss(enIyi.son)} · gerçekleşen aralığın altında` };
}

/* ── Ö4 vakası (v2.416): 01.10 koşusunun 15 dk teslim dilimleri ──
 * ÜRETİM: depodaki ext/tahmin/alt_saatlik.saatlikten_15dk ile, kaynak CSV'den
 * (tur7/gun4_01_10, vitrin reçetesi ÷200 → kapasiteye oran), 11:00–12:45 TRT penceresi.
 * Saat içi şekil açık-gök profilinden gelir; HER SAATİN 4-DİLİM ORTALAMASI SAATLİK
 * DEĞERE EŞİTTİR (enerji koruma — mantik.test tarar, gunSerisi ile bağlar).
 * Elle değer yazılmaz; yeniden üretim: pytest ortamında saatlikten_15dk(seri, 37.716, 33.55). */
export interface VakaDilimi { saat: string; p10: number; p50: number; p90: number; gercek: number }
export const VAKA_PENCERESI = "11:00–12:45" as const;
export const VAKA_SAATI = 12 as const;                 // saat kartının gösterdiği teslim saati
export const VAKA_15DK: readonly VakaDilimi[] = [
  { saat: "11:00", p10: 0.615, p50: 0.873, p90: 0.873, gercek: 0.4858 },
  { saat: "11:15", p10: 0.633, p50: 0.8985, p90: 0.8985, gercek: 0.5 },
  { saat: "11:30", p10: 0.6477, p50: 0.9195, p90: 0.9195, gercek: 0.5117 },
  { saat: "11:45", p10: 0.6592, p50: 0.9357, p90: 0.9357, gercek: 0.5207 },
  { saat: "12:00", p10: 0.2049, p50: 0.7206, p90: 0.8537, gercek: 0.7311 },
  { saat: "12:15", p10: 0.2064, p50: 0.7256, p90: 0.8596, gercek: 0.7362 },
  { saat: "12:30", p10: 0.2067, p50: 0.7269, p90: 0.8612, gercek: 0.7375 },
  { saat: "12:45", p10: 0.2061, p50: 0.7245, p90: 0.8583, gercek: 0.7351 },
];
