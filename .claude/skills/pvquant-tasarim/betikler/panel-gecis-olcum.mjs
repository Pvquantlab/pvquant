/** Panel sayfa geçişi ölçümü — GERÇEK TIKLAMA, sahte panel API'si (uç başına gecikme), Playwright/CDP (24.10 açık tema turu).
 *  node panel-gecis-olcum.mjs <base-url> <etiket> [TEKRAR=3]
 *  ortam: TEMA=acik|koyu|oto (varsayılan acik) · CPU=4 (yavaşlatma) · AG=yavas (400 kb/s, 150 ms) · PW_DIR (playwright kökü) · API (sahte API)
 *  Zaman çizelgesi (tıklama = 0 ms): vurgu (aria-current) · h1 · ilk içerik (rakamlı KPI ya da gerçek kart gövdesi; iskelet değil)
 *  · tam (iskelet/yer tutucu/«Yükleniyor»/«hesaplanıyor» kalmadı) · tuval sayısı. Senaryolar: soğuk ilk ziyaret (sırayla 9 sayfa),
 *  sıcak tekrar (<60 sn, araya başka sayfa), bellek dolmuş dönüş (+61 sn Date kayması), geri dönüş (A→B→A), hızlı ardışık 3×9;
 *  istek sayıları sahte API günlüğünden; CLS, heap, konsol/istisna. Sayı uydurulmaz: her değer tarayıcıdan okunur. */
