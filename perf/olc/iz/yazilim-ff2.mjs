// yazilim-ff2.mjs — Playwright Firefox başsız (yazılımla birleştirme): aynı bağlamda iki açılış. 1.: tuval kurulur, ilk saniye sınaması
// söker mi; sonra boşta kare aralığı. 2.: kayıt sayesinde tuval hiç kurulmuyor mu. node olc/iz/yazilim-ff2.mjs --hedef sonra7
import { firefox } from "playwright";
import { HEDEFLER, GORUNUMLER, baglamAyar } from "../ortak.mjs";
const arg = (ad, vars) => { const i = process.argv.indexOf("--" + ad); return i > 0 ? process.argv[i + 1] : vars; };
const hedef = arg("hedef", "sonra7"), g = GORUNUMLER[arg("gorunum", "1440x900")];
const t = await firefox.launch({ headless: true });
const b = await t.newContext(baglamAyar("firefox", g));
for (const acilis of [1, 2]) {
  const s = await b.newPage();
  await s.goto(HEDEFLER[hedef].yok + "/", { waitUntil: "load" });
  const r = await s.evaluate(async () => {
    const v = document.querySelector("video.vt-hero__video"); const b0 = performance.now();
    while (performance.now() - b0 < 30000 && !(v && !v.paused && v.readyState >= 3 && v.currentTime > 6.8)) await new Promise((r) => setTimeout(r, 100));
    const c = document.querySelector("canvas.vt-hero__keskin");
    const durum = () => (c ? (c.classList.contains("is-hazir") ? "etkin" : "gizli") : "yok") + "/" + (v.classList.contains("is-gl") ? "süzgeç-yok" : "css");
    const iz = [[Math.round(performance.now() - b0), durum()]];
    for (let i = 0; i < 8; i++) { await new Promise((r) => setTimeout(r, 500)); iz.push([Math.round(performance.now() - b0), durum()]); }
    const d = []; let o = null; await new Promise((res) => { const f = (t) => { if (o !== null) d.push(t - o); o = t; if (d.length < 90) requestAnimationFrame(f); else res(); }; requestAnimationFrame(f); });
    d.sort((a, z) => a - z);
    return { iz: iz.map(([t, x]) => `${t}:${x}`).join(" "), ortanca: +d[45].toFixed(1), p95: +d[85].toFixed(1), kayit: localStorage.getItem("pvq_keskin_yazilim") ? "var" : "yok" };
  });
  console.log(`${hedef} açılış ${acilis}: ${JSON.stringify(r)}`);
  await s.close();
}
await t.close();
