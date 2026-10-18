// video-zaman.mjs — stok Firefox (pencereli): video oynamaya başladıktan sonra 30 sn boyunca 5 sn'lik pencerelerde video kare
// düşmesi, sunulan kare (rVFC), rAF p95 ve süreç ağacı CPU'su. Değişkenler (aynı «sonra» derlemesi): yeni (#vt-keskin-wr, olduğu gibi)
// · ozgun (CSS ile özgün #vt-keskin'e zorlanır) · filtresiz. node olc/video-zaman.mjs [--hedef sonra] [--kosu 2] [--gorunum 1440x900]
import { execFileSync } from "node:child_process";
import puppeteer from "puppeteer-core";
import fs from "node:fs";
import path from "node:path";
import { KOK, HEDEFLER, GORUNUMLER } from "./ortak.mjs";
const arg = (ad, vars) => { const i = process.argv.indexOf("--" + ad); return i > 0 ? process.argv[i + 1] : vars; };
const hedef = arg("hedef", "sonra"), kosu = Number(arg("kosu", "2")), g = GORUNUMLER[arg("gorunum", "1440x900")];
const degiskenler = arg("degisken", "yeni,ozgun,filtresiz").split(",");
const CSS = { yeni: "", ozgun: ".vt .vt-hero--wr .vt-hero__video, .vt .vt-hero--wr .vt-hero__poster { filter: url(#vt-keskin) !important; }",
  filtresiz: ".vt-hero video, .vt-hero img { filter: none !important; }" };
const cikti = path.join(KOK, arg("cikti", "after/ab"), "video-zaman.jsonl");
const bekle = (ms) => new Promise((r) => setTimeout(r, ms));
function cpu(kok) {
  const s = execFileSync("ps", ["-A", "-o", "pid=,ppid=,time="], { encoding: "utf8" }).trim().split("\n").map((l) => l.trim().split(/\s+/)).map(([p, pp, t]) => ({ p: +p, pp: +pp, t: t.split(":").map(Number).reduce((a, x) => a * 60 + x, 0) }));
  const c = new Map(); for (const x of s) { if (!c.has(x.pp)) c.set(x.pp, []); c.get(x.pp).push(x); }
  let top = 0; const y = [kok]; while (y.length) { const k = y.pop(); for (const x of c.get(k) || []) { top += x.t; y.push(x.p); } } return top;
}
for (let k = 1; k <= kosu; k++) for (const d of (k % 2 ? degiskenler : [...degiskenler].reverse())) {
  const t = await puppeteer.launch({ browser: "firefox", executablePath: "/Applications/Firefox.app/Contents/MacOS/firefox", headless: false, acceptInsecureCerts: true, defaultViewport: null });
  const s = await t.newPage(); await s.setViewport({ width: g.width, height: g.height, deviceScaleFactor: g.dpr });
  if (CSS[d]) await s.evaluateOnNewDocument((c) => { document.addEventListener("DOMContentLoaded", () => { const e = document.createElement("style"); e.textContent = c; document.head.appendChild(e); }); }, CSS[d]);
  await s.goto(HEDEFLER[hedef].yok + "/", { waitUntil: "load" });
  await s.evaluate(async () => { const v = document.querySelector("video.vt-hero__video"); const b = performance.now(); while (performance.now() - b < 30000 && !(v && !v.paused && v.readyState >= 3)) await new Promise((r) => setTimeout(r, 50)); });
  const pid = t.process().pid; const pencereler = [];
  for (let p = 0; p < 6; p++) {
    const c0 = cpu(pid);
    const r = await s.evaluate(async () => {
      const v = document.querySelector("video.vt-hero__video"); const q0 = v.getVideoPlaybackQuality(); let rv = 0; const b = performance.now();
      const f = () => { rv++; if (performance.now() - b < 5000) v.requestVideoFrameCallback(f); }; v.requestVideoFrameCallback(f);
      const dd = []; let o = null; await new Promise((res) => { const g = (tm) => { if (o !== null) dd.push(tm - o); o = tm; if (performance.now() - b < 5000) requestAnimationFrame(g); else res(); }; requestAnimationFrame(g); });
      const q1 = v.getVideoPlaybackQuality(); dd.sort((a, z) => a - z);
      return { dusen: q1.droppedVideoFrames - q0.droppedVideoFrames, toplam: q1.totalVideoFrames - q0.totalVideoFrames, rvfc: rv, p95: dd[Math.floor(dd.length * 0.95)], t: v.currentTime };
    });
    r.cpu = +((cpu(pid) - c0) / 5).toFixed(2); pencereler.push(r);
  }
  const satir = { hedef, degisken: d, kosu: k, gorunum: `${g.width}x${g.height}`, surum: await t.version(), zaman: new Date().toISOString(), pencereler };
  fs.appendFileSync(cikti, JSON.stringify(satir) + "\n");
  console.log(`${d.padEnd(9)} #${k} düşen/toplam: ${pencereler.map((x) => `${x.dusen}/${x.toplam}`).join(" ")} · rVFC: ${pencereler.map((x) => x.rvfc).join(" ")} · cpu: ${pencereler.map((x) => x.cpu).join(" ")}`);
  await t.close();
}
