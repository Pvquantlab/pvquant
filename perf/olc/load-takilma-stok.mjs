// load-takilma-stok.mjs — aynı sınama stok Firefox 158 ile (puppeteer-core + WebDriver BiDi): ilk yükleme → hemen aynı adrese yeniden gezinme.
// node olc/load-takilma-stok.mjs [--tekrar 40] [--url https://localhost:18443/] [--basli]
import puppeteer from "puppeteer-core";
const arg = (ad, vars) => { const i = process.argv.indexOf("--" + ad); return i > 0 ? process.argv[i + 1] : vars; };
const url = arg("url", "https://localhost:18443/"), tekrar = Number(arg("tekrar", "40"));
const t = await puppeteer.launch({ browser: "firefox", executablePath: "/Applications/Firefox.app/Contents/MacOS/firefox", headless: !process.argv.includes("--basli"), acceptInsecureCerts: true, defaultViewport: null });
let takilma = 0, uzun = 0;
for (let k = 1; k <= tekrar; k++) {
  const b = await t.createBrowserContext(); const s = await b.newPage(); await s.setViewport({ width: 1440, height: 900, deviceScaleFactor: 2 });
  await s.goto(url, { waitUntil: "load", timeout: 45000 }).catch(() => {});
  await new Promise((r) => setTimeout(r, (k * 137) % 1500));        // video inerken yenile: 0–1,5 sn arası farklı anlar
  const vInis = await s.evaluate(() => { const v = document.querySelector("video"); return v ? v.networkState : -1; }).catch(() => -2);
  const t0 = Date.now();
  const ok = await s.goto(url, { waitUntil: "load", timeout: 15000 }).then(() => true).catch(() => false);
  const sure = Date.now() - t0;
  if (!ok) { takilma++; const d = await s.evaluate(() => document.readyState + " / video ağ " + document.querySelector("video")?.networkState).catch((e) => String(e)); console.log(`#${k} TAKILDI (15 sn; önceki video ağ ${vInis}) belge ${d}`); }
  else if (sure > 3000) { uzun++; console.log(`#${k} uzun: ${sure} ms`); }
  await b.close();
}
console.log(`stok Firefox ${await t.version()} · takılma ${takilma} / ${tekrar} · >3 sn ${uzun}`);
await t.close();
