/** API sozlesmesi — apps/api'nin donmesi gereken sekiller.
 *  Kaynak: mevcut Streamlit ekranlarinin gosterdigi veri. */
export type Mod = "A" | "B" | "C";

export interface HavaGun { etiket: string; sicaklik: number; isinim: number; }

export interface SantralOzeti {
  ad: string; kapasite_kwp: number; ac_tavani_kw: number | null;
  lat: number; lon: number; tz: string;
  egim_azimut: string;                    // v2.71-C
  mod: Mod | null; model_adi: string;
  sapma_pct: number | null; son_kalibrasyon: string | null;
  saatlik_mape: number | null; son_kosu: string | null;
  bugun_kwh: number | null; yarin_kwh: number | null;
  hafta_mwh: number | null;               // v2.71-A: ILK 7 gun
  anlati: string;
  hava: HavaGun[];
  gunler: { etiket: string; mwh: number }[];   // v2.71-A: tam 7
  aylik: { ay: string; mwh: number; saglam_saat: number; kapsam_pct: number }[];
  saglik: { son_scada: string | null; kesinti_gun: number | null;
            islenen_saat: number; anomali: number };
}

export interface TahminSerisi {
  mod: Mod | null; model: string; kosu_zamani: string; ufuk_saat: number;
  ac_tavani_kw: number | null; simdi_idx: number | null;
  saatlik: { ts: string; p50_kw: number; p10_kw: number | null;
             p90_kw: number | null; gercek_kw: number | null }[];
  gunluk: { tarih: string; p50_kwh: number; p10_kwh: number | null; p90_kwh: number | null }[];
}

export interface Karne {
  kova: string; gun_sayisi: number;       // v2.71-E
  wmape_ort: number | null; naife_ustunluk_pct: number | null;
  ilk_tarih: string | null; son_tarih: string | null;
  gunluk: { tarih: string; kova: string; wmape: number; naif_wmape: number | null }[];
}
