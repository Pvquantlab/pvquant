// kritik-yol.mjs — soğuk yüklemede kaynak zaman çizelgesi (başlangıç→bitiş) ve FCP; derlemeler arası ilk boyama farkını açıklamak için.
// node olc/kritik-yol.mjs --motor firefox --gorunum 390x844 --ag yavas4g --kosu 5 [--hedef once,sonra]
import { HEDEFLER, GORUNUMLER, motorAc, baglamAyar } from "./ortak.mjs";
const arg = (ad, vars) => { const i = process.argv.indexOf("--" + ad); return i > 0 ? process.argv[i + 1] : vars; };
const motor = arg("motor", "firefox"), gAd = arg("gorunum", "390x844"), ag = arg("ag", "yavas4g"), kosu = Number(arg("kosu", "5"));
const bekle = (ms) => new Promise((r) => setTimeout(r, ms));
async function hatBos(url) { const p = Number(new URL(url).port) + 1; let b = 0; for (let i = 0; i < 400; i++) { const d = await fetch(`http://127.0.0.1:${p}/`).then((r) => r.json()).catch(() => null); if (d && d.kuyruk <= 0 && d.asagiMs <= 0) { if ((b += 250) >= 750) return; } else b = 0; await bekle(250); } }
for (const hedef of arg("hedef", "once,sonra").split(",")) {
  const t = await motorAc(motor, hedef);
  for (let k = 1; k <= kosu; k++) {
    const b = await t.newContext(baglamAyar(motor, GORUNUMLER[gAd])); const s = await b.newPage();
    const url = HEDEFLER[hedef][ag] + arg("yol", "/"); await hatBos(url);
    await s.goto(url, { waitUntil: "load", timeout: 120000 }); await s.waitForTimeout(3000);
    const r = await s.evaluate(() => { const n = performance.getEntriesByType("navigation")[0]; const fcp = performance.getEntriesByName("first-contentful-paint")[0]?.startTime;
      const k = performance.getEntriesByType("resource").filter((e) => /\.(css|js|woff2|webp)$/.test(e.name) || /dogrulama/.test(e.name)).map((e) => `${e.name.split("/").pop().replace(/-[\w-]{8}\.(\w+)$/, ".$1").slice(0, 22)} ${Math.round(e.startTime)}→${Math.round(e.responseEnd)}`);
      return { html: `${Math.round(n.responseStart)}→${Math.round(n.responseEnd)}`, dcl: Math.round(n.domContentLoadedEventEnd), fcp: Math.round(fcp), k }; });
    console.log(`${hedef} #${k} FCP ${r.fcp} · html ${r.html} · DCL ${r.dcl}\n    ${r.k.join(" | ")}`);
    await b.close();
  }
  await t.close();
}
