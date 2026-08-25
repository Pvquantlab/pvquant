/**
 * ProductionForecastChart v5 — utility-grade probabilistic PV forecast chart.
 *
 * v5 (data-correctness pass). The component no longer decides the window, the
 * mode, or the now-value: the page slices ONE series around ONE anchor
 * (tahminPencere.ts) and passes `nowValue` + `mode` down — D2's single source.
 *
 *  D3  A filled dot marks the series value at t0 on the now divider (the
 *      divider no longer implies y=0).
 *  V1  Daily mode renders a narrow ribbon: daily max(P10)..max(P90) hugging
 *      the daily max(P50) peak line — never an area anchored to zero.
 *  V2  AC limit: plain dashed terminus, no end symbols (own __rules series
 *      with markLine-level symbol ["none","none"]).
 *  V3  Day rules: 1px dotted, no markers. Only __now carries the single
 *      down-pointing triangle at the plot top.
 *  U2  3px minimum rendered band height in BOTH modes (display-level only;
 *      tooltips keep true values).
 *  U3  Saturation strip (v2.179, hourly only): hours where the band top
 *      rests on the AC ceiling (p90 >= limit*(1-1e-9), the client twin of
 *      backend flag ac_power_band_sature v2.177) get a thin tinted strip
 *      under the limit line + a tooltip row. The zero-width band there is
 *      ceiling-truncated, not model certainty; the exceed '>' test never
 *      fires on clipped data, so saturation was a blind spot.
 *  D7  Daily peak/ribbon aggregate the same clipped series the hourly view
 *      plots: max over the day of P50 (and of P10/P90 for the ribbon).
 *
 * Theme resolves live from <html data-tema="koyu">; `dark` prop overrides.
 * All colors come from CHART_TOKENS (CSS vars + spec fallbacks).
 */

import { useEffect, useMemo, useRef, useState } from "react";
import * as echarts from "echarts";
import type { EChartsOption, SeriesOption } from "echarts";

// ---------------------------------------------------------------- types

export type ForecastPoint = {
  ts: string;
  p10: number | null;
  p50: number;
  p90: number | null;
};

export type ActualPoint = { ts: string; kw: number };

export type Plant = {
  acCapacityKw: number | null;
  lat: number;
  lon: number;
  timezone: string;
};

export type ChartFeatures = {
  rangeSelector?: boolean;
  dataZoom?: boolean;
  exportButtons?: boolean;
};

export type ProductionForecastChartProps = {
  forecast: ForecastPoint[]; // pre-sliced window from tahminPencere.dilimle
  plant: Plant;
  /** Single anchor (ms) shared by every view — from tahminPencere.t0Hesapla. */
  nowMs: number;
  /** Single now-value shared by every view — from tahminPencere.simdiDegeri. */
  nowValue: number | null;
  mode: "hourly" | "daily";
  actual?: ActualPoint[];
  dark?: boolean;
  features?: ChartFeatures;
  height?: number;
};

// ---------------------------------------------------------------- tokens

function cssVar(name: string, fallback: string): string {
  if (typeof window === "undefined") return fallback;
  const v = getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();
  return v || fallback;
}

