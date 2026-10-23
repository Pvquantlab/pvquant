/** İki temada hesaplanmış stil denetimi (ham CDP; 22.10.2026 ikinci denetim): görünür metin düğümleri için
 *  aile/punto/ağırlık/renk/etkin zemin (yarı saydam katmanlar harmanlanır) → WCAG kontrast; düğme/girdi yükseklikleri;
 *  grafik jetonları. Kullanım: TEMA=acik|koyu node denetim.mjs <port> <base> <çıktı.json> [genişlik]  (örnek kip) */
import fs from "node:fs";
import http from "node:http";
const [port, base, cikti, wArg] = process.argv.slice(2);
const w = Number(wArg ?? 1440);
const PANEL = ["Portföy", "Santralim", "Veri yükleme", "Kalibrasyon", "Tahminler", "Doğruluk", "Aylık beklenti", "Raporlar", "Hakkında"];
const sekme = await new Promise((res, rej) => { http.get(`http://127.0.0.1:${port}/json/new?about:blank`, { method: "PUT" }, (r) => { let s = ""; r.on("data", (c) => (s += c)); r.on("end", () => res(JSON.parse(s))); }).on("error", rej); });
const ws = new WebSocket(sekme.webSocketDebuggerUrl);
await new Promise((r, j) => { ws.addEventListener("open", r, { once: true }); ws.addEventListener("error", j, { once: true }); });
let sira = 0; const bek = new Map();
ws.addEventListener("message", async (ev) => { const m = JSON.parse(typeof ev.data === "string" ? ev.data : Buffer.from(await ev.data.arrayBuffer()).toString()); if (m.id && bek.has(m.id)) { const { res, rej } = bek.get(m.id); bek.delete(m.id); m.error ? rej(new Error(m.error.message)) : res(m.result); } });
const cdp = (metot, p = {}) => new Promise((res, rej) => { const i = ++sira; bek.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method: metot, params: p })); });
const js = async (e) => { const r = await cdp("Runtime.evaluate", { expression: e, returnByValue: true, awaitPromise: true }); if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description ?? "hata"); return r.result.value; };
const uyut = (ms) => new Promise((r) => setTimeout(r, ms));
await cdp("Page.enable");
await cdp("Emulation.setDeviceMetricsOverride", { width: w, height: 900, deviceScaleFactor: 1, mobile: w < 768 });
await cdp("Page.navigate", { url: base + "/" }); await uyut(1500);
await js(`localStorage.setItem('pvq_token','ornek-kip'); localStorage.setItem('pvq_tema', ${JSON.stringify(process.env.TEMA ?? "koyu")}); true`);
await cdp("Page.navigate", { url: base + "/" }); await uyut(2500);

