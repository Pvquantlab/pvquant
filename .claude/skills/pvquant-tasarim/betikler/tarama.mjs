/** PVQuant görsel QA taraması (ham CDP; bağımlılıksız — Node 20+).
 *  Kullanım: node tarama.mjs <cdp-port> <url> <çıktı-dizini> [genişlikler]
 *  Örn:      node tarama.mjs 9333 http://localhost:5173/ qa/taramalar/dal1 320,375,768,1081,1440
 *  Headless Chrome: "…/Google Chrome" --headless=new --remote-debugging-port=9333 --user-data-dir=<tmp>
 *  Her genişlikte: taşma, çift id, a11y özeti (isimsiz etkileşimli, alt'sız img, atlanan
 *  heading, <44px dokunma hedefi), jeton-dışı font-size raporu; 1440+375'te kare.
 *  Çıkış kodu: ihlal varsa 1 (rapor <çıktı>/tarama.json). */
import fs from "node:fs";
import http from "node:http";

const [port, url, dizin, genislikArg] = process.argv.slice(2);
if (!port || !url || !dizin) { console.error("kullanım: node tarama.mjs <port> <url> <dizin> [genişlikler]"); process.exit(2); }
const GENISLIKLER = (genislikArg ?? "320,375,768,1081,1440").split(",").map(Number);
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

const DENETIM = `(() => {
  const S = { ihlaller: [] };
  const de = document.documentElement;
  S.tasma = de.scrollWidth - de.clientWidth;
  if (S.tasma > 0) S.ihlaller.push("yatay taşma: " + S.tasma + "px");
  const idler = [...document.querySelectorAll("[id]")].map((e) => e.id);
  const cift = idler.filter((v, i) => idler.indexOf(v) !== i);
  if (cift.length) S.ihlaller.push("çift id: " + [...new Set(cift)].join(","));
  for (const img of document.querySelectorAll("img"))
    if (!img.hasAttribute("alt")) S.ihlaller.push("alt'sız img: " + (img.src || "").slice(-40));
  for (const e of document.querySelectorAll("button, a[href], [role=button]")) {
    const ad = (e.getAttribute("aria-label") || e.textContent || "").trim();
    if (!ad) S.ihlaller.push("isimsiz etkileşimli: <" + e.tagName.toLowerCase() + "> " + (e.className + "").slice(0, 40));
    const k = e.getBoundingClientRect();
    // WCAG 2.5.8 satır içi istisnası: metin akışındaki bağlantı (p/li/td/dd/figcaption
    // içindeki <a>) hedef boyutu kuralından muaftır — rubrik turu v2.399 düzeltmesi.
    const satirIci = getComputedStyle(e).display === "inline" ||
      (e.tagName === "A" && e.closest("p, li, td, dd, figcaption"));
    // ::before inset:0 absolute = «kartın tamamı tıklanabilir» hilesi (vt-panelde
    // kalıbı) — gerçek hedef kart; eleman kutusu ölçüte girmez.
    const ob = getComputedStyle(e, "::before");
    const genisHedef = ob.content !== "none" && ob.position === "absolute" &&
      ob.top === "0px" && ob.bottom === "0px" && ob.left === "0px" && ob.right === "0px";
    if (innerWidth < 768 && k.width > 0 && (k.width < 44 || k.height < 44) && !satirIci && !genisHedef)
      S.kucukHedef = (S.kucukHedef ?? 0) + 1;
  }
  let onceki = 0;
  for (const h of document.querySelectorAll("h1,h2,h3,h4,h5,h6")) {
    const sev = +h.tagName[1];
    if (onceki && sev > onceki + 1) S.ihlaller.push("atlanan heading: h" + onceki + "→h" + sev);
    onceki = sev;
  }
  // jeton-dışı font-size raporu (bilgi; tek başına ihlal değil)
  const boyutlar = {};
  for (const e of document.querySelectorAll("body *")) {
    if (!e.checkVisibility || !e.checkVisibility()) continue;
    if (!e.textContent || !e.textContent.trim()) continue;
    const fs = getComputedStyle(e).fontSize;
    boyutlar[fs] = (boyutlar[fs] ?? 0) + 1;
  }
  S.fontBoyutlari = Object.fromEntries(Object.entries(boyutlar).sort((a, b) => b[1] - a[1]));
  return S;
})()`;

const rapor = { url, zaman: new Date().toISOString(), genislikler: {} };
let ihlalVar = false;
for (const g of GENISLIKLER) {
  await cdp("Emulation.setDeviceMetricsOverride", { width: g, height: 900, deviceScaleFactor: 1, mobile: g < 768 });
  // telefon genişliği = dokunmatik aygıt: pointer:coarse medya kuralları (ör. 44px hedef
  // tabanı) gerçekte uygulanır; emülasyonsuz ölçüm yanlış pozitif verir (Mühür 1, v2.408).
  await cdp("Emulation.setTouchEmulationEnabled", { enabled: g < 768, maxTouchPoints: 5 }).catch(() => {});
  await cdp("Page.navigate", { url });
  await uyut(2500);
  const s = await js(DENETIM);
  rapor.genislikler[g] = s;
  if (s.ihlaller.length) ihlalVar = true;
  console.log(`${g}px: ${s.ihlaller.length ? "İHLAL — " + s.ihlaller.join(" · ") : "temiz"}` + (s.kucukHedef ? ` · küçük hedef ×${s.kucukHedef}` : ""));
  if (g === 1440 || g === 375) {
    await cdp("Emulation.setDeviceMetricsOverride", { width: g, height: 1000, deviceScaleFactor: 2, mobile: g < 768 });
    await uyut(400);
    const k = await cdp("Page.captureScreenshot", { format: "png", clip: { x: 0, y: 0, width: g, height: 1000, scale: g > 768 ? 0.62 : 1 } });
    fs.writeFileSync(`${dizin}/kare-${g}.png`, Buffer.from(k.data, "base64"));
  }
}
fs.writeFileSync(`${dizin}/tarama.json`, JSON.stringify(rapor, null, 2));
await cdp("Page.close").catch(() => {});
ws.close();
console.log(ihlalVar ? "SONUÇ: ihlal var — tarama.json" : "SONUÇ: temiz");
process.exit(ihlalVar ? 1 : 0);
