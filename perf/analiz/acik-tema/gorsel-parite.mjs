// 24.10 — görsel parite: önce (4274) ile sonra (4275) derlemelerinin 9 panel sayfası, açık + koyu temada,
// veri oturduktan sonra tam sayfa kare; pixelmatch farkı; yatay taşma; konsol hataları.
// Amaç: (1) koyu tema değişmedi mi? (2) açık temada görsel bozulma var mı? Sayı uydurulmaz: her değer tarayıcıdan.
// kullanım: PW_DIR=/home/user/pvquant/perf CHROME=/opt/pw-browsers/chromium node gorsel-parite.mjs
import fs from "node:fs";
import { createRequire } from "node:module";
const req = createRequire((process.env.PW_DIR ?? process.cwd()) + "/");
const pw = req("playwright"); const { PNG } = req("pngjs"); const pixelmatch = req("pixelmatch").default ?? req("pixelmatch");
const SAYFALAR = ["Portföy", "Santralim", "Veri yükleme", "Kalibrasyon", "Tahminler", "Doğruluk", "Aylık beklenti", "Raporlar", "Hakkında"];
const DERLEME = { once: "http://127.0.0.1:4274", sonra: "http://127.0.0.1:4275" };
const JETON = "x." + Buffer.from('{"role":"admin"}').toString("base64url") + ".y";
const SABIT_MS = Date.UTC(2026, 9, 24, 9, 30, 0); // 24.10.2026 12:30 İstanbul — iki derlemede aynı «şimdi»
const b = await pw.chromium.launch({ headless: true, executablePath: process.env.CHROME ?? undefined });
const kareler = {}; const hatalar = {}; const tasma = {};
for (const tema of ["acik", "koyu"]) for (const [ad, base] of Object.entries(DERLEME)) {
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 }, locale: "tr-TR", timezoneId: "Europe/Istanbul", reducedMotion: "reduce", deviceScaleFactor: 1 });
  await ctx.addInitScript(({ j, tema, sabit }) => {
    localStorage.setItem("pvq_token", j); localStorage.setItem("pvq_tema", tema); localStorage.setItem("pvq_plant", "a1");
    const G = Date; class S extends G { constructor(...a) { a.length === 0 ? super(sabit) : super(...a); } static now() { return sabit; } } window.Date = S;
  }, { j: JETON, tema, sabit: SABIT_MS });
  const p = await ctx.newPage(); const h = [];
  p.on("pageerror", (e) => h.push("istisna: " + e.message.slice(0, 160)));
  p.on("console", (m) => { if (m.type() === "error" && !/404/.test(m.text())) h.push("konsol: " + m.text().slice(0, 160)); });
  await p.goto(base + "/", { waitUntil: "load" }); await p.waitForSelector(".nav-btn"); await p.waitForTimeout(1500);
  const dizin = `gorsel/${tema}/${ad}`; fs.mkdirSync(dizin, { recursive: true });
  for (const s of SAYFALAR) {
    await p.locator(".nav-btn", { hasText: new RegExp(`^${s}$`) }).click();
    await p.waitForLoadState("networkidle"); await p.waitForTimeout(2500);
    await p.evaluate(() => window.scrollTo(0, 0));
    const dosya = `${dizin}/${s.replace(/\s+/g, "-")}.png`;
    await p.screenshot({ path: dosya, fullPage: true });
    (kareler[`${tema}/${s}`] ??= {})[ad] = dosya;
    (tasma[`${tema}/${s}`] ??= {})[ad] = await p.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  }
  hatalar[`${tema}/${ad}`] = h;
  await ctx.close();
}
await b.close();
console.log("| Tema / sayfa | fark px | oran | boyut önce → sonra | taşma önce → sonra |\n|---|---|---|---|---|");
for (const [k, v] of Object.entries(kareler)) {
  const a = PNG.sync.read(fs.readFileSync(v.once)), c = PNG.sync.read(fs.readFileSync(v.sonra));
  const w = Math.max(a.width, c.width), hh = Math.max(a.height, c.height);
  const buyut = (im) => { if (im.width === w && im.height === hh) return im; const o = new PNG({ width: w, height: hh }); PNG.bitblt(im, o, 0, 0, im.width, im.height, 0, 0); return o; };
  const A = buyut(a), C = buyut(c), D = new PNG({ width: w, height: hh });
  const fark = pixelmatch(A.data, C.data, D.data, w, hh, { threshold: 0.1 });
  if (fark > 0) fs.writeFileSync(v.sonra.replace(/\.png$/, ".fark.png"), PNG.sync.write(D));
  console.log(`| ${k} | ${fark} | ${(100 * fark / (w * hh)).toFixed(3)}% | ${a.width}×${a.height} → ${c.width}×${c.height} | ${tasma[k].once} → ${tasma[k].sonra} |`);
}
for (const [k, v] of Object.entries(hatalar)) console.log(`konsol/istisna ${k}: ${v.length}${v.length ? "\n  " + v.join("\n  ") : ""}`);
