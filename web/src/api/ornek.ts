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
    { ay: "May 25", mwh: 722.5, saglam_saat: 402, kapsam_pct: 54.0 },
    { ay: "Haz 25", mwh: 866.1, saglam_saat: 431, kapsam_pct: 59.9 },
    { ay: "Tem 25", mwh: 892.4, saglam_saat: 446, kapsam_pct: 60.0 },
    { ay: "Ağu 25", mwh: 865.4, saglam_saat: 438, kapsam_pct: 58.9 },
    { ay: "Eyl 25", mwh: 767.4, saglam_saat: 421, kapsam_pct: 58.5 },
    { ay: "Eki 25", mwh: 606.3, saglam_saat: 442, kapsam_pct: 59.4 },
    { ay: "Kas 25", mwh: 494.0, saglam_saat: 376, kapsam_pct: 52.2 },
    { ay: "Ara 25", mwh: 449.2, saglam_saat: 401, kapsam_pct: 53.9 },
    { ay: "Oca 26", mwh: 380.6, saglam_saat: 402, kapsam_pct: 54.0 },
    { ay: "Şub 26", mwh: 406.8, saglam_saat: 387, kapsam_pct: 57.6 },
    { ay: "Mar 26", mwh: 641.8, saglam_saat: 449, kapsam_pct: 60.3 },
    { ay: "Nis 26", mwh: 630.2, saglam_saat: 484, kapsam_pct: 67.2 },
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
           simdi_idx: ufuk === "24h" ? 18 : null, saatlik, gunluk };
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
  beklenti: Array.from({ length: 12 }, (_, i) => ({
    ay: i + 1, p10: 60 + i * 14, p50: 75 + i * 15, p90: 90 + i * 16,
    yil_sayisi: 20 })),
  yillik: Array.from({ length: 60 }, (_, i) => ({
    yil: 2005 + (i % 5), ay: (i % 12) + 1,
    ghi_kwh_m2: 70 + ((i * 37) % 180) })),
};
