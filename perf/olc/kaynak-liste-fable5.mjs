// kaynak-liste-fable5.mjs — bir sayfanın soğuk açılışta istediği TÜM kaynaklar (ad, bayt, tür, başlangıç/bitiş) — Chromium, kısıtsız hat.
// node olc/kaynak-liste-fable5.mjs --hedef fable5-once --gorunum 390x844 --sayfa ana
import { HEDEFLER, GORUNUMLER, SAYFALAR, motorAc, baglamAyar } from "./ortak.mjs";
const arg = (ad, vars) => { const i = process.argv.indexOf("--" + ad); return i > 0 ? process.argv[i + 1] : vars; };
const hedef = arg("hedef", "fable5-once"), g = GORUNUMLER[arg("gorunum", "390x844")], motor = arg("motor", "chromium");
const url = HEDEFLER[hedef].yok + SAYFALAR[arg("sayfa", "ana")];
const t = await motorAc(motor, hedef); const c = await t.newContext(baglamAyar(motor, g)); const p = await c.newPage();
await p.goto(url, { waitUntil: "load" }); await p.waitForTimeout(6000);
const r = await p.evaluate(() => performance.getEntriesByType("resource").map((e) => ({ u: e.name.replace(/^https?:\/\/[^/]+/, ""), tur: e.initiatorType, b: e.transferSize, ham: e.decodedBodySize, bas: Math.round(e.startTime), bit: Math.round(e.responseEnd) })));
console.log(`${motor} ${arg("gorunum", "390x844")} ${url}: ${r.length} kaynak, aktarım ${(r.reduce((s, e) => s + e.b, 0) / 1024).toFixed(0)} KB`);
for (const e of r.sort((a, z) => a.bas - z.bas)) console.log(String(e.bas).padStart(6), String(e.bit).padStart(6), String(e.b).padStart(9), String(e.ham).padStart(9), e.tur.padEnd(8), e.u.slice(0, 70));
await t.close();
