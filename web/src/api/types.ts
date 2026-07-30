/** API sozlesmesi — apps/api'nin donmesi gereken sekiller.
 *  Kaynak: mevcut Streamlit ekranlarinin gosterdigi veri (ekranlar sartname). */

export type Mod = "A" | "B" | "C";

/** GET /v1/plants/{id}/summary  — Santralim ekrani */
export interface SantralOzeti {
  ad: string;
  kapasite_kwp: number;
  ac_tavani_kw: number | null;
  lat: number;
  lon: number;
  egim_azimut: string;          // v2.71-C: gercekte kullanilani soyler
  mod: Mod | null;
  model_adi: string;            // "Hibrit" | "Kalibre fizik" | ...
  sapma_pct: number | null;     // yillik enerji sapmasi
  son_kalibrasyon: string | null;
  bugun_kwh: number | null;
  yarin_kwh: number | null;
  hafta_mwh: number | null;     // v2.71-A: ILK 7 gunun toplami
  gunler: { etiket: string; mwh: number }[];   // v2.71-A: tam 7 gun
}

/** GET /v1/plants/{id}/forecast?horizon=24h|72h|7d|16d */
export interface TahminSerisi {
  mod: Mod;
  model: string;
  kosu_zamani: string;
  ufuk_saat: number;            // v2.71-D: alt yazi bunu soyler
  saatlik: {
    ts: string;
    p50_kw: number;
    p10_kw: number | null;
    p90_kw: number | null;
  }[];
  gunluk: {
    tarih: string;
    p50_kwh: number;
    p10_kwh: number | null;
    p90_kwh: number | null;
  }[];
}

/** GET /v1/plants/{id}/skill?bucket=0-24 — Dogruluk karnesi */
export interface Karne {
  kova: string;
  gun_sayisi: number;           // v2.71-E: baslik bunu soyler, sabit 30 degil
  wmape_ort: number | null;
  naife_ustunluk_pct: number | null;
  ilk_tarih: string | null;     // v2.71-E: kapsanan donem
  son_tarih: string | null;
  gunluk: { tarih: string; kova: string; wmape: number; naif_wmape: number | null }[];
}

/** GET /v1/plants/{id}/health — veri sagligi kutusu */
export interface VeriSagligi {
  son_scada: string | null;
  islenen_saat: number;
  anomali_sayisi: number;
  kesinti_gun: number | null;
}
