/** Portföy geçiş ölçümü — gerçek tıklama, sahte API (canlı gecikmeler). Kullanım:
 *  node portfoy-olcum.mjs <base-url> <etiket> [TEKRAR=10] ; ortam: CPU=4 (yavaşlatma), AG=yavas (Slow 4G benzeri), PW_DIR
 *  Zaman çizelgesi (tıklama = 0): vurgu (aria-current), h1 «Portföy», KPI değeri (iskelet değil), tablo satırı, tahmin kartı
 *  yerleşti, DSG kartı yerleşti, hepsi. Senaryolar: soğuk ilk açılış (boş bellek), Portföy→Tahminler→Portföy ×N (sıcak,
 *  <60 sn), Portföy→Santralim→Portföy ×N, bellek dolmuş dönüş (+61 sn Date kayması, bayat-önce yolu), istek sayısı ve
 *  tekrar isteği (sahte API günlüğü), konsol/istisna, heap, CLS. */
import fs from "node:fs";
import { createRequire } from "node:module";
const pw = createRequire((process.env.PW_DIR ?? process.cwd()) + "/")("playwright");
const [base, etiket, tekrarArg] = process.argv.slice(2); const TEKRAR = Number(tekrarArg ?? 10);
const API = "http://127.0.0.1:4807";
const JETON = "x." + Buffer.from('{"role":"admin"}').toString("base64url") + ".y";
const b = await pw.chromium.launch({ headless: true });
const ctx = await b.newContext({ viewport: { width: 1440, height: 900 }, locale: "tr-TR", timezoneId: "Europe/Istanbul" });
await ctx.addInitScript(() => { window.__kayma = 0; const G = Date; class S extends G { constructor(...a) { a.length === 0 ? super(G.now() + window.__kayma) : super(...a); } static now() { return G.now() + window.__kayma; } } window.Date = S; });
await ctx.addInitScript((j) => { localStorage.setItem("pvq_token", j); localStorage.setItem("pvq_tema", "koyu"); localStorage.setItem("pvq_plant", "a1"); }, JETON);
const p = await ctx.newPage(); const hatalar = [];
p.on("pageerror", (e) => hatalar.push("istisna: " + e.message.slice(0, 100)));
p.on("console", (m) => { if (m.type() === "error" && !/500|404/.test(m.text())) hatalar.push("konsol: " + m.text().slice(0, 100)); });
const cdp = await ctx.newCDPSession(p);
if (process.env.CPU) await cdp.send("Emulation.setCPUThrottlingRate", { rate: Number(process.env.CPU) });
if (process.env.AG === "yavas") { await cdp.send("Network.enable"); await cdp.send("Network.emulateNetworkConditions", { offline: false, latency: 150, downloadThroughput: 400 * 1024 / 8 * 10, uploadThroughput: 400 * 1024 / 8 }); }
await p.goto(base + "/", { waitUntil: "load" }); await p.waitForSelector(".nav-btn"); await p.waitForTimeout(2500);
const sifirla = () => fetch(API + "/_sifirla", { method: "POST" });
const gunluk = async () => (await (await fetch(API + "/_log")).json()).map((x) => x.yol);
const gecis = async (hedef) => p.evaluate(async (hedef) => {
  const t0 = performance.now(); const z = {}; const kayma = [];
  const po = new PerformanceObserver((l) => { for (const e of l.getEntries()) if (!e.hadRecentInput) kayma.push(e.value); }); po.observe({ type: "layout-shift", buffered: false });
  const btn = [...document.querySelectorAll(".nav-btn")].find((b) => b.textContent.trim() === hedef); btn.click();
  const ic = () => document.querySelector(".icerik");
  const kosullar = {
    vurgu: () => btn.getAttribute("aria-current") === "page",
    h1: () => ic()?.querySelector("h1")?.textContent === hedef || (hedef === "Portföy" && ic()?.querySelector("h1")?.textContent === "Portföy"),
    kpi: () => hedef !== "Portföy" ? true : !!ic()?.querySelector(".kpi") && !ic()?.querySelector(".iskelet") && /\d/.test(ic()?.querySelector(".kpi")?.textContent ?? ""),
    tablo: () => hedef !== "Portföy" ? true : !!ic()?.querySelector("table.santral tbody tr, table.veri tbody tr"),
    tahmin: () => hedef !== "Portföy" ? true : (() => { const k = [...ic()?.querySelectorAll(".kart") ?? []].find((k) => /günlük üretim tahmini/.test(k.textContent)); return !!k && !k.querySelector(".iskelet-alan") && !/güncelleniyor/.test(k.querySelector(".cip")?.textContent ?? ""); })(),
    dsg: () => hedef !== "Portföy" ? true : (() => { const k = [...ic()?.querySelectorAll(".kart") ?? []].find((k) => /DSG/.test(k.textContent)); return !!k && !k.querySelector(".iskelet-alan") && !/güncelleniyor/.test(k.querySelector(".cip")?.textContent ?? ""); })(),
    icerik: () => hedef === "Portföy" ? true : !!ic()?.querySelector(".kart, .kpi, .bos-durum, table") && !/Yükleniyor/.test(ic()?.textContent ?? ""),
  };
  const bitis = t0 + 12000;
  while (performance.now() < bitis && Object.keys(kosullar).some((k) => !(k in z))) {
    await new Promise((r) => requestAnimationFrame(r));
    for (const [k, f] of Object.entries(kosullar)) if (!(k in z) && f()) z[k] = Math.round(performance.now() - t0);
  }
  await new Promise((r) => setTimeout(r, 400)); po.disconnect();
  return { ...z, cls: Math.round(kayma.reduce((a, c) => a + c, 0) * 1000) / 1000 };
}, hedef);
const sonuc = { etiket, cpu: process.env.CPU ?? "1", ag: process.env.AG ?? "hizli", senaryolar: {} };
const kayit = (ad, r, istekler) => { (sonuc.senaryolar[ad] ??= []).push({ ...r, istekler }); };
const yaz = (ad, r, istekler) => console.log(`${ad.padEnd(34)} vurgu ${String(r.vurgu ?? "-").padStart(5)}  h1 ${String(r.h1 ?? "-").padStart(5)}  kpi ${String(r.kpi ?? "-").padStart(5)}  tablo ${String(r.tablo ?? "-").padStart(5)}  tahmin ${String(r.tahmin ?? "-").padStart(5)}  dsg ${String(r.dsg ?? "-").padStart(5)}  cls ${r.cls}  istek ${istekler.length}${istekler.length !== new Set(istekler).size ? " (TEKRAR!)" : ""}`);
// 1) soğuk: ilk Portföy açılışı (panel Santralim ile açıldı; Portföy belleği boş)
await sifirla(); let r = await gecis("Portföy"); let g = await gunluk(); kayit("soguk", r, g); yaz("1 soğuk ilk açılış", r, g);
// 2) Portföy → Tahminler → Portföy ×N (sıcak, bellek <60 sn)
for (let i = 0; i < TEKRAR; i++) { await gecis("Tahminler"); await p.waitForTimeout(250); await sifirla(); r = await gecis("Portföy"); g = await gunluk(); kayit("tahminler-donus", r, g); if (i < 2 || i === TEKRAR - 1) yaz(`2 Tahminler→Portföy #${i + 1}`, r, g); }
// 3) Portföy → Santralim → Portföy ×N
for (let i = 0; i < TEKRAR; i++) { await gecis("Santralim"); await p.waitForTimeout(250); await sifirla(); r = await gecis("Portföy"); g = await gunluk(); kayit("santralim-donus", r, g); if (i < 2 || i === TEKRAR - 1) yaz(`3 Santralim→Portföy #${i + 1}`, r, g); }
// 4) bellek dolmuş dönüş: +61 sn, Portföy→Tahminler→Portföy ×3
for (let i = 0; i < 3; i++) { await gecis("Tahminler"); await p.waitForTimeout(250); await p.evaluate(() => { window.__kayma += 61_000; }); await sifirla(); r = await gecis("Portföy"); g = await gunluk(); kayit("bellek-dolmus", r, g); yaz(`4 bellek dolmuş dönüş #${i + 1}`, r, g); }
// 5) hızlı ardışık: Portföy↔Tahminler 10 kez 120 ms arayla, sonra Portföy'ün yerleşmesi
await sifirla(); for (let i = 0; i < 10; i++) { await p.evaluate((h) => [...document.querySelectorAll(".nav-btn")].find((b) => b.textContent.trim() === h).click(), i % 2 ? "Portföy" : "Tahminler"); await p.waitForTimeout(120); }
r = await gecis("Portföy"); g = await gunluk(); kayit("hizli-ardisik", r, g); yaz("5 hızlı ardışık sonrası Portföy", r, g);
{ const say = {}; for (const y of g) say[y] = (say[y] ?? 0) + 1; console.log("   tekrar eden yollar:", JSON.stringify(Object.fromEntries(Object.entries(say).filter(([, n]) => n > 1)))); }
const heap = await cdp.send("Runtime.getHeapUsage").catch(() => null);
const med = (a) => { const s = [...a].sort((x, y) => x - y); return s.length ? s[Math.floor(s.length / 2)] : null; };
const oz = {}; for (const [ad, l] of Object.entries(sonuc.senaryolar)) oz[ad] = Object.fromEntries(["vurgu", "h1", "kpi", "tablo", "tahmin", "dsg", "icerik"].map((k) => [k, { medyan: med(l.map((x) => x[k]).filter((v) => v != null)), enKotu: Math.max(...l.map((x) => x[k] ?? -1)) }]).concat([["istek", { medyan: med(l.map((x) => x.istekler.length)) }], ["cls", { enKotu: Math.max(...l.map((x) => x.cls)) }]]));
sonuc.ozet = oz; sonuc.hatalar = hatalar; sonuc.heapMB = heap ? Math.round(heap.usedSize / 1048576) : null;
console.log("medyan/en kötü:", JSON.stringify(oz));
console.log("hata:", hatalar.length, hatalar.slice(0, 4), "heap MB:", sonuc.heapMB);
fs.writeFileSync(`${process.env.CIKTI ?? "."}/olcum-${etiket}.json`, JSON.stringify(sonuc, null, 2));
await b.close();