export const CHART_TOKENS = (dark: boolean) => ({
  p50Future: cssVar("--chart-p50-future", dark ? "#FBBF24" : "#D97706"),
  p50FutureWidth: 3,
  p50Past: cssVar("--chart-p50-past", dark ? "#14B8A6" : "#0D9488"),
  p50PastWidth: 2,
  bandFutFill: cssVar(
    "--chart-band-future",
    dark ? "rgba(245,158,11,0.28)" : "rgba(251,191,36,0.30)",
  ),
  bandFutEdge: cssVar("--chart-band-future-edge", dark ? "#FBBF24" : "#D97706"),
  bandFutEdgeOpacity: 0.5,
  bandPastFill: cssVar(
    "--chart-band-past",
    dark ? "rgba(20,184,166,0.16)" : "rgba(20,184,166,0.18)",
  ),
  bandPastEdge: cssVar("--chart-band-past-edge", dark ? "#2DD4BF" : "#0D9488"),
  bandPastEdgeOpacity: dark ? 0.35 : 0.4,
  bandEdgeWidth: 1,
  actualLine: cssVar("--chart-actual", dark ? "#E8ECEF" : "#1A222B"),
  actualWidth: 2.2, // v2.201: D cizim dili — gerceklesen murekkebi bir tik kalin
  acLimit: cssVar("--chart-limit", dark ? "#A78BFA" : "#7C3AED"),
  acExceedTint: cssVar(
    "--chart-limit-tint",
    dark ? "rgba(167,139,250,0.10)" : "rgba(124,58,237,0.08)",
  ),
  satureTint: cssVar(
    "--chart-sature-tint",
    dark ? "rgba(167,139,250,0.28)" : "rgba(124,58,237,0.22)",
  ),
  nowLine: cssVar("--chart-now", dark ? "#E2E8F0" : "#334155"),
  dayBreak: cssVar("--chart-daybreak", dark ? "#334155" : "#E2E8F0"),
  gridLine: cssVar("--chart-grid", dark ? "#1E293B" : "#EFF3F7"),
  axisText: cssVar("--chart-axis-text", dark ? "#94A3B8" : "#475569"),
  unitText: cssVar("--chart-unit", dark ? "#94A3B8" : "#64748B"),
  surface: cssVar("--chart-surface", dark ? "#0F172A" : "#FFFFFF"),
  labelText: dark ? "#E8ECEF" : "#1A222B",
  mutedText: cssVar("--chart-muted", dark ? "#94A3B8" : "#64748B"),
  btnBorder: cssVar("--chart-btn-border", "rgba(100,116,139,0.4)"),
  z: {
    rules: 0,
    exceedTint: 1,
    bandPast: 2,
    bandFut: 3,
    ac: 4,
    p50Past: 5,
    p50Fut: 6,
    exceed: 7,
    nowDot: 8,
  },
});

// ---------------------------------------------------------------- helpers

const toMs = (ts: string) => new Date(ts).getTime();
const nfKw = new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 0 });

