/** Ince ECharts sargisi (v2.73-A yeniden yazim — kayip lib/ dosyasi).
 *  Sozlesme kullanim yerlerinden: option + height + ariaLabel.
 *  Yasam dongusu: init -> setOption (degisimde) -> resize (gozlemci) -> dispose. */
import { useEffect, useRef } from "react";
import * as echarts from "echarts";
import type { EChartsOption } from "echarts";

export function EChart({ option, height = 300, ariaLabel }:
  { option: EChartsOption; height?: number; ariaLabel?: string }) {
  const kutuRef = useRef<HTMLDivElement | null>(null);
  const grafikRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!kutuRef.current) return;
    const g = echarts.init(kutuRef.current, undefined,
      { devicePixelRatio: Math.max(2, window.devicePixelRatio || 1) });
    grafikRef.current = g;
    const gozlemci = new ResizeObserver(() => g.resize());
    gozlemci.observe(kutuRef.current);
    return () => { gozlemci.disconnect(); g.dispose(); grafikRef.current = null; };
  }, []);

  useEffect(() => {
    grafikRef.current?.setOption(option, { notMerge: true });
  }, [option]);

  return <div ref={kutuRef} role="img" aria-label={ariaLabel}
              style={{ width: "100%", height }} />;
}
