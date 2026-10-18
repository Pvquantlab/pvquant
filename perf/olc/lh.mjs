// lh.mjs — Lighthouse 12 (Chromium; Firefox/WebKit için Lighthouse YOK). Mobil (varsayılan: benzetilmiş Slow 4G + 4× CPU)
// ve masaüstü ön ayarı; «/» ve «/yontem»; 3 koşu. node olc/lh.mjs --hedef once|sonra|canli --cikti baseline [--kosu 3]
import fs from "node:fs";
import path from "node:path";
import lighthouse from "lighthouse";
import desktopConfig from "lighthouse/core/config/desktop-config.js";
import * as chromeLauncher from "chrome-launcher";
import { chromium } from "playwright";
import { KOK, HEDEFLER, SAYFALAR, yaprakSpki } from "./ortak.mjs";

const arg = (ad, vars) => { const i = process.argv.indexOf("--" + ad); return i > 0 ? process.argv[i + 1] : vars; };
const hedef = arg("hedef", "once");
const cikti = path.join(KOK, arg("cikti", "baseline"), "lighthouse");
const kosu = Number(arg("kosu", "3"));
fs.mkdirSync(cikti, { recursive: true });
const dosya = path.join(cikti, `lh-${hedef}.jsonl`);
const bayrak = ["--headless=new", "--no-first-run", "--no-default-browser-check", "--disable-extensions"];
if (HEDEFLER[hedef].spki) bayrak.push("--ignore-certificate-errors-spki-list=" + (await yaprakSpki(hedef)));   // canlı yaprak SPKI (ortak.mjs)
const ILGI = ["render-blocking-resources", "unused-javascript", "unused-css-rules", "uses-responsive-images", "modern-image-formats", "uses-optimized-images",
  "image-size-responsive", "font-display", "total-byte-weight", "largest-contentful-paint-element", "layout-shifts", "lcp-lazy-loaded",
  "prioritize-lcp-image", "bootup-time", "mainthread-work-breakdown", "non-composited-animations", "server-response-time", "uses-long-cache-ttl", "dom-size", "efficient-animated-content"];

for (const [sAd, yol] of Object.entries(SAYFALAR)) for (const tur of ["mobil", "masaustu"]) for (let k = 1; k <= kosu; k++) {
  const chrome = await chromeLauncher.launch({ chromePath: chromium.executablePath(), chromeFlags: bayrak });
  try {
    const url = HEDEFLER[hedef].yok + yol;
    const sonuc = await lighthouse(url, { port: chrome.port, output: ["json", "html"], logLevel: "error" }, tur === "masaustu" ? desktopConfig : undefined);
    const lhr = sonuc.lhr;
    const a = lhr.audits;
    const sayi = (id) => a[id]?.numericValue ?? null;
    const kayit = {
      hedef, sayfa: sAd, tur, kosu: k, surum: lhr.lighthouseVersion, chrome: lhr.environment?.hostUserAgent?.match(/Chrome\/[\d.]+/)?.[0],
      skor: Object.fromEntries(Object.entries(lhr.categories).map(([id, c]) => [id, c.score === null ? null : Math.round(c.score * 100)])),
      metrik: { fcp: sayi("first-contentful-paint"), lcp: sayi("largest-contentful-paint"), tbt: sayi("total-blocking-time"), cls: sayi("cumulative-layout-shift"), si: sayi("speed-index"), ttfb: sayi("server-response-time") },
      uyari: Object.fromEntries(ILGI.filter((id) => a[id]).map((id) => [id, { skor: a[id].score, deger: a[id].displayValue ?? null, ozet: (a[id].details?.items || []).slice(0, 5).map((it) => it.url || it.node?.snippet || it.node?.selector || it.label || it.groupLabel || null) }])),
      calismaZamani: lhr.runtimeError ?? null, uyarilar: lhr.runWarnings,
    };
    fs.appendFileSync(dosya, JSON.stringify(kayit) + "\n");
    fs.writeFileSync(path.join(cikti, `lh-${hedef}-${sAd}-${tur}-${k}.html`), sonuc.report[1]);
    console.log(`LH ${hedef} ${sAd} ${tur} #${k}: perf ${kayit.skor.performance} · LCP ${Math.round(kayit.metrik.lcp)} · TBT ${Math.round(kayit.metrik.tbt)} · CLS ${kayit.metrik.cls?.toFixed(3)} · SI ${Math.round(kayit.metrik.si)}`);
  } finally { await chrome.kill(); }
}
