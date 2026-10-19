// ab-ozet.mjs — analiz/ab/{boya,yukleme}.jsonl → analiz/ab/AB-TABLOLAR.md (medyanlar).
// node olc/ab-ozet.mjs [analiz/ab]
import fs from "node:fs";
import path from "node:path";
import { KOK, medyan } from "./ortak.mjs";

const klasor = path.join(KOK, process.argv[2] || "analiz/ab");
const oku = (f) => (fs.existsSync(f) ? fs.readFileSync(f, "utf8").trim().split("\n").filter(Boolean).map((s) => JSON.parse(s)) : []);
const h = (v, b = 0) => (v === null || v === undefined || Number.isNaN(v) ? "—" : typeof v === "number" ? v.toFixed(b).replace(".", ",") : String(v));
let md = "<!-- olc/ab-ozet.mjs tarafından üretildi; elle düzenlemeyin -->\n";

// ── boya
const boya = oku(path.join(klasor, "boya.jsonl"));
if (boya.length) {
  const DEG = ["mevcut", "filtresiz", "filtresiz-video", "camsiz", "filtresiz+camsiz", "video-durgun", "ayrisik", "katman"];
  const grup = new Map();
  for (const r of boya) { const k = [r.surucu, r.mod, r.gorunum].join("|"); if (!grup.has(k)) grup.set(k, []); grup.get(k).push(r); }
  md += `\n## Boya / birleştirme A/B (hero ekranda, video oynarken; değişkenler yük SONRASI aynı sayfada; medyan)\n\nSürümler: ${[...new Set(boya.map((r) => `${r.surucu} ${r.surum}`))].join(" · ")}\n`;
  for (const [pencere, ad] of [["bosta", "5 sn boşta (hero, video oynuyor)"], ["kaydirma", "3 sn kaydırma"]]) {
    md += `\n### ${ad}\n\n| sürücü · kip · görünüm | n | değişken | kare p50 (ms) | p95 | kaçan kare | ana iş parç. tıkanma (ms) | video kare/sn (rVFC) | düşen video karesi | CPU (çekirdek) |\n|---|---:|---|---:|---:|---:|---:|---:|---:|---:|\n`;
    for (const [k, rs] of [...grup].sort()) for (const d of DEG) {
      const al = (f) => medyan(rs.map((r) => f(r.sonuc[d]?.[pencere])).filter((v) => v !== null && v !== undefined));
      if (!rs.some((r) => r.sonuc[d])) continue;
      md += `| ${k.replace(/\|/g, " · ")} | ${rs.length} | ${d} | ${h(al((x) => x?.p50), 1)} | ${h(al((x) => x?.p95), 1)} | %${h(100 * (al((x) => x?.kacan) ?? NaN))} | ${h(al((x) => x?.tikanma))} | ${h(al((x) => (x?.videoKare ?? null) === null ? null : x.videoKare / (pencere === "bosta" ? 5 : 3)), 1)} | ${h(al((x) => x?.videoKalite?.dusen ?? null))} | ${h(al((x) => x?.cpu), 2)} |\n`;
    }
  }
  const oynamadi = boya.filter((r) => !r.oynadi).map((r) => r.anahtar);
  if (oynamadi.length) md += `\nVideo 20 sn içinde oynamaya başlamayan koşular (geçersiz sayılmaz ama not edilir): ${oynamadi.join(", ")}\n`;
}

// ── yükleme
const yuk = oku(path.join(klasor, "yukleme.jsonl"));
if (yuk.length) {
  const grup = new Map();
  for (const r of yuk) { const k = [r.motor, r.gorunum, r.ag, r.degisken].join("|"); if (!grup.has(k)) grup.set(k, []); grup.get(k).push(r); }
  const levhaSon = (x) => { const t = Object.entries(x.img || {}).filter(([u]) => u.endsWith(".png")).map(([, t]) => t); return t.length ? Math.max(...t) : null; };
  const levhaN = (x) => Object.keys(x.img || {}).filter((u) => u.endsWith(".png")).length;
  const poster = (x) => Object.entries(x.img || {}).find(([u]) => u.includes("santral-poster"))?.[1] ?? null;
  md += `\n## Yükleme yolu A/B — «mevcut» ↔ «videosuz» (kenar sunucu *.mp4 → 404; aynı derleme) · medyan\n\nBayt: vekilin alıcıya yazdığı (TLS dahil; süren medya indirmeleri dahil), gezinme başından.\n\n| motor · görünüm · ağ · değişken | n | soğuk FCP | soğuk LCP | poster yüklendi | levha (adet / son) | video playing | bayt load | +5 sn | +10 sn | +20 sn | sıcak: video playing | sıcak bayt +12 sn | sıcak kayıt |\n|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---|\n`;
  for (const [k, rs] of [...grup].sort()) {
    const al = (f) => medyan(rs.map(f).filter((v) => v !== null && v !== undefined));
    const mb = (v) => (v === null ? "—" : (v / 1e6).toFixed(2).replace(".", ",") + " MB");
    const kayit = [...new Set(rs.map((r) => { try { const j = JSON.parse(r.sicak.yavasKayit); return j ? `y:${j.y}` : "yok"; } catch { return String(r.sicak.yavasKayit); } }))].join("/");
    md += `| ${k.replace(/\|/g, " · ")} | ${rs.length} | ${h(al((r) => r.soguk.fcp))} | ${h(al((r) => r.soguk.lcp.at(-1)?.t ?? null))} | ${h(al((r) => poster(r.soguk)))} | ${h(al((r) => levhaN(r.soguk)))} / ${h(al((r) => levhaSon(r.soguk)))} | ${h(al((r) => r.soguk.oynadi))} | ${mb(al((r) => r.soguk.bayt.load))} | ${mb(al((r) => r.soguk.bayt["+5"]))} | ${mb(al((r) => r.soguk.bayt["+10"]))} | ${mb(al((r) => r.soguk.bayt["+20"]))} | ${h(al((r) => r.sicak.oynadi))} | ${mb(al((r) => r.sicak.bayt["+12"]))} | ${kayit} |\n`;
  }
  // font dosyaları (soğuk, kısıtlı hat; motor başına birleşik küme)
  md += `\n### Soğuk yüklemede indirilen font dosyaları (motor başına, tüm koşuların birleşimi)\n\n`;
  for (const m of [...new Set(yuk.map((r) => r.motor))]) {
    const say = new Map(); let n = 0;
    for (const r of yuk.filter((x) => x.motor === m)) { n++; for (const f of r.soguk.font || []) say.set(f.u, (say.get(f.u) || 0) + 1); }
    md += `- **${m}** (${n} yükleme): ${[...say].sort().map(([u, c]) => `${u} ×${c}`).join(" · ")}\n`;
  }
}
fs.writeFileSync(path.join(klasor, "AB-TABLOLAR.md"), md);
console.log("yazıldı:", path.join(klasor, "AB-TABLOLAR.md"), boya.length, "boya ·", yuk.length, "yükleme");
