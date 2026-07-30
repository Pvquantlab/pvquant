/** Ornek veri — Konya GES'in 30 Tem 2026 kosusundan. API baglanana kadar
 *  ekranin gercekci gorunmesi icin; uretimde hicbir yerde kullanilmaz. */
import type { SantralOzeti, TahminSerisi } from "./types";

export const ornekOzet: SantralOzeti = {
  ad: "Konya GES",
  kapasite_kwp: 4514,
  ac_tavani_kw: 3560,
  lat: 37.87,
  lon: 32.49,
  egim_azimut: "20° / 180° (varsayılan)",
  mod: "C",
  model_adi: "Hibrit",
  sapma_pct: 1.65,
  son_kalibrasyon: "2026-07-29",
  bugun_kwh: 30356,
  yarin_kwh: 30626,
  hafta_mwh: 212.9,
  gunler: [
    { etiket: "Bugün", mwh: 30.4 }, { etiket: "Yarın", mwh: 30.6 },
    { etiket: "Cmt", mwh: 31.6 }, { etiket: "Paz", mwh: 31.5 },
    { etiket: "Pzt", mwh: 29.8 }, { etiket: "Sal", mwh: 29.3 },
    { etiket: "Çar", mwh: 29.8 },
  ],
};

const PROFIL = [0, 0, 0, 0, 0, 40, 300, 900, 1500, 1620, 2600, 3300,
                3560, 3560, 3560, 3400, 2900, 2100, 1300, 500, 60, 0, 0, 0];

export function ornekTahmin(ufuk: "24h" | "72h" | "7d" | "16d"): TahminSerisi {
  const saat = { "24h": 24, "72h": 72, "7d": 168, "16d": 384 }[ufuk];
  const bas = new Date("2026-07-30T00:00:00+03:00").getTime();
  const saatlik = Array.from({ length: saat }, (_, i) => {
    const p50 = PROFIL[i % 24];
    return {
      ts: new Date(bas + i * 3600_000).toISOString(),
      p50_kw: p50,
      p10_kw: Math.round(p50 * 0.958),
      p90_kw: Math.round(p50 * 1.096),
    };
  });
  const gunluk = Array.from({ length: Math.ceil(saat / 24) }, (_, g) => {
    const dilim = saatlik.slice(g * 24, g * 24 + 24);
    const t = (k: "p50_kw" | "p10_kw" | "p90_kw") =>
      Math.round(dilim.reduce((a, s) => a + (s[k] ?? 0), 0));
    return {
      tarih: new Date(bas + g * 86_400_000).toISOString().slice(0, 10),
      p50_kwh: t("p50_kw"), p10_kwh: t("p10_kw"), p90_kwh: t("p90_kw"),
    };
  });
  return { mod: "C", model: "hybrid_residual", kosu_zamani: "2026-07-30T12:58:48Z",
           ufuk_saat: saat, saatlik, gunluk };
}
