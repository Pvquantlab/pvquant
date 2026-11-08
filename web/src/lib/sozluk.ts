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
  sorun: { scada_yok: "veri yok", scada_bayat: "veri eski", kosu_yok: "tahmin yok", kosu_bayat: "tahmin eski", kiraci_askida: "müşteri askıda",
           segment_yok: "segment seçilmedi" } as Record<string, string>,   // v2.515: segment yoksa KÜPST/DSG hesaplanamaz
  /** v2.515: platform tablolarında kısa segment adı (müşteri paneli SEGMENTLER'in uzun etiketini kullanır) */
  segmentKisa: { lisansli_serbest: "Lisanslı serbest", lisansli_yekdem: "Lisanslı YEKDEM", yeka: "YEKA", lisanssiz_iletim: "Lisanssız iletim",
                 lisanssiz_dagitim: "Lisanssız dağıtım", oz_tuketim_saatlik: "Öz tüketim" } as Record<string, string>,
  /** hesap ve kullanıcı durumları */
  hesapDurumu: { active: "etkin", suspended: "askıda" } as Record<string, string>,
  kullaniciDurumu: { aktif: "etkin", pasif: "pasif" },
  /** 27.10 — denetim izi eylem kodları (denetim_izi.eylem; kaynak denetim_service.EYLEMLER_* + kaydet çağrıları + sunucu CLI betikleri).
   *  Kod API/DB sözleşmesidir, değişmez; burada yalnız görünen Türkçe karşılığı. Sözlükte olmayan kod olduğu gibi gösterilir. */
  eylem: {
    // platform (PVQuant personeli)
    giris: "Giriş", giris_basarisiz: "Başarısız giriş",
    kiraci_olustur: "Müşteri hesabı açıldı", kiraci_guncelle: "Müşteri güncellendi", kiraci_goruntule: "Müşteri görüntülendi",
    kiraci_temsil: "Müşteri gözüyle görüntüleme", kullanici_guncelle: "Kullanıcı güncellendi",
    parola_sifirlama_gonder: "Parola bağlantısı gönderildi", parola_sifirla_cli: "Parola sıfırlandı (sunucu)", eposta_degistir_cli: "E-posta değiştirildi (sunucu)",
    iki_adim_ac: "İki adımlı doğrulama açıldı", iki_adim_sifirla: "İki adımlı doğrulama sıfırlandı",
    basvuru_okundu: "Başvuru okundu", operator_ekle: "Operatör eklendi", operator_guncelle: "Operatör güncellendi", plan_guncelle: "Plan güncellendi",
    yekdem_fiyat: "YEKDEM aylık fiyatı girildi", kur_doldur: "Döviz kuru arşivi dolduruldu",
    // müşteri (kuruluş ekibi)
    takim_ekle: "Ekip üyesi eklendi", takim_guncelle: "Ekip üyesi güncellendi", takim_iki_adim_sifirla: "Ekip üyesi 2FA sıfırlandı",
    anahtar_uret: "API anahtarı üretildi", anahtar_iptal: "API anahtarı iptal edildi", webhook_ekle: "Webhook eklendi", webhook_sil: "Webhook silindi",
    santral_arsivle: "Santral arşivlendi", santral_geri_al: "Santral arşivden alındı", scada_sil: "SCADA verisi silindi",
    parola_degistir: "Parola değiştirildi", kurulus_ayar: "Kuruluş ayarı değiştirildi",
    // v2.516 (#7) — uzlaştırma katmanı
    kgup_indir: "KGÜP dosyası indirildi", eak_indir: "EAK dosyası indirildi", kgup_bildirilen_yukle: "Bildirilen KGÜP yüklendi",
    kgup_sablon_ogren: "KGÜP şablonu öğrenildi", kgup_sablon_sifirla: "KGÜP şablonu sıfırlandı",
    santral_segment: "Segment / UEVÇB ayarlandı", eak_ayar: "EAK ayarı değiştirildi", sensor_ayar: "Sensör envanteri değiştirildi", veri_yolu_ayar: "Veri kaynağı beyanı değiştirildi", veri_yolu_sinama: "Veri kaynağı bağlantısı sınandı",
    santral_tarihler: "Santral tarihleri ayarlandı",   // v2.518 (P3a)
    olay_ekle: "Olay kaydı açıldı", olay_guncelle: "Olay kaydı güncellendi",   // v2.521 (P1a)
    mutabakat_yukle: "Uzlaştırma bildirimi yüklendi", dsg_belge_indir: "DSG üye dağılımı belgesi indirildi",   // v2.522 (P2b)
    sayac_yukle: "Sayaç dosyası yüklendi", sayac_ayar: "Sayaç ve SCADA ayarı değişti",   // v2.523 (P4a)
    mutabakat_saatlik_yukle: "EPYS saatlik detayı yüklendi", mutabakat_saatlik_indir: "Saatlik kıyas indirildi",   // v2.527 (P2b-2)
    rapor_donem_indir: "Dönem raporu indirildi", rapor_gonderim_ayar: "Rapor gönderim ayarı değişti", rapor_gonderim: "Dönem raporu e-postayla gönderildi",   // v2.525
  } as Record<string, string>,
} as const;

export const isDurumu = (tamam: boolean) => (tamam ? SOZLUK.isDurumu.tamam : SOZLUK.isDurumu.basarisiz);
export const tazelik = (bayat: boolean) => (bayat ? SOZLUK.tazelik.eski : SOZLUK.tazelik.guncel);
export const sorunAdi = (kod: string) => SOZLUK.sorun[kod] ?? kod;
export const segmentKisa = (kod: string) => SOZLUK.segmentKisa[kod] ?? kod;
export const hesapDurumu = (durum: string) => SOZLUK.hesapDurumu[durum] ?? durum;
export const eylemAdi = (kod: string) => SOZLUK.eylem[kod] ?? kod;
