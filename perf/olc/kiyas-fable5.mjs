// kiyas-fable5.mjs — fable5-once (288 hücre) ↔ fable5-sonra (390/1440, 4 hat) kontrol kıyası: soğuk FCP/LCP ve sıcak FCP medyanları,
// |fark| > 150 ms hücreler işaretli. node olc/kiyas-fable5.mjs > analiz/fable5-sonra/KIYAS-FABLE5.md
import fs from "node:fs";
const oku = (f) => fs.readFileSync(f, "utf8").trim().split("\n").map(JSON.parse);
const A = oku("analiz/fable5-once/matris.jsonl"), B = oku("analiz/fable5-sonra/matris.jsonl");
const med = (a) => { a = a.filter(Number.isFinite).sort((x, y) => x - y); return a.length ? (a.length % 2 ? a[(a.length - 1) / 2] : (a[a.length / 2 - 1] + a[a.length / 2]) / 2) : null; };
const h = (v) => (v === null ? "—" : Math.round(v).toLocaleString("tr-TR"));
const M = ["chromium", "edge", "firefox", "webkit"], G = ["390x844", "1440x900"], AG = [["yok", "Kısıtsız"], ["yavas4g", "Slow 4G"], ["hizli3g", "Fast 3G"], ["kablo20", "Kablo 20 Mbps (yalnız sonra)"]];
const sec = (R, m, g, ag, s) => R.filter((r) => r.motor === m && r.gorunum === g && r.ag === ag && r.sayfa === s);
let md = "<!-- olc/kiyas-fable5.mjs üretti -->\n\nÖnce = fable5-once (1494f8e, T=18), sonra = fable5-sonra (çalışma ağacı HEAD, dist bayt bayt aynı, T=28). Medyan (3 koşu), ms. «!» = |fark| > 150 ms.\n";
const sapan = [];
for (const [s, sAd] of [["ana", "/"], ["yontem", "/yontem"]]) for (const [met, metAd, onb] of [["fcp", "FCP soğuk", "soguk"], ["lcp", "LCP soğuk", "soguk"], ["fcp", "FCP sıcak", "sicak"]]) {
  md += `\n### «${sAd}» — ${metAd}: önce → sonra\n\n| hat | ${M.flatMap((m) => G.map((g) => `${m.slice(0, 2)} ${g.split("x")[0]}`)).join(" | ")} |\n|---|${M.flatMap(() => G.map(() => "---:")).join("|")}|\n`;
  for (const [ag, agAd] of AG) md += `| ${agAd} | ${M.flatMap((m) => G.map((g) => { const a = med(sec(A, m, g, ag, s).map((r) => r[onb][met])), b = med(sec(B, m, g, ag, s).map((r) => r[onb][met])); const f = a !== null && b !== null && Math.abs(a - b) > 150; if (f) sapan.push(`${sAd} ${metAd} ${m} ${g} ${agAd}: ${h(a)} → ${h(b)}`); return `${h(a)} → ${h(b)}${f ? " !" : ""}`; })).join(" | ")} |\n`;
}
md += `\n### Sıcak ziyaret: hattan geçen MB (vekil; «/»), önce → sonra\n\n| hat | ${M.flatMap((m) => G.map((g) => `${m.slice(0, 2)} ${g.split("x")[0]}`)).join(" | ")} |\n|---|${M.flatMap(() => G.map(() => "---:")).join("|")}|\n`;
for (const [ag, agAd] of AG.slice(1)) md += `| ${agAd} | ${M.flatMap((m) => G.map((g) => { const a = med(sec(A, m, g, ag, "ana").map((r) => r.sicak.hatBayt)), b = med(sec(B, m, g, ag, "ana").map((r) => r.sicak.hatBayt)); return `${a === null ? "—" : (a / 1e6).toFixed(2)} → ${b === null ? "—" : (b / 1e6).toFixed(2)}`; })).join(" | ")} |\n`;
const hata = (R) => R.reduce((n, r) => n + ["soguk", "sicak"].reduce((k, o) => k + (r[o].hata?.konsol?.length || 0) + (r[o].hata?.sayfa?.length || 0) + (r[o].hata?.http?.length || 0) + (r[o].hata?.basarisiz?.length || 0) + (r[o].gezinmeHatasi ? 1 : 0), 0), 0);
md += `\nKonsol/HTTP/başarısız istek/gezinme hatası: önce ${hata(A)} (${A.length * 2} yükleme), sonra ${hata(B)} (${B.length * 2} yükleme).\n`;
md += `\nGürültü bandı dışına çıkan hücreler (${sapan.length}):\n` + (sapan.length ? sapan.map((x) => "- " + x).join("\n") : "- yok") + "\n";
process.stdout.write(md);