function fmtTime(ms: number, tz: string): string {
  return new Intl.DateTimeFormat("tr-TR", {
    timeZone: tz,
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(ms));
}

function fmtDay(ms: number, tz: string): string {
  return new Intl.DateTimeFormat("tr-TR", {
    timeZone: tz,
    day: "numeric",
    month: "short",
  }).format(new Date(ms));
}

function fmtAxisLabel(ms: number, tz: string): string {
  const parts = new Intl.DateTimeFormat("tr-TR", {
    timeZone: tz,
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(new Date(ms));
  const get = (t: string) => parts.find((p) => p.type === t)?.value ?? "";
  return get("hour") === "00"
    ? `${get("day")} ${get("month")}`
    : `${get("hour")}:${get("minute")}`;
}

function tzHour(ms: number, tz: string): number {
  return Number(
    new Intl.DateTimeFormat("en-GB", {
      timeZone: tz,
      hour: "2-digit",
      hourCycle: "h23",
    }).format(new Date(ms)),
  );
}

function tzDayKey(ms: number, tz: string): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: tz,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date(ms));
}

function nearestTs(ms: number, tsList: string[]): string {
  let best = tsList[0];
  let bestD = Infinity;
  for (const t of tsList) {
    const d = Math.abs(toMs(t) - ms);
    if (d < bestD) {
      bestD = d;
      best = t;
    }
  }
  return best;
}

export function splitPastFuture<T>(
  values: (T | null)[],
  boundaryIdx: number,
): { past: (T | null)[]; future: (T | null)[] } {
  return {
    past: values.map((v, i) =>
      boundaryIdx >= 0 && i <= boundaryIdx ? v : null,
    ),
    future: values.map((v, i) => (i >= Math.max(boundaryIdx, 0) ? v : null)),
  };
}

export function bandSature(
  p90: number | null | undefined,
  acVal: number | null,
): boolean {
  // U3: v2.177 arka-uç maskesinin birebir istemci karşılığı.
  return acVal !== null && typeof p90 === "number" &&
    p90 >= acVal * (1 - 1e-9);
}

function contiguous(idx: boolean[]): [number, number][] {
  const out: [number, number][] = [];
  let s = -1;
  for (let i = 0; i < idx.length; i++) {
    if (idx[i] && s === -1) s = i;
    if ((!idx[i] || i === idx.length - 1) && s !== -1) {
      out.push([s, idx[i] ? i : i - 1]);
      s = -1;
    }
  }
  return out;
}

type BandStyle = {
  fill: string;
  edge: string;
  edgeOpacity: number;
  edgeWidth: number;
};

export function buildBandSeries(
  name: string,
  lower: (number | null)[],
  upper: (number | null)[],
  stackId: string,
  st: BandStyle,
  z: number,
): SeriesOption[] {
  const delta = upper.map((u, i) =>
    u === null || lower[i] === null ? null : u - (lower[i] as number),
  );
  const edge = { color: st.edge, opacity: st.edgeOpacity, width: st.edgeWidth };
  return [
    {
      name,
      type: "line",
      stack: stackId,
      data: lower,
      lineStyle: edge,
      symbol: "none",
      silent: true,
      z,
    },
    {
      name,
      type: "line",
      stack: stackId,
      data: delta,
      lineStyle: edge,
      symbol: "none",
      silent: true,
      z,
      areaStyle: { color: st.fill },
    },
  ];
}

// ---------------------------------------------------------------- daily agg
// D7/V1: aggregate the SAME (already clipped-or-not) series the hourly view
// plots — max over the plant-tz day of P50, P10 and P90.

type DayRow = {
  label: string;
  firstMs: number;
  lastMs: number;
  maxP50: number;
  maxP10: number | null;
  maxP90: number | null;
  /** sample count for the day — tail days with too few samples are pruned */
  saat: number;
};

export function buildDays(forecast: ForecastPoint[], tz: string): DayRow[] {
  const rows: (DayRow & { key: string })[] = [];
  for (const p of forecast) {
    const ms = toMs(p.ts);
    const key = tzDayKey(ms, tz);
    let last = rows[rows.length - 1];
    if (!last || last.key !== key) {
      last = {
        key,
        label: fmtDay(ms, tz),
        firstMs: ms,
        lastMs: ms,
        maxP50: p.p50,
        maxP10: p.p10,
        maxP90: p.p90,
        saat: 1,
      };
      rows.push(last);
    } else {
      last.saat += 1;
      last.lastMs = ms;
      last.maxP50 = Math.max(last.maxP50, p.p50);
      last.maxP10 =
        last.maxP10 === null || p.p10 === null
          ? null
          : Math.max(last.maxP10, p.p10);
      last.maxP90 =
        last.maxP90 === null || p.p90 === null
          ? null
          : Math.max(last.maxP90, p.p90);
    }
  }
  const out = rows.map(({ key: _k, ...r }) => r);
  // Prune the TAIL day when the horizon leaves it only a sliver (< 6 samples):
  // a near-empty final day plots as a false collapse-to-zero. Head days stay —
  // the current (partial) day is always meaningful.
  while (out.length > 1 && out[out.length - 1].saat < 6) out.pop();
  return out;
}

// ---------------------------------------------------------------- option

export type BuildInput = {
  forecast: ForecastPoint[];
  plant: Plant;
  nowMs: number;
  nowValue: number | null;
  mode: "hourly" | "daily";
  actual?: ActualPoint[];
  dark: boolean;
  features: ChartFeatures;
  narrow: boolean;
  plotHeightPx: number;
};

export function buildChartOption(input: BuildInput): EChartsOption {
  const {
    forecast,
    plant,
    nowMs,
    nowValue,
    mode,
    actual,
    dark,
    features,
    narrow,
  } = input;
  const T = CHART_TOKENS(dark);
  const tz = plant.timezone;
  const daily = mode === "daily";

  const rawMax = Math.max(
    plant.acCapacityKw ?? 0,
    ...forecast.map((p) => Math.max(p.p50, p.p90 ?? p.p50)),
  );
  const yMax = Math.max(1000, Math.ceil((rawMax * 1.05) / 1000) * 1000);
  const kwPerPx = yMax / Math.max(input.plotHeightPx, 1);
  const minKw = 3 * kwPerPx; // U2: 3px minimum rendered band height

  // v2.166: undefined 'null degil' tuzagi — acVal'i normalize et; aksi halde
  // AC markLine yAxis: undefined ile kurulur ve ECharts 'coord' cokusu verir.
  const acVal = plant.acCapacityKw ?? null;
  const series: SeriesOption[] = [];
  let cats: string[];
  let axisIntervalFn: (i: number, v: string) => boolean;
  let axisFmtFn: (v: string) => string;
  let nowCat: string;
  let dayRuleCats: string[] = [];
  let tooltipFmt: (c: string) => string;
  let exceedIdx: boolean[] = [];
  let satureIdx: boolean[] = []; // U3

  if (!daily) {
    // -------- hourly (24s / 72s / 7g)
    cats = forecast.map((p) => p.ts);
    let boundaryIdx = -1;
    for (let i = 0; i < cats.length; i++) {
      if (toMs(cats[i]) <= nowMs) boundaryIdx = i;
    }
    nowCat = boundaryIdx >= 0 ? cats[boundaryIdx] : cats[0]; // bos dizide undefined — asagida bekci var
    dayRuleCats = cats.filter((t) => tzHour(toMs(t), tz) === 0);
    axisIntervalFn = (_i, v) => {
      const h = tzHour(toMs(v), tz);
      return forecast.length > 96 ? h === 0 : h % 6 === 0;
    };
    axisFmtFn = (v) => fmtAxisLabel(toMs(v), tz);

    const byTs = new Map(forecast.map((p) => [p.ts, p]));
    const hasOuter = forecast.every(
      (p) => typeof p.p10 === "number" && typeof p.p90 === "number",
    );
    const actualByTs = new Map<string, number>();
    (actual ?? []).forEach((a) =>
      actualByTs.set(nearestTs(toMs(a.ts), cats), a.kw),
    );

    if (hasOuter) {
      const loAdj = forecast.map((p) => {
        const lo = p.p10 as number;
        const hi = p.p90 as number;
        return hi - lo < minKw ? Math.max(0, p.p50 - minKw / 2) : lo;
      });
      const hiAdj = forecast.map((p) => {
        const lo = p.p10 as number;
        const hi = p.p90 as number;
        return hi - lo < minKw ? Math.min(yMax, p.p50 + minKw / 2) : hi;
      });
      const lo = splitPastFuture(loAdj, boundaryIdx);
      const hi = splitPastFuture(hiAdj, boundaryIdx);
      series.push(
        ...buildBandSeries("bandPast", lo.past, hi.past, "b_past", {
          fill: T.bandPastFill,
          edge: T.bandPastEdge,
          edgeOpacity: T.bandPastEdgeOpacity,
          edgeWidth: T.bandEdgeWidth,
        }, T.z.bandPast),
        ...buildBandSeries("bandFut", lo.future, hi.future, "b_fut", {
          fill: T.bandFutFill,
          edge: T.bandFutEdge,
          edgeOpacity: T.bandFutEdgeOpacity,
          edgeWidth: T.bandEdgeWidth,
        }, T.z.bandFut),
      );
    }

    if (actualByTs.size > 0) {
      series.push({
        name: "actual",
        type: "line",
        data: cats.map((t) => actualByTs.get(t) ?? null),
        lineStyle: { color: T.actualLine, width: T.actualWidth },
        symbol: "none",
        connectNulls: false,
        z: T.z.p50Past,
      });
    }

    const p50sp = splitPastFuture(forecast.map((p) => p.p50), boundaryIdx);
    series.push(
      {
        name: "p50past",
        type: "line",
        data: p50sp.past,
        lineStyle: {
          color: T.p50Past,
          width: T.p50PastWidth,
          cap: "round",
          join: "round",
        },
        symbol: "none",
        z: T.z.p50Past,
      },
      {
        name: "p50fut",
        type: "line",
        data: p50sp.future,
        lineStyle: {
          color: T.p50Future,
          width: T.p50FutureWidth,
          cap: "round",
          join: "round",
        },
        symbol: "none",
        z: T.z.p50Fut,
      },
    );

    if (acVal !== null) {
      exceedIdx = forecast.map(
        (p) => p.p50 > acVal || (typeof p.p90 === "number" && p.p90 > acVal),
      );
      // U3: doyma = üst bant tavanda AMA aşım değil (aşım kendi dilini
      // konuşuyor); kırpık veride p90 > tavan imkânsız, bu yüzden ayrı test.
      satureIdx = forecast.map(
        (p, i) => bandSature(p.p90, acVal) && !exceedIdx[i],
      );
      const over = forecast.map((p) => (p.p50 > acVal ? p.p50 : null));
      if (over.some((v) => v !== null)) {
        series.push({
          name: "exceed",
          type: "line",
          data: over,
          lineStyle: { color: T.p50Future, width: 4, cap: "round" },
          symbol: "none",
          silent: true,
          z: T.z.exceed,
        });
      }
    }

    tooltipFmt = (ts: string) => {
      const p = byTs.get(ts);
      if (!p) return "";
      const isPast = toMs(ts) <= nowMs;
      const rows = [
        `<b>${fmtTime(toMs(ts), tz)} · ${isPast ? "Geçmiş" : "Tahmin"}</b>`,
        `P50&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;${nfKw.format(p.p50)} kW`,
      ];
      if (typeof p.p10 === "number" && typeof p.p90 === "number") {
        rows.push(
          `P10–P90&nbsp;&nbsp;${nfKw.format(p.p10)} – ${nfKw.format(
            p.p90,
          )} kW`,
          `Bant&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;${nfKw.format(
            p.p90 - p.p10,
          )} kW`,
        );
        if (bandSature(p.p90, acVal)) {
          // U3: sıfır/ince bant burada kesinlik değil, tavan kesmesi.
          rows.push(`Bant tavana dayalı — üst sınır AC kırpması`);
        }
      }
      if (acVal !== null) {
        rows.push(`AC payı&nbsp;&nbsp;&nbsp;${nfKw.format(acVal - p.p50)} kW`);
      }
      const a = actualByTs.get(ts);
      if (typeof a === "number") {
        rows.push(`Gerçekleşen&nbsp;${nfKw.format(a)} kW`);
      }
      return rows.join("<br/>");
    };
  } else {
    // -------- daily envelope (>7g) — V1 ribbon around the peak, D7 max(P50)
    const days = buildDays(forecast, tz);
    cats = days.map((d) => d.label);
    const byLabel = new Map(days.map((d) => [d.label, d]));
    let bIdx = -1;
    for (let i = 0; i < days.length; i++) {
      if (days[i].firstMs <= nowMs) bIdx = i;
    }
    nowCat = bIdx >= 0 ? cats[bIdx] : cats[0];
    axisIntervalFn = () => true;
    axisFmtFn = (v) => v;

    const hasQ = days.every(
      (d) => d.maxP10 !== null && d.maxP90 !== null,
    );
    const peak = days.map((d) => d.maxP50);
    const peakSp = splitPastFuture(peak, bIdx);

    if (hasQ) {
      const loAdj = days.map((d) => {
        const lo = d.maxP10 as number;
        const hi = d.maxP90 as number;
        return hi - lo < minKw ? Math.max(0, d.maxP50 - minKw / 2) : lo;
      });
      const hiAdj = days.map((d) => {
        const lo = d.maxP10 as number;
        const hi = d.maxP90 as number;
        return hi - lo < minKw ? Math.min(yMax, d.maxP50 + minKw / 2) : hi;
      });
      const lo = splitPastFuture(loAdj, bIdx);
      const hi = splitPastFuture(hiAdj, bIdx);
      series.push(
        ...buildBandSeries("ribPast", lo.past, hi.past, "r_past", {
          fill: T.bandPastFill,
          edge: T.bandPastEdge,
          edgeOpacity: T.bandPastEdgeOpacity,
          edgeWidth: T.bandEdgeWidth,
        }, T.z.bandPast),
        ...buildBandSeries("ribFut", lo.future, hi.future, "r_fut", {
          fill: T.bandFutFill,
          edge: T.bandFutEdge,
          edgeOpacity: T.bandFutEdgeOpacity,
          edgeWidth: T.bandEdgeWidth,
        }, T.z.bandFut),
      );
    }

    series.push(
      {
        name: "peakPast",
        type: "line",
        data: peakSp.past,
        lineStyle: { color: T.p50Past, width: 2, cap: "round" },
        symbol: "none",
        z: T.z.p50Past,
      },
      {
        name: "peakFut",
        type: "line",
        data: peakSp.future,
        lineStyle: { color: T.p50Future, width: 2, cap: "round" },
        symbol: "none",
        z: T.z.p50Fut,
      },
    );

    if (acVal !== null) {
      exceedIdx = days.map((d) => d.maxP50 > acVal);
      const over = days.map((d) => (d.maxP50 > acVal ? d.maxP50 : null));
      if (over.some((v) => v !== null)) {
        series.push({
          name: "exceed",
          type: "line",
          data: over,
          lineStyle: { color: T.p50Future, width: 4, cap: "round" },
          symbol: "none",
          silent: true,
          z: T.z.exceed,
        });
      }
    }

    tooltipFmt = (label: string) => {
      const d = byLabel.get(label);
      if (!d) return "";
      const isPast = d.lastMs <= nowMs;
      const rows = [
        `<b>${label} · ${isPast ? "Geçmiş" : "Tahmin"}</b>`,
        `Tepe P50&nbsp;&nbsp;${nfKw.format(d.maxP50)} kW`,
      ];
      if (d.maxP10 !== null && d.maxP90 !== null) {
        rows.push(
          `Tepe P10–P90&nbsp;&nbsp;${nfKw.format(d.maxP10)} – ${nfKw.format(
            d.maxP90,
          )} kW`,
        );
      }
      if (acVal !== null) {
        rows.push(
          `AC payı&nbsp;&nbsp;&nbsp;${nfKw.format(acVal - d.maxP50)} kW`,
        );
      }
      return rows.join("<br/>");
    };
  }

  // -------- rules: day boundaries + AC (no markers, V2/V3)
  series.push({
    name: "__rules",
    type: "line",
    data: [],
    silent: true,
    markLine: {
      silent: true,
      symbol: ["none", "none"], // series-level: kills default circle/arrow
      data: [
        ...dayRuleCats.map((t) => ({
          xAxis: t,
          lineStyle: { type: [2, 4], color: T.dayBreak, width: 1 },
          label: { show: false },
        })),
        ...(acVal !== null
          ? [
              {
                yAxis: acVal,
                lineStyle: { color: T.acLimit, type: [6, 4], width: 1.5 },
                label: { show: false },
              },
            ]
          : []),
      ] as never,
    },
    markArea:
      acVal !== null && (exceedIdx.some(Boolean) || satureIdx.some(Boolean))
        ? {
            silent: true,
            data: [
              ...contiguous(exceedIdx).map(([a, b]) => [
                {
                  xAxis: cats[a],
                  yAxis: acVal,
                  itemStyle: { color: T.acExceedTint },
                },
                { xAxis: cats[b], yAxis: yMax },
              ]),
              // U3: tavan altına yapışık ince şerit — kalınlık U2'nin
              // 3px diliyle (3*kwPerPx), taban 0'ın altına düşmez.
              ...contiguous(satureIdx).map(([a, b]) => [
                {
                  xAxis: cats[a],
                  yAxis: acVal,
                  itemStyle: { color: T.satureTint },
                },
                { xAxis: cats[b], yAxis: Math.max(0, acVal - 3 * kwPerPx) },
              ]),
            ] as never,
          }
        : undefined,
    z: T.z.rules,
  });

  // -------- now divider: its own series, single triangle at the top (V3)
  if (nowCat !== undefined) series.push({
    name: "__now",
    type: "line",
    data: [],
    silent: true,
    markLine: {
      silent: true,
      symbol: ["none", "triangle"],
      symbolSize: 8,
      symbolRotate: 180,
      data: [
        {
          xAxis: nowCat,
          lineStyle: { type: [6, 3], color: T.nowLine, width: 1.5 },
          label: { show: false },
        },
      ] as never,
    },
    z: T.z.rules,
  });

  // -------- D3: filled dot at the series value on the now divider
  if (nowValue !== null && !daily && nowCat !== undefined) {
    series.push({
      name: "__nowdot",
      type: "scatter",
      data: [[nowCat, nowValue]] as never,
      symbolSize: 8,
      itemStyle: {
        color: T.nowLine,
        borderColor: T.surface,
        borderWidth: 1.5,
      },
      silent: true,
      z: T.z.nowDot,
    });
  }

  return {
    animation: false,
    backgroundColor: "transparent",
    legend: { show: false }, // legend is the component's HTML layer
    grid: {
      // v2.201: D cizim dili — dondurulmus eksen basligi + alt eksen notu payi
      left: narrow ? 52 : 76,
      right: narrow ? 12 : 16,
      top: 34,
      bottom: features.dataZoom ? 58 : narrow ? 32 : 48,
    },
    graphic:
      acVal !== null
        ? [
            {
              type: "text",
              left: 4,
              top: 34 + input.plotHeightPx * (1 - acVal / yMax) - 6,
              style: {
                text: nfKw.format(acVal),
                fill: T.acLimit,
                font: "10px monospace",
              },
              silent: true,
              z: 50,
            },
          ]
        : [],
    xAxis: {
      type: "category",
      data: cats,
      boundaryGap: false,
      axisLabel: {
        color: T.axisText,
        hideOverlap: true,
        interval: axisIntervalFn as never,
        formatter: axisFmtFn,
        fontFamily: "monospace",
        fontSize: narrow ? 9 : 11,
      },
      axisLine: { lineStyle: { color: T.gridLine } },
      axisTick: { show: false },
      splitLine: { show: false },
      // v2.201: D cizim dili — Solargis'in koseli parantezli eksen notu
      ...(narrow ? {} : {
        name: daily ? "[gün · yerel]" : "[saat · yerel]",
        nameLocation: "middle" as const,
        nameGap: 30,
        nameTextStyle: { color: T.unitText, fontFamily: "monospace", fontSize: 10.5 },
      }),
    },
    yAxis: {
      type: "value",
      min: 0,
      max: yMax,
      interval: 1000,
      axisLabel: {
        color: T.axisText,
        fontFamily: "monospace",
        fontSize: narrow ? 9 : 11,
        formatter: (v: number) => nfKw.format(v),
      },
      splitLine: { lineStyle: { color: T.gridLine, width: 1 } },
      ...(narrow ? {} : {
        name: "Güç [kW]",
        nameLocation: "middle" as const,
        nameGap: 56,
        nameRotate: 90,
        nameTextStyle: { color: T.unitText, fontFamily: "monospace", fontSize: 10.5 },
      }),
    },
    ...(features.dataZoom
      ? {
          dataZoom: [
            { type: "inside" as const },
            { type: "slider" as const, height: 18, bottom: 6 },
          ],
        }
      : {}),
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "cross", label: { show: false } },
      backgroundColor: T.surface,
      borderColor: T.gridLine,
      borderWidth: 0.5,
      extraCssText: "box-shadow:none;",
      textStyle: { color: T.labelText, fontFamily: "monospace", fontSize: 12 },
      formatter: (params: unknown) => {
        const arr = params as { axisValue: string }[];
        if (!arr?.length) return "";
        return tooltipFmt(arr[0].axisValue);
      },
    },
    series,
  };
}

