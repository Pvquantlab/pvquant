// kiyas.mjs — önce/sonra karşılaştırması ve kabul ölçütleri: baseline/ozet.json ↔ after/ozet.json (+ Lighthouse, piksel, A/B).
// node olc/kiyas.mjs [--sonra after] [--hedef sonra]   → <sonra>/KIYAS.md (üretilir; elle düzenlenmez). 19.10: son derleme için --sonra son --hedef sonra5
import fs from "node:fs";
import path from "node:path";
import { KOK, medyan } from "./ortak.mjs";

const arg = (ad, vars) => { const i = process.argv.indexOf("--" + ad); return i > 0 ? process.argv[i + 1] : vars; };
const SON = arg("sonra", "after"), SON_HEDEF = arg("hedef", "sonra");
const oku = (f) => JSON.parse(fs.readFileSync(path.join(KOK, f), "utf8"));
const satirlar = (f) => (fs.existsSync(path.join(KOK, f)) ? fs.readFileSync(path.join(KOK, f), "utf8").trim().split("\n").filter(Boolean).map((s) => JSON.parse(s)) : []);
const A = oku("baseline/ozet.json"), B = oku(`${SON}/ozet.json`);
const MOTOR = ["chromium", "firefox", "webkit"], GOR = ["390x844", "768x1024", "1440x900", "1920x1080"], AG = ["yok", "hizli3g", "yavas4g"];
const h = (v, b = 0) => (v === null || v === undefined || Number.isNaN(v) ? "—" : typeof v === "number" ? v.toFixed(b).replace(".", ",") : String(v));
const ok = (b) => (b ? "✅" : "❌");
let md = "<!-- olc/kiyas.mjs tarafından üretildi; elle düzenlemeyin -->\n\n";

// ── yükleme metrikleri: önce → sonra (soğuk, medyan)
for (const sayfa of ["ana", "yontem"]) for (const [met, ad, b] of [["lcp", "LCP (ms)", 0], ["fcp", "FCP (ms)", 0], ["kaymaMax", "en büyük öğe kayması (px)", 0]]) {
  md += `\n### «${sayfa === "ana" ? "/" : "/yontem"}» ${ad} — soğuk, medyan: önce → sonra\n\n| ağ | ${MOTOR.flatMap((m) => GOR.map((g) => `${m.slice(0, 2)} ${g.split("x")[0]}`)).join(" | ")} |\n|---|${MOTOR.flatMap(() => GOR.map(() => "---:")).join("|")}|\n`;
  for (const ag of AG) md += `| ${ag} | ${MOTOR.flatMap((m) => GOR.map((g) => { const k = [m, g, ag, sayfa, "soguk"].join("|"); return `${h(A.yukleme[k]?.[met], b)} → ${h(B.yukleme[k]?.[met], b)}`; })).join(" | ")} |\n`;
}
// sıcak yükleme LCP + vekil baytı (yalnız sonra)
md += `\n### «/» sıcak yükleme LCP (ms): önce → sonra\n\n| ağ | ${MOTOR.flatMap((m) => GOR.map((g) => `${m.slice(0, 2)} ${g.split("x")[0]}`)).join(" | ")} |\n|---|${MOTOR.flatMap(() => GOR.map(() => "---:")).join("|")}|\n`;
for (const ag of AG) md += `| ${ag} | ${MOTOR.flatMap((m) => GOR.map((g) => { const k = [m, g, ag, "ana", "sicak"].join("|"); return `${h(A.yukleme[k]?.lcp)} → ${h(B.yukleme[k]?.lcp)}`; })).join(" | ")} |\n`;

// LCP öğesi (sonra)
md += `\n### LCP öğesi (sonra; soğuk, «/»)\n\n| motor · ağ | ${GOR.join(" | ")} |\n|---|${GOR.map(() => "---").join("|")}|\n`;
for (const m of MOTOR) for (const ag of ["yok", "yavas4g"]) md += `| ${m} · ${ag} | ${GOR.map((g) => (B.yukleme[[m, g, ag, "ana", "soguk"].join("|")]?.lcpOge || []).map((e) => String(e).replace(/\|/g, "/").slice(0, 44)).join("<br>")).join(" | ")} |\n`;

