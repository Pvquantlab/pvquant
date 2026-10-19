// rapor-tablo.mjs — REPORT.md §2 tabloları ham dosyalardan (elle sayı yazılmasın): Lighthouse, FCP/LCP seçili hücreler, Firefox kaydırma
// A/B, boşta video, HTML boyu. node olc/rapor-tablo.mjs [--sonra son] [--hedef final2] > <dosya>
import fs from "node:fs";
import path from "node:path";
import { KOK, medyan } from "./ortak.mjs";

const arg = (ad, vars) => { const i = process.argv.indexOf("--" + ad); return i > 0 ? process.argv[i + 1] : vars; };
const SON = arg("sonra", "son"), HEDEF = arg("hedef", "final2");
const oku = (f) => JSON.parse(fs.readFileSync(path.join(KOK, f), "utf8"));
const satir = (f) => (fs.existsSync(path.join(KOK, f)) ? fs.readFileSync(path.join(KOK, f), "utf8").trim().split("\n").filter(Boolean).map((s) => JSON.parse(s)) : []);
const A = oku("baseline/ozet.json"), B = oku(`${SON}/ozet.json`);
const h = (v, b = 0) => (v === null || v === undefined || Number.isNaN(v) ? "—" : typeof v === "number" ? v.toFixed(b).replace(".", ",").replace(/\B(?=(\d{3})+(?!\d))/g, " ") : String(v));
const sn = (v) => (v === null || v === undefined ? "—" : (v / 1000).toFixed(2).replace(".", ","));
let md = `<!-- olc/rapor-tablo.mjs --sonra ${SON} --hedef ${HEDEF} tarafından üretildi -->\n`;

// ── Lighthouse: koşular ve medyan
const lhA = satir("baseline/lighthouse/lh-once.jsonl"), lhB = satir(`${SON}/lighthouse/lh-${HEDEF}.jsonl`);
md += `\n**Lighthouse 12.8.2 (replika; Chromium; 3 koşu, medyan)**\n\n| Sayfa · tür | Perf önce → sonra (koşular) | LCP | FCP | TBT | CLS | Erişil. / En iyi uyg. / SEO |\n|---|---|---:|---:|---:|---:|---|\n`;
for (const s of ["ana", "yontem"]) for (const t of ["mobil", "masaustu"]) {
  const a = lhA.filter((r) => r.sayfa === s && r.tur === t), b = lhB.filter((r) => r.sayfa === s && r.tur === t);
  const m = (l, f) => medyan(l.map(f));
  const skor = (l) => `${h(m(l, (r) => r.skor.performance))} (${l.map((r) => r.skor.performance).join("/")})`;
  const birim = t === "mobil" ? (v) => `${sn(v)} sn` : (v) => `${h(v)} ms`;
  md += `| \`${s === "ana" ? "/" : "/yontem"}\` · ${t === "mobil" ? "mobil" : "masaüstü"} | **${skor(a)} → ${skor(b)}** | ${birim(m(a, (r) => r.metrik.lcp))} → ${birim(m(b, (r) => r.metrik.lcp))} | ${birim(m(a, (r) => r.metrik.fcp))} → ${birim(m(b, (r) => r.metrik.fcp))} | ${h(m(a, (r) => r.metrik.tbt))} → ${h(m(b, (r) => r.metrik.tbt))} ms | ${h(m(a, (r) => r.metrik.cls), 3)} → ${h(m(b, (r) => r.metrik.cls), 3)} | ${[...new Set(a.map((r) => `${r.skor.accessibility}/${r.skor["best-practices"]}/${r.skor.seo}`))].join(",")} → ${[...new Set(b.map((r) => `${r.skor.accessibility}/${r.skor["best-practices"]}/${r.skor.seo}`))].join(",")} |\n`;
}

