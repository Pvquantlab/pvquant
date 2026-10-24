/** 24.10 Faz 2 — PLATFORM (PVQuant personeli) API istemcisi: /v1/yonetim/*.
 *  Müşteri istemcisinden (client.ts) AYRI jeton anahtarı (`pvq_platform_token`): iki yüz aynı tarayıcıda yan yana
 *  yaşar, müşteri 401 işleyicisi platform oturumunu düşürmez (ve tersi). Jeton `kapsam: platform` taşır; sunucu müşteri
 *  uçlarını bu jetona 403 ile kapatır. Örnek kipte (VITE_API_URL yok) yönetim yüzü yoktur: TABAN null → ekran bunu söyler. */
const _API_HAM = import.meta.env.VITE_API_URL as string | undefined;
export const PTABAN: string | null = _API_HAM == null ? null : _API_HAM === "." ? "" : _API_HAM;
const ANAHTAR = "pvq_platform_token";

export function platformJeton(): string | null { return localStorage.getItem(ANAHTAR); }
export function platformCikis(): void { localStorage.removeItem(ANAHTAR); }
let dusunce: (() => void) | null = null;
export function platformDusunce_kaydet(fn: (() => void) | null): void { dusunce = fn; }

export class YonetimHata extends Error { durum: number; constructor(durum: number, mesaj: string) { super(mesaj); this.durum = durum; } }

async function istek<T>(yol: string, method: "GET" | "POST" | "PUT" = "GET", govde?: unknown): Promise<T> {
  if (PTABAN == null) throw new YonetimHata(0, "Örnek kipte yönetim yüzü yok.");
  const j = platformJeton();
  const y = await fetch(`${PTABAN}/v1/yonetim${yol}`, {
    method, body: govde === undefined ? undefined : JSON.stringify(govde),
    headers: { ...(j ? { Authorization: `Bearer ${j}` } : {}), ...(govde === undefined ? {} : { "Content-Type": "application/json" }) } });
  if (y.status === 401 && j) { platformCikis(); dusunce?.(); return new Promise<T>(() => {}); }
  if (!y.ok) {
    let mesaj = `${y.status} ${yol}`;
    try { const g = (await y.json()) as { detail?: unknown }; if (typeof g.detail === "string") mesaj = g.detail; } catch { /* gövde yok */ }
    throw new YonetimHata(y.status, mesaj);
  }
  return (await y.json()) as T;
}

export interface Ben { id: string; email: string; rol: "sahip" | "operator"; totp_aktif: boolean; son_giris: string | null; olusturma: string }
export interface Kiraci { id: string; ad: string; plan: string; durum: string; olusturma: string; guncelleme: string | null; notlar: string | null;
  santral: number; kurulu_guc_kwp: number; kullanici: number; son_giris: string | null }
export interface KiraciKullanici { id: string; email: string; rol: string; aktif: boolean; totp_aktif: boolean; son_giris: string | null; olusturma: string }
export interface KiraciSantral { id: string; ad: string; kapasite_kwp: number; tz: string; arsivli: boolean; olusturma: string; son_scada: string | null; son_kosu: string | null }
export interface KiraciDetay { id: string; ad: string; plan: string; durum: string; notlar: string | null; olusturma: string; guncelleme: string | null;
  kullanicilar: KiraciKullanici[]; santraller: KiraciSantral[] }
export interface Kullanici extends KiraciKullanici { tenant_id: string; firma: string }
export interface Operator { id: string; email: string; rol: string; aktif: boolean; totp_aktif: boolean; son_giris: string | null; olusturma: string }
export interface Basvuru { id: string; eposta: string; santral_adi: string | null; kurulu_guc_kwp: number | null; okundu: boolean; created_at: string }
export interface DenetimKaydi { id: number; zaman: string; kapsam: string; aktor_id: string | null; aktor_eposta: string | null; tenant_id: string | null;
  eylem: string; nesne_tur: string | null; nesne_id: string | null; ayrinti: Record<string, unknown>; ip: string | null }

