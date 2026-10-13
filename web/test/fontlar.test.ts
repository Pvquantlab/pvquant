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
