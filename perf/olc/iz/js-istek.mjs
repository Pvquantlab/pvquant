// js-istek.mjs — soğuk yüklemede index-*.js için TÜM istekler (Resource Timing + ağ olayları), başlatıcı türü, konsol uyarıları.
// node olc/iz/js-istek.mjs --motor chromium --hedef sonra6 --yol /yontem --ag yavas4g --kosu 3
import { HEDEFLER, GORUNUMLER, motorAc, baglamAyar } from "../ortak.mjs";
const arg = (ad, vars) => { const i = process.argv.indexOf("--" + ad); return i > 0 ? process.argv[i + 1] : vars; };
const motor = arg("motor", "chromium"), hedef = arg("hedef", "sonra6"), yol = arg("yol", "/yontem"), ag = arg("ag", "yavas4g"), kosu = Number(arg("kosu", "3"));
const bekle = (ms) => new Promise((r) => setTimeout(r, ms));
async function hatBos(url) { const p = Number(new URL(url).port) + 1; let b = 0; for (let i = 0; i < 400; i++) { const d = await fetch(`http://127.0.0.1:${p}/`).then((r) => r.json()).catch(() => null); if (d && d.kuyruk <= 0 && d.asagiMs <= 0) { if ((b += 250) >= 750) return; } else b = 0; await bekle(250); } }
const t = await motorAc(motor, hedef);
for (let k = 1; k <= kosu; k++) {
  const b = await t.newContext(baglamAyar(motor, GORUNUMLER[arg("gorunum", "390x844")])); const s = await b.newPage();
  const istek = [], konsol = [];
  s.on("request", (r) => { if (/index-[\w-]+\.js/.test(r.url())) istek.push(r.resourceType()); });
  s.on("console", (m) => { if (["warning", "error"].includes(m.type())) konsol.push(m.type() + ": " + m.text().slice(0, 120)); });
  const url = HEDEFLER[hedef][ag] + yol; await hatBos(url);
  await s.goto(url, { waitUntil: "load", timeout: 120000 }); await s.waitForTimeout(4000);
  const r = await s.evaluate(() => ({ fcp: Math.round(performance.getEntriesByName("first-contentful-paint")[0]?.startTime ?? -1),
    js: performance.getEntriesByType("resource").filter((e) => /index-[\w-]+\.js/.test(e.name)).map((e) => `${e.initiatorType} ${Math.round(e.startTime)}→${Math.round(e.responseEnd)}`),
    kabuksuz: document.documentElement.classList.contains("vt-kabuksuz"), mp: document.querySelectorAll('link[rel="modulepreload"]').length }));
  console.log(`${motor} ${hedef} ${yol} #${k} FCP ${r.fcp} · kabuksuz=${r.kabuksuz} modulepreload=${r.mp} · RT: ${r.js.join(" | ")} · ağ istekleri: ${istek.join(",")}${konsol.length ? " · KONSOL: " + konsol.join(" ; ") : ""}`);
  await b.close();
}
await t.close();
