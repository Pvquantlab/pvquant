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
  for (const s of ["genel", "santralim", "tahminler", "aylik", "dogruluk", "kalibrasyon", "kgup", "mutabakat", "finans", "sayac", "veri", "olaylar", "takvim"]) assert.match(cl, new RegExp(`\\n  ${s}: \\(p\\) => \\[api\\.`), s);
  assert.match(cl, /finans: \(p\) => \[api\.finansalEtki\(p, donemSecenekleri\("ay"\)\[1\]\?\.kod/);   // sayfanın ilk çağrısıyla aynı dönem → aynı yol
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

test("Mutabakat: iki veri yükleyicisi de son-çağrı-kazanır yarış korumalı", () => {
  const m = oku("../../src/features/sayfalar/Mutabakat.tsx");
  assert.equal((m.match(/const canli = useRef\(0\);/g) ?? []).length, 2);
  assert.equal((m.match(/if \(n === canli\.current\) set[KO]\(v\)/g) ?? []).length, 2);
  assert.doesNotMatch(m, /\.then\(set[KO], /);
});

test("Operasyon: Sayaç ve Olay kaydı yükleyicileri son-çağrı-kazanır; Veri yükleme kartları acik bayraklı", () => {
  for (const d of ["Sayac", "Olaylar"]) {
    const s = oku(`../../src/features/sayfalar/${d}.tsx`);
    assert.match(s, /const canli = useRef\(0\);/, d);
    assert.match(s, /const n = \+\+canli\.current;/, d);
    assert.doesNotMatch(s, /\.then\(setO, /, d);
  }
  const dg = oku("../../src/features/sayfalar/Digerleri.tsx");
  assert.match(dg, /let acik = true; api\.epiasUretim\(plantId\)/);
  assert.match(dg, /let acik = true; api\.isler\(\)/);
  // yönetim: Raporlar koşu listesi ve rapor gönderim kartı
  assert.match(dg, /let acik = true; api\.raporGonderim\(plantId\)/);
  assert.match(dg, /api\.kosular\(plantId\)\.then\(\(v\) => \{ if \(acik\) setKosular\(v\); \}\)/);
});
