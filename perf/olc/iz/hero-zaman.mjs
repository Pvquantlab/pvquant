// hero-zaman.mjs — tek açılışta hero zaman çizelgesi: LCP adayları, poster yükleme/çözme, heroHazır, levha src'leri, video durumu,
// hero paragrafının kutusu (yedek yüz ↔ web fontu). node olc/iz/hero-zaman.mjs --motor webkit --gorunum 1440x900 --hedef fable5-once --ag yok
import { HEDEFLER, GORUNUMLER, motorAc, baglamAyar, OLCUM_BETIGI } from "../ortak.mjs";
const arg = (ad, vars) => { const i = process.argv.indexOf("--" + ad); return i > 0 ? process.argv[i + 1] : vars; };
const motor = arg("motor", "webkit"), g = GORUNUMLER[arg("gorunum", "1440x900")], hedef = arg("hedef", "fable5-once"), ag = arg("ag", "yok");
const t = await motorAc(motor, hedef); const c = await t.newContext(baglamAyar(motor, g, process.argv.includes("--azalt") ? { reducedMotion: "reduce" } : {})); await c.addInitScript(OLCUM_BETIGI);
await c.addInitScript(`(() => { window.__iz = []; const b = () => performance.now();
  const kay = (ad, ek) => window.__iz.push([Math.round(b()), ad, ek || ""]);
  document.addEventListener("DOMContentLoaded", () => kay("DCL")); addEventListener("load", () => kay("load"));
  if (document.fonts) { document.fonts.addEventListener("loadingdone", () => kay("fonts.loadingdone", [...document.fonts].filter(f=>f.status==="loaded").map(f=>f.family+"/"+f.weight).join(","))); }
  const bak = () => { const p = document.querySelector("img.vt-hero__poster"); const v = document.querySelector("video.vt-hero__video");
    const par = document.querySelector("p.vt-hero__giris"); const h1 = document.querySelector("h1"); const lev = [...document.querySelectorAll("img.vt-levha__img, .vt-levha img, .vt-is__levha img")];
    const r = par ? par.getBoundingClientRect() : null; const rh = h1 ? h1.getBoundingClientRect() : null;
    kay("durum", JSON.stringify({ poster: p ? (p.complete ? "tam" : "bekliyor") + " " + p.naturalWidth + " " + (p.className.includes("is-gecti") ? "geçti" : "") : "yok",
      video: v ? v.readyState + " t=" + v.currentTime.toFixed(1) + (v.paused ? " dur" : " oyn") + " pre=" + v.preload + " " + (v.classList.contains("is-gl") ? "gl" : "") : "yok",
      levha: lev.length + "/" + lev.filter((i) => i.getAttribute("src")).length, par: r ? Math.round(r.width) + "x" + Math.round(r.height) : null, h1: rh ? Math.round(rh.width) + "x" + Math.round(rh.height) : null,
      font: par ? getComputedStyle(par).fontFamily.slice(0, 30) : null, root: document.documentElement.className })); };
  for (const ms of [100, 300, 600, 1000, 1500, 2000, 2500, 3000, 4000, 5000, 6000, 8000]) setTimeout(bak, ms);
})();`);
const p = await c.newPage();
p.on("console", (m) => { if (m.type() === "error") console.log("KONSOL", m.text().slice(0, 150)); });
await p.goto(HEDEFLER[hedef][ag] + "/", { waitUntil: "load" }); await p.waitForTimeout(8500);
const r = await p.evaluate(() => ({ iz: window.__iz, lcp: (window.__olc?.lcp || []).map((e) => Math.round(e.t) + "ms " + e.boy + "px² " + e.el), res: performance.getEntriesByType("resource").map((e) => Math.round(e.startTime) + "→" + Math.round(e.responseEnd) + " " + e.transferSize + " " + e.name.split("/").pop().slice(0, 40)) }));
console.log(`== ${motor} ${arg("gorunum", "1440x900")} ${ag}`); console.log("LCP:", r.lcp.join(" | ")); for (const x of r.iz) console.log(String(x[0]).padStart(5), x[1], x[2]); console.log("kaynaklar:"); for (const x of r.res) console.log("  " + x);
await t.close();
