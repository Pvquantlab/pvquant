// Chromium izleme: yavaş hatta soğuk yükleme, ana iş parçacığı olayları + kaynak bitişleri + FCP
import { HEDEFLER, GORUNUMLER, motorAc, baglamAyar, yaprakSpki } from "../ortak.mjs";
import fs from "node:fs";
const arg = (ad, vars) => { const i = process.argv.indexOf("--" + ad); return i > 0 ? process.argv[i + 1] : vars; };
const hedef = arg("hedef", "sonra"), gAd = arg("gorunum", "390x844"), ag = arg("ag", "yavas4g"), cikti = arg("cikti", "/tmp/iz.json");
const bekle = (ms) => new Promise((r) => setTimeout(r, ms));
async function hatBos(url) { const p = Number(new URL(url).port) + 1; let b = 0; for (let i = 0; i < 400; i++) { const d = await fetch(`http://127.0.0.1:${p}/`).then((r) => r.json()).catch(() => null); if (d && d.kuyruk <= 0 && d.asagiMs <= 0) { if ((b += 250) >= 750) return; } else b = 0; await bekle(250); } }
const t = arg("kanal", "") ? await (await import("playwright")).chromium.launch({ channel: arg("kanal"), args: ["--ignore-certificate-errors-spki-list=" + (await yaprakSpki(hedef))] }) : await motorAc("chromium", hedef);
console.log("sürüm", t.version());
const b = await t.newContext(baglamAyar("chromium", GORUNUMLER[gAd])); const s = await b.newPage();
const url = HEDEFLER[hedef][ag] + "/"; await hatBos(url);
const cdp = await b.newCDPSession(s);
const olaylar = [];
cdp.on("Tracing.dataCollected", (e) => olaylar.push(...e.value));
const bitti = new Promise((r) => cdp.once("Tracing.tracingComplete", r));
await cdp.send("Tracing.start", { traceConfig: { includedCategories: ["devtools.timeline", "disabled-by-default-devtools.timeline", "blink", "loading", "blink.user_timing", "v8.execute", "disabled-by-default-devtools.timeline.frame", "toplevel", "netlog", "benchmark", "rail", "cc", "viz"] }, transferMode: "ReportEvents" });
await s.goto(url, { waitUntil: "load", timeout: 120000 }); await s.waitForTimeout(Number(arg("bekle", "2500")));
await cdp.send("Tracing.end"); await bitti;
fs.writeFileSync(cikti, JSON.stringify(olaylar));
console.log("olay", olaylar.length, "→", cikti);
await t.close();
