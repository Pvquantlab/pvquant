// izleme çözümleyici: gezinme başlangıcına göre ms; kaynaklar, ana iş parçacığı üst düzey olaylar, boyama işaretleri
import fs from "node:fs";
const ev = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const nav = ev.find((e) => e.name === "navigationStart" && e.args?.data?.isLoadingMainFrame && /localhost/.test(e.args.data.documentLoaderURL || ""));
const t0 = nav.ts, ms = (t) => Math.round((t - t0) / 1000);
// renderer ana iş parçacığı
const adlar = ev.filter((e) => e.name === "thread_name");
const ana = adlar.filter((e) => e.args.name === "CrRendererMain").map((e) => `${e.pid}:${e.tid}`);
const pidAna = new Set(ev.filter((e) => e.name === "navigationStart" && e.ts === t0).map((e) => `${e.pid}:${e.tid}`));
console.log("ana", [...pidAna]);
const istek = {};
for (const e of ev) {
  const d = e.args?.data; if (!d) continue;
  if (e.name === "ResourceSendRequest") istek[d.requestId] = { url: d.url.split("/").pop().slice(0, 30), bas: ms(e.ts), oncelik: d.priority };
  if (e.name === "ResourceReceiveResponse" && istek[d.requestId]) istek[d.requestId].yanit = ms(e.ts);
  if (e.name === "ResourceFinish" && istek[d.requestId]) istek[d.requestId].son = ms(d.finishTime ? d.finishTime * 1e6 : e.ts);
}
for (const r of Object.values(istek)) if (r.bas < 4000) console.log(`  kaynak ${String(r.bas).padStart(5)}→${String(r.yanit).padStart(5)}→${String(r.son).padStart(5)} ${r.oncelik} ${r.url}`);
const isaret = ev.filter((e) => /firstPaint|firstContentfulPaint|largestContentfulPaint::Candidate|firstMeaningfulPaint|MarkDOMContent|MarkLoad/.test(e.name) && e.ts >= t0);
for (const e of isaret) console.log(`  işaret ${ms(e.ts)} ${e.name} ${e.args?.data?.type || e.args?.data?.nodeName || ""} ${e.args?.data?.size || ""}`);
const anaOlay = ev.filter((e) => pidAna.has(`${e.pid}:${e.tid}`) && e.ph === "X" && e.ts >= t0 && ms(e.ts) < 2500 && e.dur > 3000);
const ust = anaOlay.filter((e) => ["RunTask", "ThreadControllerImpl::RunTask"].includes(e.name));
for (const e of ust) {
  const ic = anaOlay.filter((x) => x !== e && x.ts >= e.ts && x.ts + x.dur <= e.ts + e.dur && !["RunTask", "ThreadControllerImpl::RunTask"].includes(x.name)).sort((a, b) => b.dur - a.dur).slice(0, 4);
  console.log(`  görev ${ms(e.ts)}+${Math.round(e.dur / 1000)} ms: ${ic.map((x) => `${x.name}${x.args?.data?.url ? "(" + x.args.data.url.split("/").pop().slice(0, 20) + ")" : ""} ${Math.round(x.dur / 1000)}`).join(", ")}`);
}
// boyama ile ilgili: BeginMainFrame / Paint / Layout / UpdateLayoutTree / ParseAuthorStyleSheet / ParseHTML zamanları
const sec = ev.filter((e) => pidAna.has(`${e.pid}:${e.tid}`) && e.ts >= t0 && ms(e.ts) < 2500 && /^(ParseHTML|ParseAuthorStyleSheet|UpdateLayoutTree|Layout|Paint|PrePaint|Commit|EvaluateScript|v8.compileModule|v8.evaluateModule|FunctionCall|BeginMainThreadFrame|ScheduleStyleRecalculation|EventDispatch)$/.test(e.name));
const ozet = sec.map((e) => `${ms(e.ts)}${e.dur ? "+" + (e.dur / 1000).toFixed(1) : ""} ${e.name}${e.args?.data?.url ? "(" + String(e.args.data.url).split("/").pop().slice(0, 18) + ")" : ""}${e.name === "ParseHTML" ? "[" + (e.args?.beginData?.startLine ?? "") + "-" + (e.args?.endData?.endLine ?? "") + "]" : ""}`);
console.log("  akış:", ozet.join(" · "));
