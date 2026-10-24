// 24.10 — önce/sonra karşılaştırma: panel-gecis-olcum.mjs JSON'larından Markdown tablo.
// kullanım: node karsilastir.mjs [cpu=1]  → once/panel-gecis-once-<tema>-cpu<cpu>.json ile sonra/… yan yana
import fs from "node:fs";
const cpu = process.argv[2] ?? "1";
const oku = (e, t) => { const y = `${e}/panel-gecis-${e}-${t}-cpu${cpu}.json`; return fs.existsSync(y) ? JSON.parse(fs.readFileSync(y, "utf8")) : null; };
const d = (a, b) => (a == null || b == null ? "—" : `${a} → ${b}`);
const satir = (ad, o, s) => `| ${ad} | ${d(o?.h1, s?.h1)} | ${d(o?.ilkIcerik, s?.ilkIcerik)} | ${d(o?.tam, s?.tam)} | ${d(o?.istek, s?.istek)} | ${d(o?.cls, s?.cls)} |`;
const BAS = "| Sayfa | başlık (h1) ms | ilk içerik ms | tam ms | istek | CLS |\n|---|---|---|---|---|---|";
for (const t of ["acik", "oto", "koyu"]) {
  const o = oku("once", t), s = oku("sonra", t);
  if (!o || !s) { console.log(`\n### ${t}: eksik dosya (önce ${!!o}, sonra ${!!s})`); continue; }
  console.log(`\n### Tema kipi: ${t} (CPU ${cpu}×, değerler «önce → sonra»)`);
  for (const [k, ad] of [["soguk", "Soğuk ilk ziyaret"], ["sicak", "Sıcak tekrar (<60 sn, medyan/3)"], ["dolmus", "Bellek dolmuş dönüş (+61 sn)"]]) {
    console.log(`\n**${ad}**\n\n${BAS}`);
    for (const sayfa of Object.keys({ ...o[k], ...s[k] })) console.log(satir(sayfa, o[k][sayfa], s[k][sayfa]));
  }
  console.log(`\n**Geri dönüş (A → B → A)**\n\n${BAS}`);
  for (let i = 0; i < Math.max(o.geriDonus.length, s.geriDonus.length); i++) console.log(satir(o.geriDonus[i]?.akis ?? s.geriDonus[i]?.akis, o.geriDonus[i], s.geriDonus[i]));
  console.log(`\n**Hızlı ardışık 3×9** — süre ms / heap MB: önce ${o.hizli.map((x) => `${x.sureMs}/${x.heapMB}`).join(" · ")} → sonra ${s.hizli.map((x) => `${x.sureMs}/${x.heapMB}`).join(" · ")}`);
  console.log(`\n**Konsol/istisna**: önce ${o.hatalar.length} → sonra ${s.hatalar.length}${s.hatalar.length ? "\n" + s.hatalar.map((h) => "- " + h).join("\n") : ""}`);
}
