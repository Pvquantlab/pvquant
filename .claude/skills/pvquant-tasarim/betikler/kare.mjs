/** Panel + vitrin tam sayfa kareleri (ham CDP, bağımlılıksız; 22–23.10.2026 panel tasarım turları).
 *  Kullanım: [TEMA=acik|koyu] node kare.mjs <cdp-port> <base-url> <çıktı-dizini> [genişlikler] [sayfalar|-]
 *  Headless Chrome: "…/Google Chrome" --headless=new --remote-debugging-port=9333 --user-data-dir=<tmp> --hide-scrollbars
 *  Örnek kip (web/.env.local kenara): sahte jetonla "/" paneli açar; "/?vitrin" vitrin, "/yontem", "giris" giriş ekranı.
 *  Her karede yatay taşma ve görünen yazı tipi özeti rapor.json'a yazılır. */
import fs from "node:fs";
import http from "node:http";

const [port, base, dizin, genislikArg, sayfaArg] = process.argv.slice(2);
if (!port || !base || !dizin) { console.error("kullanım: node kare.mjs <port> <base> <dizin> [genişlikler] [sayfalar]"); process.exit(2); }
const GENISLIKLER = (genislikArg ?? "375,768,1024,1440,1920").split(",").map(Number);
const PANEL = ["Portföy", "Santralim", "Veri yükleme", "Kalibrasyon", "Tahminler", "Doğruluk", "Aylık beklenti", "Raporlar", "Hakkında"];
const SAYFALAR = sayfaArg && sayfaArg !== "-" ? sayfaArg.split(",") : [...PANEL, "vitrin", "yontem"];
fs.mkdirSync(dizin, { recursive: true });

