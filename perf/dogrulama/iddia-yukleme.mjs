// Bağımsız denetim: yukleme.jsonl → kart tamamlanma, video playing, sıcak bayt (+12 sn) — ham koşular + medyan
import fs from "node:fs";
const med = (a) => { const d = a.filter((x) => typeof x === "number" && isFinite(x)).sort((x, y) => x - y); if (!d.length) return null; const m = d.length >> 1; return d.length % 2 ? d[m] : (d[m - 1] + d[m]) / 2; };
const L = fs.readFileSync(process.argv[2], "utf8").trim().split("\n").map((s) => JSON.parse(s));
const g = {}; for (const r of L) { const k = [r.hedef, r.motor, r.gorunum, r.ag, r.degisken].join("|"); (g[k] = g[k] || []).push(r); }
const png = (x) => Object.entries(x.img || {}).filter(([u]) => u.endsWith(".png"));
for (const [k, rs] of Object.entries(g).sort()) {
  const son = rs.map((r) => { const p = png(r.soguk); return p.length === 8 ? Math.max(...p.map(([, t]) => t)) : null; });
  const n = rs.map((r) => png(r.soguk).length);
  const oyn = rs.map((r) => r.soguk.oynadi), sb = rs.map((r) => r.sicak?.bayt?.["+12"]);
  console.log(k.padEnd(44), "n", rs.length, "kart8son", JSON.stringify(son), "med", med(son), "| adet", n.join(","), "| playing", JSON.stringify(oyn.map((v) => v && Math.round(v))), "med", med(oyn), "| sicak+12MB", sb.map((v) => v == null ? "-" : (v / 1e6).toFixed(2)).join(","), "| sogukFCP", med(rs.map(r=>r.soguk.fcp)));
}
