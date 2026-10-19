// uretim-ayikla.mjs — üretim tuvalinin (keskinGL.ts) gerçekte kullandığı değerler: ResizeObserver girdileri ve WebGL uniform/viewport
// çağrıları sayfa açılmadan sarılır ve kaydedilir. node olc/iz/uretim-ayikla.mjs --hedef sonra6 --gorunum 1366x768@1
import puppeteer from "puppeteer-core";
import { HEDEFLER, GORUNUMLER } from "../ortak.mjs";
const arg = (ad, vars) => { const i = process.argv.indexOf("--" + ad); return i > 0 ? process.argv[i + 1] : vars; };
const hedef = arg("hedef", "sonra6"), gAd = arg("gorunum", "1366x768@1");
const g = GORUNUMLER[gAd] ?? (([w, h, d]) => ({ width: +w, height: +h, dpr: +d }))(gAd.split(/[x@]/));
const t = await puppeteer.launch({ browser: "firefox", executablePath: "/Applications/Firefox.app/Contents/MacOS/firefox", headless: false, acceptInsecureCerts: true, defaultViewport: null });
const s = await t.newPage(); await s.setViewport({ width: g.width, height: g.height, deviceScaleFactor: g.dpr });
await s.evaluateOnNewDocument(() => {
  const k = (window.__k = []); const RO = window.ResizeObserver;
  window.ResizeObserver = class extends RO { constructor(f) { super((es, o) => { for (const e of es) k.push(["ro", e.target.tagName, e.contentBoxSize?.[0]?.inlineSize, e.contentBoxSize?.[0]?.blockSize, e.contentRect.width, e.contentRect.height]); f(es, o); }); } };
  const P = WebGLRenderingContext.prototype;
  for (const ad of ["uniform4f", "uniform2f", "uniform1f", "viewport"]) { const o = P[ad]; P[ad] = function (...a) { k.push([ad, ...a.filter((x) => typeof x === "number").map((x) => +x.toPrecision(7))]); return o.apply(this, a); }; }
});
await s.goto(HEDEFLER[hedef].yok + "/", { waitUntil: "load" });
await s.evaluate(async () => { const v = document.querySelector("video.vt-hero__video"); const b = performance.now();
  while (performance.now() - b < 40000 && !(v && !v.paused && v.readyState >= 3 && v.currentTime > 6.8)) await new Promise((r) => setTimeout(r, 100)); await new Promise((r) => setTimeout(r, 1500)); });
console.log(await s.evaluate(() => JSON.stringify({ kayit: window.__k.slice(0, 30), video: [document.querySelector("video.vt-hero__video").getBoundingClientRect().height], tampon: [document.querySelector("canvas.vt-hero__keskin").width, document.querySelector("canvas.vt-hero__keskin").height] })));
await t.close();