const sekme = await new Promise((res, rej) => {
  http.get(`http://127.0.0.1:${port}/json/new?about:blank`, { method: "PUT" }, (r) => {
    let s = ""; r.on("data", (c) => (s += c)); r.on("end", () => res(JSON.parse(s)));
  }).on("error", rej);
});
const ws = new WebSocket(sekme.webSocketDebuggerUrl);
await new Promise((r, j) => { ws.addEventListener("open", r, { once: true }); ws.addEventListener("error", j, { once: true }); });
let sira = 0; const bekleyen = new Map();
ws.addEventListener("message", async (ev) => {
  const d = typeof ev.data === "string" ? ev.data : Buffer.from(await ev.data.arrayBuffer()).toString();
  const m = JSON.parse(d);
  if (m.id && bekleyen.has(m.id)) { const { res, rej } = bekleyen.get(m.id); bekleyen.delete(m.id); m.error ? rej(new Error(m.error.message)) : res(m.result); }
});
const cdp = (metot, p = {}) => new Promise((res, rej) => { const i = ++sira; bekleyen.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method: metot, params: p })); });
const js = async (ifade) => {
  const r = await cdp("Runtime.evaluate", { expression: ifade, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description ?? "sayfa hatası");
  return r.result.value;
};
const uyut = (ms) => new Promise((r) => setTimeout(r, ms));
await cdp("Page.enable");
await cdp("Emulation.setEmulatedMedia", { features: [{ name: "prefers-reduced-motion", value: "reduce" }] });

const OZET = `(() => {
  const de = document.documentElement;
  const aileler = {}; let n = 0;
  for (const e of document.querySelectorAll("body *")) {
    if (n++ > 6000) break;
    if (!e.textContent || !e.textContent.trim()) continue;
    if (e.children.length && [...e.childNodes].every((c) => c.nodeType !== 3 || !c.textContent.trim())) continue;
    const cs = getComputedStyle(e);
    if (cs.display === "none" || cs.visibility === "hidden") continue;
    const k = cs.fontFamily.split(",")[0].replace(/['"]/g, "") + " " + cs.fontWeight + " " + cs.fontSize;
    aileler[k] = (aileler[k] ?? 0) + 1;
  }
  return { tasma: de.scrollWidth - de.clientWidth, yukseklik: de.scrollHeight, aileler, tema: de.dataset.tema };
})()`;

async function bekleHazir(secici, sure = 8000) {
  const t0 = Date.now();
  while (Date.now() - t0 < sure) {
    if (await js(`!!document.querySelector(${JSON.stringify(secici)})`)) return true;
    await uyut(100);
  }
  return false;
}
async function kare(ad, w) {
  await js("document.fonts.ready.then(() => true)");
  await uyut(250);
  const { contentSize } = await cdp("Page.getLayoutMetrics");
  const h = Math.min(Math.ceil(contentSize.height), 12000);
  await cdp("Emulation.setDeviceMetricsOverride", { width: w, height: h, deviceScaleFactor: 1, mobile: w < 768 });
  await uyut(150);
  const r = await cdp("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
  fs.writeFileSync(`${dizin}/${ad}-${w}.png`, Buffer.from(r.data, "base64"));
  await cdp("Emulation.setDeviceMetricsOverride", { width: w, height: 900, deviceScaleFactor: 1, mobile: w < 768 });
}

const rapor = {};
for (const w of GENISLIKLER) {
  await cdp("Emulation.setDeviceMetricsOverride", { width: w, height: 900, deviceScaleFactor: 1, mobile: w < 768 });
  const panelde = SAYFALAR.filter((s) => PANEL.includes(s));
  if (panelde.length) {
    await cdp("Page.navigate", { url: base + "/" });
    await bekleHazir("#root *", 8000);
    await js("localStorage.setItem('pvq_token', 'ornek-kip'); true");
    if (process.env.TEMA) await js(`localStorage.setItem('pvq_tema', ${JSON.stringify(process.env.TEMA)}); true`);
    else await js("localStorage.removeItem('pvq_tema'); true");
    await cdp("Page.navigate", { url: base + "/" });
    if (!(await bekleHazir(".nav-btn"))) throw new Error("panel açılmadı (.nav-btn yok) — örnek kip mi?");
    for (const s of panelde) {
      await js(`[...document.querySelectorAll(".nav-btn")].find((b) => b.textContent.trim() === ${JSON.stringify(s)}).click(); true`);
      await uyut(900);
      await js("window.scrollTo(0,0); true");
      const o = await js(OZET);
      rapor[`${s}@${w}`] = o;
      await kare(s.replace(/\s/g, "_").toLowerCase(), w);
      process.stdout.write(`${o.tema} ${s}@${w}: taşma ${o.tasma}px · ${o.yukseklik}px\n`);
    }
  }
  if (SAYFALAR.includes("giris")) {
    await cdp("Page.navigate", { url: base + "/" });
    await bekleHazir("#root *", 8000);
    await js("localStorage.removeItem('pvq_token'); true");
    await cdp("Page.navigate", { url: base + "/" });
    await bekleHazir(".vt", 8000);
    await uyut(800);
    await js(`[...document.querySelectorAll("button, a")].find((b) => b.textContent.trim() === "Panele giriş").click(); true`);
    await bekleHazir(".giris", 8000);
    await uyut(800);
    const o = await js(OZET);
    rapor[`giris@${w}`] = o;
    await kare("giris", w);
    process.stdout.write(`giris@${w}: taşma ${o.tasma}px · ${o.yukseklik}px\n`);
  }
  for (const [ad, yol] of [["vitrin", "/?vitrin"], ["yontem", "/yontem"]]) {
    if (!SAYFALAR.includes(ad)) continue;
    await cdp("Page.navigate", { url: base + yol });
    await bekleHazir(".vt", 8000);
    await uyut(1500);
    await js("window.scrollTo(0,0); true");
    const o = await js(OZET);
    rapor[`${ad}@${w}`] = o;
    await kare(ad, w);
    process.stdout.write(`${ad}@${w}: taşma ${o.tasma}px · ${o.yukseklik}px\n`);
  }
}
fs.writeFileSync(`${dizin}/rapor.json`, JSON.stringify(rapor, null, 1));
const tasanlar = Object.entries(rapor).filter(([, o]) => o.tasma > 0);
console.log(tasanlar.length ? "TAŞMA: " + tasanlar.map(([k, o]) => `${k} ${o.tasma}px`).join(", ") : "taşma yok");
ws.close();
process.exit(0);
