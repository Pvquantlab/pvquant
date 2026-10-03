// v2.384 — Gizlilik Anayasası (docs/design/CLAUDE.md): vitrin metinlerinde yöntem ve kaynak adı geçmez.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { pathToFileURL, fileURLToPath } from "node:url";

const YASAK = [/erbs/i, /perez/i, /faiman/i, /barhdadi/i, /modelselector/i, /calibrate\(\)/i, /predict\(\)/i,
  /eta_bos/i, /bifacial/i, /BG=/, /η=/, /open-?meteo/i, /literatür katsayı/i, /pvlib/i,
  /gefs/i, /ecmwf/i, /sarah/i, /pvgis/i, /nasa/i, /\bnwp\b/i];

test("vitrin dosyalarında ve index.html'de yasaklı terim yok", () => {
  const kok = fileURLToPath(new URL("../../src/features/vitrin/", import.meta.url));
  const dosyalar = readdirSync(kok, { withFileTypes: true, recursive: true })
    .filter((g) => g.isFile())
    .map((g) => pathToFileURL(join(g.parentPath, g.name)));   // varlik/ SVG'leri dahil
  dosyalar.push(new URL("../../index.html", import.meta.url));
  for (const dosya of dosyalar) {
    const icerik = readFileSync(dosya, "utf8");
    for (const desen of YASAK) assert.doesNotMatch(icerik, desen, `${dosya.pathname}: ${desen}`);
  }
});