// ---------------------------------------------------------------- component

function useDomDark(override?: boolean): boolean {
  const read = () =>
    typeof document !== "undefined" &&
    document.documentElement.dataset.tema === "koyu";
  const [domDark, setDomDark] = useState(read);
  useEffect(() => {
    if (typeof document === "undefined") return;
    const obs = new MutationObserver(() => setDomDark(read()));
    obs.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-tema", "class"],
    });
    return () => obs.disconnect();
  }, []);
  return override ?? domDark;
}

function LineSample({ color, dashed }: { color: string; dashed?: boolean }) {
  return (
    <span
      style={{
        display: "inline-block",
        width: 18,
        borderTop: dashed ? `2px dashed ${color}` : `3px solid ${color}`,
        verticalAlign: "middle",
      }}
    />
  );
}

function BandSample({
  pastFill,
  futFill,
  pastEdge,
  futEdge,
}: {
  pastFill: string;
  futFill: string;
  pastEdge: string;
  futEdge: string;
}) {
  return (
    <span
      style={{
        display: "inline-block",
        width: 18,
        height: 10,
        verticalAlign: "middle",
        background: `linear-gradient(90deg, ${pastFill} 0 50%, ${futFill} 50% 100%)`,
        borderTop: `1px solid ${futEdge}`,
        borderBottom: `1px solid ${pastEdge}`,
        borderRadius: 2,
      }}
    />
  );
}

