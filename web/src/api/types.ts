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

/** /pr yaniti — v2.249 (IEC 61724-1, olcumden; POA yoksa 'poa_yok'). */
export interface PrKarti {
  durum: "ok" | "poa_yok" | "veri_yok"; gun: number; saat: number; poa_orani: number | null;
  Y_r: number | null; Y_f: number | null; PR: number | null; PR_sicaklik: number | null;
  CF: number | null; t_ref: number | null; pencere_gun: number;
  /** v2.251: pencerenin bitisi = son gecerli olcum gunu (takvim degil). */
  son_olcum?: string | null;
}

/** /konformal yaniti — v2.252 (bant kalibrasyon ayarı özeti). */
export interface KonformalAyar {
  aktif: boolean; alpha?: number; n?: number; pencere_gun?: number; hesap_zamani?: string;
  ort_q_kw?: number | null; q_hat?: Record<string, number>;
}

/** /v1/plants — v2.263 (kabuk santral seçici). */
export interface SantralKisa { id: string; name: string; capacity_kwp: number; tz: string }
/** /v1/portfoy — v2.263. */
export interface Portfoy {
  gun: string;
  santraller: { id: string; ad: string; kapasite_kwp: number; tz: string; segment: string | null; son_olcum: string | null; kesinti_gun: number | null;
                wmape_30g: number | null; bugun_kwh: number | null; yarin_kwh: number | null; acik_alarm: number; son_kosu: string | null }[];
  toplam: { santral: number; kapasite_kwp: number; bugun_kwh: number | null; yarin_kwh: number | null; wmape_agirlikli: number | null;
            wmape_kapsanan_kwp: number; acik_alarm: number; veri_gecikmis: number } | null;
}
/** v2.265 — alarm okundu/atama, kural seçimi, değişim damgası. */
export interface Kullanici { id: string; email: string; rol: string }
export interface AlarmKurallari { secili: string[]; secilebilir: string[]; esik: Record<string, number>;
  etiket: Record<string, string>; varsayilan: string[] }
export interface Damga { son_scada: string | null; son_kosu: string | null; son_alarm: string | null; acik_alarm: number;
  son_skill: string | null; son_kalibrasyon: string | null }
/** v2.264 — dış erişim (yönetici). */
export interface ApiAnahtar { id: string; ad: string | null; prefix: string; kapsamlar: string[]; iptal: boolean;
  expires_at: string | null; rpm: number; son_kullanim: string | null; olusturma: string | null }
export interface ApiAnahtarYeni extends Omit<ApiAnahtar, "iptal" | "son_kullanim" | "olusturma"> { anahtar: string }
export interface Webhook { id: string; plant_id: string | null; santral: string | null; url: string; olaylar: string[]; aktif: boolean;
  son_gonderim: string | null; son_durum: number | null; hata_sayisi: number }
/** /kgup?fmt=json — v2.260 önizleme; /segment — v2.260. */
export interface KgupOnizleme {
  gun: string; kantil: string; kosu: { run_at?: string; mode?: string }; uyarilar: string[]; sicrama_saatleri: number[];
  toplam_mwh: number; satirlar: { saat: number; kgup_mwh: number; eak_mwh: number }[]; dosya_adi: string;
  teslim: { hedef_gun: string; durum: string; dakika_kaldi: number; teyit_saati: string };
}
export const SEGMENTLER: { deger: string; etiket: string }[] = [
  { deger: "lisansli_serbest", etiket: "Lisanslı · serbest piyasa" }, { deger: "lisansli_yekdem", etiket: "Lisanslı · YEKDEM" },
  { deger: "yeka", etiket: "YEKA" }, { deger: "lisanssiz_iletim", etiket: "Lisanssız · iletim bağlantılı" },
  { deger: "lisanssiz_dagitim", etiket: "Lisanssız · dağıtım (GTŞ/toplayıcı)" }, { deger: "oz_tuketim_saatlik", etiket: "Öz tüketim · saatlik mahsup" },
];
/** /dengesizlik — v2.259: karnenin TL dili. */
export interface Dengesizlik {
  gun_sayisi: number; pencere_gun: number; not: string;
  aylar: { ay: string; uretim_mwh: number; sapma_mwh: number; referans_gelir_tl: number; pvquant_tl: number; naif_tl: number | null;
           kurtarilan_tl: number | null; gelir_oran_pct: number | null; tl_per_mwh: number | null }[];
  toplam: { pvquant_tl: number; naif_tl: number | null; kurtarilan_tl: number | null; gelir_oran_pct: number | null; referans_gelir_tl: number } | null;
  fiyat: { epias_saat: number; senaryo_saat: number };
  segment: { segment: string | null; kgup_yukumlu: boolean | null; dengesizlik_sahibi: string | null; santral_tasir: boolean | null };
}
/** /saglik — v2.256: bozunma ve performans eğilimi. */
export interface Saglik {
  gun: number; ay: number; indeks_ort: number | null; bozunma_yuzde_yil: number | null; bozunma_ga: number[] | null;
  egim_yuzde_yil: number | null; son3_vs_onceki12_pct: number | null; pr_egim_yuzde_yil: number | null; not: string;
  pencere_gun: number; kaynak: string;
}
/** /hijyen — v2.254: kırpma/kısıntı sayımı ve kısıtsız senaryo kaybı. */
export interface Hijyen {
  pencere_gun: number; son_olcum?: string | null; saat: number; kirpma_saat: number; kirpma_gun: number; kisinti_saat: number; kisinti_gun: number;
  kisinti_kayip_kwh: number; beklenen_kapsama: number | null; kisinti_aranabildi: boolean;
}
/** /backtest — v2.253: konformal katmanın kayan-başlangıç sınavı. */
export interface Backtest {
  pencere: number; picp_ham_ort: number | null; picp_kal_ort: number | null; hedef: number; hukum: string;
  satirlar: { baslangic: string; n_test: number; picp_ham: number; picp_kal: number; bant_ham_n: number; bant_kal_n: number; q_ort: number }[];
}
/** /kayma — v2.253: eğitim (arşiv) / servis (tahmin) meteo kayması. */
export interface Kayma {
  n_saat: number; hukum: string; gun?: number; baslangic?: string; bitis?: string;
  kaynak: { egitim: string; servis: string; not: string };
  ozellikler: { ad: string; etiket: string; n: number; psi: number; ks: number; sapma: number; sapma_pct: number | null; hukum: string }[];
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
  /** v2.248: P10–P90 bandinin gece sinavi (gun ortalamalari; dolu gun yoksa null). */
  olasiliksal?: { gun_sayisi: number; pinball_p10: number | null; pinball_p50: number | null; pinball_p90: number | null;
                  crps: number | null; picp80: number | null; kapsama_p10: number | null; kapsama_p90: number | null;
                  bant_n: number | null };
  gunluk: { tarih: string; kova: string; wmape: number; naif_wmape: number | null;
            nmae?: number | null; nrmse?: number | null; nmbe?: number | null }[];
}

/** /kalibrasyon yaniti — apps/api/main.py v2.122 ile birebir. */
export interface KalibrasyonOzeti {
  mode: string; eta_bos: number | null; bg: number | null;
  /** v2.255: fizik terimleri — 'none' kapalı; kt_referans 'toa' | 'ineichen'. */
  fizik_terimleri?: { iam: string; spektral: string; kt_referans: string; kirlenme?: string; kar?: string };
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
