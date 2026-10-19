// dpr-degis.mjs — stok Firefox: tuval etkinken aygıt pikseli yoğunluğu değişince (setViewport deviceScaleFactor) tampon yeniden
// boyutlanıyor mu. node olc/iz/dpr-degis.mjs --hedef sonra6
import puppeteer from "puppeteer-core";
import { HEDEFLER } from "../ortak.mjs";
const arg = (ad, vars) => { const i = process.argv.indexOf("--" + ad); return i > 0 ? process.argv[i + 1] : vars; };
const hedef = arg("hedef", "sonra6");
const bekle = (ms) => new Promise((r) => setTimeout(r, ms));
const t = await puppeteer.launch({ browser: "firefox", executablePath: "/Applications/Firefox.app/Contents/MacOS/firefox", headless: false, acceptInsecureCerts: true, defaultViewport: null });
const s = await t.newPage(); await s.setViewport({ width: 1440, height: 900, deviceScaleFactor: 2 });
await s.goto(HEDEFLER[hedef].yok + "/", { waitUntil: "load" });
await s.evaluate(async () => { const v = document.querySelector("video.vt-hero__video"); const b = performance.now();
  while (performance.now() - b < 40000 && !(v && !v.paused && v.readyState >= 3 && v.currentTime > 6.8)) await new Promise((r) => setTimeout(r, 100)); });
await bekle(1500);
const durum = () => s.evaluate(() => { const c = document.querySelector("canvas.vt-hero__keskin"), v = document.querySelector("video.vt-hero__video");
  return { dpr: devicePixelRatio, tuval: c ? `${c.width}×${c.height}` : "yok", hazir: c?.classList.contains("is-hazir"), kutu: `${v.clientWidth}×${v.clientHeight}`, suzgec: getComputedStyle(v).filter }; });
console.log("başlangıç", JSON.stringify(await durum()));
for (const d of [1, 1.5, 3, 2]) { await s.setViewport({ width: 1440, height: 900, deviceScaleFactor: d }); await bekle(1500); console.log(`dsf ${d}`, JSON.stringify(await durum())); }
await t.close();
