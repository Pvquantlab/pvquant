import type { SantralOzeti, TahminSerisi, Karne, AylikBeklenti , HataMatrisi , HataDagilimi , GunesYolu , SaatAyMatrisi , KalibrasyonOzeti , PrKarti , KonformalAyar } from "./types";
import { ornekOzet, ornekTahmin, ornekKarne, ornekAylik } from "./ornek";

/** Ince API istemcisi (v2.73-A). Kural: sozlesmeyi API belirler, istemci uyar.
 *  VITE_API_URL tanimliysa GERCEK kapiya gider; degilse ornek veriye duser. */
const _API_HAM = import.meta.env.VITE_API_URL as string | undefined;
/** v2.148: "." = AYNI KÖKEN (caddy arkası) — fetch'ler göreli /v1'e gider,
 *  alan adından bağımsız tek build. Tanımsız = örnek kip (API'siz demo). */
const TABAN = _API_HAM === "." ? "" : _API_HAM;

/** UI ufuk etiketi -> saat. Kapinin dili saat sayisidir (?hours=N, tavan 384). */
const UFUK_SAAT = { "24h": 24, "72h": 72, "7d": 168, "16d": 384 } as const;
type Ufuk = keyof typeof UFUK_SAAT;

/** Gercek kapinin yanit sekli — apps/api/main.py v2.72 ile birebir. */
interface ForecastYanit {
  plant_id: string;
  run_at: string | null;
  mode: "A" | "B" | "C" | null;
  hours: number;
  /** v2.203 — pencerenin astronomik dogus/batis ciftleri (UTC ISO). */
  gunes?: { gun: string; dogus_utc: string; batis_utc: string }[];
  series: { ts_utc: string; p10_kw: number | null;
            p50_kw: number | null; p90_kw: number | null;
            /* v2.204: ic bant — eski kosu/Mod A-B'de null */
            p25_kw?: number | null; p75_kw?: number | null }[];
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
             p10_kw: s.p10_kw, p90_kw: s.p90_kw,
             p25_kw: s.p25_kw ?? null, p75_kw: s.p75_kw ?? null,  // v2.204
             gercek_kw: null };
  });
  const gunler = new Map<string, number>();
  for (const s of saatlik) {
    const gun = s.ts.slice(0, 10);
    gunler.set(gun, (gunler.get(gun) ?? 0) + s.p50_kw);  // saatlik kW -> gunluk kWh
  }
  return {
    mod: g.mode, model: "", kosu_zamani: g.run_at ?? "",
    ufuk_saat: g.hours, ac_tavani_kw: null, simdi_idx: simdiIdx,
    gunes: (g.gunes ?? []).map((x) =>
      ({ gun: x.gun, dogus: x.dogus_utc, batis: x.batis_utc })),
    saatlik,
    gunluk: [...gunler].map(([tarih, p50_kwh]) =>
      ({ tarih, p50_kwh, p10_kwh: null, p90_kwh: null })),
  };
}