// ── kabul ölçütleri
const krit = [];
// 1) Lighthouse ≥ 90 (sonra, replika) her sayfa × mobil/masaüstü; erişilebilirlik / en iyi uyg. düşmez
for (const sayfa of ["ana", "yontem"]) for (const tur of ["mobil", "masaustu"]) {
  const a = A.lighthouse[["once", sayfa, tur].join("|")], b = B.lighthouse[[SON_HEDEF, sayfa, tur].join("|")];
  if (!b) { krit.push([`Lighthouse perf ≥ 90 · ${sayfa} · ${tur}`, "ölçülmedi", false]); continue; }
  krit.push([`Lighthouse perf ≥ 90 · ${sayfa} · ${tur}`, `${h(a?.skor.performance)} → ${h(b.skor.performance)}`, b.skor.performance >= 90]);
  krit.push([`Erişilebilirlik / En iyi uyg. düşmez · ${sayfa} · ${tur}`, `${h(a?.skor.accessibility)}/${h(a?.skor["best-practices"])} → ${h(b.skor.accessibility)}/${h(b.skor["best-practices"])}`,
    b.skor.accessibility >= (a?.skor.accessibility ?? 0) && b.skor["best-practices"] >= (a?.skor["best-practices"] ?? 0)]);
  krit.push([`TBT ≤ 200 ms (Lighthouse) · ${sayfa} · ${tur}`, `${h(a?.metrik.tbt)} → ${h(b.metrik.tbt)} ms`, b.metrik.tbt <= 200]);
  krit.push([`CLS ≤ 0,1 (Lighthouse) · ${sayfa} · ${tur}`, `${h(a?.metrik.cls, 3)} → ${h(b.metrik.cls, 3)}`, b.metrik.cls <= 0.1]);
}
// 2) LCP ≤ 2,5 sn mobil Slow 4G (matris: 390 ve 768, soğuk, her motor, her sayfa)
for (const sayfa of ["ana", "yontem"]) for (const g of ["390x844", "768x1024"]) for (const m of MOTOR) {
  const k = [m, g, "yavas4g", sayfa, "soguk"].join("|"); const v = B.yukleme[k]?.lcp;
  krit.push([`LCP ≤ 2,5 sn · Slow 4G · ${sayfa} · ${m} ${g}`, `${h(A.yukleme[k]?.lcp)} → ${h(v)} ms`, v !== null && v !== undefined && v <= 2500]);
}
// 3) CLS ≤ 0,1 (Chromium matris, tüm hücreler) ve tüm motorlarda öğe kayması
let clsMax = 0; for (const [k, v] of Object.entries(B.yukleme)) if (k.startsWith("chromium") && typeof v.cls === "number") clsMax = Math.max(clsMax, v.cls);
let clsMaxA = 0; for (const [k, v] of Object.entries(A.yukleme)) if (k.startsWith("chromium") && typeof v.cls === "number") clsMaxA = Math.max(clsMaxA, v.cls);
krit.push(["CLS ≤ 0,1 (matris, Chromium, tüm hücreler, en kötü medyan)", `${h(clsMaxA, 3)} → ${h(clsMax, 3)}`, clsMax <= 0.1]);
// 4) Firefox / Chromium LCP farkı < %20 (Firefox Chromium'dan en fazla %20 yavaş) — soğuk, her sayfa × görünüm × ağ
for (const sayfa of ["ana", "yontem"]) for (const ag of AG) for (const g of GOR) {
  const f = B.yukleme[["firefox", g, ag, sayfa, "soguk"].join("|")]?.lcp, c = B.yukleme[["chromium", g, ag, sayfa, "soguk"].join("|")]?.lcp;
  const fa = A.yukleme[["firefox", g, ag, sayfa, "soguk"].join("|")]?.lcp, ca = A.yukleme[["chromium", g, ag, sayfa, "soguk"].join("|")]?.lcp;
  if (f && c) krit.push([`Firefox/Chromium LCP ≤ 1,20 · ${sayfa} · ${ag} · ${g}`, `${h(fa / ca, 2)} → ${h(f / c, 2)} (${h(f)} / ${h(c)} ms)`, f / c <= 1.2]);
}
// 5) konsol hatası / başarısız istek (matris, sonra)
const hataSay = Object.entries(B.hata).filter(([k]) => !/PARSED_DATA_CACHED/.test(k)).reduce((s, [, n]) => s + n, 0);
krit.push(["Konsol hatası, 4xx/5xx, başarısız istek = 0 (sonra matrisi, 432 yükleme)", `${Object.entries(A.hata).filter(([k]) => !/PARSED_DATA_CACHED/.test(k)).reduce((s, [, n]) => s + n, 0)} → ${hataSay}`, hataSay === 0]);
// 6) görsel regresyon (piksel.json varsa)
if (fs.existsSync(path.join(KOK, `${SON}/piksel.json`))) {
  const p = oku(`${SON}/piksel.json`);
  const bolum = fs.existsSync(path.join(KOK, `${SON}/piksel-bolum.json`)) ? oku(`${SON}/piksel-bolum.json`) : {};
  const ayni = p.filter((r) => r.durum === "aynı");
  krit.push([`Piksel · birebir aynı görüntüler (${p.length} görüntü; Chromium + Firefox tamamı, WebKit «/» tam sayfa hariç)`, `${ayni.length} / ${p.length} aynı`, p.every((r) => r.durum === "aynı" || (r.ad.startsWith("webkit-") && r.ad.endsWith("-ana.png")))]);
  for (const r of p.filter((r) => r.durum !== "aynı")) {
    const g = r.ad.replace(/^webkit-/, "").replace(/-ana\.png$/, ""), b = bolum[`webkit-${g}`] || [];
    const degisen = b.filter((x) => x.durum === "boy değişti").map((x) => x.bolum);
    const enCok = Math.max(0, ...b.filter((x) => x.oran !== undefined && !/katmanlar/.test(x.bolum)).map((x) => x.oran));
    const beklenen = r.ad.startsWith("webkit-") && degisen.length === 1 && /isler/.test(degisen[0]) && enCok < 0.02;
    krit.push([`Piksel · ${r.ad} (bilinçli değişiklik K6: yalnız #isler kısalmalı)`, `${r.durum}; boyu değişen bölüm: ${degisen.join(", ") || "—"}; diğer bölümlerde en çok %${h(100 * enCok, 2)} (alt-piksel kayması; «katmanlar» gürültü bandı hariç)`, beklenen]);
  }
}
md += `\n## Kabul ölçütleri (sonra)\n\n| ölçüt | önce → sonra | durum |\n|---|---|:---:|\n` + krit.map(([a, b, c]) => `| ${a} | ${b} | ${ok(c)} |`).join("\n") + "\n";
md += `\nÖzet: ${krit.filter((k) => k[2]).length} / ${krit.length} ölçüt karşılandı.\n`;

