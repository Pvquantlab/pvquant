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
  aylik: { ay: string; mwh: number; saglam_saat: number; kapsam_pct: number;
           /** v2.205 — ay tam kapsanmadan null (kismi toplam yaniltir). */
           beklenti_mwh: number | null }[];
  saglik: { son_scada: string | null; kesinti_gun: number | null;
            islenen_saat: number; anomali: number };
}

export interface TahminSerisi {
  mod: Mod | null; model: string; kosu_zamani: string; ufuk_saat: number;
  ac_tavani_kw: number | null; simdi_idx: number | null;
  /** v2.203 — pencerenin astronomik dogus/batis ciftleri (UTC ISO). */
  gunes: { gun: string; dogus: string; batis: string }[];
  saatlik: { ts: string; p50_kw: number; p10_kw: number | null;
             p90_kw: number | null;
             /** v2.204 — ic bant; eski kosu/Mod A-B'de null. */
             p25_kw: number | null; p75_kw: number | null;
             gercek_kw: number | null }[];
  gunluk: { tarih: string; p50_kwh: number; p10_kwh: number | null; p90_kwh: number | null }[];
}

export interface Karne {
  kova: string; gun_sayisi: number;       // v2.71-E
  wmape_ort: number | null; naife_ustunluk_pct: number | null;
  ilk_tarih: string | null; son_tarih: string | null;
  /** v2.247: SFA sozlugu — kapasiteye normalize yuzdeler (eski kayitlarda null). */
  nmae_ort?: number | null; nrmse_ort?: number | null; nmbe_ort?: number | null;
  gunluk: { tarih: string; kova: string; wmape: number; naif_wmape: number | null;
            nmae?: number | null; nrmse?: number | null; nmbe?: number | null }[];
}

/** /kalibrasyon yaniti — apps/api/main.py v2.122 ile birebir. */
export interface KalibrasyonOzeti {
  mode: string; eta_bos: number | null; bg: number | null;
  gecerli_saat: number | null; tarih: string | null;
  mape_once: number | null; mape_sonra: number | null;
  wmape_once: number | null; wmape_sonra: number | null;
  sapma_once: number | null; sapma_sonra: number | null;
  uyarilar: string[];
}

/** /saat-ay-matrisi yaniti — apps/api/main.py v2.121 ile birebir. */
export interface SaatAyMatrisi {
  saatler: string[]; hucreler: (number | null)[][];
  toplam: (number | null)[]; birim: string; tz: string;
}

/** /gunes-yolu yaniti — apps/api/main.py v2.116 ile birebir. */
export interface GunesYolu {
  lat: number; lon: number; tz: string; yil: number;
  egriler: { ad: string;
             nokta: [number, number][];          // [azimut, yukseklik]
             saat: [number, number, number][] }[]; // [azimut, yukseklik, saat]
}

/** /hata-dagilimi yaniti — apps/api/main.py v2.112 ile birebir. */
export interface HataDagilimi {
  kutular: { lo: number; hi: number; adet: number }[];
  mu: number | null; sd: number | null; ndays: number;
  p10: number | null; p50: number | null; p90: number | null;
  birim: string; kova: string; tz: string;
}

/** /hata-matrisi yaniti — apps/api/main.py v2.111 ile birebir. */
export interface HataMatrisi {
  gunler: string[]; saatler: string[];
  hucreler: (number | null)[][];        // [saat][gun], p50 - gercek, kW
  metrik: string; birim: string; kova: string; tz: string;
}

/** /monthly yaniti — apps/api/main.py v2.78-B ile birebir. */
export interface AylikBeklenti {
  plant_id: string;
  hesap_zamani: string;
  beklenti: { ay: number; p10: number | null; p50: number | null;
              p90: number | null; yil_sayisi: number }[];
  yillik: { yil: number; ay: number; ghi_kwh_m2: number | null }[];
}
