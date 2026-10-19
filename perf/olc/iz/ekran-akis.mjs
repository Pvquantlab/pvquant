// ekran-akis.mjs — DENEY: stok Firefox'ta (pencereli) hero videosunun EKRANDA ne sıklıkla değiştiği: 4 sn boyunca ~100 ms arayla
// hero bölgesinin ekran görüntüsü; ardışık görüntüler arası değişen piksel oranı → «ekranda yenilenen» görüntü sayısı.
// Değişkenler: mevcut (CSS süzgeci) · webgl (olc/iz/keskin-webgl.js) · filtresiz. node olc/iz/ekran-akis.mjs [--hedef sonra3]
import fs from "node:fs";
import puppeteer from "puppeteer-core";
import { PNG } from "pngjs";
import { HEDEFLER, GORUNUMLER } from "../ortak.mjs";
const arg = (ad, vars) => { const i = process.argv.indexOf("--" + ad); return i > 0 ? process.argv[i + 1] : vars; };
const hedef = arg("hedef", "sonra3"), g = GORUNUMLER[arg("gorunum", "1440x900")];
const KOD = fs.readFileSync(new URL("./keskin-webgl.js", import.meta.url), "utf8");
const bekle = (ms) => new Promise((r) => setTimeout(r, ms));
const t = await puppeteer.launch({ browser: "firefox", executablePath: "/Applications/Firefox.app/Contents/MacOS/firefox", headless: false, acceptInsecureCerts: true, defaultViewport: null });
const s = await t.newPage(); await s.setViewport({ width: g.width, height: g.height, deviceScaleFactor: g.dpr });
await s.goto(HEDEFLER[hedef].yok + "/", { waitUntil: "load" });
await s.evaluate(async () => { const v = document.querySelector("video.vt-hero__video"); const b = performance.now();
  while (performance.now() - b < 40000 && !(v && !v.paused && v.readyState >= 3 && v.currentTime > 6.8)) await new Promise((r) => setTimeout(r, 100)); });
await bekle(3000);
await s.evaluate((kod) => { (0, eval)(kod); const e = document.createElement("style"); e.textContent = ".vt-ust, .vt-hero .vt-kap, .vt-bolumcubuk { visibility: hidden !important; }"; document.head.appendChild(e); }, KOD);
const kutu = { x: 200, y: 300, width: 600, height: 400 };
for (const d of ["mevcut", "webgl", "filtresiz", "mevcut", "webgl", "filtresiz"]) {
  await s.evaluate((d) => { window.__keskinSok?.(); window.__keskinSok = null; document.getElementById("__ab")?.remove(); const v = document.querySelector("video.vt-hero__video");
    if (d === "webgl") window.__keskinKur(v, { adim: 1 });
    if (d === "filtresiz") { const e = document.createElement("style"); e.id = "__ab"; e.textContent = ".vt-hero video { filter: none !important; }"; document.head.appendChild(e); } }, d);
  await bekle(1500);
  const resimler = []; const b0 = Date.now(); const vt0 = await s.evaluate(() => document.querySelector("video.vt-hero__video").currentTime);
  while (Date.now() - b0 < 4000) { resimler.push(PNG.sync.read(Buffer.from(await s.screenshot({ clip: kutu, type: "png" })))); await bekle(60); }
  const vt1 = await s.evaluate(() => document.querySelector("video.vt-hero__video").currentTime);
  let degisen = 0; const oran = [];
  for (let i = 1; i < resimler.length; i++) { const a = resimler[i - 1].data, b = resimler[i].data; let n = 0;
    for (let j = 0; j < a.length; j += 4) if (Math.abs(a[j] - b[j]) + Math.abs(a[j + 1] - b[j + 1]) + Math.abs(a[j + 2] - b[j + 2]) > 6) n++;
    const o = n / (a.length / 4); oran.push(o); if (o > 0.002) degisen++; }
  console.log(`${d.padEnd(9)} görüntü ${resimler.length} · değişen ardışık çift ${degisen}/${resimler.length - 1} · video ${vt0.toFixed(2)}→${vt1.toFixed(2)} sn · değişim oranları ${oran.map((x) => (100 * x).toFixed(1)).join(" ")}`);
}
await t.close();
