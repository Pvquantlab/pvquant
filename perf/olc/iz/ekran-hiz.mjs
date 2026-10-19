// ekran-hiz.mjs — DENEY: stok Firefox (pencereli) hero videosunun ekranda saniyede kaç FARKLI görüntü verdiği: küçük bir bölgenin
// (64×64 CSS px) ekran görüntüsü olabildiğince sık alınır; ardışık görüntüler karşılaştırılır. Video karesi sayısıyla (rVFC) kıyaslanır.
// node olc/iz/ekran-hiz.mjs --hedef sonra3,sonra4 [--sure 6000]
import puppeteer from "puppeteer-core";
import { HEDEFLER, GORUNUMLER } from "../ortak.mjs";
const arg = (ad, vars) => { const i = process.argv.indexOf("--" + ad); return i > 0 ? process.argv[i + 1] : vars; };
const g = GORUNUMLER[arg("gorunum", "1440x900")], sure = Number(arg("sure", "6000"));
const bekle = (ms) => new Promise((r) => setTimeout(r, ms));
for (const hedef of arg("hedef", "sonra3,sonra4").split(",")) {
  const t = await puppeteer.launch({ browser: "firefox", executablePath: "/Applications/Firefox.app/Contents/MacOS/firefox", headless: false, acceptInsecureCerts: true, defaultViewport: null });
  const s = await t.newPage(); await s.setViewport({ width: g.width, height: g.height, deviceScaleFactor: g.dpr });
  await s.goto(HEDEFLER[hedef].yok + "/", { waitUntil: "load" });
  await s.evaluate(async () => { const v = document.querySelector("video.vt-hero__video"); const b = performance.now();
    while (performance.now() - b < 40000 && !(v && !v.paused && v.readyState >= 3 && v.currentTime > 6.8)) await new Promise((r) => setTimeout(r, 100)); });
  await bekle(12000);                                                   // durağan oynatma (açılış artığı geçsin)
  for (const [ad, kutu] of [["gökyüzü", { x: 700, y: 120, width: 64, height: 64 }], ["paneller", { x: 900, y: 640, width: 64, height: 64 }]]) {
    const v0 = await s.evaluate(() => { window.__rv = 0; const v = document.querySelector("video.vt-hero__video"); const f = () => { window.__rv++; v.requestVideoFrameCallback(f); }; v.requestVideoFrameCallback(f); return 0; });
    let onceki = null, farkli = 0, adet = 0; const b0 = Date.now();
    while (Date.now() - b0 < sure) { const buf = await s.screenshot({ clip: kutu, type: "png", encoding: "base64" }); adet++; if (onceki !== null && buf !== onceki) farkli++; onceki = buf; }
    const rv = await s.evaluate(() => window.__rv);
    console.log(`${hedef.padEnd(7)} ${ad.padEnd(9)} ${((Date.now() - b0) / 1000).toFixed(1)} sn · görüntü ${adet} (${(adet / (sure / 1000)).toFixed(1)}/sn) · öncekinden farklı ${farkli} (${(farkli / (sure / 1000)).toFixed(1)}/sn) · video karesi (rVFC) ${rv} (${(rv / (sure / 1000)).toFixed(1)}/sn)`);
  }
  await t.close();
}
