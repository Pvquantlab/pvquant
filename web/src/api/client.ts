/** Ince API istemcisi. VITE_API_URL tanimliysa gercek API'ye gider;
 *  tanimli degilse ornek veriye duser — boylece apps/api kapilari
 *  acilmadan once de ekran gelistirilebilir. */
import type { SantralOzeti, TahminSerisi } from "./types";
import { ornekOzet, ornekTahmin } from "./ornek";

const TABAN = import.meta.env.VITE_API_URL as string | undefined;

async function getir<T>(yol: string, yedek: T): Promise<T> {
  if (!TABAN) return yedek;
  const jeton = localStorage.getItem("pvq_token");
  const y = await fetch(`${TABAN}${yol}`, {
    headers: jeton ? { Authorization: `Bearer ${jeton}` } : {},
  });
  if (!y.ok) throw new Error(`${y.status} ${yol}`);
  return (await y.json()) as T;
}

export const api = {
  ozet: (plantId: string) =>
    getir<SantralOzeti>(`/v1/plants/${plantId}/summary`, ornekOzet),
  tahmin: (plantId: string, ufuk: "24h" | "72h" | "7d" | "16d") =>
    getir<TahminSerisi>(`/v1/plants/${plantId}/forecast?horizon=${ufuk}`, ornekTahmin(ufuk)),
};
