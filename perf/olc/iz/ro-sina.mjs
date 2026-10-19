import puppeteer from "puppeteer-core";
const bekle = (ms) => new Promise((r) => setTimeout(r, ms));
const t = await puppeteer.launch({ browser: "firefox", executablePath: "/Applications/Firefox.app/Contents/MacOS/firefox", headless: false, acceptInsecureCerts: true, defaultViewport: null });
const s = await t.newPage(); await s.setViewport({ width: 800, height: 600, deviceScaleFactor: Number(process.argv[2] || 2) });
await s.goto("data:text/html,<div id=d style='width:300.5px;height:100px;background:red'></div>");
await s.evaluate(() => { window.__g = []; const ro = new ResizeObserver((es) => { for (const e of es) window.__g.push({ dpr: devicePixelRatio, css: e.contentBoxSize?.[0]?.inlineSize, dev: e.devicePixelContentBoxSize?.[0]?.inlineSize }); });
  try { ro.observe(document.getElementById("d"), { box: "device-pixel-content-box" }); window.__kip = "dpcb"; } catch (x) { window.__kip = "hata " + x; ro.observe(document.getElementById("d")); }
  const mq = () => { const m = matchMedia(`(resolution: ${devicePixelRatio}dppx)`); m.addEventListener("change", () => { window.__g.push({ mq: "değişti", dpr: devicePixelRatio }); mq(); }, { once: true }); }; mq(); });
await bekle(500);
for (const d of [1, 1.5, 3]) { await s.setViewport({ width: 800, height: 600, deviceScaleFactor: d }); await bekle(800); }
console.log(await s.evaluate(() => JSON.stringify({ kip: window.__kip, g: window.__g, ua: navigator.userAgent })));
await t.close();