/** v2.73-B: gercek oturum. Ornek kipte (TABAN yok) kapi yoktur, gecis serbest. */
export async function giris(email: string, sifre: string): Promise<boolean> {
  if (TABAN == null) return true;
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

/** v2.89: kayit yaniti — apps/api/main.py v2.87 /scada ucu ile birebir. */
export interface ScadaKayit {
  batch_id: string;
  n_satir: number;
  report: { n_rows_read: number; n_rows_valid: number;
            flag_counts: Record<string, number>; gap_hours: number;
            gap_periods: [string, string][];
            coverage_start: string | null; coverage_end: string | null;
            warnings: string[] };
  transform: { source_timezone: string | null; power_unit: string;
               irradiance_unit: string | null;
               irradiance_unit_source: string | null;
               timestep_minutes: number; energy_to_power: boolean;
               energy_cumulative: boolean };
}

/** v2.91: otomatik esleme reddi — sihirbazi kuran yapilandirilmis 422. */
export interface EslemeVerisi {
  tur: "esleme";
  columns: string[];
  sample_rows: { columns: string[]; rows: (string | null)[][] };
  file_format: ScadaOnizleme["file_format"];
}
export class EslemeHatasi extends Error {
  veri: EslemeVerisi;
  constructor(veri: EslemeVerisi) { super("esleme reddi"); this.veri = veri; }
}

/** v2.94: gecmis kosu satiri — /runs ucu ile birebir. */
export interface KosuSatiri { run_at: string; mode: string; model: string; }
/** v2.240 — zil kapısı satırı (apps/api alarmlar ile birebir). */
export interface AlarmSatiri {
  id: string; kural: string; siddet: string; mesaj: string; zaman: string;
}

/** v2.88: dosyali POST — getir'in 401 sozlesmesinin aynisi. 4xx'te sunucunun
 *  detail mesaji Error olur (422 esleme reddi UI'da durustce okunur). */
async function dosyaGonder<T>(yol: string, dosya: File,
                              alanlar?: Record<string, string>): Promise<T> {
  const jeton = localStorage.getItem("pvq_token");
  const veri = new FormData();
  veri.append("dosya", dosya);
  if (alanlar)
    for (const [k, v] of Object.entries(alanlar)) veri.append(k, v);
  const y = await fetch(`${TABAN}${yol}`, {
    method: "POST", body: veri,
    headers: jeton ? { Authorization: `Bearer ${jeton}` } : {} });
  if (y.status === 401) {
    cikis(); oturumDusunce?.();
    return new Promise<T>(() => {});   // v2.84 sozlesmesi: sessiz dusus
  }
  if (!y.ok) {
    let mesaj = `${y.status} ${yol}`;
    let esleme: EslemeHatasi | null = null;
    try {
      const g = (await y.json()) as { detail?: unknown };
      const d = g.detail;
      if (d && typeof d === "object" && (d as { tur?: string }).tur === "esleme")
        esleme = new EslemeHatasi(d as EslemeVerisi);   // v2.91
      else if (typeof d === "string") mesaj = d;
    } catch { /* govde yoksa durum kodu kalir */ }
    if (esleme) throw esleme;
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
           kapsam_pct: number | null;
           /* v2.205: ay TAM kapsanmadan API null gonderir */
           beklenti_mwh?: number | null }[];
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
      saglam_saat: a.saglam_saat ?? 0, kapsam_pct: a.kapsam_pct ?? 0,
      // v2.205: beklenti 0'a INDIRGENMEZ — null durust yokluktur (imlec yok)
      beklenti_mwh: a.beklenti_mwh ?? null })),
    saglik: { son_scada: trTarih(sonScada), kesinti_gun: kesintiGun,
              islenen_saat: g.saglik.islenen_saat, anomali: g.saglik.anomali },
  };
}

/** v2.147: kapinin bulgusu — kod (D1..D18/R1..R2), seviye, mesaj, beklenen/bulunan. */
export interface DenetimBulgusu {
  kod: string; seviye: "hata" | "uyari";
  mesaj: string; beklenen?: string; bulunan?: string;
}
export class RaporDenetimHata extends Error {
  bulgular: DenetimBulgusu[];
  constructor(mesaj: string, bulgular: DenetimBulgusu[]) {
    super(mesaj); this.bulgular = bulgular;
  }
}

