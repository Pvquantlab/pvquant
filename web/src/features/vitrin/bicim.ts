/** Vitrin sayı ve tarih biçimleri (tr-TR, v2.384). Değer yoksa tire — uydurma yedek yok. */
export function yuzdeTr(deger: number | null | undefined): string {
  return deger == null ? "—" : `%${deger.toLocaleString("tr-TR")}`;
}

/** "2026-10-01" → "1 Eki" (öğlen sabitlenir; saat dilimi günü kaydırmaz). */
export function kisaTarihTr(gun: string | null | undefined): string {
  if (!gun) return "—";
  return new Date(`${gun}T12:00:00`).toLocaleDateString("tr-TR", { day: "numeric", month: "short" });
}

/** "2026-09" → "Eylül 2026" */
export function ayTr(ay: string): string {
  return new Date(`${ay}-15T12:00:00`).toLocaleDateString("tr-TR", { month: "long", year: "numeric" });
}