import fs from "node:fs";
import { createRequire } from "node:module";
const pw = createRequire((process.env.PW_DIR ?? process.cwd()) + "/")("playwright");
const [base, etiket, tekrarArg] = process.argv.slice(2);
if (!base || !etiket) { console.error("kullanım: node panel-gecis-olcum.mjs <base-url> <etiket> [TEKRAR]"); process.exit(2); }
const TEKRAR = Number(tekrarArg ?? 3);
const TEMA = process.env.TEMA ?? "acik";
const API = process.env.API ?? "http://127.0.0.1:4807";
const SAYFALAR = ["Portföy", "Santralim", "Veri yükleme", "Kalibrasyon", "Tahminler", "Doğruluk", "Aylık beklenti", "Raporlar", "Hakkında"];
const JETON = "x." + Buffer.from('{"role":"admin"}').toString("base64url") + ".y";
const b = await pw.chromium.launch({ headless: true, executablePath: process.env.CHROME ?? undefined });
const ctx = await b.newContext({ viewport: { width: 1440, height: 900 }, locale: "tr-TR", timezoneId: "Europe/Istanbul", reducedMotion: "no-preference" });
await ctx.addInitScript(() => { window.__kayma = 0; const G = Date; class S extends G { constructor(...a) { a.length === 0 ? super(G.now() + window.__kayma) : super(...a); } static now() { return G.now() + window.__kayma; } } window.Date = S; });
await ctx.addInitScript(({ j, tema }) => { localStorage.setItem("pvq_token", j); if (tema === "oto") localStorage.removeItem("pvq_tema"); else localStorage.setItem("pvq_tema", tema); localStorage.setItem("pvq_plant", "a1"); }, { j: JETON, tema: TEMA });
const p = await ctx.newPage(); const hatalar = [];
p.on("pageerror", (e) => hatalar.push("istisna: " + e.message.slice(0, 120)));
p.on("console", (m) => { if (m.type() === "error" && !/404/.test(m.text())) hatalar.push("konsol: " + m.text().slice(0, 120)); });
const cdp = await ctx.newCDPSession(p);
if (process.env.CPU) await cdp.send("Emulation.setCPUThrottlingRate", { rate: Number(process.env.CPU) });
if (process.env.AG === "yavas") { await cdp.send("Network.enable"); await cdp.send("Network.emulateNetworkConditions", { offline: false, latency: 150, downloadThroughput: 400 * 1024 / 8 * 10, uploadThroughput: 400 * 1024 / 8 }); }
await p.goto(base + "/", { waitUntil: "load" }); await p.waitForSelector(".nav-btn"); await p.waitForTimeout(3000);
const sifirla = () => fetch(API + "/_sifirla", { method: "POST" });
const gunluk = async () => (await (await fetch(API + "/_log")).json()).map((x) => x.yol);
/** tek geçiş: tıkla → zaman çizelgesi (ms) */
const gecis = async (hedef) => p.evaluate(async (hedef) => {
  const t0 = performance.now(); const z = {}; const kayma = [];
  const po = new PerformanceObserver((l) => { for (const e of l.getEntries()) if (!e.hadRecentInput) kayma.push(e.value); }); po.observe({ type: "layout-shift", buffered: false });
  const btn = [...document.querySelectorAll(".nav-btn")].find((b) => b.textContent.trim() === hedef);
  const ic = () => document.querySelector(".icerik");
  const h1Once = ic()?.querySelector("h1")?.textContent ?? "";
  btn.click();
  const bekliyorMu = (k) => !!k.querySelector(".iskelet, .iskelet-alan") || /Yükleniyor|hesaplanıyor|Hesaplanıyor…|Karşılaştırılıyor…|güncelleniyor/.test(k.textContent ?? "");
  const kosullar = {
    vurgu: () => btn.getAttribute("aria-current") === "page",
    h1: () => { const h = ic()?.querySelector("h1")?.textContent ?? ""; return !!h && h !== h1Once; },
    // ilk içerik / tam: YENİ sayfanın başlığı görünmeden sayılmaz — startTransition eski sayfayı yeni sayfa hazır olana
    // dek ekranda tutar; eski sayfanın kartları «içerik» sanılırdı (24.10 ilk ölçümde 3 ms'lik sahte değerler)
    ilkIcerik: () => { if (!("h1" in z)) return false; const k = ic(); if (!k || k.querySelector(".iskelet")) return false;
      const kpi = [...k.querySelectorAll(".kpi")].some((x) => /\d/.test(x.textContent ?? "") && !x.querySelector(".iskelet-alan"));
      const kart = [...k.querySelectorAll(".kart")].some((x) => (x.textContent ?? "").length > 80 && !bekliyorMu(x));
      return kpi || kart || !!k.querySelector(".bos-durum, table tbody tr"); },
    tam: () => { if (!("h1" in z)) return false; const k = ic(); return !!k && !!(k.querySelector(".kart, .kpi, .bos-durum, table")) && !bekliyorMu(k); },
  };
  const bitis = t0 + 12000;
  while (performance.now() < bitis && Object.keys(z).length < Object.keys(kosullar).length) {
    await new Promise((r) => requestAnimationFrame(r));
    for (const [ad, f] of Object.entries(kosullar)) if (!(ad in z) && f()) z[ad] = Math.round(performance.now() - t0);
  }
  await new Promise((r) => setTimeout(r, 300));
  po.disconnect();
  return { ...z, tuval: ic()?.querySelectorAll("canvas").length ?? 0, cls: +kayma.reduce((a, v) => a + v, 0).toFixed(4) };
}, hedef);
const heap = async () => { const r = await cdp.send("Runtime.evaluate", { expression: "performance.memory ? Math.round(performance.memory.usedJSHeapSize/1048576) : null", returnByValue: true }); return r.result.value; };
const medyan = (a) => { const b = a.filter((x) => typeof x === "number").sort((x, y) => x - y); return b.length ? b[Math.floor(b.length / 2)] : null; };
const yaz = (s) => process.stdout.write(s + "\n");
const satir = (ad, o) => `${ad.padEnd(16)} vurgu ${String(o.vurgu ?? "—").padStart(4)} · h1 ${String(o.h1 ?? "—").padStart(4)} · ilk içerik ${String(o.ilkIcerik ?? "—").padStart(5)} · tam ${String(o.tam ?? "—").padStart(5)} ms · tuval ${o.tuval} · CLS ${o.cls}${o.istek != null ? ` · ${o.istek} istek` : ""}`;
const sonuc = { etiket, ayar: { TEMA, CPU: process.env.CPU ?? "1", AG: process.env.AG ?? "hizli", TEKRAR, base, API }, soguk: {}, sicak: {}, dolmus: {}, geriDonus: [], hizli: [], hatalar: [] };
// 1) soğuk ilk ziyaret — açılış sayfası Santralim; sırayla
yaz(`[${etiket}] TEMA=${TEMA} CPU=${sonuc.ayar.CPU} AG=${sonuc.ayar.AG}`);
yaz("— soğuk ilk ziyaret —");
for (const s of SAYFALAR) {
  if (s === "Santralim") continue;
  await sifirla(); const o = await gecis(s); o.istek = (await gunluk()).length; sonuc.soguk[s] = o; yaz(satir(s, o));
}
// Santralim'i de soğuk say: açılıştan sonra ilk dönüş (parça inmiş; veri 60 sn bellekte olabilir) — bellek dolmuş senaryoda ayrıca ölçülür
// 2) sıcak tekrar (<60 sn): her sayfaya TEKRAR kez, araya başka sayfa
yaz("— sıcak tekrar (<60 sn), medyan —");
for (const s of SAYFALAR) {
  const olc = [];
  for (let i = 0; i < TEKRAR; i++) { const ara = SAYFALAR[(SAYFALAR.indexOf(s) + 1 + i) % SAYFALAR.length]; await gecis(ara); await sifirla(); const o = await gecis(s); o.istek = (await gunluk()).length; olc.push(o); }
  const m = { vurgu: medyan(olc.map((o) => o.vurgu)), h1: medyan(olc.map((o) => o.h1)), ilkIcerik: medyan(olc.map((o) => o.ilkIcerik)), tam: medyan(olc.map((o) => o.tam)), tuval: olc[0].tuval, cls: medyan(olc.map((o) => o.cls)), istek: medyan(olc.map((o) => o.istek)), olcumler: olc };
  sonuc.sicak[s] = m; yaz(satir(s, m));
}
// 3) bellek dolmuş dönüş (+61 sn): her sayfaya bir kez, araya başka sayfa, Date kaydırılarak
yaz("— bellek dolmuş dönüş (+61 sn) —");
for (const s of SAYFALAR) {
  const ara = SAYFALAR[(SAYFALAR.indexOf(s) + 1) % SAYFALAR.length]; await gecis(ara);
  await p.evaluate(() => { window.__kayma += 61_000; }); await sifirla();
  const o = await gecis(s); o.istek = (await gunluk()).length; sonuc.dolmus[s] = o; yaz(satir(s, o));
}
// 4) geri dönüş: A → B → A (sıcak)
yaz("— geri dönüş (A → B → A) —");
for (const [a, bb] of [["Doğruluk", "Tahminler"], ["Kalibrasyon", "Santralim"], ["Aylık beklenti", "Raporlar"], ["Portföy", "Hakkında"]]) {
  await gecis(a); await gecis(bb); const o = await gecis(a); sonuc.geriDonus.push({ akis: `${a} → ${bb} → ${a}`, ...o }); yaz(satir(`${a}↩`, o));
}
// 5) hızlı ardışık 3×9 + heap
yaz("— hızlı ardışık 3×9 —");
for (let t = 0; t < 3; t++) { const t0 = Date.now(); for (const s of SAYFALAR) await gecis(s); sonuc.hizli.push({ sureMs: Date.now() - t0, heapMB: await heap() }); }
yaz(sonuc.hizli.map((t) => `${t.sureMs} ms / heap ${t.heapMB} MB`).join(" · "));
sonuc.hatalar = hatalar; yaz(`konsol/istisna: ${hatalar.length}${hatalar.length ? "\n  " + [...new Set(hatalar)].slice(0, 6).join("\n  ") : ""}`);
const dosya = `panel-gecis-${etiket}-${TEMA}-cpu${sonuc.ayar.CPU}.json`; fs.writeFileSync(dosya, JSON.stringify(sonuc, null, 2)); yaz(`yazıldı ${dosya}`);
await b.close();