export const api = {
  /** v2.88: SCADA onizleme — dosyayi kapiya tasir, yaniti OLDUGU GIBI doner
   *  (yorum UI'nin isi degil; icat yok). Ornek kipte kapi yok — durust hata. */
  scadaOnizleme: async (p: string, dosya: File): Promise<ScadaOnizleme> => {
    if (TABAN == null) throw new Error(
      "Örnek kipte dosya kapısı yok — VITE_API_URL tanımlı değil.");
    return dosyaGonder<ScadaOnizleme>(`/v1/plants/${p}/scada/preview`, dosya);
  },
  /** v2.89: onayli kayit — dosya + santral kaydindan gelen tz. Karne
   *  yanitta doner; UI oldugu gibi gosterir (yorum yok, icat yok). */
  scadaYukle: async (p: string, dosya: File, tz: string | null,
                     esleme?: Record<string, string>): Promise<ScadaKayit> => {
    if (TABAN == null) throw new Error(
      "Örnek kipte dosya kapısı yok — VITE_API_URL tanımlı değil.");
    const alanlar: Record<string, string> = {};
    if (tz) alanlar.source_timezone = tz;   // v2.91: bos -> santral tz (sunucu)
    if (esleme)
      for (const [k, v] of Object.entries(esleme))
        if (v) alanlar["map_" + k] = v;     // v2.91: sihirbaz kararlari
    return dosyaGonder<ScadaKayit>(`/v1/plants/${p}/scada`, dosya, alanlar);
  },
  /** v2.93: taze tahmin kosusu — es zamanli, 10-20 sn surer. */
  tahminKos: async (p: string): Promise<{ run_id: string }> => {
    if (TABAN == null) throw new Error(
      "Örnek kipte koşu tetiklenmez — VITE_API_URL tanımlı değil.");
    const jeton = localStorage.getItem("pvq_token");
    const y = await fetch(`${TABAN}/v1/plants/${p}/forecast/run`, {
      method: "POST",
      headers: jeton ? { Authorization: `Bearer ${jeton}` } : {} });
    if (y.status === 401) {
      cikis(); oturumDusunce?.();
      return new Promise(() => {});   // v2.84 sozlesmesi
    }
    if (!y.ok) {
      let mesaj = `${y.status} kosu`;
      try {
        const g = (await y.json()) as { detail?: unknown };
        if (typeof g.detail === "string") mesaj = g.detail;
      } catch { /* govde yoksa kod kalir */ }
      throw new Error(mesaj);
    }
    return (await y.json()) as { run_id: string };
  },
  /** v2.94: gecmis kosular — ornek kipte sayfanin eski sabit listesi doner. */
  kosular: async (p: string): Promise<KosuSatiri[]> => {
    if (TABAN == null) return [
      { run_at: "2026-07-30T12:58:00", mode: "C", model: "hybrid_residual" },
      { run_at: "2026-07-30T00:42:00", mode: "C", model: "hybrid_residual" },
      { run_at: "2026-07-30T00:30:00", mode: "C", model: "hybrid_residual" },
      { run_at: "2026-07-29T20:27:00", mode: "C", model: "hybrid_residual" },
      { run_at: "2026-07-28T21:49:00", mode: "B", model: "barhdadi_bennis" },
    ];
    return getir<KosuSatiri[]>(`/v1/plants/${p}/runs`);
  },
  /** v2.94: rapor indir — blob + Content-Disposition adi; 401 sozlesmesi ayni.
      v2.147 (Adim 4): 422 yapilandirilmis govde (mesaj+bulgular) tipli hataya
      cevrilir; SPA denetim bulgularini kullaniciya gosterir. */
  raporIndir: async (p: string, fmt: "pdf" | "pdf16" | "xlsx" | "json"): Promise<void> => {
    if (TABAN == null) throw new Error(
      "Örnek kipte rapor üretimi yok — VITE_API_URL tanımlı değil.");
    const jeton = localStorage.getItem("pvq_token");
    const y = await fetch(`${TABAN}/v1/plants/${p}/report?fmt=${fmt}`, {
      headers: jeton ? { Authorization: `Bearer ${jeton}` } : {} });
    if (y.status === 401) {
      cikis(); oturumDusunce?.();
      return new Promise<void>(() => {});   // v2.84 sozlesmesi
    }
    if (!y.ok) {
      let mesaj = `${y.status} rapor`;
      try {
        const g = (await y.json()) as { detail?: unknown };
        if (typeof g.detail === "string") mesaj = g.detail;
        else if (g.detail && typeof g.detail === "object") {
          const d = g.detail as { mesaj?: string; bulgular?: DenetimBulgusu[] };
          if (Array.isArray(d.bulgular))
            throw new RaporDenetimHata(d.mesaj ?? "denetim geçemedi", d.bulgular);
          if (d.mesaj) mesaj = d.mesaj;
        }
      } catch (h) {
        if (h instanceof RaporDenetimHata) throw h;
        /* govde yoksa kod kalir */
      }
      throw new Error(mesaj);
    }
    const cd = y.headers.get("Content-Disposition") ?? "";
    const es = /filename="([^"]+)"/.exec(cd);
    const ad = es ? es[1] : `PVQuant_rapor.${fmt}`;
    const url = URL.createObjectURL(await y.blob());
    const a = document.createElement("a");
    a.href = url; a.download = ad; a.click();
    URL.revokeObjectURL(url);
  },
  /** karne: gercek kapisi HENUZ yok — API tarafiyla birlikte dogana
   *  kadar ornekte kalir; var olmayan URL cagrilmaz (v2.73-A karari). */
  ozet: async (p: string): Promise<SantralOzeti> => {
    if (TABAN == null) return ornekOzet;
    return uyarlaOzet(await getir<OzetYanit>(`/v1/plants/${p}/summary`));
  },
  karne: async (p: string, gun = 60): Promise<Karne> => {
    if (TABAN == null) return ornekKarne;
    // v2.76: KPI'lar 0-24 kovasindan; grafik karsilastirmasi icin 24-72 de
    // cekilir ve gunluk birlesir (kapi kova basina calisir).
    // v2.230: gun parametresi kapida ZATEN vardi (1-365) — donem segmenti
    // icin istemciden gecirilir; varsayilan 60 (mockup H karari).
    const [k0, k1] = await Promise.all([
      getir<Karne>(`/v1/plants/${p}/skill?bucket=0-24&gun=${gun}`),
      getir<Karne>(`/v1/plants/${p}/skill?bucket=24-72&gun=${gun}`),
    ]);
    return { ...k0, gunluk: [...k0.gunluk, ...k1.gunluk] };
  },
  alarmlar: async (p: string, n = 20): Promise<AlarmSatiri[]> => {
    if (TABAN == null) return [];
    return getir<AlarmSatiri[]>(`/v1/plants/${p}/alarmlar?n=${n}`);
  },
  /** v2.252: bant kalibrasyon ayarı — kapı yoksa/hata {aktif:false}. */
  konformal: async (p: string): Promise<KonformalAyar> => {
    if (TABAN == null) return { aktif: false };
    try { return await getir<KonformalAyar>(`/v1/plants/${p}/konformal`); }
    catch { return { aktif: false }; }
  },
  /** v2.249: performans orani (IEC 61724-1) — kapi yoksa/hata null (kunye tire yazar). */
  pr: async (p: string, gun = 30): Promise<PrKarti | null> => {
    if (TABAN == null) return null;
    try { return await getir<PrKarti>(`/v1/plants/${p}/pr?gun=${gun}`); }
    catch { return null; }
  },
  kalibrasyon: async (p: string): Promise<KalibrasyonOzeti | null> => {
    if (TABAN == null) return null;
    try { return await getir<KalibrasyonOzeti>(`/v1/plants/${p}/kalibrasyon`); }
    catch { return null; }
  },
  saatAyMatrisi: async (p: string): Promise<SaatAyMatrisi> => {
    if (TABAN == null) return { saatler: [], hucreler: [], toplam: [], birim: "kW", tz: "UTC" };
    return getir<SaatAyMatrisi>(`/v1/plants/${p}/saat-ay-matrisi`);
  },
  gunesYolu: async (p: string): Promise<GunesYolu> => {
    if (TABAN == null) return { lat: 0, lon: 0, tz: "UTC", yil: 2026, egriler: [] };
    return getir<GunesYolu>(`/v1/plants/${p}/gunes-yolu`);
  },
  hataDagilimi: async (p: string, gun = 120): Promise<HataDagilimi> => {
    if (TABAN == null) return { kutular: [], mu: null, sd: null, ndays: 0,
      p10: null, p50: null, p90: null, birim: "MWh/gun", kova: "0-24", tz: "UTC" };
    return getir<HataDagilimi>(`/v1/plants/${p}/hata-dagilimi?gun=${gun}&kova=0-24`);
  },
  hataMatrisi: async (p: string, gun = 30): Promise<HataMatrisi> => {
    if (TABAN == null) return { gunler: [], saatler: [], hucreler: [],
      metrik: "isaretli_hata", birim: "kW", kova: "0-24", tz: "UTC" };
    return getir<HataMatrisi>(`/v1/plants/${p}/hata-matrisi?gun=${gun}&kova=0-24`);
  },
  aylik: async (p: string): Promise<AylikBeklenti> => {
    if (TABAN == null) return ornekAylik;
    return getir<AylikBeklenti>(`/v1/plants/${p}/monthly`);
  },
  tahmin: async (p: string, u: Ufuk): Promise<TahminSerisi> => {
    if (TABAN == null) return ornekTahmin(u);
    return uyarla(await getir<ForecastYanit>(
      `/v1/plants/${p}/forecast?hours=${UFUK_SAAT[u]}`));
  },
};
