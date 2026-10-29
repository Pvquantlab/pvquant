/** 29.10 dil turu — alarm kuralı adları: panel (Santralim KURAL_ADI) ile arka uç (alarm_service.KURAL_ETIKET) aynı kod kümesi ve
 *  aynı Türkçe ad; ekranda ham kural kodu («pr_dustu») ve iç terim («isabet») görünmez. */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const oku = (p: string) => readFileSync(new URL(p, import.meta.url), "utf8");

test("alarm kuralı adları panel ve arka uçta birebir", () => {
  const py = oku("../../../src/pvquant/services/alarm_service.py");
  const tsx = oku("../../src/features/santralim/Santralim.tsx");
  const pyBlok = py.slice(py.indexOf("KURAL_ETIKET = {"), py.indexOf("}", py.indexOf("KURAL_ETIKET = {")) + 1).replace(/#[^\n]*/g, "");
  const tsBlok = tsx.slice(tsx.indexOf("const KURAL_ADI"), tsx.indexOf("};", tsx.indexOf("const KURAL_ADI")) + 1);
  const cift = (s: string) => Object.fromEntries([...s.matchAll(/["']?([a-z_]+)["']?\s*:\s*"([^"]+)"/g)].map((m) => [m[1], m[2]]));
  const arka = cift(pyBlok), on = cift(tsBlok);
  assert.ok(Object.keys(arka).length >= 8, "arka uç etiketleri okunamadı");
  assert.deepEqual(on, arka);
  assert.doesNotMatch(JSON.stringify(Object.values(arka)), /isabet/i);
  // eşik metni her kurala özgü: sabit kuralların eski «>6 s» kalıntısı yok
  assert.doesNotMatch(tsx, /\} s`\}/);
  assert.match(tsx, /k === "veri_gelmedi" \? "48 saat"/);
});
