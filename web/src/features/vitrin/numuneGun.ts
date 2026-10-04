/** Hero'daki 01.10.2026 numune günü (R19). GERÇEK araştırma koşusu verisi: gerçekleşen üretim
 *  kamuya açık üretim kaydından (açık ayna), bant ve P50 o gecenin koşusundan (v2.382 fiziği); değerler
 *  kurulu güce oran (0–1). Canlı panel çıktısı DEĞİLDİR ve künyede böyle söylenir. Sayılar elle
 *  değiştirilmez; tutarlılığı mantik.test.ts tarar. Kaynak: vitrin tasarım araştırması, 01.10 koşusu. */
export interface EgriNoktasi { saat: number; p10: number; p50: number; p90: number; gercek: number }

export const NUMUNE_TARIH = "01.10.2026";

const NUMUNE: readonly EgriNoktasi[] = [
  { saat: 5, p10: 0, p50: 0, p90: 0, gercek: 0 },
  { saat: 6, p10: 0, p50: 0, p90: 0, gercek: 0 },
  { saat: 7, p10: 0.0651, p50: 0.1391, p90: 0.1427, gercek: 0.065 },
  { saat: 8, p10: 0.2787, p50: 0.6519, p90: 0.6717, gercek: 0.1469 },
  { saat: 9, p10: 0.5316, p50: 0.9335, p90: 0.9335, gercek: 0.4576 },
  { saat: 10, p10: 0.6021, p50: 0.9444, p90: 0.9444, gercek: 0.546 },
  { saat: 11, p10: 0.6387, p50: 0.9067, p90: 0.9067, gercek: 0.5045 },
  { saat: 12, p10: 0.206, p50: 0.7244, p90: 0.8582, gercek: 0.7349 },
  { saat: 13, p10: 0.1924, p50: 0.7354, p90: 0.8797, gercek: 0.695 },
  { saat: 14, p10: 0.1577, p50: 0.723, p90: 0.9114, gercek: 0.666 },
  { saat: 15, p10: 0.0278, p50: 0.4525, p90: 0.6738, gercek: 0.2653 },
  { saat: 16, p10: 0.0157, p50: 0.3133, p90: 0.5457, gercek: 0.125 },
  { saat: 17, p10: 0.0068, p50: 0.1037, p90: 0.1621, gercek: 0.0244 },
  { saat: 18, p10: 0, p50: 0, p90: 0, gercek: 0 },
  { saat: 19, p10: 0, p50: 0, p90: 0, gercek: 0 },
];

export function numuneGun(): readonly EgriNoktasi[] {
  return NUMUNE;
}
