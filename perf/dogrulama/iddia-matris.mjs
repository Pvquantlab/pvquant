// Bağımsız denetim: matris.jsonl'den medyanlar (ozet.mjs kullanılmadan).
import fs from "node:fs";
const oku = (f) => fs.readFileSync(f, "utf8").trim().split("\n").filter(Boolean).map((s) => JSON.parse(s));
const med = (a) => { const d = a.filter((x) => typeof x === "number" && isFinite(x)).sort((x, y) => x - y); if (!d.length) return null; const m = d.length >> 1; return d.length % 2 ? d[m] : (d[m - 1] + d[m]) / 2; };
const [, , dosya, metrik = "lcp", onb = "soguk", sayfa = "ana"] = process.argv;
const L = oku(dosya);
const M = ["chromium", "firefox", "webkit"], G = ["390x844", "768x1024", "1440x900", "1920x1080"], A = ["yok", "hizli3g", "yavas4g"];
const deger = (r) => {
  const o = r[onb]; if (!o) return null;
  if (metrik === "kayma") return Math.max(0, ...Object.values(o.kayma || {}).map((d) => Math.max(d.dy, d.dx)));
  return o[metrik];
};
const out = {};
for (const a of A) { const row = []; for (const m of M) for (const g of G) {
  const rs = L.filter((r) => r.motor === m && r.gorunum === g && r.ag === a && r.sayfa === sayfa);
  const v = rs.map(deger); out[[m, g, a].join("|")] = { n: rs.length, v, med: med(v) };
  row.push(`${m.slice(0,2)}${g.split("x")[0]}=${med(v) === null ? "—" : Math.round(med(v))}`); }
  console.log(a.padEnd(8), row.join(" ")); }
if (process.env.JSON) fs.writeFileSync(process.env.JSON, JSON.stringify(out));
