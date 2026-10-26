/** 26.10 — ORTAK SÖZLÜK: platform (/yonetim) ve müşteri paneli aynı teknik kavramı aynı sözcükle söyler.
 *  Kaynak dil müşteri panelinin «piyasa dili» (v2.462); platform paneli buna uyar. API alan adları (bayat, taze, tamam, kosu…)
 *  SÖZLEŞMEDİR, değişmez — burada yalnız kullanıcıya görünen karşılıkları durur. İş adlarının tek kaynağı sunucudaki
 *  isler_service.ISIM_TR'dir (iki panel de API'den «ad» alır); burada tekrar edilmez. */
export const SOZLUK = {
  /** jobs_log.status == 'ok' → tamam; aksi → başarısız (iki panelde de «düştü» yok) */
  isDurumu: { tamam: "tamam", basarisiz: "başarısız" },
  /** veri/iş tazeliği: uçtan gelen bayat/taze hükmünün sözcüğü (hesap arayüzde yapılmaz) */
  tazelik: { guncel: "güncel", eski: "eski" },
  /** son ölçüm (scada_hourly max ts) ve son tahmin koşusu (forecast_runs max run_at) — iki panelde aynı etiket */
  sonVeri: "son veri", sonTahmin: "son tahmin", sonKontrol: "son kontrol",
  /** veri kaynakları ve sistem bileşenleri */
  kaynak: { hava: "Hava verisi", piyasa: "Piyasa fiyatları (PTF/SMF)", piyasaKisa: "Piyasa fiyatları", yedek: "Yedek",
            zamanlayici: "Zamanlayıcı", geceIsleri: "Gece işlemleri", isKayitlari: "İş kayıtları" },
  /** santral envanteri sorun kodları (sistem_service.santraller) */
  sorun: { scada_yok: "veri yok", scada_bayat: "veri eski", kosu_yok: "tahmin yok", kosu_bayat: "tahmin eski", kiraci_askida: "müşteri askıda" } as Record<string, string>,
  /** hesap ve kullanıcı durumları */
  hesapDurumu: { active: "etkin", suspended: "askıda" } as Record<string, string>,
  kullaniciDurumu: { aktif: "etkin", pasif: "pasif" },
} as const;

export const isDurumu = (tamam: boolean) => (tamam ? SOZLUK.isDurumu.tamam : SOZLUK.isDurumu.basarisiz);
export const tazelik = (bayat: boolean) => (bayat ? SOZLUK.tazelik.eski : SOZLUK.tazelik.guncel);
export const sorunAdi = (kod: string) => SOZLUK.sorun[kod] ?? kod;
export const hesapDurumu = (durum: string) => SOZLUK.hesapDurumu[durum] ?? durum;
