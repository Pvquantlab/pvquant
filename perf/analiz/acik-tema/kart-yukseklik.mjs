// 24.10 — yer tutucu yükseklik sondası: bellek dolmuş dönüşte (+61 sn) her kartın yoldaki (yer tutuculu) ve oturmuş
// yüksekliği; fark = yer tutucunun oturmuş içerikle uyuşmazlığı (CLS kaynağı). Çıktı: sayfa | kart | yolda → oturdu | fark.
// kullanım: PW_DIR=/home/user/pvquant/perf CHROME=/opt/pw-browsers/chromium node kart-yukseklik.mjs http://127.0.0.1:4275
import { createRequire } from "node:module";
const pw = createRequire((process.env.PW_DIR ?? process.cwd()) + "/")("playwright");
const base = process.argv[2] ?? "http://127.0.0.1:4275";
const SAYFALAR = ["Kalibrasyon", "Tahminler", "Doğruluk", "Aylık beklenti", "Hakkında", "Portföy"];
const JETON = "x." + Buffer.from('{"role":"admin"}').toString("base64url") + ".y";
const b = await pw.chromium.launch({ headless: true, executablePath: process.env.CHROME ?? undefined });
const ctx = await b.newContext({ viewport: { width: 1440, height: 900 }, locale: "tr-TR", timezoneId: "Europe/Istanbul" });
await ctx.addInitScript(() => { window.__kayma = 0; const G = Date; class S extends G { constructor(...a) { a.length === 0 ? super(G.now() + window.__kayma) : super(...a); } static now() { return G.now() + window.__kayma; } } window.Date = S; });
await ctx.addInitScript(({ j }) => { localStorage.setItem("pvq_token", j); localStorage.setItem("pvq_tema", "acik"); localStorage.setItem("pvq_plant", "a1"); }, { j: JETON });
const p = await ctx.newPage();
await p.goto(base + "/", { waitUntil: "load" }); await p.waitForSelector(".nav-btn");
const tikla = (s) => p.locator(".nav-btn", { hasText: new RegExp(`^${s}$`) }).click();
const olc = () => p.evaluate(() => [...document.querySelectorAll(".icerik .kart")].map((k) => ({ ad: (k.querySelector("h2,h3,.kart-baslik")?.textContent ?? "?").trim().slice(0, 48), y: Math.round(k.getBoundingClientRect().height), yolda: !!k.querySelector(".iskelet-alan") })));
// ısınma: her sayfayı bir kez gez (bellek dolsun), sonra +61 sn kaydır → bayat-önce + yer tutucu yolu
for (const s of SAYFALAR) { await tikla(s); await p.waitForLoadState("networkidle"); await p.waitForTimeout(600); }
await p.evaluate(() => { window.__kayma += 61000; });
console.log("| Sayfa | Kart | yolda → oturdu (px) | fark |\n|---|---|---|---|");
for (const s of SAYFALAR) {
  await tikla(s); await p.waitForTimeout(40);
  const once = await olc();
  await p.waitForLoadState("networkidle"); await p.waitForTimeout(1500);
  const sonra = await olc();
  for (let i = 0; i < Math.max(once.length, sonra.length); i++) {
    const a = once[i], c = sonra.find((x) => x.ad === a?.ad) ?? sonra[i];
    if (a?.yolda || (a && c && a.y !== c.y)) console.log(`| ${s} | ${a?.ad ?? c?.ad} | ${a?.y ?? "—"} → ${c?.y ?? "—"} | ${a && c ? c.y - a.y : "—"}${a?.yolda ? " (yer tutuculu)" : ""} |`);
  }
}
await b.close();
