/** 18.11 gezinme (Parti A #2): ECharts (209 KB gzip) kritik yoldan çıktı. Grafikli sayfaların modülü `./echarts`'ı statik
 *  içe aktardığından sayfa, kütüphane inmeden değerlenemiyordu (4G soğuk parça: Santralim başlığı 870 ms, Doğruluk 771 ms —
 *  sayfa parçası 115 ms'te inmişti). Kütüphane artık yalnız buradan, dinamik import ile ve bir kez iner; sayfa kabuğu/KPI'lar
 *  hemen gelir, grafikler kütüphane gelince dolar (kap yüksekliği baştan ayrılır, düzen kaymaz). Boş zaman ön yükleyicisi
 *  (App.tsx ONYUKLENECEKLER) aynı import() ifadesiyle parçayı önceden indirir. */
import type * as E from "./echarts";

export type EchartsModul = typeof E;
let modul: EchartsModul | null = null;
let soz: Promise<EchartsModul> | null = null;

/** İnmişse modülün kendisi (eşzamanlı; ilk çizimde bekleme yok), yoksa null. */
export function echartsHazir(): EchartsModul | null { return modul; }

/** Kütüphaneyi indirir (tek uçuş; başarısızlıkta bir sonraki çağrı yeniden dener). */
export function echartsYukle(): Promise<EchartsModul> {
  return (soz ??= import("./echarts").then((m) => (modul = m), (e: unknown) => { soz = null; throw e; }));
}
