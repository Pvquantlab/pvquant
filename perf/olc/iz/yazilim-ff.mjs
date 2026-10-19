// yazilim-ff.mjs — Playwright Firefox (başsız; yazılımla birleştirme): tuval etkin mi, WebGL çizici, boşta rAF aralığı (video oynarken)
// node olc/iz/yazilim-ff.mjs --hedef final,sonra --gorunum 1440x900
import { firefox } from "playwright";
import { HEDEFLER, GORUNUMLER, baglamAyar } from "../ortak.mjs";
const arg = (ad, vars) => { const i = process.argv.indexOf("--" + ad); return i > 0 ? process.argv[i + 1] : vars; };
const g = GORUNUMLER[arg("gorunum", "1440x900")], basli = process.argv.includes("--basli");
for (const hedef of arg("hedef", "final,sonra").split(",")) {
  const t = await firefox.launch({ headless: !basli });
  const b = await t.newContext(baglamAyar("firefox", g)); const s = await b.newPage();
  await s.goto(HEDEFLER[hedef].yok + "/", { waitUntil: "load" });
  const r = await s.evaluate(async () => {
    const v = document.querySelector("video.vt-hero__video"); const b0 = performance.now();
    while (performance.now() - b0 < 30000 && !(v && !v.paused && v.readyState >= 3 && v.currentTime > 6.8)) await new Promise((r) => setTimeout(r, 100));
    await new Promise((r) => setTimeout(r, 2000));
    const d = []; let o = null; await new Promise((res) => { const f = (t) => { if (o !== null) d.push(t - o); o = t; if (d.length < 90) requestAnimationFrame(f); else res(); }; requestAnimationFrame(f); });
    d.sort((a, z) => a - z);
    let cizici = "?"; try { const c = document.createElement("canvas").getContext("webgl"); const x = c && c.getExtension("WEBGL_debug_renderer_info"); cizici = c ? (x ? c.getParameter(x.UNMASKED_RENDERER_WEBGL) : c.getParameter(c.RENDERER)) : "webgl yok"; } catch (e) { cizici = "hata " + e; }
    let caveat = "?"; try { caveat = document.createElement("canvas").getContext("webgl", { failIfMajorPerformanceCaveat: true }) ? "geçti" : "reddedildi"; } catch (e) { caveat = "hata"; }
    const c = document.querySelector("canvas.vt-hero__keskin");
    return { tuval: c ? (c.classList.contains("is-hazir") ? "etkin" : "gizli") : "yok", ortanca: +d[45].toFixed(1), p95: +d[85].toFixed(1), cizici, caveat, oynuyor: !v.paused };
  });
  console.log(`${hedef} ${basli ? "başlı" : "başsız"} ${t.version()} ${JSON.stringify(r)}`);
  await t.close();
}
