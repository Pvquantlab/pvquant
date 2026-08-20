/**
 * tahminPencere — pure windowing/anchoring/aggregation for the Tahminler view.
 *
 * D1/D2 architecture: the page fetches ONE full series (ufuk="16d") and every
 * view is a client-side slice around a single anchor t0 = now floored to the
 * hour. The now-value is computed ONCE from that anchor and shared by all
 * views. No DOM, no ECharts — unit-testable as-is.
 *
 * D4: forecast hours are reported as the ACTUAL future samples in the slice
 * (the archive may end before t0 + nominal horizon); past context is stated
 * separately. Horizon keys are the API contract and unchanged.
 */

import type { TahminSerisi } from "../../api/types";

export type Ufuk = "24h" | "72h" | "7d" | "16d";
export type Saatlik = TahminSerisi["saatlik"][number];

/** Nominal FORECAST span per horizon key (hours ahead of t0). */
export const UFUK_ILERI_SAAT: Record<Ufuk, number> = {
  "24h": 24,
  "72h": 72,
  "7d": 168,
  "16d": 360, // v2.156 user decision: horizon is 15 days / 360 h
};

/** Trailing past-context window per horizon — the single named table (D1). */
export const GECMIS_BAGLAM_SAAT: Record<Ufuk, number> = {
  "24h": 6,
  "72h": 24,
  "7d": 24,
  "16d": 24,
};

/** Views above 7 days render the daily envelope (L1). */
export const GUNLUK_MOD: Record<Ufuk, boolean> = {
  "24h": false,
  "72h": false,
  "7d": false,
  "16d": true,
};

const toMs = (ts: string) => new Date(ts).getTime();

/** Anchor: now floored to the current hour (D1). */
export function t0Hesapla(nowMs: number): number {
  return Math.floor(nowMs / 3_600_000) * 3_600_000;
}

/**
 * The single now-value (D2): P50 at the sample matching the floored anchor;
 * nearest-sample fallback when the archive grid is offset. Every view must
 * receive THIS value.
 */
export function simdiDegeri(
  saatlik: Saatlik[],
  t0Ms: number,
): number | null {
  if (saatlik.length === 0) return null;
  let best = 0;
  let bestD = Infinity;
  for (let i = 0; i < saatlik.length; i++) {
    const d = Math.abs(toMs(saatlik[i].ts) - t0Ms);
    if (d < bestD) {
      bestD = d;
      best = i;
    }
  }
  // > 1h away means t0 is outside the archive entirely — no honest now-value.
  return bestD <= 3_600_000 ? saatlik[best].p50_kw : null;
}

export type Dilim = {
  saatlik: Saatlik[];
  /** actual past-context hours included (may be clamped by archive start) */
  gecmisSaat: number;
  /** actual FORECAST hours included (may be clamped by archive end) — D4 */
  tahminSaat: number;
  /** nominal forecast hours for the tab label */
  nominalSaat: number;
};

/** Slice [t0 - context, t0 + horizon], clamped to the archive (D1/D5). */
export function dilimle(
  saatlik: Saatlik[],
  t0Ms: number,
  ufuk: Ufuk,
): Dilim {
  const startMs = t0Ms - GECMIS_BAGLAM_SAAT[ufuk] * 3_600_000;
  const endMs = t0Ms + UFUK_ILERI_SAAT[ufuk] * 3_600_000;
  const kesit = saatlik.filter((s) => {
    const ms = toMs(s.ts);
    return ms >= startMs && ms <= endMs;
  });
  let gecmis = 0;
  let tahmin = 0;
  for (const s of kesit) {
    if (toMs(s.ts) <= t0Ms) gecmis += 1;
    else tahmin += 1;
  }
  return {
    saatlik: kesit,
    gecmisSaat: gecmis,
    tahminSaat: tahmin,
    nominalSaat: UFUK_ILERI_SAAT[ufuk],
  };
}

export type GunToplam = {
  etiket: string; // "20 Ağu"
  p50Kwh: number;
  p10Kwh: number | null;
  p90Kwh: number | null;
  /** hours of the slice falling on this day */
  saat: number;
  /** true when the day is clipped by the window (head context / tail horizon) */
  kismi: boolean;
};

function tzDayKey(ms: number, tz: string): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: tz,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date(ms));
}

function fmtDay(ms: number, tz: string): string {
  return new Intl.DateTimeFormat("tr-TR", {
    timeZone: tz,
    day: "numeric",
    month: "short",
  }).format(new Date(ms));
}

/**
 * Daily energy totals derived from the SLICE (rows always match the plotted
 * window — D1 verification; D6 column population). Hourly kW × 1 h = kWh.
 * P10/P90 daily totals are sums of the hourly quantiles — the standard
 * full-temporal-correlation approximation; null (column hidden by the page)
 * when the run carries no quantiles (Mod B).
 */
export function gunlukToplamlar(
  saatlik: Saatlik[],
  tz: string,
): GunToplam[] {
  const rows: (GunToplam & { key: string; qOk: boolean })[] = [];
  for (const s of saatlik) {
    const ms = toMs(s.ts);
    const key = tzDayKey(ms, tz);
    let last = rows[rows.length - 1];
    if (!last || last.key !== key) {
      last = {
        key,
        etiket: fmtDay(ms, tz),
        p50Kwh: 0,
        p10Kwh: 0,
        p90Kwh: 0,
        saat: 0,
        kismi: false,
        qOk: true,
      };
      rows.push(last);
    }
    last.p50Kwh += s.p50_kw;
    last.saat += 1;
    if (typeof s.p10_kw === "number" && typeof s.p90_kw === "number") {
      (last.p10Kwh as number) += s.p10_kw;
      (last.p90Kwh as number) += s.p90_kw;
    } else {
      last.qOk = false;
    }
  }
  return rows.map(({ key: _k, qOk, ...r }) => ({
    ...r,
    kismi: r.saat < 24,
    p10Kwh: qOk ? r.p10Kwh : null,
    p90Kwh: qOk ? r.p90Kwh : null,
  }));
}
