// v2.396 (Mühür B) — grafik teması bekçisi: fabrikalara geçmiş dosyalarda
// eksen/tooltip görünümü ELLE yazılamaz; tek kaynak lib/grafikTema.ts.
// Mühür C'de her göç eden dosya GECENLER listesine eklenir.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const oku = (yol: string) => readFileSync(new URL(yol, import.meta.url), "utf8");

// fabrikalara geçmiş dosyalar — ECharts kullanan TÜM dosyalar geçti (Mühür C, v2.397)
const GECENLER = [
  "../src/features/sayfalar/Dogruluk.tsx",
  "../src/features/sayfalar/Aylik.tsx",
  "../src/features/sayfalar/Digerleri.tsx",
  "../src/features/santralim/Cubuklar.tsx",
  "../src/features/santralim/Santralim.tsx",
];

// elle görünüm kurmanın imzaları — fabrika varken bunları yazmak yasak
const YASAK: [RegExp, string][] = [
  [/axisLabel:\s*\{\s*color:/, "elle axisLabel rengi (eksenYazi kullan)"],
  [/oku\("--/, "ham jeton okuması (renkler(oku) paketini kullan)"],
  [/tooltip:\s*\{\s*(trigger:[^,]+,\s*)?backgroundColor:/, "elle tooltip zemini (tooltipTemel/tooltipEksen kullan)"],
  [/splitLine:\s*\{\s*lineStyle:\s*\{\s*color:\s*oku\(/, "elle ızgara rengi (eksenDeger kullan)"],
  [/animation:\s*false/, "elle animation:false (TEMEL'i yay)"],
];

test("fabrikalara geçen grafik dosyaları görünümü elle kurmaz (grafik-tema bekçisi)", () => {
  for (const dosya of GECENLER) {
    const icerik = oku(dosya);
    assert.match(icerik, /from "\.\.\/\.\.\/lib\/grafikTema"/, `${dosya}: grafikTema importu yok`);
    for (const [desen, mesaj] of YASAK) {
      assert.doesNotMatch(icerik, desen, `${dosya}: ${mesaj}`);
    }
  }
});

test("grafikTema sözleşmesi: veri renk jetonları doğru kaynaktan", () => {
  const tema = oku("../src/lib/grafikTema.ts");
  assert.match(tema, /tahmin: oku\("--chart-p50-future"\)/);
  assert.match(tema, /gercek: oku\("--chart-actual"\)/);
  // kayıtlı tema bilinçli yok — geri gelirse çifte kaynak olur (yorum değil, çağrı aranır)
  assert.doesNotMatch(tema, /registerTheme\(/);
});

test("EChart sarmalayıcı sözleşmesi: lazyUpdate + grup/connect", () => {
  const sarici = oku("../src/lib/EChart.tsx");
  assert.match(sarici, /notMerge: true, lazyUpdate: true/);
  assert.match(sarici, /echarts\.connect\(grup\)/);
});
