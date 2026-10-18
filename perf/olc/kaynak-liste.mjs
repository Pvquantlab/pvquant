import { chromium, firefox, webkit } from "playwright";
import fs from "node:fs";
const SPKI = fs.readFileSync(".replika/once/spki.txt", "utf8").trim();
const URL = process.argv[2] || "https://localhost:18443/";
for (const [ad, tip, ops] of [["chromium", chromium, { args: ["--ignore-certificate-errors-spki-list=" + SPKI] }], ["firefox", firefox, {}], ["webkit", webkit, {}]]) {
  const b = await tip.launch(ops); const c = await b.newContext({ ignoreHTTPSErrors: true, viewport: { width: 1440, height: 900 } }); const p = await c.newPage();
  const istek = []; p.on("requestfinished", async (r) => { const s = await r.sizes().catch(() => null); istek.push({ u: r.url().replace(/^https:\/\/[^/]+/, ""), tur: r.resourceType(), b: s ? s.responseBodySize + s.responseHeadersSize : -1 }); });
  await p.goto(URL, { waitUntil: "load" }); await p.waitForTimeout(4000);
  const vid = await p.evaluate(() => [...document.querySelectorAll("video")].map(v => ({ src: (v.currentSrc || "").split("/").pop(), kaynak: [...v.querySelectorAll("source")].map(s => (s.getAttribute("media") || "-") + " → " + s.getAttribute("src").split("/").pop()), preload: v.preload, oynuyor: !v.paused, rs: v.readyState })));
  const top = istek.reduce((x, r) => x + Math.max(0, r.b), 0);
  console.log(`\n== ${ad} ${b.version()} — ${istek.length} istek, ${(top / 1e6).toFixed(1)} MB (Playwright gövde+başlık)`);
  for (const r of istek.sort((a, z) => z.b - a.b).slice(0, 8)) console.log(`  ${(r.b / 1e6).toFixed(2).padStart(6)} MB  ${r.tur.padEnd(10)} ${r.u.slice(0, 70)}`);
  console.log("  video:", JSON.stringify(vid));
  await b.close();
}
