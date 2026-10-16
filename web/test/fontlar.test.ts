// v2.384 — Fontlar kendi sunucumuzdan: Google Fonts isteği kalmamalı (KVKK + açılış hızı).
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const oku = (yol: string) => readFileSync(new URL(yol, import.meta.url), "utf8");

test("hiçbir giriş dosyası Google Fonts'a istek atmaz", () => {
  for (const yol of ["../index.html", "../src/index.css", "../src/main.tsx", "../src/fontlar.ts"]) {
    assert.doesNotMatch(oku(yol), /fonts\.(googleapis|gstatic)\.com/, yol);
  }
});

test("vitrin TEK aile Inter Tight (13.10 jua katmanı): 300/400/500/600 @fontsource'tan; eski aileler yüklenmez", () => {
  const vitrin = oku("../src/features/vitrin/fontlar.ts");
  assert.doesNotMatch(vitrin, /fonts\.(googleapis|gstatic)\.com/);
  for (const agirlik of ["300", "400", "500", "600"]) {
    assert.ok(vitrin.includes(`@fontsource/inter-tight/${agirlik}.css`), `Inter Tight ${agirlik}`);
  }
  // Bricolage/Plex Sans bayt yükü olarak geri gelmesin (gövde+başlık tek aile; Plex Mono genel yığından)
  assert.doesNotMatch(vitrin, /bricolage|ibm-plex-sans/);
  const css = oku("../src/features/vitrin/vitrin.css");
  // Jua katmanı kök jetonu ezer: son tanım kazanır → son --vt-baslik satırı Inter Tight olmalı
  const basliklar = [...css.matchAll(/--vt-baslik: ([^;]+);/g)].map((m) => m[1]);
  assert.match(basliklar[basliklar.length - 1], /^'Inter Tight'/);
  const sanslar = [...css.matchAll(/--vt-sans: ([^;]+);/g)].map((m) => m[1]);
  assert.match(sanslar[sanslar.length - 1], /^'Inter Tight'/);
  assert.match(css, /--vt-mono: 'IBM Plex Mono'/);   // sayı/künye gövde fontuyla dizilmez (jetonlar.md)
});

test("panel aileleri @fontsource'tan yüklenir; yığın 'Inter Variable' ile başlar", () => {
  const fontlar = oku("../src/fontlar.ts");
  for (const paket of ["@fontsource-variable/inter/opsz.css", "@fontsource/space-grotesk/", "@fontsource/ibm-plex-mono/"]) {
    assert.ok(fontlar.includes(paket), paket);
  }
  assert.match(oku("../src/main.tsx"), /import ['"]\.\/fontlar['"]/);
  assert.match(oku("../src/index.css"), /--font: 'Inter Variable', 'Inter'/);
  assert.match(oku("../src/index.css"), /--display: 'Space Grotesk', 'Inter Variable'/);
});

// 16.10 hız turu 4 — Türkçe harf alt kümesi ve unicode-range'li içe aktarma
test("vitrin: ğ/ş/İ küçük Türkçe alt kümeden gelir; latin-ext ön yüklenmez", () => {
  const vitrin = oku("../src/features/vitrin/fontlar.ts");
  const tr = vitrin.indexOf('import "./font/inter-tight-tr.css"');
  assert.ok(tr > 0, "Türkçe alt küme içe aktarılmalı");
  // sıra şart: çakışan unicode-range'de tarayıcı SON tanımlanan yüzü önce dener
  for (const agirlik of ["300", "400", "500", "600"]) {
    assert.ok(vitrin.indexOf(`@fontsource/inter-tight/${agirlik}.css`) < tr, `Türkçe alt küme ${agirlik}'den sonra gelmeli`);
  }
  const css = oku("../src/features/vitrin/font/inter-tight-tr.css");
  const yuzler = [...css.matchAll(/@font-face\s*\{([^}]*)\}/g)].map((m) => m[1]);
  assert.equal(yuzler.length, 3);
  for (const [i, agirlik] of ["400", "500", "600"].entries()) {
    assert.match(yuzler[i], new RegExp(`font-weight: ${agirlik};`));
    assert.match(yuzler[i], /font-family: 'Inter Tight';/);
    assert.match(yuzler[i], new RegExp(`src: url\\(\\./inter-tight-tr-${agirlik}\\.woff2\\)`));
    assert.match(yuzler[i], /unicode-range: U\+011E-011F,U\+0130,U\+015E-015F,U\+20BA;/);
  }
  const yapi = oku("../vite.config.ts");
  const kritik = /const KRITIK_FONT = (\/.*\/)\n/.exec(yapi)?.[1] ?? "";
  assert.ok(kritik && !kritik.includes("latin-ext"), "latin-ext ön yüklemesi geri gelmemeli: " + kritik);
  // Türkçe yüzler ön yüklenir ve CSS'e gömülmez (gömülü yüz ilk karede yedek fontla çizdiriyordu)
  const re = new RegExp(kritik.slice(1, -1));
  for (const ad of ["inter-tight-tr-500-AbC123xy.woff2", "inter-tight-tr-600-AbC123xy.woff2", "inter-tight-latin-500-normal-AbC123xy.woff2", "inter-tight-latin-600-normal-AbC123xy.woff2"]) {
    assert.ok(re.test(ad), `ön yüklenmeli: ${ad}`);
  }
  for (const ad of ["inter-tight-latin-ext-500-normal-AbC123xy.woff2", "inter-tight-latin-400-normal-AbC123xy.woff2", "inter-tight-tr-400-AbC123xy.woff2"]) {
    assert.ok(!re.test(ad), `ön yüklenmemeli: ${ad}`);
  }
  assert.match(yapi, /assetsInlineLimit: \(dosya\) => \(\/inter-tight-tr-\\d\{3\}\\\.woff2\$\/\.test\(dosya\) \? false : undefined\)/);
});

test("panel fontları toplu ağırlık dosyalarından: tek alt küme (unicode-range'siz) içe aktarma yok", () => {
  const fontlar = oku("../src/fontlar.ts");
  assert.doesNotMatch(fontlar, /@fontsource\/[\w-]+\/latin(-ext)?(-\d{3})?\.css/);
  for (const d of ["space-grotesk/500", "space-grotesk/600", "ibm-plex-mono/400", "ibm-plex-mono/500", "ibm-plex-mono/600"]) {
    assert.ok(fontlar.includes(`@fontsource/${d}.css`), d);
  }
});