const DENETIM = `(() => {
  const ayr = (s) => { const m = s.match(/rgba?\\(([^)]+)\\)/); if (!m) return null; const p = m[1].split(",").map(Number); return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 }; };
  const lum = ({ r, g, b }) => { const f = (c) => { c /= 255; return c <= .03928 ? c / 12.92 : ((c + .055) / 1.055) ** 2.4; }; return .2126 * f(r) + .7152 * f(g) + .0722 * f(b); };
  const kar = (a, b) => { const la = lum(a), lb = lum(b); return (Math.max(la, lb) + .05) / (Math.min(la, lb) + .05); };
  const harman = (ust, alt) => ({ r: ust.a * ust.r + (1 - ust.a) * alt.r, g: ust.a * ust.g + (1 - ust.a) * alt.g, b: ust.a * ust.b + (1 - ust.a) * alt.b, a: 1 });
  const zemin = (e) => { let acc = null; for (let n = e; n; n = n.parentElement) { const bg = ayr(getComputedStyle(n).backgroundColor); if (bg && bg.a > 0) { acc = acc ? harman(acc, bg) : bg; if (acc.a >= 1 && bg.a >= 1) return acc; } } return acc ?? { r: 255, g: 255, b: 255, a: 1 }; };
  const out = { metin: [], dugme: [], girdi: [] };
  let n = 0;
  for (const e of document.querySelectorAll("body *")) {
    if (n++ > 8000) break;
    if (e.closest(".yan-ort, .palet-ort") || e.tagName === "SCRIPT" || e.tagName === "STYLE") continue;
    const cs = getComputedStyle(e);
    if (cs.display === "none" || cs.visibility === "hidden" || cs.opacity === "0") continue;
    const k = e.getBoundingClientRect(); if (k.width === 0 || k.height === 0) continue;
    if (e.matches("button, a[href], .dugme, .nav-btn")) out.dugme.push({ cls: (e.className + "").slice(0, 40), metin: (e.textContent || "").trim().slice(0, 30), h: Math.round(k.height), w: Math.round(k.width), fs: cs.fontSize });
    if (e.matches("input, select, textarea")) out.girdi.push({ cls: (e.className + "").slice(0, 40), h: Math.round(k.height), fs: cs.fontSize, ph: e.placeholder || "" });
    const metinVar = [...e.childNodes].some((c) => c.nodeType === 3 && c.textContent.trim());
    if (!metinVar) continue;
    const fg = ayr(cs.color), bg = zemin(e); if (!fg) continue;
    const fgE = fg.a < 1 ? harman(fg, bg) : fg;
    const fs = parseFloat(cs.fontSize), fw = parseInt(cs.fontWeight, 10);
    const buyuk = fs >= 24 || (fs >= 18.66 && fw >= 700);
    const kr = kar(fgE, bg);
    out.metin.push({ tag: e.tagName.toLowerCase(), cls: (e.className + "").slice(0, 40), metin: [...e.childNodes].filter((c) => c.nodeType === 3).map((c) => c.textContent.trim()).join(" ").slice(0, 40),
      aile: cs.fontFamily.split(",")[0].replace(/['"]/g, ""), fs, fw, renk: cs.color, zemin: "rgb(" + Math.round(bg.r) + "," + Math.round(bg.g) + "," + Math.round(bg.b) + ")", kontrast: Math.round(kr * 100) / 100, esik: buyuk ? 3 : 4.5 });
    if (e.matches("input") && e.placeholder) { const pc = ayr(getComputedStyle(e, "::placeholder").color); if (pc) out.metin.push({ tag: "placeholder", cls: (e.className + "").slice(0, 40), metin: e.placeholder.slice(0, 30), aile: cs.fontFamily.split(",")[0], fs, fw, renk: getComputedStyle(e, "::placeholder").color, zemin: "", kontrast: Math.round(kar(pc.a < 1 ? harman(pc, bg) : pc, bg) * 100) / 100, esik: 4.5 }); }
  }
  const kok = getComputedStyle(document.documentElement);
  out.grafik = {}; for (const j of ["--chart-surface", "--chart-axis-text", "--chart-grid", "--chart-muted", "--izgara", "--kenar", "--kart", "--zemin", "--yan", "--soluk", "--ikincil", "--metin", "--ch-dusuk", "--ch-cubuk", "--chart-limit", "--chart-now"]) out.grafik[j] = kok.getPropertyValue(j).trim();
  out.tema = document.documentElement.dataset.tema;
  return out;
})()`;

const rapor = {};
for (const s of PANEL) {
  await js(`[...document.querySelectorAll(".nav-btn")].find((b) => b.textContent.trim() === ${JSON.stringify(s)}).click(); true`);
  await uyut(1100);
  rapor[s] = await js(DENETIM);
  const m = rapor[s].metin;
  const kucuk = m.filter((x) => x.fs < 12).length, dusuk = m.filter((x) => x.kontrast < x.esik).length;
  const kd = rapor[s].dugme.filter((x) => x.h < 32).length, kg = rapor[s].girdi.filter((x) => x.h < 32).length;
  process.stdout.write(`${rapor[s].tema} ${s}: metin ${m.length} · <12px ${kucuk} · kontrast düşük ${dusuk} · düğme<32 ${kd}/${rapor[s].dugme.length} · girdi<32 ${kg}/${rapor[s].girdi.length}\n`);
}
fs.writeFileSync(cikti, JSON.stringify(rapor, null, 1));
ws.close(); process.exit(0);
