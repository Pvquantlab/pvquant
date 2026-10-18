// ortak.mjs — ölçüm düzeneğinin ortak tanımları (hedefler, görünümler, motor açılışı, sayfa içi ölçüm betiği).
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium, firefox, webkit } from "playwright";

export const KOK = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

/** Ölçülen hedefler. once = main (d6ab50a, canlıyla bayt bayt aynı derleme), sonra = perf/cross-browser derlemesi. */
export const HEDEFLER = {
  once:  { yok: "https://localhost:18443", hizli3g: "https://localhost:19443", yavas4g: "https://localhost:20443", spki: ".replika/once/spki.txt" },
  sonra: { yok: "https://localhost:28443", hizli3g: "https://localhost:29443", yavas4g: "https://localhost:30443", spki: ".replika/sonra/spki.txt" },
  canli: { yok: "https://pvquant.com" },
  // Faz 3 ara ölçümleri (tek düzeltmenin etkisini ayırmak için; T=38/48)
  araa:  { yok: "https://localhost:38443", hizli3g: "https://localhost:39443", yavas4g: "https://localhost:40443", spki: ".replika/araa/spki.txt" },
  arac:  { yok: "https://localhost:58443", hizli3g: "https://localhost:59443", yavas4g: "https://localhost:60443", spki: ".replika/arac/spki.txt" },
  arad:  { yok: "https://localhost:24443", hizli3g: "https://localhost:25443", yavas4g: "https://localhost:26443", spki: ".replika/arad/spki.txt" },
  arae:  { yok: "https://localhost:34443", hizli3g: "https://localhost:35443", yavas4g: "https://localhost:36443", spki: ".replika/arae/spki.txt" },
  arab:  { yok: "https://localhost:48443", hizli3g: "https://localhost:49443", yavas4g: "https://localhost:50443", spki: ".replika/arab/spki.txt" },
};

/** Görünümler: 390 = iPhone 13 (DPR 3, dokunmatik), 768 = tablet (DPR 2, dokunmatik), 1440 = MacBook (DPR 2), 1920 = harici ekran (DPR 1). */
export const GORUNUMLER = {
  "390x844":   { width: 390,  height: 844,  dpr: 3, mobil: true },
  "768x1024":  { width: 768,  height: 1024, dpr: 2, mobil: true },
  "1440x900":  { width: 1440, height: 900,  dpr: 2, mobil: false },
  "1920x1080": { width: 1920, height: 1080, dpr: 1, mobil: false },
};
export const MOTORLAR = { chromium, firefox, webkit };
export const SAYFALAR = { ana: "/", yontem: "/yontem" };

export async function motorAc(ad, hedef) {
  const ops = {};
  if (ad === "chromium" && HEDEFLER[hedef].spki) {
    const spki = fs.readFileSync(path.join(KOK, HEDEFLER[hedef].spki), "utf8").trim();
    ops.args = ["--ignore-certificate-errors-spki-list=" + spki];      // yerel sertifika «geçerli» sayılır → HTTP önbelleği çalışır
  }
  return MOTORLAR[ad].launch(ops);
}

export function baglamAyar(motor, g, ek = {}) {
  const ayar = { viewport: { width: g.width, height: g.height }, deviceScaleFactor: g.dpr, ignoreHTTPSErrors: true, ...ek };
  if (g.mobil) { ayar.hasTouch = true; if (motor !== "firefox") ayar.isMobile = true; }   // Firefox isMobile desteklemez (Playwright)
  return ayar;
}

