// saha.mjs — saha verisi: PageSpeed Insights API (anahtarsız) üzerinden CrUX «loadingExperience» (sayfa ve köken).
// CrUX API'nin kendisi anahtar ister — bu ortamda anahtar yok. Vercel Speed Insights uygulanamaz (site Vercel'de değil).
import fs from "node:fs";
import path from "node:path";
import { KOK } from "./ortak.mjs";
const cikti = path.join(KOK, process.argv[2] || "baseline", "saha.json");
const sonuc = {};
for (const strateji of ["mobile", "desktop"]) {
  const u = `https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=${encodeURIComponent("https://pvquant.com/")}&strategy=${strateji}&category=performance`;
  try {
    const r = await fetch(u); const j = await r.json();
    sonuc[strateji] = { http: r.status, hata: j.error?.message ?? null, sayfa: j.loadingExperience ?? null, koken: j.originLoadingExperience ?? null,
      psiLab: j.lighthouseResult ? { perf: Math.round((j.lighthouseResult.categories.performance.score ?? 0) * 100), lcp: j.lighthouseResult.audits["largest-contentful-paint"]?.numericValue, cls: j.lighthouseResult.audits["cumulative-layout-shift"]?.numericValue, tbt: j.lighthouseResult.audits["total-blocking-time"]?.numericValue } : null };
  } catch (e) { sonuc[strateji] = { hata: String(e) }; }
}
fs.writeFileSync(cikti, JSON.stringify(sonuc, null, 1));
for (const [s, v] of Object.entries(sonuc)) console.log(s, "http", v.http, "| hata", v.hata, "| CrUX sayfa:", v.sayfa?.overall_category ?? (v.sayfa ? "metrik yok" : "veri yok"), "| köken:", v.koken?.overall_category ?? "veri yok", "| PSI lab:", JSON.stringify(v.psiLab));
