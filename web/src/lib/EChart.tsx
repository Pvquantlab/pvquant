/** Ince ECharts sargisi (v2.73-A yeniden yazim — kayip lib/ dosyasi).
 *  Sozlesme kullanim yerlerinden: option + height + ariaLabel.
 *  Yasam dongusu: init -> setOption (degisimde) -> resize (gozlemci) -> dispose. */
import { useEffect, useRef, useState } from "react";
import * as echarts from "./echarts";
import type { EChartsOption } from "echarts";

/** 24.10 performans turu: grafik GÖRÜNÜR OLUNCA (ya da 240 px yaklaşınca) başlatılır — Santralim/Doğruluk'ta ekran
 *  altındaki 3–8 grafik sayfa açılışında tuval kurup çizmiyor (4× CPU'da 266 ms uzun görev ölçüldü). Kap yüksekliği
 *  baştan ayrılır (düzen kayması yok); IntersectionObserver yoksa eski davranış (hemen). Veri/option aynı. */
export function EChart({ option, height = 300, ariaLabel }:
  { option: EChartsOption; height?: number; ariaLabel?: string }) {
  const kutuRef = useRef<HTMLDivElement | null>(null);
  const grafikRef = useRef<echarts.ECharts | null>(null);
  const [gorunur, setGorunur] = useState(() => typeof IntersectionObserver === "undefined");

  useEffect(() => {
    if (gorunur || !kutuRef.current) return;
    const io = new IntersectionObserver((girdiler) => {
      if (girdiler.some((g) => g.isIntersecting)) { setGorunur(true); io.disconnect(); }
    }, { rootMargin: "240px 0px" });
    io.observe(kutuRef.current);
    return () => io.disconnect();
  }, [gorunur]);

  useEffect(() => {
    if (!gorunur || !kutuRef.current) return;
    const g = echarts.init(kutuRef.current, undefined,
      { devicePixelRatio: Math.max(2, window.devicePixelRatio || 1) });
    grafikRef.current = g;
    const gozlemci = new ResizeObserver(() => g.resize());
    gozlemci.observe(kutuRef.current);
    return () => { gozlemci.disconnect(); g.dispose(); grafikRef.current = null; };
  }, [gorunur]);

  useEffect(() => {
    grafikRef.current?.setOption(option, { notMerge: true });
  }, [option, gorunur]);

  return <div ref={kutuRef} role="img" aria-label={ariaLabel}
              style={{ width: "100%", height }} />;
}