/** Her gezinmede sayfaya enjekte edilen ölçüm betiği: LCP/CLS/FCP/uzun görev gözlemcileri + motor bağımsız kayma izleyicisi. */
export const OLCUM_BETIGI = `(() => {
  const tanimla = (n) => { if (!n || !n.tagName) return n && n.nodeName ? n.nodeName : null;
    const s = n.tagName.toLowerCase() + (n.id ? "#" + n.id : "") + (n.className && typeof n.className === "string" ? "." + n.className.trim().split(/\\s+/).slice(0, 3).join(".") : "");
    const k = n.currentSrc || n.src || ""; const m = (n.textContent || "").trim().slice(0, 40);
    return s + (k ? " [" + k.split("/").pop() + "]" : "") + (m && !k ? " «" + m + "»" : ""); };
  const o = window.__olc = { lcp: [], ls: [], lt: [], ev: [], yok: [], kayma: {}, kare: [] };
  const destek = (window.PerformanceObserver && PerformanceObserver.supportedEntryTypes) || [];
  const izle = (tip, f) => { if (!destek.includes(tip)) { o.yok.push(tip); return; } try { new PerformanceObserver((l) => l.getEntries().forEach(f)).observe({ type: tip, buffered: true }); } catch (e) { o.yok.push(tip); } };
  izle("largest-contentful-paint", (e) => o.lcp.push({ t: e.startTime, boy: e.size, el: tanimla(e.element), url: (e.url || "").split("/").pop() }));
  izle("layout-shift", (e) => { if (!e.hadRecentInput) o.ls.push({ t: e.startTime, v: e.value, kaynak: (e.sources || []).map((s) => tanimla(s.node)) }); });
  izle("longtask", (e) => o.lt.push({ t: e.startTime, d: e.duration }));
  izle("event", (e) => o.ev.push({ ad: e.name, t: e.startTime, d: e.duration }));
  // motor bağımsız kayma izleyicisi: önemli öğelerin belge içi dikey konumu her karede; ilk görünüşten sonraki en büyük oynama
  const SECICI = ["h1", ".vt-hero__sol .vt-giris", ".vt-hero__eylem", ".vt-hero__mikro", ".vt-ust__ic", ".vt-bolumcubuk", "main section:nth-of-type(2) h2", ".vt-yontem-giris .vt-giris"];
  const bas = performance.now();
  const kare = () => {
    const t = performance.now();
    if (t - bas > 20000) return;
    for (const s of SECICI) { const el = document.querySelector(s); if (!el) continue; const r = el.getBoundingClientRect(); if (r.height === 0 && r.width === 0) continue;
      const y = Math.round(r.top + window.scrollY), x = Math.round(r.left), k = o.kayma[s] || (o.kayma[s] = { ilk: t, y0: y, x0: x, maxDy: 0, maxDx: 0 });
      k.maxDy = Math.max(k.maxDy, Math.abs(y - k.y0)); k.maxDx = Math.max(k.maxDx, Math.abs(x - k.x0)); }
    requestAnimationFrame(kare);
  };
  requestAnimationFrame(kare);
})();`;

/** Gezinme sonrası sayfadan toplanan özet. */
export async function topla(sayfa) {
  return sayfa.evaluate(() => {
    const o = window.__olc || {};
    const n = performance.getEntriesByType("navigation")[0] || {};
    const p = Object.fromEntries(performance.getEntriesByType("paint").map((e) => [e.name, e.startTime]));
    const r = performance.getEntriesByType("resource");
    const boy = (e) => Math.max(e.transferSize || 0, e.encodedBodySize || 0);
    const fcp = p["first-contentful-paint"] ?? null;
    // CLS: 1 sn ara / 5 sn pencereli oturum penceresi (web-vitals tanımı)
    let cls = null;
    if (!o.yok?.includes("layout-shift")) { cls = 0; let pen = 0, ilk = 0, son = 0;
      for (const e of o.ls) { if (pen && e.t - son < 1000 && e.t - ilk < 5000) { pen += e.v; } else { pen = e.v; ilk = e.t; } son = e.t; cls = Math.max(cls, pen); } }
    const lcpSon = o.lcp?.length ? o.lcp[o.lcp.length - 1] : null;
    const tbt = o.yok?.includes("longtask") ? null : o.lt.filter((x) => fcp === null || x.t >= fcp).reduce((s, x) => s + Math.max(0, x.d - 50), 0);
    return {
      ttfb: n.responseStart ?? null, dcl: n.domContentLoadedEventEnd ?? null, load: n.loadEventEnd ?? null,
      fp: p["first-paint"] ?? null, fcp, lcp: lcpSon ? lcpSon.t : null, lcpEl: lcpSon ? lcpSon.el : null, lcpUrl: lcpSon ? lcpSon.url : null, lcpAday: o.lcp?.length ?? 0,
      cls, clsKaynak: (o.ls || []).filter((e) => e.v > 0.001).map((e) => ({ v: +e.v.toFixed(4), t: Math.round(e.t), kaynak: e.kaynak })).slice(0, 12),
      tbt, uzunGorev: o.yok?.includes("longtask") ? null : o.lt.length,
      kayma: Object.fromEntries(Object.entries(o.kayma || {}).map(([s, k]) => [s, { dy: k.maxDy, dx: k.maxDx }])),
      kaynakSayisi: r.length + 1, aktarim: r.reduce((s, e) => s + (e.transferSize || 0), 0) + (n.transferSize || 0),
      enBuyuk: r.map((e) => ({ u: e.name.replace(/^https?:\/\/[^/]+/, "").slice(0, 80), b: boy(e), tur: e.initiatorType })).sort((a, z) => z.b - a.b).slice(0, 10),
      desteklenmeyen: o.yok || [],
    };
  });
}

export function medyan(dizi) {
  const d = dizi.filter((x) => typeof x === "number" && Number.isFinite(x)).sort((a, z) => a - z);
  if (!d.length) return null;
  const m = Math.floor(d.length / 2);
  return d.length % 2 ? d[m] : (d[m - 1] + d[m]) / 2;
}
