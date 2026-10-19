// webgl-esdeger.mjs — DENEY: keskin-webgl.js tuvali ile CSS feConvolveMatrix süzgecinin piksel eşdeğerliği (duraklatılmış video karesi).
// node olc/iz/webgl-esdeger.mjs [--surucu firefox-stok,chrome] [--gorunum 1440x900,390x844] [--hedef sonra3] [--zaman 10]
// Her motorda: ozgun (CSS süzgeci) ×2 (gürültü tabanı) · webgl-css (komşu 1 CSS pikseli) · webgl-aygit (1 aygıt pikseli) · filtresiz.
import fs from "node:fs";
import path from "node:path";
import { PNG } from "pngjs";
import { chromium } from "playwright";
import puppeteer from "puppeteer-core";
import { KOK, GORUNUMLER, HEDEFLER, yaprakSpki } from "../ortak.mjs";

const arg = (ad, vars) => { const i = process.argv.indexOf("--" + ad); return i > 0 ? process.argv[i + 1] : vars; };
const suruculer = arg("surucu", "firefox-stok,chrome").split(","), gorunumler = arg("gorunum", "1440x900").split(",");
const hedef = arg("hedef", "sonra3"), zaman = Number(arg("zaman", "10"));
const cikti = path.join(KOK, arg("cikti", "analiz/webgl")); fs.mkdirSync(cikti, { recursive: true });
const KOD = fs.readFileSync(new URL("./keskin-webgl.js", import.meta.url), "utf8");
const bekle = (ms) => new Promise((r) => setTimeout(r, ms));
async function ac(surucu, g) {
  if (surucu === "firefox-stok") {
    const t = await puppeteer.launch({ browser: "firefox", executablePath: "/Applications/Firefox.app/Contents/MacOS/firefox", headless: false, acceptInsecureCerts: true, defaultViewport: null });
    const s = await t.newPage(); await s.setViewport({ width: g.width, height: g.height, deviceScaleFactor: g.dpr });
    return { surum: await t.version(), git: (u) => s.goto(u, { waitUntil: "load" }), deger: (f, a) => s.evaluate(f, a), resim: (clip) => s.screenshot({ clip, type: "png" }), kapat: () => t.close() };
  }
  const t = await chromium.launch({ headless: false, channel: surucu === "chrome" ? "chrome" : undefined, args: ["--ignore-certificate-errors-spki-list=" + (await yaprakSpki(hedef))] });
  const b = await t.newContext({ viewport: { width: g.width, height: g.height }, deviceScaleFactor: g.dpr, ignoreHTTPSErrors: true });
  const s = await b.newPage();
  return { surum: t.version(), git: (u) => s.goto(u, { waitUntil: "load" }), deger: (f, a) => s.evaluate(f, a), resim: (clip) => s.screenshot({ clip, type: "png" }), kapat: () => t.close() };
}
const kiyas = (a, b, kenar) => {
  if (a.width !== b.width || a.height !== b.height) return { boyut: [a.width, a.height, b.width, b.height] };
  let enBuyuk = 0, f1 = 0, f2 = 0, f4 = 0, f8 = 0, n = 0, top = 0;
  for (let y = kenar; y < a.height - kenar; y++) for (let x = kenar; x < a.width - kenar; x++) {
    const i = (y * a.width + x) * 4; const d = Math.max(Math.abs(a.data[i] - b.data[i]), Math.abs(a.data[i + 1] - b.data[i + 1]), Math.abs(a.data[i + 2] - b.data[i + 2]));
    n++; top += d; enBuyuk = Math.max(enBuyuk, d); if (d > 1) f1++; if (d > 2) f2++; if (d > 4) f4++; if (d > 8) f8++;
  }
  return { enBuyuk, ort: +(top / n).toFixed(3), ">1": +(f1 / n).toFixed(5), ">2": +(f2 / n).toFixed(5), ">4": +(f4 / n).toFixed(5), ">8": +(f8 / n).toFixed(5) };
};
const sonuc = [];
for (const surucu of suruculer) for (const gAd of gorunumler) {
  const g = GORUNUMLER[gAd] ?? (([w, h, d]) => ({ width: +w, height: +h, dpr: +d }))(gAd.split(/[x@]/)); const t = await ac(surucu, g);
  await t.git(HEDEFLER[hedef].yok + "/"); await bekle(2000);
  const durum = await t.deger(async (zaman) => { const v = document.querySelector("video.vt-hero__video"); const b = performance.now();
    while (performance.now() - b < 40000 && !(v && !v.paused && v.readyState >= 3)) await new Promise((r) => setTimeout(r, 100));
    v.pause(); v.currentTime = zaman; await new Promise((r) => { v.addEventListener("seeked", r, { once: true }); setTimeout(r, 5000); });
    const e = document.createElement("style"); e.textContent = "img.vt-hero__poster, .vt-ust, .vt-hero .vt-kap, .vt-hero__ortu, .vt-bolumcubuk { visibility: hidden !important; } .vt-hero::after, .vt-hero::before { display: none !important; }";
    document.head.appendChild(e);
    return { hazir: v.readyState, t: v.currentTime, kaynak: v.currentSrc.split("/").pop(), boy: [v.videoWidth, v.videoHeight] }; }, zaman);
  await t.deger((kod) => { (0, eval)(kod); }, KOD);
  const kutu = await t.deger(() => { const r = document.querySelector("video.vt-hero__video").getBoundingClientRect();
    return { x: Math.max(0, r.left), y: Math.max(0, r.top), width: Math.min(innerWidth, r.width), height: Math.min(innerHeight - Math.max(0, r.top), r.height) }; });
  await bekle(1000);
  const durumlar = arg("durum", "") ? [["ozgun", null], ["ozgun-tekrar", null], ...arg("durum").split(",").map((d) => [d, d === "filtresiz" ? "yok" : d])] : [["ozgun", null], ["ozgun-tekrar", null], ["webgl-css", 1], ["webgl-aygit", 1 / g.dpr], ["filtresiz", "yok"], ["webgl-kimlik", "kimlik"], ["webgl-css-1x", "1x"]];
  const resim = {}, bilgi = {};
  for (const [ad, adim] of durumlar) {
    bilgi[ad] = await t.deger(({ adim }) => { window.__keskinSok?.(); window.__keskinSok = null; const v = document.querySelector("video.vt-hero__video");
      document.getElementById("__ab")?.remove();
      if (adim === "yok") { const e = document.createElement("style"); e.id = "__ab"; e.textContent = ".vt-hero video { filter: none !important; }"; document.head.appendChild(e); return "filtresiz"; }
      if (adim === null) return getComputedStyle(v).filter;
      const AYAR = { "kesirli": { adim: 1, kesirli: true }, "snap": { adim: 1, kesirli: true, snap: true }, "h776-keskin": { adim: 1, H: 775.6 }, "h768": { adim: 1, kimlik: true, H: 768 }, "h776": { adim: 1, kimlik: true, H: 775.6 }, "h768-keskin": { adim: 1, H: 768 }, "webgl-css": { adim: 1 }, "mip": { adim: 1, mip: true }, "ss2": { adim: 1, ss: 2 }, "ss3": { adim: 1, ss: 3 }, "mip-ss2": { adim: 1, mip: true, ss: 2 } };
      return window.__keskinKur(v, adim === "kimlik" ? { adim: 1, kimlik: true } : adim === "1x" ? { adim: 1, olcek: 1 } : AYAR[adim] || { adim }) ? "webgl tamam" : "webgl YOK"; }, { adim });
    await bekle(1200);
    const buf = await t.resim(kutu); resim[ad] = PNG.sync.read(Buffer.from(buf));
    fs.writeFileSync(path.join(cikti, `${surucu}-${gAd}-${ad}.png`), Buffer.from(buf));
  }
  const r = { surucu, surum: t.surum, gorunum: gAd, durum, kutu, bilgi, kiyas: {} };
  for (const [ad] of durumlar.slice(1)) r.kiyas[ad] = { tum: kiyas(resim.ozgun, resim[ad], 0), ic: kiyas(resim.ozgun, resim[ad], 6) };
  if (resim.filtresiz && resim["webgl-kimlik"]) r.kiyas["kimlik↔filtresiz"] = { tum: kiyas(resim.filtresiz, resim["webgl-kimlik"], 0), ic: kiyas(resim.filtresiz, resim["webgl-kimlik"], 6) };
  sonuc.push(r);
  console.log(`${surucu} ${r.surum} ${gAd} ${JSON.stringify(durum)} ${JSON.stringify(bilgi)}`);
  for (const [ad, k] of Object.entries(r.kiyas)) console.log(`   ${ad.padEnd(13)} iç: en büyük ${k.ic.enBuyuk} · ort ${k.ic.ort} · >2 %${(100 * k.ic[">2"]).toFixed(3)} · >4 %${(100 * k.ic[">4"]).toFixed(3)} · >8 %${(100 * k.ic[">8"]).toFixed(3)}`);
  await t.kapat();
}
fs.writeFileSync(path.join(cikti, "esdeger.json"), JSON.stringify(sonuc, null, 1));
