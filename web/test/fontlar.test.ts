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

test("vitrin ailesi @fontsource'tan: Gantari (v2.425 — Solcast kıyası, kullanıcı seçimi)", () => {
  const vitrin = oku("../src/features/vitrin/fontlar.ts");
  assert.doesNotMatch(vitrin, /fonts\.(googleapis|gstatic)\.com/);
  assert.ok(vitrin.includes("@fontsource-variable/gantari"), "@fontsource-variable/gantari");
  assert.match(oku("../src/features/vitrin/vitrin.css"), /--vt-baslik: 'Gantari Variable'/);
  assert.match(oku("../src/features/vitrin/vitrin.css"), /--vt-sans: 'Gantari Variable'/);
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
