// canli-dogrula.mjs — dağıtım sonrası canlı doğrulama (pvquant.com): (1) index.html içeriği (gömülü CSS, <body>'de font ön yüklemesi,
// font bekleme ve modulepreload betikleri, sürüm izi), (2) Chromium/Firefox/WebKit'te «/», «/yontem» ve giriş ekranı: FCP, LCP, konsol
// hatası, başarısız istek, (3) stok Firefox (pencereli, donanım): video oynarken WebGL tuvali etkin, boşta kare aralığı.
// node olc/iz/canli-dogrula.mjs [--adres https://pvquant.com]
import { chromium, firefox, webkit } from "playwright";
import puppeteer from "puppeteer-core";
const arg = (ad, vars) => { const i = process.argv.indexOf("--" + ad); return i > 0 ? process.argv[i + 1] : vars; };
const ADRES = arg("adres", "https://pvquant.com");


// (1) HTML
const yanit = await fetch(ADRES + "/", { headers: { "accept-encoding": "br" } });
const html = await yanit.text();
const denetim = {
  durum: yanit.status,
  kodlama: yanit.headers.get("content-encoding"),
  gomuluCss: /<style>@font-face\{font-family:Inter Variable/.test(html) && !/<link rel="stylesheet"/.test(html),
  fontOnYuklemeBodyde: html.indexOf('<link rel="preload" as="font"') > html.indexOf("<body>"),
  fontBekle: html.includes("vt-font-bekle"),
  modulePreload: html.includes('l.rel="modulepreload"'),
  modulBetik: /<script type="module" crossorigin src="\/assets\/index-[\w-]+\.js"><\/script>/.exec(html)?.[0].match(/index-[\w-]+\.js/)?.[0],
  boyKB: Math.round(html.length / 1024),
};
console.log("HTML:", JSON.stringify(denetim));

// (2) üç motor
for (const [ad, motor] of [["chromium", chromium], ["firefox", firefox], ["webkit", webkit]]) {
  const t = await motor.launch();
  for (const yol of ["/", "/yontem", "giriş"]) {   // giriş ayrı yol değil: «/» → Menü → çekmecede «Panele giriş» (ekran.mjs ile aynı)
    const b = await t.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, ...(ad === "firefox" ? {} : { isMobile: true }), hasTouch: true });
    const s = await b.newPage(); const hata = [], basarisiz = [];
    s.on("console", (m) => { if (m.type() === "error") hata.push(m.text().slice(0, 120)); });
    s.on("pageerror", (e) => hata.push("pageerror: " + String(e).slice(0, 120)));
    s.on("requestfailed", (r) => basarisiz.push(`${r.url().split("/").pop().slice(0, 40)} ${r.failure()?.errorText}`));
    s.on("response", (r) => { if (r.status() >= 400) basarisiz.push(`${r.status()} ${r.url().split("/").pop().slice(0, 40)}`); });
    await s.addInitScript(() => { window.__lcp = 0; try { new PerformanceObserver((l) => { for (const e of l.getEntries()) window.__lcp = e.startTime; }).observe({ type: "largest-contentful-paint", buffered: true }); } catch { /* yok */ } });
    try {
      const giris = yol === "giriş";
      await s.goto(ADRES + (giris ? "/" : yol), { waitUntil: "load", timeout: 60000 }); await s.waitForTimeout(giris ? 1200 : 3000);
      if (giris) {
        await s.locator("button.vt-menu-dugme").click(); await s.locator("#vt-cekmece button", { hasText: "Panele giriş" }).click();
        await s.waitForFunction(() => !document.querySelector(".vt-ust") && document.querySelector(".giris-form input"), null, { timeout: 15000 });
        await s.waitForTimeout(1500);
      }
      const r = await s.evaluate(() => ({ fcp: Math.round(performance.getEntriesByName("first-contentful-paint")[0]?.startTime ?? -1), lcp: Math.round(window.__lcp),
        baslik: document.querySelector("h1")?.textContent?.trim().slice(0, 40) ?? "—", form: !!document.querySelector(".giris-form input") }));
      console.log(`${ad.padEnd(8)} ${yol.padEnd(8)} FCP ${r.fcp} LCP ${r.lcp} · h1 «${r.baslik}»${giris ? ` · giriş formu ${r.form}` : ""} · konsol hatası ${hata.length}${hata.length ? " " + JSON.stringify(hata) : ""} · başarısız ${basarisiz.length}${basarisiz.length ? " " + JSON.stringify(basarisiz) : ""}`);
    } catch (e) { console.log(`${ad} ${yol} GEZİNME HATASI ${String(e).slice(0, 160)}`); }
    await b.close();
  }
  await t.close();
}

// (3) stok Firefox, pencereli (donanım birleştirme): tuval etkin mi
const t = await puppeteer.launch({ browser: "firefox", executablePath: "/Applications/Firefox.app/Contents/MacOS/firefox", headless: false, defaultViewport: null });
const s = await t.newPage(); await s.setViewport({ width: 1440, height: 900, deviceScaleFactor: 2 });
const ffHata = []; s.on("console", (m) => { if (m.type() === "error") ffHata.push(m.text().slice(0, 120)); });
await s.goto(ADRES + "/", { waitUntil: "load" });
const ff = await s.evaluate(async () => {
  const v = document.querySelector("video.vt-hero__video"); const b0 = performance.now();
  while (performance.now() - b0 < 40000 && !(v && !v.paused && v.readyState >= 3 && v.currentTime > 6.8)) await new Promise((r) => setTimeout(r, 100));
  await new Promise((r) => setTimeout(r, 3000));
  const d = []; let o = null; await new Promise((res) => { const f = (t) => { if (o !== null) d.push(t - o); o = t; if (d.length < 90) requestAnimationFrame(f); else res(); }; requestAnimationFrame(f); });
  d.sort((a, z) => a - z); const c = document.querySelector("canvas.vt-hero__keskin");
  return { oynuyor: !!v && !v.paused, tuval: c ? c.className : "yok", video: v?.className, tampon: c ? `${c.width}×${c.height}` : "—", ortanca: +d[45].toFixed(1), p95: +d[85].toFixed(1), kayit: localStorage.getItem("pvq_keskin_yazilim") ? "var" : "yok" };
});
console.log("stok Firefox (pencereli) «/»:", JSON.stringify({ ...ff, konsolHatasi: ffHata.length, hatalar: ffHata }));
await t.close();
