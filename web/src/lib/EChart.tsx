/** Ince ECharts sargisi (v2.73-A; Mühür B v2.396 sözleşme güncellemesi).
 *  Sozlesme: option + height + ariaLabel + grup (echarts.connect ile senkron
 *  imleç/zoom — aynı grup adını taşıyan grafikler bağlanır).
 *  Yasam dongusu: init -> setOption (degisimde) -> resize (gozlemci) -> dispose.
 *  setOption notMerge:true KALIR (option'lar fabrikalardan her seferinde tam
 *  kurulur; merge eski seriyi sızdırır) + lazyUpdate: çizim bir kareye ertelenir.
 *  Tema: grafikTema.ts fabrikaları CSS jetonlarını okur, useTema().n değişimde
 *  option'ı yeniden kurar — kayıtlı ECharts teması BİLEREK yok (çifte kaynak). */
import { useEffect, useRef } from "react";
import * as echarts from "echarts";
import type { EChartsOption } from "echarts";

export function EChart({ option, height = 300, ariaLabel, grup }:
  { option: EChartsOption; height?: number; ariaLabel?: string; grup?: string }) {
  const kutuRef = useRef<HTMLDivElement | null>(null);
  const grafikRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!kutuRef.current) return;
    const g = echarts.init(kutuRef.current, undefined,
      { devicePixelRatio: Math.max(2, window.devicePixelRatio || 1) });
    grafikRef.current = g;
    if (grup) { g.group = grup; echarts.connect(grup); }
    const gozlemci = new ResizeObserver(() => g.resize());
    gozlemci.observe(kutuRef.current);
    return () => { gozlemci.disconnect(); g.dispose(); grafikRef.current = null; };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- grup mount sözleşmesidir, değişimi yeniden init gerektirir (kullanım yok)
  }, []);

  useEffect(() => {
    grafikRef.current?.setOption(option, { notMerge: true, lazyUpdate: true });
  }, [option]);

  return <div ref={kutuRef} role="img" aria-label={ariaLabel}
              style={{ width: "100%", height }} />;
}
