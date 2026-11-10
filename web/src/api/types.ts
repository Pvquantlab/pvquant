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
  /** v2.316 — mwh null: takvimde var ama verisi yok (iç boşluk ayı); 0 uydurulmaz. */
  aylik: { ay: string; mwh: number | null; saglam_saat: number; kapsam_pct: number;
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
  /** v2.533 (P8a, IH-084): AC sınırında kırpılan saat sayısı ve kırpma dışı PR */
  kirpma_saat?: number; PR_kirpma_disi?: number | null;
}

/** /konformal yaniti — v2.252 (bant kalibrasyon ayarı özeti). */
export interface KonformalAyar {
  aktif: boolean; alpha?: number; n?: number; pencere_gun?: number; hesap_zamani?: string;
  ort_q_kw?: number | null; q_hat?: Record<string, number | Record<string, number>>;
  /** v2.296: ufuk kovası başına ortalama q̂ (kW) — yalnız kova öğrenildiyse. */
  kova_ort_q_kw?: Record<string, number> | null;
}

/** /v1/plants — v2.263 (kabuk santral seçici). */
export interface SantralKisa { id: string; name: string; capacity_kwp: number; tz: string }
/** /v1/portfoy — v2.263. */
export interface Portfoy {
  gun: string;
  santraller: { id: string; ad: string; kapasite_kwp: number; tz: string; segment: string | null; son_olcum: string | null; kesinti_gun: number | null; baglanti?: { tur: string; tur_kisa: string; kod: string; etiket: string; saglayici: string | null; cekis_acik: boolean; n_cihaz: number } | null;
                wmape_30g: number | null; bugun_kwh: number | null; yarin_kwh: number | null; acik_alarm: number; son_kosu: string | null;
                /** 29.10: yarının programı — yükümlü mü, 15:30 kesimi öncesi tahmin var mı */
                program?: { yukumlu: boolean | null; hazir: boolean | null; run_at: string | null; not: string | null;
                            teslim: { hedef_gun: string; durum: string; dakika_kaldi: number; teyit_saati: string };
                            /** 29.10: müşterinin yarın için yüklediği (bildirdiğini beyan ettiği) KGÜP dosyası var mı — TPYS kabulü doğrulanmaz */
                            bildirilen?: boolean; bildirim_zamani?: string | null } }[];
  toplam: { santral: number; kapasite_kwp: number; bugun_kwh: number | null; yarin_kwh: number | null; wmape_agirlikli: number | null;
            wmape_kapsanan_kwp: number; acik_alarm: number; veri_gecikmis: number;
            program_yukumlu?: number; program_hazir?: number; program_segment_yok?: number; program_bildirilen?: number } | null;
}
/** v2.270 — Hakkında: veri kaynakları ve lisanslar (Anayasa v2.245 istisnası — yalnız bu sayfa, rapor künyesi, README). */
export interface Hakkinda {
  urun: string; meteo_kaynak: string;
  kaynaklar: { kimlik: string; ad: string; kurum: string; lisans: string; lisans_url: string; veri_url: string; not: string;
    /** v2.535: lisans sayfasının son doğrulama tarihi (ISO) ve notu — yalnız gerçekten okunan sayfalar; yoksa null */
    lisans_dogrulama?: string | null; lisans_notu?: string | null }[];
  kunye: string; uyarilar: string[]; yontem: string;
  /** v2.535: indirme işinin günlüğü — arşivdeki model tahmin saatinden ayrı: son başarılı, son deneme ve durumu */
  isler?: Record<string, { ad: string; son_basarili: string | null; son_deneme: string | null; son_durum: string | null; son_ayrinti: string | null }>;
  /** v2.295: mevzuat/standart dayanağı — madde referansları tek yerde. */
  mevzuat?: { ad: string; kapsam: string; not: string; kunye?: string }[];   // v2.535: birincil yayım bilgisi (RG tarih-sayı, karar no)
  arsiv: Record<string, { son: string | null; nokta: number; satir: number; ilk: string | null; son_ts: string | null }>;
}
/** v2.266 — kısa ufuk (0–6 s), ölçüm persistansı; uydu değil. */
export interface Nowcast {
  durum: "ok" | "gece" | "scada_bayat" | "tahmin_yok" | "olcum_yok"; uydu: boolean; yontem?: string; ufuk_saat?: number;
  son_olcum?: string | null; tazelik_saat?: number | null; oran: number | null; n_saat: number; not?: string;
  ufuk: { ts: string; p50_kw: number; nowcast_kw: number; agirlik: number }[];
}
/** v2.265 — alarm okundu/atama, kural seçimi, değişim damgası. */
export interface Kullanici { id: string; email: string; rol: string }
export interface AlarmKurallari { secili: string[]; secilebilir: string[]; esik: Record<string, number>;
  etiket: Record<string, string>; varsayilan: string[];
  alicilar: string[]; ortam_alicisi: boolean }   // v2.519 (P7a): santral alıcıları (e-posta) + ortam adresi var mı
export interface Damga { son_scada: string | null; son_kosu: string | null; son_alarm: string | null; acik_alarm: number;
  son_skill: string | null; son_kalibrasyon: string | null }
/** v2.264 — dış erişim (yönetici). */
export interface ApiAnahtar { id: string; ad: string | null; prefix: string; kapsamlar: string[]; iptal: boolean;
  expires_at: string | null; rpm: number; son_kullanim: string | null; olusturma: string | null }
export interface ApiAnahtarYeni extends Omit<ApiAnahtar, "iptal" | "son_kullanim" | "olusturma"> { anahtar: string }
export interface Webhook { id: string; plant_id: string | null; santral: string | null; url: string; olaylar: string[]; aktif: boolean;
  son_gonderim: string | null; son_durum: number | null; hata_sayisi: number }
/** v2.281 — kullanılabilirlik, kayıp ağacı, tarife. */
export interface Kullanilabilirlik { durum: string; mumkun_saat?: number; veri_orani?: number; haric_saat?: number; ariza_saat?: number;
  ariza_olay_sayisi?: number; mtbf_saat?: number | null; mttr_saat?: number | null;   // 04.11 v2.531 (ENV-F10): olay kaydındaki arızalardan
  A_t?: number | null; A_e?: number | null; kayip_kwh?: number; not?: string; pencere_gun?: number; beklenen_kwh?: number;
  /** v2.533 (P8a, K-07): Santral ayarlarındaki sözleşme eşiği girildiyse açık (kWh, TL) — kıyas tabanı, alacak değil */
  sozlesme?: { esik: number; A_gercek: number; acik_puan: number; acik_kwh: number; acik_tl: number | null; fiyat_tl_mwh: number | null; fiyat_kaynak: string; not: string } | null }
/** v2.533 (P8a, IH-087): gerçekleşen kayıp ayrışımı — nedene göre saat / kWh / TL; beklenen = fizik modeli (hava tahmini girdili) */
export interface KayipAyrisimi { durum: "ok" | "yetersiz" | "veri_yok"; pencere_gun?: number; son_olcum?: string | null; mumkun_saat?: number; veri_saat?: number;
  uretim_kwh?: number; beklenen_kwh?: number; epi?: number | null; toplam_kayip_kwh?: number; toplam_kayip_tl?: number; fiyatsiz_saat?: number; olay_saat?: number;
  fiyat?: { kaynak: string; tip: string | null; senaryo_saat: number; etiket: string }; not?: string;
  satirlar?: { neden: string; etiket: string; kaynak: string; kpi_disi: boolean | null; saat: number; kayip_kwh: number | null; kayip_tl: number | null; not: string }[] }
export interface KayipAgaci { durum: string; yil?: number; kaynak?: string; ghi_kwh_m2?: number; poa_kwh_m2?: number; nominal_dc_kwh?: number; sebeke_kwh?: number;
  pr?: number | null; ozgul_kwh_kwp?: number; hesap_zamani?: string;
  satirlar?: { adim: string; etiket: string; giren_kwh: number; cikan_kwh: number; kayip_kwh: number; kayip_pct: number; kaynak: string }[] }
export interface Tarife { tip: "sabit" | "ptf" | "yekdem" | "cok_zamanli"; tl_mwh?: number; prim_oran?: number; sabit_ek_tl_mwh?: number; usd_cent_kwh?: number; kur_tl_usd?: number;
  gunduz_tl_mwh?: number; puant_tl_mwh?: number; gece_tl_mwh?: number; eskalasyon_yillik?: number;
  // v2.520 (P5a): YEKDEM rejimi (işletmeye giriş tarihinden ya da seçim), tesis tipi, yerli katkı (7189: açık/kapalı; Cetvel I: ¢/kWh); kur yalnız yedek
  rejim?: "otomatik" | "cetvel1" | "7189"; tesis_tipi?: "gunes" | "gunes_depolamali"; yerli_katki?: boolean; yerli_katki_usd_cent?: number }
/** v2.520 (P5a): YEKDEM katmanı — rejim, bugünün YEK fiyatı, 7189 aylık ilanları (USD band konumu), kur arşivi, m.23(6) saat işareti (belirsiz). Yeniden hesaptır. */
export interface YekdemBant { durum: "icinde" | "tabanda" | "tavanda" | "kur_yok"; usd_cent: number | null; kur_ortalama: number | null; kur_ayi: string; taban_cent: number; tavan_cent: number;
  taban_kr: number | null; tavan_kr: number | null }
