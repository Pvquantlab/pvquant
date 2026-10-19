// lcp.mjs — soğuk yükleme, kısıtlı hat: son LCP adayı (zaman, öğe), FCP, poster isteği. Chromium ve Firefox (LCP API'si olan motorlar).
// node olc/iz/lcp.mjs --motor chromium --gorunum 768x1024 --ag yavas4g --hedef sonra3,araj --kosu 5   (hedefler dönüşümlü)
import { HEDEFLER, GORUNUMLER, MOTORLAR, motorAc, baglamAyar, yaprakSpki } from "../ortak.mjs";
const arg = (ad, vars) => { const i = process.argv.indexOf("--" + ad); return i > 0 ? process.argv[i + 1] : vars; };
const motor = arg("motor", "chromium"), gAd = arg("gorunum", "768x1024"), ag = arg("ag", "yavas4g"), kosu = Number(arg("kosu", "5"));
const hedefler = arg("hedef", "sonra3").split(",");
const bekle = (ms) => new Promise((r) => setTimeout(r, ms));
async function hatBos(url) { const p = Number(new URL(url).port) + 1; let b = 0; for (let i = 0; i < 400; i++) { const d = await fetch(`http://127.0.0.1:${p}/`).then((r) => r.json()).catch(() => null); if (d && d.kuyruk <= 0 && d.asagiMs <= 0) { if ((b += 250) >= 750) return; } else b = 0; await bekle(250); } }
const basli = process.argv.includes("--basli");   // pencereli: GPU ile tarama (başsız Chromium yazılımla tarar)
const tarayici = {}; for (const h of hedefler) tarayici[h] = basli ? await MOTORLAR[motor].launch({ headless: false, args: motor === "chromium" ? ["--ignore-certificate-errors-spki-list=" + (await yaprakSpki(h))] : [] }) : await motorAc(motor, h);
for (let k = 1; k <= kosu; k++) for (const h of (k % 2 ? hedefler : [...hedefler].reverse())) {
  const b = await tarayici[h].newContext(baglamAyar(motor, GORUNUMLER[gAd])); const s = await b.newPage();
  const url = HEDEFLER[h][ag] + "/"; await hatBos(url);
  await s.addInitScript(() => { window.__lcp = []; try { new PerformanceObserver((l) => { for (const e of l.getEntries()) window.__lcp.push({ t: e.startTime, el: e.element ? e.element.tagName.toLowerCase() + "." + String(e.element.className).split(" ")[0] : "?", url: (e.url || "").split("/").pop() }); }).observe({ type: "largest-contentful-paint", buffered: true }); } catch (x) {} });
  await s.goto(url, { waitUntil: "load", timeout: 120000 });
  await s.waitForFunction(() => performance.getEntriesByType("resource").some((e) => /santral-poster/.test(e.name) && e.responseEnd > 0), null, { timeout: 60000 }).catch(() => {});
  await s.waitForTimeout(3000);
  const r = await s.evaluate(() => { const p = performance.getEntriesByType("resource").find((e) => /santral-poster/.test(e.name)); const f = performance.getEntriesByName("first-contentful-paint")[0];
    const son = window.__lcp.at(-1) || {}; return { fcp: Math.round(f?.startTime ?? -1), lcp: Math.round(son.t ?? -1), el: son.el + (son.url ? "[" + son.url.replace(/-[\w-]{8}\.(\w+)$/, ".$1") + "]" : ""), poster: p ? `${Math.round(p.startTime)}→${Math.round(p.responseEnd)}` : "—" }; });
  console.log(`${gAd} ${motor}${basli ? "/başlı" : ""} ${h.padEnd(6)} #${k} FCP ${r.fcp} LCP ${r.lcp} ${r.el} poster ${r.poster}`);
  await b.close();
}
for (const t of Object.values(tarayici)) await t.close();
