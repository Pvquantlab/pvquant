// matris-birlesik.mjs — ana doğrulama koşuları (2) + ek koşular (3) birleşik medyanları. node dogrulama/matris-birlesik.mjs → dogrulama/matris-birlesik.json
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
const KOK = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const oku = (f) => (fs.existsSync(path.join(KOK, f)) ? fs.readFileSync(path.join(KOK, f), "utf8").trim().split("\n").filter(Boolean).map((s) => JSON.parse(s)) : []);
const medyan = (d0) => { const d = d0.filter(Number.isFinite).sort((a, z) => a - z); if (!d.length) return null; const m = d.length >> 1; return d.length % 2 ? d[m] : (d[m - 1] + d[m]) / 2; };
const K = { once: ["dogrulama/once/matris.jsonl", "dogrulama/ek-once/matris.jsonl"], sonra: ["dogrulama/sonra/matris.jsonl", "dogrulama/ek-sonra/matris.jsonl"] };
const out = {};
for (const [h, fl] of Object.entries(K)) { const r = fl.flatMap(oku); for (const m of ["chromium", "firefox", "webkit"]) for (const g of ["390x844", "1440x900"]) {
  const x = r.filter((y) => y.motor === m && y.gorunum === g && y.ag === "yavas4g" && y.sayfa === "ana"); if (!x.length) continue;
  out[`${h} ${m} ${g}`] = { n: x.length, lcp: x.map((y) => Math.round(y.soguk.lcp)), fcp: x.map((y) => Math.round(y.soguk.fcp)), medLcp: medyan(x.map((y) => y.soguk.lcp)), medFcp: medyan(x.map((y) => y.soguk.fcp)),
    hata: x.reduce((t, y) => t + ["soguk", "sicak"].reduce((u, o) => u + y[o].hata.konsol.length + y[o].hata.sayfa.length + y[o].hata.http.length + y[o].hata.basarisiz.length + (y[o].gezinmeHatasi ? 1 : 0), 0), 0) };
} }
for (const g of ["390x844", "1440x900"]) { const f = out[`sonra firefox ${g}`], c = out[`sonra chromium ${g}`]; if (f && c) out[`oran sonra ${g}`] = { lcp: +(f.medLcp / c.medLcp).toFixed(2), fcp: +(f.medFcp / c.medFcp).toFixed(2) }; }
fs.writeFileSync(path.join(KOK, "dogrulama/matris-birlesik.json"), JSON.stringify(out, null, 1));
for (const [k, v] of Object.entries(out)) console.log(k.padEnd(24), JSON.stringify(v));
