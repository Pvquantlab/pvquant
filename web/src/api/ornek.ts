/** Ornek veri — Konya GES'in 30 Tem 2026 kosusundan. API baglanana kadar. */
import type { SantralOzeti, TahminSerisi, Karne } from "./types";

const PROFIL = [0, 0, 0, 0, 0, 40, 300, 900, 1500, 1620, 2600, 3300,
                3560, 3560, 3560, 3400, 2900, 2100, 1300, 500, 60, 0, 0, 0];

export const ornekOzet: SantralOzeti = {
  ad: "Konya GES", kapasite_kwp: 4514, ac_tavani_kw: 3560,
  lat: 37.87, lon: 32.49, tz: "Europe/Istanbul",
  egim_azimut: "20° / 180° (varsayılan)",
  mod: "C", model_adi: "Hibrit", sapma_pct: 1.65, son_kalibrasyon: "29 Tem 2026",
  saatlik_mape: 60.6, son_kosu: "30.07 12:58",
  bugun_kwh: 30356, yarin_kwh: 30626, hafta_mwh: 212.9,
  anlati: "Yarın beklenen üretim bugünle aynı seviyede.",
  hava: [
    { etiket: "Bugün", sicaklik: 25.6, isinim: 7.7 },
    { etiket: "Yarın", sicaklik: 25.5, isinim: 7.7 },
    { etiket: "Cmt", sicaklik: 28.3, isinim: 8.0 },
  ],
  gunler: [
    { etiket: "Bugün", mwh: 30.4 }, { etiket: "Yarın", mwh: 30.6 },
    { etiket: "Cmt", mwh: 31.6 }, { etiket: "Paz", mwh: 31.5 },
    { etiket: "Pzt", mwh: 29.8 }, { etiket: "Sal", mwh: 29.3 },
    { etiket: "Çar", mwh: 29.8 },
  ],
  aylik: [
    { ay: "May 25", mwh: 722.5, saglam_saat: 402, kapsam_pct: 54.0, beklenti_mwh: null },
    { ay: "Haz 25", mwh: 866.1, saglam_saat: 431, kapsam_pct: 59.9, beklenti_mwh: null },
    { ay: "Tem 25", mwh: 892.4, saglam_saat: 446, kapsam_pct: 60.0, beklenti_mwh: null },
    { ay: "Ağu 25", mwh: 865.4, saglam_saat: 438, kapsam_pct: 58.9, beklenti_mwh: null },
    { ay: "Eyl 25", mwh: 767.4, saglam_saat: 421, kapsam_pct: 58.5, beklenti_mwh: null },
    { ay: "Eki 25", mwh: 606.3, saglam_saat: 442, kapsam_pct: 59.4, beklenti_mwh: null },
    { ay: "Kas 25", mwh: 494.0, saglam_saat: 376, kapsam_pct: 52.2, beklenti_mwh: null },
    { ay: "Ara 25", mwh: 449.2, saglam_saat: 401, kapsam_pct: 53.9, beklenti_mwh: null },
    { ay: "Oca 26", mwh: 380.6, saglam_saat: 402, kapsam_pct: 54.0, beklenti_mwh: null },
    { ay: "Şub 26", mwh: 406.8, saglam_saat: 387, kapsam_pct: 57.6, beklenti_mwh: null },
    { ay: "Mar 26", mwh: 641.8, saglam_saat: 449, kapsam_pct: 60.3, beklenti_mwh: null },
    { ay: "Nis 26", mwh: 630.2, saglam_saat: 484, kapsam_pct: 67.2, beklenti_mwh: null },
  ],
  saglik: { son_scada: "30 Nis 2026", kesinti_gun: 91, islenen_saat: 5781, anomali: 11737 },
};

