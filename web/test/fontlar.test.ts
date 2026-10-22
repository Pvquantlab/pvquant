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
  for (const paket of ["@fontsource-variable/inter/opsz.css", "@fontsource/ibm-plex-mono/"]) {
    assert.ok(fontlar.includes(paket), paket);
  }
  // 22.10 tek tasarım sistemi: başlık ailesi vitrinle ortak Inter Tight; Space Grotesk bayt yükü olarak geri gelmesin
  assert.doesNotMatch(fontlar, /space-grotesk/);
  assert.match(oku("../src/main.tsx"), /import ['"]\.\/fontlar['"]/);
  assert.match(oku("../src/index.css"), /--font: 'Inter Variable', 'Inter'/);
  assert.match(oku("../src/index.css"), /--display: 'Inter Tight', 'Inter Tight Yedek', 'Inter Variable'/);
  // Inter Tight dosyalarını vitrin yükler; Vitrin.tsx tembel değil, ana pakette — panel de aynı yüzleri görür
  assert.match(oku("../src/App.tsx"), /import \{ Vitrin \} from "\.\/features\/vitrin\/Vitrin";/);
  assert.match(oku("../src/features/vitrin/Vitrin.tsx"), /import "\.\/fontlar";/);
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
  for (const d of ["ibm-plex-mono/400", "ibm-plex-mono/500", "ibm-plex-mono/600"]) {
    assert.ok(fontlar.includes(`@fontsource/${d}.css`), d);
  }
});

// 18.10 perf/cross-browser — FOUT kayması (390 px'te düğmeler 25 px zıplıyordu) ve Firefox'un gereksiz latin-ext inişi.
test("vitrin: metrik eşlemeli yedek yüz Inter Tight'tan hemen sonra; latin-ext aralığı tr/latin yüzlerinin çizdiğini kapsamaz", () => {
  const yedek = oku("../src/features/vitrin/font/inter-tight-yedek.css");
  const yuz = [...yedek.matchAll(/@font-face \{([\s\S]*?)\}/g)].map((m) => m[1]);
  assert.equal(yuz.length, 3, "üç ağırlık aralığı");
  for (const [agirlik, boy, ust, alt] of [["100 449", "94.52%", "102.49%", "25.52%"], ["450 549", "97.14%", "99.73%", "24.83%"], ["550 900", "92.72%", "104.48%", "26.01%"]]) {
    const y = yuz.find((x) => x.includes(`font-weight: ${agirlik};`));
    assert.ok(y, agirlik);
    assert.match(y, new RegExp(`size-adjust: ${boy.replace(".", "\\.")};`));
    assert.match(y, new RegExp(`ascent-override: ${ust.replace(".", "\\.")};`));
    assert.match(y, new RegExp(`descent-override: ${alt.replace(".", "\\.")};`));
    assert.match(y, /line-gap-override: 0%;/);
    assert.match(y, /src: local\(/, "yalnız yerel font: ağdan bayt yok");
    assert.doesNotMatch(y, /url\(/);
  }
  // tek kaynak: <head>'de satır içi (Firefox yüklenmemiş local() yüzü atlıyor); CSS demetine ikinci kez girmez
  assert.ok(!oku("../src/features/vitrin/fontlar.ts").includes('import "./font/inter-tight-yedek.css";'), "yedek CSS demetinde olmamalı");
  const css = oku("../src/features/vitrin/vitrin.css");
  for (const j of ["--vt-baslik", "--vt-sans"]) {
    const son = [...css.matchAll(new RegExp(`${j}: ([^;]+);`, "g"))].map((m) => m[1]).at(-1);
    assert.match(son ?? "", /^'Inter Tight', 'Inter Tight Yedek', ui-sans-serif, system-ui, sans-serif$/, j);
  }
  const yapi = oku("../vite.config.ts");
  assert.match(yapi, /plugins: \[interTightAralik\(\), react\(\), fontOnYukle\(\), yedekFont\(\), vitrinKabugu\(\), cssGom\(\), fontBekle\(\)\]/);
  assert.match(yapi, /new URL\('\.\/src\/features\/vitrin\/font\/inter-tight-yedek\.css', import\.meta\.url\)/);
  assert.ok(yapi.includes(`document.fonts.load(w+" 1em \\'Inter Tight Yedek\\'").catch(function(){})`), "yerel yüzler CSS inmeden yüklenir; yerel font yoksa (Android) red yakalanır");
  assert.ok(yapi.includes("'U+0100-011D,U+0120-012F,U+0132-015D,U+0160-02BA,'"), "ğ İ ı ş latin-ext'ten çıkar");
  assert.ok(yapi.includes("'U+20AD-20B9,U+20BB-20C0,'"), "₺ latin-ext'ten çıkar");
});
