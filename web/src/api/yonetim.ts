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

// 25.10 Faz 3 — sistem izleme. Bayatlık HÜKÜMLERİ (bayat, taze, durum) uçtan gelir; arayüz eşik uydurmaz.
export interface SistemOzet {
  zaman: string;
  nabiz: { durum: "calisiyor" | "sessiz" | "yok"; son: string | null; yas_dk: number | null; ayrinti: Record<string, unknown>; aralik_dk: number; sessiz_dk: number };
  gece_turu: { taze: boolean; bayat_isler: string[]; son: string | null; esik_saat: number; uretici_isler: { kod: string; is: string; son_ok: string | null }[] };
  isler_24: { toplam: number; hata: number };
  meteo: { esik_saat: number; kaynaklar: { kaynak: string; son_indirme: string | null; nokta: number | null; satir: number | null; ilk: string | null; son_ts: string | null; yas_saat: number | null; bayat: boolean }[] };
  piyasa: { son_ts: string | null; son_guncelleme: string | null; satir: number; yas_saat: number | null; esik_saat: number; bayat: boolean };
  yedek: { son_basarili: string | null; yas_saat: number | null; esik_saat: number; bayat: boolean; son_deneme: { zaman: string | null; tamam: boolean; ayrinti: string | null } | null };
  db: { boyut_bayt: number };
  santral: { etkin: number; arsivli: number };
}
export interface IsKaydi { id: string; kod: string; is: string; tenant_id: string | null; kiraci: string | null; plant_id: string | null; santral: string | null;
  zaman: string; sure_sn: number | null; tamam: boolean; durum: string; ayrinti: string | null }
export interface SantralEnvanter { id: string; ad: string; kapasite_kwp: number; tz: string; olusturma: string; tenant_id: string; kiraci: string; kiraci_durum: string;
  son_scada: string | null; son_kosu: string | null; son_hata: string | null; sorunlar: string[] }

// 25.10 Faz 4 — kullanım: sayaç türleri (dis_api, webhook, webhook_hata) + türetilmiş sayımlar (rapor, kosu, scada_saat, yukleme)
export interface KullanimToplam { dis_api: number; webhook: number; webhook_hata: number; rapor: number; kosu: number; scada_saat: number; yukleme: number }
export interface KullanimKiraci { id: string; ad: string; plan: string; durum: string; etkin_anahtar: number; etkin_webhook: number; son_api_kullanim: string | null;
  bu_ay: KullanimToplam; onceki_ay: KullanimToplam }
export interface KullanimOzet { ay: string; onceki_ay: string; turler: string[]; kiracilar: KullanimKiraci[] }
export interface KullanimGunler { ay: string; tenant_id: string; ad: string | null; gunler: ({ gun: string } & KullanimToplam)[] }

/** Sorgu dizesi: boş/undefined alanlar atlanır. */
const sorgu = (p: Record<string, unknown>): string => {
  const q = Object.entries(p).filter(([, v]) => v !== undefined && v !== "" && v !== false).map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`).join("&");
  return q ? "?" + q : "";
};

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
  denetim: (p: { tenant_id?: string; eylem?: string; kapsam?: string; limit?: number; once_id?: number } = {}): Promise<{ kayitlar: DenetimKaydi[] }> =>
    istek(`/denetim${sorgu(p)}`),
  // 25.10 Faz 3 — sistem izleme (salt okunur)
  sistem: (): Promise<SistemOzet> => istek("/sistem"),
  isler: (p: { saat?: number; yalniz_hata?: boolean; job?: string; tenant_id?: string; limit?: number } = {}): Promise<{ isler: IsKaydi[]; pencere_saat: number; is_turleri: { kod: string; is: string }[] }> =>
    istek(`/isler${sorgu(p)}`),
  santraller: (sorunlu = false): Promise<{ santraller: SantralEnvanter[]; esik: { scada_saat: number; kosu_saat: number }; toplam: number }> =>
    istek(`/santraller${sorgu({ sorunlu })}`),
  // 25.10 Faz 4 — kullanım (salt okunur); ay 'YYYY-MM', boşsa bu ay
  kullanim: (ay?: string): Promise<KullanimOzet> => istek(`/kullanim${sorgu({ ay })}`),
  kullanimGunler: (tenant_id: string, ay?: string): Promise<KullanimGunler> => istek(`/kullanim${sorgu({ tenant_id, ay })}`),
};

/** Göreli yaş: «3 dk önce», «5 saat önce», «2 gün önce»; null «—». Hüküm değil, okunurluk. */
export function yasTr(s: string | null | undefined, simdi = Date.now()): string {
  if (!s) return "—";
  const dk = Math.max(0, Math.round((simdi - new Date(s).getTime()) / 60000));
  if (dk < 60) return `${dk} dk önce`;
  if (dk < 48 * 60) return `${Math.round(dk / 60)} saat önce`;
  return `${Math.round(dk / 1440)} gün önce`;
}

/** Tarih/saat kısa (tr-TR) — null «—» */
export function zamanTr(s: string | null | undefined): string {
  return s ? new Date(s).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "short" }) : "—";
}