export interface Yekdem {
  bugun: string; pencere_gun: number; segment: string | null; uygulanir: boolean; tarife_yekdem: boolean;
  rejim: { secim: string; isletmeye_giris: string | null; tesis_tipi: "gunes" | "gunes_depolamali"; rejim: "cetvel1" | "7189" | null; etiket: string; kaynak: string; kaynak_turu: "kullanici" | "hesaplanan" | "yok" };
  fiyat: { gun: string; yek_tl_mwh: number | null; yerli_tl_mwh: number | null; toplam_tl_mwh: number | null; kaynak: string; kaynak_etiket: string; kur: number | null; kur_gunu: string | null;
    onceki_gun: boolean; ay_fiyat_kr_kwh: number | null; usd_cent_kwh: number | null } | null;
  kur: { son_gun: string | null; son_usd_alis: number | null; son_eur_alis: number | null; gun_sayisi: number; ilk_gun: string | null; eksik_is_gunu_30: string[]; kaynak: string } | null;
  aylar: { ay: string; fiyat_kr_kwh: number | null; yerli_katki_kr_kwh: number | null; kaynak: string | null; bant: YekdemBant | null; durum: "ilan" | "ilan_yok" }[];
  m23_6: { baslangic: string; etiket: string; pencere_gun: number; saat: number; aday_saat: number; fiyat_yok_saat: number; kapsam_saat: number; yekdem_disi_mwh: number; yekdem_disi_tl: number;
    bildirilmemis_saat: number; ilk_saat: string | null; son_saat: string | null; not: string;
    /** v2.532 (DK-301): bildirilen KGÜP yüklenmemiş saatlerde mevzuat okuması — KGÜP = 0, üretimin tamamı dışarıda */
    kgup0_saat?: number; kgup0_mwh?: number; kgup0_tl?: number;
    /** v2.540 (EK-3 DK-333): YEK Yön. m.23(9) tatil günü işareti, 1.1–18.10.2026 (RG 33122 → RG 33405 ile mülga) */
    m23_9?: { baslangic: string; bitis: string; kapsam_saat: number; saat: number; kgup_yok_saat: number; mwh: number; tl: number; ilk_saat: string | null; son_saat: string | null; etiket: string; not: string } } | null;
  not: string | null;
  sabitler: { cetvel1_cent: number; bant_cent: [number, number]; baslangic_kr: [number, number]; yerli_yil: number; j: number };
  /** v2.538 (EK-3 DK-297/DK-323/DK-675): YEKDEM hesabının modellemediği kurallar (kapsam sınırı) */ kapsam_sinirlari?: { kod: string; etiket: string; metin: string }[];
}
/** /guc-matrisi — v2.283: IEC 61853 kalıbıyla modül davranışı. */
export interface GucMatrisi {
  durum: string; kaynak?: string; gamma?: number; yil?: number; hesap_zamani?: string; not?: string;
  tablo?: { g_wm2: number; verim_25_pct: number; verim_50_pct: number }[];
  cser?: number | null; e_dc_kwh_kwp?: number; h_poa_kwh_m2?: number;
  dusuk_isinim_kayip_pct?: number; sicaklik_50_kayip_pct?: number;
}
/** /p-degerleri — v2.534 (P8b-1; IH-098/099): yıl yıl P50/P75/P90/P99 serisi (bozunma dâhil, biçim etiketli) ve gerçekleşen kıyası (hava düzeltmesiz) */
export interface PDegerSatiri { n: number; takvim_yili: number | null; bicim: string; p50: number; p75: number; p90: number; p95: number; p99: number }
export interface PDegerleri { durum: "ok" | "bankable_yok"; not?: string; bugun?: string; p50_kwh?: number; bankable_hesap_zamani?: string; bankable_donem?: string;
  ilk_yil?: number | null; ilk_yil_kaynak?: string | null; n_yil?: number; bozunma_yuzde_yil?: number; bozunma_kaynak?: string; butce_kwh_yil?: number | null;
  sigma_1yil?: number; sigma_nyil?: number; satirlar?: PDegerSatiri[];
  omur_ortalamasi?: { bicim: string; n_yil: number; p50: number; p75: number; p90: number; p95: number; p99: number };
  omur_toplami?: { bicim: string; n_yil: number; p50: number; p75: number; p90: number; p95: number; p99: number };
  kiyas?: { yil: number; n: number; durum: "tam_yil" | "kapsam_yetersiz" | "cari_yil" | "cari_pay_yok"; kapsam_pct?: number; ytd_pay?: number | null; gerceklesen_kwh: number;
    p50_kwh: number; p90_kwh: number; oran_p50: number | null; oran_p90: number | null; konum: "ustu" | "arasi" | "alti" | null; butce_orani: number | null }[] }
/** /bankable — v2.278: yıllık P50/P90 (1 ve 10 yıl), belirsizlik bütçesi, TMY. */
export interface Bankable {
  durum: string; hesap_zamani?: string; kaynak?: string; donem?: string; mod?: string; not?: string;
  p50_kwh?: number; ozgul_verim_kwh_kwp?: number; sigma_toplam?: number; yil_sayisi?: number; N_yil?: number;
  bilesenler?: Record<string, number>; bir_yil?: Record<string, number>; n_yil?: Record<string, number>;
  /** v2.283: bileşen katkıları (%), çarpımsal sınama ve ölçüm kalibresi bilgisi */
  katki_pct?: Record<string, number>; olcumle_kalibre?: boolean;
  monte_carlo?: { p90_1yil: number; p99_1yil: number; not?: string };
  ghi?: { p50_kwh_m2: number; p90_kwh_m2_1yil: number; sigma_yillar_arasi: number };
  yillar?: { yil: number; kwh: number; ghi_kwh_m2: number }[];
  tmy?: { secilen_yillar?: Record<string, number>; p90_yili?: number; p90_yili_ghi?: number; tmy_ghi_kwh_m2?: number; hata?: string };
  /** v2.281: tarife tanımlıysa yıllık gelir */
  gelir?: { tip: string; fiyat_tl_mwh: number; p50_tl: number; p90_1yil_tl: number; p90_nyil_tl: number; not?: string | null };
}
/** /epias-uretim — v2.278: EPİAŞ gerçekleşen üretim akışı durumu. */
export interface EpiasUretim { uygun: boolean; neden: string; epias_santral_id: number | null; n_saat: number; son: string | null }
/** /portfoy/tahmin — v2.280: hiyerarşik uzlaştırılmış portföy tahmini. */
export interface PortfoyTahmin {
  durum: string; santral?: number; yontem?: string; tutarli?: boolean; n_saat?: number; kapasite_kwp?: number; artik_gun?: number; not?: string;
  santral_eksik?: string[];   // 03.11: koşusu olmayan santraller (tabloda yok; özet kartı «—» gösterir)
  gunler?: { gun: string; p50_mwh: number; p10_mwh: number; p90_mwh: number; saat: number }[];
  santral_bugun_mwh?: Record<string, number>;
}
/** /portfoy/dsg — v2.276: DSG netleştirmesi. */
export type DsgAnahtar = "sapma" | "esit" | "uretim";
/** v2.511 (04 #14): toplayıcı/GTŞ portföyü — KÜPST UEVÇB bazında; santrallere dağılım anahtarı sözleşmesel (mevzuatta tanımsız) */
export type PortfoyAnahtar = "sapma" | "uretim" | "kurulu" | "esit";
export interface PortfoyKupst {
  santral: number; kupst_toplam_tl: number | null; dagitim_anahtari: PortfoyAnahtar; dagitim_etiket: string; etiket: string;
  pencere_gun: number; fiyat: { epias_saat: number; senaryo_saat: number }; not?: string;
  uevcbler: { kod: string; kod_tanimsiz: boolean; /** v2.541 (DK-267) */ kod_kaynagi?: "uevcb" | "gts_adi" | "tanimsiz"; santraller: string[]; n_saat: number; kupst_tl: number | null; not?: string;
              udups_mwh?: number; kupsm_mwh?: number; uretim_mwh?: number; hesaplanamayan_saat?: number; kural_dayanak?: string; kural_surumu?: string;
              uyeler?: Record<string, { kupst_tl: number | null; pay_pct: number; sapma_mwh: number; uretim_mwh: number; kurulu_mw: number }> }[];
}
export interface PortfoyDsg {
  /** v2.502 (F-08): yürürlükteki kural — üye eşiği × PH grupta, aşan kısım bireysel; KÜPST üye bazında toplanır. gosterge=false.
   *  'kazanc_tl' = netleşme farkı (sözleşme adı; vaat değil). edt_* işaretli (negatif = katılımcı öder). */
  gosterge?: boolean;
  santral: number; n_saat: number; ayri_tl: number | null; net_tl: number | null; kazanc_tl: number | null; kazanc_pct?: number | null;
  edt_tek_tl?: number; edt_dsg_tl?: number; edt_grup_tl?: number; edt_bireysel_tl?: number; netlesme_farki_tl?: number; kupst_uye_tl?: number | null;
  esik?: number; esik_kaynak?: string; kural_surumu?: string; hesaplanamayan_saat?: number; disi?: string[]; segment_yok?: string[];
  /** v2.513: DUY Geçici m.39 — dağıtım/GTŞ DSG'lerinde üye eşiği 1.1.2027'ye kadar %100 (ekran notu; 2027'den sonra null) */
  gecici_m39?: string | null;
  /** 29.10: üye başına dağıtım — edt_dsg_tl = bireysel + pay × grup; netlesme_farki_tl = edt_dsg − edt_tek; pay_pct ortalama saatlik pay */
  uyeler?: Record<string, { kayip_tl: number; edt_tek_tl: number; edt_bireysel_tl: number; kupst_tl: number | null; sapma_mwh: number; grup_payi_mwh: number;
                            edt_dsg_tl?: number; netlesme_farki_tl?: number; pay_pct?: number }>;
  /** 29.10: grubun EDT'sinin üyelere dağıtım anahtarı (sapma | esit | uretim; sözleşmesel) ve Türkçe etiketi */
  dagitim_anahtari?: DsgAnahtar; dagitim_etiket?: string;
  santral_tl?: Record<string, number>; uretim_mwh?: number; sapma_net_mwh?: number; sapma_ayri_mwh?: number;
  pencere_gun: number; fiyat: { epias_saat: number; senaryo_saat: number }; not: string;
  /** v2.539 (EK-3 DK-258/261): DSG grupları santral kaydındaki koda göre; grup = gösterilen grup, varsayım = kod girilmemiş tek grup; dışarıda kalanlar nedeniyle */
  grup?: string | null; grup_kaynagi?: "beyan" | "varsayim"; disi_nedenleri?: Record<string, string>; katilimci_notu?: string;
  /** v2.541 (DK-252): aynı piyasa katılımcısı kodunu taşıyan santraller tek üye olarak toplandı */ katilimci_gruplari?: Record<string, string[]>;
  gruplar?: { kod: string | null; santral: number; uyeler: string[]; n_saat: number | null; ayri_tl: number | null; net_tl: number | null; kazanc_tl: number | null; not?: string | null; secili: boolean }[];
}
/** /kgup?fmt=json — v2.260 önizleme; /segment — v2.260. */
export interface KgupOnizleme {
  gun: string; kantil: string; kosu: { run_at?: string; mode?: string; kesim?: string; run_id?: string }; uyarilar: string[]; sicrama_saatleri: number[];
  toplam_mwh: number; satirlar: { saat: number; kgup_mwh: number; eak_mwh: number; eak_mw?: number }[]; dosya_adi: string;
  /** 29.10 (F-05/F-06): dosya özeti, şablon durumu, takvim, bildirim notu, dengeleme birimi bayrağı */
  sha256?: string; sablon?: { durum: string; kolonlar: string[]; ayrac: string; ondalik: string;
                              /** 29.10 (v2.506): müşteri dosyasından öğrenildiyse kaynağı */
                              kaynak?: { dosya: string; zaman: string; bicim: string } | null;
                              /** v2.512: saat yazımı («%H:00» TPYS), BOM, EAK dosyasının kolonları (TPYS EAK.csv) */
                              saat_bicim?: string; bom?: boolean; eak_kolonlar?: string[] };
  /** v2.512: EAK ayrı dosya (TPYS EAK.csv; ?fmt=eak) */
  bom?: boolean; eak_dosya_adi?: string; eak_sha256?: string;
  takvim?: { pencere_acilis: string; bytm_son: string; son: string; teyit: string }; bildirim?: string; dengeleme_birimi?: boolean; luy_istisna?: boolean;
  /** v2.275: o gün için etkin EAK ve kaynağı (gecici | eak_alani | ac_tavani | kurulu_guc) */
  eak?: { eak_mw: number; kaynak: string; bitis?: string };
  /** v2.287: GİP revizyon kapısı + önerilen kantil */
  gip?: { kural: string; ornek_teslimat: string; ornek_kapi: string; ornek_revizyon_son: string };
  oneri?: { durum: string; kantil: string | null; tau?: number; not?: string } | null;
  teslim: { hedef_gun: string; durum: string; dakika_kaldi: number; teyit_saati: string };
}
/** /kgup/revizyon — v2.507 (F-10): bugünün programı ↔ güncel beklenti; eşik üstü ve revize edilebilir saatler. Yol gösterici, kayıt yazmaz. */
/** /piyasa/durum — EPİAŞ kimliği tanımlı mı, son fiyat saati, fiyat/yön saat sayısı, senaryo değerleri. */
export interface PiyasaDurum { kimlik: boolean; son_fiyat: string | null; saat: number; yon_saat?: number; senaryo: { ptf: number; smf: number; ad: string } }
/** v2.513 (04 #14): /epias/uevcb-ara — kuruluş adıyla UEVÇB adayları (EPİAŞ Şeffaflık organization-list + uevcb-list) */
export interface UevcbArama { durum: string; toplam_kurulus: number; kuruluslar: { kurulus: string; kurulus_id: number | string; hata?: string | null; uevcbler: { id: number | string; eic: string | null; name: string | null }[] }[] }
export interface KgupRevizyon {
  durum: "ok" | "program_yok" | "tahmin_yok" | "gun_bitti"; gun: string; simdi: string; esik_oran: number; not: string;
  program_kaynagi: string | null; beklenen_kaynagi: string | null; toplam_fark_mwh?: number; ilk_revizyon_son?: string | null; taban_mwh?: number;
  saatler: { saat: number; ts: string; program_mwh: number; beklenen_mwh: number | null; fark_mwh: number | null; fark_oran: number | null;
             esik_mwh: number; revizyon_son: string; revize_mumkun: boolean; oneri: boolean }[];
  oneri_saatleri: number[];
}
/** /kgup/surumler — v2.502 (F-06): indirilen dosyaların değiştirilemez sürüm kaydı. */
export interface KgupSurum {
  id: string; teslim_gunu: string; surum: number; kantil: string; run_id: string | null; run_at: string | null; kesim: string | null;
  eak_mw: number | null; eak_kaynak: string | null; toplam_mwh: number | null; sha256: string; dosya_adi: string; olusturma: string;
  indiren: string | null; bayt: number;
  /** v2.517 (P2a, IH-001): teslim günü için GÖP teklif kapanışından (D-1 12:30) önce indirilen son öneri */
  gop_esas?: boolean;
  /** v2.503: pvquant (öneri/indirilen) | musteri (bildirildiği beyan edilen) | v2.513: eak (TPYS EAK.csv dosyası) */
  kaynak?: "pvquant" | "musteri" | "eak";
}
/** /kgup/kiyas — v2.503: son öneri ↔ müşterinin bildirdiği KGÜP, saat saat. */
export interface KgupKiyas {
  gun: string;
  oneri: { id: string; surum: number; sha256: string; zaman: string; toplam_mwh: number | null; kantil: string } | null;
  bildirilen: { id: string; surum: number; sha256: string; zaman: string; toplam_mwh: number | null; kantil: string } | null;
  saatler: { saat: number; oneri_mwh: number; bildirilen_mwh: number; fark_mwh: number }[];
  ozet: { fark_toplam_mwh: number; fark_mutlak_mwh: number; en_buyuk_fark_saat: number; en_buyuk_fark_mwh: number; farkli_saat: number; ayni: boolean } | null;
}
export const SEGMENTLER: { deger: string; etiket: string }[] = [
  { deger: "lisansli_serbest", etiket: "Lisanslı (serbest piyasa)" }, { deger: "lisansli_yekdem", etiket: "Lisanslı (YEKDEM)" },
  { deger: "yeka", etiket: "YEKA" }, { deger: "lisanssiz_iletim", etiket: "Lisanssız (iletim bağlantılı)" },
  { deger: "lisanssiz_dagitim", etiket: "Lisanssız (dağıtım, GTŞ/toplayıcı)" }, { deger: "oz_tuketim_saatlik", etiket: "Öz tüketim (saatlik mahsup)" },
];
/** /dengesizlik — v2.259: karnenin TL dili. 29.10 (F-01/02/03): EDT ve KÜPST ayrı; kural sürümü; hesaplanamayan saat;
 *  pvquant_tl/kupst_tl KÜPST hesaplanamıyorsa null (0 değil). 'kurtarilan_tl' = referans programa göre fark (sözleşme adı). */
