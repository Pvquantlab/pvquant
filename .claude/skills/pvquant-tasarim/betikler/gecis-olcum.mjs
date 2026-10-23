/** Panel sayfa GEÇİŞ ölçümü (ham CDP, bağımlılıksız; 24.10.2026 performans turu).
 *  Kullanım: [TEKRAR=3] [CPU=1] [AG=hizli|yavas] node gecis-olcum.mjs <cdp-port> <base-url> <çıktı.json>
 *  Örnek kip (API'siz üretim derlemesi) — sahte jetonla panel açılır; her sayfa için nav tıklaması → sayfa h1'i
 *  (ilk görsel tepki) → "hazır" (ilk .kart ya da .kpi ya da .bos-durum; «Yükleniyor» yok) süreleri; kaç uzun görev
 *  (>50 ms), düzen kayması (CLS katkısı), kaç kaynak isteği ve ağır parça indirildiği. İlk ziyaret (soğuk parça) ve
 *  tekrar ziyaretler ayrı; medyan + dağılım raporlanır. Sayı uydurulmaz: her değer PerformanceObserver/MutationObserver. */
import fs from "node:fs";
import http from "node:http";

const [port, base, cikti] = process.argv.slice(2);
if (!port || !base || !cikti) { console.error("kullanım: node gecis-olcum.mjs <port> <base> <çıktı.json>"); process.exit(2); }
const TEKRAR = Number(process.env.TEKRAR ?? 3);
const CPU = Number(process.env.CPU ?? 1);
const AG = process.env.AG ?? "hizli";
const SAYFALAR = ["Portföy", "Santralim", "Veri yükleme", "Kalibrasyon", "Tahminler", "Doğruluk", "Aylık beklenti", "Raporlar", "Hakkında"];
const AKISLAR = [["Portföy", "Santralim", "Veri yükleme"], ["Veri yükleme", "Kalibrasyon", "Tahminler"], ["Tahminler", "Doğruluk"],
  ["Doğruluk", "Aylık beklenti"], ["Aylık beklenti", "Raporlar"], ["Raporlar", "Hakkında"], ["Hakkında", "Portföy"]];

const sekme = await new Promise((res, rej) => { http.get(`http://127.0.0.1:${port}/json/new?about:blank`, { method: "PUT" }, (r) => { let s = ""; r.on("data", (c) => (s += c)); r.on("end", () => res(JSON.parse(s))); }).on("error", rej); });
const ws = new WebSocket(sekme.webSocketDebuggerUrl);
await new Promise((r, j) => { ws.addEventListener("open", r, { once: true }); ws.addEventListener("error", j, { once: true }); });
let sira = 0; const bek = new Map();
ws.addEventListener("message", async (ev) => { const m = JSON.parse(typeof ev.data === "string" ? ev.data : Buffer.from(await ev.data.arrayBuffer()).toString()); if (m.id && bek.has(m.id)) { const { res, rej } = bek.get(m.id); bek.delete(m.id); m.error ? rej(new Error(m.error.message)) : res(m.result); } });
const cdp = (metot, p = {}) => new Promise((res, rej) => { const i = ++sira; bek.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method: metot, params: p })); });
const js = async (e) => { const r = await cdp("Runtime.evaluate", { expression: e, returnByValue: true, awaitPromise: true }); if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description ?? "hata"); return r.result.value; };
const uyut = (ms) => new Promise((r) => setTimeout(r, ms));
await cdp("Page.enable"); await cdp("Network.enable"); await cdp("Runtime.enable"); await cdp("Log.enable");
// konsol hataları ve yakalanmamış istisnalar (ikinci bağımsız tur için)
const hatalar = [];
ws.addEventListener("message", async (ev) => { const m = JSON.parse(typeof ev.data === "string" ? ev.data : Buffer.from(await ev.data.arrayBuffer()).toString());
  if (m.method === "Runtime.exceptionThrown") hatalar.push("istisna: " + (m.params.exceptionDetails.exception?.description ?? m.params.exceptionDetails.text).slice(0, 120));
  if (m.method === "Log.entryAdded" && m.params.entry.level === "error") hatalar.push("konsol: " + m.params.entry.text.slice(0, 120));
  if (m.method === "Runtime.consoleAPICalled" && m.params.type === "error") hatalar.push("console.error: " + (m.params.args[0]?.value ?? "").toString().slice(0, 120)); });
