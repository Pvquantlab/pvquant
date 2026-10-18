// Bağımsız denetim: boya.jsonl → sürücü·görünüm·değişken·kip medyanları
import fs from "node:fs";
const med = (a) => { const d = a.filter((x) => typeof x === "number" && isFinite(x)).sort((x, y) => x - y); if (!d.length) return null; const m = d.length >> 1; return d.length % 2 ? d[m] : (d[m - 1] + d[m]) / 2; };
const f = process.argv[2], filtre = process.argv[3] ? new RegExp(process.argv[3]) : null;
const L = fs.readFileSync(f, "utf8").trim().split("\n").map((s) => JSON.parse(s));
const g = {};
for (const r of L) for (const [deg, s] of Object.entries(r.sonuc || {})) for (const kip of ["bosta", "kaydirma"]) {
  const k = [r.hedef, r.surucu, r.mod, r.gorunum, deg, kip].join("|"); (g[k] = g[k] || []).push({ ...s[kip], oynadi: r.oynadi, kosu: r.kosu });
}
for (const [k, a] of Object.entries(g)) { if (filtre && !filtre.test(k)) continue;
  const v = (x) => a.map(x);
  console.log(k.padEnd(52), "n", a.length, "p95", med(v((s) => s.p95))?.toFixed(1), "kacan%", (100 * med(v((s) => s.kacan))).toFixed(0), "cpu", med(v((s) => s.cpu))?.toFixed(2), "dusen", med(v((s) => s.videoKalite?.dusen)), "[", v((s) => s.videoKalite?.dusen).join(","), "] cpu[", v((s) => s.cpu?.toFixed(2)).join(","), "] p95[", v((s) => s.p95?.toFixed(1)).join(","), "] oynadi", v((s) => s.oynadi).join(","));
}
