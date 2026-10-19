// matris-kiyas.mjs — bağımsız yeniden ölçüm (dogrulama/once|sonra/matris.jsonl, 2 koşu) ↔ raporun verisi (baseline|after/matris.jsonl, 3 koşu).
// node dogrulama/matris-kiyas.mjs  → dogrulama/matris-kiyas.json + konsola tablo. Ölçütler ozet.mjs ile aynı tanım:
// soğuk LCP, soğuk FCP, kaymaMax = koşu başına max(dy, dx) seçiciler üstünde → koşular arası medyan. Hata sayıları da toplanır.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const KOK = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const oku = (f) => (fs.existsSync(path.join(KOK, f)) ? fs.readFileSync(path.join(KOK, f), "utf8").trim().split("\n").filter(Boolean).map((s) => JSON.parse(s)) : []);
const medyan = (d0) => { const d = d0.filter((x) => typeof x === "number" && Number.isFinite(x)).sort((a, z) => a - z); if (!d.length) return null; const m = Math.floor(d.length / 2); return d.length % 2 ? d[m] : (d[m - 1] + d[m]) / 2; };
const kayma = (o) => Math.max(0, ...Object.values(o?.kayma || {}).map((d) => Math.max(d.dy, d.dx)));
const KAYNAK = { "dogrulama-once": "dogrulama/once/matris.jsonl", "dogrulama-sonra": "dogrulama/sonra/matris.jsonl", "rapor-once": "baseline/matris.jsonl", "rapor-sonra": "after/matris.jsonl" };
const sonuc = {};
for (const motor of ["chromium", "firefox", "webkit"]) for (const g of ["390x844", "1440x900"]) {
  const hucre = (sonuc[`${motor} ${g}`] = {});
  for (const [ad, f] of Object.entries(KAYNAK)) {
    const r = oku(f).filter((x) => x.motor === motor && x.gorunum === g && x.ag === "yavas4g" && x.sayfa === "ana");
    const hata = r.reduce((t, x) => t + ["soguk", "sicak"].reduce((u, o) => u + (x[o].hata.konsol.length + x[o].hata.sayfa.length + x[o].hata.http.length + x[o].hata.basarisiz.length + (x[o].gezinmeHatasi ? 1 : 0)), 0), 0);
    hucre[ad] = { n: r.length, lcp: r.map((x) => Math.round(x.soguk.lcp)), fcp: r.map((x) => Math.round(x.soguk.fcp)), kayma: r.map((x) => kayma(x.soguk)),
      ttfb: r.map((x) => Math.round(x.soguk.ttfb)), lcpEl: [...new Set(r.map((x) => x.soguk.lcpEl))], cls: r.map((x) => x.soguk.cls),
      sicakLcp: r.map((x) => Math.round(x.sicak.lcp)), hata,
      med: { lcp: medyan(r.map((x) => x.soguk.lcp)), fcp: medyan(r.map((x) => x.soguk.fcp)), kayma: medyan(r.map((x) => kayma(x.soguk))), ttfb: medyan(r.map((x) => x.soguk.ttfb)) } };
  }
}
fs.writeFileSync(path.join(KOK, "dogrulama/matris-kiyas.json"), JSON.stringify(sonuc, null, 1));
const f = (v) => (v === null || v === undefined ? "—" : Math.round(v));
console.log("hücre (yavas4g, «/», soğuk) | LCP med: rapor önce / doğr. önce / rapor sonra / doğr. sonra | FCP med (aynı sıra) | kayma med (aynı sıra) | TTFB med (aynı sıra)");
for (const [k, h] of Object.entries(sonuc)) {
  const s = ["rapor-once", "dogrulama-once", "rapor-sonra", "dogrulama-sonra"];
  console.log(k.padEnd(18), "| LCP", s.map((x) => f(h[x].med.lcp)).join(" / "), "| FCP", s.map((x) => f(h[x].med.fcp)).join(" / "), "| kayma", s.map((x) => f(h[x].med.kayma)).join(" / "), "| TTFB", s.map((x) => f(h[x].med.ttfb)).join(" / "));
  for (const x of ["dogrulama-once", "dogrulama-sonra"]) console.log("   ", x.padEnd(16), "koşular LCP", h[x].lcp.join(","), "FCP", h[x].fcp.join(","), "kayma", h[x].kayma.join(","), "TTFB", h[x].ttfb.join(","), "CLS", h[x].cls.map((c) => c?.toFixed?.(3)).join(","), "hata", h[x].hata, "LCP öğesi", h[x].lcpEl.join(" ; ").slice(0, 90));
}
