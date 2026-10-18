// ozet.mjs — <klasör>/{matris.jsonl, etkilesim.jsonl, lighthouse/lh-*.jsonl, ekran.json, saha.json} → <klasör>/ozet.json + tablolar (markdown).
// node olc/ozet.mjs baseline   → baseline/ozet.json, baseline/TABLOLAR.md
import fs from "node:fs";
import path from "node:path";
import { KOK, GORUNUMLER, medyan } from "./ortak.mjs";

const klasor = path.join(KOK, process.argv[2] || "baseline");
const oku = (f) => (fs.existsSync(f) ? fs.readFileSync(f, "utf8").trim().split("\n").filter(Boolean).map((s) => JSON.parse(s)) : []);
const matris = oku(path.join(klasor, "matris.jsonl"));
const etk = oku(path.join(klasor, "etkilesim.jsonl"));
const lhDir = path.join(klasor, "lighthouse");
const lh = fs.existsSync(lhDir) ? fs.readdirSync(lhDir).filter((f) => f.endsWith(".jsonl")).flatMap((f) => oku(path.join(lhDir, f))) : [];
const MOTOR = ["chromium", "firefox", "webkit"], GOR = Object.keys(GORUNUMLER), AG = ["yok", "hizli3g", "yavas4g"], ONB = ["soguk", "sicak"], SAYFA = ["ana", "yontem"];
const yuvarla = (v, b = 0) => (v === null || v === undefined ? null : Number(v.toFixed(b)));
const grup = (f) => { const m = new Map(); for (const x of matris) { const k = f(x); if (!m.has(k)) m.set(k, []); m.get(k).push(x); } return m; };
const g = grup((x) => [x.motor, x.gorunum, x.ag, x.sayfa].join("|"));
const ozet = { yukleme: {}, surum: {}, lighthouse: {}, etkilesim: {}, hata: {}, lcpOge: {}, enBuyuk: {} };
for (const x of matris) ozet.surum[x.motor] = x.surum;

for (const [k, kosular] of g) for (const o of ONB) {
  const al = (f) => kosular.map((x) => f(x[o])).filter((v) => v !== null && v !== undefined);
  const kaymaMax = kosular.map((x) => Math.max(0, ...Object.values(x[o].kayma || {}).map((d) => Math.max(d.dy, d.dx))));
  ozet.yukleme[k + "|" + o] = {
    n: kosular.length, ttfb: medyan(al((m) => m.ttfb)), fcp: medyan(al((m) => m.fcp)), lcp: medyan(al((m) => m.lcp)),
    cls: kosular.some((x) => x[o].cls === null) ? null : medyan(al((m) => m.cls)), tbt: kosular.some((x) => x[o].tbt === null) ? null : medyan(al((m) => m.tbt)),
    kaymaMax: medyan(kaymaMax), aktarimKB: yuvarla(medyan(al((m) => m.aktarim)) / 1024), istek: medyan(al((m) => m.kaynakSayisi)), load: medyan(al((m) => m.load)),
    lcpOge: [...new Set(al((m) => m.lcpEl))].slice(0, 3),
    hata: kosular.reduce((s, x) => s + (x[o].hata?.konsol?.length || 0) + (x[o].hata?.sayfa?.length || 0) + (x[o].hata?.http?.length || 0) + (x[o].hata?.basarisiz?.length || 0) + (x[o].gezinmeHatasi ? 1 : 0), 0),
  };
}
// hatalar ayrıntılı (benzersiz iletiler)
for (const x of matris) for (const o of ONB) { const h = x[o].hata || {}; for (const [tur, liste] of Object.entries(h)) for (const msg of liste) { const k = `${x.motor} · ${tur} · ${msg}`; ozet.hata[k] = (ozet.hata[k] || 0) + 1; } if (x[o].gezinmeHatasi) { const k = `${x.motor} · gezinme · ${x[o].gezinmeHatasi}`; ozet.hata[k] = (ozet.hata[k] || 0) + 1; } }
// en büyük kaynaklar: 1440 kısıtsız soğuk «/»
for (const mot of MOTOR) { const x = matris.find((y) => y.motor === mot && y.gorunum === "1440x900" && y.ag === "yok" && y.sayfa === "ana"); if (x) ozet.enBuyuk[mot] = x.soguk.enBuyuk; }
// Lighthouse
const lhg = new Map(); for (const r of lh) { const k = [r.hedef, r.sayfa, r.tur].join("|"); if (!lhg.has(k)) lhg.set(k, []); lhg.get(k).push(r); }
for (const [k, rs] of lhg) ozet.lighthouse[k] = { n: rs.length, chrome: rs[0].chrome, surum: rs[0].surum,
  skor: Object.fromEntries(["performance", "accessibility", "best-practices", "seo"].map((c) => [c, medyan(rs.map((r) => r.skor[c]))])),
  metrik: Object.fromEntries(["fcp", "lcp", "tbt", "cls", "si", "ttfb"].map((m) => [m, medyan(rs.map((r) => r.metrik[m]))])),
  uyari: Object.fromEntries(Object.entries(rs[0].uyari).filter(([, v]) => v.skor !== null && v.skor < 0.9).map(([id, v]) => [id, { deger: v.deger, ornek: v.ozet.filter(Boolean).slice(0, 3) }])) };
