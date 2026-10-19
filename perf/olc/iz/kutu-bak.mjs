// kutu-bak.mjs — stok Firefox: video ve tuval kutuları, tampon, object-position, video boyu (bir görünümde)
import puppeteer from "puppeteer-core";
import { HEDEFLER, GORUNUMLER } from "../ortak.mjs";
const arg = (ad, vars) => { const i = process.argv.indexOf("--" + ad); return i > 0 ? process.argv[i + 1] : vars; };
const hedef = arg("hedef", "sonra6"), gAd = arg("gorunum", "1366x768@1");
const g = GORUNUMLER[gAd] ?? (([w, h, d]) => ({ width: +w, height: +h, dpr: +d }))(gAd.split(/[x@]/));
const t = await puppeteer.launch({ browser: "firefox", executablePath: "/Applications/Firefox.app/Contents/MacOS/firefox", headless: false, acceptInsecureCerts: true, defaultViewport: null });
const s = await t.newPage(); await s.setViewport({ width: g.width, height: g.height, deviceScaleFactor: g.dpr });
await s.goto(HEDEFLER[hedef].yok + "/", { waitUntil: "load" });
await s.evaluate(async () => { const v = document.querySelector("video.vt-hero__video"); const b = performance.now();
  while (performance.now() - b < 40000 && !(v && !v.paused && v.readyState >= 3 && v.currentTime > 6.8)) await new Promise((r) => setTimeout(r, 100)); await new Promise((r) => setTimeout(r, 1500)); });
console.log(await s.evaluate(() => { const v = document.querySelector("video.vt-hero__video"), c = document.querySelector("canvas.vt-hero__keskin");
  const k = (e) => { const r = e.getBoundingClientRect(), cs = getComputedStyle(e); return { x: r.x, y: r.y, w: r.width, h: r.height, op: cs.objectPosition, of: cs.objectFit, tr: cs.transform, cw: e.clientWidth, ch: e.clientHeight }; };
  return JSON.stringify({ video: { ...k(v), vw: v.videoWidth, vh: v.videoHeight, kaynak: v.currentSrc.split("/").pop() }, tuval: { ...k(c), tw: c.width, th: c.height }, sahne: k(document.querySelector(".vt-hero__sahne")), ic: innerWidth + "×" + innerHeight }, null, 1); }));
await t.close();
