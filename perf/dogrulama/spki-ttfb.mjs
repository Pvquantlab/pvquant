// spki-ttfb.mjs — bağımsız doğrulama: Chromium'a geçersiz (eski) SPKI verilince yavaş 4G TTFB'si ne kadar şişiyor?
// node dogrulama/spki-ttfb.mjs  → dogrulama/spki-ttfb.jsonl. «once» replikası, Slow 4G vekili (20443), 390x844, soğuk bağlam.
// canli = ortak.mjs yaprakSpki (o anki yaprak); bayat = rastgele 32 bayt (sertifika eşleşmez → ignoreHTTPSErrors yolu).
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";
import { yaprakSpki, GORUNUMLER, baglamAyar } from "../olc/ortak.mjs";

const KOK = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const URL_ = "https://localhost:20443/";
const bekle = (ms) => new Promise((r) => setTimeout(r, ms));
async function hatBos() { const bas = Date.now(); let bos = 0; while (Date.now() - bas < 90000) { const d = await fetch("http://127.0.0.1:20444/").then((r) => r.json()).catch(() => null); if (d && d.kuyruk <= 0 && d.asagiMs <= 0) { if ((bos += 250) >= 750) return; } else bos = 0; await bekle(250); } }
const canli = await yaprakSpki("once"), bayat = crypto.randomBytes(32).toString("base64");
const dosya = path.join(KOK, "dogrulama/spki-ttfb.jsonl");
for (const tur of ["canli", "bayat", "canli", "bayat"]) {
  const t = await chromium.launch({ args: ["--ignore-certificate-errors-spki-list=" + (tur === "canli" ? canli : bayat)] });
  const b = await t.newContext(baglamAyar("chromium", GORUNUMLER["390x844"]));
  const s = await b.newPage();
  await hatBos();
  await s.goto(URL_, { waitUntil: "load", timeout: 120000 });
  await s.waitForTimeout(1500);
  const m = await s.evaluate(() => { const n = performance.getEntriesByType("navigation")[0]; const p = Object.fromEntries(performance.getEntriesByType("paint").map((e) => [e.name, e.startTime])); return { ttfb: n.responseStart, baglanti: n.connectEnd - n.connectStart, istek: n.responseStart - n.requestStart, fcp: p["first-contentful-paint"] ?? null }; });
  await t.close();
  const satir = { tur, ...Object.fromEntries(Object.entries(m).map(([k, v]) => [k, v === null ? null : Math.round(v)])) };
  fs.appendFileSync(dosya, JSON.stringify(satir) + "\n");
  console.log(JSON.stringify(satir));
}
