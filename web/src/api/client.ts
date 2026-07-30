import type { SantralOzeti, TahminSerisi, Karne } from "./types";
import { ornekOzet, ornekTahmin, ornekKarne } from "./ornek";

/** Ince API istemcisi (v2.73-A). Kural: sozlesmeyi API belirler, istemci uyar.
 *  VITE_API_URL tanimliysa GERCEK kapiya gider; degilse ornek veriye duser. */
const TABAN = import.meta.env.VITE_API_URL as string | undefined;

/** UI ufuk etiketi -> saat. Kapinin dili saat sayisidir (?hours=N, tavan 384). */
const UFUK_SAAT = { "24h": 24, "72h": 72, "7d": 168, "16d": 384 } as const;
type Ufuk = keyof typeof UFUK_SAAT;

/** Gercek kapinin yanit sekli — apps/api/main.py v2.72 ile birebir. */
interface ForecastYanit {
  plant_id: string;
  run_at: string | null;
  mode: "A" | "B" | "C" | null;
  hours: number;
  series: { ts_utc: string; p10_kw: number | null;
            p50_kw: number | null; p90_kw: number | null }[];
}

async function getir<T>(yol: string): Promise<T> {
  const jeton = localStorage.getItem("pvq_token");
  const y = await fetch(`${TABAN}${yol}`, {
    headers: jeton ? { Authorization: `Bearer ${jeton}` } : {} });
  if (!y.ok) throw new Error(`${y.status} ${yol}`);
  return (await y.json()) as T;
}

/** Gercek yaniti UI sekline tasi. API'nin vermedigi alanlar null kalir
 *  (gercek_kw, gunluk bant, AC tavani) — istemci veri UYDURMAZ. */
function uyarla(g: ForecastYanit): TahminSerisi {
  const simdi = Date.now();
  let simdiIdx: number | null = null;
  const saatlik = g.series.map((s, i) => {
    if (simdiIdx === null && new Date(s.ts_utc).getTime() > simdi)
      simdiIdx = Math.max(0, i - 1);
    return { ts: s.ts_utc, p50_kw: s.p50_kw ?? 0,
             p10_kw: s.p10_kw, p90_kw: s.p90_kw, gercek_kw: null };
  });
  const gunler = new Map<string, number>();
  for (const s of saatlik) {
    const gun = s.ts.slice(0, 10);
    gunler.set(gun, (gunler.get(gun) ?? 0) + s.p50_kw);  // saatlik kW -> gunluk kWh
  }
  return {
    mod: g.mode, model: "", kosu_zamani: g.run_at ?? "",
    ufuk_saat: g.hours, ac_tavani_kw: null, simdi_idx: simdiIdx,
    saatlik,
    gunluk: [...gunler].map(([tarih, p50_kwh]) =>
      ({ tarih, p50_kwh, p10_kwh: null, p90_kwh: null })),
  };
}

/** v2.73-B: gercek oturum. Ornek kipte (TABAN yok) kapi yoktur, gecis serbest. */
export async function giris(email: string, sifre: string): Promise<boolean> {
  if (!TABAN) return true;
  const y = await fetch(`${TABAN}/v1/auth/login`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, sifre }) });
  if (!y.ok) return false;
  const g = (await y.json()) as { token: string };
  localStorage.setItem("pvq_token", g.token);
  return true;
}

export function cikis(): void { localStorage.removeItem("pvq_token"); }

export const api = {
  /** ozet/karne: gercek kapilari HENUZ yok — API tarafiyla birlikte dogana
   *  kadar ornekte kalirlar; var olmayan URL cagrilmaz (v2.73-A karari). */
  ozet: async (_p: string): Promise<SantralOzeti> => ornekOzet,
  karne: async (_p: string): Promise<Karne> => ornekKarne,
  tahmin: async (p: string, u: Ufuk): Promise<TahminSerisi> => {
    if (!TABAN) return ornekTahmin(u);
    return uyarla(await getir<ForecastYanit>(
      `/v1/plants/${p}/forecast?hours=${UFUK_SAAT[u]}`));
  },
};