const GEN = Number(process.env.GENISLIK ?? 1440); await cdp("Emulation.setDeviceMetricsOverride", { width: GEN, height: GEN < 768 ? 812 : 900, deviceScaleFactor: 1, mobile: GEN < 768 });
if (CPU > 1) await cdp("Emulation.setCPUThrottlingRate", { rate: CPU });
if (AG === "yavas") await cdp("Network.emulateNetworkConditions", { offline: false, latency: 150, downloadThroughput: 1.6e6 / 8, uploadThroughput: 750e3 / 8 });

// gözlemciler (sayfa yaşam döngüsü boyunca)
const KUR = `(() => {
  window.__olc = { uzun: [], cls: [], kaynak: [] };
  new PerformanceObserver((l) => { for (const e of l.getEntries()) window.__olc.uzun.push([e.startTime, e.duration]); }).observe({ type: "longtask", buffered: true });
  new PerformanceObserver((l) => { for (const e of l.getEntries()) if (!e.hadRecentInput) window.__olc.cls.push([e.startTime, e.value]); }).observe({ type: "layout-shift", buffered: true });
  new PerformanceObserver((l) => { for (const e of l.getEntries()) window.__olc.kaynak.push([e.startTime, e.name.split("/").pop(), Math.round(e.transferSize || 0)]); }).observe({ type: "resource", buffered: true });
  true; })()`;

await cdp("Page.navigate", { url: base + "/" }); await uyut(1500);
await js("localStorage.setItem('pvq_token','ornek-kip'); localStorage.setItem('pvq_tema','koyu'); true");
await cdp("Page.navigate", { url: base + "/" }); await uyut(2500);
await js(KUR);

/** tek geçiş: nav tıkla → h1 metni değişene dek (ilk tepki) → hazır işareti (kart/kpi/boş durum, «Yükleniyor» yok) */
async function gecis(hedef) {
  // zaten açık sayfaya «geçiş» ölçülmez (h1 değişmez → 8 sn zaman aşımı yanlış ölçüm olurdu)
  const acik = await js(`[...document.querySelectorAll('.nav-btn')].find((b) => b.getAttribute('aria-current') === 'page')?.textContent.trim() ?? ''`);
  if (acik === hedef) return { ilkTepki: 0, hazir: 0, uzunGorev: 0, uzunToplam: 0, cls: 0, istek: 0, indirilenKB: 0, parcalar: [], ayniSayfa: true };
  const r = await js(`(async () => {
    const t0 = performance.now();
    const h1once = document.querySelector('.icerik h1')?.textContent ?? '';
    const uzunOnce = window.__olc.uzun.length, clsOnce = window.__olc.cls.length, kayOnce = window.__olc.kaynak.length;
    [...document.querySelectorAll('.nav-btn')].find((b) => b.textContent.trim() === ${JSON.stringify(hedef)}).click();
    let ilkTepki = null, hazir = null;
    const bitis = t0 + 8000;
    while (performance.now() < bitis) {
      await new Promise((r) => requestAnimationFrame(r));
      const h1 = document.querySelector('.icerik h1')?.textContent ?? '';
      const ic = document.querySelector('.icerik');
      const yukleniyor = /Yükleniyor/.test(ic?.textContent ?? '');
      if (ilkTepki === null && h1 && h1 !== h1once) ilkTepki = performance.now() - t0;
      if (hazir === null && ilkTepki !== null && !yukleniyor && ic && (ic.querySelector('.kart, .kpi, .bos-durum, table') || ic.textContent.length > 200)) { hazir = performance.now() - t0; break; }
      if (hazir === null && ilkTepki === null && h1 === h1once && !yukleniyor && ic && ic.querySelector('.kart, .kpi')) { /* aynı başlık, içerik değişti */ }
    }
    await new Promise((r) => setTimeout(r, 400));   // geç gelen uzun görev / kayma için pay
    const uzun = window.__olc.uzun.slice(uzunOnce).map(([s, d]) => Math.round(d));
    const cls = window.__olc.cls.slice(clsOnce).reduce((a, [, v]) => a + v, 0);
    const kaynak = window.__olc.kaynak.slice(kayOnce);
    return { ilkTepki: ilkTepki == null ? null : Math.round(ilkTepki), hazir: hazir == null ? null : Math.round(hazir),
             uzunGorev: uzun.length, uzunToplam: uzun.reduce((a, b) => a + b, 0), cls: +cls.toFixed(4),
             istek: kaynak.length, indirilenKB: Math.round(kaynak.reduce((a, [, , b]) => a + b, 0) / 1024), parcalar: kaynak.map((k) => k[1]).filter((n) => /\\.js$/.test(n)) };
  })()`);
  return r;
}

