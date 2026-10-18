// Bağımsız denetim: Lighthouse HTML raporundan gömülü LHR'yi çıkar; FCP anından önce başlayan istekleri listele
import fs from "node:fs";
for (const f of process.argv.slice(2)) {
  const h = fs.readFileSync(f, "utf8"); const m = h.match(/window\.__LIGHTHOUSE_JSON__ = (\{.*?\});<\/script>/s); if (!m) { console.log(f, "LHR yok"); continue; }
  const lhr = JSON.parse(m[1]); const a = lhr.audits;
  const obs = a.metrics?.details?.items?.[0] || {}; const fcpObs = obs.observedFirstContentfulPaint, t0 = obs.observedNavigationStart ?? 0;
  const reqs = (a["network-requests"]?.details?.items || []).map((r) => ({ u: r.url.split("/").pop().slice(0, 40), s: Math.round(r.networkRequestTime ?? r.startTime ?? 0), b: r.transferSize, p: r.priority }));
  const once = reqs.filter((r) => r.s <= fcpObs);
  console.log(f.split("/").pop(), "simFCP", Math.round(a["first-contentful-paint"].numericValue), "simLCP", Math.round(a["largest-contentful-paint"].numericValue), "obsFCP", fcpObs, "| FCP öncesi başlayan istek:", once.length, once.map((r) => `${r.u}@${r.s}(${r.p})`).join(" "));
}