// Etkileşim
const eg = new Map(); for (const r of etk) { const k = [r.motor, r.gorunum].join("|"); if (!eg.has(k)) eg.set(k, []); eg.get(k).push(r); }
for (const [k, rs] of eg) ozet.etkilesim[k] = { n: rs.length, videoOynuyor: rs.filter((r) => r.videoOynuyor).length,
  menuAc: medyan(rs.map((r) => r.menuAc)), ctaUzerine: medyan(rs.map((r) => r.ctaUzerine)), girisGirdi: medyan(rs.map((r) => r.girisGirdi)), girisSure: medyan(rs.map((r) => r.girisSure)),
  bostaOrtanca: medyan(rs.map((r) => r.bosta?.ortanca)), bostaP95: medyan(rs.map((r) => r.bosta?.p95)), bostaYavas: medyan(rs.map((r) => r.bosta?.yavas)),
  kaydirmaOrtanca: medyan(rs.map((r) => r.kaydirma?.ortanca)), kaydirmaP95: medyan(rs.map((r) => r.kaydirma?.p95)), kaydirmaYavas: medyan(rs.map((r) => r.kaydirma?.yavas)),
  hata: rs.filter((r) => r.girisHata).map((r) => r.girisHata) };
fs.writeFileSync(path.join(klasor, "ozet.json"), JSON.stringify(ozet, null, 1));

