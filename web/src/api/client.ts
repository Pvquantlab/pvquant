import type { SantralOzeti, TahminSerisi, Karne, AylikBeklenti } from "./types";
import { ornekOzet, ornekTahmin, ornekKarne, ornekAylik } from "./ornek";

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

/** v2.73-C: 401'de oturum dusurulur — token 12 saatte olur, SPA sessiz kirilmasin. */
let oturumDusunce: (() => void) | null = null;
export function oturumDusunce_kaydet(fn: (() => void) | null): void {
  oturumDusunce = fn;
}

async function getir<T>(yol: string): Promise<T> {
  const jeton = localStorage.getItem("pvq_token");
  const y = await fetch(`${TABAN}${yol}`, {
    headers: jeton ? { Authorization: `Bearer ${jeton}` } : {} });
  if (y.status === 401) {
    cikis(); oturumDusunce?.();
    // v2.84: uygulama zaten girise dusuyor — bekleyen cagri ne cozulur ne
    // reddedilir; "Uncaught (in promise)" gurultusu konsola dusmez.
    return new Promise<T>(() => {});
  }
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

/** v2.88: SCADA onizleme yaniti — apps/api/main.py v2.87 ile birebir. */
export interface ScadaOnizleme {
  file_format: { encoding: string; delimiter: string; decimal: string;
                 header_row: number; sheet_name: string | null;
                 n_preview_rows: number; confidence: number };
  mapping: { timestamp: string; power: string | null; energy: string | null;
             poa_irradiance: string | null; temp_ambient: string | null;
             temp_module: string | null; wind_speed: string | null;
             ghi: string | null; confidence: Record<string, number> };
  unmapped_columns: string[];
  sample_rows: { columns: string[]; rows: (string | null)[][] };
  matched_template: string | null;
  notes: string[];
  onerilen_tz: string;
}

/** v2.88: dosyali POST — getir'in 401 sozlesmesinin aynisi. 4xx'te sunucunun
 *  detail mesaji Error olur (422 esleme reddi UI'da durustce okunur). */
async function dosyaGonder<T>(yol: string, dosya: File): Promise<T> {
  const jeton = localStorage.getItem("pvq_token");
  const veri = new FormData();
  veri.append("dosya", dosya);
  const y = await fetch(`${TABAN}${yol}`, {
    method: "POST", body: veri,
    headers: jeton ? { Authorization: `Bearer ${jeton}` } : {} });
  if (y.status === 401) {
    cikis(); oturumDusunce?.();
    return new Promise<T>(() => {});   // v2.84 sozlesmesi: sessiz dusus
  }
  if (!y.ok) {
    let mesaj = `${y.status} ${yol}`;
    try {
      const g = (await y.json()) as { detail?: unknown };
      if (typeof g.detail === "string") mesaj = g.detail;
    } catch { /* govde yoksa durum kodu kalir */ }
    throw new Error(mesaj);
  }
  return (await y.json()) as T;
}

/** /summary yaniti — apps/api/main.py v2.74-A ile birebir. */
interface OzetYanit {
  plant: { id: string; name: string; capacity_kwp: number;
           ac_limit_kw: number | null; lat: number; lon: number; tz: string;
           tilt: number | null; azimuth: number | null;
           panel_tech: string | null };
  mode: "A" | "B" | "C" | null; sapma_pct: number | null;
  anlati: string | null; bugun_kwh: number | null; yarin_kwh: number | null;
  yarin_hava: string; hafta_mwh: number | null; model_alt: string;
  kalibrasyon_tarihi: string | null;
  hava: { gun: string; derece: number; kwhm2: number }[];
  gunler: { etiket: string; mwh: number | null }[];
  saglik: { son_scada: string | null; islenen_saat: number; anomali: number };
  aylik: { ay: string; mwh: number | null; saglam_saat: number | null;
           kapsam_pct: number | null }[];
}

const AYLAR_KISA_TR = ["Oca", "Şub", "Mar", "Nis", "May", "Haz",
                       "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"];

/** '2026-06' -> 'Haz 26' (Streamlit'in aylik cubuk sesi). */
function ayEtiketi(ay: string): string {
  const [yil, ayNo] = ay.split("-");
  const ad = AYLAR_KISA_TR[Number(ayNo) - 1];
  return ad ? `${ad} ${yil.slice(2)}` : ay;
}

function trTarih(iso: string | null): string | null {
  return iso ? new Date(iso).toLocaleDateString("tr-TR",
    { day: "numeric", month: "short", year: "numeric" }) : null;
}

/** API yanitini UI sekline tasi. Sapma UI'da mutlak deger (%X,XX kalibi);
 *  egim/azimut null ise ornekteki 'varsayilan' sesi; kesinti_gun istemcide. */
function uyarlaOzet(g: OzetYanit): SantralOzeti {
  const sonScada = g.saglik.son_scada;
  const kesintiGun = sonScada
    ? Math.max(0, Math.floor((Date.now() - new Date(sonScada).getTime()) / 86400000))
    : null;
  return {
    ad: g.plant.name, kapasite_kwp: g.plant.capacity_kwp,
    ac_tavani_kw: g.plant.ac_limit_kw,
    lat: g.plant.lat, lon: g.plant.lon, tz: g.plant.tz,
    egim_azimut: g.plant.tilt !== null && g.plant.azimuth !== null
      ? `${g.plant.tilt}° / ${g.plant.azimuth}°`
      : "20° / 180° (varsayılan)",
    mod: g.mode, model_adi: g.model_alt || "—",
    sapma_pct: g.sapma_pct !== null ? Math.abs(g.sapma_pct) : null,
    son_kalibrasyon: trTarih(g.kalibrasyon_tarihi),
    saatlik_mape: null, son_kosu: null,
    bugun_kwh: g.bugun_kwh, yarin_kwh: g.yarin_kwh, hafta_mwh: g.hafta_mwh,
    anlati: g.anlati ?? "",
    hava: g.hava.map((h) => ({ etiket: h.gun, sicaklik: h.derece,
                               isinim: h.kwhm2 })),
    gunler: g.gunler.map((x) => ({ etiket: x.etiket, mwh: x.mwh ?? 0 })),
    aylik: g.aylik.map((a) => ({ ay: ayEtiketi(a.ay), mwh: a.mwh ?? 0,
      saglam_saat: a.saglam_saat ?? 0, kapsam_pct: a.kapsam_pct ?? 0 })),
    saglik: { son_scada: trTarih(sonScada), kesinti_gun: kesintiGun,
              islenen_saat: g.saglik.islenen_saat, anomali: g.saglik.anomali },
  };
}

export const api = {
  /** v2.88: SCADA onizleme — dosyayi kapiya tasir, yaniti OLDUGU GIBI doner
   *  (yorum UI'nin isi degil; icat yok). Ornek kipte kapi yok — durust hata. */
  scadaOnizleme: async (p: string, dosya: File): Promise<ScadaOnizleme> => {
    if (!TABAN) throw new Error(
      "Örnek kipte dosya kapısı yok — VITE_API_URL tanımlı değil.");
    return dosyaGonder<ScadaOnizleme>(`/v1/plants/${p}/scada/preview`, dosya);
  },
  /** karne: gercek kapisi HENUZ yok — API tarafiyla birlikte dogana
   *  kadar ornekte kalir; var olmayan URL cagrilmaz (v2.73-A karari). */
  ozet: async (p: string): Promise<SantralOzeti> => {
    if (!TABAN) return ornekOzet;
    return uyarlaOzet(await getir<OzetYanit>(`/v1/plants/${p}/summary`));
  },
  karne: async (p: string): Promise<Karne> => {
    if (!TABAN) return ornekKarne;
    // v2.76: KPI'lar 0-24 kovasindan; grafik karsilastirmasi icin 24-72 de
    // cekilir ve gunluk birlesir (kapi kova basina calisir).
    const [k0, k1] = await Promise.all([
      getir<Karne>(`/v1/plants/${p}/skill?bucket=0-24`),
      getir<Karne>(`/v1/plants/${p}/skill?bucket=24-72`),
    ]);
    return { ...k0, gunluk: [...k0.gunluk, ...k1.gunluk] };
  },
  aylik: async (p: string): Promise<AylikBeklenti> => {
    if (!TABAN) return ornekAylik;
    return getir<AylikBeklenti>(`/v1/plants/${p}/monthly`);
  },
  tahmin: async (p: string, u: Ufuk): Promise<TahminSerisi> => {
    if (!TABAN) return ornekTahmin(u);
    return uyarla(await getir<ForecastYanit>(
      `/v1/plants/${p}/forecast?hours=${UFUK_SAAT[u]}`));
  },
};
