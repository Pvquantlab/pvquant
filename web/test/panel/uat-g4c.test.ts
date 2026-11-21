/** UAT 21.11 G4-C1 — kadran: son TAMAMLANMIŞ saatin ölçümü (t0 süren saat; API ona ölçüm vermez). Davranış testi (QA Ö-10). */
import test from "node:test";
import assert from "node:assert/strict";
import { register } from "node:module";
register("./ts-cozucu.mjs", import.meta.url);   // tahminPencere → ../../lib/bicim (uzantısız) çözülsün
const { simdiGercekSon, simdiGercegi } = await import("../../src/features/sayfalar/tahminPencere.ts");

const T0 = Date.parse("2026-11-21T12:00:00Z");
const n = (h: number, g: number | null) => ({ ts: `2026-11-21T${String(h).padStart(2, "0")}:00:00Z`, p50_kw: 100, p10_kw: null, p90_kw: null, p25_kw: null, p75_kw: null, gercek_kw: g });

test("G4-C1: t0 örneği (süren saat) atlanır, t0−1 sa ölçümü döner", () => {
  const s = [n(10, 100), n(11, 200), n(12, 150), n(13, null)];
  assert.deepEqual(simdiGercekSon(s, T0), { kw: 200, ts: "2026-11-21T11:00:00Z" });
  assert.equal(simdiGercegi(s, T0), 150);   // eski kural t0 örneğini seçer — kadran artık bunu kullanmaz
});
test("G4-C1: t0−1 sa boşsa t0−2 sa; ikisi de boşsa null (daha eskisi «anlık» değil)", () => {
  assert.deepEqual(simdiGercekSon([n(10, 100), n(11, null), n(12, 150)], T0), { kw: 100, ts: "2026-11-21T10:00:00Z" });
  assert.equal(simdiGercekSon([n(9, 50), n(10, null), n(11, null), n(12, 150)], T0), null);
  assert.equal(simdiGercekSon([n(12, 150), n(13, 160)], T0), null);
  assert.deepEqual(simdiGercekSon([n(10, 0), n(11, 0)], T0), { kw: 0, ts: "2026-11-21T11:00:00Z" });   // gerçek 0 ölçümdür
});