// ── markdown tabloları
const h = (v, b = 0) => (v === null || v === undefined ? "—" : typeof v === "number" ? v.toFixed(b).replace(".", ",") : String(v));
let md = `<!-- olc/ozet.mjs tarafından üretildi; elle düzenlemeyin -->\n\nSürümler: ${Object.entries(ozet.surum).map(([m, s]) => `${m} ${s}`).join(" · ")}\n\n`;
for (const s of SAYFA) for (const [met, ad, b] of [["lcp", "LCP (ms)", 0], ["fcp", "FCP (ms)", 0], ["cls", "CLS (yalnız Chromium destekler)", 3], ["kaymaMax", "En büyük öğe kayması, px (tüm motorlar; kendi izleyicimiz)", 0], ["tbt", "TBT yaklaşımı, ms (uzun görev; yalnız Chromium)", 0], ["aktarimKB", "Aktarım (KB, gözlem penceresi sonunda)", 0]]) {
  md += `\n#### «${s === "ana" ? "/" : "/yontem"}» — ${ad} — medyan (3 koşu)\n\n| ağ · önbellek | ${MOTOR.flatMap((m) => GOR.map((v) => `${m.slice(0, 2)} ${v.split("x")[0]}`)).join(" | ")} |\n|---|${MOTOR.flatMap(() => GOR.map(() => "---:")).join("|")}|\n`;
  for (const a of AG) for (const o of ONB) md += `| ${a} · ${o === "soguk" ? "soğuk" : "sıcak"} | ${MOTOR.flatMap((m) => GOR.map((v) => h(ozet.yukleme[[m, v, a, s, o].join("|")]?.[met], b))).join(" | ")} |\n`;
}
md += `\n#### Firefox / Chromium LCP oranı (soğuk, medyan) — kabul ölçütü: fark < %20\n\n| sayfa · ağ | ${GOR.join(" | ")} |\n|---|${GOR.map(() => "---:").join("|")}|\n`;
for (const s of SAYFA) for (const a of AG) md += `| ${s} · ${a} | ${GOR.map((v) => { const f = ozet.yukleme[["firefox", v, a, s, "soguk"].join("|")]?.lcp, c = ozet.yukleme[["chromium", v, a, s, "soguk"].join("|")]?.lcp; return f && c ? h(f / c, 2) : "—"; }).join(" | ")} |\n`;
md += `\n#### LCP öğesi (soğuk, kısıtsız)\n\n| motor | ${GOR.join(" | ")} |\n|---|${GOR.map(() => "---").join("|")}|\n`;
for (const m of MOTOR) md += `| ${m} | ${GOR.map((v) => (ozet.yukleme[[m, v, "yok", "ana", "soguk"].join("|")]?.lcpOge || []).map((e) => String(e).replace(/\|/g, "/").slice(0, 60)).join("<br>")).join(" | ")} |\n`;
if (Object.keys(ozet.lighthouse).length) {
  md += `\n#### Lighthouse (Chromium) — medyan\n\n| hedef · sayfa · tür | Perf | Erişil. | En iyi uyg. | SEO | FCP | LCP | TBT | CLS | SI | TTFB |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n`;
  for (const [k, v] of Object.entries(ozet.lighthouse).sort()) md += `| ${k.replace(/\|/g, " · ")} | ${h(v.skor.performance)} | ${h(v.skor.accessibility)} | ${h(v.skor["best-practices"])} | ${h(v.skor.seo)} | ${h(v.metrik.fcp)} | ${h(v.metrik.lcp)} | ${h(v.metrik.tbt)} | ${h(v.metrik.cls, 3)} | ${h(v.metrik.si)} | ${h(v.metrik.ttfb)} |\n`;
}
if (Object.keys(ozet.etkilesim).length) {
  md += `\n#### Etkileşim ve kare süreleri — medyan (başsız tarayıcı; motorlar arası/önce-sonra kıyası içindir)\n\n| motor · görünüm | menü açma (girdi→kare, ms) | CTA üzerine | «Panele giriş» → form (ms) | boşta kare p95 (video oynarken) | boşta >33 ms | kaydırma kare p95 | kaydırma >33 ms |\n|---|---:|---:|---:|---:|---:|---:|---:|\n`;
  for (const m of MOTOR) for (const v of GOR) { const e = ozet.etkilesim[[m, v].join("|")]; if (e) md += `| ${m} · ${v} | ${h(e.menuAc)} | ${h(e.ctaUzerine)} | ${h(e.girisSure)} | ${h(e.bostaP95, 1)} | %${h(100 * (e.bostaYavas ?? 0))} | ${h(e.kaydirmaP95, 1)} | %${h(100 * (e.kaydirmaYavas ?? 0))} |\n`; }
}
const hataListe = Object.entries(ozet.hata).sort((a, z) => z[1] - a[1]);
md += `\n#### Konsol hataları, 4xx/5xx ve başarısız istekler (tüm yüklemeler)\n\n${hataListe.length ? hataListe.slice(0, 30).map(([k, n]) => `- ${n}× ${k.replace(/\|/g, "/")}`).join("\n") : "- yok (0)"}\n`;
md += `\n#### En büyük 10 kaynak — 1440×900, kısıtsız, soğuk, «/»\n\n`;
for (const [m, liste] of Object.entries(ozet.enBuyuk)) md += `- **${m}**: ${liste.map((r) => `${r.u.split("/").pop()} ${(r.b / 1024).toFixed(0)} KB`).join(" · ")}\n`;
fs.writeFileSync(path.join(klasor, "TABLOLAR.md"), md);
console.log("yazıldı:", path.join(klasor, "TABLOLAR.md"), "·", matris.length, "matris satırı ·", etk.length, "etkileşim ·", lh.length, "Lighthouse");
