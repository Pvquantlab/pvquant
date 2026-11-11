/** v2.595 (Faz 3 F3-H) — dönem seçenekleri (FinansalEtki'den ortak kullanıma taşındı; v2.584): kod biçimleri arka uçla aynı
 *  (YYYY-MM-DD | YYYY-Wnn | YYYY-MM | YYYY-QN | YYYY). Bugünden geriye: 14 gün, 8 hafta, 12 ay (süren ay dâhil), 4 çeyrek, 2 yıl. */
import type { FinansDonemTur } from "../api/types";
export type { FinansDonemTur };
export const TUR_AD: Record<FinansDonemTur, string> = { gun: "gün", hafta: "hafta", ay: "ay", ceyrek: "çeyrek", yil: "yıl" };
export const AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"];
const p2 = (n: number) => String(n).padStart(2, "0");

export function isoHafta(d: Date): [number, number] {
  const t = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate())); const gun = t.getUTCDay() || 7;
  t.setUTCDate(t.getUTCDate() + 4 - gun); const y = t.getUTCFullYear(); const bas = Date.UTC(y, 0, 1);
  return [y, Math.ceil(((t.getTime() - bas) / 86400000 + 1) / 7)];
}

export function donemSecenekleri(tur: FinansDonemTur, bugun = new Date()): { kod: string; etiket: string }[] {
  const out: { kod: string; etiket: string }[] = [];
  if (tur === "gun") for (let i = 1; i <= 14; i++) { const d = new Date(bugun); d.setDate(d.getDate() - i); out.push({ kod: `${d.getFullYear()}-${p2(d.getMonth() + 1)}-${p2(d.getDate())}`, etiket: `${d.getDate()} ${AYLAR[d.getMonth()]} ${d.getFullYear()}` }); }
  if (tur === "hafta") for (let i = 1; i <= 8; i++) { const d = new Date(bugun); d.setDate(d.getDate() - 7 * i); const [y, h] = isoHafta(d); out.push({ kod: `${y}-W${p2(h)}`, etiket: `${y}, ${h}. hafta` }); }
  if (tur === "ay") for (let i = 0; i < 12; i++) { const d = new Date(bugun.getFullYear(), bugun.getMonth() - i, 1); out.push({ kod: `${d.getFullYear()}-${p2(d.getMonth() + 1)}`, etiket: `${AYLAR[d.getMonth()]} ${d.getFullYear()}${i === 0 ? " (süren)" : ""}` }); }
  if (tur === "ceyrek") { const q0 = Math.floor(bugun.getMonth() / 3); for (let i = 0; i < 4; i++) { let q = q0 - i, y = bugun.getFullYear(); while (q < 0) { q += 4; y -= 1; } out.push({ kod: `${y}-Q${q + 1}`, etiket: `${y}, ${q + 1}. çeyrek${i === 0 ? " (süren)" : ""}` }); } }
  if (tur === "yil") for (let i = 0; i < 2; i++) { const y = bugun.getFullYear() - i; out.push({ kod: String(y), etiket: `${y}${i === 0 ? " (süren)" : ""}` }); }
  return out;
}
