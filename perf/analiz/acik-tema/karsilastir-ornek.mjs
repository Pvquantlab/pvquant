// 24.10 — örnek kip (API'siz) önce/sonra: gecis-tema.mjs JSON'larından Markdown tablo (tekrar ziyaret medyanları).
import fs from "node:fs";
const d = (a, b) => `${a ?? "—"} → ${b ?? "—"}`;
for (const t of ["acik", "koyu"]) {
  const o = JSON.parse(fs.readFileSync(`once/${t}-cpu1.json`, "utf8")), s = JSON.parse(fs.readFileSync(`sonra/${t}-cpu1.json`, "utf8"));
  console.log(`\n### Örnek kip — ${t} (CPU 1×, tekrar ziyaret medyan/3; «önce → sonra»)\n\n| Sayfa | hazır ms | görev ms | betik ms | stil ms | yerleşim ms | uzun görev |\n|---|---|---|---|---|---|---|`);
  const nesne = (x) => (Array.isArray(x) ? Object.fromEntries(x) : x);
  const ot = nesne(o.tekrar), st = nesne(s.tekrar);
  for (const p of Object.keys(ot)) { const a = ot[p], b = st[p]; console.log(`| ${p} | ${d(a.hazirMedyan, b?.hazirMedyan)} | ${d(a.gorevMs, b?.gorevMs)} | ${d(a.betikMs, b?.betikMs)} | ${d(a.stilMs, b?.stilMs)} | ${d(a.yerlesimMs, b?.yerlesimMs)} | ${d(a.uzunGorev, b?.uzunGorev)} |`); }
  const oi = nesne(o.ilkZiyaret), si = nesne(s.ilkZiyaret);
  console.log(`\nİlk ziyaret hazır ms: ${Object.keys(oi).map((p) => `${p} ${oi[p].hazir} → ${si[p]?.hazir}`).join(" · ")}`);
  console.log(`Hızlı 3×9 süre/heap: önce ${o.hizliTur.map((x) => `${x.sureMs}/${x.heapMB}`).join(" · ")} → sonra ${s.hizliTur.map((x) => `${x.sureMs}/${x.heapMB}`).join(" · ")}; konsol ${o.hatalar.length} → ${s.hatalar.length}`);
}