export function ornekTahmin(ufuk: "24h" | "72h" | "7d" | "16d"): TahminSerisi {
  const saat = { "24h": 24, "72h": 72, "7d": 168, "16d": 384 }[ufuk];
  const bas = new Date("2026-07-30T00:00:00+03:00").getTime();
  const saatlik = Array.from({ length: saat }, (_, i) => {
    const p50 = PROFIL[i % 24];
    return { ts: new Date(bas + i * 3600_000).toISOString(), p50_kw: p50,
             p10_kw: Math.round(p50 * 0.958), p90_kw: Math.round(p50 * 1.096),
             // v2.204: ornek kipte ic bant da temsili — ayni sabit profil ailesi
             p25_kw: Math.round(p50 * 0.978), p75_kw: Math.round(p50 * 1.049),
             gercek_kw: null };
  });
  const gunluk = Array.from({ length: Math.ceil(saat / 24) }, (_, g) => {
    const d = saatlik.slice(g * 24, g * 24 + 24);
    const t = (k: "p50_kw" | "p10_kw" | "p90_kw") =>
      Math.round(d.reduce((a, s) => a + (s[k] ?? 0), 0));
    return { tarih: new Date(bas + g * 86_400_000).toISOString().slice(0, 10),
             p50_kwh: t("p50_kw"), p10_kwh: t("p10_kw"), p90_kwh: t("p90_kw") };
  });
  return { mod: "C", model: "hybrid_residual", kosu_zamani: "2026-07-30T12:58:48Z",
           ufuk_saat: saat, ac_tavani_kw: 3560,
           simdi_idx: ufuk === "24h" ? 18 : null,
           gunes: [],  // v2.203: ornek kip astronomi uydurmaz
           saatlik, gunluk };
}

export const ornekKarne: Karne = {
  kova: "0-24", gun_sayisi: 2, wmape_ort: 60.6, naife_ustunluk_pct: 16,
  ilk_tarih: "2026-04-15", son_tarih: "2026-04-18",
  gunluk: [
    { tarih: "15 Nis", kova: "0-24", wmape: 83, naif_wmape: 99 },
    { tarih: "16 Nis", kova: "0-24", wmape: 39, naif_wmape: 46 },
    { tarih: "17 Nis", kova: "24-72", wmape: 47, naif_wmape: 56 },
    { tarih: "18 Nis", kova: "24-72", wmape: 53, naif_wmape: 63 },
  ],
};

export const ornekAylik = {
  plant_id: "ornek",
  hesap_zamani: new Date().toISOString(),
  donem: "2006\u20132025", yil_sayisi: 20,
  beklenti: Array.from({ length: 12 }, (_, i) => ({
    ay: i + 1, p10: 60 + i * 14, p50: 75 + i * 15, p90: 90 + i * 16,
    yil_sayisi: 20 })),
  yillik: Array.from({ length: 60 }, (_, i) => ({
    yil: 2005 + (i % 5), ay: (i % 12) + 1,
    ghi_kwh_m2: 70 + ((i * 37) % 180) })),
};

/** v2.575 (Faz 1 F1-D): örnek kip — bağımsız doğrulama (temsili; sayılar canlı hesap değildir). */
export const ornekBagimsiz = {
  kayitli: false, gun: 30, kaynak: "scada",
  metrik: { n_saat: 318, n_gun: 29, wmape: 11.4, wmape_gunluk_ort: 12.1, mae_kw: 186.2, rmse_kw: 262.9, nmae: 4.1, nrmse: 5.8, mbe_kw: 41.0, nmbe: 0.9, enerji_sapma_kwh_gun: 450.3,
            picp80: 78.6, p10_alti: 12.3, p90_ustu: 9.1, bant_genisligi_oran: 19.4, winkler_kw: 1210.5, bant_n: 318 },
  kesit: { gun: [], en_zayif_gunler: [{ kesit: "2026-04-11", n_saat: 11, wmape: 27.9, mae_kw: 410.2, nmbe: -6.1, enerji_sapma_kwh_gun: -2940.0 }, { kesit: "2026-04-03", n_saat: 12, wmape: 22.4, mae_kw: 355.0, nmbe: 4.4, enerji_sapma_kwh_gun: 2110.0 }],
           ufuk: [{ kesit: "24-48", n_saat: 318, wmape: 11.4 }] },
  referans: { fizik: { n_saat: 318, wmape: 14.9, model_wmape_ayni_saatler: 11.4, beceri_pct: 23.5, sonuc: "model daha iyi", tanim: "aynı tahminin saf fizik modeli" },
              persistans: { n_saat: 301, wmape: 24.6, model_wmape_ayni_saatler: 11.5, beceri_pct: 53.3, sonuc: "model daha iyi" },
              cliper: { n_saat: 0, wmape: null, beceri_pct: null, sonuc: null, tanim: "hesaplanamadı: dönem öncesi yeterli ölçüm yok" } },
  butunluk: { olcum: { beklenen_saat: 720, olculdu_saat: 684, kapsama_pct: 95.0, dislanan: { eksik: 24, "bayrak:frozen_value": 8, "olay:ariza": 4 }, kirpma_saat: 31, kapsama_bilinmeyen_saat: 684, kaynak: "scada", sinir: "plant_gross_ac", sinir_etiketi: "tesis brüt AC (SCADA)" },
              gunduz_saat: 348, degerlendirilen_saat: 318, degerlendirilen_pct: 91.4, gunduz_dislanan: { eksik: 18, "bayrak:frozen_value": 8, "olay:ariza": 4 }, kirpma_saat_degerlendirilen: 31,
              gece: { n_saat: 372, tahmin_pozitif_saat: 12, tahmin_kwh: 9.6, gercek_pozitif_saat: 0 } },
  meta: { sozluk_surumu: "2026-11-10", kural: "program", kaynak: "scada", kapasite_kwp: 4514, gunduz_orani: 0.02, donem: { bas: "2026-03-19", bit: "2026-04-18", tz: "Europe/Istanbul" },
          kosu_sayisi: 29, kosu_kumesi_sha: "3b8f6bc9000ebbd5", saat_kumesi_sha: "24cf6d3a7a88664d", hesap_zamani: "2026-04-18T03:50:00+00:00", yazilim_surumu: null,
          kosu_kunyesi: { mode: ["C"], model: ["hybrid_residual"], meteo_source: ["acik-nwp"], kalibrasyon_id: [], yazilim_surumu: [], nwp_yasi_saat_ort: 4.2, ilk_run_at: "2026-03-18", son_run_at: "2026-04-17" } },
};