export default function ProductionForecastChart({
  forecast,
  plant,
  nowMs,
  nowValue,
  mode,
  actual,
  dark,
  features = {},
  height = 360,
}: ProductionForecastChartProps) {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);
  const [narrow, setNarrow] = useState(false);
  const isDark = useDomDark(dark);
  const T = CHART_TOKENS(isDark);

  const daily = mode === "daily";
  const hasOuter =
    !daily &&
    forecast.every(
      (p) => typeof p.p10 === "number" && typeof p.p90 === "number",
    );
  const hasActual = !daily && (actual ?? []).length > 0;
  const plotHeightPx = height - 34 - (features.dataZoom ? 58 : 30);

  const option = useMemo(
    () =>
      buildChartOption({
        forecast,
        plant,
        nowMs,
        nowValue,
        mode,
        actual,
        dark: isDark,
        features,
        narrow,
        plotHeightPx,
      }),
    [
      forecast,
      plant,
      nowMs,
      nowValue,
      mode,
      actual,
      isDark,
      features,
      narrow,
      plotHeightPx,
    ],
  );

  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    chartRef.current = chart;
    const onResize = () => {
      chart.resize();
      setNarrow(ref.current ? ref.current.clientWidth < 480 : false);
    };
    onResize();
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      chart.dispose();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    chartRef.current?.setOption(option, { notMerge: true });
  }, [option]);

  const exportCsv = () => {
    const head = ["ts", "p10", "p50", "p90", "gerceklesen_kw"];
    const aBy = new Map((actual ?? []).map((a) => [a.ts, a.kw]));
    const lines = forecast.map((p) =>
      [p.ts, p.p10 ?? "", p.p50, p.p90 ?? "", aBy.get(p.ts) ?? ""].join(","),
    );
    const blob = new Blob([[head.join(","), ...lines].join("\n")], {
      type: "text/csv;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "pvquant_tahmin.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  const exportPng = () => {
    const chart = chartRef.current;
    if (!chart) return;
    const a = document.createElement("a");
    a.href = chart.getDataURL({ pixelRatio: 2, backgroundColor: T.surface });
    a.download = "pvquant_tahmin.png";
    a.click();
  };

  const btn: React.CSSProperties = {
    font: "11px monospace",
    padding: "3px 8px",
    border: `1px solid ${T.btnBorder}`,
    borderRadius: 4,
    background: "transparent",
    color: "inherit",
    cursor: "pointer",
  };
  const key: React.CSSProperties = {
    display: "inline-flex",
    alignItems: "center",
    gap: 6,
    font: `${narrow ? 10 : 12}px monospace`,
    color: T.axisText,
  };
  const pill: React.CSSProperties = {
    font: "11px monospace",
    background: T.surface,
    border: `0.5px solid ${T.gridLine}`,
    borderRadius: 4,
    padding: "3px 7px",
  };

  return (
    <div>
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: narrow ? 10 : 16,
          justifyContent: "center",
          marginBottom: 6,
        }}
      >
        <span style={key}>
          <LineSample color={T.p50Past} />
          {daily ? "Geçmiş tepe" : "Geçmiş P50"}
        </span>
        <span style={key}>
          <LineSample color={T.p50Future} dashed />
          {daily ? "Tahmin tepe" : "Tahmin P50"}
        </span>
        {(hasOuter || daily) && (
          <span style={key}>
            <BandSample
              pastFill={T.bandPastFill}
              futFill={T.bandFutFill}
              pastEdge={T.bandPastEdge}
              futEdge={T.bandFutEdge}
            />
            {daily ? "Tepe P10–P90" : "P10–P90"}
          </span>
        )}
        {plant.acCapacityKw !== null && (
          <span style={key}>
            <LineSample color={T.acLimit} dashed />
            AC tavanı
          </span>
        )}
        {hasActual && (
          <span style={key}>
            <LineSample color={T.actualLine} />
            Gerçekleşen
          </span>
        )}
      </div>

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 8,
          marginBottom: 4,
        }}
      >
        <span style={{ ...pill, color: T.labelText }}>
          {nowValue !== null
            ? `şimdi · ${nfKw.format(nowValue)} kW`
            : "şimdi"}
        </span>
        <span style={{ font: "11px monospace", color: T.mutedText }}>
          {daily ? "günlük tepe ve aralık · " : ""}kW
        </span>
      </div>

      {features.exportButtons && (
        <div
          style={{
            display: "flex",
            gap: 6,
            justifyContent: "flex-end",
            marginBottom: 6,
          }}
        >
          <button style={btn} onClick={exportPng}>
            PNG
          </button>
          <button style={btn} onClick={exportCsv}>
            CSV
          </button>
        </div>
      )}
      <div ref={ref} style={{ width: "100%", height }} />
    </div>
  );
}
