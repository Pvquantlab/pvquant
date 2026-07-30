import type { SantralOzeti, TahminSerisi, Karne } from "./types";
import { ornekOzet, ornekTahmin, ornekKarne } from "./ornek";

const TABAN = import.meta.env.VITE_API_URL as string | undefined;

async function getir<T>(yol: string, yedek: T): Promise<T> {
  if (!TABAN) return yedek;
  const jeton = localStorage.getItem("pvq_token");
  const y = await fetch(`${TABAN}${yol}`, {
    headers: jeton ? { Authorization: `Bearer ${jeton}` } : {} });
  if (!y.ok) throw new Error(`${y.status} ${yol}`);
  return (await y.json()) as T;
}

export const api = {
  ozet: (p: string) => getir<SantralOzeti>(`/v1/plants/${p}/summary`, ornekOzet),
  tahmin: (p: string, u: "24h" | "72h" | "7d" | "16d") =>
    getir<TahminSerisi>(`/v1/plants/${p}/forecast?horizon=${u}`, ornekTahmin(u)),
  karne: (p: string) => getir<Karne>(`/v1/plants/${p}/skill?bucket=0-24`, ornekKarne),
};
