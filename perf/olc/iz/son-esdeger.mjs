// son-esdeger.mjs — derlenmiş sayfada (keskinGL.ts) Firefox tuvali ↔ aynı sayfada CSS süzgecine dönüş: duraklatılmış karede piksel kıyası
// ve kenar enerjisi. Ayrıca önceki derlemenin (CSS süzgeci) aynı karesiyle kıyas. node olc/iz/son-esdeger.mjs --hedef sonra4 --onceki sonra3
import fs from "node:fs";
import path from "node:path";
import { PNG } from "pngjs";
import puppeteer from "puppeteer-core";
import { KOK, GORUNUMLER, HEDEFLER } from "../ortak.mjs";
const arg = (ad, vars) => { const i = process.argv.indexOf("--" + ad); return i > 0 ? process.argv[i + 1] : vars; };
const hedef = arg("hedef", "sonra4"), onceki = arg("onceki", "sonra3"), zaman = Number(arg("zaman", "10"));
const cikti = path.join(KOK, "analiz/webgl-son"); fs.mkdirSync(cikti, { recursive: true });
const bekle = (ms) => new Promise((r) => setTimeout(r, ms));
const kiyas = (a, b, k = 6) => { let e = 0, t = 0, n = 0, f2 = 0, f4 = 0, f8 = 0;
  for (let y = k; y < a.height - k; y++) for (let x = k; x < a.width - k; x++) { const i = (y * a.width + x) * 4;
    const d = Math.max(Math.abs(a.data[i] - b.data[i]), Math.abs(a.data[i + 1] - b.data[i + 1]), Math.abs(a.data[i + 2] - b.data[i + 2]));
    n++; t += d; e = Math.max(e, d); if (d > 2) f2++; if (d > 4) f4++; if (d > 8) f8++; }
  return `en büyük ${e} · ort ${(t / n).toFixed(2)} · >2 %${(100 * f2 / n).toFixed(1)} · >4 %${(100 * f4 / n).toFixed(1)} · >8 %${(100 * f8 / n).toFixed(1)}`; };
const kenar = (p) => { const { width: w, height: h, data: d } = p; let t = 0, n = 0; const L = (x, y) => { const i = (y * w + x) * 4; return 0.2126 * d[i] + 0.7152 * d[i + 1] + 0.0722 * d[i + 2]; };
  for (let y = 6; y < h - 6; y++) for (let x = 6; x < w - 6; x++) { const gx = L(x + 1, y - 1) + 2 * L(x + 1, y) + L(x + 1, y + 1) - L(x - 1, y - 1) - 2 * L(x - 1, y) - L(x - 1, y + 1);
    const gy = L(x - 1, y + 1) + 2 * L(x, y + 1) + L(x + 1, y + 1) - L(x - 1, y - 1) - 2 * L(x, y - 1) - L(x + 1, y - 1); t += Math.hypot(gx, gy) / 8; n++; } return (t / n).toFixed(3); };
for (const gAd of arg("gorunum", "1440x900,390x844").split(",")) {
  const g = GORUNUMLER[gAd] ?? (([w, h, d]) => ({ width: +w, height: +h, dpr: +d }))(gAd.split(/[x@]/)); const resim = {};
  for (const h of [hedef, onceki]) {
    const t = await puppeteer.launch({ browser: "firefox", executablePath: "/Applications/Firefox.app/Contents/MacOS/firefox", headless: false, acceptInsecureCerts: true, defaultViewport: null });
    const s = await t.newPage(); await s.setViewport({ width: g.width, height: g.height, deviceScaleFactor: g.dpr });
    await s.goto(HEDEFLER[h].yok + "/", { waitUntil: "load" }); await bekle(1500);
    const durum = await s.evaluate(async (zaman) => { const v = document.querySelector("video.vt-hero__video"); const b = performance.now();
      while (performance.now() - b < 40000 && !(v && !v.paused && v.readyState >= 3 && v.currentTime > 6.8)) await new Promise((r) => setTimeout(r, 100));
      await new Promise((r) => setTimeout(r, 1500));
      v.pause(); v.currentTime = zaman; await new Promise((r) => { v.addEventListener("seeked", r, { once: true }); setTimeout(r, 5000); });
      const e = document.createElement("style"); e.textContent = "img.vt-hero__poster, .vt-ust, .vt-hero .vt-kap, .vt-hero__ortu, .vt-bolumcubuk { visibility: hidden !important; } .vt-hero::after, .vt-hero::before, .vt-hero__sahne::after { display: none !important; }";
      document.head.appendChild(e);
      const c = document.querySelector("canvas.vt-hero__keskin");
      return { tuval: c ? c.classList.contains("is-hazir") : null, videoSuzgec: getComputedStyle(v).filter, t: v.currentTime }; }, zaman);
    const kutu = await s.evaluate(() => { const r = document.querySelector("video.vt-hero__video").getBoundingClientRect(); return { x: Math.max(0, r.left), y: Math.max(0, r.top), width: Math.min(innerWidth - 15, r.width), height: Math.min(innerHeight - Math.max(0, r.top), r.height) }; });
    await bekle(1200);
    resim[h] = PNG.sync.read(Buffer.from(await s.screenshot({ clip: kutu, type: "png" })));
    if (h === hedef) {   // aynı sayfada CSS süzgecine dön: tuval gizlenir, video süzgeci geri gelir
      await s.evaluate(() => { document.querySelector("canvas.vt-hero__keskin")?.classList.remove("is-hazir"); document.querySelector("video.vt-hero__video").classList.remove("is-gl"); });
      await bekle(1200);
      resim[hedef + "-css"] = PNG.sync.read(Buffer.from(await s.screenshot({ clip: kutu, type: "png" })));
    }
    console.log(`${gAd} ${h} ${JSON.stringify(durum)} kutu ${kutu.width}×${kutu.height}`);
    await t.close();
  }
  for (const [ad, p] of Object.entries(resim)) fs.writeFileSync(path.join(cikti, `${gAd}-${ad}.png`), PNG.sync.write(p));
  console.log(`   ${hedef} tuval ↔ aynı sayfa CSS süzgeci: ${kiyas(resim[hedef], resim[hedef + "-css"])}`);
  console.log(`   ${hedef} tuval ↔ ${onceki} (CSS süzgeci): ${kiyas(resim[hedef], resim[onceki])}`);
  console.log(`   ${hedef}-css ↔ ${onceki}: ${kiyas(resim[hedef + "-css"], resim[onceki])}`);
  console.log(`   kenar enerjisi: ${hedef} tuval ${kenar(resim[hedef])} · ${hedef} CSS ${kenar(resim[hedef + "-css"])} · ${onceki} ${kenar(resim[onceki])}`);
}
