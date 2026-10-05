/** Grafik teması — TEK doğruluk kaynağı (tasarım zekâsı Mühür B, v2.396).
 *
 *  Karar: echarts.registerTheme KULLANILMAZ — bu kod tabanında «tema», CSS
 *  jetonlarını (--chart-*, --izgara, --soluk…) okuyan bu fabrika katmanıdır.
 *  useTema().n koyu/açık geçişinde option'ları zaten yeniden kurar; ikinci bir
 *  kayıtlı tema çifte kaynak olurdu. (Sözleşme: .claude/skills/pvquant-tasarim/
 *  referans/grafik-tema.md)
 *
 *  Kural (bekçi testi zorlar): features/** altında grafik option'ı eksen/
 *  tooltip/ızgara stilini ELLE yazamaz — buradaki fabrikalardan kurar.
 *  Fabrikalar GÖRÜNÜMÜ verir; ölçek/veri/formatter karar düzeyi grafiğin
 *  kendisinde kalır (grafik-karar.md tablosu). */
import type { EChartsOption, XAXisComponentOption, YAXisComponentOption, TooltipComponentOption } from "echarts";

/** Eksen fabrikaları hem x hem y eksenine atanabilsin diye kesişim tipi —
 *  literal nesne iki bileşen tipinin de alanlarını taşır. */
type Eksen = XAXisComponentOption & YAXisComponentOption;

type Oku = (ad: string) => string;

/** Jeton paketi — kurucu başında BİR kez okunur (getComputedStyle maliyeti). */
export function renkler(oku: Oku) {
  return {
    metin: oku("--metin"), ikincil: oku("--ikincil"), soluk: oku("--soluk"),
    kart: oku("--kart"), kenar: oku("--kenar"), izgara: oku("--izgara"),
    mono: oku("--mono"),
    marka: oku("--marka"), markaKoyu: oku("--marka-koyu"),
    dusuk: oku("--ch-dusuk"), cubuk: oku("--ch-cubuk"),
    tahmin: oku("--chart-p50-future"),      // mavi = tahmin (sözleşme)
    gercek: oku("--chart-actual"),          // amber = YALNIZ gerçekleşen
    taban: oku("--chart-baseline"),
  };
}
export type Renkler = ReturnType<typeof renkler>;

type Sozluk = Record<string, unknown>;

/** Eksen yazısı: mono + soluk — sayı gövde fontuyla dizilmez (jetonlar.md). */
export function eksenYazi(r: Renkler, boyut = 10, ek?: Sozluk) {
  return { color: r.soluk, fontFamily: r.mono, fontSize: boyut, ...ek };
}

/** Değer ekseni: ızgara soluk + mono etiket. BİLEREK minimal — axisLine/
 *  axisTick görünümü grafikten grafiğe farklı (pilotta pixel-parite korunur),
 *  gerekiyorsa `ek` ile verilir. Formatter: eksenYazi(r, b, {formatter}). */
export function eksenDeger(r: Renkler, ek?: Sozluk): Eksen {
  return {
    type: "value" as const,
    splitLine: { lineStyle: { color: r.izgara } },
    axisLabel: eksenYazi(r),
    ...ek,
  } as Eksen;
}

/** Kategori ekseni: tiksiz + mono etiket. axisLine grafiğe göre `ek` ile. */
export function eksenKategori(r: Renkler, data: unknown[], ek?: Sozluk): Eksen {
  return {
    type: "category" as const, data,
    axisTick: { show: false },
    axisLabel: eksenYazi(r),
    ...ek,
  } as Eksen;
}

/** Tooltip gövdesi: kart zemini, yarım kenar, 12px metin — varsayılan beyaz
 *  kutu yasak. `ek`: trigger/formatter/valueFormatter. */
export function tooltipTemel(r: Renkler, ek?: Sozluk): TooltipComponentOption {
  return {
    backgroundColor: r.kart, borderColor: r.kenar, borderWidth: 0.5,
    textStyle: { color: r.metin, fontSize: 12 },
    ...ek,
  } as TooltipComponentOption;
}

/** Eksen tetikli tooltip kısayolu. */
export function tooltipEksen(r: Renkler, ek?: Sozluk): TooltipComponentOption {
  return tooltipTemel(r, { trigger: "axis" as const, ...ek });
}

/** Ortak kök: animasyon kapalı (grafik-karar.md ortak kuralı). */
export const TEMEL: Pick<EChartsOption, "animation"> = { animation: false };
