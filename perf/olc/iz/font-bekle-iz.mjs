// font-bekle-iz.mjs — vt-font-bekle sınıfının eklenme/silinme anları, setTimeout zamanlaması, FCP (motor başına).
import { HEDEFLER, GORUNUMLER, motorAc, baglamAyar } from "../ortak.mjs";
const arg = (ad, vars) => { const i = process.argv.indexOf("--" + ad); return i > 0 ? process.argv[i + 1] : vars; };
const motor = arg("motor", "webkit"), hedef = arg("hedef", "sonra8"), ag = arg("ag", "yavas4g"), kosu = Number(arg("kosu", "2"));
const bekle = (ms) => new Promise((r) => setTimeout(r, ms));
async function hatBos(url) { const p = Number(new URL(url).port) + 1; let b = 0; for (let i = 0; i < 400; i++) { const d = await fetch(`http://127.0.0.1:${p}/`).then((r) => r.json()).catch(() => null); if (d && d.kuyruk <= 0 && d.asagiMs <= 0) { if ((b += 250) >= 750) return; } else b = 0; await bekle(250); } }
const t = await motorAc(motor, hedef);
for (let k = 1; k <= kosu; k++) {
  const b = await t.newContext(baglamAyar(motor, GORUNUMLER[arg("gorunum", "390x844")])); const s = await b.newPage();
  await s.addInitScript(() => {
    const iz = (window.__fb = []); const P = DOMTokenList.prototype, ek = P.add, si = P.remove, st = window.setTimeout;
    P.add = function (...a) { if (a.includes("vt-font-bekle")) iz.push("ekle@" + Math.round(performance.now())); return ek.apply(this, a); };
    P.remove = function (...a) { if (a.includes("vt-font-bekle")) iz.push("sil@" + Math.round(performance.now())); return si.apply(this, a); };
    window.setTimeout = function (f, ms, ...r) { if (ms === 100) { const kur = performance.now(); return st.call(this, () => { iz.push(`zamanlayıcı(${Math.round(kur)}→${Math.round(performance.now())})`); f(); }, ms, ...r); } return st.call(this, f, ms, ...r); };
  });
  const url = HEDEFLER[hedef][ag] + "/"; await hatBos(url);
  await s.goto(url, { waitUntil: "load", timeout: 120000 }); await s.waitForTimeout(1500);
  const r = await s.evaluate(() => ({ iz: window.__fb.join(" "), fcp: Math.round(performance.getEntriesByName("first-contentful-paint")[0]?.startTime ?? -1),
    font: performance.getEntriesByType("resource").filter((e) => /inter-tight-(latin|tr)-(500|600)/.test(e.name)).map((e) => Math.round(e.responseEnd)).join("/") }));
  console.log(`${motor} ${hedef} ${ag} #${k}: ${r.iz} · FCP ${r.fcp} · font bitişleri ${r.font}`);
  await b.close();
}
await t.close();