const sonuc = { ayar: { TEKRAR, CPU, AG, base }, ilkZiyaret: {}, tekrar: {}, akislar: [] };
const medyan = (a) => { const b = [...a].sort((x, y) => x - y); return b.length ? b[Math.floor(b.length / 2)] : null; };
// 1) ilk ziyaret (soğuk parça): sayfalar sırayla
let onceki = "Santralim";
for (const s of SAYFALAR) {
  if (s === onceki) { continue; }
  sonuc.ilkZiyaret[s] = await gecis(s); onceki = s;
  process.stdout.write(`ilk  ${s.padEnd(16)} tepki ${String(sonuc.ilkZiyaret[s].ilkTepki).padStart(4)} ms · hazır ${String(sonuc.ilkZiyaret[s].hazir).padStart(4)} ms · uzun ${sonuc.ilkZiyaret[s].uzunGorev} (${sonuc.ilkZiyaret[s].uzunToplam} ms) · CLS ${sonuc.ilkZiyaret[s].cls} · ${sonuc.ilkZiyaret[s].istek} istek ${sonuc.ilkZiyaret[s].indirilenKB} KB\n`);
}
// 2) tekrar ziyaretler: her sayfaya TEKRAR kez, araya başka sayfa girerek
for (const s of SAYFALAR) {
  const olc = [];
  for (let i = 0; i < TEKRAR; i++) {
    const ara = SAYFALAR[(SAYFALAR.indexOf(s) + 1 + i) % SAYFALAR.length];
    await gecis(ara);
    olc.push(await gecis(s));
  }
  sonuc.tekrar[s] = { tepkiMedyan: medyan(olc.map((o) => o.ilkTepki)), hazirMedyan: medyan(olc.map((o) => o.hazir)),
    hazirMin: Math.min(...olc.map((o) => o.hazir ?? 9999)), hazirMax: Math.max(...olc.map((o) => o.hazir ?? 0)),
    uzunGorev: medyan(olc.map((o) => o.uzunGorev)), cls: medyan(olc.map((o) => o.cls)), istek: medyan(olc.map((o) => o.istek)), olcumler: olc };
  const t = sonuc.tekrar[s];
  process.stdout.write(`tekr ${s.padEnd(16)} tepki ${String(t.tepkiMedyan).padStart(4)} ms · hazır ${String(t.hazirMedyan).padStart(4)} ms (${t.hazirMin}–${t.hazirMax}) · uzun ${t.uzunGorev} · CLS ${t.cls} · ${t.istek} istek\n`);
}
// 3) akışlar (kullanıcı brief'i): ardışık geçişler, toplam süre
for (const akis of AKISLAR) {
  await gecis(akis[0]);
  const adimlar = [];
  for (const s of akis.slice(1)) adimlar.push({ s, ...(await gecis(s)) });
  sonuc.akislar.push({ akis: akis.join(" → "), adimlar });
  process.stdout.write(`akış ${akis.join(" → ").padEnd(40)} ${adimlar.map((a) => `${a.s}:${a.hazir}ms`).join("  ")}\n`);
}
// 4) hızlı ardışık geçiş: 3 tur × 9 sayfa; tur başına heap (bellek sızıntısı kabaca: tur tur büyüyor mu?)
const heap = async () => { const r = await cdp("Runtime.evaluate", { expression: "performance.memory ? Math.round(performance.memory.usedJSHeapSize/1048576) : null", returnByValue: true }); return r.result.value; };
sonuc.hizliTur = [];
for (let t = 0; t < 3; t++) { const t0 = Date.now(); for (const s of SAYFALAR) await gecis(s); sonuc.hizliTur.push({ sureMs: Date.now() - t0, heapMB: await heap() }); }
process.stdout.write(`hızlı ardışık 3×9: ${sonuc.hizliTur.map((t) => `${t.sureMs} ms / heap ${t.heapMB} MB`).join(" · ")}\n`);
sonuc.heapMB = await heap();
sonuc.hatalar = hatalar;
process.stdout.write(`konsol/istisna: ${hatalar.length}${hatalar.length ? "\n  " + hatalar.slice(0, 5).join("\n  ") : ""}\n`);
fs.writeFileSync(cikti, JSON.stringify(sonuc, null, 2));
process.stdout.write(`heap ${sonuc.heapMB} MB · yazıldı ${cikti}\n`);
process.exit(0);
