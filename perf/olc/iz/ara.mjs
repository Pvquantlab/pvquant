import fs from "node:fs";
const ev = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const [a, z] = [Number(process.argv[3]), Number(process.argv[4])];
const nav = ev.find((e) => e.name === "navigationStart" && e.args?.data?.isLoadingMainFrame && /localhost/.test(e.args.data.documentLoaderURL || ""));
const t0 = nav.ts, ms = (t) => (t - t0) / 1000;
const ad = {}; for (const e of ev) if (e.name === "thread_name") ad[`${e.pid}:${e.tid}`] = e.args.name;
const sec = ev.filter((e) => e.ts && ms(e.ts) >= a && ms(e.ts) <= z && e.ph !== "M");
const say = {};
for (const e of sec) { const k = `${ad[`${e.pid}:${e.tid}`] || e.tid}|${e.name}`; say[k] = (say[k] || 0) + 1; }
for (const e of sec.filter((e) => !/^(ThreadControllerImpl::RunTask|RunTask|SequenceManager|TaskQueueManager|ThreadPool_RunTask|Receive mojo message|SimpleWatcher|MessagePort|ScopedBlockingCall)/.test(e.name)).slice(0, 400)) {
  const th = ad[`${e.pid}:${e.tid}`] || e.tid;
  if (/ThreadPool|Network|IO|Media|Chrome_Child|NetworkService/.test(th) && !/Resource|Font|Decode|Image|Paint/.test(e.name)) continue;
  console.log(ms(e.ts).toFixed(1).padStart(7), (e.dur ? "+" + (e.dur / 1000).toFixed(1) : "").padEnd(7), String(th).slice(0, 22).padEnd(22), e.ph, e.name, JSON.stringify(e.args?.data ?? e.args ?? {}).slice(0, 120));
}