export interface DengesizlikKural {
  tarih: string; kural_surumu: string; rejim: "2025" | "2026"; edt_dayanak: string; k: Record<string, number>; l: Record<string, number>;
  V: number | null; B: number | null; AFL: number | null; aylik_toplama: string;
  kupst_m: number | null; kupst_n: number | null; kupst_n_ariza: number | null; kupst_ariza_esigi: number | null; kupst_taban: number;
  kupst_net_sapma: boolean; kupst_birim: string; kupst_dayanak: string; dsg_esik: number | null; dsg_dayanak: string; belirsiz_2027: boolean;
}
/** v2.517 (P2a): piyasa pozisyonu ayarı — EDM = gerçekleşen − pozisyon */
export interface PozisyonAyari { kaynak: "program" | "uretim" | "sabit"; sabit_mwh: number | null; etiket: string }
/** v2.517 (P2a): saatlik uzlaştırma dökümü (JSON önizleme; CSV/XLSX ayrı indirilir) */
export interface DengesizlikSaatlik { satir: number; kolonlar: string[]; not: string; program?: Dengesizlik["program"]; toplam: Dengesizlik["toplam"];
  /** v2.539 (EK-3 DK-056): Olay kaydındaki talimat/acil kesme saatleri (yat | yal | acil) işaretli; hesap değişmez; v2.541: miktar girilmiş saat sayısı (BUDÜP sütunları) */ talimat_saat?: number; talimat_notu?: string | null; talimat_mw_saat?: number;
  satirlar: Record<string, string | number | null>[] }