// ── etkileşim (başsız) önce → sonra
md += `\n### Etkileşim (başsız; motorlar arası ve önce/sonra kıyası) — medyan: önce → sonra\n\n| motor · görünüm | menü (ms) | giriş → form (ms) | kaydırma kare p95 (ms) | kaydırma >33 ms | koşu hatası |\n|---|---:|---:|---:|---:|---:|\n`;
const ka = satirlar("baseline/etkilesim.jsonl"), kb = satirlar(`${SON}/etkilesim.jsonl`);
for (const m of MOTOR) for (const g of GOR) {
  const e = A.etkilesim[[m, g].join("|")], f = B.etkilesim[[m, g].join("|")];
  const hataA = ka.filter((r) => r.motor === m && r.gorunum === g && r.kosuHatasi).length, hataB = kb.filter((r) => r.motor === m && r.gorunum === g && r.kosuHatasi).length;
  md += `| ${m} · ${g} | ${h(e?.menuAc)} → ${h(f?.menuAc)} | ${h(e?.girisSure)} → ${h(f?.girisSure)} | ${h(e?.kaydirmaP95, 1)} → ${h(f?.kaydirmaP95, 1)} | %${h(100 * (e?.kaydirmaYavas ?? NaN))} → %${h(100 * (f?.kaydirmaYavas ?? NaN))} | ${hataA} → ${hataB} |\n`;
}
fs.writeFileSync(path.join(KOK, `${SON}/KIYAS.md`), md);
console.log(`yazıldı: ${SON}/KIYAS.md ·`, krit.filter((k) => k[2]).length, "/", krit.length, "ölçüt");
