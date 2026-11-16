import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { yuzdeTr } from "../../src/lib/bicim.ts";

// 16.11.2026 — yüzde işaret sırası tek kural: «%» önek, işaret ondan ÖNCE (U+2212), isaret=true ile artı; sıfırda işaret yok.
test("yuzdeTr: işaret «%»den önce, tr-TR ondalık, tire yedeği", () => {
  assert.equal(yuzdeTr(-8.4), "\u2212%8,4");
  assert.equal(yuzdeTr(-14.52, 1), "\u2212%14,5");
  assert.equal(yuzdeTr(12.3), "%12,3");
  assert.equal(yuzdeTr(2.1, 1, true), "+%2,1");
  assert.equal(yuzdeTr(0, 1, true), "%0,0");
  assert.equal(yuzdeTr(-0.04, 1, true), "%0,0");   // yuvarlanınca sıfır → işaret yok
  assert.equal(yuzdeTr(96.8, 0), "%97");
  assert.equal(yuzdeTr(null), "\u2014"); assert.equal(yuzdeTr(undefined), "\u2014"); assert.equal(yuzdeTr(Number.NaN), "\u2014");
});

test("panelde «%${sayiTr(» kalıbı kalmadı (işaretli değerde «%−8,4» üretirdi)", () => {
  const kok = fileURLToPath(new URL("../../src/features", import.meta.url));
  const dosyalar: string[] = [];
  const gez = (d: string) => { for (const e of fs.readdirSync(d, { withFileTypes: true })) { const p = path.join(d, e.name); if (e.isDirectory()) { if (e.name !== "vitrin") gez(p); } else if (p.endsWith(".tsx")) dosyalar.push(p); } };
  gez(kok);
  for (const p of dosyalar) {
    const s = fs.readFileSync(p, "utf8");
    assert.doesNotMatch(s, /%\$\{sayiTr\(/, p);
    assert.doesNotMatch(s, /%\{sayiTr\(/, p);
  }
});