export interface Dengesizlik { luy_istisna?: boolean;   // v2.510 (Ç3): santral ayarı, Santralim onay kutusunu doldurur
  gun_sayisi: number; pencere_gun: number; not: string;
  aylar: { ay: string; uretim_mwh: number; sapma_mwh: number; referans_gelir_tl: number; pvquant_tl: number | null; naif_tl: number | null;
           kurtarilan_tl: number | null; gelir_oran_pct: number | null; tl_per_mwh: number | null; kupst_tl?: number | null; dengesizlik_tl?: number;
           edt_neg_tl?: number | null; edt_poz_tl?: number | null; edta_tl?: number | null; edtb_tl?: number | null; hesaplanamayan_saat?: number; kural_surumu?: string;
           /** v2.517 (P2a): tolerans dışı saat (KÜPSM > 0), KÜPSM toplamı, bildirilen programla hesaplanan saat */
           tolerans_disi_saat?: number; kupsm_mwh?: number; bildirilen_saat?: number }[];
  toplam: { pvquant_tl: number | null; naif_tl: number | null; kurtarilan_tl: number | null; gelir_oran_pct: number | null; referans_gelir_tl: number;
            kupst_tl?: number | null; teminat_tl?: number | null; dengesizlik_tl?: number; edt_neg_tl?: number; edt_poz_tl?: number; edta_tl?: number; edtb_tl?: number;
            /** v2.541 (EK-3 DK-804, Karar 14626): takvim yılı negatif dengesizlik miktarı ↔ YEÜM (LDYEÜM girildiyse); yalnız (d) kalemi, alt sınır */
            yeum?: { yil: number; negatif_dengesizlik_mwh: number | null; saat: number; ldyeum_mwh: number | null; yeum_mwh: number | null; oran_pct: number | null; kapsam: string; kalemler_disinda: string[]; not: string; pencere_gun?: number };
            tolerans_disi_saat?: number; kupsm_mwh?: number;
            /** v2.522 (P2b): dengesizlik teminatı göstergesi — mevzuat formülü; risk katsayısı Santral ayarlarından, yoksa tutar yok */
            teminat?: { edm_neg_max_mwh: number | null; edm_ay: string | null; ay_sayisi?: number; smf_ort_tl_mwh: number | null; smf_ay_sayisi: number; risk_katsayisi: number | null; tutar_tl: number | null; dogrulanmis: boolean; formul: string; not: string } } | null;
  /** v2.517 (P2a): programın kaynağı — bildirilen KGÜP (müşteri beyanı) saat/gün sayısı, kalan öneri; pozisyon ayarı (program | uretim | sabit) */
  program?: { bildirilen_saat: number; oneri_saat: number; bildirilen_gun: number; pozisyon: PozisyonAyari;
    /** v2.532 (DK-180/195): net sapma saatlerinde UEÇM kaynağı — sayaç çekişi bilinen saat sayısı; yoksa 0 varsayıldı */
    uecm_saat?: number; net_sapma_saat?: number; uecm_etiketi?: string | null };
  /** v2.287: önerilen bildirim kantili (senaryo fiyatta null + not; yön verisi yoksa durum 'yon_eksik') */
  oneri?: { durum: string; kantil: string | null; tau?: number; n_saat?: number; acik_saat_orani?: number; not?: string };
  katsayilar?: { k: number; l: number; kupst_n: number | null; kupst_tolerans?: number | null; k_yon?: Record<string, number>; l_yon?: Record<string, number>;
    /** v2.535: KÜPST n/tolerans santral ayarından geçersiz kılındı mı (resmî tablo `kural` alanında kalır) */
    kupst_gecersiz_kilma?: boolean; kupst_kaynak?: string };
  fiyat: { epias_saat: number; senaryo_saat: number; yon_varsayilan_saat?: number; yon_eksik_saat?: number };
  hesaplanamayan_saat?: number; kural_surumu?: string | null; kural?: DengesizlikKural;
  /** v2.543 (P9, IH-109): uzlaştırma dönemi / SMF çözünürlüğü — saatlik; 15 dk geçişi belirsiz etiketli */ cozunurluk?: { deger: string; kesinlik: string; gecis_hukuki: string; etiket: string };
  segment: { segment: string | null; kgup_yukumlu: boolean | null; dengesizlik_sahibi: string | null; santral_tasir: boolean | null; uevcb?: string | null;
    /** v2.543 (P9): depolama ünitesi beyanı ve kural eşikleri (hazırlık) */ depolama?: Depolama;
    /** v2.539 (EK-3 DK-258/261): DSG adı/kodu (beyan) ve toplayıcı portföyü işareti; v2.540 (DK-612): YEK-G kaydı */ dsg_kodu?: string | null; toplayici_portfoyu?: boolean; yek_g_kayitli?: boolean;
    /** v2.541: aynı kodlu santraller DSG'de tek üye (DK-252); lisanstaki yıllık üretim (LDYEÜM, Karar 14626; DK-804) */ piyasa_katilimcisi?: string | null; lisans_yillik_uretim_mwh?: number | null;
    /** v2.541 (EK-2 DK-267): UEVÇB kodu yoksa portföy KÜPST gruplaması bu ada göre */ gts_toplayici_adi?: string | null };
}
/** /dengesizlik/geri-test — v2.503 (F-07): 12 aylık uzlaştırma kalemleri geri testi; karşı-olgu sütunları; varsayımsal yeniden hesap. */
export interface DengesizlikGeriTest {
  gun_sayisi: number; pencere_gun?: number; baslik: string; kural_surumu?: string;
  aylar: { ay: string; gun: number; uretim_mwh: number; sapma_mwh: number; eksik_tl: number | null; fazla_tl: number | null; kupst_tl: number | null;
           toplam_tl: number | null; karsi_2026_tl: number | null; karsi_v100_tl: number | null; referans_tl: number | null; hesaplanamayan_saat: number; kural_surumu: string }[];
  toplam: { eksik_tl: number | null; fazla_tl: number | null; kupst_tl: number | null; toplam_tl: number | null; karsi_2026_tl: number | null; karsi_v100_tl: number | null;
            referans_tl: number | null; uretim_mwh: number; referans_gelir_tl: number | null; tl_per_mwh?: number; referans_fark_tl?: number | null } | null;
  mekanizma: { saat: number; acik_saat: number; fazla_saat: number; dengede_saat: number; b_dali_saat: number; afl_dali_saat: number; v_tabani_saat: number;
               b_dali_tl: number | null; afl_dali_tl: number | null; senaryo_saat: number; yon_varsayilan_saat: number; yon_eksik_saat: number; hesaplanamayan_saat: number } | null;
  fiyat?: { epias_saat: number; senaryo_saat: number; yon_varsayilan_saat?: number; yon_eksik_saat?: number };
  segment?: { segment: string | null; kgup_yukumlu: boolean | null; dengesizlik_sahibi: string | null; santral_tasir: boolean | null };
  /** v2.508 (04 #2): hata duyarlılığı — santralin kendi hata deseni hedef WMAPE'ye ölçeklenir; varsayımsal */
  duyarlilik?: { yontem: string; wmape_gercek: number; uretim_mwh: number; not: string;
                 seviyeler: { wmape_hedef: number; wmape_elde: number; gercek: boolean; eksik_tl: number | null; fazla_tl: number | null; kupst_tl: number | null; toplam_tl: number | null; tl_per_mwh: number | null }[] } | null;
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
  /** v2.297: ufuk kovası sınavı — ham / tek q̂ / kova q̂ kapsaması kova başına. */
  kova_sinav?: { pencere: number; hedef?: number; hukum: string;
    kovalar: { kova: string; n: number; picp_ham: number; picp_tek: number; picp_kova: number; bant_kova_n: number }[] };
}
/** /fizik-terimleri — v2.274: santral bazında fizik terimleri (aç/kapa) + önizleme. */
export interface FizikTerimleri {
  iam_model: string; spectral_model: string; soiling_model: string; kar_model: string;
  soiling_gunluk_kayip: number | null; soiling_temizleme_mm: number | null; soiling_baslangic: number | null;
  secenekler: Record<string, string[]>; etiket: Record<string, string>; not: Record<string, string>;
}
export interface FizikOnizleme {
  gun: { tarih: string; mevcut_kwh: number; aday_kwh: number; fark_pct: number | null }[];
  toplam_mevcut_kwh: number; toplam_aday_kwh: number; toplam_fark_pct: number | null;
  nem_var: boolean; kar_var: boolean; yagis_var: boolean; kaynak: string;
}
/** /guvenilirlik — v2.271: kantil güvenilirliği, PIT, keskinlik (ham ↔ kalibre). */
export interface Guvenilirlik {
  durum: "ok" | "yetersiz" | "veri_yok"; n_saat: number; gun_sayisi?: number; min_saat?: number; pencere_gun?: number;
  guvenilirlik?: { ham: { tau: number; gozlenen: number; sapma: number; n: number }[]; kalibre: { tau: number; gozlenen: number; sapma: number; n: number }[] };
  pit?: { kutu: string; oran: number }[]; pit_max_sapma?: number;
  keskinlik?: { ham: number; kalibre: number }; aralik_skoru_n?: { ham: number; kalibre: number }; picp80?: { ham: number; kalibre: number };
}
/** /kayma — v2.253: eğitim (arşiv) / servis (tahmin) meteo kayması. */
export interface Kayma {
  n_saat: number; hukum: string; gun?: number; baslangic?: string; bitis?: string;
  /** v2.282: eğitim meteosu alınamadıysa neden (dürüst boş sonuç) */
  not?: string;
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
  /** v2.568: program kovası (D-1 KGÜP kesimi öncesi son koşu) — ayrı KPI; kova satırı yoksa null */
  program?: { wmape_ort: number | null; gun_sayisi: number; naife_ustunluk_pct: number | null } | null;
  wmape_ort: number | null; naife_ustunluk_pct: number | null;
  ilk_tarih: string | null; son_tarih: string | null;
  /** v2.247: SFA sozlugu — kapasiteye normalize yuzdeler (eski kayitlarda null). */
  nmae_ort?: number | null; nrmse_ort?: number | null; nmbe_ort?: number | null;
  /** v2.279: iklimsel + persistans optimal birleşim referansı (Yang 2019) — bu referansı geçemeyen model beceri iddia edemez. */
  cliper_wmape_ort?: number | null; cliper_ustunluk_pct?: number | null;
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

/** /saat-profili yanıtı — apps/api/main.py v2.532 ile birebir (saat × gün matrisi 04.11.2026'da kaldırıldı; Kalibrasyon sayfası). */
export interface SaatProfili {
  saatler: string[];
  profil: { saat: string; ort_hata_kw: number | null; ort_mutlak_kw: number | null; n: number }[];   // p50 − gerçek, kW; saat başına ortalama
  gun_sayisi: number; ilk_gun: string | null; son_gun: string | null;
  /** |ortalama işaretli hata| ≥ %5 kapasite ve n ≥ 5 olan saatler */
  sistematik: { saat: string; yon: "fazla" | "eksik"; ort_hata_kw: number; n: number }[];
  esik_kw: number; metrik: string; birim: string; tz: string;
}

/** /monthly yaniti — apps/api/main.py v2.78-B ile birebir. */
export interface AylikBeklenti {
  plant_id: string;
  hesap_zamani: string;
  /** v2.317 — iklim penceresi veriden ("2006\u20132025"); hesaplanmadiysa null. */
  donem?: string | null;
  yil_sayisi?: number | null;
  beklenti: { ay: number; p10: number | null; p50: number | null;
              p90: number | null; yil_sayisi: number }[];
  yillik: { yil: number; ay: number; ghi_kwh_m2: number | null }[];
}

/** v2.289: kuruluşlar arası veri paylaşımı. */
export interface Paylasim { id: string; santral: string; takma_ad: string | null; kapasite_kwp: number | null;
  karsi_kurulus: string; izinler: string[]; bitis: string | null; iptal: boolean; aktif: boolean; }
export interface PaylasimListesi { verilenler: Paylasim[]; alinanlar: Paylasim[];
  izin_secenekleri: { deger: string; etiket: string }[]; }
export interface PaylasilanVeri { santral: string; kapasite_kwp?: number | null; not?: string;
  gunler?: { gun: string; p50_kwh?: number | null; p10_kwh?: number | null; p90_kwh?: number | null; kwh?: number }[];
  gun?: number; wmape_pct?: number | null; nmae_pct?: number | null; picp80?: number | null; }

/** v2.294: kamuya açık doğrulama karnesi. */
export interface Dogrulama { durum: "acik" | "kapali"; santral_etiketi?: string; pencere_gun?: number;
  son_gun?: string; wmape_pct?: number | null; naif_wmape_pct?: number | null;
  siki_referans_wmape_pct?: number | null; nmae_pct?: number | null; beceri_naif_pct?: number | null;
  beceri_siki_pct?: number | null; bant_kapsama_pct?: number | null; bant_hedef_pct?: number;
  aylar?: { ay: string; gun: number; wmape_pct: number | null; naif_wmape_pct: number | null;
            bant_kapsama_pct: number | null }[]; not?: string; }

/** v2.299: ekip yönetimi. */
export interface TakimUyesi { id: string; email: string; rol: string; aktif: boolean;
  son_giris: string | null; olusturma: string | null; iki_adim?: boolean; }

/** v2.301: gece işleri görünürlüğü. */
export interface Isler { isler: { is: string; zaman: string; sure_sn: number | null; tamam: boolean }[];
  pencere_saat: number; gece_calisiyor: boolean; son_gece_isi: string | null; not: string | null;
  bayat_isler?: string[];
  /** v2.359: "uyari" = gerçek bayatlık; "bilgi" = santral yok / ilk gece bekleniyor. */
  seviye?: "uyari" | "bilgi" | null; }

/** v2.351: JSON raporu (şema 1.2.0) — panel önizlemesi için tip. Alan adları
 *  dosyayla birebir; makine adları (run.model vb.) burada da ham kalır, görünür
 *  ad eşlemesi bileşende yapılır. */
export interface RaporJson {
  schema_version: string;
  schema_url: string;
  report_id: string | null;
  generated_at: string;
  conventions: { timestamp: string; period: string; timezone: string; missing: string };
  units: Record<string, string>;
  plant: { name: string; capacity_kwp: number; latitude: number; longitude: number; timezone: string };
  run: { model: string; model_version: string; mode: string; meteo_source: string; run_at: string };
  totals: { p50_mwh: number; p10_mwh: number | null; p90_mwh: number | null;
            capacity_factor_pct: number; specific_yield_kwh_kwp: number };
  daily: { date: string; p50_kwh: number; p10_kwh: number | null; p90_kwh: number | null }[];
  hourly: { ts: string; p50_kw: number; p10_kw: number | null; p90_kw: number | null; energy_kwh: number }[];
  accuracy: {
    window_days: number; last_measured_date: string;
    wmape_pct: number | null; nmae_pct: number | null; naive_wmape_pct: number | null;
    skill_vs_naive_pct: number | null; band_coverage_pct: number | null; band_target_pct: number;
    daily: { date: string; measured: boolean; wmape_0_24: number | null; wmape_24_72: number | null;
             naive_wmape: number | null; skill: number | null; coverage_pct: number | null }[];
  } | null;
  quality: {
    mape_pct: number | null; deviation_pct: number | null; eta_bos: number | null; bg: number | null;
    hybrid?: { holdout_mape_pct: number; holdout_rmse_kw: number | null; physics_mape_pct: number | null;
               improvement_pct: number | null; holdout_hours: number | null; note: string | null };
    warnings: string[];
  };
}

/** 26.10 Faz 6 — kuruluş: kiracı içi denetim izi kaydı (platform tipiyle aynı alanlar) ve ayarlar. */
export interface DenetimKaydi { id: number; zaman: string; kapsam: string; aktor_id: string | null; aktor_eposta: string | null; tenant_id: string | null;
  eylem: string; nesne_tur: string | null; nesne_id: string | null; ayrinti: Record<string, unknown>; ip: string | null }
export interface KurulusAyarlar { yonetici_2fa_zorunlu: boolean; iki_adimsiz_yonetici: number }

/** v2.518 (P3a): piyasa ve mevzuat takvimi — olay (kaynak_turu: mevzuat | hesaplanan | duyuru | kunye [Santral tarihleri formundan];
 *  kaydirma: is_gunu | yok | belirsiz) */
export type TakvimOlay = { kod: string; ad: string; tarih: string; saat: string | null; kaynak: string; kaynak_turu: "mevzuat" | "hesaplanan" | "duyuru" | "kunye";
  /** v2.535: kaynak metnindeki anılışların Resmî Gazete yayımları (tarih-sayı) */ dayanak?: string[];
  kaydirma: "is_gunu" | "yok" | "belirsiz"; kapsam: string[]; donem: string | null; not: string | null; hafta_sonu: boolean; tatil: boolean; kalan_gun?: number;
  /** v2.524 (P3b): kaçırılınca — ilgili madde ve ihtar süresi; bent eşlemesi «çıkarım» etiketli, tutar yok */ sonuc?: string | null; sonuc_kisa?: string | null;
  /** işlem gerekli (santral) / takip edilmeli (başkasının adımı) / mevzuat değişikliği / doğrulama gerekli (koşul PVQuant'ta kayıtlı değil) */ islem?: "islem" | "takip" | "mevzuat" | "dogrulama"; sorumlu?: string | null };
/** v2.524 (P3b): olay kaydındaki planlı bakım için TEİAŞ bildirim son anı (Elektrik Şebeke Yön. m.54) */
export type TakvimBakim = { olay_id: string; baslangic: string; bitis: string | null; etkilenen_kw: number | null; sure_saat: number | null; kural: string; son_an: string | null; gecti: boolean; kaynak: string };
export type KunyeTarihler = { alanlar: Record<string, string | number | null>;
  turetilen: { lisans_kalan_gun: number | null; lisans_bedeli_muafiyet_bitis: string | null; ilerleme_raporu_yukumlu?: boolean; isg_sonraki_kontrol?: string | null;
    yekdem: { rejim: string; ilk_yil: number; son_yil: number; yek_bitis?: string; yerli_katki_bitis?: string; kaynak: string; kaynak_turu: string } | null;
    police_kalan_gun: number | null };
  etiketler: Record<string, string> };
export type Takvim = { bugun: string; pencere_gun: number; segment: string | null; kgup_yukumlu: boolean | null; yaklasan: TakvimOlay[];
  uyum: TakvimOlay[]; bakim: TakvimBakim[]; uyum_not: string; bakim_kaynak: string; yaklasan_piyasa?: TakvimOlay[]; islem_etiketleri?: Record<string, string>;   // v2.524 (P3b)
  donemler: { donem: string; olaylar: TakvimOlay[] }[];
  gunluk: { saat: string; ad: string; kaynak: string; kapsam: string[]; not: string | null; gunler: "her gün" | "iş günü" }[];
  kunye: KunyeTarihler; tatil_kaynak: string; tatil_yillari: number[]; not: string;
  /** v2.535: dinî bayramı tanımlı olmayan yıla düşen tarih varsa o yıllar (iş günü hesabı bayramı iş günü sayar) */
  tatil_eksik_yillar?: number[];
  /** v2.541 (EK-2 DK-659): lisanssız tesiste LÜY rejimi — ölçüt çağrı mektubuna hak kazanma tarihi (12.05.2019) */
  luy_rejimi?: { rejim: "m25" | "m26" | null; etiket: string; olcut: string | null; tarih: string | null; kesinlik: "teyit" | "yorum" | "belirsiz"; not: string } | null };
/** v2.521 (P1a): olay kaydı — planlı bakım, arıza, talimat, acil kesme, şebeke kesintisi, hasar; EAK/program, arıza sayacı ve kullanılabilirlik bunlardan beslenir. */
export type OlayTur = "planli_bakim" | "ariza" | "talimat_yat" | "talimat_yal" | "acil_kesme" | "sebeke_kesintisi" | "hasar" | "uzaktan_acma";   // v2.523 (P4a): uzaktan açma yapılamadı
export interface OlayKural { eak_dusur: boolean; gerekce: string | null; istisna: boolean; sayac: boolean; not: string }
export interface Olay { id: string; plant_id: string; tur: OlayTur; tur_etiket: string; baslangic: string; bitis: string | null; etkilenen_kw: number | null; neden: string | null;
  eak_gerekcesi: string | null; kanit: string | null; durum: "acik" | "kapali" | "iptal"; acik: boolean; evre: "planli" | "suruyor" | "bitti" | "iptal"; olusturma: string; guncelleme: string | null; kural: OlayKural;
  /** v2.541 (EK-3 DK-741/743): acil kesmede şebeke işletmecisinin sona erme bildirimi (LÜY m.21(8), 15 dk) ve gecikmesi; YAL/YAT talimat miktarı (kayıt) ve gerekçe son günü (DUY m.71/A, 3 iş günü) */
  bildirim_zamani?: string | null; bildirim_gecikme_dk?: number | null; bildirim_15dk_asildi?: boolean | null; talimat_mw?: number | null; gerekce_son_gunu?: string | null }
export interface OlayOzet { bugun: string; pencere_gun: number; olaylar: Olay[]; acik: number; planli: number;
  ariza_sayaci: { sayi: number; olay: number; elle: number; kaynak: string; esik: number; uyari: number; ay: string };
  eak_bugun: { saat_sayisi: number; en_cok_kw: number; taban_kw: number; kismi_saat: number; suren: number };
  aciklama: { kapasite: string; sayac: string; kullanilabilirlik: string; islem: string; gerekce: string;
    /** v2.538 (EK-3 DK-733/DK-740): talimat tutarının yansıtılması — segmente göre lisanssız / lisanslı metni */ talimat?: string;
    /** v2.541 (DK-741/743): sona erme bildirimi ve gerekçe süresi */ bildirim?: string };
  /** v2.538 (EK-3 DK-613): 1 saat kuralının yürürlüğü 01.01.2027 (çıkarım); basladi = olay başlangıcı yürürlükten sonra */
  dahili_bilgi: { olay_id: string; tur: string; esik: string; etkilenen_kw: number; son_saat: string; kalan_dk: number; gecti: boolean; yururluk: string; basladi?: boolean; yururluk_notu?: string; kosul?: string | null; not: string }[];
  dahili_yururluk?: { tarih: string; etiket: string; basladi: boolean; not: string }; segment?: string | null;
  /** v2.540 (EK-3 DK-612): YEK-G sisteminde kayıtlı tesiste arıza/plansız bakım eşiksiz (Karar 14967 Ek sıra 17; fıkra 3(b) koşulu) */ yek_g_kayitli?: boolean; yek_g_notu?: string;
  turler: ({ kod: OlayTur; etiket: string } & OlayKural)[]; gerekceler: { kod: string; etiket: string }[]; not: string }
/** v2.523 (P4a): sayaç izleme — OSOS/MASS/EPYS sayaç serisi (SCADA'dan ayrı), geliş beklentisi, SCADA ↔ sayaç farkı, lisanssız SCADA durumu */
export type SayacKaynak = "osos" | "mass" | "epys" | "elle";
export type SayacNitelik = "olculmus" | "tahmini" | "doldurulmus" | "elle" | "yok";
export interface SayacYukleme { yukleme_id: string; kaynak: SayacKaynak; kaynak_etiket: string; dosya_adi: string | null; sha256: string | null; bicim: string | null; bas: string | null; bit: string | null;
  n_saat: number; n_satir: number; nitelik_sayim: Record<string, number>; uyarilar: string[]; zaman: string }
export interface SayacYuklemeYanit { yukleme_id: string; kaynak: SayacKaynak; kaynak_etiket: string; dosya_adi: string; sha256: string; bicim: string; bas: string; bit: string; n_saat: number; n_satir: number;
  cozunurluk_dk: number; nitelik_sayim: Record<string, number>; toplam_veris_kwh: number; kolonlar: { zaman: string; veris: string; cekis: string | null; nitelik: string | null }; uyarilar: string[];
  atlanan?: { okunamayan: number; gelecek: number; negatif: number; yinelenen: number } }
export interface SayacGun { gun: string; scada_kwh: number | null; sayac_kwh: number | null; ortak_scada_kwh: number | null; ortak_sayac_kwh: number | null; fark_kwh: number | null; fark_pct: number | null;
  saat_scada: number; saat_sayac: number; saat_ortak: number; saat_tahmini: number; saat_olculmus: number; olc_fark_pct: number | null }
/** toplam çifti: fark = sayaç − SCADA; yüzde SCADA toplamına oranla */
export interface SayacKiyas { saat: number; scada_kwh: number | null; sayac_kwh: number | null; fark_kwh: number | null; fark_pct: number | null }
export interface SayacFark { pencere_gun: number; bas: string; bit: string; gunler: SayacGun[];
  /** yalnız ölçülmüş sayaç saatleri ↔ tahmini/doldurulmuş dâhil bütün ortak saatler; kapsam = ortak saat / pencere */
  olculmus: SayacKiyas; tahmini_dahil: SayacKiyas; kapsam: { pencere_saat: number; ortak_saat: number; ortak_pct: number | null; yalniz_scada_saat: number; yalniz_sayac_saat: number; ikisi_de_yok_saat: number };
  toplam: { scada_kwh: number; sayac_kwh: number; ortak_scada_kwh: number | null; ortak_sayac_kwh: number | null; saat_scada: number; saat_sayac: number; saat_ortak: number; saat_tahmini: number; fark_kwh: number | null; fark_pct: number | null };
  en_buyuk_fark: { gun: string; fark_kwh: number; fark_pct: number } | null; kaynak_sayim: Record<string, number>; sayac_kaynak_sayim: Record<string, number>; pencere_saat: number; aciklama: string }
export interface SayacDonemKapsam { vadesi_gelen: number; yuklu: number; olculmus: number; tahmini: number; eksik: number; tam_ay: boolean }
export interface SayacDonem { donem: string; sayac_veri: string; itiraz_son: string; kalan_saat: number; gecti: boolean; hafta_sonu: boolean; not: string | null; kaynak: string; kapsam: SayacDonemKapsam }
/** bu ayın saat sınıflandırması: vadesi gelen (m.8(2) saat + 2 sa) / vadesi gelmemiş / yüklü (ölçülmüş, tahmini) / eksik (vadesi gelen ama PVQuant'ta yok) */
export interface SayacSiniflama { gecen_saat: number; vadesi_gelen: number | null; vadesi_gelmemis: number | null; yuklu: number; yuklu_olculmus: number; yuklu_tahmini: number; eksik: number | null; not: string }
export interface SayacGelis { sayac_turu: string | null; sayac_turu_etiket: string | null;
  beklenen: { kural: string; dayanak: string | null; kesinlik: "belirsiz" | "mevzuat" | null; not: string | null; son_beklenen_saat: string | null; son_beklenen_dilim: string | null };
  son_sayac: string | null; son_scada: string | null; son_sayac_saat_once: number | null; ay: string; ay_sayac_saat: number; ay_beklenen_saat: number | null; ay_eksik_saat: number | null;
  siniflama: SayacSiniflama; donemler: SayacDonem[]; kaynak: string }
export interface SayacBedelKalem { kod: string; etiket: string; kat: number; birim: string; tutar_tl: number | null; kesinlik?: string; not?: string;
  /** askı (LÜY Geçici m.14(2)): (f)/(g) kapsamda; (ç) askıda değil (v2.538, DK-656) */ aski?: "kapsamda" | "askida_degil" | "dogrulanmadi"; uyari_tarihi?: string; sure_sonu?: string }
export interface SayacScada { yukumlu: boolean; esik_kw: number; kurulu_kw: number; kurulu_kaynak: string;
  /** anlaşma tarafı: dağıtıma bağlı (Dağıtım Sistemine Bağlantı Anlaşması, Karar 14909) ya da iletime bağlı (TEİAŞ; gösterge yok); m.75(4) kapsamı 900 kW+ */
  anlasma: "dagitim" | "iletim"; m75_kapsam: boolean; m75_esik_kw: number;
  durum: string | null; durum_etiket: string; durum_kaynagi: "beyan"; kopukluk_baslangic: string | null; kopukluk_gun: number | null;
  /** v2.538 (DK-735): 900 kW kıyası AC sınırıyla (teyit) ya da DC kWp ile (belirsiz); (DK-656) dağıtım şirketi uyarı tarihi ve (ç) süre sonu */
  m75_kesinlik?: "teyit" | "belirsiz"; uyari_tarihi?: string | null; uyari_sure_sonu?: string | null;
  uzaktan_acma_var: boolean | null; uzaktan_acma_ay: number; bedel_tl_ay: number | null; kalemler: SayacBedelKalem[]; uygulanmayan: string[]; toplam_tl: number | null;
  toplam_aski_tl: number | null; toplam_aski_disi_tl: number | null; aski_kapsami: string; tutar_niteligi: "varsayimsal";
  aski_bitis: string; aski_kesinlik: string; aski_gecti: boolean; aski_kalan_gun: number; kaynak: string; dayanak_yukumluluk: string; not: string }
export interface SayacAyar { sayac_turu?: string | null; scada_durum?: string | null; scada_kopukluk_baslangic?: string | null; scada_uyari_tarihi?: string | null; uzaktan_acma_var?: boolean | null; sistem_kullanim_bedeli_tl_ay?: number | null;
  /** v2.526 (P4a-2): uzlaştırma yeniden hesabında gerçekleşen üretim kaynağı */ uzlastirma_girdi?: "scada" | "sayac" | null }
export interface SayacOzet { bugun: string; pencere_gun: number; segment: string | null; ayar: Required<SayacAyar>; gelis: SayacGelis; fark: SayacFark; scada: SayacScada | null; scada_notu: string | null; yuklemeler: SayacYukleme[];
  kaynaklar: { kod: SayacKaynak; etiket: string }[]; nitelikler: { kod: SayacNitelik; etiket: string }[]; sayac_turleri: { kod: string; etiket: string }[]; scada_durumlari: { kod: string; etiket: string }[];
  uretim_secenekleri: { kod: "scada" | "sayac"; etiket: string }[]; not: string }
/** v2.526 (P4a-2): yeniden hesapta üretim kaynağı sayımı ve sayaç ↔ SCADA kıyası */
export interface UretimKaynak { secim: "scada" | "sayac"; etiket?: string; sayac_olculmus_saat: number; sayac_tahmini_saat: number; scada_saat: number; sayac_kullanilmayan_saat?: number;
  kiyas?: { edt_net_fark_tl?: number; kupst_fark_tl?: number; scada_saat?: number; not?: string; hata?: string } | null }
/** v2.525 (raporlama): dönem raporu (ay / çeyrek / yıl) önizlemesi ve zamanlanmış gönderim ayarı */
export interface RaporDonem { tur: "ay" | "ceyrek" | "yil"; kod: string; bas: string; bit: string; etiket: string; kirpildi: boolean; saat: number }
export interface RaporDonemVeri { donem: RaporDonem; santral: string; kapasite_kwp: number; ac_kw: number | null;
  ozet: { uretim_kwh: number | null; beklenen_kwh: number | null; veri_durumu: "tam" | "kismi" | "yok"; veri_durumu_metni: string; ortak_gun: number; sapma_pct: number | null; gun_sayisi: number; veri_gun: number; saat: number; beklenen_saat: number; kapsam_pct: number | null;
    olay: number; ariza: number; en_iyi_gun: { gun: string; kwh: number } | null; en_dusuk_gun: { gun: string; kwh: number } | null };
  gunler: { gun: string; kwh: number | null; saat: number; p50_kwh: number | null; p10_kwh: number | null; p90_kwh: number | null; sapma_pct: number | null }[];
  aylar: { ay: string; uretim_kwh: number; beklenen_kwh: number; saat: number; gun: number; sapma_pct: number | null }[] | null;
  olaylar: { tur: string; etiket: string; baslangic: string; bitis: string | null; sure_saat: number; etkilenen_kw: number; neden: string | null; istisna: boolean; ariza: boolean }[];
  kullanilabilirlik: { oran: number; ariza_esdeger_saat: number; istisna_esdeger_saat: number; saat: number; not: string } | null;
  /** v2.542 (P8b-2): dönemin ölçülen havayla beklenen üretimi ve EPI'si; hesap alınamazsa durum ≠ ok */
  performans?: { durum: string; epi?: number | null; uretim_kwh?: number; beklenen_kwh?: number; referans?: string; sicaklik?: string; sensor?: string | null; not?: string;
    isinim?: { durum: string; yil: number | null; not: string }; aylar?: { ay: string; uretim_kwh: number; beklenen_kwh: number | null; epi: number | null; epi_temiz: number | null; isinim_endeksi: number | null; poa_kapsam: number }[] } | null;
  pr: { pr: number; gun: number; e_kwh: number; h_kwh_m2: number; not: string } | null;
  uzlastirma: { satirlar?: { kalem: string; pvquant_alacak_tl: number | null; pvquant_borc_tl: number | null; epias_alacak_tl: number | null; epias_borc_tl: number | null }[]; saat?: number;
    guvenilirlik?: string | null; nedenler?: string[]; bildirim?: { surum: string; zaman: string } | null; hata?: string | null } | null;
  notlar: string[]; kaynaklar: string[]; uretim_zamani: string }
export interface RaporGonderim { aktif: boolean; gun: number; alicilar: string[]; son_gonderim?: string | null; son_durum?: string | null; son_donem?: string | null; deneme?: number; varsayilan_alicilar: string[]; posta_yapilandirildi: boolean }
export interface RaporGonderimSonuc { durum: "gonderildi" | "gonderim_hatasi" | "rapor_hatasi" | "posta_yapilandirilmadi" | "alici_yok"; donem: string; etiket: string; alici: number; zaman: string }
/** v2.522 (P2b-1): EPİAŞ uzlaştırma bildirimiyle kalem kalem mutabakat */
export type MutabakatDurum = "uyumlu" | "fark" | "senaryo" | "hesaplanamaz" | "bildirimde_yok" | "hesap_yok";
export interface MutabakatSatir { kod: string; etiket: string; hesaplanir: boolean; kalem_ad: string | null; bildirim_alacak_tl: number | null; bildirim_borc_tl: number | null;
  pvquant_alacak_tl: number | null; pvquant_borc_tl: number | null; pvquant_not: string | null; kaba: boolean; fark_tl: number | null; fark_pct: number | null;
  fark_alacak_tl?: number | null; fark_borc_tl?: number | null; bilesen_notu?: string | null; durum: MutabakatDurum;
  /** 02.11 inceleme: hükmün doğrulama niteliği — tam (gerçek verilerle) | kismi | senaryo; hesaplanamayan satırda null */ dogrulama?: "tam" | "kismi" | "senaryo" | "yok" | null }
/** sürüm etiketi ↔ resmî takvim (DUY m.132/A–B); EPİAŞ durumu dosyadan doğrulanamaz → resmi_durum her zaman «dogrulanmadi» */
export interface SurumDogrulama { durum: "takvim_uyumlu" | "takvimden_once"; resmi_durum: "dogrulanmadi"; beklenen_tarih: string; on_bildirim: string; nihai_bildirim: string; itiraz_son: string; itiraz_60: string; aciklama: string; kaynak: string }
export interface MutabakatGuvenilirlik { durum: "gercek" | "kismi" | "senaryo" | "veri_yok"; etiket: string; nedenler: string[] }
export interface Mutabakat { donem: string; donem_etiket: string;
  bildirim: { yukleme_id: string; surum: string; surum_etiket: string; zaman: string; dosya_adi: string | null; sha256?: string | null; surum_kaynagi?: string | null; dosya_surum?: string | null; surum_dogrulama?: SurumDogrulama } | null;
  satirlar: MutabakatSatir[];
  ozet: { bildirim_alacak_tl: number | null; bildirim_borc_tl: number | null; bildirim_kiyas_alacak_tl: number | null; bildirim_kiyas_borc_tl: number | null; bildirim_kiyas_net_tl: number | null;
    pvquant_alacak_tl: number | null; pvquant_borc_tl: number | null; pvquant_net_tl: number | null; fark_tl: number | null; uyumlu: number; farkli: number; senaryo: number; kiyaslanan: number; kapsam: string | null;
    dogrulama?: "tam" | "kismi" | "senaryo" | "yok" | null; kapsam_saat?: number; beklenen_saat?: number | null };
  uyum: { pct: number; tl: number; not: string }; guvenilirlik: MutabakatGuvenilirlik; eylem: string | null;
  pvquant: { saat: number; beklenen_saat?: number; son_saat?: string; hesaplanamayan_saat?: number; bildirilen_saat?: number; senaryo_saat?: number; senaryo_kapsam?: string; kural_surumu?: string; hata?: string;
    /** v2.541: KÜPST katsayılarının kaynağı (kural tablosu | santral ayarı (geçersiz kılma)) */ kupst_kaynak?: string | null; kupst_gecersiz_kilma?: boolean;
    /** v2.523 (P4a): dönemin sayaç kapsamı — hesaba girmez, yalnız bilgi */
    sayac?: { toplam_saat: number; yuklu: number; olculmus: number; tahmini: number; olc_fark_pct: number | null } | null; uretim_kaynak?: UretimKaynak };
  /** v2.527 (P2b-2): dönem için yüklü EPYS saatlik detayı varsa eş kapsamlı kıyas özeti */ saatlik_detay?: SaatlikOzet | null; not: string; program_notu: string | null;
  /** v2.538 (EK-3 DK-557/DK-395): dönemin itiraz süreleri ve geriye dönük 12 ay penceresi (DUY m.133; lisanssızda LÜY m.27) */ itiraz?: MutabakatItiraz }
export interface MutabakatItiraz { donem: string; on_bildirim_itiraz_son: string; fatura_itiraz_60_gun: string;
  geriye_donuk: { pencere_ay: number; son_basvuru: string; gecti: boolean; kalan_gun: number; sonuc_ay: number; kesinlik: "cikarim"; not: string };
  inceleme: { olcum_teias_dagitim_gun: number; olcum_epias_is_gunu: number; olcum_disi_is_gunu: number; dayanak: string };
  lisanssiz: { itiraz_is_gunu: number; inceleme_is_gunu: number; muhatap: string; dayanak: string; not: string } | null; dayanak: string }
export interface MutabakatOzet { bugun: string;
  donemler: { donem: string; surum: string; surum_etiket: string; yukleme_id: string; zaman: string; dosya_adi: string | null; sha256?: string | null; kalem_sayisi: number; surum_kaynagi?: string | null; dosya_surum?: string | null; gecerli: boolean; surum_dogrulama: SurumDogrulama }[];
  secili: Mutabakat; surumler: { kod: string; etiket: string }[]; kalemler: { kod: string; etiket: string; hesaplanir: boolean; epys: string }[]; guvenilirlik_etiketleri: Record<string, string>;
  uretim_ayari: "scada" | "sayac"; uretim_secenekleri: { kod: "scada" | "sayac"; etiket: string }[] }
/** v2.527 (P2b-2): EPYS saatlik detayı ↔ PVQuant dökümü eş kapsamlı kıyas */
export interface SaatlikKiyasToplam { edt_net_epias_tl: number | null; edt_net_pvquant_tl: number; edt_net_fark_tl: number | null; edt_poz_epias_tl: number | null; edt_neg_epias_tl: number | null;
  edt_poz_pvquant_tl: number; edt_neg_pvquant_tl: number; kupst_epias_tl: number | null; kupst_pvquant_tl: number; kupst_fark_tl: number | null; uevm_mwh: number | null; gerceklesen_pvquant_mwh: number; fark_isareti: string }
export interface SaatlikAyristirma { fiyat_farki_saat: number; uretim_farki_saat: number; program_farki_saat: number; pozisyon_farki_saat?: number; yuvarlama_saat?: number; kural_farki_saat: number; edt_farki_saat: number | null; uyumlu_saat: number | null;
  fiyat_karsilastirildi: boolean; uretim_karsilastirildi: boolean; program_karsilastirildi: boolean; pozisyon_karsilastirildi?: boolean; edt_karsilastirildi: boolean; not: string }
export interface SaatlikSatir { zaman: string; ptf_epias: number | null; ptf_pvquant: number | null; smf_epias: number | null; smf_pvquant: number | null; uevm_mwh: number | null; gerceklesen_pvquant_mwh: number | null;
  budup_mwh: number | null; program_pvquant_mwh: number | null; program_kaynak: string | null; edm_epias_mwh?: number | null; sapma_pvquant_mwh?: number | null; yon?: string | null; durum_pvquant?: string | null;
  edt_net_epias_tl: number | null; edt_net_pvquant_tl: number | null; edt_fark_tl: number | null;
  kupst_epias_tl: number | null; kupst_pvquant_tl: number | null; nedenler: string[] }
export interface SaatlikYukleme { donem: string; yukleme_id: string; kaynak_ekran: string; zaman: string; dosya_adi: string | null; sha256?: string | null; saat: number; bas: string; bit: string; versiyon?: string | null }
export interface SaatlikKiyas { donem: string; yuklu: boolean; yuklemeler: SaatlikYukleme[]; epias_saat: number; pv_saat?: number; ortak_saat: number; yalniz_epias_saat?: number; yalniz_pvquant_saat?: number;
  kolonlar: string[]; uretim?: string | null; toplam: SaatlikKiyasToplam | null; ayristirma: SaatlikAyristirma | null; en_buyuk: SaatlikSatir[]; satirlar: SaatlikSatir[]; not: string;
  tolerans: { fiyat_tl_mwh: number; mwh: number; tl: number }; neden_aciklama?: Record<string, string>; yuklemeler_tum?: SaatlikYukleme[] }
export interface SaatlikYuklemeYanit { yukleme_id: string; donem: string; saat: number; kolonlar: string[]; kolon_etiketleri: string[]; kaynak_ekran: string; bicim: string; sha256: string; uyarilar: string[]; dosya_adi: string }
export interface SaatlikOzet { yuklu: boolean; epias_saat: number; pv_saat?: number; ortak_saat: number; toplam?: SaatlikKiyasToplam | null; ayristirma?: SaatlikAyristirma | null; uretim?: string | null }
/** v2.528 (P10): uzlaştırma kuralı sürüm tablosu (ext/turkiye/kurallar.tablo) */
export interface KuralSatiri { gecerlilik_bas: string; gecerlilik_bitis: string | null; rejim: string; kural_surumu: string;
  /** sistem yönüne göre katsayılar: { acik, fazla, dengede } */ k: Record<string, number> | null; l: Record<string, number> | null; V: number | null; B: number | null; AFL: number | null;
  aylik_toplama: string | null; kupst: { m: number | null; n: number | null; n_ariza: number | null; ariza_esigi: number | null; taban: number | null; net_sapma: boolean | null; birim: string | null; dayanak: string | null };
  dsg_esik: number | null; dsg_dayanak: string | null; edt_dayanak: string | null; belirsiz_2027: boolean;
  /** v2.535: satırın kaynak durumu — dayanak metnindeki işaretlerden türetilir (kurallar.dogrulama_durumu) */
  dogrulama?: "dogrulandi" | "cikarim" | "dogrulama_gerekli" | "belirsiz"; dogrulama_notu?: string }
export interface KuralTablosu { segment: string; satirlar: KuralSatiri[] }
export interface MutabakatYukleme { yukleme_id: string; donem: string; surum: string; surum_kaynagi: string; kalem_sayisi: number; bicim: string; sha256: string; uyarilar: string[]; taninmayan: string[]; dosya_adi: string; surum_dogrulama: SurumDogrulama }
/** ekleme yanıtı: aynı saatlerde başka kayıt varsa uyarı (engel değil) */
export type OlayYanit = Olay & { uyari?: string; cakisan?: string[] };
export interface OlayGiris { tur: OlayTur; baslangic: string; bitis?: string | null; etkilenen_kw?: number | null; neden?: string | null; eak_gerekcesi?: string | null; kanit?: string | null;
  /** v2.541 */ bildirim_zamani?: string | null; talimat_mw?: number | null }

/** v2.542 (P8b-2; IH-083/099/104): ölçülen düzlem-içi ışınım ve hücre sıcaklığıyla beklenen üretim, EPI, üç referans, ışınım endeksi. */
export interface PerformansAy { ay: string; uretim_kwh: number; saat: number; poa_kapsam: number; kirpma_saat: number; kisinti_saat: number; isinim_kwh_m2: number | null;
  beklenen_kwh: number | null; epi: number | null; epi_temiz: number | null; durum: "ok" | "poa_yok"; tahmin_kwh?: number | null; p50_kwh?: number | null;
  isinim_p50_kwh_m2?: number | null; isinim_endeksi?: number | null; p50_hava_duzeltmeli_kwh?: number | null }
export interface IsinimKaynagi { duzlem: "poa" | "ghi" | null; etiket: string; sinif: string | null; kalibrasyon: string | null; tur: string | null; vade?: string | null }
export interface Performans { durum: "ok" | "poa_yok" | "veri_yok" | "referans_yok"; ay: number; bugun: string; not: string; sensor_sayisi: number; sensorler: IsinimKaynagi;
  referans?: { deger: number; kaynak: "tasarim" | "olcum"; etiket: string }; sicaklik?: { kaynak: string; etiket: string }; gamma?: number; ac_sinir_kw?: number | null; ac_sinir_kaynak?: string | null;
  aylar?: PerformansAy[]; toplam?: { ay_ok: number; ay: number; uretim_kwh: number; beklenen_kwh: number; epi: number | null; tahmin_kwh: number | null; p50_kwh: number | null };
  isinim?: { durum: "ok" | "poa_p50_yok" | "sensor_yok" | "iklim_yok" | "olcum_yok"; yil: number | null; not: string; duzlem: string | null };
  pr_olcum?: Record<string, number | string | null> }
/** v2.542 (P8b-2; IH-092): sensör envanteri — vade ve durum sunucuda türetilir. */
export interface Sensor { tur: string; olcum: string; marka_model?: string | null; seri_no?: string | null; sinif?: string | null; kalibrasyon_tarihi?: string | null;
  kalibrasyon_periyodu_ay?: number; not?: string | null; vade?: string | null; kalan_gun?: number | null; durum?: "gecti" | "yaklasiyor" | "uygun" | "tarih_yok" }
export interface Sensorler { sensorler: Sensor[]; isinim: IsinimKaynagi; turler: Record<string, string>; olcumler: Record<string, string>; siniflar: string[];
  varsayilan_periyot_ay: number; yaklasan_gun: number; not: string }

/** v2.543 (P9 hazırlık): depolama ünitesi beyanı, dengeleme birimi eşiği (DUY m.22, 30 MW), emre amadelik eşiği (DUY m.81/A %85/%80; ölçüm belirsiz). */
export interface Depolama { var: boolean; guc_mw: number | null; kapasite_mwh: number | null; konfigurasyon: string | null; konfigurasyon_etiketi: string | null;
  konfigurasyonlar: Record<string, string>; uevcb: string | null; uevcb_notu: string; kabul_tarihi: string | null; butunlesik: boolean | null;
  dengeleme_birimi: { yukumlu: boolean | null; esik_mw: number; kesinlik: string; dayanak: string; not: string };
  emre_amadelik: { oran: number | null; yil: number | null; gecis_tarihi: string | null; ilk_yil: number; oran_ilk: number; oran_sonra: number; esik_kesinlik: string; olcum_kesinlik: string; olcum_notu: string; dayanak: string; sonuc: string; not: string } | null;
  yekdem_notu: string; smf_cozunurluk: { deger: string; kesinlik: string; gecis_hukuki: string; etiket: string }; not: string; dayanaklar?: string[] }

/** v2.544 (dalga 3 kalanı; IH-090/092): açık-gök tabanlı kirlenme ve ölçüm tutarlılığı göstergesi — ön tanı, hesap değil. */
export interface Kirlenme { durum: "ok" | "egim_yok" | "poa_yok" | "acik_gun_yok"; pencere_gun: number; not: string; aciklama?: string; son_olcum?: string;
  sensor: IsinimKaynagi; tazelik?: { son_olcum: string; veri_yasi_gun: number; bayat: boolean; not: string | null }; pencere?: { bas: string; bit: string }; yontem?: string[];
  acik_gun?: number; acik_gun_30?: number; age_7g?: number; pr_acik_7g?: number | null; age_egim_pct_ay?: number | null; pr_egim_pct_ay?: number | null;
  yorum?: { kod: "sensor" | "modul" | "atmosfer" | "ikisi" | "toparlanma" | "kararli" | "yetersiz"; baslik: string; metin: string; tur: "olcum" | "uretim" | "bilgi"; uretim_kaybi: "yok" | "olasi" | "belirsiz" };
  son_yagis?: { tarih: string | null; mm: number | null; gun_once: number | null; referans?: string; kaynak?: string; not?: string };
  gunler?: { gun: string; acik_saat: number; age: number; pr_acik: number | null }[];
  /** v2.545 (IH-090): kirlenme kaybı tahmini — temiz referans PR kantili; yalnız «modül»/«ikisi» yorumunda anlamlı */
  kayip?: { durum: "ok" | "yetersiz" | "askida"; nitelik?: "tahmin" | "senaryo"; not: string; aciklama?: string; neden?: string; bitis?: string; referans_pr?: number; referans_kaynak?: string;
    son7_gunluk_kayip_pct?: number | null; son30_kayip_kwh?: number; son30_kayip_tl?: number | null; son30_gun?: number; pencere_kayip_kwh?: number;
    gecerlilik?: "anlamli" | "zayif" | "belirsiz" | "yanli"; gecerlilik_metin?: string;
    temizlik?: { maliyet_tl: number; son30_karsilar: boolean; geri_odeme_gun: number | null } | null; temizlik_neden?: string | null };
  /** v2.546: son modül temizliği (Santral ayarları); gün önce son ölçüm gününe göre */
  son_temizlik?: { tarih: string; gun_once: number; referans: string } | null;
  /** 08.11 inceleme II: sonuçların değerlendirildiği an (UTC ISO) */
  hesaplama_zamani?: string;
  esikler?: Record<string, number | number[]> }
/** v2.544 (P4b hazırlık; IH-023): veri kaynakları, bağlantı durumu ve hazırlık listesi. durum: mevcut (uygulamada var) | kurulmadi (bağlantı henüz yok). */
export interface VeriYolu { tur: string; etiket: string; kisa: string; durum: "mevcut" | "kurulmadi"; durum_etiketi: string; yon: string; tur_etiketi: string; gerekenler: string[]; not: string;
  /** 09.11 inceleme III: yolun gerçek yetenekleri — arayüz varsayım yapmaz */
  yetenekler?: { yapilandirma: string | null; sinama: "kimlik" | "okuma" | "ulasilabilirlik" | null; veri_okuma: boolean; duzenli_cekis: boolean; dogrulama: "canli" | "sahte" | "yok"; ozet: string; sinama_etiketi: string; dogrulama_etiketi: string } }
export interface VeriYoluEtkin { tur: string; etiket: string; tur_etiketi: string; tanimli: boolean; son: string | null; son_olcum?: string | null; ayrinti: string | null;
  tazelik: "guncel" | "gecikmis" | "yok" | "dosya" | "dosya_eski"; tazelik_etiketi: string; yas_saat: number | null;
  /** 08.11 inceleme: EPİAŞ çekiş durumu — hata ≠ yeni kayıt yok ≠ SCADA öncelikli */
  cekis?: { kod: string; etiket: string; zaman: string | null; ayrinti?: string | null } | null;
  /** 08.11 inceleme II: bağlantı sağlığı (veri tazeliğinden ayrı) ve veri cümlesi */
  baglanti?: { durum: "ok" | "hata" | "yok" | "bilinmiyor"; etiket: string; zaman: string | null } | null; veri_etiketi?: string; veri_kodu?: string;
  /** 10.11 inceleme II (yalnız bulut satırı): birim doğrulanmadıysa «veri» rozeti olumlu renge boyanmaz */
  saglayici?: string; birim_dogrulandi?: boolean; son_cekis_ok?: boolean }
/** 08.11 inceleme (faz 3): hedef bağlantının aşamaları; hiçbiri diğerini ima etmez */
export interface VeriYoluAsama { kod: "secildi" | "ayar" | "sinama" | "nokta" | "kimlik" | "cekis" | "akis" | "birim"; etiket: string; tamam: boolean; zaman: string | null; durum?: string }
export interface VeriYoluOzet { etkin: VeriYoluEtkin[];
  beyan: { tur: string; saglayici: string | null; periyot_dk: number | null; salt_okuma_onayi: boolean; not: string | null; beyan_zamani: string; baglanti?: { host: string; port: number; birim: number; zaman_asimi_sn?: number | null; profil?: string | null; cihazlar?: { birim: number; ad?: string; profil?: string }[] } | null;
    son_sinama?: { zaman: string; durum: VeriYoluSinama["durum"]; ozet?: VeriYoluSinama["ozet"] | Record<string, unknown> | null; aciklama?: string | null; saglayici?: string } | null;
    /** v2.546: sahibin «düzenli veri çekişini başlat» kararı */
    ornekleme_acik?: boolean;
    /** v2.548 (Aşama 0, H2): IEC 104 STARTDT yalnız sahibin «ayrı istemci yuvası tanımlandı» onayıyla */
    startdt_onayi?: boolean;
    /** v2.554 (S4): IEC 104 ayarları ve nokta tablosu */
    iec104?: { ca: number; sinir: string; parametreler: Record<string, number> } | null; nokta_tablosu?: { ioa: number; alan: string; carpan: number; ad: string | null }[] | null } | null;
  hedef: VeriYolu | null; asamalar?: VeriYoluAsama[]; yollar: VeriYolu[]; taze_saat: number; dosya_eski_gun?: number; dosya_yukleme_sikligi_gun?: number | null; not: string;
  /** v2.547: bulut sağlayıcıları (bağlayıcısı olanlar) ve henüz olmayanlar */
  bulut?: { saglayicilar: { kod: string; ad: string; kimlik_alanlari: string[]; kimlik_etiketleri?: Record<string, string>; gizli_alanlar?: string[]; bolge: boolean; bolgeler?: string[]; varsayilan_bolge?: string | null; not: string; durum?: string; durum_etiketi?: string; oauth?: boolean; elle_giris?: boolean }[]; bolgeler: string[]; henuz_yok: string[]; henuz_yok_etiketi?: string; hesap_durumu?: { saglayici: string | null; birim_dogrulandi: boolean; etiket: string } | null; diger_etiketi?: string; not: string; kasa?: { var: boolean; id: string | null; eski: string[]; hata?: string } };   // v2.556: şifreli saklama açık mı
  /** 09.11 inceleme III: hedef bağlantının tek durum kodu */
  baglanti_durumu?: { kod: string; etiket: string };
  /** v2.552 (S2): Modbus kayıt haritaları (SunSpec + üretici profilleri) */
  profiller?: { kod: string; ad: string; aciklama: string; uretici: string | null; fonksiyon: number; sinir: string; belge: string | null; birim_varsayilan: number; dogrulama: string }[] }
/** v2.545 (P4b): Modbus TCP / SunSpec bağlantı sınaması sonucu (yalnız okuma; veri akışı başlatmaz). */
export interface VeriYoluSinama { durum: "ok" | "kismi" | "veri_modeli_yok" | "protokol_yaniti_yok" | "kimlik_hatasi" | "saglayici_desteklenmiyor" | "saglayici_kapandi" | "onay_yok" | "adres_reddedildi" | "ayar_hatasi" | "baglanti_hatasi"; zaman: string; aciklama?: string;
  /** v2.547: bulut sınaması özeti */
  saglayici?: string; bulut_ozet?: { santral_sayisi: number; ilk_santral: string | null; ilk_kapasite_kwp: number | null; saat_dilimi: string | null };
  hedef?: { host: string; port: number; birim: number; ip?: string; ag?: string };
  ozet?: { uretici?: string | null; model?: string | null; seri_no?: string | null; guc_kw?: number | null; enerji_mwh?: number | null; durum?: string | null; olaylar?: string[]; model_sayisi?: number;
    /** v2.547: bulut (santral listesi) ve IEC 104 özetleri aynı alanda; v2.548: IEC 104 yöntemi tcp (STARTDT yok) | startdt */
    santral_sayisi?: number; ilk_santral?: string | null; ilk_kapasite_kwp?: number | null; saat_dilimi?: string | null; uc?: string | null; tcp?: boolean; startdt_con?: boolean | null; yontem?: "tcp" | "startdt" | "gi";
    /** v2.551/v2.552: profil (1xx | 7xx | üretici haritası), enerji kaynağı, ölçüm sınırı */
    profil?: string | null; enerji_yolu?: string | null; sinir?: string | null; uretici_durum?: string | null; uygulanmayan?: string[];
    /** v2.554 (S4): IEC 104 genel sorgulama (yontem "gi") */
    nokta_sayisi?: number; tablo_sayisi?: number; eslesen?: number; ikame?: number; gelmeyen_ioa?: number[]; gonderilen_tipler?: number[] };
  not?: string }

/** v2.550 (D5): gölge saatlik görünüm — kaynak seçimi ile üretim serisi yan yana (tahmin bu görünümü kullanmaz) */
export interface GolgeSaat { ts_utc: string; secilen: { kaynak: string; cihaz_id: string | null; power_kw: number | null; energy_kwh: number | null; tamlik: string; tamlik_etiketi: string | null; yontem: string | null; revizyon: number | null; kapsama_dk: number | null } | null;
  neden: string | null; alternatif_sayisi: number; mevcut: { power_kw: number | null; energy_kwh: number | null; flag: string | null; kaynak: string | null } | null; fark_kwh: number | null }
export interface GolgeGorunum { bas: string; bit: string; saatler: GolgeSaat[]; ozet: { n_saat: number; n_tam: number; n_kismi: number; n_mevcut: number; n_fark_05kwh: number }; sinir: string; sinir_etiketi: string; oncelik: Record<string, number>; not: string; uyari?: string }
/** v2.555 (V2): cihaz durumundan olay adayları (otomatik kayıt yok) */
export interface OlayAday { tur: "ariza" | "iletisim_kopuklugu" | "kisit"; kisma_yuzde_ort?: number; kisma_yuzde_maks?: number; tur_etiketi: string; cihaz_id: string; bas: string; bit: string | null; sure_dk: number; ornek_sayisi: number; kodlar: string[]; durum: "bitti" | "suruyor"; kayitli: boolean; not: string }
export interface OlayAdaylari { adaylar: OlayAday[]; pencere_saat: number; n_ornek: number; periyot_dk?: number; not: string }

/** v2.556/v2.557 (Aşama 3, K1/K2): şifreli bulut kimliği durumu — gizli alan yok, etiket maskeli */
export interface BulutKimlikKayit { saglayici: string; saglayici_adi: string; bolge: string | null; dis_kimlik: string | null; kek_id: string; surum: number; etiket: string | null;
  onay_json: { metinler: Record<string, string>; zaman: string; aktor_id: string | null }; cekis_acik: boolean; birim_dogrulandi: boolean; kota_gun: string | null; kota_sayac: number;
  son_cekis: string | null; son_durum: string | null; son_durum_etiketi: string | null; son_hata: string | null; olusturma: string; guncelleme: string;
  /** v2.565: portal dışa aktarımıyla birim kıyası özeti; «birim doğrulandı» yalnız belge_uyumlu iken işaretlenebilir */
  birim_kanit?: BulutBirimKiyas | null }
export interface BulutBirimKiyas { sonuc: string; metin: string; belge_uyumlu: boolean; n_referans: number; n_ortak: number; n_uretimli?: number; isaret_kaldirildi?: boolean; zaman?: string; dosya?: string | null; uyari?: string | null; kaydedildi?: boolean;
  alanlar: { alan: string; etiket?: string | null; hipotez: string; hipotez_etiketi: string; n_ortak: number; n_uretimli?: number; n_tolerans_ici?: number; oran: number | null; mape_pct: number | null; toplam_fark_pct: number | null; sonuc: string }[];
  tolerans: { pct: number; kwh: number; min_ortak_saat: number; min_uretimli_saat?: number }; not: string }
export interface BulutKimlikDurum { kasa: { var: boolean; id: string | null; eski: string[]; hata?: string }; kayitlar: BulutKimlikKayit[]; onay_metinleri: Record<string, string>; not: string;
  ham_son: { saglayici: string; ts_utc: string; dis_kimlik: string | null; alanlar: Record<string, number | string | null>; alinma: string }[];
  alanlar: Record<string, { birim: string; etiket: string; hedef?: string }>; birim_notu: string; gunluk_tavan: number;
  saglayici_alanlari?: Record<string, { alanlar: Record<string, { birim: string; etiket: string }>; birim_notu: string; gunluk_tavan: number; toplu: boolean }>;
  /** v2.564: sahip onayı (OAuth) — platform uygulaması yapılandırıldı mı (eksik ortam değişkeni ADLARI), son girişim (durum kodu, santral listesi) */
  oauth?: { uygulamalar: Record<string, { yapilandirildi: boolean; eksik: string[]; geri_donus: string; kayit: string | null }>;
    son: { saglayici: string; bolge: string | null; baslatma: string; bitis: string; kullanildi: boolean; durum: string; etiket: string; aciklama?: string | null; santraller: { kimlik: string; ad: string | null; kapasite_kwp: number | null }[]; zaman?: string | null } | null } }
export interface BulutKimlikSonuc { durum: string; kaydedildi: boolean; aciklama?: string; zaman?: string; saglayici?: string; dis_kimlik?: string; dis_ad?: string | null; etiket?: string | null; kek_id?: string;
  santraller?: { kimlik: string; ad: string | null; kapasite_kwp: number | null }[]; not?: string }
/** v2.564: sahip onayı başlatma yanıtı — yetki_url sağlayıcının onay sayfası (tek kullanımlık, 15 dk) */
export interface BulutOAuthBaslat { durum: string; aciklama?: string; yetki_url?: string; bitis?: string; geri_donus?: string; saglayici?: string; bolge?: string | null; eksik?: string[]; not?: string }

/** v2.560 (Aşama 4): pilot kapıları ve referans kıyası */
export interface PilotKapi { kod: string; ad: string; kaynak: "saha" | "kod"; p0: boolean; aciklama: string; tamam: boolean; not: string | null; zaman: string | null; aktor_id: string | null; durum_etiketi: string }
export interface ReferansKiyasOzet { sonuc: "uyumlu" | "uyumsuz" | "yetersiz"; metin: string; n_referans: number; n_ortak: number; n_tolerans_ici: number; tolerans_orani: number | null; n_golge_yok: number; n_golge_kismi_disi: number; mape_pct: number | null; maks_mutlak_fark_kwh: number; toplam_fark_pct: number | null; sinir?: string; bas?: string; bit?: string; dosya?: string | null; zaman?: string; uyarilar?: string[]; tolerans_disi_saatler?: { ts_utc: string; referans_kwh: number; golge_kwh: number; fark_kwh: number; kaynak: string | null }[] }
export interface PilotDurum { kapilar: PilotKapi[]; p0_acik: string[]; sahaya_hazir: boolean; referans_sonuc: ReferansKiyasOzet | null; not: string }
/** v2.561 (Aşama 6): saha toplayıcısı kimlikleri (anahtar yalnız üretim yanıtında) */
export interface EdgeToplayici { id: string; ad: string; prefix: string; durum: "etkin" | "iptal"; olusturma: string; son_gorulme: string | null; son_sira: number | null; iptal_zamani: string | null }
export interface EdgeToplayiciYeni { id: string; ad: string; prefix: string; anahtar: string; olusturma: string; not: string }
