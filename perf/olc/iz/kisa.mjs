// kisa.mjs — izleme özeti: CSS bitişi, «çizime hazır» (render-blocking bitti) anı, FCP, font/poster istekleri
import fs from "node:fs";
for (const f of process.argv.slice(2)) {
  const ev = JSON.parse(fs.readFileSync(f, "utf8"));
  const nav = ev.find((e) => e.name === "navigationStart" && e.args?.data?.isLoadingMainFrame && /localhost/.test(e.args.data.documentLoaderURL || ""));
  const ms = (t) => Math.round((t - nav.ts) / 1000);
  const ist = {};
  for (const e of ev) { const d = e.args?.data; if (!d || e.ts < nav.ts) continue;
    if (e.name === "ResourceSendRequest") ist[d.requestId] = { u: d.url.split("/").pop().replace(/-[\w-]{8}\.(\w+)$/, ".$1"), b: ms(e.ts), o: d.priority, rb: d.renderBlocking };
    if (e.name === "ResourceFinish" && ist[d.requestId]) ist[d.requestId].s = ms(e.ts); }
  const hazir = ev.filter((e) => e.name === "Document::BeginLifecycleUpdatesIfRenderingReady" && e.ts >= nav.ts && e.args?.data).map((e) => [ms(e.ts), e.args.data.have_render_blocking_resources_loaded]);
  const ilkHazir = hazir.find(([t, v], i) => v && i > 0 && hazir.slice(0, i).some(([, w]) => !w));
  const fcp = ev.find((e) => e.name === "firstContentfulPaint" && e.ts >= nav.ts);
  const css = Object.values(ist).find((r) => /\.css$/.test(r.u));
  const sec = Object.values(ist).filter((r) => /woff2|webp|\.js$|dogrulama/.test(r.u) && r.b < 3000);
  console.log(`${f}: CSS ${css?.b}→${css?.s} · çizime hazır ${ilkHazir?.[0]} · FCP ${fcp ? ms(fcp.ts) : "—"}\n   ` + sec.map((r) => `${r.u} ${r.b}→${r.s ?? "…"}${r.rb && r.rb !== "non_blocking" ? " [" + r.rb + "]" : ""}`).join(" | "));
}