/** v2.584 (Faz 2 F2-F): Finansal etki — örnek kipte TEMSİLİ veri (API yok); yapı finansal_etki_service.ozet ile aynı. Sonuç değildir. */
const _fb = (kod: string, ad: string, tutar: number | null, nitelik: string, kaynak: string, toplanir = true, kapsam: number | null = 720, beklenen: number | null = 744, notlar: string[] = []) => ({
  kod, ad, tutar_tl: tutar, alacak_tl: tutar == null ? null : Math.max(tutar, 0), borc_tl: tutar == null ? null : Math.max(-tutar, 0), nitelik, nitelik_ad: ({ resmi: "resmî", hesaplanan: "hesaplanan", sozlesme_tahmini: "sözleşme tahmini", senaryo: "senaryo", eksik: "eksik" } as Record<string, string>)[nitelik],
  kaynak, kapsam_saat: kapsam, beklenen_saat: beklenen, kapsam_orani: kapsam == null || !beklenen ? null : +(kapsam / beklenen).toFixed(4), kural_surumu: kod === "dengesizlik" || kod === "kupst" ? "edt-2026-V100-edta_ayrik" : null, dayanak: null, toplanir, notlar });
export const ornekFinansalEtki = (kod = "2026-10") => {
  const b = [
    _fb("satis_geliri", "Enerji satışı", 2396400, "sozlesme_tahmini", "gerçekleşen üretim × tarife (sabit fiyat)", true, 720, 744, ["Satış geliri santral ayarlarındaki tarifeyle gerçekleşen üretimin çarpımıdır; fatura ya da EPİAŞ uzlaştırma sonucu değildir."]),
    _fb("dengesizlik", "Enerji dengesizlik tutarı", -61300, "hesaplanan", "PVQuant yeniden hesabı (Doğruluk ve Mutabakat ile aynı saatlik hesap)", true, 712, 744, ["32 saat hesaba girmedi (ölçüm, program ya da fiyat yok)."]),
    _fb("kupst", "KGÜP sapma tutarı (KÜPST)", -8900, "hesaplanan", "kural tablosu", true, 712, 744),
    _fb("teminat", "Dengesizlik teminatı (gösterge)", null, "eksik", "EPİAŞ teminat tanımı", false, null, null, ["Risk katsayısı girilmedi ya da yeterli ay yok; tutar verilmez."]),
    _fb("uretim_dusuklugu", "Üretim düşüklüğü (gelir kaybı tahmini)", -74200, "sozlesme_tahmini", "kayıp ayrışımı × sabit tarife", false, 701, 744, ["Nedeni bilinen kayıp 37.100 kWh; EPI 0,94."]),
    _fb("sozlesme_acigi", "Kullanılabilirlik sözleşme açığı (kıyas tabanı)", null, "eksik", "santral ayarı", false, null, null, ["Sözleşme eşiği girilmedi ya da kullanılabilirlik hesaplanamadı."]),
    _fb("ileri_maruziyet", "İleriye dönük maruziyet (senaryo)", -14000, "senaryo", "gelecek 168 saat programı × son 30 günün planlanan MWh başına net uzlaştırma oranı", false, 168, 168, ["Aralık (çeyrekler): -21.000 … -6.000 TL."]),
  ];
  const dengesizlik = { ...b[1], alacak_tl: 12400, borc_tl: 73700 };
  b[1] = dengesizlik;
  const toplam = { tutar_tl: 2326200, alacak_tl: 2326200, borc_tl: 0, nitelik: "sozlesme_tahmini", nitelik_ad: "sözleşme tahmini", giren: ["satis_geliri", "dengesizlik", "kupst"], eksik: [], isaret: "artı = santral lehine (alacak), eksi = santral aleyhine (borç)" };
  return {
    donem: { tur: "ay", kod, bas: "2026-10-01", bit: "2026-11-01", etiket: "Ekim 2026", kirpildi: false, gun: 31, saat: 744, tz: "Europe/Istanbul" }, kayitli: true, hesap_zamani: "2026-11-01T00:55:00+00:00",
    uretim: { planlanan: { mwh: 1240.5, saat: 744, kaynak: "karisik", kaynak_etiket: "bildirilen KGÜP ve PVQuant önerisi", bildirilen_saat: 600, oneri_saat: 144, yok_saat: 0, tamamlanan_saat: 24 },
      gerceklesen: { mwh: 1198.2, saat: 720, beklenen_saat: 744, secim: "scada", secim_etiket: "SCADA ölçümü", sinir: "plant_gross_ac", sinir_etiket: "tesis brüt AC (SCADA)", kaynak_saat: { scada: 720 }, kapsama: { beklenen_saat: 744, olculdu_saat: 720, kapsama_pct: 96.8, dislanan: { eksik: 19, "bayrak:frozen_value": 5 } } },
      tahmin: { mwh: 1251.0, saat: 744, etiket: "gün öncesi tahmin (P50)" }, sapma: { mwh: -42.3, pct: -3.41, yon: "eksik", ortak_saat: 720, etiket: "gerçekleşen − program (artı = fazla üretim)", tahmine_gore_mwh: -52.8, tahmin_ortak_saat: 720 },
      notlar: ["24 saatte ölçüm yok; bu saatler 0 sayılmadı, toplamlara girmedi.", "Program 600 saatte bildirilen KGÜP, 144 saatte PVQuant önerisinden kuruldu."] },
    gelir: { bilesenler: [b[0]], toplam: { ...toplam, tutar_tl: 2396400, alacak_tl: 2396400, giren: ["satis_geliri"] }, tarife: { tip: "sabit", etiket: "sabit fiyat", ortalama_fiyat_tl_mwh: 2000 }, uretim_mwh: 1198.2, fiyat: { epias_saat: 720, senaryo_saat: 0 }, resmi: null, fark_tl: null, fark_etiket: null,
      notlar: ["Serbest satışta (ikili anlaşma / GÖP) enerji satış tutarı EPİAŞ uzlaştırma bildiriminin bir kalemiyle birebir eşleşmez; resmî karşılaştırma yapılmaz."] },
    uzlastirma: { bilesenler: [b[1], b[2]], toplam: { ...toplam, tutar_tl: -70200, alacak_tl: 0, borc_tl: 70200, nitelik: "hesaplanan", nitelik_ad: "hesaplanan", giren: ["dengesizlik", "kupst"] }, fiyat: { epias_saat: 712, senaryo_saat: 0, yon_varsayilan_saat: 0, yon_eksik_saat: 8 },
      hesaplanamayan_saat: 8, kural_surumu: "edt-2026-V100-edta_ayrik", segment: "lisansli_serbest", santral_tasir: true, notlar: ["Enerji dengesizlik tutarı ve KGÜP sapma tutarı PVQuant'ın EPİAŞ saatlik fiyatı ve sistem yönüyle yeniden hesabıdır; EPİAŞ uzlaştırma sonucu değildir."],
      resmi: { bilesenler: [], fark: {}, durum: null, not: "Bu dönem için EPİAŞ bildirimi yüklenmedi; Mutabakat sayfasından yüklendiğinde hesaplanan tutar ile bildirilen tutar karşılaştırılır." }, gostergeler: { bilesenler: [b[3]] }, dsg: { neden: null, uye: null } },
    dusukluk: { tahmin_hatasi: { n_saat: 720, eksik_mwh: 61.4, fazla_mwh: 19.1, net_mwh: -42.3, program: "bildirilen KGÜP ve öneri karışık", wmape: 9.8, etiket: "program ile gerçekleşen farkı", dogrulama_n_saat: 360 },
      siniflar: [{ kod: "kisinti_bakim", ad: "Kısıntı, talimat ve planlı bakım", saat: 14, kayip_kwh: 16300, kayip_tl: 32600, nedenler: [] }, { kod: "fiziksel", ad: "Fiziksel kayıp (arıza, şebeke, kırpma)", saat: 9, kayip_kwh: 20800, kayip_tl: 41600, nedenler: [] },
        { kod: "olcum", ad: "Ölçüm yok", saat: 24, kayip_kwh: null, kayip_tl: null, nedenler: [] }, { kod: "aciklanmayan", ad: "Açıklanmayan sapma (tahmin belirsizliği dâhil)", saat: 318, kayip_kwh: 48900, kayip_tl: null, nedenler: [] }],
      kayip: { durum: "ok", mumkun_saat: 365, veri_saat: 341, epi: 0.94, toplam_kayip_kwh: 37100, toplam_kayip_tl: 74200, fiyatsiz_saat: 0 }, fiyat: { kaynak: "tarife", tip: "sabit", senaryo_saat: 0, etiket: "sabit tarife" }, sozlesme: null,
      bilesenler: [b[4], b[5]], notlar: ["Üretim düşüklüğü, hava tahmini girdili fizik beklentisi ile gerçekleşen arasındaki farkın neden sınıflarıdır; TL karşılığı gelir kaybı tahminidir, uzlaştırma kalemi değildir.", "Program ile gerçekleşen arasındaki fark tahmin hatasıdır; mali karşılığı enerji dengesizlik satırındadır, burada ikinci kez sayılmaz."] },
    maruziyet: { program_mwh: 286.4, saat: 168, kaynak: { bildirilen: 24, son_tahmin: 144 }, gecmis_gun: 30, oran_tl_mwh: { p25: -73.4, p50: -48.9, p75: -21.0 }, aralik_tl: { p25: -21000, p50: -14000, p75: -6000 }, nitelik: "senaryo",
      notlar: ["İleriye dönük maruziyet senaryodur: gelecek günlerin programı × son dönemde planlanan MWh başına gerçekleşen net uzlaştırma tutarının dağılımı (çeyrekler)."], bilesenler: [b[6]], ufuk: { bas: "2026-11-02", bit: "2026-11-09", gun: 7, gecmis_gun_pencere: 30 } },
    bilesenler: b, toplam, toplam_etiket: "enerji satışı + dengesizlik + KGÜP sapma tutarı (net; resmî satırlar, DSG, göstergeler, üretim düşüklüğü ve maruziyet toplama girmez)",
    oneriler: [
      { kod: "bildirim_yok", tur: "eylem", tur_ad: "eylem", metin: "Resmî uzlaştırma bildirimi yüklendiğinde hesaplanan tutar ile bildirilen tutar karşılaştırılabilir; EPYS'den indirdiğiniz dosyayı Mutabakat sayfasına yükleyin.", sayfa: "mutabakat", dayanak: null },
      { kod: "sozlesme_esigi", tur: "bilgi", tur_ad: "bilgi", metin: "Kullanılabilirlik sözleşme eşiği girilmediğinden sözleşme açığı hesaplanmadı; O&M sözleşmenizdeki eşiği Santral ayarlarına girebilirsiniz.", sayfa: "santralim", dayanak: null },
      { kod: "maruziyet", tur: "bilgi", tur_ad: "bilgi", metin: "Gelecek 7 günün programı için tahmini net uzlaştırma aralığı -21.000 … -6.000 TL (senaryo). Program düzeltmesi bu aralığı değiştirebilir; gerçekleşen tutar piyasa fiyatına ve sapmaya bağlıdır.", sayfa: "tahminler", dayanak: null },
      { kod: "dsg_kodu", tur: "bilgi", tur_ad: "bilgi", metin: "DSG kodu girilmediğinden DSG içi netleşme hesaplanmadı; Dengeden Sorumlu Grup üyeliğiniz varsa kodu Santral ayarlarına girin.", sayfa: "santralim", dayanak: null }],
    meta: { hesap_zamani: "2026-11-01T00:55:00+00:00", sozluk_surumu: "2026-11-11", yazilim_surumu: "v2.584-ornek", uretim_girdisi: "scada", pencere_gun: 44, segment: "lisansli_serbest", pozisyon: { kaynak: "program", sabit_mwh: null },
      kural_surumu: "edt-2026-V100-edta_ayrik", fiyat: { epias_saat: 712, senaryo_saat: 0 }, program_kaynak: { kaynak: "karisik", bildirilen_saat: 600, oneri_saat: 144, tamamlanan_saat: 24 }, tarife: { tip: "sabit", sha: "3b8f6bc9000ebbd5" }, bildirim: null, senaryo: null,
      isaret: "artı = santral lehine (alacak), eksi = santral aleyhine (borç)" },
  };
};