// ── FCP / LCP seçili hücreler (soğuk, medyan; önce → sonra)
const MOTOR = ["chromium", "firefox", "webkit"], GOR = ["390x844", "768x1024", "1440x900", "1920x1080"], AG = [["yok", "Kısıtsız"], ["yavas4g", "Slow 4G"], ["hizli3g", "Fast 3G"]];
for (const [sayfa, met, ad] of [["ana", "fcp", "«/» FCP"], ["ana", "lcp", "«/» LCP"], ["yontem", "fcp", "«/yontem» FCP (= LCP)"]]) {
  md += `\n**${ad}, soğuk, medyan (ms): önce → sonra**\n\n| | ${MOTOR.flatMap((m) => GOR.map((g) => `${m[0].toUpperCase() + m.slice(1, 2)} ${g.split("x")[0]}`)).join(" | ")} |\n|---|${MOTOR.flatMap(() => GOR.map(() => "---:")).join("|")}|\n`;
  for (const [ag, agAd] of AG) md += `| ${agAd} | ${MOTOR.flatMap((m) => GOR.map((g) => { const k = [m, g, ag, sayfa, "soguk"].join("|"); return `${h(A.yukleme[k]?.[met])} → ${h(B.yukleme[k]?.[met])}`; })).join(" | ")} |\n`;
}
// en büyük öğe kayması ve CLS
let kaymaA = 0, kaymaB = 0, clsA = 0, clsB = 0;
for (const [k, v] of Object.entries(A.yukleme)) { if (k.endsWith("soguk")) kaymaA = Math.max(kaymaA, v.kaymaMax ?? 0); if (k.startsWith("chromium") && typeof v.cls === "number") clsA = Math.max(clsA, v.cls); }
for (const [k, v] of Object.entries(B.yukleme)) { if (k.endsWith("soguk")) kaymaB = Math.max(kaymaB, v.kaymaMax ?? 0); if (k.startsWith("chromium") && typeof v.cls === "number") clsB = Math.max(clsB, v.cls); }
md += `\nEn büyük öğe kayması (soğuk, tüm motor × görünüm × ağ × sayfa hücrelerinin en kötü medyanı): ${h(kaymaA)} → ${h(kaymaB)} px · Chromium CLS en kötü medyan: ${h(clsA, 3)} → ${h(clsB, 3)}\n`;
const hataB = Object.entries(B.hata).filter(([k]) => !/PARSED_DATA_CACHED/.test(k)).reduce((s, [, n]) => s + n, 0);
md += `Konsol hatası / 4xx-5xx / başarısız istek (sonra matrisi, ${Object.values(B.yukleme).reduce((s, v) => s + (v.n || 0), 0)} yükleme): ${hataB}\n`;

// ── Firefox kaydırma A/B (stok Firefox, pencereli; önceki derleme «sonra» = 0dee665 ↔ son derleme; dönüşümlü)
const ab = [1, 2, 3].flatMap((k) => satir(`${SON}/firefox-kaydirma/k${k}/boya.jsonl`).map((r) => ({ ...r, tur: k })));
if (ab.length) {
  md += `\n**Firefox kaydırma ve boşta (stok Firefox ${ab[0].surum?.replace("firefox/", "")}, pencereli; 0dee665 ↔ ${HEDEF}, dönüşümlü 3 koşu, açılıştan ~5 sn sonra)**\n\n| Görünüm | Kaydırma CPU (çekirdek) | Kaydırma kare p95 (ms) | Kaçan kare | Kaydırmada sunulan video karesi (3 sn) | Düşen video karesi | Boşta CPU |\n|---|---|---|---|---|---|---|\n`;
  for (const g of ["1440x900", "390x844"]) {
    const l = (hd) => ab.filter((r) => r.gorunum === g && r.hedef === hd).map((r) => r.sonuc.mevcut);
    const a = l("sonra"), b = l(HEDEF);
    const s = (x, f, d = 2) => `${x.map((v) => h(f(v), d)).join(" / ")}`;
    md += `| ${g.split("x")[0]} @${g === "1440x900" ? 2 : 3} | ${s(a, (v) => v.kaydirma.cpu)} → ${s(b, (v) => v.kaydirma.cpu)} | ${s(a, (v) => v.kaydirma.p95, 0)} → ${s(b, (v) => v.kaydirma.p95, 0)} | %${s(a, (v) => 100 * v.kaydirma.kacan, 0)} → %${s(b, (v) => 100 * v.kaydirma.kacan, 0)} | ${s(a, (v) => v.kaydirma.videoKare, 0)} → ${s(b, (v) => v.kaydirma.videoKare, 0)} | ${s(a, (v) => v.kaydirma.videoKalite?.dusen ?? null, 0)} → ${s(b, (v) => v.kaydirma.videoKalite?.dusen ?? null, 0)} | ${s(a, (v) => v.bosta.cpu)} → ${s(b, (v) => v.bosta.cpu)} |\n`;
  }
}
// ── boşta video (30 sn)
const vz = satir(`${SON}/video-zaman.jsonl`);
if (vz.length) {
  md += `\n**Boşta video, 30 sn (stok Firefox, pencereli, 1440×900@2; 5 sn'lik 6 pencere)**\n\n| Koşu | Tuval | Düşen / toplam kare | Sunulan kare (rVFC) | CPU (çekirdek) |\n|---|---|---|---|---|\n`;
  for (const r of vz) md += `| ${r.kosu} | ${r.pencereler[0].gl ?? "—"} | ${r.pencereler.map((p) => `${p.dusen}/${p.toplam}`).join(" ")} | ${r.pencereler.map((p) => p.rvfc).join(" ")} | ${r.pencereler.map((p) => h(p.cpu, 2)).join(" ")} |\n`;
}
// ── HTML boyu
const boy = (ad) => { const d = path.join(KOK, ".replika", ad, "dist"); return fs.existsSync(d) ? { ham: fs.statSync(path.join(d, "index.html")).size, br: fs.statSync(path.join(d, "index.html.br")).size } : null; };
const bo = boy("once"), bs = boy(HEDEF);
if (bo && bs) md += `\nindex.html: ${h(bo.ham)} B (br ${h(bo.br)}) → ${h(bs.ham)} B (br ${h(bs.br)}) · ayrı CSS isteği: var → yok (gömülü)\n`;
process.stdout.write(md);
