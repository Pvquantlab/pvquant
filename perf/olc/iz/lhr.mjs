// lhr.mjs — Lighthouse HTML raporundan LHR: gözlenen FCP/LCP, LCP öğesi, ağ istekleri (başlangıç/bitiş, öncelik)
import fs from "node:fs";
for (const f of process.argv.slice(2)) {
  const h = fs.readFileSync(f, "utf8");
  const m = /window\.__LIGHTHOUSE_JSON__ = (\{[\s\S]*?\});<\/script>/.exec(h);
  const lhr = JSON.parse(m[1]);
  const met = lhr.audits.metrics.details.items[0];
  console.log(f.split("/").slice(-3).join("/"), "perf", Math.round(lhr.categories.performance.score * 100), "LCP", Math.round(lhr.audits["largest-contentful-paint"].numericValue),
    "| gözlenen FCP", met.observedFirstContentfulPaint, "LCP", met.observedLargestContentfulPaint, "DCL", met.observedDomContentLoaded, "load", met.observedLoad);
  const el = lhr.audits["largest-contentful-paint-element"]?.details?.items?.[0]?.items?.[0]?.node;
  console.log("   LCP öğesi:", el?.selector, "«" + (el?.snippet || "").slice(0, 80) + "»");
  const istek = lhr.audits["network-requests"].details.items.filter((r) => /woff2|webp|\.js|\.css|dogrulama|\/$/.test(r.url)).map((r) => `${r.url.split("/").pop().replace(/-[\w-]{8}\.(\w+)$/, ".$1").slice(0, 26) || "html"} ${Math.round(r.networkRequestTime)}→${Math.round(r.networkEndTime)} ${r.priority}`);
  console.log("   " + istek.join(" | "));
}
