import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
const oku = (yol: string) => readFileSync(new URL(yol, import.meta.url), "utf8");

// 16.11.2026 gezinme hızı partisi — kaynak pinleri (davranış: istemci belleği damgaya bağlı 10 dk; yan menüde ısıtma; Santralim kademe + yarış koruması)
test("istemci belleği 10 dk (damga tazeler), ısıtma beş üretim sayfasını + Genel bakış'ı kapsar", () => {
  const cl = oku("../../src/api/client.ts");
  assert.match(cl, /const BELLEK_MS = 600_000;/);
  assert.match(cl, /export function bellekEskit\(\)/);                     // damga değişince yaş sıfırlanır — tazelik güvencesi bu
  assert.match(cl, /export function isit\(sayfa: string, plantId\?: string\): void/);
  for (const s of ["genel", "santralim", "tahminler", "aylik", "dogruluk", "kalibrasyon"]) assert.match(cl, new RegExp(`\\n  ${s}: \\(p\\) => \\[api\\.`), s);
  assert.match(cl, /if \(TABAN == null \|\| !plantId\) return;/);          // örnek kipte ve santralsız ısıtma yok
});

test("yan menü düğmesi niyet anında ısıtır (fare + odak), tıklama davranışı aynı", () => {
  const k = oku("../../src/shell/Kabuk.tsx");
  assert.match(k, /onClick=\{\(\) => \{ setSayfa\(s\.id\); setMenuAcik\(false\); \}\}\n\s+onMouseEnter=\{\(\) => isit\(s\.id, plantId\)\} onFocus=\{\(\) => isit\(s\.id, plantId\)\}/);
});

test("Santralim: her veri efekti yarış korumalı, ikincil kartlar özet gelince başlar", () => {
  const s = oku("../../src/features/santralim/Santralim.tsx");
  assert.match(s, /const plantRef = useRef\(plantId\); plantRef\.current = plantId;/);
  assert.match(s, /const hazir = o != null \|\| oHata;/);
  assert.ok((s.match(/plantRef\.current/g) ?? []).length >= 20, "yarış koruması sayısı");
  assert.equal((s.match(/if \(!hazir\) return;/g) ?? []).length, 9, "kademeli efekt sayısı");
  // korumasız .then(setX) kalmadı (veri efektlerinde)
  for (const satir of s.split("\n")) if (/useEffect\(\(\) => \{/.test(satir) && /\[plantId/.test(satir)) assert.doesNotMatch(satir, /\.then\(set[A-Za-z]+\)/, "korumasız mount efekti");
});
