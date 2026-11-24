/** P-1 (24.11.2026) — gece işleri tablosu: kayıtları yerel (TSİ) güne göre gruplar ve gün özeti üretir.
 *  Saf; sıralama girdideki gibi (sunucu zamana göre azalan verir). Sayı uydurulmaz: yalnız verilen kayıtlar sayılır. */
export interface IsSatiri { is: string; zaman: string; sure_sn: number | null; tamam: boolean; durum?: string; kod?: string }
export interface GunGrubu { gun: string; etiket: string; satirlar: IsSatiri[]; tamam: number; atlandi: number; basarisiz: number }

const TZ = "Europe/Istanbul";

export function gunAnahtari(iso: string, tz: string = TZ): string {
  return new Intl.DateTimeFormat("sv-SE", { timeZone: tz, year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date(iso));   // YYYY-MM-DD
}

export function gunEtiketi(iso: string, tz: string = TZ): string {
  return new Intl.DateTimeFormat("tr-TR", { timeZone: tz, day: "numeric", month: "long", weekday: "long" }).format(new Date(iso));
}

export function gunlereGrupla(isler: IsSatiri[], tz: string = TZ): GunGrubu[] {
  const out: GunGrubu[] = [];
  for (const x of isler) {
    const gun = gunAnahtari(x.zaman, tz);
    let g = out[out.length - 1];
    if (!g || g.gun !== gun) { g = { gun, etiket: gunEtiketi(x.zaman, tz), satirlar: [], tamam: 0, atlandi: 0, basarisiz: 0 }; out.push(g); }
    g.satirlar.push(x);
    if (x.durum === "atlandi") g.atlandi += 1; else if (x.tamam) g.tamam += 1; else g.basarisiz += 1;
  }
  return out;
}

export function grupOzeti(g: GunGrubu): string {
  const p = [`${g.tamam} tamam`];
  if (g.atlandi) p.push(`${g.atlandi} atlandı`);
  if (g.basarisiz) p.push(`${g.basarisiz} başarısız`);
  return p.join(" · ");
}