export const yonetim = {
  /** "hata" | "iki_adim" | { rol, email, iki_adim_kurulmali } — jeton depoya yazılır */
  giris: async (email: string, sifre: string, kod?: string): Promise<"hata" | "iki_adim" | { rol: string; email: string; iki_adim_kurulmali: boolean }> => {
    if (PTABAN == null) return "hata";
    const y = await fetch(`${PTABAN}/v1/yonetim/giris`, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, sifre, ...(kod ? { kod } : {}) }) });
    if (!y.ok) return "hata";
    const g = (await y.json()) as { token?: string; rol?: string; email?: string; iki_adim_gerekli?: boolean; iki_adim_kurulmali?: boolean };
    if (g.iki_adim_gerekli) return "iki_adim";
    if (!g.token) return "hata";
    localStorage.setItem(ANAHTAR, g.token);
    return { rol: g.rol ?? "", email: g.email ?? email, iki_adim_kurulmali: !!g.iki_adim_kurulmali };
  },
  oturumYenile: async (): Promise<{ rol: string; email: string; iki_adim_kurulmali: boolean } | null> => {
    try { const y = await istek<{ token: string; rol: string; email: string; iki_adim_kurulmali: boolean }>("/oturum/yenile", "POST");
      localStorage.setItem(ANAHTAR, y.token); return { rol: y.rol, email: y.email, iki_adim_kurulmali: y.iki_adim_kurulmali }; } catch { return null; }
  },
  ben: (): Promise<Ben> => istek("/ben"),
  parolaDegistir: (eski: string, yeni: string): Promise<{ tamam: boolean }> => istek("/parola", "POST", { eski, yeni }),
  ikiAdimBaslat: (): Promise<{ secret: string; otpauth_uri: string }> => istek("/iki-adim/baslat", "POST"),
  ikiAdimDogrula: (kod: string): Promise<{ tamam: boolean }> => istek("/iki-adim/dogrula", "POST", { kod }),
  operatorler: (): Promise<{ operatorler: Operator[]; roller: string[] }> => istek("/operatorler"),
  operatorEkle: (email: string, rol: string): Promise<Operator & { gecici_parola: string }> => istek("/operatorler", "POST", { email, rol }),
  operatorGuncelle: (id: string, g: { rol?: string; aktif?: boolean; iki_adim_sifirla?: boolean }): Promise<{ tamam: boolean }> => istek(`/operatorler/${id}`, "PUT", g),
  kiracilar: (): Promise<{ kiracilar: Kiraci[] }> => istek("/kiracilar"),
  kiraciOlustur: (firma: string, yonetici_eposta: string, plan: string): Promise<{ tenant_id: string; user_id: string; davet_gonderildi: boolean; davet_baglantisi?: string; not?: string }> =>
    istek("/kiracilar", "POST", { firma, yonetici_eposta, plan }),
  kiraci: (id: string): Promise<KiraciDetay> => istek(`/kiracilar/${id}`),
  kiraciGuncelle: (id: string, g: { ad?: string; plan?: string; durum?: string; notlar?: string }): Promise<{ tamam: boolean }> => istek(`/kiracilar/${id}`, "PUT", g),
  kullanicilar: (q = "", limit = 100): Promise<{ kullanicilar: Kullanici[] }> => istek(`/kullanicilar?q=${encodeURIComponent(q)}&limit=${limit}`),
  kullaniciGuncelle: (id: string, g: { aktif?: boolean; rol?: string }): Promise<{ tamam: boolean }> => istek(`/kullanicilar/${id}`, "PUT", g),
  kullaniciParolaBaglantisi: (id: string): Promise<{ gonderildi: boolean; baglanti?: string }> => istek(`/kullanicilar/${id}/parola-sifirlama`, "POST"),
  kullaniciIkiAdimSifirla: (id: string): Promise<{ tamam: boolean }> => istek(`/kullanicilar/${id}/iki-adim-sifirla`, "POST"),
  basvurular: (): Promise<{ basvurular: Basvuru[] }> => istek("/basvurular"),
  basvuruOkundu: (id: string): Promise<{ tamam: boolean }> => istek(`/basvurular/${id}/okundu`, "POST"),
  denetim: (p: { tenant_id?: string; eylem?: string; kapsam?: string; limit?: number; once_id?: number } = {}): Promise<{ kayitlar: DenetimKaydi[] }> => {
    const q = Object.entries(p).filter(([, v]) => v !== undefined && v !== "").map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`).join("&");
    return istek(`/denetim${q ? "?" + q : ""}`);
  },
};

/** Tarih/saat kısa (tr-TR) — null «—» */
export function zamanTr(s: string | null | undefined): string {
  return s ? new Date(s).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "short" }) : "—";
}
