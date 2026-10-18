// video-canli-mi.mjs — filtreli video ekranda gerçekten güncelleniyor mu? Oynarken 1 sn arayla iki ekran görüntüsü;
// hero bölgesinde değişen piksel oranı. Durumlar: mevcut filtre · filtresiz · ayrışık. node olc/video-canli-mi.mjs [--surucu firefox-stok|pw-firefox|pw-chromium|pw-webkit] [--basli]
import { PNG } from "pngjs";
import { chromium, firefox, webkit } from "playwright";
import puppeteer from "puppeteer-core";
import fs from "node:fs";
import path from "node:path";
import { KOK, HEDEFLER } from "./ortak.mjs";
const arg = (ad, vars) => { const i = process.argv.indexOf("--" + ad); return i > 0 ? process.argv[i + 1] : vars; };
const surucu = arg("surucu", "firefox-stok"), basli = process.argv.includes("--basli");
const bekle = (ms) => new Promise((r) => setTimeout(r, ms));
const spki = fs.readFileSync(path.join(KOK, HEDEFLER.once.spki), "utf8").trim();
const AYRISIK = `<filter id="vt-keskin-ab" color-interpolation-filters="sRGB" x="0" y="0" width="1" height="1"><feOffset in="SourceGraphic" dx="0.5" dy="0" result="l"/><feOffset in="SourceGraphic" dx="-0.5" dy="0" result="r"/><feOffset in="SourceGraphic" dx="0" dy="0.5" result="u"/><feOffset in="SourceGraphic" dx="0" dy="-0.5" result="a"/><feComposite in="l" in2="r" operator="arithmetic" k2=".5" k3=".5" result="lr"/><feComposite in="u" in2="a" operator="arithmetic" k2=".5" k3=".5" result="ua"/><feComposite in="lr" in2="ua" operator="arithmetic" k2=".5" k3=".5" result="m"/><feComposite in="SourceGraphic" in2="m" operator="arithmetic" k2="2.8" k3="-1.8"/></filter>`;
let s, kapat;
if (surucu === "firefox-stok") {
  const t = await puppeteer.launch({ browser: "firefox", executablePath: "/Applications/Firefox.app/Contents/MacOS/firefox", headless: !basli, acceptInsecureCerts: true, defaultViewport: null });
  s = await t.newPage(); await s.setViewport({ width: 1440, height: 900, deviceScaleFactor: 2 }); kapat = () => t.close();
} else {
  const m = { "pw-chromium": chromium, "pw-firefox": firefox, "pw-webkit": webkit }[surucu];
  const t = await m.launch({ headless: !basli, args: m === chromium ? ["--ignore-certificate-errors-spki-list=" + spki] : [] });
  const b = await t.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2, ignoreHTTPSErrors: true }); s = await b.newPage(); kapat = () => t.close();
}
await s.goto("https://localhost:18443/", { waitUntil: "load" });
await s.evaluate(async () => { const v = document.querySelector("video.vt-hero__video"); const b = performance.now(); while (performance.now() - b < 30000 && !(v && !v.paused && v.readyState >= 3)) await new Promise((r) => setTimeout(r, 100)); });
await bekle(2500);
await s.evaluate((svg) => { document.querySelector("svg.vt-hero__filtre").insertAdjacentHTML("beforeend", svg);
  const e = document.createElement("style"); e.textContent = ".vt-ust, .vt-hero .vt-kap, .vt-bolumcubuk { visibility: hidden !important; } .vt-hero::after, .vt-hero::before { display: none !important; }"; document.head.appendChild(e); }, AYRISIK);
const clip = { x: 100, y: 100, width: 1200, height: 650 };
for (const [ad, css] of [["mevcut", ""], ["filtresiz", ".vt-hero video, .vt-hero img { filter: none !important; }"], ["ayrisik", ".vt-hero video, .vt-hero img { filter: url(#vt-keskin-ab) !important; }"], ["mevcut-tekrar", ""]]) {
  await s.evaluate((css) => { document.getElementById("__ab")?.remove(); const e = document.createElement("style"); e.id = "__ab"; e.textContent = css; document.head.appendChild(e); }, css);
  await bekle(1000);
  const sonuclar = [];
  for (let i = 0; i < 3; i++) {
    const t0 = await s.evaluate(() => document.querySelector("video.vt-hero__video").currentTime);
    const a = PNG.sync.read(Buffer.from(await s.screenshot({ clip, type: "png" })));
    await bekle(700);
    const t1 = await s.evaluate(() => document.querySelector("video.vt-hero__video").currentTime);
    const b = PNG.sync.read(Buffer.from(await s.screenshot({ clip, type: "png" })));
    let deg = 0; for (let k = 0; k < a.data.length; k += 4) if (Math.abs(a.data[k] - b.data[k]) + Math.abs(a.data[k + 1] - b.data[k + 1]) + Math.abs(a.data[k + 2] - b.data[k + 2]) > 12) deg++;
    sonuclar.push(`video ${t0.toFixed(2)}→${t1.toFixed(2)} sn: değişen piksel %${(100 * deg / (a.width * a.height)).toFixed(1)}`);
  }
  console.log(surucu, ad.padEnd(14), sonuclar.join(" · "));
}
await kapat();
