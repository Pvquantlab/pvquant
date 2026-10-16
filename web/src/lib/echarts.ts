/** ECharts — yalnız kullanılan parçalar (16.10 hız turu 4).
 *  Tüm paketi (`import * as echarts from "echarts"`) almak panel parçasını 1,1 MB (gzip 371 KB) yapıyordu;
 *  her kullanıcının ilk panel açılışında indirilip ayrıştırılıyordu. Liste kaynaktan çıkarıldı (seri türleri:
 *  line/bar/scatter/heatmap/custom; bileşenler: tooltip, legend, dataZoom slider+inside, visualMap, markLine/
 *  markArea/markPoint, graphic, axisPointer cross). YENİ BİR SERİ TÜRÜ YA DA BİLEŞEN eklenirse buraya da
 *  eklenmeli — eksik bileşen üretimde sessizce çizilmez (test/echarts.test.ts kaynakta tarar). */
import { use as parcalariKaydet } from "echarts/core";   // adı «use» — React kancası sanılmasın
import { BarChart, CustomChart, HeatmapChart, LineChart, ScatterChart } from "echarts/charts";
import {
  AxisPointerComponent, DataZoomComponent, GraphicComponent, GridComponent, LegendComponent,
  MarkAreaComponent, MarkLineComponent, MarkPointComponent, TooltipComponent, VisualMapComponent,
} from "echarts/components";
import { LabelLayout } from "echarts/features";
import { CanvasRenderer } from "echarts/renderers";

parcalariKaydet([
  LineChart, BarChart, ScatterChart, HeatmapChart, CustomChart,
  GridComponent, TooltipComponent, AxisPointerComponent, LegendComponent, DataZoomComponent, VisualMapComponent,
  MarkLineComponent, MarkAreaComponent, MarkPointComponent, GraphicComponent,
  LabelLayout, CanvasRenderer,
]);

export * from "echarts/core";
